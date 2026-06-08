"""Compute every study number once, write results.json + LaTeX macros + figures + tables.

`python run_all.py --dataset synthetic` regenerates the entire quantitative
content of the paper from the data contract. Numbers are never hand-typed in
the .tex: they flow data -> results.json -> macros/results_macros.tex ->
\\input in the paper. Re-pointing --dataset at the real export reproduces
everything.
"""

from __future__ import annotations

import argparse
import json

import numpy as np

import figures
import tables
from common import (
    ALL_CONFIGS,
    BAND_QUANTILE,
    DIMENSIONS,
    GLOBAL_SEED,
    MACRO_DIR,
    N_PERM,
    NAT_ACCEPT_RATE,
    PRIMARY_CONFIG,
    PRIMARY_VENUE,
    PRODUCTION_CONFIG,
    RELIABILITY_BINS,
    REPLICATION_VENUE,
    RESULTS_DIR,
    SCORE_WEIGHTS,
)
from schema import Dataset, base_reject_rate, load_dataset
from stats import (
    auroc,
    auroc_ci,
    auroc_pvalue,
    benjamini_hochberg,
    classify_at_threshold,
    cliffs_delta,
    cohens_d,
    jonckheere_trend,
    low_band_spearman,
    paired_auroc_diff,
    prevalence_reweighted_bottom_precision,
    quantile_membership_overlap,
    score_band_table,
    spearman,
    spearman_ci,
    threshold_for_accept_rate,
)

_N_BANDS = int(round(1 / BAND_QUANTILE))  # 0.2 -> 5 (quintiles)


def _primary(df):
    return df[(df["venue"] == PRIMARY_VENUE[0]) & (df["year"] == PRIMARY_VENUE[1])].reset_index(drop=True)


def _weighted_overall(df, weights: dict):
    """Recompute the overall as a weighted mean of the subscores under an
    arbitrary weighting (for the equal-weight / leave-one-out robustness check).
    Iterates the weighting's own keys, so a leave-one-out dict (one dimension
    omitted) drops that dimension entirely rather than KeyError-ing."""
    tot = sum(weights.values())
    return sum(w * df[d].values for d, w in weights.items()) / tot


