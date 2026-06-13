"""Correctness tests for the analysis pipeline.

Run from the analysis/ directory:  .venv/Scripts/python -m pytest -q
These guard the two things a reviewer must trust: the data contract rejects
malformed input, and the statistics compute what they claim. Estimator
*calibration* (CI coverage, Type-I error) is established separately by
simulation.py; these are unit-level correctness checks.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import schema  # noqa: E402
import stats  # noqa: E402


# --------------------------------------------------------------------------- schema
def test_synthetic_loads_and_nests():
    d = schema.load_dataset("synthetic")
    c = d.cohort_counts()
    assert c["full"] <= c["full_mini"]  # cohort H ⊆ M
    assert d.submissions["accept_bool"].nunique() == 2


def test_validate_rejects_bad_tier_rank():
    d = schema.load_dataset("synthetic")
    subs = d.submissions.copy()
    subs.loc[0, "tier_rank"] = 9  # inconsistent with decision_tier
    with pytest.raises(AssertionError):
        schema.validate(subs, d.gradings)


def test_validate_rejects_mixed_pipeline_version():
    d = schema.load_dataset("synthetic")
    grad = d.gradings.copy()
    grad.loc[0, "pipeline_version"] = "v5"
    with pytest.raises(AssertionError):
        schema.validate(d.submissions, grad)


def test_validate_rejects_out_of_range_score():
    d = schema.load_dataset("synthetic")
    grad = d.gradings.copy()
    grad.loc[0, "overall"] = 150
    with pytest.raises(AssertionError):
        schema.validate(d.submissions, grad)


def test_validate_rejects_duplicate_submission_id():
    d = schema.load_dataset("synthetic")
    subs = d.submissions.copy()
    subs.loc[1, "submission_id"] = subs.loc[0, "submission_id"]  # collide two ids
    with pytest.raises(AssertionError):
        schema.validate(subs, d.gradings)


def test_validate_rejects_unknown_config():
    d = schema.load_dataset("synthetic")
    grad = d.gradings.copy()
    grad.loc[0, "config"] = "mystery_config"
    with pytest.raises(AssertionError):
        schema.validate(d.submissions, grad)


def test_validate_rejects_missing_required_column():
    d = schema.load_dataset("synthetic")
    subs = d.submissions.drop(columns=["decision_raw"])
    with pytest.raises(AssertionError):
        schema.validate(subs, d.gradings)


def test_validate_rejects_bad_metadata_domain():
    d = schema.load_dataset("synthetic")
    subs = d.submissions.copy()
    subs.loc[0, "arxiv_prior_to_cutoff"] = 7  # not 0/1
    with pytest.raises(AssertionError):
        schema.validate(subs, d.gradings)


def test_validate_rejects_negative_token_usage():
    d = schema.load_dataset("synthetic")
    grad = d.gradings.copy()
    grad.loc[0, "input_tokens"] = -5
    with pytest.raises(AssertionError):
        schema.validate(d.submissions, grad)


def test_synthetic_has_metadata_and_leakage_configs():
    d = schema.load_dataset("synthetic")
    for c in schema.METADATA_COLS:
        assert c in d.submissions.columns
    # manuscript length + grading token usage are present
    assert {"word_count", "token_count"} <= set(d.submissions.columns)
    for c in schema.GRADING_USAGE_COLS:
        assert c in d.gradings.columns and d.gradings[c].notna().any()
    # the two-pass pipeline config uses more input tokens than the single-pass naive judge
    g = d.gradings
    assert g[g["config"] == "full"]["input_tokens"].mean() > g[g["config"] == "naive"]["input_tokens"].mean()
    configs = set(d.gradings["config"].unique())
    assert "naive" in configs
    # the Phase-2 Pillar-1 re-grade config is present
    assert "full_full_p2" in configs
    # the dropped leakage configs must not reappear in the export
    assert not ({"blinded", "prior_only"} & configs)
    # naive and the Pillar-1 re-grade are graded on the H cohort only
    h_ids = set(d.gradings.loc[d.gradings["config"] == "full", "submission_id"])
    for lc in ("naive", "full_full_p2"):
        lc_ids = set(d.gradings.loc[d.gradings["config"] == lc, "submission_id"])
        assert lc_ids <= h_ids and lc_ids


def test_naive_baseline_contract():
    """The naive baseline is honest about what it is: an OVERALL-only grade
    (subscores blank), marked pipeline_version='naive' (NOT v6 — it is a single
    prompt, not the pipeline), graded on cohort H."""
    d = schema.load_dataset("synthetic")
    naive = d.gradings[d.gradings["config"] == "naive"]
    assert len(naive)
    # overall present; the five subscores are blank by design
    assert naive["overall"].notna().all()
    for dim in ("novelty", "rigor", "applicability", "clarity", "citation"):
        assert naive[dim].isna().all(), f"naive must not carry a {dim} subscore"
    # honest pipeline marker
    assert set(naive["pipeline_version"].unique()) == {"naive"}
    # same model as full (only the pipeline differs)
    full_model = set(d.gradings.loc[d.gradings["config"] == "full", "model_name"].unique())
    assert set(naive["model_name"].unique()) == full_model
    # multiple runs per paper so run-to-run variance is measurable
    runs = naive.groupby("submission_id")["run_index"].nunique()
    assert runs.min() >= 2


def test_validate_rejects_naive_mislabeled_v6():
    """A naive row labeled v6 implies a pipeline it never ran — must be rejected."""
    d = schema.load_dataset("synthetic")
    grad = d.gradings.copy()
    idx = grad.index[grad["config"] == "naive"][0]
    grad.loc[idx, "pipeline_version"] = "v6"
    with pytest.raises(AssertionError):
        schema.validate(d.submissions, grad)


def test_validate_rejects_nonnaive_missing_subscore():
    """Only naive may omit subscores; a missing subscore on a full row is a bug."""
    d = schema.load_dataset("synthetic")
    grad = d.gradings.copy()
    idx = grad.index[grad["config"] == "full"][0]
    grad.loc[idx, "novelty"] = float("nan")
    with pytest.raises(AssertionError):
        schema.validate(d.submissions, grad)


# ------------------------------------------------------------ per-(venue, year) ladders
def test_synthetic_iclr2025_arm_and_vocabulary():
    """The synthetic Phase-2 arm: all four 2025 tiers, ranked by the 4-tier
    ladder (spotlight rank 2, oral rank 3), decision_raw drawn verbatim from
    the recorded fixture vocabulary, and full-mini ONLY (no 2025 frontier
    arm, per the addendum)."""
    d = schema.load_dataset("synthetic")
    rep = d.submissions[(d.submissions["venue"] == "ICLR") & (d.submissions["year"] == 2025)]
    assert len(rep)
    assert set(rep["decision_tier"]) == {"reject", "poster", "spotlight", "oral"}
    assert (rep.loc[rep["decision_tier"] == "spotlight", "tier_rank"] == 2).all()
    assert (rep.loc[rep["decision_tier"] == "oral", "tier_rank"] == 3).all()
    allowed = {"ICLR 2025 Oral", "ICLR 2025 Spotlight", "ICLR 2025 Poster",
               "Submitted to ICLR 2025", "ICLR.cc/2025/Conference/Rejected_Submission"}
    assert set(rep["decision_raw"]) <= allowed
    g25 = d.gradings[d.gradings["submission_id"].isin(set(rep["submission_id"]))]
    assert set(g25["config"]) == {"full_mini"}


def test_validate_rejects_spotlight_under_2026_ladder():
    """Consumer mirror of the producer's stray-spotlight pin: a spotlight row
    under (ICLR, 2026) — whose ladder has no spotlight — must be rejected."""
    d = schema.load_dataset("synthetic")
    subs = d.submissions.copy()
    idx = subs.index[(subs["year"] == 2026) & (subs["decision_tier"] == "oral")][0]
    subs.loc[idx, "decision_tier"] = "spotlight"  # rank stays 2: valid for 2025, not 2026
    with pytest.raises(AssertionError):
        schema.validate(subs, d.gradings)


def test_validate_rejects_unprofiled_venue_year():
    """An unprofiled (venue, year) fails loudly — never a silent fallthrough
    to another year's ladder."""
    d = schema.load_dataset("synthetic")
    subs = d.submissions.copy()
    subs.loc[subs.index[0], "year"] = 2024
    with pytest.raises(AssertionError):
        schema.validate(subs, d.gradings)


