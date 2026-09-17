"""Single-page valve durability review."""
from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd
import streamlit as st
import yaml

from ui.charts import valve_outlook_curve
from ui.data import AuditSummary, ClinicalDataRepository, PatientRecord
from ui.predictor import DurabilityPrediction, load_posterior, predict_durability
from ui.reporting import build_research_summary
from ui.styles import APP_CSS, safe, section_header


ROOT = Path(__file__).resolve().parent
POSTERIOR_PATH = ROOT / "reports" / "head_a_posterior.nc"
EVIDENCE_COLUMNS = (
    ("Reintervention evidence", "redo_evidence"),
    ("Explicit SVD evidence", "svd_explicit_evidence"),
    ("Regurgitation evidence", "ar_evidence"),
    ("Morphology evidence", "morphology_evidence"),
    ("Gradient-trend evidence", "gradient_trend_evidence"),
    ("Alternative mechanism evidence", "exclusion_reason"),
)

st.set_page_config(page_title="Valve Durability | Dyania", page_icon="D", layout="wide", initial_sidebar_state="collapsed")
st.markdown(APP_CSS, unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def get_repository(root: str) -> ClinicalDataRepository:
    return ClinicalDataRepository(root)


@st.cache_resource(show_spinner="Loading durability model…")
def get_posterior(path: str):
    return load_posterior(path)


@st.cache_data(show_spinner="Analysing longitudinal notes…")
def process_notes_file(file_bytes: bytes) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the repository's deterministic NLP pipeline on an uploaded workbook."""

    from pipeline import run_pipeline

    with NamedTemporaryFile(suffix=".xlsx") as temporary:
        temporary.write(file_bytes)
        temporary.flush()
        return run_pipeline(temporary.name)


def optional_text(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def optional_float(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def family_mapping() -> dict[str, str]:
    path = ROOT / "config" / "priors.yaml"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as stream:
        return (yaml.safe_load(stream) or {}).get("valve_model_to_family", {})


def patient_from_pipeline(row: pd.Series) -> PatientRecord:
    valve_model = optional_text(row.get("index_valve_model"))
    valve_family = family_mapping().get(valve_model) if valve_model else None
    size = optional_float(row.get("index_valve_size_mm"))
    index_year = optional_float(row.get("index_implant_year"))
    last_year = optional_float(row.get("last_note_year"))
    bvf_stage = int(row.get("bvf_stage", 0) or 0)
    evidence = tuple(
        (label, text)
        for label, column in EVIDENCE_COLUMNS
        if (text := optional_text(row.get(column))) is not None
    )
    return PatientRecord(
        profile_key=str(row["profile_key"]),
        index_implant_year=int(index_year) if index_year is not None else None,
        index_implant_source=optional_text(row.get("index_implant_source")),
        approach=optional_text(row.get("index_approach")),
        valve_model=valve_model,
        valve_family=valve_family,
        valve_family_known=valve_family is not None,
        valve_size_mm=size,
        size_known=size is not None,
        ppm_proxy_flag=size is not None and size <= 21,
        last_note_year=int(last_year) if last_year is not None else None,
        years_followup=optional_float(row.get("years_followup")),
        hvd_stage=int(row.get("hvd_stage", 0) or 0),
        bvf_stage=bvf_stage,
        phenotype=optional_text(row.get("phenotype")),
        confidence_tier=optional_text(row.get("confidence_tier")) or "unknown",
        rationale=optional_text(row.get("rationale")) or "No rationale available.",
        event=bvf_stage >= 2,
        t_lower=optional_float(row.get("years_followup")),
        t_upper=None,
        baseline_mg=optional_float(row.get("baseline_mg")),
        worst_followup_mg=optional_float(row.get("worst_followup_mg")),
        evidence=evidence,
    )


def audit_from_pipeline(frame: pd.DataFrame, profile_key: str) -> AuditSummary:
    rows = frame[frame["profile_key"].astype(str) == profile_key]

    def total(column: str) -> int:
        return int(pd.to_numeric(rows.get(column, pd.Series(dtype=float)), errors="coerce").fillna(0).sum())

    post = rows.get("is_post_implant", pd.Series(False, index=rows.index)).astype(bool)
    return AuditSummary(
        total_notes=len(rows), post_implant_notes=int(post.sum()), redo_hits=total("n_redo"),
        viv_hits=total("n_viv"), svd_hits=total("n_svd_explicit"), gradient_hits=total("n_gradients"),
        morphology_hits=total("n_morphology"), exclusion_hits=total("n_exclusion"),
        note_types=tuple(sorted(rows.get("note_type", pd.Series(dtype=str)).dropna().astype(str).unique())),
    )


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def risk_category(risk: float, patient: PatientRecord) -> str:
    if risk > 0.15 or patient.hvd_stage >= 3:
        return "High"
    if risk >= 0.05 or patient.hvd_stage == 2:
        return "Moderate"
    return "Low"


def follow_up_plan(risk: float, patient: PatientRecord) -> tuple[str, str, str, float | None]:
    flags = tuple(flag for flag in patient.alternative_mechanism_flags() if flag.detected)
    thrombosis = any(flag.label == "Thrombosis / HALT" for flag in flags)
    rapid_gradient = patient.gradient_delta is not None and patient.gradient_delta >= 10
    if patient.event or patient.bvf_stage >= 2:
        return "Review now", "Confirm recorded endpoint", "Valve-failure or reintervention event found", None
    if risk > 0.15 or patient.hvd_stage >= 3 or rapid_gradient:
        test = "TTE and specialist valve review"
        if thrombosis:
            test += "; consider 4D-CT/TEE for suspected thrombosis"
        return "Within 6 months", test, "High-risk or rapid-change pathway", 0.5
    if risk >= 0.05 or patient.hvd_stage == 2:
        return "Within 12 months", "Transthoracic echocardiogram (TTE)", "Moderate risk or Stage 2 HVD", 1.0
    return "Standard schedule", "TTE per treating team's surveillance plan", "No model-driven shortening", 2.0


def stage_track(patient: PatientRecord) -> str:
    names = ("No detected deterioration", "Morphological change", "Moderate HVD", "Severe HVD")
    return '<div class="stage-track">' + "".join(
        f'<div class="stage {"active" if index == patient.hvd_stage else ""}"><div class="stage-num">Stage {index}</div><div class="stage-name">{safe(name)}</div></div>'
        for index, name in enumerate(names)
    ) + "</div>"


def patient_facts(patient: PatientRecord) -> str:
    size = f"{patient.valve_size_mm:g} mm" if patient.valve_size_mm is not None else "Unavailable"
    facts = (("Approach", patient.approach or "Unavailable"), ("Valve", patient.valve_model or "Unavailable"),
             ("Size", size), ("Implant year", patient.index_implant_year or "Unavailable"),
             ("Latest note", patient.last_note_year or "Unavailable"), ("Evidence", patient.confidence_tier.title()))
    return '<div class="fact-grid">' + "".join(
        f'<div class="fact"><div class="fact-label">{safe(label)}</div><div class="fact-value">{safe(value)}</div></div>'
        for label, value in facts
    ) + "</div>"


def factor_rows(prediction: DurabilityPrediction) -> str:
    rows = []
    for factor in prediction.factors:
        ratio = factor.ratio
        if not factor.applied:
            direction = "Reference value"
        elif ratio.median < 0.98:
            direction = "Reduces modeled durability"
        elif ratio.median > 1.02:
            direction = "Increases modeled durability"
        else:
            direction = "Minimal change"
        rows.append(
            f'<div class="factor"><div><div class="factor-name">{safe(factor.label)}</div><div class="factor-copy">{safe(factor.description)}</div></div>'
            f'<div class="factor-effect">{safe(direction)}<small>Time ratio {ratio.median:.2f}× · interval {ratio.low:.2f}–{ratio.high:.2f}</small></div></div>'
        )
    return "".join(rows)


def detected_flag_rows(patient: PatientRecord) -> str:
    flags = tuple(flag for flag in patient.alternative_mechanism_flags() if flag.detected)
    return "".join(
        f'<div class="flag"><div class="flag-dot"></div><div><div class="flag-name">{safe(flag.label)}</div>'
        f'<div class="flag-copy">{safe(flag.source or flag.next_step)}</div></div><div class="flag-status">Review</div></div>'
        for flag in flags
    )


repository = get_repository(str(ROOT))
patient_ids = repository.available_patient_ids(model_eligible_only=True)

st.markdown('<div class="nav"><div class="nav-brand">DY<span>A</span>NIA</div><div class="nav-links"><div class="nav-active">Patient review</div><div>Model evidence</div><div>About</div></div></div>', unsafe_allow_html=True)
st.markdown('<div class="page-intro"><div><div class="page-title">Bioprosthetic valve durability</div><div class="page-subtitle">Upload longitudinal notes to review present valve status, expected durability and the factors supporting the estimate.</div></div><div class="prototype-note">De-identified data · Physician review required</div></div>', unsafe_allow_html=True)

st.markdown('<div class="input-panel"><div class="input-title">Upload clinical notes</div><div class="input-copy">The deterministic NLP pipeline will extract implant details, hemodynamic findings and alternative mechanisms.</div>', unsafe_allow_html=True)
uploaded = st.file_uploader("Longitudinal notes workbook", type=["xlsx"], help="Required columns: Profile Key, Type, Notes, Service Date. Upload de-identified data only.")

patient: PatientRecord
audit: AuditSummary
if uploaded is not None:
    try:
        uploaded_labels, uploaded_audit = process_notes_file(uploaded.getvalue())
        eligible = uploaded_labels[uploaded_labels["index_approach"].notna()]
        if eligible.empty:
            st.error("No dated AVR implant could be identified in the uploaded notes, so durability cannot be estimated.")
            st.stop()
        uploaded_ids = eligible["profile_key"].astype(str).tolist()
        chosen = st.selectbox("Patient found in notes", uploaded_ids) if len(uploaded_ids) > 1 else uploaded_ids[0]
        patient = patient_from_pipeline(eligible[eligible["profile_key"].astype(str) == chosen].iloc[0])
        audit = audit_from_pipeline(uploaded_audit, chosen)
        st.success(f"Analysed {audit.total_notes} notes for {chosen}.")
    except Exception as exc:
        st.error("The notes could not be analysed. Confirm that the workbook uses the expected pipeline columns.")
        with st.expander("Technical detail"):
            st.code(str(exc))
        st.stop()
else:
    with st.expander("Preview with a de-identified sample"):
        selected_id = st.selectbox("Sample patient", patient_ids, format_func=lambda pid: repository.patient(pid).display_label)
    patient = repository.patient(selected_id)
    audit = repository.audit_summary(selected_id)

st.markdown(f'<div class="patient-line"><strong>{safe(patient.profile_key)}</strong> <span>· {safe(patient.approach or "Approach unavailable")} · {safe(patient.valve_model or "Valve unavailable")} · {safe(patient.years_followup or 0)} years observed</span></div></div>', unsafe_allow_html=True)

prediction: DurabilityPrediction | None = None
prediction_error: str | None = None
if not patient.event and patient.bvf_stage < 2:
    try:
        prediction = predict_durability(get_posterior(str(POSTERIOR_PATH)), approach=patient.approach or "", valve_family=patient.valve_family,
                                        family_known=patient.valve_family_known, ppm_proxy_flag=patient.ppm_proxy_flag,
                                        size_known=patient.size_known, observed_event_free_years=patient.years_followup or 0.0)
    except Exception as exc:
        prediction_error = str(exc)

if prediction is None:
    st.warning("A future durability estimate is unavailable because an endpoint is recorded or the extracted implant inputs are incomplete.")
    if prediction_error:
        with st.expander("Technical detail"):
            st.code(prediction_error)
else:
    five_year = prediction.conditional_risk_by_horizon[5]
    category = risk_category(five_year.median, patient)
    interval, examination, basis, review_year = follow_up_plan(five_year.median, patient)
    st.markdown(
        '<div class="summary">'
        f'<div class="summary-main"><div class="summary-label">Estimated valve durability</div><div class="summary-value">{prediction.median_event_free_years.median:.1f} years</div><div class="summary-detail">Median modeled time free from the study endpoint after implantation<br>Uncertainty interval {prediction.median_event_free_years.low:.1f}–{prediction.median_event_free_years.high:.1f} years</div></div>'
        f'<div class="summary-side"><div class="summary-label">Current valve state</div><div class="summary-value">Stage {patient.hvd_stage}</div><div class="summary-detail">{safe(patient.current_state_label)}<br>{safe(patient.confidence_tier.title())} evidence</div></div>'
        f'<div class="summary-side"><div class="summary-label">Risk context</div><div class="summary-value">{safe(category)}</div><div class="summary-detail">{pct(five_year.median)} modeled endpoint risk over the next 5 years</div><div class="risk-note">The 5-year horizon provides a common comparison window; it does not determine treatment by itself.</div></div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section">' + section_header("What shaped this estimate", "Direct explanation of the fitted durability model"), unsafe_allow_html=True)
    st.markdown(factor_rows(prediction) + '<div class="method-note">These are the three inputs used by the current Head A model. Effects are shown on the accelerated-failure-time scale and include posterior uncertainty.</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section">' + section_header("Current valve status", "Findings extracted from the longitudinal record"), unsafe_allow_html=True)
    st.markdown(stage_track(patient), unsafe_allow_html=True)
    st.markdown(patient_facts(patient), unsafe_allow_html=True)
    st.markdown(f'<div class="evidence"><strong>Why this stage:</strong> {safe(patient.rationale)}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section">' + section_header("Durability outlook", "How to read it: right = later in time · higher = more likely to remain event-free"), unsafe_allow_html=True)
    st.plotly_chart(valve_outlook_curve(prediction, review_year=review_year), width="stretch", config={"displayModeBar": False, "responsive": True})
    st.markdown('<div class="method-note"><strong>Teal:</strong> this patient profile. <strong>Grey dashed:</strong> model reference with the same implant approach. <strong>Shaded area:</strong> uncertainty. The vertical marker is the suggested reassessment point, not a predicted operation date.</div></div>', unsafe_allow_html=True)

    detected_flags = detected_flag_rows(patient)
    if detected_flags:
        st.markdown('<div class="section">' + section_header("Additional findings to review", "Alternative mechanisms detected in the notes"), unsafe_allow_html=True)
        st.markdown(detected_flags + '</div>', unsafe_allow_html=True)

    st.markdown('<div class="section">' + section_header("Next review", "Suggested window · treating clinician confirms or overrides"), unsafe_allow_html=True)
    st.markdown(
        '<div class="followup-grid">'
        f'<div class="followup-cell"><div class="followup-label">When</div><div class="followup-value">{safe(interval)}</div></div>'
        f'<div class="followup-cell"><div class="followup-label">Assessment</div><div class="followup-value">{safe(examination)}</div></div>'
        f'<div class="followup-cell"><div class="followup-label">Why</div><div class="followup-value">{safe(basis)}</div></div></div>'
        '<div class="followup-foot">Decision-support output only. Symptoms, new examination findings and clinician judgement take priority over this interval.</div></div>',
        unsafe_allow_html=True,
    )

with st.expander("Evidence and model limitations"):
    st.markdown(
        f"**Notes reviewed:** {audit.total_notes}, including {audit.post_implant_notes} after implantation.  \n"
        "**Current valve state:** deterministic VARC-3/Capodanno rule pipeline.  \n"
        "**Durability estimate:** fitted hierarchical Bayesian Weibull AFT posterior using approach, valve family and small-valve/PPM proxy.  \n"
        "**Limitations:** small endpoint count, wide uncertainty, no competing-mortality model and physician adjudication still pending."
    )
    for label, text in patient.evidence:
        st.markdown(f"**{label}:** {text}")

summary = build_research_summary(patient, prediction, audit)
st.download_button("Download case summary", data=summary, file_name=f"{patient.profile_key.lower()}_valve_review.md", mime="text/markdown")
st.markdown('<div class="footer-note">DYANIA · Valve durability decision support · De-identified data only</div>', unsafe_allow_html=True)