def compute(d: Dataset) -> dict:
    R: dict = {"dataset": d.name, "is_synthetic": d.is_synthetic}

    mini = _primary(d.config_frame(PRIMARY_CONFIG))
    full = _primary(d.config_frame(PRODUCTION_CONFIG))

    # ---- sample / cohorts -------------------------------------------------
    # Cohort M (full-mini, primary large-N) ⊇ cohort H (full, frontier).
    R["sample"] = {
        "n_mini": int(len(mini)),
        "n_full": int(len(full)),
        "n_total_submissions": int(len(d.submissions)),
        "base_reject_rate": base_reject_rate(mini),
        "tier_counts": {t: int((mini["decision_tier"] == t).sum()) for t in mini["decision_tier"].unique()},
    }

    def block(df, tag):
        y = df["accept_bool"].values
        s = df["overall"].values
        out = {
            "auroc": auroc_ci(y, s).as_dict(),
            "spearman_rating": spearman_ci(df["mean_reviewer_rating"].values, s).as_dict(),
            "cohens_d_acc_vs_rej": cohens_d(s[y == 0], s[y == 1]),
            "cliffs_delta": cliffs_delta(s[y == 0], s[y == 1]),
            "trend": jonckheere_trend(s, df["tier_rank"].values, n_perm=N_PERM).as_dict(),
            "subscore_auroc": {dim: auroc_ci(y, df[dim].values).as_dict() for dim in DIMENSIONS},
        }
        return out

    R[PRIMARY_CONFIG] = block(mini, "mini")
    R[PRODUCTION_CONFIG] = block(full, "full")

    # ---- multiple-comparison control across the 5 subscore tests ----------
    sub_p = {dim: auroc_pvalue(mini["accept_bool"].values, mini[dim].values) for dim in DIMENSIONS}
    R["subscore_bh"] = benjamini_hochberg(sub_p, alpha=0.05)

    # ---- citation subscore: the "always-100%" bug -------------------------
    # In this frozen offline grading config the citation dimension is pinned high
    # (no live retrieval wired), so it carries no reject/accept signal. Surface
    # the pinned rate + its (chance) AUROC, and a sensitivity dropping citation
    # from the weighting on BOTH cohorts — the headline must not hinge on it.
    R["citation_pinned"] = _citation_pinned(d, R)
    R["citation_sensitivity"] = _citation_sensitivity(mini, full)

    # ---- null guardrail: shuffled labels must give AUROC ~ 0.5 ------------
    rng = np.random.default_rng(20260601)
    y = mini["accept_bool"].values
    s = mini["overall"].values
    null_aucs = [auroc(rng.permutation(y), s) for _ in range(200)]
    R["null_control"] = {
        "mean_auroc": float(np.mean(null_aucs)),
        "p05": float(np.percentile(null_aucs, 5)),
        "p95": float(np.percentile(null_aucs, 95)),
        "passes": bool(0.45 <= np.mean(null_aucs) <= 0.55),
    }
    assert R["null_control"]["passes"], "null control failed: shuffled-label AUROC not ~0.5"

    # ---- H1: low-end flagging (score bands, with bootstrap lift CI) -------
    bands = score_band_table(
        mini["overall"].values, mini["accept_bool"].values, mini["tier_rank"].values,
        n_bins=_N_BANDS, seed=GLOBAL_SEED,
    )
    R["score_bands"] = [b.__dict__ for b in bands]
    R["bottom_band"] = bands[0].__dict__
    R["top_band"] = bands[-1].__dict__

    # ---- H1 on the FRONTIER (production) cohort directly. The deployable
    # bottom-flag claim should rest on the model that ships, not on the cheap
    # proxy whose low-end bridge to the frontier score is weak (H5). Smaller n
    # and wider CI, but it sidesteps the proxy entirely: the flag is computed on
    # the production score itself.
    bands_full = score_band_table(
        full["overall"].values, full["accept_bool"].values, full["tier_rank"].values,
        n_bins=_N_BANDS, seed=GLOBAL_SEED,
    )
    R["bottom_band_full"] = bands_full[0].__dict__

    # ---- H1 under natural prevalence: reject precision at real ICLR accept rate
    R["prevalence_point"] = prevalence_reweighted_bottom_precision(
        mini["overall"].values, mini["accept_bool"].values, BAND_QUANTILE, NAT_ACCEPT_RATE
    )

    # ---- H5: mini<->frontier bridge on cohort H (global + LOW-END agreement) --
    paired = _primary_pair(d)
    a_mini = paired[f"overall_{PRIMARY_CONFIG}"].values
    a_full = paired[f"overall_{PRODUCTION_CONFIG}"].values
    R["bridge"] = {
        "spearman": spearman_ci(a_mini, a_full).as_dict(),
        "low_band_spearman": low_band_spearman(a_mini, a_full, q=BAND_QUANTILE, n_boot=2000).as_dict(),
        "bottom_overlap": quantile_membership_overlap(a_mini, a_full, q=BAND_QUANTILE),
        "n": int(len(paired)),
    }

    # ---- weighting robustness: equal-weight + leave-one-dimension-out -----
    # The deployed weights are proprietary; show the headline does not hinge on
    # them. AUROC under each alternative weighting + its rank agreement with the
    # deployed score.
    y = mini["accept_bool"].values
    deployed = mini["overall"].values
    eq = _weighted_overall(mini, {d: 1.0 for d in DIMENSIONS})
    wr = {"equal_weight": {"auroc": auroc_ci(y, eq).as_dict(), "rho_vs_deployed": float(spearman(eq, deployed))}}
    loo = {}
    for drop in DIMENSIONS:
        w = {d: SCORE_WEIGHTS[d] for d in DIMENSIONS if d != drop}
        s = _weighted_overall(mini, w)
        loo[drop] = {"auroc": auroc_ci(y, s).as_dict(), "rho_vs_deployed": float(spearman(s, deployed))}
    wr["leave_one_out"] = loo
    R["weight_robustness"] = wr

    # ---- contamination controls: temporal leakage (arXiv-split + contrast) -
    # Compare the clean primary cohort (decisions post-cutoff) to the fully
    # pre-cutoff replication venue (contaminated contrast), and split the headline
    # on arXiv-before-cutoff within the primary cohort.
    R["contamination"] = _contamination(d, mini, full)

    # ---- naive-judge baseline: the "why us" comparison on cohort H --------
    R["naive_baseline"] = _naive_baseline(d, full)

    # ---- manuscript-length confounding: does AIPR just reward length? -----
    R["length_confound"] = _length_confound(mini)

    # ---- grading cost: tokens used per config (the cost-design numbers) ----
    R["cost"] = _cost_by_config(d)

    # ---- run-to-run variance on full (consistent-config re-runs only) -----
    # min_run=1: exclude run 0 (its full_full citation audit returned empty ->
    # pinned 100 for the original cohort, a config-state artifact); the variance
    # sub-study measures stochastic noise under the working-audit re-runs.
    rv = _primary(d.run_variance(PRODUCTION_CONFIG, min_run=1).merge(d.submissions[["submission_id", "venue", "year"]], on="submission_id"))
    R["run_variance_full"] = {
        "median_sd": float(np.nanmedian(rv["run_sd"])) if len(rv) else float("nan"),
        "mean_sd": float(np.nanmean(rv["run_sd"])) if len(rv) else float("nan"),
        "n_runs_each": int(np.nanmax(rv["n_runs"])) if len(rv) else 0,
        # papers actually re-graded (n_runs>1): lets the paper say "n=10 papers
        # re-graded 3x" honestly rather than implying all 100 were repeated.
        "n_variance_papers": int((rv["n_runs"] > 1).sum()) if len(rv) else 0,
    }

    # ---- model-tier comparison: AUROC across configs on the shared cohort H -
    # (mini vs frontier, both the full pipeline — does the frontier model add
    # discrimination over the cheap model on the same papers?)
    h_ids = set(full["submission_id"])
    R["nested_auroc"] = {}
    for cfg in ("full_mini", "full"):
        sub = _primary(d.config_frame(cfg))
        sub = sub[sub["submission_id"].isin(h_ids)]
        if sub["accept_bool"].nunique() == 2:
            R["nested_auroc"][cfg] = auroc_ci(sub["accept_bool"].values, sub["overall"].values).as_dict()

    # ---- replication venue (full-mini only) -------------------------------
    rep = d.config_frame(PRIMARY_CONFIG)
    rep = rep[(rep["venue"] == REPLICATION_VENUE[0]) & (rep["year"] == REPLICATION_VENUE[1])]
    if len(rep) and rep["accept_bool"].nunique() == 2:
        R["replication"] = {
            "venue": f"{REPLICATION_VENUE[0]} {REPLICATION_VENUE[1]}",
            "n": int(len(rep)),
            "auroc": auroc_ci(rep["accept_bool"].values, rep["overall"].values).as_dict(),
            "spearman_rating": spearman_ci(rep["mean_reviewer_rating"].values, rep["overall"].values).as_dict(),
        }
    return R