def test_validate_rejects_2025_rank_under_wrong_ladder():
    """A 2025 oral mis-ranked with the 3-tier rank (2 instead of 3) must fail
    the row-wise bijection."""
    d = schema.load_dataset("synthetic")
    subs = d.submissions.copy()
    idx = subs.index[(subs["year"] == 2025) & (subs["decision_tier"] == "oral")][0]
    subs.loc[idx, "tier_rank"] = 2
    with pytest.raises(AssertionError):
        schema.validate(subs, d.gradings)


def test_full_full_p2_contract():
    """The Pillar-1 re-grade rows: single run, v6, same model as full, all
    five subscores present, citation informative (not pinned), ids ⊆ H."""
    d = schema.load_dataset("synthetic")
    p2 = d.gradings[d.gradings["config"] == "full_full_p2"]
    assert len(p2)
    assert set(p2["run_index"]) == {0}
    assert set(p2["pipeline_version"]) == {"v6"}
    full_model = set(d.gradings.loc[d.gradings["config"] == "full", "model_name"])
    assert set(p2["model_name"]) == full_model
    for dim in schema.DIMENSIONS:
        assert p2[dim].notna().all(), f"full_full_p2 must carry the {dim} subscore"
    assert (p2["citation"] >= 100).mean() < 0.5  # post-fix: not pinned at 100
    h_ids = set(d.gradings.loc[d.gradings["config"] == "full", "submission_id"])
    assert set(p2["submission_id"]) <= h_ids


