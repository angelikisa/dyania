"""Data access and patient-view assembly for the dashboard."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


EVIDENCE_FIELDS = (
    ("Reintervention evidence", "redo_evidence"),
    ("Explicit SVD evidence", "svd_explicit_evidence"),
    ("Regurgitation evidence", "ar_evidence"),
    ("Morphology evidence", "morphology_evidence"),
    ("Gradient-trend evidence", "gradient_trend_evidence"),
    ("Exclusion evidence", "exclusion_reason"),
)


def _optional_text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or pd.isna(value):
        return False
    return str(value).strip().lower() in {"true", "1", "yes"}


@dataclass(frozen=True)
class PatientRecord:
    profile_key: str
    index_implant_year: int | None
    index_implant_source: str | None
    approach: str | None
    valve_model: str | None
    valve_family: str | None
    valve_family_known: bool
    valve_size_mm: float | None
    size_known: bool
    ppm_proxy_flag: bool
    last_note_year: int | None
    years_followup: float | None
    hvd_stage: int
    bvf_stage: int
    phenotype: str | None
    confidence_tier: str
    rationale: str
    event: bool
    t_lower: float | None
    t_upper: float | None
    baseline_mg: float | None
    worst_followup_mg: float | None
    evidence: tuple[tuple[str, str], ...]

    @property
    def display_label(self) -> str:
        valve = self.valve_model or "model unavailable"
        size = f"{self.valve_size_mm:g} mm" if self.valve_size_mm is not None else "size unavailable"
        return f"{self.profile_key} | {self.approach or 'approach unavailable'} | {valve}, {size}"

    @property
    def endpoint_label(self) -> str:
        if self.bvf_stage == 2:
            return "BVF Stage 2"
        if self.bvf_stage == 3:
            return "BVF Stage 3"
        return f"HVD Stage {self.hvd_stage}"

    @property
    def phenotype_label(self) -> str:
        return {
            "S": "Stenosis-dominant",
            "R": "Regurgitation-dominant",
            "RS": "Mixed stenosis/regurgitation",
        }.get(self.phenotype or "", "No phenotype assigned")


@dataclass(frozen=True)
class AuditSummary:
    total_notes: int
    post_implant_notes: int
    redo_hits: int
    viv_hits: int
    svd_hits: int
    gradient_hits: int
    morphology_hits: int
    exclusion_hits: int
    note_types: tuple[str, ...]


@dataclass(frozen=True)
class ValidationSummary:
    apparent_c_index: float | None
    corrected_c_index: float | None
    ci_low: float | None
    ci_high: float | None
    bootstrap_resamples: int | None
    method_note: str | None


class ClinicalDataRepository:
    """Read-only view over Head A/Head B artifacts committed to the repo."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.labels = pd.read_csv(self.root / "labels.csv")
        self.features = pd.read_csv(self.root / "data_processed_patient_features.csv")
        self.head_a_labels = pd.read_csv(self.root / "data_processed_patient_labels.csv")
        audit_path = self.root / "notes_audit.csv"
        self.audit = pd.read_csv(audit_path) if audit_path.exists() else pd.DataFrame()

        merged = self.features.merge(
            self.head_a_labels,
            on="profile_key",
            how="left",
            suffixes=("", "_head_a"),
            validate="one_to_one",
        ).merge(
            self.labels,
            on="profile_key",
            how="left",
            suffixes=("_head_a", ""),
            validate="one_to_one",
        )
        self.patient_table = merged.sort_values("profile_key").reset_index(drop=True)

    def available_patient_ids(self, *, model_eligible_only: bool = True) -> list[str]:
        table = self.patient_table
        if model_eligible_only:
            table = table[table["index_approach"].notna()]
        return table["profile_key"].astype(str).tolist()

    def patient(self, profile_key: str) -> PatientRecord:
        match = self.patient_table[self.patient_table["profile_key"] == profile_key]
        if match.empty:
            raise KeyError(f"Unknown patient profile: {profile_key}")
        row = match.iloc[0]

        evidence = tuple(
            (label, text)
            for label, column in EVIDENCE_FIELDS
            if (text := _optional_text(row.get(column))) is not None
        )
        index_year = _optional_float(row.get("index_implant_year"))
        last_year = _optional_float(row.get("last_note_year"))
        return PatientRecord(
            profile_key=str(row["profile_key"]),
            index_implant_year=int(index_year) if index_year is not None else None,
            index_implant_source=_optional_text(row.get("index_implant_source")),
            approach=_optional_text(row.get("index_approach")),
            valve_model=_optional_text(row.get("index_valve_model")),
            valve_family=_optional_text(row.get("valve_family")),
            valve_family_known=_bool_value(row.get("valve_family_known")),
            valve_size_mm=_optional_float(row.get("index_valve_size_mm")),
            size_known=_bool_value(row.get("size_known")),
            ppm_proxy_flag=_bool_value(row.get("ppm_proxy_flag")),
            last_note_year=int(last_year) if last_year is not None else None,
            years_followup=_optional_float(row.get("years_followup")),
            hvd_stage=int(row.get("hvd_stage", 0) or 0),
            bvf_stage=int(row.get("bvf_stage", 0) or 0),
            phenotype=_optional_text(row.get("phenotype")),
            confidence_tier=_optional_text(row.get("confidence_tier")) or "unknown",
            rationale=_optional_text(row.get("rationale")) or "No rationale available.",
            event=_bool_value(row.get("event")),
            t_lower=_optional_float(row.get("t_lower")),
            t_upper=_optional_float(row.get("t_upper")),
            baseline_mg=_optional_float(row.get("baseline_mg")),
            worst_followup_mg=_optional_float(row.get("worst_followup_mg")),
            evidence=evidence,
        )

    def audit_summary(self, profile_key: str) -> AuditSummary:
        if self.audit.empty:
            return AuditSummary(0, 0, 0, 0, 0, 0, 0, 0, ())
        rows = self.audit[self.audit["profile_key"] == profile_key]
        if rows.empty:
            return AuditSummary(0, 0, 0, 0, 0, 0, 0, 0, ())

        def total(column: str) -> int:
            if column not in rows:
                return 0
            return int(pd.to_numeric(rows[column], errors="coerce").fillna(0).sum())

        post = rows.get("is_post_implant", pd.Series(False, index=rows.index)).map(_bool_value)
        note_types = tuple(sorted(rows.get("note_type", pd.Series(dtype=str)).dropna().astype(str).unique()))
        return AuditSummary(
            total_notes=int(len(rows)),
            post_implant_notes=int(post.sum()),
            redo_hits=total("n_redo"),
            viv_hits=total("n_viv"),
            svd_hits=total("n_svd_explicit"),
            gradient_hits=total("n_gradients"),
            morphology_hits=total("n_morphology"),
            exclusion_hits=total("n_exclusion"),
            note_types=note_types,
        )

    def cohort_summary(self) -> dict[str, int]:
        eligible = self.patient_table[self.patient_table["index_approach"].notna()]
        return {
            "head_b_patients": int(self.labels["profile_key"].nunique()),
            "head_a_time_eligible": int(self.features["profile_key"].nunique()),
            "head_a_model_fit": int(eligible["profile_key"].nunique()),
            "events": int(pd.to_numeric(eligible["event"], errors="coerce").fillna(0).sum()),
        }

    def validation_summary(self) -> ValidationSummary:
        path = self.root / "reports" / "head_a_bootstrap_bayesian.yaml"
        if not path.exists():
            return ValidationSummary(None, None, None, None, None, None)
        with path.open(encoding="utf-8") as stream:
            data = yaml.safe_load(stream) or {}
        return ValidationSummary(
            apparent_c_index=data.get("apparent_c_index"),
            corrected_c_index=data.get("bootstrap_corrected_c_index"),
            ci_low=data.get("ci_95_low"),
            ci_high=data.get("ci_95_high"),
            bootstrap_resamples=data.get("n_resamples_used"),
            method_note=data.get("method_note"),
        )