def _primary_pair(d: Dataset):
    p = d.paired_frame(PRIMARY_CONFIG, PRODUCTION_CONFIG)
    ids = set(_primary(d.config_frame(PRODUCTION_CONFIG))["submission_id"])
    return p[p["submission_id"].isin(ids)].reset_index(drop=True)


def _contamination(d: Dataset, mini, full) -> dict:
    """Temporal leakage controls — the outcome cannot be memorized on the primary
    venue (decisions postdate the model cutoff). Three comparable full-mini AUROCs
    as `bars`: (a) the clean primary cohort; (b) the fully pre-cutoff replication
    venue — the *contaminated contrast*: if discrimination is no stronger there
    than on the clean cohort, memorization is not driving it; (c) the primary
    cohort with arXiv-before-cutoff papers excluded — bounding residual
    paper-text leakage. `arxiv_split` carries the split counts. Self-skips
    cohorts/columns the export lacks."""
    out: dict = {}
    bars: dict = {}
    # (a) clean primary cohort
    if mini["accept_bool"].nunique() == 2:
        bars["primary"] = {
            "label": f"{PRIMARY_VENUE[0]} {PRIMARY_VENUE[1]} (clean)",
            "n": int(len(mini)),
            "auroc": auroc_ci(mini["accept_bool"].values, mini["overall"].values).as_dict(),
        }
    # (b) contaminated contrast: the fully pre-cutoff replication venue
    rep = d.config_frame(PRIMARY_CONFIG)
    rep = rep[(rep["venue"] == REPLICATION_VENUE[0]) & (rep["year"] == REPLICATION_VENUE[1])]
    if len(rep) and rep["accept_bool"].nunique() == 2:
        bars["replication"] = {
            "label": f"{REPLICATION_VENUE[0]} {REPLICATION_VENUE[1]} (pre-cutoff)",
            "n": int(len(rep)),
            "auroc": auroc_ci(rep["accept_bool"].values, rep["overall"].values).as_dict(),
        }
    # (c) arXiv-split sensitivity within the primary cohort
    if "arxiv_prior_to_cutoff" in mini.columns and mini["arxiv_prior_to_cutoff"].notna().any():
        flag = mini["arxiv_prior_to_cutoff"].fillna(0).astype(int)
        clean = mini[flag == 0]
        out["arxiv_split"] = {
            "n_prior": int((flag == 1).sum()),
            "n_clean": int((flag == 0).sum()),
        }
        if clean["accept_bool"].nunique() == 2:
            e = auroc_ci(clean["accept_bool"].values, clean["overall"].values).as_dict()
            out["arxiv_split"]["auroc_no_prior"] = e
            bars["arxiv_no_prior"] = {
                "label": f"{PRIMARY_VENUE[1]}, excl.\\ pre-cutoff arXiv",
                "n": int(len(clean)),
                "auroc": e,
            }
    out["bars"] = bars
    return out


