"""Statistical primitives for the score-validation study.

Everything that produces a number in the paper lives here, so the analysis is
auditable in one file. Design choices made for defensibility:

* Confidence intervals are 95% bias-corrected and accelerated (BCa) bootstraps by
  default (percentile available as a fallback), seeded for exact reproducibility.
  AUROC and other class-conditional statistics use a STRATIFIED resample that
  preserves the per-class counts of the observed sample.
* The trend test across ordered decision tiers is Jonckheere-Terpstra with a
  MONTE CARLO permutation p-value (assumption-light: ``n_perm`` random label
  shuffles plus the observed, with the +1 correction so p>0). Exact enumeration
  is infeasible at these sample sizes; the Monte Carlo p-value is unbiased and
  its resolution is bounded by ``1/(n_perm+1)``. Reported alongside the Spearman
  effect size; no reliance on the normal approximation.
* Effect sizes (Cohen's d, Cliff's delta, AUROC, Spearman rho) accompany every
  significance statement, because "strong signal" is an effect-size claim.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from common import GLOBAL_SEED, TIER_RANK


# ----------------------------------------------------------------------------
# Generic bootstrap
# ----------------------------------------------------------------------------
@dataclass
class Estimate:
    point: float
    lo: float
    hi: float
    n: int

    def as_dict(self) -> dict:
        return asdict(self)

    def fmt(self, d: int = 2) -> str:
        return f"{self.point:.{d}f} [{self.lo:.{d}f}, {self.hi:.{d}f}]"


def _rng(seed: int | None) -> np.random.Generator:
    return np.random.default_rng(GLOBAL_SEED if seed is None else seed)


def bca_interval(point: float, reps: np.ndarray, jack: np.ndarray, alpha: float) -> tuple[float, float]:
    """Bias-corrected and accelerated (BCa) bootstrap interval.

    `reps` are bootstrap replicates of the statistic; `jack` are leave-one-out
    jackknife values (for the acceleration). Falls back to the percentile
    interval when the bias-correction is degenerate (all replicates on one side).
    """
    reps = np.asarray(reps, float)
    pl, ph = 100 * alpha / 2, 100 * (1 - alpha / 2)
    prop = float(np.mean(reps < point))
    if prop <= 0.0 or prop >= 1.0 or len(jack) < 3:
        return tuple(np.percentile(reps, [pl, ph]))
    z0 = stats.norm.ppf(prop)
    jbar = jack.mean()
    d = jbar - jack
    denom = 6.0 * (np.sum(d**2) ** 1.5)
    a = float(np.sum(d**3) / denom) if denom != 0 else 0.0
    zlo, zhi = stats.norm.ppf(alpha / 2), stats.norm.ppf(1 - alpha / 2)

    def _adj(z):
        return stats.norm.cdf(z0 + (z0 + z) / (1 - a * (z0 + z)))

    a1, a2 = _adj(zlo), _adj(zhi)
    if not (np.isfinite(a1) and np.isfinite(a2)):
        return tuple(np.percentile(reps, [pl, ph]))
    return tuple(np.percentile(reps, [100 * a1, 100 * a2]))


def _strata_resample(rng: np.random.Generator, strata: np.ndarray) -> np.ndarray:
    """One stratified bootstrap index draw: resample WITH replacement within each
    stratum to its observed count, so per-class sizes are preserved exactly."""
    out = []
    for s in np.unique(strata):
        pos = np.flatnonzero(strata == s)
        out.append(rng.choice(pos, size=len(pos), replace=True))
    return np.concatenate(out)


def bootstrap_ci(
    fn,
    *arrays,
    n_boot: int = 4000,
    alpha: float = 0.05,
    seed: int | None = None,
    paired: bool = True,
    method: str = "bca",
    strata: np.ndarray | None = None,
) -> Estimate:
    """Bootstrap CI for ``fn(*arrays)``.

    Resamples row indices (paired across arrays) ``n_boot`` times. ``method``
    is ``"bca"`` (bias-corrected accelerated, default — nominal coverage on
    skewed statistics like AUROC at small n) or ``"percentile"``. When ``strata``
    is given (an array aligned with the data, e.g. the class labels for AUROC),
    each replicate resamples WITHIN strata so the per-class counts match the
    observed sample — a genuine stratified bootstrap. Replicates for which ``fn``
    is undefined (e.g. AUROC with one class absent) are skipped.
    """
    arrays = [np.asarray(a) for a in arrays]
    n = len(arrays[0])
    rng = _rng(seed)
    strata = np.asarray(strata) if strata is not None else None
    point = float(fn(*arrays))
    reps = np.empty(n_boot)
    k = 0
    for _ in range(n_boot):
        if not paired:
            idx = None
        elif strata is not None:
            idx = _strata_resample(rng, strata)
        else:
            idx = rng.integers(0, n, n)
        try:
            reps[k] = fn(*[a[idx] for a in arrays])
            k += 1
        except Exception:
            continue
    reps = reps[:k]
    if method == "percentile":
        lo, hi = np.percentile(reps, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    else:
        # jackknife for the acceleration term
        idx_all = np.arange(n)
        jack = np.empty(n)
        kk = 0
        for i in range(n):
            keep = np.delete(idx_all, i)
            try:
                jack[kk] = fn(*[a[keep] for a in arrays])
                kk += 1
            except Exception:
                continue
        lo, hi = bca_interval(point, reps, jack[:kk], alpha)
    return Estimate(point=point, lo=float(lo), hi=float(hi), n=n)


# ----------------------------------------------------------------------------
# Discrimination
# ----------------------------------------------------------------------------
def auroc(y_true: np.ndarray, score: np.ndarray) -> float:
    """AUROC of ``score`` predicting the positive class (accept_bool==1)."""
    return float(roc_auc_score(y_true, score))


def auroc_ci(y_true, score, **kw) -> Estimate:
    """Stratified bootstrap CI for AUROC: resamples within each decision class so
    every replicate keeps the observed reject/accept counts (a degenerate
    one-class replicate is impossible). Pass ``strata=`` to override."""
    y_true = np.asarray(y_true)
    kw.setdefault("strata", y_true)
    return bootstrap_ci(auroc, y_true, np.asarray(score), **kw)


def roc_points(y_true, score):
    fpr, tpr, _ = roc_curve(y_true, score)
    return fpr, tpr


def auroc_pvalue(y_true: np.ndarray, score: np.ndarray) -> float:
    """One-sided Mann-Whitney p for AUROC>0.5 (positive class scores higher)."""
    y_true = np.asarray(y_true)
    score = np.asarray(score, float)
    pos, neg = score[y_true == 1], score[y_true == 0]
    if len(pos) == 0 or len(neg) == 0:
        return 1.0
    return float(stats.mannwhitneyu(pos, neg, alternative="greater").pvalue)


def mwu_pvalue(a, b) -> float:
    """Two-sided Mann-Whitney U p for a difference in two score groups (e.g. the
    overall-score distributions of two decision tiers). NaN if either is empty."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    return float(stats.mannwhitneyu(a, b, alternative="two-sided").pvalue)