def test_validate_rejects_p2_outside_cohort_h():
    """full_full_p2 graded outside the frozen cohort-H ids violates 9b."""
    import pandas as pd

    d = schema.load_dataset("synthetic")
    grad = d.gradings.copy()
    h_ids = set(grad.loc[grad["config"] == "full", "submission_id"])
    outside = next(
        s for s in grad.loc[grad["config"] == "full_mini", "submission_id"].unique()
        if s not in h_ids
    )
    row = grad[(grad["config"] == "full_mini") & (grad["submission_id"] == outside)].iloc[[0]].copy()
    row["config"] = "full_full_p2"
    bad = pd.concat([grad, row], ignore_index=True)
    with pytest.raises(AssertionError):
        schema.validate(d.submissions, bad)


def test_validate_rejects_p2_mislabeled_non_v6():
    """A full_full_p2 row claiming a non-v6 pipeline must be rejected (the
    non-naive uniform-v6 invariant covers the p2 config)."""
    d = schema.load_dataset("synthetic")
    grad = d.gradings.copy()
    idx = grad.index[grad["config"] == "full_full_p2"][0]
    grad.loc[idx, "pipeline_version"] = "v5"
    with pytest.raises(AssertionError):
        schema.validate(d.submissions, grad)


# --------------------------------------------------------------------------- AUROC
def test_auroc_perfect_separation():
    y = np.array([0, 0, 1, 1])
    s = np.array([1.0, 2.0, 3.0, 4.0])
    assert stats.auroc(y, s) == 1.0
    assert stats.auroc(y, -s) == 0.0


def test_auroc_ci_brackets_point():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 300)
    s = y + rng.normal(0, 1, 300)
    e = stats.auroc_ci(y, s, n_boot=500)
    assert e.lo <= e.point <= e.hi
    assert 0.5 < e.point <= 1.0


def test_auroc_pvalue_significant_when_separated():
    y = np.r_[np.zeros(50), np.ones(50)].astype(int)
    s = np.r_[np.zeros(50), np.ones(50)] + np.random.default_rng(1).normal(0, 0.3, 100)
    assert stats.auroc_pvalue(y, s) < 0.01


# --------------------------------------------------------------------------- effect sizes
def test_cohens_d_sign_and_zero():
    a = np.array([0.0, 1, 2, 3, 4])
    b = a + 5
    assert stats.cohens_d(a, b) > 0
    assert abs(stats.cohens_d(a, a)) < 1e-9


def test_cliffs_delta_bounds():
    a = np.arange(20).astype(float)
    b = np.arange(20).astype(float) + 100
    assert pytest.approx(stats.cliffs_delta(a, b), abs=1e-6) == 1.0
    assert -1.0 <= stats.cliffs_delta(b, a) <= 1.0


# --------------------------------------------------------------------------- trend
def test_jonckheere_detects_monotone_trend():
    rng = np.random.default_rng(2)
    vals = np.concatenate([rng.normal(m, 1, 30) for m in (0, 1, 2, 3)])
    ranks = np.repeat([0, 1, 2, 3], 30)
    res = stats.jonckheere_trend(vals, ranks, n_perm=400)
    assert res.p_permutation < 0.01
    assert res.spearman_rho > 0.4


def test_jonckheere_null_not_significant():
    rng = np.random.default_rng(3)
    vals = rng.normal(0, 1, 120)
    ranks = np.repeat([0, 1, 2, 3], 30)
    res = stats.jonckheere_trend(vals, ranks, n_perm=400)
    assert res.p_permutation > 0.05


# --------------------------------------------------------------------------- ordinal (Phase 2)
def test_adjacent_boundary_aurocs_separated_four_tier():
    """On clearly separated per-tier score distributions every adjacent
    boundary discriminates (>0.5), the CI brackets the point, and the boundary
    names follow the 4-tier ladder in order."""
    rng = np.random.default_rng(12)
    tiers = ("reject", "poster", "spotlight", "oral")
    means = {"reject": 0.0, "poster": 2.0, "spotlight": 4.0, "oral": 6.0}
    ns = {"reject": 60, "poster": 40, "spotlight": 25, "oral": 20}
    score = np.concatenate([rng.normal(means[t], 0.8, ns[t]) for t in tiers])
    dt = np.concatenate([np.full(ns[t], t) for t in tiers])
    out = stats.adjacent_boundary_aurocs(score, dt, tiers, n_boot=300)
    assert list(out) == ["reject|poster", "poster|spotlight", "spotlight|oral"]
    expected_n = {"reject|poster": 100, "poster|spotlight": 65, "spotlight|oral": 45}
    for name, e in out.items():
        assert e["lo"] <= e["point"] <= e["hi"]
        assert e["point"] > 0.5
        assert e["n"] == expected_n[name]


