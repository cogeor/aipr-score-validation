"""Load + validate the two-CSV data contract (see DATA_SCHEMA.md).

`load_dataset(name)` returns a `Dataset` bundle with the validated submissions
and gradings frames plus convenience accessors used everywhere downstream. All
contract invariants are asserted here so no figure or number can render from
malformed input.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from common import ALL_CONFIGS, CONFIGS, DATA_DIR, DIMENSIONS, TIER_ORDER, TIER_RANK

# The model-output scores carried per grading row. Confidence is intentionally
# absent: the v6 pipeline currently emits a constant confidence, so exporting it
# would be a contract lie (the producer drops it; the confidence-conditioned
# reliability analysis is removed until a real signal exists).
SCORE_COLS = ("overall", *DIMENSIONS)

# Required columns by table. Presence is checked first, with a clear error, so a
# malformed real export fails loudly instead of aggregating/duplicating silently.
REQUIRED_SUB_COLS = (
    "submission_id", "venue", "year", "decision_raw", "decision_tier",
    "tier_rank", "accept_bool", "mean_reviewer_rating", "rating_std",
    "n_reviews", "stratum", "excluded", "exclude_reason",
)
REQUIRED_GRAD_COLS = (
    "submission_id", "config", "run_index", "model_name", "pipeline_version",
    *SCORE_COLS, "run_kind",
)
# Manuscript-surface + provenance metadata. Optional for the primary hypotheses,
# required for the confounding/contamination checks (area, length, arXiv-split).
# Defaults are filled when a column is absent so older exports still load, but the
# synthetic generator emits all of them.
# page_count/word_count/token_count are manuscript-LENGTH metrics (length
# confounding, #11); the grading-side token usage lives in gradings.csv.
METADATA_COLS = ("primary_area", "page_count", "word_count", "token_count",
                 "n_references", "n_figures", "arxiv_prior_to_cutoff",
                 "is_anonymized", "pdf_sha")
# Tokens the grading run CONSUMED ("tokens used"): prompt/input and generated
# output. Optional (older exports lack them); backfilled to NaN. They quantify
# the cost-design story (full-mini vs full).
GRADING_USAGE_COLS = ("input_tokens", "output_tokens")


@dataclass
class Dataset:
    name: str
    is_synthetic: bool
    submissions: pd.DataFrame  # one row per submission
    gradings: pd.DataFrame  # one row per (submission, config, run_index)

    # ---- convenience accessors -------------------------------------------
    def config_frame(self, config: str, *, include_excluded: bool = False) -> pd.DataFrame:
        """Submissions joined with their mean grading for `config`.

        Multiple run_index rows per (submission, config) are averaged for point
        estimates. Excluded submissions are dropped unless requested.
        """
        g = self.gradings[self.gradings["config"] == config]
        agg = {c: "mean" for c in SCORE_COLS}
        gmean = g.groupby("submission_id", as_index=False).agg(agg)
        merged = self.submissions.merge(gmean, on="submission_id", how="inner")
        if not include_excluded:
            merged = merged[merged["excluded"] == 0]
        return merged.reset_index(drop=True)

    def paired_frame(self, config_a: str, config_b: str) -> pd.DataFrame:
        """Submissions graded by BOTH configs (for the mini<->frontier bridge)."""
        a = self.config_frame(config_a)[["submission_id", "overall", *DIMENSIONS]]
        b = self.config_frame(config_b)[["submission_id", "overall", *DIMENSIONS]]
        return a.merge(b, on="submission_id", suffixes=(f"_{config_a}", f"_{config_b}"))

    def run_variance(self, config: str) -> pd.DataFrame:
        """Per-submission within-config SD of `overall` (run-to-run noise)."""
        g = self.gradings[self.gradings["config"] == config]
        return (
            g.groupby("submission_id")["overall"]
            .agg(["mean", "std", "count"])
            .reset_index()
            .rename(columns={"std": "run_sd", "count": "n_runs"})
        )

    def cohort_counts(self) -> dict:
        out = {}
        for c in CONFIGS:
            ids = set(self.gradings.loc[self.gradings["config"] == c, "submission_id"])
            out[c] = len(ids)
        return out


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"missing required file: {path}")
    return pd.read_csv(path)


def validate(subs: pd.DataFrame, grad: pd.DataFrame, *, require_metadata: bool = False) -> None:
    """Assert every DATA_SCHEMA.md invariant. Raises on the first violation.

    Hardened for real exports: required columns
    are checked first with a clear message, then keys/uniqueness, then the
    semantic invariants. ``require_metadata`` additionally enforces the
    confounding/leakage metadata columns (the synthetic generator always emits
    them; an older export missing them gets defaults filled in ``load_dataset``).
    """
    # 0. required columns present (clear error before anything else touches them)
    miss_s = [c for c in REQUIRED_SUB_COLS if c not in subs.columns]
    miss_g = [c for c in REQUIRED_GRAD_COLS if c not in grad.columns]
    assert not miss_s, f"submissions.csv missing required columns: {miss_s}"
    assert not miss_g, f"gradings.csv missing required columns: {miss_g}"
    if require_metadata:
        miss_m = [c for c in METADATA_COLS if c not in subs.columns]
        assert not miss_m, f"submissions.csv missing metadata columns: {miss_m}"

    # 1. one row per submission_id; (submission_id, config, run_index) unique
    dup_s = subs["submission_id"][subs["submission_id"].duplicated()].tolist()
    assert not dup_s, f"duplicate submission_id in submissions: {dup_s[:5]}"
    gkey = grad[["submission_id", "config", "run_index"]]
    dup_g = gkey[gkey.duplicated()]
    assert dup_g.empty, f"duplicate (submission_id, config, run_index): {dup_g.head().to_dict('records')}"

    # 2. tier_rank <-> decision_tier bijection + accept_bool consistency
    bad = subs[subs.apply(lambda r: TIER_RANK.get(r["decision_tier"]) != r["tier_rank"], axis=1)]
    assert bad.empty, f"tier_rank/decision_tier mismatch on {bad['submission_id'].tolist()[:5]}"
    assert ((subs["accept_bool"] == (subs["tier_rank"] >= 1).astype(int)).all()), (
        "accept_bool != (tier_rank>=1)"
    )
    assert set(subs["decision_tier"]).issubset(set(TIER_ORDER)), "unknown decision_tier value"

    # 3. decision_raw present for every row (lets a third party re-derive the tier)
    assert (subs["decision_raw"].fillna("").str.len() > 0).all(), "decision_raw empty on some rows"

    # 4. n_reviews >= 1
    assert (subs["n_reviews"].astype(int) >= 1).all(), "n_reviews must be >= 1"

    # 5. pipeline version. AIPR grades are uniform v6; the naive baseline carries
    #    its own marker ("naive") — it is a single prompt, NOT the v6 pipeline, so
    #    labeling it v6 would imply a pipeline it never ran (cf. the dropped
    #    confidence column: a name must not claim more than the value delivers).
    nonnaive_vers = set(grad.loc[grad["config"] != "naive", "pipeline_version"].unique())
    assert nonnaive_vers == {"v6"}, f"non-naive pipeline_version must be uniform v6, got {nonnaive_vers}"
    naive_vers = set(grad.loc[grad["config"] == "naive", "pipeline_version"].unique())
    assert naive_vers <= {"naive"}, f"naive pipeline_version must be 'naive', got {naive_vers}"

    # 6. config values restricted; run_index a nonnegative integer
    bad_cfg = set(grad["config"].unique()) - set(ALL_CONFIGS)
    assert not bad_cfg, f"unknown config value(s): {bad_cfg}"
    ri = grad["run_index"]
    assert (ri.astype(int) == ri).all() and (ri >= 0).all(), "run_index must be a nonnegative integer"

    # 7. score ranges. `overall` is mandatory on every grading row; the five
    #    subscores may be NaN ONLY for the naive baseline (a one-paragraph judge
    #    produces a single overall grade, not five calibrated subscores — emitting
    #    fabricated subscores would be a contract lie). Range-check non-null only.
    assert grad["overall"].notna().all(), "overall must be present on every grading row"
    nonnaive = grad[grad["config"] != "naive"]
    for c in DIMENSIONS:
        assert nonnaive[c].notna().all(), f"{c} missing on a non-naive grading row"
    for c in SCORE_COLS:
        col = grad[c].dropna()
        assert col.between(0, 100).all(), f"{c} out of [0,100]"

    # 8. referential integrity
    missing = set(grad["submission_id"]) - set(subs["submission_id"])
    assert not missing, f"gradings reference unknown submissions: {list(missing)[:5]}"

    # 9. cohort nesting H subset M (cost ladder only; the naive baseline is
    #    exempt — it is an extra grading on cohort H, not part of the ladder)
    ids = {c: set(grad.loc[grad["config"] == c, "submission_id"]) for c in CONFIGS}
    assert ids["full"] <= ids["full_mini"], "cohort H (full) not subset of M (full_mini)"
    # the naive baseline is graded on the H cohort (paired with a full-text score)
    for lc in ("naive",):
        lc_ids = set(grad.loc[grad["config"] == lc, "submission_id"])
        assert lc_ids <= ids["full"], f"{lc} gradings must be a subset of cohort H"

    # 10. exclusion reasons present
    exc = subs[subs["excluded"] == 1]
    assert (exc["exclude_reason"].fillna("").str.len() > 0).all(), "excluded row missing reason"

    # 11. run_kind discipline
    assert set(grad["run_kind"].unique()) <= {"adhoc"}, "study grades must be run_kind=adhoc"

    # 12. metadata domains (only when present)
    for c in ("arxiv_prior_to_cutoff", "is_anonymized"):
        if c in subs.columns:
            assert set(subs[c].dropna().unique()) <= {0, 1}, f"{c} must be 0/1"
    for c in ("page_count", "word_count", "token_count", "n_references", "n_figures"):
        if c in subs.columns:
            assert (subs[c].dropna() >= 0).all(), f"{c} must be nonnegative"
    for c in GRADING_USAGE_COLS:
        if c in grad.columns:
            assert (grad[c].dropna() >= 0).all(), f"{c} must be nonnegative"

    # both decision classes present (else AUROC undefined)
    assert subs["accept_bool"].nunique() == 2, "need both accept and reject present"


def _fill_metadata_defaults(subs: pd.DataFrame, grad: pd.DataFrame) -> None:
    """Backfill optional metadata columns so an export predating them still loads.
    Confounding/cost checks that need a column self-skip when it is all-NaN.
    Mutates both frames in place."""
    sub_defaults = {
        "primary_area": "", "page_count": np.nan, "word_count": np.nan,
        "token_count": np.nan, "n_references": np.nan, "n_figures": np.nan,
        "arxiv_prior_to_cutoff": np.nan, "is_anonymized": np.nan, "pdf_sha": "",
    }
    for c, default in sub_defaults.items():
        if c not in subs.columns:
            subs[c] = default
    for c in GRADING_USAGE_COLS:
        if c not in grad.columns:
            grad[c] = np.nan


def load_dataset(name: str) -> Dataset:
    base = DATA_DIR / name
    subs = _read_csv(base / "submissions.csv")
    grad = _read_csv(base / "gradings.csv")
    validate(subs, grad)
    _fill_metadata_defaults(subs, grad)
    is_synth = name == "synthetic" or bool(grad["model_name"].str.contains("synthetic").any())
    return Dataset(name=name, is_synthetic=is_synth, submissions=subs, gradings=grad)


def base_reject_rate(subs: pd.DataFrame) -> float:
    keep = subs[subs["excluded"] == 0]
    return float((keep["accept_bool"] == 0).mean())