def paired_auroc_diff(
    y_true, score_a, score_b, n_boot: int = 4000, alpha: float = 0.05, seed: int | None = None
) -> dict:
    """Paired difference in AUROC, ``delta = AUROC(a) - AUROC(b)``, with a
    stratified paired bootstrap CI and a two-sided bootstrap p-value.

    Both scores are evaluated against the SAME labels on the SAME resampled rows
    in each replicate, so the difference is genuinely paired — the
    correlated-AUROC comparison that two overlapping marginal CIs cannot resolve.
    Resampling is stratified on the label (per-class counts preserved, as in
    ``auroc_ci``). ``p`` is the two-sided bootstrap tail
    ``2*min(P(delta*<=0), P(delta*>=0))`` with the +1 correction so p>0; a
    non-significant result means the pre-declared superiority criterion (CI
    excluding zero) is not met, and is reported as such — neither superiority
    nor equivalence.
    """
    y = np.asarray(y_true).astype(int)
    a = np.asarray(score_a, float)
    b = np.asarray(score_b, float)
    delta = auroc(y, a) - auroc(y, b)
    rng = _rng(seed)
    reps: list[float] = []
    for _ in range(n_boot):
        idx = _strata_resample(rng, y)
        try:
            reps.append(auroc(y[idx], a[idx]) - auroc(y[idx], b[idx]))
        except Exception:
            continue
    r = np.asarray(reps)
    lo, hi = np.percentile(r, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    p_left = (np.sum(r <= 0) + 1) / (len(r) + 1)
    p_right = (np.sum(r >= 0) + 1) / (len(r) + 1)
    p = float(min(1.0, 2 * min(p_left, p_right)))
    return {"delta": float(delta), "lo": float(lo), "hi": float(hi), "p": p, "n": int(len(y))}


def paired_run_sd_test(sd_a, sd_b) -> dict:
    """Exact Wilcoxon signed-rank test for paired within-paper run SDs.

    ``sd_a`` and ``sd_b`` are per-paper run-to-run SDs of the SAME papers under
    two graders (e.g. the full pipeline vs the direct judge), aligned by paper.
    Pairs with a missing SD on either side are dropped. The p-value is the
    two-sided exact signed-rank p (``scipy.stats.wilcoxon``, ``method="exact"``
    — feasible because the variance sub-study has few pairs), testing whether
    the within-paper SDs differ systematically across the two graders rather
    than only in their medians. Returns ``{statistic, p, n}`` with ``n`` the
    number of complete pairs used.
    """
    a = np.asarray(sd_a, float)
    b = np.asarray(sd_b, float)
    mask = np.isfinite(a) & np.isfinite(b)
    a, b = a[mask], b[mask]
    res = stats.wilcoxon(a, b, alternative="two-sided", method="exact")
    return {"statistic": float(res.statistic), "p": float(res.pvalue), "n": int(len(a))}


def benjamini_hochberg(pvals: dict[str, float], alpha: float = 0.05) -> dict[str, dict]:
    """Benjamini-Hochberg FDR control over a family of named p-values.

    Returns {name: {p, q, significant}} where q is the BH-adjusted value and
    `significant` is the step-up decision at level `alpha`.
    """
    names = list(pvals)
    p = np.array([pvals[k] for k in names], float)
    m = len(p)
    order = np.argsort(p)
    ranks = np.empty(m, int)
    ranks[order] = np.arange(1, m + 1)
    # adjusted q (monotone) via the standard step-up
    q_sorted = np.minimum.accumulate((p[order] * m / np.arange(1, m + 1))[::-1])[::-1]
    q = np.empty(m)
    q[order] = np.clip(q_sorted, 0, 1)
    # rejection threshold: largest k with p_(k) <= alpha*k/m
    thresh_ok = p[order] <= alpha * np.arange(1, m + 1) / m
    kmax = np.where(thresh_ok)[0].max() + 1 if thresh_ok.any() else 0
    crit = p[order][kmax - 1] if kmax > 0 else -1.0
    return {names[i]: {"p": float(p[i]), "q": float(q[i]), "significant": bool(p[i] <= crit)} for i in range(m)}


# ----------------------------------------------------------------------------
# Rank correlation
# ----------------------------------------------------------------------------
def spearman(x: np.ndarray, y: np.ndarray) -> float:
    return float(stats.spearmanr(x, y).statistic)


def spearman_ci(x, y, **kw) -> Estimate:
    return bootstrap_ci(spearman, np.asarray(x, float), np.asarray(y, float), **kw)


# ----------------------------------------------------------------------------
# Ordinal (Phase-2) discrimination over a per-(venue, year) tier ladder.
# The pre-declared 4-tier additions: adjacent-boundary AUROCs and the
# per-tier median summary with a monotonicity statement.
# ----------------------------------------------------------------------------
def adjacent_boundary_aurocs(score, decision_tier, tier_order, **kw) -> dict[str, dict]:
    """AUROC at every ADJACENT tier boundary of an ordinal ladder.

    For each consecutive pair ``(lo, hi)`` of ``tier_order`` (e.g. the 4-tier
    ICLR-2025 ladder yields reject|poster, poster|spotlight, spotlight|oral),
    subset to the rows in those two tiers and compute the AUROC of ``score``
    predicting membership in the HIGHER tier, with the same stratified BCa
    bootstrap CI machinery as :func:`auroc_ci` (``**kw`` forwarded, e.g.
    ``n_boot``). Returns ``{"lo|hi": Estimate-dict}`` in ladder order; a
    boundary with either tier empty is skipped (no degenerate AUROC)."""
    score = np.asarray(score, float)
    decision_tier = np.asarray(decision_tier)
    out: dict[str, dict] = {}
    for lo_t, hi_t in zip(tier_order[:-1], tier_order[1:]):
        mask = (decision_tier == lo_t) | (decision_tier == hi_t)
        y = (decision_tier[mask] == hi_t).astype(int)
        if len(np.unique(y)) < 2:
            continue
        out[f"{lo_t}|{hi_t}"] = auroc_ci(y, score[mask], **kw).as_dict()
    return out


def per_tier_summary(score, decision_tier, tier_order) -> dict:
    """Per-tier ``{tier: {n, median}}`` in ladder order, plus ``monotone``.

    ``monotone`` is True iff the per-tier medians are non-decreasing along the
    ladder (empty tiers — median NaN — are skipped in the comparison, so a
    missing tier never spuriously breaks monotonicity)."""
    score = np.asarray(score, float)
    decision_tier = np.asarray(decision_tier)
    tiers: dict[str, dict] = {}
    medians: list[float] = []
    for t in tier_order:
        s = score[decision_tier == t]
        med = float(np.median(s)) if len(s) else float("nan")
        tiers[t] = {"n": int(len(s)), "median": med}
        medians.append(med)
    present = [m for m in medians if m == m]
    monotone = all(b >= a for a, b in zip(present, present[1:]))
    return {"tiers": tiers, "monotone": bool(monotone)}


# ----------------------------------------------------------------------------
# Descriptive supplementary checks (reviewer-requested, NOT confirmatory):
#   1. covariate-control CV AUROC — does the score-outcome relationship survive
#      conditioning on manuscript-surface + area covariates?
#   2. within-tier score<->rating Spearman — is the score a fine ranking of
#      strong papers, or a low-end triage signal?
# ----------------------------------------------------------------------------
_COVARIATE_NUMERIC = ("page_count", "word_count", "n_references", "n_figures", "rating_std", "n_reviews")
_COVARIATE_CATEGORICAL = ("primary_area",)


def covariate_control_auc(frame, score_col: str = "overall") -> dict:
    """Cross-validated AUROC of a logistic model that adds manuscript-surface and
    area covariates to the AIPR score, reported against a score-only CV AUROC.

    Model: ``accept_bool ~ score + primary_area + page_count + word_count +
    n_references + n_figures + rating_std + n_reviews``. Numerics are
    standard-scaled and ``primary_area`` is one-hot encoded
    (``handle_unknown="ignore"``) inside a single ``Pipeline`` so the fold-fit
    transforms never leak across folds. AUROC is the mean of a stratified 5-fold
    ``cross_val_score`` (``shuffle=True, random_state=GLOBAL_SEED``); the
    score-only baseline reuses the SAME CV protocol with ``score`` as the only
    feature (so the two AUROCs are comparable under one estimator and one split,
    NOT the paper's headline point-AUROC). Descriptive/exploratory: this is a
    confound audit, not a replacement for the pre-registered AUROC.

    Self-restricts to the covariate columns actually present and the rows with no
    missing covariate; returns ``n`` = rows used.
    """
    y = np.asarray(frame["accept_bool"].values).astype(int)
    num_cols = [c for c in _COVARIATE_NUMERIC if c in frame.columns and frame[c].notna().any()]
    cat_cols = [c for c in _COVARIATE_CATEGORICAL if c in frame.columns and frame[c].notna().any()]
    use_cols = [score_col, *num_cols, *cat_cols]
    sub = frame[[*use_cols, "accept_bool"]].dropna(subset=use_cols).reset_index(drop=True)
    y = sub["accept_bool"].values.astype(int)
    n = int(len(sub))
    cv = StratifiedKFold(5, shuffle=True, random_state=GLOBAL_SEED)

    def _cv_auc(feature_cols: list[str]) -> float:
        x = sub[feature_cols]
        num = [c for c in feature_cols if c in (score_col, *num_cols)]
        cat = [c for c in feature_cols if c in cat_cols]
        transformers = [("num", StandardScaler(), num)]
        if cat:
            transformers.append(("cat", OneHotEncoder(handle_unknown="ignore"), cat))
        pipe = Pipeline(
            [
                ("pre", ColumnTransformer(transformers)),
                ("clf", LogisticRegression(max_iter=1000)),
            ]
        )
        return float(cross_val_score(pipe, x, y, cv=cv, scoring="roc_auc").mean())

    return {
        "cv_auc_covariate": _cv_auc([score_col, *num_cols, *cat_cols]),
        "cv_auc_score_only": _cv_auc([score_col]),
        "n": n,
    }


def within_tier_spearman(frame) -> dict:
    """Spearman of the AIPR ``overall`` against ``mean_reviewer_rating`` WITHIN each
    decision subgroup: reject-only, poster-only, oral-only, and accepted-only
    (poster + oral). Supports the bounded claim — the score is a low-end triage
    signal, not a fine ranking of strong papers, so the within-accepted
    correlation is expected to be weak. Subgroups with ``n < 3`` report
    ``rho = nan`` (rendered ``"--"`` downstream).
    """
    tr = np.asarray(frame["tier_rank"].values).astype(int)
    overall = np.asarray(frame["overall"].values, float)
    rating = np.asarray(frame["mean_reviewer_rating"].values, float)
    masks = {
        "reject": tr == TIER_RANK["reject"],
        "poster": tr == TIER_RANK["poster"],
        "oral": tr == TIER_RANK["oral"],
        "accepted": tr >= TIER_RANK["poster"],
    }
    out: dict = {}
    for name, mask in masks.items():
        n = int(mask.sum())
        rho = spearman(overall[mask], rating[mask]) if n >= 3 else float("nan")
        out[name] = {"rho": float(rho), "n": n}
    return out


# ----------------------------------------------------------------------------
# Loop 07 — three further DESCRIPTIVE (NOT confirmatory) reviewer checks:
#   3. bottom-band tie/threshold sensitivity — is the low-score flag robust to
#      the exact bottom-band membership rule (quintile vs bottom-K vs fixed
#      cutoffs), given integer scores make quintile ties mildly arbitrary?
#   4. reviewer-disagreement moderation — does the score track the outcome
#      worse where the human reviewers disagree (high rating_std)?
#   5. area / subfield subgroup audit — is the headline concentrated in one
#      ICLR primary area, or broadly present across areas?
# ----------------------------------------------------------------------------
def bottom_band_sensitivity(
    score: np.ndarray, accept_bool: np.ndarray, tier_rank: np.ndarray,
    sub_order: np.ndarray | None = None, bottom_k: int = 60,
) -> list[dict]:
    """Robustness of the low-score flag to the bottom-band membership rule.

    The integer score + quintile binning makes exact bottom-band membership
    mildly tie-dependent. For each of several band definitions we report the
    reject rate, the lift over the base reject rate, and the oral rate, so the
    headline low-end signal can be shown to hold regardless of the rule. The
    definitions are:

    * ``strict quintile`` — ``score < quantile(score, 0.2)`` (the pre-registered
      band-0 membership of :func:`score_band_table`);
    * ``bottom-K`` (K=``bottom_k``, default 60) — the lowest K submissions after a
      DETERMINISTIC tie-break: sort by score ascending then by ``sub_order``
      (submission order) ascending, take the first K. Ties never resolve by row
      order or RNG, so the set is reproducible. When ``sub_order`` is absent the
      original row index is the tie-break;
    * fixed thresholds ``score<=63``, ``score<=64``, ``score<=65``.

    ``lift`` = band reject rate / overall base reject rate (the SAME base used by
    :func:`score_band_table`). Bands with ``n==0`` report ``reject_rate``/
    ``oral_rate`` 0 and ``lift`` nan. Descriptive: this is a tie/threshold
    sensitivity sweep, not a confirmatory test.
    """
    score = np.asarray(score, float)
    accept_bool = np.asarray(accept_bool, int)
    tier_rank = np.asarray(tier_rank, int)
    n_all = len(score)
    order = np.arange(n_all) if sub_order is None else np.asarray(sub_order)
    base = float((accept_bool == 0).mean())

    def _row(label: str, mask: np.ndarray) -> dict:
        n = int(mask.sum())
        rr = float((accept_bool[mask] == 0).mean()) if n else 0.0
        orr = float((tier_rank[mask] == TIER_RANK["oral"]).mean()) if n else 0.0
        lift = (rr / base) if (base > 0 and n) else float("nan")
        return {"label": label, "n": n, "reject_rate": rr, "lift": lift, "oral_rate": orr}

    rows: list[dict] = []
    rows.append(_row("strict quintile", score < float(np.quantile(score, 0.2))))
    # deterministic bottom-K: lexsort puts the primary key LAST.
    k = min(bottom_k, n_all)
    chosen = np.lexsort((order, score))[:k]
    bk_mask = np.zeros(n_all, dtype=bool)
    bk_mask[chosen] = True
    rows.append(_row(f"bottom-{bottom_k}", bk_mask))
    for thr in (63, 64, 65):
        rows.append(_row(f"score<={thr}", score <= thr))
    return rows


def disagreement_moderation(frame) -> dict:
    """Does the AIPR score track the outcome WORSE where the human reviewers
    disagree (high ``rating_std``)? Two descriptive readings on one cohort:

    (a) ``rho_resid_std`` — Spearman of the absolute score-vs-rating rank
        residual against ``rating_std``. The rank residual is
        ``rank(overall) - rank(mean_reviewer_rating)`` (the score's local
        disagreement with the human ranking); we correlate its magnitude with the
        within-paper reviewer disagreement. A positive rho means the score and the
        human ranking diverge more where reviewers themselves disagree.
    (b) ``auroc_low_std`` / ``auroc_high_std`` — AUROC of ``overall`` vs
        ``accept_bool``, computed separately on the low- and high-disagreement
        halves (median split of ``rating_std``; ties go to the LOW half via a
        ``<=`` cut so the split is deterministic). A subgroup missing a class
        reports AUROC nan.

    Returns the two AUROCs, their gap (low minus high), the residual rho, the
    median split point and per-half n. Descriptive: the ground truth is itself
    noisier where reviewers disagree, so a modest AUROC drop on the high-std half
    is expected and is NOT read as a model failure.
    """
    overall = np.asarray(frame["overall"].values, float)
    rating = np.asarray(frame["mean_reviewer_rating"].values, float)
    rstd = np.asarray(frame["rating_std"].values, float)
    y = np.asarray(frame["accept_bool"].values).astype(int)
    n = int(len(overall))
    # rank residual (average ranks; sign irrelevant since we take |.|)
    rank_overall = stats.rankdata(overall)
    rank_rating = stats.rankdata(rating)
    resid = np.abs(rank_overall - rank_rating)
    rho = spearman(resid, rstd) if n >= 3 else float("nan")
    med = float(np.median(rstd))
    low = rstd <= med
    high = ~low

    def _auc(mask: np.ndarray) -> float:
        yy, ss = y[mask], overall[mask]
        if len(np.unique(yy)) < 2:
            return float("nan")
        return auroc(yy, ss)

    auc_low, auc_high = _auc(low), _auc(high)
    gap = (auc_low - auc_high) if (auc_low == auc_low and auc_high == auc_high) else float("nan")
    return {
        "rho_resid_std": float(rho),
        "auroc_low_std": float(auc_low),
        "auroc_high_std": float(auc_high),
        "auroc_gap": float(gap),
        "median_std": med,
        "n_low": int(low.sum()),
        "n_high": int(high.sum()),
        "n": n,
    }


def area_subgroup_audit(frame, min_n: int = 8) -> list[dict]:
    """Per-``primary_area`` descriptive audit: is the score-outcome relationship
    concentrated in one ICLR area, or broadly present?

    For every area with at least ``min_n`` submissions, report the accept rate,
    mean AIPR ``overall``, Spearman of ``overall`` vs ``mean_reviewer_rating``,
    and AUROC of ``overall`` vs ``accept_bool`` (AUROC only where BOTH classes are
    present in the cell, else nan -> rendered ``"--"`` downstream; Spearman needs
    ``n >= 3`` else nan). Areas below ``min_n`` are POOLED into a single ``other``
    row so no submission is dropped and tiny cells are not over-interpreted. Rows
    are sorted by descending ``n`` with the pooled ``other`` row last.

    Descriptive only: per-area cells are small and noisy; the row to read is that
    no single area carries the headline, not any individual cell estimate.
    """
    if "primary_area" not in frame.columns:
        return []
    area = frame["primary_area"].astype(str).values
    overall = np.asarray(frame["overall"].values, float)
    rating = np.asarray(frame["mean_reviewer_rating"].values, float)
    y = np.asarray(frame["accept_bool"].values).astype(int)

    def _cell(label: str, mask: np.ndarray) -> dict:
        n = int(mask.sum())
        ov, rt, yy = overall[mask], rating[mask], y[mask]
        rho = spearman(ov, rt) if n >= 3 else float("nan")
        au = auroc(yy, ov) if len(np.unique(yy)) == 2 else float("nan")
        return {
            "area": label,
            "n": n,
            "accept_rate": float((yy == 1).mean()) if n else 0.0,
            "mean_score": float(ov.mean()) if n else float("nan"),
            "rho_score_rating": float(rho),
            "auroc": float(au),
        }

    counts: dict[str, int] = {}
    for a in area:
        counts[a] = counts.get(a, 0) + 1
    big = sorted([a for a, c in counts.items() if c >= min_n], key=lambda a: (-counts[a], a))
    small = [a for a, c in counts.items() if c < min_n]
    rows = [_cell(a, area == a) for a in big]
    if small:
        pooled = np.isin(area, small)
        if pooled.any():
            rows.append(_cell("other", pooled))
    return rows


def population_boundary(in_pop_df, out_of_pop_df, *, n_graded: int | None = None) -> dict:
    """Account for every eligible submission: in-population vs.\\ excluded.

    Evidences the DECISIONS.md §4 contract that no eligible submission is silently
    dropped — each one is either IN-POPULATION (passed eligibility, eligible to be
    graded) or in the eligible-but-excluded ledger with a stated reason.

    ``in_pop_df`` is the in-population ``submissions`` frame (one row per eligible
    submission; in the released export the analysis grades a stratified SAMPLE of
    these, not all of them). ``out_of_pop_df`` is the covariate-free exclusion
    ledger from :func:`schema.load_out_of_population` (or ``None`` when the export
    carries no ledger, in which case an empty dict is returned so callers
    self-skip). ``n_graded`` is the size of the graded cohort actually scored
    (e.g. cohort M, n=300); when ``None`` it falls back to ``len(in_pop_df)``.

    Returns ``n_in_population`` (eligible, not excluded), ``n_graded`` (the scored
    sample drawn from them), ``n_excluded`` (ledger rows), ``n_eligible``
    (in-population + excluded — every eligibility-screened submission accounted
    for), and ``by_reason``: a list of ``{reason, n, share}`` rows over the
    distinct ``exclude_reason`` values, sorted by descending count (``share`` is
    the reason's fraction of the excluded set). No covariates are read: the ledger
    carries none, by design (see the limitations note on why a covariate-level
    sampled-vs-eligible comparison is not possible).
    """
    if out_of_pop_df is None or not len(out_of_pop_df):
        return {}
    n_in = int(len(in_pop_df))
    n_excl = int(len(out_of_pop_df))
    counts = out_of_pop_df["exclude_reason"].astype(str).value_counts()
    by_reason = [
        {"reason": str(r), "n": int(c), "share": (float(c) / n_excl if n_excl else 0.0)}
        for r, c in counts.items()
    ]
    return {
        "n_in_population": n_in,
        "n_graded": int(n_graded) if n_graded is not None else n_in,
        "n_excluded": n_excl,
        "n_eligible": n_in + n_excl,
        "by_reason": by_reason,
    }


# ----------------------------------------------------------------------------
# Effect sizes for the two-group (reject vs accept) contrast
# ----------------------------------------------------------------------------
def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """Standardised mean difference (b - a), pooled SD. Positive => b higher."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = len(a), len(b)
    sp = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    return float((b.mean() - a.mean()) / sp) if sp > 0 else 0.0


def cliffs_delta(a: np.ndarray, b: np.ndarray) -> float:
    """Cliff's delta for (b vs a): P(b>a) - P(a>b). Rank-based, robust."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    # mann-whitney U gives sum of ranks; derive delta without O(n*m) loop
    u = stats.mannwhitneyu(b, a, alternative="two-sided").statistic
    return float(2 * u / (len(a) * len(b)) - 1)


# ----------------------------------------------------------------------------
# Ordered-tier trend test (Jonckheere-Terpstra, Monte Carlo permutation p-value)
# ----------------------------------------------------------------------------
@dataclass
class TrendResult:
    jt_statistic: float
    p_permutation: float
    spearman_rho: float
    spearman_ci: tuple[float, float]
    group_means: dict
    n_perm: int

    def as_dict(self) -> dict:
        d = asdict(self)
        d["spearman_ci"] = list(self.spearman_ci)
        return d


def _jt_statistic(values: np.ndarray, ranks: np.ndarray, order: list[int]) -> float:
    """Sum over ordered group pairs i<j of #(x_j > x_i) + 0.5*ties."""
    groups = [values[ranks == g] for g in order]
    j = 0.0
    for i in range(len(groups)):
        for jj in range(i + 1, len(groups)):
            gi, gj = groups[i], groups[jj]
            # vectorised pairwise comparison
            diff = gj[:, None] - gi[None, :]
            j += np.sum(diff > 0) + 0.5 * np.sum(diff == 0)
    return float(j)


def jonckheere_trend(
    values: np.ndarray, ranks: np.ndarray, n_perm: int = 10000, seed: int | None = None
) -> TrendResult:
    """Test H0: no trend vs H1: values increase with the ordinal group rank.

    Monte Carlo permutation p-value: shuffle the group labels ``n_perm`` times
    and count how often a JT statistic at least as extreme arises under H0, with
    the +1 correction (observed included) so p is never 0. Exact enumeration is
    infeasible at these sample sizes; resolution is ``1/(n_perm+1)``.
    """
    values = np.asarray(values, float)
    ranks = np.asarray(ranks, int)
    order = sorted(np.unique(ranks).tolist())
    obs = _jt_statistic(values, ranks, order)
    rng = _rng(seed)
    ge = 1  # +1 for the observed (conservative, avoids p=0)
    for _ in range(n_perm):
        perm = rng.permutation(ranks)
        if _jt_statistic(values, perm, order) >= obs:
            ge += 1
    p = ge / (n_perm + 1)
    sp = spearman_ci(ranks.astype(float), values, n_boot=2000, seed=seed)
    means = {int(g): float(values[ranks == g].mean()) for g in order}
    return TrendResult(
        jt_statistic=obs,
        p_permutation=float(p),
        spearman_rho=sp.point,
        spearman_ci=(sp.lo, sp.hi),
        group_means=means,
        n_perm=n_perm,
    )


# ----------------------------------------------------------------------------
# Low-end flagging: score-band lift over base rate
# ----------------------------------------------------------------------------
def wilson_interval(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (k successes of n)."""
    if n == 0:
        return (0.0, 0.0)
    z = stats.norm.ppf(1 - alpha / 2)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


@dataclass
class BandRow:
    band: str
    lo_score: float
    hi_score: float
    n: int
    reject_rate: float
    reject_ci: tuple[float, float]
    accept_rate: float
    oral_rate: float
    lift: float  # reject_rate / base_reject_rate
    lift_ci: tuple[float, float]  # bootstrap CI for the lift


def _band_lift(score: np.ndarray, accept_bool: np.ndarray, n_bins: int, b: int) -> float:
    """Lift of band ``b`` (reject rate / base reject rate) for one (re)sample.
    Bins are sample-relative quantiles, matching the pre-registered threshold."""
    base = float((accept_bool == 0).mean())
    if base <= 0:
        return float("nan")
    edges = np.quantile(score, np.linspace(0, 1, n_bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    mask = (score >= edges[b]) & (score < edges[b + 1])
    if not mask.any():
        return float("nan")
    return float((accept_bool[mask] == 0).mean()) / base


def band_lift_ci(
    score: np.ndarray, accept_bool: np.ndarray, n_bins: int, b: int,
    n_boot: int = 2000, alpha: float = 0.05, seed: int | None = None,
) -> tuple[float, float, float]:
    """Percentile bootstrap CI for a band's lift over base rate. Resampling the
    whole cohort propagates uncertainty in BOTH the band reject rate and the base
    rate (and re-derives the sample-relative band edges each replicate), which a
    Wilson interval on the reject rate alone cannot capture. This is the CI the
    pre-registered H1 success rule (lift CI lower bound > 1) reads."""
    score = np.asarray(score, float)
    accept_bool = np.asarray(accept_bool, int)
    rng = _rng(seed)
    n = len(score)
    point = _band_lift(score, accept_bool, n_bins, b)
    reps = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        v = _band_lift(score[idx], accept_bool[idx], n_bins, b)
        if np.isfinite(v):
            reps.append(v)
    reps = np.asarray(reps)
    lo, hi = np.percentile(reps, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return point, float(lo), float(hi)


def score_band_table(
    score: np.ndarray, accept_bool: np.ndarray, tier_rank: np.ndarray, n_bins: int = 5,
    seed: int | None = None,
) -> list[BandRow]:
    """Bin submissions by AIPR score quantile; per band report reject rate,
    Wilson CI, oral rate, lift over the base reject rate, and a bootstrap lift CI.

    Band 0 is the LOWEST-score band — the headline (H1) lives there.
    """
    score = np.asarray(score, float)
    accept_bool = np.asarray(accept_bool, int)
    tier_rank = np.asarray(tier_rank, int)
    base_reject = float((accept_bool == 0).mean())
    edges = np.quantile(score, np.linspace(0, 1, n_bins + 1))
    # Open the outer edges so the min/max values are always captured; with
    # +/-inf edges the half-open [edges[b], edges[b+1]) rule covers every point
    # (no last-bin special case needed).
    edges[0], edges[-1] = -np.inf, np.inf
    rows: list[BandRow] = []
    for b in range(n_bins):
        mask = (score >= edges[b]) & (score < edges[b + 1])
        n = int(mask.sum())
        rej = int((accept_bool[mask] == 0).sum())
        rr = rej / n if n else 0.0
        orr = float((tier_rank[mask] == TIER_RANK["oral"]).mean()) if n else 0.0
        _, lci, hci = band_lift_ci(score, accept_bool, n_bins, b, seed=seed)
        rows.append(
            BandRow(
                band=f"Q{b + 1}",
                lo_score=float(np.min(score[mask])) if n else float("nan"),
                hi_score=float(np.max(score[mask])) if n else float("nan"),
                n=n,
                reject_rate=rr,
                reject_ci=wilson_interval(rej, n),
                accept_rate=1 - rr,
                oral_rate=orr,
                lift=(rr / base_reject) if base_reject > 0 else float("nan"),
                lift_ci=(lci, hci),
            )
        )
    return rows


@dataclass
class HarmRow:
    n_bottom: int
    n_accepted: int
    n_oral: int
    accepted_in_bottom: int
    oral_in_bottom: int
    p_low_given_accepted: float
    p_low_given_oral: float


def low_score_harm(
    score: np.ndarray, accept_bool: np.ndarray, tier_rank: np.ndarray, q: float
) -> HarmRow:
    """Deployment-relevant error: strong work landing in the low-score band.

    The bottom band is ``score < quantile(score, q)`` -- the SAME membership as
    band 0 of :func:`score_band_table` -- so these counts describe exactly the
    region the flag fires on. Reports how many accepted / oral papers fall in it,
    as counts and as P(low | accepted) / P(low | oral). This is the opposite
    conditional to bottom-band reject precision: the triage harm a low-score flag
    must keep small (a strong paper wrongly flagged), not the reject rate.
    """
    score = np.asarray(score, float)
    accept_bool = np.asarray(accept_bool, int)
    tier_rank = np.asarray(tier_rank, int)
    low = score < float(np.quantile(score, q))
    is_oral = tier_rank == TIER_RANK["oral"]
    n_acc = int((accept_bool == 1).sum())
    n_oral = int(is_oral.sum())
    acc_low = int(((accept_bool == 1) & low).sum())
    oral_low = int((is_oral & low).sum())
    return HarmRow(
        n_bottom=int(low.sum()),
        n_accepted=n_acc,
        n_oral=n_oral,
        accepted_in_bottom=acc_low,
        oral_in_bottom=oral_low,
        p_low_given_accepted=(acc_low / n_acc) if n_acc else 0.0,
        p_low_given_oral=(oral_low / n_oral) if n_oral else 0.0,
    )


# ----------------------------------------------------------------------------
# Low-end bridge: does the cheap score agree with the frontier score WHERE THE
# CLAIM LIVES (the bottom band), not just globally? A high global Spearman can
# hide low-end disagreement.
# ----------------------------------------------------------------------------
def quantile_membership_overlap(a: np.ndarray, b: np.ndarray, q: float = 0.2) -> dict:
    """Agreement of the two bottom-``q`` sets of paired scores ``a`` and ``b``.

    ``recall`` = fraction of ``a``'s bottom quintile also in ``b``'s bottom
    quintile (would the cheap flag re-fire on the frontier score?); ``jaccard``
    = overlap of the two bottom sets. For the low-end bridge claim.
    """
    a, b = np.asarray(a, float), np.asarray(b, float)
    ta, tb = np.quantile(a, q), np.quantile(b, q)
    sa, sb = a <= ta, b <= tb
    inter, union = int(np.sum(sa & sb)), int(np.sum(sa | sb))
    return {
        "recall": float(inter / sa.sum()) if sa.sum() else float("nan"),
        "jaccard": float(inter / union) if union else float("nan"),
        "n_bottom_a": int(sa.sum()),
        "n_bottom_b": int(sb.sum()),
    }


def low_band_spearman(a: np.ndarray, b: np.ndarray, q: float = 0.2, **kw) -> Estimate:
    """Spearman of paired scores restricted to ``a``'s bottom-``q`` band (the
    low-end agreement the global bridge correlation can mask)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    mask = a <= np.quantile(a, q)
    return spearman_ci(a[mask], b[mask], **kw)


# ----------------------------------------------------------------------------
# Natural-prevalence reweighting (closed-form Bayes; the balanced cohort
# over-samples the accept tiers, so the flag's PRECISION must be reweighted).
# ----------------------------------------------------------------------------
def prevalence_reweighted_bottom_precision(
    score: np.ndarray, accept_bool: np.ndarray, q: float, nat_accept_rate: float
) -> dict:
    """Reject precision of the bottom-``q`` flag at a target natural accept
    prevalence. AUROC is prevalence-invariant; precision is not. Reweights the
    two class-conditional bottom-band rates by Bayes rather than resampling."""
    score, acc = np.asarray(score, float), np.asarray(accept_bool, int)
    bottom = score <= np.quantile(score, q)
    p_b_rej = float(bottom[acc == 0].mean()) if (acc == 0).any() else 0.0
    p_b_acc = float(bottom[acc == 1].mean()) if (acc == 1).any() else 0.0
    p_acc = float(nat_accept_rate)
    p_rej = 1.0 - p_acc
    den = p_b_rej * p_rej + p_b_acc * p_acc
    return {
        "bottom_reject_precision": float(p_b_rej * p_rej / den) if den > 0 else float("nan"),
        "base_reject_rate": p_rej,
        "nat_accept_rate": p_acc,
    }


# ----------------------------------------------------------------------------
# Calibration / reliability: empirical reject rate by score decile
# ----------------------------------------------------------------------------
def reliability_table(score: np.ndarray, accept_bool: np.ndarray, n_bins: int = 10):
    score = np.asarray(score, float)
    accept_bool = np.asarray(accept_bool, int)
    edges = np.quantile(score, np.linspace(0, 1, n_bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    out = []
    for b in range(n_bins):
        mask = (score >= edges[b]) & (score < edges[b + 1])
        n = int(mask.sum())
        if n == 0:
            continue
        rej = int((accept_bool[mask] == 0).sum())
        lo, hi = wilson_interval(rej, n)
        out.append(
            {
                "mean_score": float(score[mask].mean()),
                "reject_rate": rej / n,
                "lo": lo,
                "hi": hi,
                "n": n,
            }
        )
    return out


# ----------------------------------------------------------------------------
# Operating-point classification: threshold a quality score into accept/reject.
# Used for the naive-judge "why us" comparison (AIPR@60 etc.). Both graders get
# the SAME decision rule so the comparison isolates the score, not the rule.
# ----------------------------------------------------------------------------
def classify_at_threshold(y_true: np.ndarray, score: np.ndarray, threshold: float) -> dict:
    """Accept/reject metrics from thresholding a score (``score >= threshold`` =>
    predict accept) against the human label. Reports balanced accuracy alongside
    raw accuracy because the cohort is class-imbalanced."""
    y = np.asarray(y_true).astype(int)
    pred = (np.asarray(score, dtype=float) >= threshold).astype(int)
    tp = int(((pred == 1) & (y == 1)).sum())
    tn = int(((pred == 0) & (y == 0)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    n = len(y)
    prec = tp / (tp + fp) if (tp + fp) else float("nan")
    sens = tp / (tp + fn) if (tp + fn) else float("nan")  # recall
    spec = tn / (tn + fp) if (tn + fp) else float("nan")
    f1 = (2 * prec * sens / (prec + sens)) if (prec + sens) and not np.isnan(prec * sens) else float("nan")
    return {
        "threshold": float(threshold),
        "accuracy": (tp + tn) / n if n else float("nan"),
        "balanced_accuracy": float(np.nanmean([sens, spec])),
        "precision": prec,
        "recall": sens,
        "f1": f1,
        "pred_accept_rate": float(pred.mean()) if n else float("nan"),
        "tp": tp, "tn": tn, "fp": fp, "fn": fn, "n": n,
    }


def threshold_for_accept_rate(score: np.ndarray, accept_rate: float) -> float:
    """Score threshold whose ``>=`` predicts ``accept_rate`` of the cohort as
    accept. Lets a baseline be scored at its OWN matched accept-rate (a fair
    operating point) rather than being forced onto another grader's fixed cutoff."""
    s = np.asarray(score, dtype=float)
    if len(s) == 0:
        return float("nan")
    return float(np.quantile(s, max(0.0, min(1.0, 1.0 - accept_rate))))
