# Presentation Slide Content

> Source content for `slides.pdf` (5–10 slides, export from this outline). Each slide below is the actual
> bullet content, not a generic prompt — pull numbers directly from `review/error_catalogue.md`,
> `reports/head_a_validation_report.md`, and `config/priors.yaml`.

---

## Slide 1 — Title

- [Team name] — Dyania Health Hackathon 2026
- Notes-Derived SVD Staging and Bayesian Durability Forecasting for Bioprosthetic Aortic Valves
- 2026-09-17

---

## Slide 2 — The Clinical Problem

- Structural valve deterioration (SVD) is currently caught by fixed-interval echo surveillance, not individualized
  risk — every patient gets the same schedule regardless of their actual trajectory.
- In our own 117-patient cohort: 11 confirmed reinterventions, all SAVR-index, spanning routine ViV TAVR to one
  documented emergent case (cardiogenic shock at presentation) — a direct illustration of what late identification
  costs.
- Published durability ranges from ~92% freedom-from-SVD at 5 years (Mitroflow) to ~96% at 10 years (Freestyle) —
  device choice alone spans a wide durability range surveillance schedules don't currently account for.

## Slide 3 — Current Workflow Failure

- Fixed-interval echo surveillance treats a Freestyle and a Mitroflow patient identically, despite materially
  different published degradation curves.
- Reintervention indication is often only captured retrospectively in free text — no structured field in this
  corpus flags "SVD" directly; extracting it required a purpose-built NLP pipeline (below).
- Bottleneck: valve model/size is only recoverable from free text for about half our cohort (58/117), and labs/
  medications exist for only 17/117 patients in this extract — real-world data completeness is itself part of the
  problem.

## Slide 4 — Our Hypothesis

- If durability risk were forecast from routinely collected notes at implant time, surveillance could shift from
  fixed-interval to risk-adaptive — closer follow-up for short-predicted-durability patients, standard intervals for
  the rest.
- At n=99/11 events, we can't yet validate a deployable risk score — but we can validate the *method*: an
  auditable severity-staging engine plus a literature-anchored Bayesian durability model that degrades honestly
  (wide uncertainty) rather than overclaiming at small n.

---

## Slide 5 — Study Overview

- Population: bioprosthetic AVR recipients (SAVR/TAVR/ViV) with a recoverable implant year; 117 patients (Head B),
  99 with a usable time origin (Head A).
- Primary endpoint: BVF Stage ≥2 (reintervention), VARC-3-staged. Secondary: moderate-or-greater HVD (18/117
  patients, vs. 11 for the primary — matches the Master Prompt's own expected ~15-19 vs. 8 ratio).
- Ground truth: 5-tier hierarchy (definite/probable/possible/excluded/censored), validated against a
  physician-reviewed seed set before any modeling — reintervention-detector **F1 = 1.000** after fixing 4
  root-caused pipeline bugs (from 0.933 pre-fix).

## Slide 6 — Data Sources

- Prototype: 215 de-identified notes / 117 patients (only source covering the full cohort); labs/medications for
  17/117 only, used descriptively — **zero of our 8 confirmed SVD reinterventions fall in that 17-patient subset**,
  so we do not train any predictive feature on labs/meds (would be fabricating signal from zero events).
- Real deployment: structured echo reports and implant device (UDI) fields would close the ~50% valve-model/size
  gap this free-text extraction currently has.
- Age is masked with **zero surviving numeric values anywhere in the corpus** — flagged as a hard limitation, not
  worked around.

## Slide 7 — Validation Plan

- No train/test split at 11 events — Bayesian partial pooling + literature-informed priors instead of a
  classical split; leakage controls (feature-timestamp check, temporal ordering check, label-permutation test)
  all pass.
- Metrics: posterior diagnostics (R-hat = 1.00, ESS in the thousands, clean convergence) + in-sample C-index
  against 3 comparators.
- Comparator baseline: literature-prior-only, valve-family-only frequentist Weibull (undefined for 2/3 families —
  zero events), penalized Cox, XGBoost AFT.

---

## Slide 8 — Model Architecture

- Two heads: deterministic VARC-3 rule engine (severity, fully auditable — every label traces to a source
  sentence) + hierarchical Bayesian Weibull AFT with an interval-censored likelihood (durability).
- Interval censoring is load-bearing, not cosmetic: every date in this corpus is year-only, so every event time is
  only known to ±1 year — implemented directly in the model's likelihood, not approximated away.
- Priors fit from 3 published sources, re-verified against the actual source PDFs (not taken on faith); Trifecta
  has no literature durability point in any of the 3 papers (confirmed by full-text search) and is deliberately
  given no fabricated prior.

## Slide 9 — Results

- Bootstrap-corrected C-index (Harrell optimism correction, 95% CI — not a naive point estimate, same full-MCMC
  fitting procedure for every model): primary Bayesian model **0.591, CI [0.437, 0.725]** vs. penalized Cox 0.546
  CI [0.481, 0.585], XGBoost AFT 0.508 CI [0.446, 0.537], literature-only 0.481 (below chance, not bootstrapped).
- Honest read, shown explicitly, not hidden: with 11 events these intervals are wide — the primary model's own
  lower bound (0.437) is below chance. Its central estimate is the best of the five models, evaluated the same
  fitting method throughout (B=100 for the primary model vs. B=500 for the others — a compute-time tradeoff, not a
  method difference), but "beats chance with confidence" cannot be claimed at this n. The literature-only model
  scoring *below* chance on our own cohort is itself the key finding: it's why a Bayesian update, not literature
  transfer alone, is the right framing.
- SHAP/forest-plot outputs available (`reports/head_a_forest_plot.png`, `head_a_shap_summary.png`), reported with
  an explicit near-chance-comparator caveat.

---

## Slide 10 — Impact and Next Steps

- What this enables today: a validated, auditable NLP severity pipeline (F1=1.000 on seed set) that a physician
  can review and correct in one pass, ready to scale to a larger extract without re-architecting.
- Full validation in a real health system requires: complete 117-patient physician adjudication (in progress,
  `review/adjudication_form.xlsx`) and real Guyot KM-curve digitization (algorithm implemented + self-tested, but
  none of our 3 source papers contain an actual curve to digitize — need the primary studies, see
  `data/external/km_digitized/DIGITIZATION_CHECKLIST.md`). Bootstrap (Level 3), construct-validity (Level 2), and
  simulation (Level 5) validation are all done — see `reports/head_a_validation_report.md` — sensitivity analyses
  are what's still outstanding.
- 3-month next step: multi-site extract to push past 11 events, structured echo integration to close the
  valve-model/size gap, and a formal fairness analysis once demographic fields are available.
- Deployment readiness: method-validated, not clinically validated — the honest next milestone is n in the low
  hundreds of confirmed events, not a production rollout.