def test_adjacent_boundary_aurocs_skips_empty_tier():
    # an empty tier makes its boundaries degenerate -> they are skipped, not 0.5
    tiers = ("reject", "poster", "spotlight", "oral")
    dt = np.array(["reject"] * 5 + ["poster"] * 5 + ["oral"] * 5)  # no spotlight
    score = np.arange(15, dtype=float)
    out = stats.adjacent_boundary_aurocs(score, dt, tiers, n_boot=100)
    assert list(out) == ["reject|poster"]


def test_per_tier_summary_monotone_and_violation():
    tiers = ("reject", "poster", "spotlight", "oral")
    dt = np.array(["reject"] * 4 + ["poster"] * 4 + ["spotlight"] * 4 + ["oral"] * 4)
    inc = np.concatenate([np.full(4, v) for v in (10.0, 20.0, 30.0, 40.0)])
    out = stats.per_tier_summary(inc, dt, tiers)
    assert out["monotone"] is True
    assert [out["tiers"][t]["median"] for t in tiers] == [10.0, 20.0, 30.0, 40.0]
    assert all(out["tiers"][t]["n"] == 4 for t in tiers)
    # a dip at spotlight breaks monotonicity
    dec = np.concatenate([np.full(4, v) for v in (10.0, 30.0, 20.0, 40.0)])
    out2 = stats.per_tier_summary(dec, dt, tiers)
    assert out2["monotone"] is False


# --------------------------------------------------------------------------- proportions / bands
def test_wilson_interval_sane():
    lo, hi = stats.wilson_interval(5, 10)
    assert 0 <= lo < 0.5 < hi <= 1
    assert stats.wilson_interval(0, 0) == (0.0, 0.0)


def test_score_band_lift_monotone_data():
    rng = np.random.default_rng(4)
    n = 500
    q = rng.normal(0, 1, n)
    score = 60 + 13 * q
    accept = (q > 0).astype(int)  # high score => accept
    rank = accept * 2
    bands = stats.score_band_table(score, accept, rank, n_bins=5, seed=0)
    # bottom band rejects far more than top band
    assert bands[0].reject_rate > bands[-1].reject_rate
    assert bands[0].lift > 1.0
    # lift CI brackets the point and (here) clears the pre-registered rule
    lo, hi = bands[0].lift_ci
    assert lo <= bands[0].lift <= hi
    assert lo > 1.0


def test_score_band_oral_rate_uses_oral_rank():
    # Regression for the ==3 vs ==2 bug: the band oral-rate must count
    # tier_rank == TIER_RANK["oral"] (==2), never a literal 3 (which made every
    # band's oral rate structurally 0 and zeroed Table 3 + \bottomOralRate).
    score = np.arange(10, dtype=float)  # 0..9, strictly increasing => deterministic bands
    rank = np.array([0, 0, 1, 0, 1, 2, 1, 2, 2, 2], int)  # orals all in the top half
    accept = (rank >= 1).astype(int)
    bands = stats.score_band_table(score, accept, rank, n_bins=2, seed=0)
    # bottom band = scores 0..4 (ranks 0,0,1,0,1) -> no oral
    assert bands[0].oral_rate == 0.0
    # top band = scores 5..9 (ranks 2,1,2,2,2) -> 4 oral / 5; posters must NOT count
    assert bands[-1].oral_rate == 4 / 5


def test_low_score_harm_counts_opposite_conditional():
    # Low-score harm = accepted/oral work in the bottom band (the opposite
    # conditional to reject precision). Deterministic 10-paper frame.
    score = np.arange(10, dtype=float)  # quantile(.,0.2) = 1.8 -> bottom = {score 0, 1}
    rank = np.array([0, 2, 0, 1, 0, 1, 2, 2, 1, 2], int)
    accept = (rank >= 1).astype(int)
    h = stats.low_score_harm(score, accept, rank, q=0.2)
    assert h.n_bottom == 2
    assert h.oral_in_bottom == 1 and h.accepted_in_bottom == 1  # score 1 is an oral
    assert h.n_oral == 4 and h.n_accepted == 7
    assert h.p_low_given_oral == 1 / 4
    assert h.p_low_given_accepted == 1 / 7


def test_band_lift_ci_brackets_and_orders():
    rng = np.random.default_rng(11)
    q = rng.normal(0, 1, 600)
    score = 60 + 13 * q
    accept = (q > 0).astype(int)
    point, lo, hi = stats.band_lift_ci(score, accept, n_bins=5, b=0, n_boot=500, seed=1)
    assert lo <= point <= hi