def _naive_baseline(d: Dataset, full) -> dict:
    """The "why us" comparison on cohort H: AIPR `full` vs the naive single-prompt
    judge (same model, same PDF, no rubric/audit), scored only on the overall and
    its mapping to accept/reject. Reports (a) discrimination (AUROC side by side),
    (b) the AIPR@60 operating point for BOTH graders plus each grader at its own
    matched accept-rate (so the comparison is not an artefact of forcing the
    baseline onto AIPR's cutoff), and (c) run-to-run reliability (median
    within-paper SD). Self-skips when the export carries no naive gradings."""
    out: dict = {}
    h_ids = set(full["submission_id"])
    naive = _primary(d.config_frame("naive"))
    naive = naive[naive["submission_id"].isin(h_ids)]
    if not len(naive) or naive["accept_bool"].nunique() < 2:
        return out
    out["n"] = int(len(naive))

    # (a) discrimination. Marginal AUROCs side by side, PLUS the paired
    # difference (same labels, same papers) — the parity test the overlapping
    # marginal CIs cannot resolve. Expected non-significant: a frontier model
    # already scores competently, so the structured pipeline's value is not raw
    # discrimination but the reliability + grounded output it adds (intelligence
    # is not the bottleneck; processing is).
    out["auroc_full"] = auroc_ci(full["accept_bool"].values, full["overall"].values).as_dict()
    out["auroc_naive"] = auroc_ci(naive["accept_bool"].values, naive["overall"].values).as_dict()
    paired = full.merge(naive[["submission_id", "overall"]], on="submission_id", suffixes=("_full", "_naive"))
    out["auroc_diff"] = paired_auroc_diff(
        paired["accept_bool"].values, paired["overall_full"].values, paired["overall_naive"].values, seed=GLOBAL_SEED
    )

    # (b) operating point. AIPR@60 = predict accept iff overall >= 60, applied to
    # BOTH graders; plus each grader at its own threshold matched to the human
    # accept-rate (fair — the baseline is not handicapped by AIPR's cutoff).
    acc_rate = float(full["accept_bool"].mean())
    out["op_at60"] = {
        "threshold": 60.0,
        "full": classify_at_threshold(full["accept_bool"].values, full["overall"].values, 60.0),
        "naive": classify_at_threshold(naive["accept_bool"].values, naive["overall"].values, 60.0),
    }
    out["op_matched"] = {
        "accept_rate": acc_rate,
        "full": classify_at_threshold(
            full["accept_bool"].values, full["overall"].values,
            threshold_for_accept_rate(full["overall"].values, acc_rate),
        ),
        "naive": classify_at_threshold(
            naive["accept_bool"].values, naive["overall"].values,
            threshold_for_accept_rate(naive["overall"].values, acc_rate),
        ),
    }

    # (c) reliability: within-paper run-SD distribution, naive vs full
    def _median_sd(cfg: str) -> tuple[float, int]:
        # min_run=1: same consistent-config re-runs as run_variance_full, so the
        # full-vs-naive reliability comparison is apples-to-apples on runs 1..N-1.
        rv = d.run_variance(cfg, min_run=1)
        rv = rv[rv["submission_id"].isin(h_ids)]
        sd = float(np.nanmedian(rv["run_sd"])) if len(rv) else float("nan")
        nr = int(np.nanmax(rv["n_runs"])) if len(rv) else 0
        return sd, nr

    full_sd, full_nr = _median_sd("full")
    naive_sd, naive_nr = _median_sd("naive")
    out["reliability"] = {
        "full_median_sd": full_sd, "naive_median_sd": naive_sd,
        "full_n_runs": full_nr, "naive_n_runs": naive_nr,
    }
    return out


def _citation_pinned(d: Dataset, R: dict) -> dict:
    """The citation "always-100%" bug, as numbers. Fraction of citation subscores
    pinned at 100 on the primary venue (frontier `full` and `full_mini`), plus the
    citation dimension's reject/accept AUROC on the frontier cohort (≈0.5, i.e.
    chance) pulled from the already-computed subscore block. In this frozen
    offline config the audit pass had no live retrieval, so citation defaulted
    high and carries no scoring signal."""
    prim = d.submissions[(d.submissions["venue"] == PRIMARY_VENUE[0]) & (d.submissions["year"] == PRIMARY_VENUE[1])]
    prim_ids = set(prim["submission_id"])
    # run 0 only: the original single-run study cohort. The variance sub-study's
    # re-runs (run_index>=1) have a working audit and would dilute the cohort's
    # pinned rate; the bug statistic is about the cohort that was actually graded.
    g = d.gradings[(d.gradings["submission_id"].isin(prim_ids)) & (d.gradings["run_index"] == 0)]

    def pinned(cfg: str) -> float:
        gc = g[(g["config"] == cfg) & g["citation"].notna()]
        return float((gc["citation"] >= 100).mean()) if len(gc) else float("nan")

    return {
        "full_pinned_100": pinned(PRODUCTION_CONFIG),
        "mini_pinned_100": pinned(PRIMARY_CONFIG),
        "full_citation_auroc": R[PRODUCTION_CONFIG]["subscore_auroc"]["citation"]["point"],
    }


