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
from sklearn.metrics import roc_auc_score, roc_curve

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
    non-significant result is the parity finding the analysis expects.
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
