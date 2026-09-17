"""
Harrell bootstrap optimism correction for the PRIMARY model (hierarchical
Bayesian Weibull AFT), using MAP point estimates per resample for
computational tractability -- see bootstrap_validation.py's module
docstring for the full justification and the documented B=200 (not 500)
resample count.

Run with: PYTENSOR_FLAGS="cxx=" PYTHONIOENCODING=utf-8 python src/validation/bootstrap_bayesian.py
Expected wall-clock: ~200 x ~9.5s =~ 32 minutes on this environment.
"""
from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pymc as pm
import yaml
from lifelines.utils import concordance_index

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "models" / "durability"))
from weibull_aft_bayes import build_model  # noqa: E402

warnings.filterwarnings("ignore")
SEED = 20260917
B = 200


def load_cohort():
    features = pd.read_csv("data_processed_patient_features.csv")
    labels = pd.read_csv("data_processed_patient_labels.csv")
    d = features.merge(labels, on="profile_key")
    d = d[d["index_approach"].notna()].reset_index(drop=True)
    d["t_approx"] = np.where(d["event"] == 1, (d["t_lower"] + d["t_upper"]) / 2, d["t_lower"])
    d["t_approx"] = d["t_approx"].clip(lower=0.5)
    return d


def resample(features: pd.DataFrame, labels: pd.DataFrame, rng: np.random.Generator):
    idx = rng.integers(0, len(features), len(features))
    bf = features.iloc[idx].reset_index(drop=True)
    bl = labels.iloc[idx].reset_index(drop=True)
    new_keys = [f"boot_{i}" for i in range(len(bf))]
    bf["profile_key"] = new_keys
    bl["profile_key"] = new_keys
    return bf, bl


def median_survival_from_map(map_est: dict, d_eval: pd.DataFrame, features_eval: pd.DataFrame,
                              approaches: list[str], families: list[str], priors: dict) -> np.ndarray:
    """Compute median survival for arbitrary evaluation rows from a fitted
    MAP point estimate (mu_approach, family_offset, beta_ppm, shape_k),
    without re-invoking PyMC -- pure numpy, so it can score the ORIGINAL
    cohort using a model that was fit on a bootstrap sample."""
    approach_idx = {a: i for i, a in enumerate(approaches)}
    family_idx = {f: i for i, f in enumerate(families)}
    k = float(map_est["shape_k"])
    mu_approach = np.asarray(map_est["mu_approach"])
    family_offset = np.asarray(map_est["family_offset"])
    beta_ppm = float(map_est["beta_ppm"])

    log_scale = np.array([mu_approach[approach_idx.get(a, 0)] for a in d_eval["index_approach"]])
    fam_term = np.array([
        family_offset[family_idx[f]] if (isinstance(f, str) and f in family_idx) else 0.0
        for f in d_eval["valve_family"]
    ])
    ppm = d_eval["ppm_proxy_flag"].fillna(False).to_numpy(dtype=float)
    log_scale = log_scale + fam_term + beta_ppm * ppm
    scale = np.exp(log_scale)
    return scale * (np.log(2)) ** (1.0 / k)


def run():
    d_full = load_cohort()
    features_full = pd.read_csv("data_processed_patient_features.csv")
    features_full = features_full[features_full["profile_key"].isin(d_full["profile_key"])].reset_index(drop=True)
    labels_full = pd.read_csv("data_processed_patient_labels.csv")
    labels_full = labels_full[labels_full["profile_key"].isin(d_full["profile_key"])].reset_index(drop=True)
    with open("config/priors.yaml", encoding="utf-8") as f:
        priors = yaml.safe_load(f)

    # --- apparent: use the ALREADY-FITTED full-MCMC posterior (the actually reported model) ---
    import arviz as az
    idata = az.from_netcdf("reports/head_a_posterior.nc")
    med_surv_app = idata.posterior["median_survival_years"].mean(dim=["chain", "draw"]).values
    c_app = concordance_index(d_full["t_approx"], med_surv_app, d_full["event"])
    print(f"Apparent C-index (full MCMC posterior, reported model): {c_app:.4f}")

    model_full, meta_full = build_model(features_full, labels_full, priors)
    approaches, families = meta_full["approaches"], meta_full["families"]

    rng = np.random.default_rng(SEED)
    optimisms = []
    t_start = time.time()
    for b in range(B):
        t0 = time.time()
        bf, bl = resample(features_full, labels_full, rng)
        try:
            model_b, meta_b = build_model(bf, bl, priors)
            with model_b:
                map_b = pm.find_MAP(progressbar=False)
        except Exception as e:
            print(f"  resample {b}: FAILED to fit ({e}); skipping")
            continue

        d_boot = bf.merge(bl, on="profile_key")
        d_boot = d_boot[d_boot["index_approach"].notna()].reset_index(drop=True)
        d_boot["t_approx"] = np.clip(
            np.where(d_boot["event"] == 1, (d_boot["t_lower"] + d_boot["t_upper"]) / 2, d_boot["t_lower"]), 0.5, None)

        pred_boot = median_survival_from_map(map_b, d_boot, bf, meta_b["approaches"], meta_b["families"], priors)
        pred_orig = median_survival_from_map(map_b, d_full, features_full, meta_b["approaches"], meta_b["families"], priors)

        c_boot = concordance_index(d_boot["t_approx"], pred_boot, d_boot["event"])
        c_orig = concordance_index(d_full["t_approx"], pred_orig, d_full["event"])
        optimisms.append(c_boot - c_orig)

        if (b + 1) % 20 == 0:
            elapsed = time.time() - t_start
            print(f"  {b+1}/{B} done, {elapsed:.0f}s elapsed, ~{elapsed/(b+1)*(B-b-1):.0f}s remaining, "
                  f"running mean optimism={np.mean(optimisms):.4f}", flush=True)

    corrected = c_app - float(np.mean(optimisms))
    dist = c_app - np.array(optimisms)
    lo, hi = np.percentile(dist, [2.5, 97.5])

    result = dict(model="primary_hierarchical_bayesian_weibull_aft", apparent_c_index=float(c_app),
                  bootstrap_corrected_c_index=float(corrected), ci_95_low=float(lo), ci_95_high=float(hi),
                  n_resamples_used=len(optimisms), B=B,
                  method_note="Bootstrap resamples fit via MAP (not full MCMC) for tractability; "
                               "apparent C-index uses the full-MCMC posterior. See module docstring.")
    print("\nFINAL:", result)
    with open("reports/head_a_bootstrap_bayesian.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(result, f, sort_keys=False, allow_unicode=True)
    print("wrote reports/head_a_bootstrap_bayesian.yaml")


if __name__ == "__main__":
    run()
