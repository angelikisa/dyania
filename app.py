"""Dyania AVR durability clinical-research dashboard.

Run from the repository root with:
    streamlit run app.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from ui.charts import durability_curve, time_ratio_forest, validation_comparison
from ui.data import ClinicalDataRepository, PatientRecord
from ui.predictor import (
    DurabilityPrediction,
    PredictionUnavailable,
    load_posterior,
    predict_durability,
)
from ui.reporting import build_research_summary
from ui.styles import APP_CSS, badge, evidence_item, key_value_grid, metric_card, safe


ROOT = Path(__file__).resolve().parent
POSTERIOR_PATH = ROOT / "reports" / "head_a_posterior.nc"


st.set_page_config(
    page_title="AVR Durability Assessment | Dyania",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(APP_CSS, unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def get_repository(root: str) -> ClinicalDataRepository:
    return ClinicalDataRepository(root)


@st.cache_resource(show_spinner="Loading Bayesian posterior…")
def get_posterior(path: str):
    return load_posterior(path)


def fmt_number(value: float | None, *, digits: int = 1, suffix: str = "") -> str:
    if value is None:
        return "Unavailable"
    return f"{value:.{digits}f}{suffix}"


def fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def risk_interval(prediction: DurabilityPrediction, year: int) -> tuple[str, str]:
    summary = prediction.risk_by_year[year]
    return fmt_pct(summary.median), f"89% CrI {fmt_pct(summary.low)}–{fmt_pct(summary.high)}"


def confidence_tone(confidence: str) -> str:
    return {
        "definite": "teal",
        "probable": "amber",
        "possible": "amber",
        "excluded": "coral",
        "censored": "neutral",
    }.get(confidence.lower(), "neutral")


def state_tone(patient: PatientRecord) -> str:
    if patient.bvf_stage >= 2 or patient.hvd_stage >= 3:
        return "danger"
    if patient.hvd_stage >= 1:
        return "warning"
    return "accent"


def stage_detail(patient: PatientRecord) -> str:
    return f"{patient.phenotype_label} · {patient.confidence_tier.title()} evidence"


def patient_inputs_html(patient: PatientRecord) -> str:
    size = f"{patient.valve_size_mm:g} mm" if patient.valve_size_mm is not None else "Unavailable"
    ppm = (
        "Triggered (size <=21 mm)"
        if patient.size_known and patient.ppm_proxy_flag
        else "Not triggered"
        if patient.size_known
        else "Unavailable; model proxy defaults off"
    )
    return key_value_grid(
        [
            ("Index approach", patient.approach or "Unavailable"),
            ("Valve model", patient.valve_model or "Unavailable"),
            ("Valve family", (patient.valve_family or "Approach-level fallback").replace("_", " ")),
            ("Labelled size", size),
            ("PPM proxy", ppm),
            ("Index year", str(patient.index_implant_year or "Unavailable")),
        ]
    )


try:
    repo = get_repository(str(ROOT))
except Exception as exc:
    st.error(
        "The dashboard could not load the committed pipeline artifacts. "
        "Run it from the repository root after generating labels.csv and the Head A inputs."
    )
    with st.expander("Technical detail"):
        st.code(str(exc))
    st.stop()


patient_ids = repo.available_patient_ids(model_eligible_only=True)
if not patient_ids:
    st.error("No Head A-eligible de-identified patient profiles were found.")
    st.stop()

featured_patient = "Patient_001" if "Patient_001" in patient_ids else patient_ids[0]
if "patient_selector" not in st.session_state:
    st.session_state.patient_selector = featured_patient


with st.sidebar:
    st.markdown(
        """
        <div class="brand-lockup">
          <div class="brand-name">DYANIA HEALTH</div>
          <div class="brand-product">AVR Durability Assessment</div>
          <div class="brand-sub">Traceable current-state phenotyping and Bayesian durability forecasting.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("DE-IDENTIFIED RESEARCH COHORT")
    if st.button("Load featured case", help="Open the curated demo profile from the pipeline output."):
        st.session_state.patient_selector = featured_patient

    selected_id = st.selectbox(
        "Patient profile",
        patient_ids,
        key="patient_selector",
        format_func=lambda pid: repo.patient(pid).display_label,
    )
    patient = repo.patient(selected_id)
    audit = repo.audit_summary(selected_id)

    st.markdown("---")
    st.caption("SELECTED PROFILE")
    st.markdown(f"**{safe(patient.profile_key)}**", unsafe_allow_html=True)
    st.caption(
        f"{patient.approach or 'Approach unavailable'} · "
        f"{patient.valve_model or 'Valve model unavailable'} · "
        f"{fmt_number(patient.valve_size_mm, digits=0, suffix=' mm')}"
    )
    st.markdown(
        badge(patient.confidence_tier.title(), confidence_tone(patient.confidence_tier)),
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.caption("DATA SCOPE")
    st.caption(
        f"{audit.total_notes} notes · {fmt_number(patient.years_followup, digits=1, suffix=' y')} observed follow-up"
    )
    st.caption("No patient name, age, or direct identifier is displayed.")


prediction: DurabilityPrediction | None = None
prediction_error: str | None = None
try:
    posterior = get_posterior(str(POSTERIOR_PATH))
    prediction = predict_durability(
        posterior,
        approach=patient.approach or "",
        valve_family=patient.valve_family,
        family_known=patient.valve_family_known,
        ppm_proxy_flag=patient.ppm_proxy_flag,
        size_known=patient.size_known,
    )
except PredictionUnavailable as exc:
    prediction_error = str(exc)
except Exception as exc:  # defensive UI boundary
    prediction_error = f"Unexpected posterior prediction error: {exc}"


st.markdown(
    """
    <div class="page-header">
      <div class="eyebrow">Clinical research decision support</div>
      <div class="page-title">AVR durability assessment</div>
      <div class="page-subtitle">A two-head view of current bioprosthetic valve status and future durability, with patient-level provenance and posterior uncertainty.</div>
      <div class="header-rule"></div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="status-strip"><span class="status-dot"></span>'
    '<strong>Research prototype</strong><span class="status-separator">·</span>'
    '<span>Head B: deterministic VARC-3/Capodanno phenotyping</span>'
    '<span class="status-separator">·</span>'
    '<span>Head A: hierarchical Bayesian Weibull AFT</span>'
    '<span class="status-separator">·</span><span>Not for clinical use</span></div>',
    unsafe_allow_html=True,
)


summary_markdown = build_research_summary(patient, prediction, audit)
download_col, meta_col = st.columns([1, 4], vertical_alignment="center")
with download_col:
    st.download_button(
        "Download research summary",
        data=summary_markdown,
        file_name=f"{patient.profile_key.lower()}_avr_research_summary.md",
        mime="text/markdown",
        width="stretch",
    )
with meta_col:
    st.caption(
        f"Profile {patient.profile_key} · data through {patient.last_note_year or 'unknown'} · "
        "posterior and extraction artifacts loaded read-only"
    )


overview_tab, explanation_tab, provenance_tab, evidence_tab = st.tabs(
    ["Overview", "Why this prediction?", "Data & provenance", "Model & evidence"]
)


with overview_tab:
    st.markdown("### Clinical snapshot")
    metric_columns = st.columns(4)
    if prediction is not None:
        risk_value, risk_detail = risk_interval(prediction, 5)
        median = prediction.median_event_free_years
        median_value = f"{median.median:.1f} years"
        median_detail = f"89% CrI {median.low:.1f}–{median.high:.1f} years"
    else:
        risk_value, risk_detail = "Unavailable", "Posterior artifact could not be evaluated"
        median_value, median_detail = "Unavailable", "See model status below"

    cards = [
        ("5-year modeled endpoint probability", risk_value, risk_detail, "accent"),
        ("Posterior median event-free time", median_value, median_detail, "accent"),
        ("Current valve state", patient.endpoint_label, stage_detail(patient), state_tone(patient)),
        (
            "Evidence confidence",
            patient.confidence_tier.title(),
            f"Head B · {audit.post_implant_notes} post-implant notes assessed",
            "warning" if patient.confidence_tier in {"probable", "possible"} else "neutral",
        ),
    ]
    for column, card in zip(metric_columns, cards):
        with column:
            st.markdown(metric_card(*card), unsafe_allow_html=True)

    st.markdown("")
    chart_col, context_col = st.columns([2.15, 1], gap="large")
    with chart_col:
        st.markdown("#### Posterior durability trajectory")
        if prediction is not None:
            st.plotly_chart(
                durability_curve(prediction, observed_followup=patient.years_followup),
                width="stretch",
                config={"displayModeBar": False, "responsive": True},
            )
            st.caption(
                "The dashed endpoint curve is 1 − S(t) from Head A. It is not a competing-risk CIF; "
                "all-cause mortality is not modeled in the current fitted head."
            )
        else:
            st.warning("Head A prediction is unavailable for this run.")
            with st.expander("Technical detail"):
                st.code(prediction_error or "Unknown error")

    with context_col:
        st.markdown("#### Current assessment")
        st.markdown(
            '<div class="panel">'
            f'<div class="panel-title">{safe(patient.endpoint_label)}</div>'
            f'<div class="panel-copy">{safe(patient.rationale)}</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown("#### Model inputs")
        st.markdown(
            f'<div class="panel">{patient_inputs_html(patient)}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="callout info"><strong>Interpretation boundary.</strong> '
            'This prototype communicates uncertainty and evidence provenance. It does not assign a surveillance interval or recommend treatment.</div>',
            unsafe_allow_html=True,
        )

    if prediction is not None:
        st.markdown("#### Time-horizon summary")
        rows = []
        for year, summary in prediction.risk_by_year.items():
            rows.append(
                {
                    "Horizon": f"{year} years",
                    "Modeled endpoint probability": fmt_pct(summary.median),
                    "89% credible interval": f"{fmt_pct(summary.low)} – {fmt_pct(summary.high)}",
                    "Event-free probability": fmt_pct(1.0 - summary.median),
                }
            )
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


with explanation_tab:
    st.markdown("### Patient-specific explanation")
    st.caption(
        "The primary model is explained directly on its accelerated-failure-time scale. "
        "A time ratio above 1 corresponds to longer modeled durability; intervals crossing 1 indicate substantial uncertainty."
    )

    if prediction is None:
        st.warning("The AFT decomposition requires the fitted posterior artifact.")
    else:
        figure_col, input_col = st.columns([1.65, 1], gap="large")
        with figure_col:
            st.plotly_chart(
                time_ratio_forest(prediction),
                width="stretch",
                config={"displayModeBar": False, "responsive": True},
            )
            total = prediction.total_time_ratio
            st.markdown(
                '<div class="callout info">'
                f'<strong>Combined patient time ratio: {total.median:.2f}x</strong> '
                f'(89% CrI {total.low:.2f}–{total.high:.2f}x), relative to the SAVR approach reference '
                'with no family offset and the PPM proxy off.</div>',
                unsafe_allow_html=True,
            )
        with input_col:
            st.markdown("#### What the model used")
            factor_rows = []
            for factor in prediction.factors:
                factor_rows.append(
                    {
                        "Factor": factor.label,
                        "Time ratio": f"{factor.ratio.median:.2f}x",
                        "89% CrI": f"{factor.ratio.low:.2f}–{factor.ratio.high:.2f}x",
                        "Status": "Applied" if factor.applied else "Reference / unavailable",
                    }
                )
            st.dataframe(pd.DataFrame(factor_rows), hide_index=True, width="stretch")
            st.markdown(
                '<div class="callout"><strong>Associations, not causes.</strong> '
                'The posterior is informed by a small cohort and literature priors. Direction and magnitude must not be interpreted as treatment effects.</div>',
                unsafe_allow_html=True,
            )

    st.markdown("#### Why Head B assigned the current state")
    st.markdown(
        f'<div class="panel"><div class="panel-copy">{safe(patient.rationale)}</div></div>',
        unsafe_allow_html=True,
    )
    if patient.evidence:
        for label, text in patient.evidence:
            st.markdown(evidence_item(label, text), unsafe_allow_html=True)
    else:
        st.info("No positive source-evidence span was emitted; this profile is supported by right-censoring or normal follow-up evidence.")


with provenance_tab:
    st.markdown("### End-to-end provenance")
    st.caption("Every displayed result is linked to a committed pipeline artifact; the UI does not rerun or alter the models.")
    pipeline_steps = [
        ("01", "De-identified notes", "Operative reports and longitudinal progress notes"),
        ("02", "Deterministic extraction", "Sectioning, negation, temporal attribution, valve dictionary"),
        ("03", "Head B staging", "VARC-3 primary rules with documented Capodanno fallback"),
        ("04", "Landmark features", "Approach, valve family and labelled-size PPM proxy"),
        ("05", "Head A posterior", "Interval-censored hierarchical Bayesian Weibull AFT"),
    ]
    pipeline_html = "".join(
        '<div class="pipeline-step">'
        f'<div class="pipeline-index">{safe(index)}</div>'
        f'<div class="pipeline-name">{safe(name)}</div>'
        f'<div class="pipeline-copy">{safe(copy)}</div>'
        '</div>'
        for index, name, copy in pipeline_steps
    )
    st.markdown(f'<div class="pipeline">{pipeline_html}</div>', unsafe_allow_html=True)

    st.markdown("#### Patient-level extraction audit")
    audit_columns = st.columns(4)
    audit_cards = [
        ("Notes assessed", str(audit.total_notes), f"{audit.post_implant_notes} post-implant", "neutral"),
        ("Hemodynamic hits", str(audit.gradient_hits), "Numeric gradient extractions", "accent"),
        ("SVD / redo signals", str(audit.svd_hits + audit.redo_hits + audit.viv_hits), "Candidate evidence spans", "warning"),
        ("Exclusion signals", str(audit.exclusion_hits), "Endocarditis, thrombosis or PVL checks", "neutral"),
    ]
    for column, card in zip(audit_columns, audit_cards):
        with column:
            st.markdown(metric_card(*card), unsafe_allow_html=True)

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("#### Feature lineage")
        st.markdown(
            '<div class="panel">'
            + key_value_grid(
                [
                    ("Index source", patient.index_implant_source or "Unavailable"),
                    ("Implant year", str(patient.index_implant_year or "Unavailable")),
                    ("Approach", patient.approach or "Unavailable"),
                    ("Valve model", patient.valve_model or "Unavailable"),
                    ("Valve family mapping", (patient.valve_family or "Not mapped").replace("_", " ")),
                    ("PPM proxy definition", "Labelled valve size <=21 mm"),
                ]
            )
            + '</div>',
            unsafe_allow_html=True,
        )
    with right:
        st.markdown("#### Evidence emitted by Head B")
        if patient.evidence:
            for label, text in patient.evidence:
                st.markdown(evidence_item(label, text), unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="panel"><div class="panel-copy">No positive evidence span was emitted for this profile. '
                'The rationale records the right-censoring or absence of post-implant deterioration evidence.</div></div>',
                unsafe_allow_html=True,
            )

    with st.expander("Data-handling notes"):
        st.markdown(
            "- Patient keys are de-identified profile identifiers.\n"
            "- Age is masked throughout the provided notes and is not a model feature.\n"
            "- Evidence snippets originate from the deterministic extraction output; the dashboard does not send text to an LLM.\n"
            "- Unknown valve family falls back to the approach-level posterior. Unknown size leaves the documented PPM proxy off."
        )


with evidence_tab:
    validation = repo.validation_summary()
    cohort = repo.cohort_summary()
    st.markdown("### Model and validation evidence")
    st.caption("Validation is presented with the same uncertainty and limitations recorded in the repository.")

    validation_columns = st.columns(4)
    validation_cards = [
        (
            "Apparent C-index",
            fmt_number(validation.apparent_c_index, digits=3),
            "Full-MCMC posterior, in-sample",
            "accent",
        ),
        (
            "Optimism-corrected C-index",
            fmt_number(validation.corrected_c_index, digits=3),
            (
                f"95% CI {validation.ci_low:.3f}–{validation.ci_high:.3f}"
                if validation.ci_low is not None and validation.ci_high is not None
                else "Interval unavailable"
            ),
            "warning",
        ),
        ("Model-fit cohort", str(cohort["head_a_model_fit"]), f'{cohort["events"]} endpoint events', "neutral"),
        ("Head B cohort", str(cohort["head_b_patients"]), "Full de-identified cohort", "neutral"),
    ]
    for column, card in zip(validation_columns, validation_cards):
        with column:
            st.markdown(metric_card(*card), unsafe_allow_html=True)

    chart_col, model_col = st.columns([1.45, 1], gap="large")
    with chart_col:
        st.markdown("#### Discrimination context")
        st.plotly_chart(
            validation_comparison(
                bayesian=validation.apparent_c_index,
                corrected=validation.corrected_c_index,
            ),
            width="stretch",
            config={"displayModeBar": False, "responsive": True},
        )
        st.caption(
            "Comparator values are read from the committed bootstrap reports. Wide uncertainty around the primary estimate is material, not cosmetic."
        )
    with model_col:
        st.markdown("#### Primary Head A")
        st.markdown(
            '<div class="panel">'
            '<div class="panel-title">Hierarchical Bayesian Weibull AFT</div>'
            '<div class="panel-copy">Interval-censored likelihood; literature-informed approach priors; '
            'partial pooling of mapped valve families; one labelled-size PPM proxy. '
            'A shared Weibull shape keeps the model identifiable at the observed event count.</div>'
            + key_value_grid(
                [
                    ("Covariates", "Approach, valve family, PPM proxy"),
                    ("Excluded", "Age, CKD, diabetes, smoking, sparse baseline echo"),
                    ("Explanation", "Posterior AFT time ratios"),
                    ("Endpoint timing", "Year-level interval censoring (±1 year)"),
                ]
            )
            + '</div>',
            unsafe_allow_html=True,
        )

    st.markdown("#### Known limitations")
    st.markdown(
        '<div class="callout critical"><strong>Proof of concept, not clinical validation.</strong> '
        'The cohort is small, only a limited number of events inform Head A, the confidence interval is wide, '
        'and full-cohort blind physician adjudication remains pending.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "- Head A does **not** model competing all-cause mortality, so the displayed event curve is not a CIF.\n"
        "- TAVR and ViV-TAVR estimates are strongly prior-influenced because observed endpoint events occurred in SAVR-index valves.\n"
        "- The PPM input is a labelled-size proxy (`<=21 mm`), not measured indexed EOA.\n"
        "- Missing family or size information is surfaced in the UI and handled exactly as in the fitted pipeline.\n"
        "- Outputs describe posterior associations and must not be interpreted causally."
    )

    with st.expander("Why SHAP is not the primary explanation"):
        st.markdown(
            "SHAP in this repository belongs to the **XGBoost AFT comparator**, whose optimism-corrected "
            "C-index is approximately 0.508. The primary model is a Weibull AFT model, so the dashboard "
            "uses its own posterior time-ratio components. This is faithful to the deployed model and avoids "
            "presenting comparator diagnostics as validated patient-level importance."
        )
    with st.expander("Bootstrap method note"):
        st.write(validation.method_note or "No method note found in the committed report.")


st.markdown(
    '<div class="footer">DYANIA HEALTH · AVR durability research prototype · '
    'Current-state phenotyping aligned to repository VARC-3/Capodanno rules · '
    'Durability forecast from the committed hierarchical Bayesian Weibull AFT posterior · '
    'Not for clinical use.</div>',
    unsafe_allow_html=True,
)
