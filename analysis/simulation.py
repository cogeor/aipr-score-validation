"""Design-justification simulation — runs WITHOUT real data.

Two questions a careful reviewer asks before believing any result, both
answerable now:

1. POWER. Given plausible effect sizes, is the planned sample (n=100 frontier,
   n=300 full-mini) large enough to detect the effects each hypothesis claims, and
   what is the minimum detectable effect (MDE)? Answering this *before* grading
   protects the budget: if n=100 were underpowered for H1, we would resample.

2. ESTIMATOR CORRECTNESS. Do our own confidence intervals and tests behave?
   - Bootstrap CIs should cover the population value ~95% of the time.
   - The Jonckheere-Terpstra permutation test should reject a true null ~5% of
     the time (correct Type-I error) and yield uniform p-values under H0.

The generative model mirrors the study's assumed structure (a latent paper
quality drives tier, reviewer rating, and -- more noisily -- the AIPR score); the
effect-size knob is swept so power is reported as a function of the *true* AUROC,
not a single guessed value. This is a power/calibration study, not evidence about
AIPR.

Run: python simulation.py [--quick]
"""

from __future__ import annotations

import argparse
import json

import numpy as np
from scipy import stats
from sklearn.metrics import roc_auc_score

from common import FIG_DIR, GLOBAL_SEED, MACRO_DIR, RESULTS_DIR, apply_style

TIER_REL = np.array([-0.9, 0.0, 1.1])  # relative tier quality means (reject/poster/oral)
TIERS = np.array([0, 1, 2])
PLAN_N = {"H (frontier)": 100, "M (full-mini)": 300}


# ---------------------------------------------------------------------------
# Generative model
# ---------------------------------------------------------------------------
def _sample(n: int, sep: float, noise_sd: float, rng: np.random.Generator):
    """Balanced 3-tier sample. Returns (score, accept_bool, tier_rank, rating)."""
    per = n // 3
    tier = np.repeat(TIERS, per)
    q = rng.normal(TIER_REL[tier] * sep, 0.6)
    score = np.clip(60 + 13 * q + rng.normal(0, noise_sd, len(q)), 0, 100)
    rating = 3.0 + 1.4 * q + rng.normal(0, 0.8, len(q))
    accept = (tier >= 1).astype(int)
    return score, accept, tier, rating


def _population_auroc(sep: float, noise_sd: float, rng) -> float:
    s, a, _, _ = _sample(200_000, sep, noise_sd, rng)
    return float(roc_auc_score(a, s))


# ---------------------------------------------------------------------------
# Fast tests used inside the power loop (analytic, no nested bootstrap)
# ---------------------------------------------------------------------------
def _auroc_sig(score, accept) -> bool:
    """AUROC > 0.5 at alpha=0.05 via the Mann-Whitney normal approximation."""
    pos, neg = score[accept == 1], score[accept == 0]
    if len(pos) == 0 or len(neg) == 0:
        return False
    res = stats.mannwhitneyu(pos, neg, alternative="greater")
    return res.pvalue < 0.05


def _jt_z(values, ranks) -> float:
    """Jonckheere-Terpstra standardized statistic (normal approx, tie-naive)."""
    order = np.unique(ranks)
    groups = [values[ranks == g] for g in order]
    n = len(values)
    ni = np.array([len(g) for g in groups])
    j = 0.0
    for i in range(len(groups)):
        for k in range(i + 1, len(groups)):
            d = groups[k][:, None] - groups[i][None, :]
            j += np.sum(d > 0) + 0.5 * np.sum(d == 0)
    ej = (n**2 - np.sum(ni**2)) / 4.0
    vj = (n**2 * (2 * n + 3) - np.sum(ni**2 * (2 * ni + 3))) / 72.0
    return (j - ej) / np.sqrt(vj) if vj > 0 else 0.0


def _trend_sig(values, ranks) -> bool:
    return stats.norm.sf(_jt_z(values, ranks)) < 0.05


def _spearman_sig(x, y) -> bool:
    rho = stats.spearmanr(x, y).statistic
    n = len(x)
    if n < 4 or not np.isfinite(rho) or abs(rho) >= 1:
        return abs(rho) > 0
    z = np.arctanh(rho) * np.sqrt((n - 3) / 1.06)  # Fieller SE for Spearman
    return 2 * stats.norm.sf(abs(z)) < 0.05


def _lift_sig(score, accept, tier_rank, base: float) -> bool:
    """Bottom-quintile reject rate significantly exceeds the base reject rate."""
    thr = np.quantile(score, 0.2)
    m = score <= thr
    k = int((accept[m] == 0).sum())
    nm = int(m.sum())
    if nm == 0:
        return False
    return stats.binomtest(k, nm, base, alternative="greater").pvalue < 0.05