def test_stratified_resample_preserves_class_counts():
    rng = np.random.default_rng(5)
    strata = np.r_[np.zeros(40), np.ones(10)].astype(int)
    idx = stats._strata_resample(rng, strata)
    drawn = strata[idx]
    assert (drawn == 0).sum() == 40 and (drawn == 1).sum() == 10


def test_quantile_overlap_identical_is_one():
    x = np.arange(100).astype(float)
    ov = stats.quantile_membership_overlap(x, x.copy(), q=0.2)
    assert ov["recall"] == 1.0 and ov["jaccard"] == 1.0


def test_low_band_spearman_runs():
    rng = np.random.default_rng(6)
    a = rng.normal(0, 1, 200)
    b = a + rng.normal(0, 0.3, 200)
    e = stats.low_band_spearman(a, b, q=0.2, n_boot=300)
    assert e.lo <= e.point <= e.hi


def test_prevalence_reweight_matches_balanced_at_equal_prevalence():
    rng = np.random.default_rng(7)
    q = rng.normal(0, 1, 800)
    score = 60 + 13 * q
    accept = (q > 0).astype(int)
    # at the sample's own accept prevalence, reweighting is a no-op on the base rate
    p_acc = float(accept.mean())
    out = stats.prevalence_reweighted_bottom_precision(score, accept, 0.2, p_acc)
    assert abs(out["base_reject_rate"] - (1 - p_acc)) < 1e-9
    # a low score is a high-precision reject flag
    assert out["bottom_reject_precision"] > 0.8


# --------------------------------------------------------------------------- BH
def _synthetic_covariate_frame(n: int = 200, seed: int = 20260601):
    """Seeded synthetic frame carrying the columns the two descriptive checks read:
    an AIPR ``overall`` that genuinely predicts ``accept_bool``, plus area + the
    manuscript-surface covariates and the reviewer rating / tier columns."""
    import pandas as pd

    rng = np.random.default_rng(seed)
    q = rng.normal(0, 1, n)  # latent quality
    overall = 60 + 12 * q + rng.normal(0, 4, n)
    accept = (q + rng.normal(0, 0.5, n) > 0).astype(int)
    rating = 5 + 1.5 * q + rng.normal(0, 1, n)
    tier_rank = np.where(accept == 0, 0, rng.integers(1, 3, n))  # reject=0, poster=1, oral=2
    return pd.DataFrame(
        {
            "accept_bool": accept,
            "overall": overall,
            "mean_reviewer_rating": rating,
            "tier_rank": tier_rank,
            "primary_area": rng.choice(["A", "B", "C"], n),
            "page_count": rng.integers(8, 12, n),
            "word_count": rng.integers(6000, 12000, n),
            "n_references": rng.integers(20, 60, n),
            "n_figures": rng.integers(2, 8, n),
            "rating_std": np.abs(rng.normal(1.0, 0.3, n)),
            "n_reviews": rng.integers(3, 6, n),
        }
    )


def test_covariate_control_auc_finite_and_bounded():
    frame = _synthetic_covariate_frame()
    out = stats.covariate_control_auc(frame)
    for k in ("cv_auc_covariate", "cv_auc_score_only"):
        assert np.isfinite(out[k])
        assert 0.0 <= out[k] <= 1.0
    assert out["n"] == len(frame)
    # determinism: same seed/protocol -> identical AUROCs
    out2 = stats.covariate_control_auc(frame)
    assert out["cv_auc_covariate"] == out2["cv_auc_covariate"]
    # a score that genuinely predicts the outcome discriminates above chance
    assert out["cv_auc_score_only"] > 0.5


def test_within_tier_spearman_bounded():
    frame = _synthetic_covariate_frame()
    out = stats.within_tier_spearman(frame)
    assert set(out) == {"reject", "poster", "oral", "accepted"}
    for sub in out.values():
        assert sub["n"] >= 0
        rho = sub["rho"]
        assert (rho != rho) or (-1.0 <= rho <= 1.0)  # nan or in [-1, 1]


def test_within_tier_spearman_guards_tiny_subgroup():
    import pandas as pd

    # one oral, two posters, rest reject -> oral subgroup has n<3 -> rho nan
    n = 20
    tier_rank = np.array([2, 1, 1] + [0] * (n - 3))
    accept = (tier_rank >= 1).astype(int)
    frame = pd.DataFrame(
        {
            "accept_bool": accept,
            "overall": np.arange(n, dtype=float),
            "mean_reviewer_rating": np.arange(n, dtype=float),
            "tier_rank": tier_rank,
        }
    )
    out = stats.within_tier_spearman(frame)
    assert out["oral"]["n"] == 1 and np.isnan(out["oral"]["rho"])