def _citation_sensitivity(mini, full) -> dict:
    """Robustness: recompute the overall WITHOUT citation in the weighting and
    re-measure discrimination, on both cohorts. Because citation is pinned (no
    signal) and lightly weighted (0.5/11.5), dropping it should leave the headline
    AUROC essentially unchanged — so the validity result does not depend on the
    broken dimension."""
    out: dict = {}
    w_no_cit = {dd: SCORE_WEIGHTS[dd] for dd in DIMENSIONS if dd != "citation"}
    for tag, df in (("mini", mini), ("full", full)):
        y = df["accept_bool"].values
        s = _weighted_overall(df, w_no_cit)
        out[tag] = {
            "auroc_with": auroc_ci(y, df["overall"].values).as_dict(),
            "auroc_drop_citation": auroc_ci(y, s).as_dict(),
            "rho_vs_deployed": float(spearman(s, df["overall"].values)),
        }
    return out


def _length_confound(mini) -> dict:
    """Rank correlation of the AIPR overall with manuscript-length metrics, on the
    primary (full-mini) cohort. A score that merely rewarded length/polish would
    show a strong correlation here; the check is that it does not.
    Self-skips a metric the export lacks (all-NaN column)."""
    out: dict = {}
    overall = mini["overall"].values
    for col in ("page_count", "word_count", "n_references", "n_figures"):
        if col in mini.columns and mini[col].notna().any():
            m = mini[[col, "overall"]].dropna()
            if len(m) > 10:
                out[col] = spearman_ci(m[col].values.astype(float), m["overall"].values).as_dict()
    return out


# Dimensions surfaced on the interactive hover. Citation is deliberately omitted:
# in the graded cohort it is uninformative (pinned at the max, AUROC ~0.5; see the
# paper's results/discussion), so showing it would mislead rather than inform.
WEB_SUBSCORES = ("novelty", "rigor", "applicability", "clarity")