# ---------------------------------------------------------------------------
# Power analysis
# ---------------------------------------------------------------------------
def power_curves(n_sim: int, noise_sd: float, seed: int):
    rng = np.random.default_rng(seed)
    seps = np.linspace(0.0, 1.4, 8)
    grid = []
    for sep in seps:
        true_auc = _population_auroc(sep, noise_sd, rng)
        row = {"sep": float(sep), "true_auroc": true_auc, "power": {}}
        for label, n in PLAN_N.items():
            base = 1.0 / 3.0  # balanced 3-tier => reject prevalence 1/3
            hits = {"H1": 0, "H2": 0, "H3": 0, "H4": 0}
            for _ in range(n_sim):
                s, a, t, r = _sample(n, sep, noise_sd, rng)
                hits["H1"] += _lift_sig(s, a, t, base)
                hits["H2"] += _auroc_sig(s, a)
                hits["H3"] += _trend_sig(s, t)
                hits["H4"] += _spearman_sig(r, s)
            row["power"][str(n)] = {h: hits[h] / n_sim for h in hits}
        grid.append(row)
    return grid


def mde(grid, n: int, hyp: str, target: float = 0.8) -> float | None:
    """Smallest true AUROC reaching `target` power for hypothesis `hyp` at n."""
    xs = [(g["true_auroc"], g["power"][str(n)][hyp]) for g in grid]
    xs.sort()
    for auc, p in xs:
        if p >= target:
            return auc
    return None


# ---------------------------------------------------------------------------
# Estimator self-validation
# ---------------------------------------------------------------------------
def bootstrap_coverage(n_rep: int, n: int, n_boot: int, sep: float, noise_sd: float, seed: int):
    """Empirical coverage of the BCa 95% interval for AUROC (matches stats.py)."""
    from stats import bca_interval

    rng = np.random.default_rng(seed)
    true_auc = _population_auroc(sep, noise_sd, rng)
    covered = 0
    m = n
    for _ in range(n_rep):
        s, a, _, _ = _sample(n, sep, noise_sd, rng)
        # ``_sample`` returns a *balanced* 3-tier cohort, whose length is
        # 3*(n//3) and so can be < n (e.g. 99 for n=100). Drive every resampling
        # index off the ACTUAL sample length, never the requested n, so the
        # bootstrap and jackknife match the data.
        m = len(a)
        idx_all = np.arange(m)
        point = roc_auc_score(a, s)
        reps = []
        for _b in range(n_boot):
            idx = rng.integers(0, m, m)
            try:
                reps.append(roc_auc_score(a[idx], s[idx]))
            except ValueError:
                continue
        jack = []
        for i in range(m):
            keep = np.delete(idx_all, i)
            jack.append(roc_auc_score(a[keep], s[keep]))
        lo, hi = bca_interval(point, np.array(reps), np.array(jack), 0.05)
        covered += int(lo <= true_auc <= hi)
    return {"true_auroc": true_auc, "coverage": covered / n_rep, "target": 0.95, "n_rep": n_rep, "n": m, "method": "BCa"}


def jt_type_one(n_rep: int, n: int, n_perm: int, noise_sd: float, seed: int):
    """Under H0 (sep=0, no trend) the permutation p-values must be ~Uniform and
    reject at ~alpha."""
    rng = np.random.default_rng(seed)
    pvals = []
    for _ in range(n_rep):
        s, _a, t, _r = _sample(n, sep=0.0, noise_sd=noise_sd, rng=rng)
        obs = _jt_z(s, t)
        ge = 1
        for _p in range(n_perm):
            if _jt_z(s, rng.permutation(t)) >= obs:
                ge += 1
        pvals.append(ge / (n_perm + 1))
    pvals = np.array(pvals)
    ks = stats.kstest(pvals, "uniform")
    return {
        "type_one_error": float((pvals < 0.05).mean()),
        "target": 0.05,
        "uniform_ks_p": float(ks.pvalue),
        "n_rep": n_rep,
        "n": n,
    }


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
def render_power_figure(grid, synthetic_flag: bool = False):
    import matplotlib.pyplot as plt

    from common import COL_WIDTH, TEXT_WIDTH

    apply_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(TEXT_WIDTH, 2.6))
    aucs = [g["true_auroc"] for g in grid]
    for n, style in ((300, "-o"), (100, "--s")):
        ax1.plot(aucs, [g["power"][str(n)]["H2"] for g in grid], style, ms=3, label=f"n={n}")
    ax1.axhline(0.8, color="grey", ls=":", lw=0.8)
    ax1.set_xlabel("True AUROC (effect size)")
    ax1.set_ylabel("Power (reject $H_0$)")
    ax1.set_title("H2 power vs. effect size")
    ax1.legend(fontsize=7)
    # power of all hypotheses at the planned n=100, vs effect size
    for h in ("H1", "H2", "H3", "H4"):
        ax2.plot(aucs, [g["power"]["100"][h] for g in grid], "-o", ms=2.5, label=h)
    ax2.axhline(0.8, color="grey", ls=":", lw=0.8)
    ax2.set_xlabel("True AUROC (effect size)")
    ax2.set_ylabel("Power at n=100")
    ax2.set_title("All hypotheses, frontier cohort")
    ax2.legend(fontsize=7, ncol=2)
    if synthetic_flag:
        fig.text(0.5, 0.5, "SYNTHETIC", fontsize=40, color="red", alpha=0.08, ha="center", va="center", rotation=25)
    for ext in ("pdf", "png"):
        fig.savefig(FIG_DIR / f"figS_power.{ext}")
    plt.close(fig)