# --------------------------------------------------------------------------- loop 07
def test_bottom_band_sensitivity_definitions_and_lift():
    frame = _synthetic_covariate_frame(n=300)
    out = stats.bottom_band_sensitivity(
        frame["overall"].values, frame["accept_bool"].values, frame["tier_rank"].values,
        sub_order=np.arange(len(frame)), bottom_k=60,
    )
    labels = [r["label"] for r in out]
    assert labels == ["strict quintile", "bottom-60", "score<=63", "score<=64", "score<=65"]
    bk = next(r for r in out if r["label"] == "bottom-60")
    assert bk["n"] == 60  # deterministic bottom-K picks exactly K
    for r in out:
        assert 0.0 <= r["reject_rate"] <= 1.0
        assert 0.0 <= r["oral_rate"] <= 1.0
        assert (r["lift"] != r["lift"]) or r["lift"] >= 0.0
    # the low band's reject rate exceeds the cohort base reject rate (lift > 1)
    base = float((frame["accept_bool"].values == 0).mean())
    assert out[0]["reject_rate"] > base


def test_bottom_band_sensitivity_tiebreak_deterministic():
    # all-tied scores: bottom-K must resolve purely by sub_order, reproducibly
    n = 20
    score = np.full(n, 64.0)
    accept = np.zeros(n, int)
    tier = np.zeros(n, int)
    order = np.arange(n)[::-1]  # reverse submission order
    out = stats.bottom_band_sensitivity(score, accept, tier, sub_order=order, bottom_k=5)
    bk = next(r for r in out if r["label"] == "bottom-5")
    assert bk["n"] == 5
    out2 = stats.bottom_band_sensitivity(score, accept, tier, sub_order=order, bottom_k=5)
    assert [r["n"] for r in out] == [r["n"] for r in out2]


def test_disagreement_moderation_shape_and_bounds():
    frame = _synthetic_covariate_frame(n=300)
    out = stats.disagreement_moderation(frame)
    assert -1.0 <= out["rho_resid_std"] <= 1.0
    for k in ("auroc_low_std", "auroc_high_std"):
        assert (out[k] != out[k]) or (0.0 <= out[k] <= 1.0)
    assert out["n_low"] + out["n_high"] == out["n"] == len(frame)


def test_area_subgroup_audit_pools_small_and_covers_all():
    import pandas as pd

    rng = np.random.default_rng(7)
    n = 120
    # two big areas + a scatter of tiny ones
    area = np.array(["A"] * 50 + ["B"] * 50 + ["x1", "x2", "x3", "x4", "x5"] * 4)
    q = rng.normal(0, 1, n)
    frame = pd.DataFrame(
        {
            "primary_area": area,
            "overall": 60 + 10 * q + rng.normal(0, 4, n),
            "mean_reviewer_rating": 5 + q,
            "accept_bool": (q > 0).astype(int),
        }
    )
    out = stats.area_subgroup_audit(frame, min_n=8)
    areas = [r["area"] for r in out]
    assert "A" in areas and "B" in areas and "other" in areas
    # every submission is accounted for across the rows (pooling drops none)
    assert sum(r["n"] for r in out) == n
    # big areas sorted before the pooled row
    assert areas[-1] == "other"
    for r in out:
        assert 0.0 <= r["accept_rate"] <= 1.0
        assert (r["auroc"] != r["auroc"]) or (0.0 <= r["auroc"] <= 1.0)


def test_population_boundary_counts_sum_and_nonneg():
    import pandas as pd

    in_pop = pd.DataFrame({"submission_id": [f"s{i}" for i in range(30)]})
    out_of_pop = pd.DataFrame(
        {
            "submission_id": [f"x{i}" for i in range(12)],
            "exclude_reason": ["withdrawn"] * 8 + ["desk_rejected"] * 4,
        }
    )
    pbd = stats.population_boundary(in_pop, out_of_pop, n_graded=10)
    assert pbd["n_in_population"] == 30
    assert pbd["n_excluded"] == 12
    # the graded sample is drawn from (and never exceeds) the in-population set
    assert pbd["n_graded"] == 10
    assert pbd["n_graded"] <= pbd["n_in_population"]
    # eligible = in-population + excluded, every eligible submission accounted for
    assert pbd["n_eligible"] == pbd["n_in_population"] + pbd["n_excluded"]
    # n_graded defaults to the in-population size when not supplied
    assert stats.population_boundary(in_pop, out_of_pop)["n_graded"] == 30
    # per-reason breakdown sums back to the excluded total and is non-negative
    assert sum(r["n"] for r in pbd["by_reason"]) == pbd["n_excluded"]
    assert all(r["n"] >= 0 for r in pbd["by_reason"])
    assert all(0.0 <= r["share"] <= 1.0 for r in pbd["by_reason"])
    assert abs(sum(r["share"] for r in pbd["by_reason"]) - 1.0) < 1e-9
    # sorted by descending count; reasons are distinct
    counts = [r["n"] for r in pbd["by_reason"]]
    assert counts == sorted(counts, reverse=True)
    assert len({r["reason"] for r in pbd["by_reason"]}) == len(pbd["by_reason"])
    # absent ledger -> empty dict so downstream consumers self-skip
    assert stats.population_boundary(in_pop, None) == {}