def _num(v) -> float | None:
    """NaN-safe float for JSON (NaN is not valid JSON). Returns None for missing or
    NaN values — e.g. the naive judge emits only an overall, so its per-dimension
    subscores are absent."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else round(f, 1)


def _subscores(r, suffix: str = "") -> dict:
    """The four informative dimension scores for one row, NaN -> None."""
    return {dim: _num(r.get(f"{dim}{suffix}")) for dim in WEB_SUBSCORES}


def _safe(x) -> float | None:
    """NaN/inf -> None so the emitted JSON is valid for a browser's JSON.parse
    (Python json writes bare `NaN`, which JS rejects). Used only for points.json,
    the web bundle — results.json keeps NaN for the analysis/paper side."""
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return None
    return xf if np.isfinite(xf) else None


def _web_stats(R: dict) -> dict:
    """Compact, JS-safe headline numbers for the interactive page's callouts —
    parallel to the paper's macros but as JSON (NaN -> null). One source of truth:
    the same `R` the paper reads, so the page and the PDF never drift."""
    fu, mi = R[PRODUCTION_CONFIG], R[PRIMARY_CONFIG]
    nb = R.get("naive_baseline", {})
    cp = R.get("citation_pinned", {})
    cs = R.get("citation_sensitivity", {}).get("full", {})
    rel = nb.get("reliability", {})
    return {
        "n_validation": R["sample"]["n_mini"],
        "n_full": R["sample"]["n_full"],
        "auroc_full": _safe(fu["auroc"]["point"]),
        "auroc_mini": _safe(mi["auroc"]["point"]),
        "auroc_naive": _safe(nb.get("auroc_naive", {}).get("point")),
        "auroc_diff": {k: _safe(v) for k, v in nb.get("auroc_diff", {}).items()},
        "spearman_rating_full": _safe(fu["spearman_rating"]["point"]),
        "bottom_reject_rate": _safe(R["bottom_band"]["reject_rate"]),
        "bottom_reject_rate_frontier": _safe(R["bottom_band_full"]["reject_rate"]),
        "bottom_lift": _safe(R["bottom_band"]["lift"]),
        "bridge_rho": _safe(R["bridge"]["spearman"]["point"]),
        "citation_pinned_full": _safe(cp.get("full_pinned_100")),
        "citation_pinned_mini": _safe(cp.get("mini_pinned_100")),
        "citation_auroc": _safe(cp.get("full_citation_auroc")),
        "auroc_drop_citation_full": _safe(cs.get("auroc_drop_citation", {}).get("point")),
        "run_sd_full": _safe(rel.get("full_median_sd")),
        "run_sd_naive": _safe(rel.get("naive_median_sd")),
        "run_sd_n_papers": R["run_variance_full"]["n_variance_papers"],
    }


def _points(d: Dataset, R: dict) -> dict:
    """Per-point data for the INTERACTIVE web figures (not the static paper). Each
    point carries its four informative subscores (novelty/rigor/applicability/
    clarity; `WEB_SUBSCORES`) so the hover shows the dimension breakdown behind the
    overall. Released only via the frontend bundle, never the paper. Bundles a
    JS-safe `stats` block (NaN -> null) so the page needs only this one file."""
    mini = _primary(d.config_frame(PRIMARY_CONFIG))
    full = _primary(d.config_frame(PRODUCTION_CONFIG))
    naive = _primary(d.config_frame("naive"))
    naive = naive[naive["submission_id"].isin(set(full["submission_id"]))]

    def rows(df) -> list:
        out = []
        for _, r in df.iterrows():
            out.append({
                "submission_id": r["submission_id"],
                "overall": float(r["overall"]),
                "mean_reviewer_rating": float(r["mean_reviewer_rating"]),
                "decision_tier": r["decision_tier"],
                "tier_rank": int(r["tier_rank"]),
                "accept_bool": int(r["accept_bool"]),
                **_subscores(r),
            })
        return out

    paired = _primary_pair(d)
    bridge = []
    for _, r in paired.iterrows():
        bridge.append({
            "submission_id": r["submission_id"],
            "overall_mini": float(r[f"overall_{PRIMARY_CONFIG}"]),
            "overall_full": float(r[f"overall_{PRODUCTION_CONFIG}"]),
            # frontier (full) subscores for the hover
            **_subscores(r, suffix=f"_{PRODUCTION_CONFIG}"),
        })

    # Per-paper within-paper score SD over repeated runs (runs 1..N-1; min_run=1
    # excludes the run-0 citation artifact, matching run_variance_full). Drives the
    # reliability plot: AIPR clustered near zero, the naive judge spread wide.
    def _run_sds(cfg: str) -> list:
        rv = d.run_variance(cfg, min_run=1)
        rv = rv[rv["n_runs"] > 1]
        return [round(float(x), 2) for x in rv["run_sd"].dropna()]

    return {
        "venue": f"{PRIMARY_VENUE[0]} {PRIMARY_VENUE[1]}",
        "stats": _web_stats(R),
        "validation": rows(mini),  # fig_validation (full-mini, n=300)
        "full": rows(full),        # frontier cohort
        "naive": rows(naive),      # naive judge — overall only, no subscores (null)
        "bridge": bridge,          # fig_bridge (paired mini<->full; frontier subscores)
        "variance": {"full": _run_sds(PRODUCTION_CONFIG), "naive": _run_sds("naive")},
    }


def _cost_by_config(d: Dataset) -> dict:
    """Mean tokens used per config on the primary venue (the cost-design numbers).
    Self-skips when the export carries no token usage."""
    out: dict = {}
    g = d.gradings
    if "input_tokens" not in g.columns or g["input_tokens"].isna().all():
        return out
    prim = d.submissions[(d.submissions["venue"] == PRIMARY_VENUE[0]) & (d.submissions["year"] == PRIMARY_VENUE[1])]
    prim_ids = set(prim["submission_id"])
    g = g[g["submission_id"].isin(prim_ids)]
    for cfg in ALL_CONFIGS:
        gc = g[g["config"] == cfg]
        if not len(gc):
            continue
        inp, outp = float(gc["input_tokens"].mean()), float(gc["output_tokens"].mean())
        out[cfg] = {"input": inp, "output": outp, "total": inp + outp, "n": int(len(gc))}
    return out


# ----------------------------------------------------------------------------
# LaTeX macro emission — numbers enter the paper only through these.
# ----------------------------------------------------------------------------
def _pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}"


def write_macros(R: dict) -> None:
    L: list[str] = []

    def cmd(name: str, value: str):
        L.append(rf"\newcommand{{\{name}}}{{{value}\xspace}}")

    s = R["sample"]
    cmd("NminiPrimary", str(s["n_mini"]))
    cmd("NfullPrimary", str(s["n_full"]))
    cmd("Nsubmissions", str(s["n_total_submissions"]))
    cmd("baseRejectRate", _pct(s["base_reject_rate"]))

    mi = R[PRIMARY_CONFIG]
    fu = R[PRODUCTION_CONFIG]

    def ci_macro(prefix: str, est: dict, d: int = 2):
        cmd(prefix, f"{est['point']:.{d}f}")
        cmd(prefix + "CI", f"[{est['lo']:.{d}f}, {est['hi']:.{d}f}]")
        cmd(prefix + "Full", f"{est['point']:.{d}f} (95\\% CI {est['lo']:.{d}f}--{est['hi']:.{d}f})")

    ci_macro("aurocMini", mi["auroc"])
    ci_macro("aurocFull", fu["auroc"])
    ci_macro("spearmanRatingMini", mi["spearman_rating"])
    ci_macro("spearmanRatingFull", fu["spearman_rating"])
    cmd("cohensDMini", f"{mi['cohens_d_acc_vs_rej']:.2f}")
    cmd("cliffsDeltaMini", f"{mi['cliffs_delta']:.2f}")

    tr = mi["trend"]
    pp = tr["p_permutation"]
    cmd("trendP", ("<0.0001" if pp < 1e-4 else f"{pp:.4f}"))
    # Relation-aware form for prose: "p<0.0001" not "p=<0.0001" (table cells and
    # figure annotations use \trendP / _pfrag respectively).
    cmd("trendPrel", ("p<0.0001" if pp < 1e-4 else f"p={pp:.4f}"))
    cmd("trendRho", f"{tr['spearman_rho']:.2f}")
    cmd("trendRhoCI", f"[{tr['spearman_ci'][0]:.2f}, {tr['spearman_ci'][1]:.2f}]")

    bb, tb = R["bottom_band"], R["top_band"]
    cmd("bottomRejectRate", _pct(bb["reject_rate"]))
    cmd("bottomRejectCI", f"[{_pct(bb['reject_ci'][0])}, {_pct(bb['reject_ci'][1])}]")
    cmd("bottomLift", f"{bb['lift']:.2f}")
    cmd("bottomOralRate", _pct(bb["oral_rate"]))
    cmd("topAcceptRate", _pct(tb["accept_rate"]))
    cmd("topOralRate", _pct(tb["oral_rate"]))

    # H1 on the production (frontier) cohort directly — the deployable number that
    # does not route through the cheap-model proxy (Frontier suffix; "Full" is
    # already taken by the CI-text convention above).
    bbf = R["bottom_band_full"]
    cmd("bottomRejectRateFrontier", _pct(bbf["reject_rate"]))
    cmd("bottomRejectCIFrontier", f"[{_pct(bbf['reject_ci'][0])}, {_pct(bbf['reject_ci'][1])}]")
    cmd("bottomLiftFrontier", f"{bbf['lift']:.2f}")
    cmd("bottomOralRateFrontier", _pct(bbf["oral_rate"]))

    ci_macro("bridgeRho", R["bridge"]["spearman"])
    cmd("bridgeN", str(R["bridge"]["n"]))

    # H1 lift CI — the pre-registered success rule reads its lower bound (>1).
    cmd("bottomLiftCI", f"[{bb['lift_ci'][0]:.2f}, {bb['lift_ci'][1]:.2f}]")
    cmd("bottomLiftFull", f"{bb['lift']:.2f} (95\\% CI {bb['lift_ci'][0]:.2f}--{bb['lift_ci'][1]:.2f})")

    # Low-end bridge: agreement WHERE THE CLAIM LIVES, not just globally.
    lb = R["bridge"]["low_band_spearman"]
    cmd("bridgeLowRho", f"{lb['point']:.2f}")
    cmd("bridgeLowRhoFull", f"{lb['point']:.2f} (95\\% CI {lb['lo']:.2f}--{lb['hi']:.2f})")
    cmd("bridgeOverlap", _pct(R["bridge"]["bottom_overlap"]["recall"]))

    # Natural-prevalence operating point (real ICLR accept rate).
    pp = R["prevalence_point"]
    cmd("natAcceptRate", _pct(pp["nat_accept_rate"]))
    cmd("natBaseReject", _pct(pp["base_reject_rate"]))
    cmd("natBottomPrecision", _pct(pp["bottom_reject_precision"]))

    # Weighting robustness (equal-weight + leave-one-out range).
    ew = R["weight_robustness"]["equal_weight"]
    ci_macro("aurocEqualWeight", ew["auroc"])
    cmd("rhoEqualWeight", f"{ew['rho_vs_deployed']:.2f}")
    loo = R["weight_robustness"]["leave_one_out"]
    loo_aurocs = [loo[dd]["auroc"]["point"] for dd in loo]
    cmd("looAurocMin", f"{min(loo_aurocs):.2f}")
    cmd("looAurocMax", f"{max(loo_aurocs):.2f}")

    # Contamination controls (temporal): the contaminated-contrast AUROC is the
    # replication venue (emitted as \aurocRep below); here the arXiv-split row.
    axs = R["contamination"].get("arxiv_split", {})
    if "auroc_no_prior" in axs:
        ci_macro("aurocNoArxivPrior", axs["auroc_no_prior"])
        cmd("nArxivPrior", str(axs["n_prior"]))

    # Naive-judge baseline (the "why us" experiment): AIPR full vs a single
    # one-paragraph prompt — discrimination gap, AIPR@60 operating point, and
    # run-to-run reliability.
    nb = R.get("naive_baseline", {})
    if nb:
        cmd("naiveN", str(nb["n"]))
        ci_macro("aurocNaive", nb["auroc_naive"])
        cmd("aurocFullVsNaive", f"{nb['auroc_full']['point'] - nb['auroc_naive']['point']:.2f}")
        # Paired AUROC difference (full - naive) with CI + two-sided bootstrap p.
        # The parity test: CI straddles 0 / p not significant => scoring parity,
        # which is the "intelligence is not the bottleneck" result.
        ad = nb["auroc_diff"]
        cmd("aurocDiffFullNaive", f"{ad['delta']:.2f}")
        cmd("aurocDiffCI", f"[{ad['lo']:.2f}, {ad['hi']:.2f}]")
        pd = ad["p"]
        cmd("aurocDiffP", ("<0.001" if pd < 1e-3 else f"{pd:.2f}"))
        cmd("aurocDiffPrel", ("p<0.001" if pd < 1e-3 else f"p={pd:.2f}"))
        op = nb["op_at60"]
        cmd("opSixtyFullAcc", _pct(op["full"]["balanced_accuracy"]))
        cmd("opSixtyNaiveAcc", _pct(op["naive"]["balanced_accuracy"]))
        rel = nb["reliability"]
        # both SDs from the SAME cohort-H reliability computation (apples to apples)
        cmd("fullRunSD", f"{rel['full_median_sd']:.1f}")
        cmd("naiveRunSD", f"{rel['naive_median_sd']:.1f}")

    # Manuscript-length confounding (rank corr of overall with length metrics).
    lc = R.get("length_confound", {})
    for col, name in (("page_count", "lenRhoPage"), ("word_count", "lenRhoWord"),
                      ("n_references", "lenRhoRefs"), ("n_figures", "lenRhoFigs")):
        if col in lc:
            ci_macro(name, lc[col])

    # Grading cost (tokens used per config; k = thousands).
    cost = R.get("cost", {})
    for cfg, name in (("full_mini", "costFullMiniTok"),
                      ("full", "costFullTok"), ("naive", "costNaiveTok")):
        if cfg in cost:
            cmd(name, f"{cost[cfg]['total'] / 1000:.1f}k")
    if "full" in cost and cost.get("full_mini", {}).get("total", 0) > 0:
        cmd("costFullVsMini", f"{cost['full']['total'] / cost['full_mini']['total']:.1f}")

    cmd("runSDmedian", f"{R['run_variance_full']['median_sd']:.1f}")
    cmd("runSDnPapers", str(R["run_variance_full"]["n_variance_papers"]))

    # Citation "always-100%" bug + the sensitivity that contains it.
    cp = R.get("citation_pinned", {})
    if cp:
        cmd("citationPinnedFull", _pct(cp["full_pinned_100"]))
        cmd("citationPinnedMini", _pct(cp["mini_pinned_100"]))
        cmd("citationAUROC", f"{cp['full_citation_auroc']:.2f}")
    cs = R.get("citation_sensitivity", {})
    if cs:
        cmd("aurocDropCitationMini", f"{cs['mini']['auroc_drop_citation']['point']:.2f}")
        cmd("aurocDropCitationFull", f"{cs['full']['auroc_drop_citation']['point']:.2f}")

    if "replication" in R:
        ci_macro("aurocRep", R["replication"]["auroc"])
        cmd("repVenue", R["replication"]["venue"])

    header = (
        "% AUTO-GENERATED by analysis/run_all.py — DO NOT EDIT.\n"
        "% Regenerate: python run_all.py --dataset <name>\n"
        "% Requires \\usepackage{xspace} in the preamble.\n"
    )
    (MACRO_DIR / "results_macros.tex").write_text(header + "\n".join(L) + "\n", encoding="utf-8")
    # Drop/raise the synthetic-data banner flag the paper checks for.
    flag = MACRO_DIR / "SYNTHETIC.flag"
    if R.get("is_synthetic"):
        flag.write_text("synthetic\n", encoding="utf-8")
    elif flag.exists():
        flag.unlink()
    print(f"wrote {len(L)} macros -> {MACRO_DIR / 'results_macros.tex'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="synthetic")
    ap.add_argument("--no-figures", action="store_true")
    args = ap.parse_args()

    d = load_dataset(args.dataset)
    R = compute(d)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "results.json").write_text(json.dumps(R, indent=2, default=float), encoding="utf-8")
    print(f"wrote {RESULTS_DIR / 'results.json'}")

    # Per-point data for the interactive web figures (carries evaluation_id so
    # each AIPR point links to its live review). Static-paper build ignores this.
    (RESULTS_DIR / "points.json").write_text(
        json.dumps(_points(d, R), indent=2, default=float), encoding="utf-8"
    )
    print(f"wrote {RESULTS_DIR / 'points.json'}")

    write_macros(R)
    tables.write_all(d, R)
    if not args.no_figures:
        figures.render_all(d, R)
    print("done.")


if __name__ == "__main__":
    main()