def write_sim_macros(summary: dict):
    L = ["% AUTO-GENERATED by analysis/simulation.py — DO NOT EDIT."]

    def cmd(name, val):
        L.append(rf"\newcommand{{\{name}}}{{{val}\xspace}}")

    cmd("powerHoneN", f"{100 * summary['power_at_plan']['100']['H1']:.0f}")
    cmd("powerHtwoN", f"{100 * summary['power_at_plan']['100']['H2']:.0f}")
    cmd("powerHtwoMini", f"{100 * summary['power_at_plan']['300']['H2']:.0f}")
    mde2 = summary["mde"]["H2_n100"]
    cmd("mdeAUROC", f"{mde2:.2f}" if mde2 else "n/a")
    cmd("bootCoverage", f"{100 * summary['coverage']['coverage']:.0f}")
    cmd("jtTypeOne", f"{100 * summary['jt']['type_one_error']:.1f}")
    cmd("jtUniformP", f"{summary['jt']['uniform_ks_p']:.2f}")
    (MACRO_DIR / "sim_macros.tex").write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="fast dev run (fewer reps)")
    args = ap.parse_args()
    n_sim = 300 if args.quick else 1500
    cov_rep = 150 if args.quick else 400
    jt_rep = 150 if args.quick else 400
    n_boot = 600 if args.quick else 1000
    n_perm = 300 if args.quick else 600
    noise_sd = 9.0

    print("== power curves ==")
    grid = power_curves(n_sim, noise_sd, GLOBAL_SEED)
    # power at a fiducial moderate effect (closest grid point to true AUROC ~0.8)
    fid = min(grid, key=lambda g: abs(g["true_auroc"] - 0.80))
    print("== bootstrap coverage ==")
    cov = bootstrap_coverage(cov_rep, 100, n_boot, sep=0.9, noise_sd=noise_sd, seed=GLOBAL_SEED + 1)
    print("== JT type-I error ==")
    jt = jt_type_one(jt_rep, 100, n_perm, noise_sd, seed=GLOBAL_SEED + 2)

    summary = {
        "noise_sd": noise_sd,
        "fiducial_true_auroc": fid["true_auroc"],
        "power_at_plan": fid["power"],
        "mde": {
            "H1_n100": mde(grid, 100, "H1"),
            "H2_n100": mde(grid, 100, "H2"),
            "H2_n300": mde(grid, 300, "H2"),
            "H3_n100": mde(grid, 100, "H3"),
            "H4_n100": mde(grid, 100, "H4"),
        },
        "coverage": cov,
        "jt": jt,
        "grid": grid,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "simulation.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    # The power analysis is a pre-data design simulation (it never uses the cohort),
    # so it is not dummy "results" and carries no SYNTHETIC watermark.
    render_power_figure(grid, synthetic_flag=False)
    write_sim_macros(summary)

    print(f"\nfiducial true AUROC ~ {fid['true_auroc']:.2f}")
    print(f"power@n=100: H1={fid['power']['100']['H1']:.2f} H2={fid['power']['100']['H2']:.2f} "
          f"H3={fid['power']['100']['H3']:.2f} H4={fid['power']['100']['H4']:.2f}")
    print(f"power@n=300 H2={fid['power']['300']['H2']:.2f}")
    print(f"MDE AUROC (H2,80%,n=100) = {summary['mde']['H2_n100']}")
    print(f"bootstrap coverage = {cov['coverage']:.3f} (target 0.95)")
    print(f"JT type-I error = {jt['type_one_error']:.3f} (target 0.05); uniform KS p = {jt['uniform_ks_p']:.2f}")


if __name__ == "__main__":
    main()