def test_paired_run_sd_test_detects_known_direction():
    # one grader consistently noisier on the same papers -> small exact p
    rng = np.random.default_rng(8)
    sd_full = rng.uniform(0.3, 1.5, 12)
    sd_naive = sd_full + rng.uniform(1.0, 3.0, 12)
    out = stats.paired_run_sd_test(sd_full, sd_naive)
    assert out["n"] == 12
    assert out["p"] < 0.01


def test_paired_run_sd_test_symmetric_is_not_significant():
    # differences symmetric around zero (distinct magnitudes) -> large p
    a = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
    d = np.array([0.9, -1.1, 1.3, -1.5, 1.7, -1.9, 2.1, -2.3])
    out = stats.paired_run_sd_test(a, a + d)
    assert out["n"] == 8
    assert out["p"] > 0.5


def test_paired_run_sd_test_drops_incomplete_pairs():
    a = np.array([1.0, 2.0, np.nan, 4.0, 5.0, 6.0, 7.0])
    b = a + 1.0
    out = stats.paired_run_sd_test(a, b)
    assert out["n"] == 6  # the nan pair is dropped, not imputed


# --------------------------------------------------------------------------- V1 post-hoc power
def test_v1_delong_paired_p_null_and_separated():
    import simulation

    # identical scores: degenerate variance -> p = 1 (never spuriously significant)
    y = np.r_[np.zeros(50), np.ones(50)].astype(int)
    s = np.random.default_rng(9).normal(0, 1, 100)
    assert simulation._delong_paired_p(y, s, s.copy()) == 1.0
    # one score separates perfectly, the other is pure noise -> small p
    strong = y + np.random.default_rng(10).normal(0, 0.1, 100)
    assert simulation._delong_paired_p(y, strong, s) < 0.01


def test_v1_power_monotone_in_true_gap():
    import simulation

    out = simulation.v1_power_grid(
        n_sim=80, seed=0, fracs=(1.0, 0.6, 0.3), n_pop=80_000
    )
    g = out["grid"]
    gaps = [r["true_gap"] for r in g]
    assert gaps == sorted(gaps)  # shrinking pipeline noise raises the true gap
    assert g[0]["true_gap"] < 0.01  # equal-noise configuration is the null
    assert g[0]["power"] < 0.3  # ~alpha at the null
    assert g[-1]["power"] > g[0]["power"]  # power rises with the gap
    assert g[-1]["power"] > 0.7  # a large gap is detected


def test_v1_mde_picks_smallest_grid_gap_reaching_target():
    import simulation

    grid = [
        {"true_gap": 0.02, "power": 0.10},
        {"true_gap": 0.12, "power": 0.92},
        {"true_gap": 0.08, "power": 0.85},
    ]
    assert simulation.v1_mde(grid) == 0.08
    assert simulation.v1_mde([{"true_gap": 0.05, "power": 0.4}]) is None


def test_benjamini_hochberg_known_case():
    out = stats.benjamini_hochberg({"a": 0.001, "b": 0.04, "c": 0.5, "d": 0.9}, alpha=0.05)
    assert out["a"]["significant"]
    assert not out["c"]["significant"]
    for v in out.values():
        assert 0 <= v["q"] <= 1


# --------------------------------------------------------------------------- determinism
def test_secondary_correctness_axis():
    import secondary

    R = secondary.compute(secondary.generate())
    src = R["sources"]
    # rates are valid proportions with CIs bracketing the point
    for s in secondary.SOURCES:
        for k in secondary.THEIR_KEYS + secondary.OUR_KEYS:
            m = src[s][k]
            assert 0.0 <= m["lo"] <= m["rate"] <= m["hi"] <= 1.0
    # the study's point: AIPR leads the correctness axis ReviewBench omits...
    assert src["aipr"]["citation_grounded"]["rate"] > src["r3"]["citation_grounded"]["rate"]
    assert src["aipr"]["correctness"]["rate"] > src["r3"]["correctness"]["rate"]
    assert src["aipr"]["anchor_fidelity"]["rate"] > src["r3"]["anchor_fidelity"]["rate"]
    # ...while R3 can still lead the intent metric (consequential rate)
    assert src["r3"]["consequential"]["rate"] >= src["aipr"]["consequential"]["rate"]


def test_pipeline_determinism():
    import run_all

    d = schema.load_dataset("synthetic")
    r1 = run_all.compute(d)
    r2 = run_all.compute(d)
    assert r1[run_all.PRIMARY_CONFIG]["auroc"]["point"] == r2[run_all.PRIMARY_CONFIG]["auroc"]["point"]
    assert r1["bottom_band"]["lift"] == r2["bottom_band"]["lift"]
    assert r1["null_control"]["passes"]


