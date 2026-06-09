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
    # the dropped leakage configs must not reappear in the export
    assert not ({"blinded", "prior_only"} & configs)
    # the naive baseline is graded on the H cohort only
    h_ids = set(d.gradings.loc[d.gradings["config"] == "full", "submission_id"])
    for lc in ("naive",):
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
    # replication ("ICLR 2025") self-skips on the 2026-only synthetic cohort
    # (synth.py defers the 2025 venue; _contamination omits it when absent).
    assert {"primary", "arxiv_no_prior"} <= set(bars)
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
    # both graders scored at a fair matched accept-rate operating point too
    assert "op_matched" in nb and "full" in nb["op_matched"] and "naive" in nb["op_matched"]
