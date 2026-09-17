"""Single-page clinical review interface for the Dyania research prototype."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from ui.charts import valve_outlook_curve
from ui.data import ClinicalDataRepository, PatientRecord
from ui.predictor import DurabilityPrediction, PredictionUnavailable, load_posterior, predict_durability
from ui.reporting import build_research_summary
from ui.styles import APP_CSS, metric, safe, section_header


ROOT = Path(__file__).resolve().parent
POSTERIOR_PATH = ROOT / "reports" / "head_a_posterior.nc"

st.set_page_config(page_title="Valve Durability Review | Dyania", page_icon="D", layout="wide", initial_sidebar_state="collapsed")
st.markdown(APP_CSS, unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def get_repository(root: str) -> ClinicalDataRepository:
    return ClinicalDataRepository(root)


@st.cache_resource(show_spinner="Loading durability model…")
def get_posterior(path: str):
    return load_posterior(path)


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def risk_category(risk: float, patient: PatientRecord) -> tuple[str, str]:
    if risk > 0.15 or patient.hvd_stage >= 3:
        return "High", "critical"
    if risk >= 0.05 or patient.hvd_stage == 2:
        return "Moderate", "warning"
    return "Low", ""


def follow_up_plan(risk: float, patient: PatientRecord) -> tuple[str, str, str]:
    flags = patient.alternative_mechanism_flags()
    thrombosis_signal = any(flag.detected and flag.label == "Thrombosis / HALT" for flag in flags)
    delta = patient.gradient_delta
    rapid_gradient = delta is not None and delta >= 10
    if patient.event or patient.bvf_stage >= 2:
        return "Clinical endpoint review", "Confirm the recorded valve-failure or reintervention event", "No automated future interval"
    if risk > 0.15 or patient.hvd_stage >= 3 or rapid_gradient:
        test = "TTE and prompt specialist review"
        if thrombosis_signal:
            test += "; consider 4D cardiac CT/TEE for suspected thrombosis"
        return "Within 6 months", test, "Higher-risk research-protocol pathway"
    if risk >= 0.05 or patient.hvd_stage == 2:
        interval = "Within 6 months" if rapid_gradient else "Within 12 months"
        return interval, "TTE; stress echo only if clinically indicated", "Moderate-risk research-protocol pathway"
    return "Standard surveillance", "TTE according to the treating team's prosthetic-valve schedule", "No model-driven shortening of follow-up"


def stage_track(patient: PatientRecord) -> str:
    names = ("No detected deterioration", "Morphological change", "Moderate HVD", "Severe HVD")
    items = "".join(
        f'<div class="stage {"active" if index == patient.hvd_stage else ""}">'
        f'<div class="stage-num">Stage {index}</div><div class="stage-name">{safe(name)}</div></div>'
        for index, name in enumerate(names)
    )
    return f'<div class="stage-track">{items}</div>'


def patient_facts(patient: PatientRecord) -> str:
    size = f"{patient.valve_size_mm:g} mm" if patient.valve_size_mm is not None else "Unavailable"
    facts = (
        ("Implant approach", patient.approach or "Unavailable"),
        ("Valve", patient.valve_model or "Unavailable"),
        ("Labelled size", size),
        ("Implant year", patient.index_implant_year or "Unavailable"),
        ("Latest record", patient.last_note_year or "Unavailable"),
        ("Evidence confidence", patient.confidence_tier.title()),
    )
    return '<div class="fact-grid">' + "".join(
        f'<div class="fact"><div class="fact-label">{safe(label)}</div><div class="fact-value">{safe(value)}</div></div>'
        for label, value in facts
    ) + "</div>"


def factor_rows(prediction: DurabilityPrediction) -> str:
    rows = []
    for factor in prediction.factors:
        ratio = factor.ratio
        if not factor.applied:
            direction = "Reference / not applied"
        elif ratio.median < 0.98:
            direction = "Shorter modeled durability"
        elif ratio.median > 1.02:
            direction = "Longer modeled durability"
        else:
            direction = "Near the reference"
        rows.append(
            '<div class="factor">'
            f'<div><div class="factor-name">{safe(factor.label)}</div><div class="factor-copy">{safe(factor.description)}</div></div>'
            f'<div class="factor-effect">{safe(direction)}<small>{ratio.median:.2f}× · 89% CrI {ratio.low:.2f}–{ratio.high:.2f}</small></div></div>'
        )
    return "".join(rows)


def flag_rows(patient: PatientRecord) -> str:
    rows = []
    for flag in patient.alternative_mechanism_flags():
        status = "Evidence detected" if flag.detected else "Not detected"
        copy = flag.source if flag.source else flag.next_step
        rows.append(
            f'<div class="flag {"detected" if flag.detected else ""}"><div class="flag-dot"></div>'
            f'<div><div class="flag-name">{safe(flag.label)}</div><div class="flag-copy">{safe(copy)}</div></div>'
            f'<div class="flag-status">{safe(status)}</div></div>'
        )
    return "".join(rows)


try:
    repository = get_repository(str(ROOT))
except Exception as exc:
    st.error("The committed pipeline artifacts could not be loaded. Run the application from the repository root.")
    st.code(str(exc))
    st.stop()

patient_ids = repository.available_patient_ids(model_eligible_only=True)
if not patient_ids:
    st.error("No model-eligible de-identified profiles were found.")
    st.stop()

st.markdown(
    '<div class="app-header"><div class="app-kicker">Dyania · Clinical research interface</div>'
    '<div class="app-title">Bioprosthetic valve durability review</div>'
    '<div class="app-subtitle">A concise view of current valve status, modeled durability and the evidence behind the estimate.</div>'
    '<div class="research-label">Research prototype · Not for clinical use</div></div>',
    unsafe_allow_html=True,
)

st.markdown('<div class="surface"><div class="surface-title">Patient data</div>', unsafe_allow_html=True)
input_col, upload_col = st.columns([1.25, 1], gap="large")
with input_col:
    selected_id = st.selectbox("Select a de-identified patient", patient_ids, format_func=lambda pid: repository.patient(pid).display_label)
with upload_col:
    uploaded = st.file_uploader("Or load a processed patient CSV", type=["csv"], help="The file must contain a profile_key present in the processed model artifacts.")
    if uploaded is not None:
        try:
            uploaded_frame = pd.read_csv(BytesIO(uploaded.getvalue()))
            if "profile_key" not in uploaded_frame.columns or uploaded_frame.empty:
                st.warning("The uploaded CSV needs a non-empty profile_key column.")
            else:
                uploaded_key = str(uploaded_frame.iloc[0]["profile_key"])
                if uploaded_key in patient_ids:
                    selected_id = uploaded_key
                    st.success(f"Loaded {uploaded_key} from the processed pipeline output.")
                else:
                    st.warning("This profile is not present in the current processed model artifacts.")
        except Exception as exc:
            st.warning(f"The CSV could not be read: {exc}")

patient = repository.patient(selected_id)
audit = repository.audit_summary(selected_id)
st.markdown(
    f'<div class="patient-line"><strong>{safe(patient.profile_key)}</strong> <span>· {safe(patient.approach or "Approach unavailable")} · {safe(patient.valve_model or "Valve unavailable")} · {safe(patient.years_followup or 0):s} years observed follow-up</span></div></div>',
    unsafe_allow_html=True,
)

prediction: DurabilityPrediction | None = None
prediction_error: str | None = None
if not patient.event and patient.bvf_stage < 2:
    try:
        prediction = predict_durability(
            get_posterior(str(POSTERIOR_PATH)),
            approach=patient.approach or "",
            valve_family=patient.valve_family,
            family_known=patient.valve_family_known,
            ppm_proxy_flag=patient.ppm_proxy_flag,
            size_known=patient.size_known,
            observed_event_free_years=patient.years_followup or 0.0,
        )
    except (PredictionUnavailable, Exception) as exc:
        prediction_error = str(exc)

if prediction is not None:
    five_year = prediction.conditional_risk_by_horizon[5]
    category, tone = risk_category(five_year.median, patient)
    main_columns = st.columns(3, gap="medium")
    main_columns[0].markdown(metric("Estimated durability", f"{prediction.median_event_free_years.median:.1f} years", f"Median modeled endpoint-free time from implant · 89% CrI {prediction.median_event_free_years.low:.1f}–{prediction.median_event_free_years.high:.1f}"), unsafe_allow_html=True)
    main_columns[1].markdown(metric("Risk in the next 5 years", pct(five_year.median), f"89% CrI {pct(five_year.low)}–{pct(five_year.high)} · from latest event-free follow-up", tone), unsafe_allow_html=True)
    main_columns[2].markdown(metric("Risk category", category, f"Combines modeled risk with current HVD stage {patient.hvd_stage}", tone), unsafe_allow_html=True)
else:
    st.warning("A future durability forecast is not displayed because an endpoint is already recorded or the posterior prediction is unavailable.")
    if prediction_error:
        with st.expander("Technical detail"):
            st.code(prediction_error)

st.markdown('<div class="section">' + section_header("Current valve status", "Deterministic Head B assessment"), unsafe_allow_html=True)
st.markdown(stage_track(patient), unsafe_allow_html=True)
st.markdown(patient_facts(patient), unsafe_allow_html=True)
st.markdown(f'<div class="evidence"><strong>Pipeline rationale:</strong> {safe(patient.rationale)}</div></div>', unsafe_allow_html=True)

if prediction is not None:
    st.markdown('<div class="section">' + section_header("Valve durability outlook", "Patient profile vs approach-matched model reference"), unsafe_allow_html=True)
    st.plotly_chart(valve_outlook_curve(prediction), width="stretch", config={"displayModeBar": False, "responsive": True})
    st.markdown('<div class="method-note">The grey curve is a model-based reference with the same implant approach and no valve-family or small-valve modifier. It is not a population norm. The shaded area is posterior uncertainty; competing mortality is not modeled.</div></div>', unsafe_allow_html=True)

    explain_col, flag_col = st.columns([1.15, 1], gap="large")
    with explain_col:
        st.markdown('<div class="section">' + section_header("Factors affecting this estimate", "Actual Head A inputs"), unsafe_allow_html=True)
        st.markdown(factor_rows(prediction), unsafe_allow_html=True)
        st.markdown('<div class="method-note">Time ratio above 1 indicates longer modeled durability; below 1 indicates shorter modeled durability. These are posterior associations, not causal effects.</div></div>', unsafe_allow_html=True)
    with flag_col:
        st.markdown('<div class="section">' + section_header("Alternative mechanism flags", "Text evidence · clinical review required"), unsafe_allow_html=True)
        st.markdown(flag_rows(patient) + '</div>', unsafe_allow_html=True)

    interval, examination, pathway = follow_up_plan(five_year.median, patient)
    st.markdown('<div class="section">' + section_header("Suggested follow-up window", "Research protocol suggestion · clinician confirmation required"), unsafe_allow_html=True)
    st.markdown(
        f'<div class="followup"><div class="followup-title">{safe(interval)}</div>'
        f'<div class="followup-copy"><strong>Assessment:</strong> {safe(examination)}<br><strong>Basis:</strong> {safe(pathway)}. The treating clinician should confirm or override this suggestion.</div></div></div>',
        unsafe_allow_html=True,
    )

with st.expander("Evidence, methods and limitations"):
    st.markdown(
        f"**Evidence reviewed:** {audit.total_notes} notes, including {audit.post_implant_notes} post-implant notes.  \n"
        f"**Current-state method:** deterministic VARC-3 rules with documented fallback where baseline measurements are unavailable.  \n"
        "**Durability model:** hierarchical Bayesian Weibull AFT using implant approach, valve family and a labelled-size PPM proxy.  \n"
        "**Important limitation:** the fitted cohort has few endpoint events, intervals are wide, competing mortality is not modeled and full-cohort physician adjudication is pending."
    )
    for label, text in patient.evidence:
        st.markdown(f"**{label}:** {text}")

summary = build_research_summary(patient, prediction, audit)
st.download_button("Download research summary", data=summary, file_name=f"{patient.profile_key.lower()}_valve_review.md", mime="text/markdown")
st.markdown('<div class="footer-note">DYANIA · De-identified clinical research prototype · Outputs require physician review</div>', unsafe_allow_html=True)