def test_new_analyses_present_and_sane():
    import run_all

    d = schema.load_dataset("synthetic")
    R = run_all.compute(d)
    # low-end bridge
    assert "low_band_spearman" in R["bridge"] and "bottom_overlap" in R["bridge"]
    assert 0.0 <= R["bridge"]["bottom_overlap"]["recall"] <= 1.0
    # natural-prevalence point
    pp = R["prevalence_point"]
    assert pp["nat_accept_rate"] == run_all.NAT_ACCEPT_RATE
    assert 0.0 <= pp["bottom_reject_precision"] <= 1.0
    # weighting robustness — equal-weight ranks like deployed; LOO all discriminate
    wr = R["weight_robustness"]
    assert wr["equal_weight"]["rho_vs_deployed"] > 0.8
    assert all(wr["leave_one_out"][dim]["auroc"]["point"] > 0.5 for dim in run_all.DIMENSIONS)
    # contamination — temporal controls: clean primary cohort, the pre-cutoff
    # replication venue (contaminated contrast), and the arXiv-excluded primary
    # cohort are all present and comparable; the clean cohort is not driven by
    # memorization (synthetic: signal is identical across cohorts by construction)
    bars = R["contamination"]["bars"]
    # all three bars present: synth.py now emits the ICLR-2025 venue (the
    # Phase-2 4-tier arm), so the replication bar no longer self-skips.
    assert {"primary", "replication", "arxiv_no_prior"} <= set(bars)
    for k in bars:
        assert 0.5 < bars[k]["auroc"]["point"] <= 1.0
    assert "auroc_no_prior" in R["contamination"]["arxiv_split"]
    # length confounding — weak by construction (length independent of quality)
    lc = R["length_confound"]
    assert "page_count" in lc and abs(lc["page_count"]["point"]) < 0.3
    # grading cost — frontier full uses more tokens than the cheap full-mini
    cost = R["cost"]
    assert {"full_mini", "full"} <= set(cost)
    assert cost["full"]["total"] > cost["full_mini"]["total"]
    # naive-judge baseline — AIPR wins on discrimination, operating point, and
    # reliability (synthetic by design; verifies the comparison machinery)
    nb = R["naive_baseline"]
    assert nb["auroc_full"]["point"] > nb["auroc_naive"]["point"]
    assert nb["op_at60"]["full"]["balanced_accuracy"] > nb["op_at60"]["naive"]["balanced_accuracy"]
    assert nb["reliability"]["full_median_sd"] < nb["reliability"]["naive_median_sd"]
    # paired within-paper SD test wired (exact Wilcoxon over the variance papers)
    pw = nb["reliability"].get("paired_sd_test")
    if pw is not None:  # present whenever both configs carry re-runs on shared papers
        assert 0.0 <= pw["p"] <= 1.0 and pw["n"] >= 1
    # both graders scored at a fair matched accept-rate operating point too
    assert "op_matched" in nb and "full" in nb["op_matched"] and "naive" in nb["op_matched"]
    # loop 07 descriptive checks present and sane
    bbs = R["bottom_band_sensitivity"]
    assert [r["label"] for r in bbs][:2] == ["strict quintile", "bottom-60"]
    dm = R["disagreement_moderation"]
    assert {"mini", "full"} <= set(dm)
    for key in ("mini", "full"):
        assert -1.0 <= dm[key]["rho_resid_std"] <= 1.0
    asg = R["area_subgroup"]
    assert asg and sum(r["n"] for r in asg) == len(_primary_frame(d))
    # Phase-2 (ICLR 2025) ordinal block — present on the synthetic 4-tier arm
    # and sane: the ladder is the 4-tier one, the score tracks the tier rank,
    # all three adjacent boundaries are computed, and the per-tier medians are
    # monotone (the spotlight latent mean sits between poster and oral by
    # construction).
    p2 = R["phase2"]
    assert p2["tier_order"] == ["reject", "poster", "spotlight", "oral"]
    assert p2["spearman_tier"]["point"] > 0
    assert set(p2["boundary_aurocs"]) == {"reject|poster", "poster|spotlight", "spotlight|oral"}
    assert p2["per_tier"]["monotone"] is True
    assert p2["n"] == sum(p2["per_tier"]["tiers"][t]["n"] for t in p2["tier_order"])
    # Pillar-1 new-validation block: the post-fix citation audit beats the
    # frozen v1 artifact row (chance AUROC, pinned 100%) on synthetic data
    p1 = R["pillar1_p2"]
    assert p1["citation_auroc"]["point"] > p1["frozen_v1"]["auroc"]
    assert p1["pinned_rate"] < p1["frozen_v1"]["pinned_rate"]


def _primary_frame(d):
    import run_all

    return run_all._primary(d.config_frame(run_all.PRIMARY_CONFIG))
