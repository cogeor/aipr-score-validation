"""All paper figures. `render_all(d, R)` writes vector PDFs (+ PNG previews) into
paper/figures/. Each figure carries one message; the main and supplementary
figures are split per the paper's figure inventory.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from common import (
    BAND_QUANTILE,
    COL_WIDTH,
    CONFIG_COLORS,
    CONFIG_LABELS,
    DIM_LABELS,
    DIMENSIONS,
    FIG_DIR,
    PRIMARY_CONFIG,
    PRIMARY_VENUE,
    PRODUCTION_CONFIG,
    RELIABILITY_BINS,
    REPLICATION_VENUE,
    TEXT_WIDTH,
    TIER_COLORS,
    TIER_LABELS,
    TIER_ORDER,
    apply_style,
    watermark,
)
from stats import reliability_table, roc_points

_N_BANDS = int(round(1 / BAND_QUANTILE))


def _primary(df):
    return df[(df["venue"] == PRIMARY_VENUE[0]) & (df["year"] == PRIMARY_VENUE[1])].reset_index(drop=True)


def _save(fig, name: str, synthetic: bool):
    watermark(fig, synthetic)
    for ext in ("pdf", "png"):
        fig.savefig(FIG_DIR / f"{name}.{ext}")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main figures
# ---------------------------------------------------------------------------
def fig_design(d, R):
    """F0: study-design / data-flow schematic. A reader should see the cohorts,
    the grading configs, and which hypothesis each output feeds before the
    results (a page-1 orientation schematic)."""
    fig, ax = plt.subplots(figsize=(TEXT_WIDTH, 2.7))
    ax.set_xlim(0, 100); ax.set_ylim(0, 40); ax.axis("off")

    def box(x, y, w, h, text, fc, fontsize=7.5):
        ax.add_patch(plt.Rectangle((x, y), w, h, fc=fc, ec="0.4", lw=0.8, zorder=2))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize, zorder=3)

    def arrow(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops={"arrowstyle": "-|>", "color": "0.35", "lw": 1.1}, zorder=1)

    # Top lane = grading path; bottom lane = ground-truth path. No crossings.
    box(1, 23, 20, 12, "Submitted PDF\n(version reviewers saw)", "#EAEAEA")
    box(1, 4, 20, 12, "OpenReview venue\n(ICLR 2026)", "#EAEAEA")
    box(27, 21, 24, 16,
        "AIPR v6 grading\n" + r"$M \supseteq H$" + "\n(full-mini / full)\n+ naive baseline",
        CONFIG_COLORS["full_mini"] + "55")
    box(57, 23, 22, 12, "5 subscores +\nweighted overall\n+ tokens used", "#EAEAEA")
    box(40, 4, 26, 12, "Decision tier +\nmean reviewer rating\n(ground truth)", "#EAEAEA")
    box(86, 14, 13, 12, "Validation\nH1–H5", CONFIG_COLORS["full"] + "44")

    arrow(11, 16, 11, 23)      # venue -> submitted PDF (provides the artifact)
    arrow(21, 10, 40, 10)      # venue -> ground-truth labels
    arrow(21, 29, 27, 29)      # PDF -> grading
    arrow(51, 29, 57, 29)      # grading -> scores
    arrow(79, 29, 86, 22)      # scores -> validation
    arrow(66, 10, 86, 18)      # ground truth -> validation
    _save(fig, "fig0_design", d.is_synthetic)


def _ax_tiers(ax, df, R):
    """Panel: overall-score distribution across the four ordered decision tiers (H3)."""
    data = [df.loc[df["decision_tier"] == t, "overall"].values for t in TIER_ORDER]
    parts = ax.violinplot(data, showextrema=False, widths=0.8)
    for i, b in enumerate(parts["bodies"]):
        b.set_facecolor(TIER_COLORS[TIER_ORDER[i]])
        b.set_alpha(0.45)
    bp = ax.boxplot(data, widths=0.18, showfliers=False, patch_artist=True, medianprops={"color": "black"})
    for i, box in enumerate(bp["boxes"]):
        box.set_facecolor(TIER_COLORS[TIER_ORDER[i]])
        box.set_alpha(0.9)
    for i, t in enumerate(TIER_ORDER):
        x = np.random.default_rng(i).normal(i + 1, 0.05, len(data[i]))
        ax.scatter(x, data[i], s=2, color="black", alpha=0.12, zorder=3)
    ax.set_xticks(range(1, len(TIER_ORDER) + 1))
    ax.set_xticklabels([TIER_LABELS[t] for t in TIER_ORDER], rotation=20, ha="right")
    ax.set_ylabel("AIPR overall score")
    ax.set_xlabel("Decision tier")
    rho = R[PRIMARY_CONFIG]["trend"]["spearman_rho"]
    pf = _pfrag(R[PRIMARY_CONFIG]["trend"]["p_permutation"])
    # Effect size as a neutral annotation; interpretation lives in the caption.
    ax.text(0.03, 0.97, rf"$\rho={rho:.2f}$, ${pf}$", transform=ax.transAxes,
            va="top", ha="left", fontsize=7)


def _ax_reliability(ax, df, R):
    """Panel: empirical reject rate by AIPR score decile + bottom-band lift (H1)."""
    rel = reliability_table(df["overall"].values, df["accept_bool"].values, n_bins=RELIABILITY_BINS)
    base = R["sample"]["base_reject_rate"]
    xs = [r["mean_score"] for r in rel]
    ys = [100 * r["reject_rate"] for r in rel]
    # Wilson interval is asymmetric about the raw proportion; clamp tiny
    # negative arms to zero so matplotlib accepts the error bars.
    lo = [max(0.0, 100 * (r["reject_rate"] - r["lo"])) for r in rel]
    hi = [max(0.0, 100 * (r["hi"] - r["reject_rate"])) for r in rel]
    bb = R["bottom_band"]
    # Shade the bottom-quintile score region instead of an arrow that crosses the
    # curve; the callout then sits in the empty top-right corner.
    ax.axvspan(min(xs) - 2, bb["hi_score"], color=CONFIG_COLORS[PRIMARY_CONFIG], alpha=0.08, lw=0)
    ax.errorbar(xs, ys, yerr=[lo, hi], fmt="o-", color=CONFIG_COLORS[PRIMARY_CONFIG], ms=3, capsize=2)
    ax.axhline(100 * base, ls="--", color="grey", lw=0.9)
    ax.text(0.985, 100 * base + 1.5, f"base {100 * base:.0f}%", transform=ax.get_yaxis_transform(),
            va="bottom", ha="right", fontsize=7, color="grey")
    ax.text(0.97, 0.95,
            f"bottom Q\n{100 * bb['reject_rate']:.0f}% rej ({bb['lift']:.2f}$\\times$)",
            transform=ax.transAxes, va="top", ha="right", fontsize=7,
            bbox={"boxstyle": "round,pad=0.3", "fc": "white", "ec": "0.7", "lw": 0.5})
    ax.set_xlabel("AIPR overall score (decile mean)")
    ax.set_ylabel("Empirical reject rate (%)")


def _ax_rating(ax, df, R):
    """Panel: AIPR overall vs mean reviewer rating, colored by tier (H4)."""
    for t in TIER_ORDER:
        sub = df[df["decision_tier"] == t]
        ax.scatter(sub["mean_reviewer_rating"], sub["overall"], s=5, alpha=0.30,
                   color=TIER_COLORS[t], edgecolors="none", label=TIER_LABELS[t])
    # robust trend line
    x, y = df["mean_reviewer_rating"].values, df["overall"].values
    b, a = np.polyfit(x, y, 1)
    xs = np.linspace(x.min(), x.max(), 50)
    ax.plot(xs, a + b * xs, color="black", lw=1.0)
    sp = R[PRIMARY_CONFIG]["spearman_rating"]
    ax.text(0.03, 0.97, rf"$\rho={sp['point']:.2f}$ [{sp['lo']:.2f}, {sp['hi']:.2f}]",
            transform=ax.transAxes, va="top", ha="left", fontsize=7)
    ax.set_xlabel("Mean reviewer rating")
    ax.set_ylabel("AIPR overall score")
    leg = ax.legend(fontsize=5.5, ncol=2, loc="lower right", markerscale=2, handletextpad=0.2,
                    columnspacing=0.6, borderpad=0.3)
    for lh in leg.legend_handles:
        lh.set_alpha(1.0)


def fig_validation_panel(d, R):
    """F2 (headline): the AIPR score recovers the human outcome, three ways. One
    figure, one message; (a) ordinal decision tiers, (b) the deployable low-score
    flag, (c) the continuous reviewer rating. Replaces the former four separate
    score-vs-outcome figures (one finding shown four times)."""
    df = _primary(d.config_frame(PRIMARY_CONFIG))
    fig, (axa, axb, axc) = plt.subplots(1, 3, figsize=(TEXT_WIDTH, 2.5))
    _ax_tiers(axa, df, R)
    _ax_reliability(axb, df, R)
    _ax_rating(axc, df, R)
    for ax, letter in ((axa, "a"), (axb, "b"), (axc, "c")):
        ax.set_title(f"({letter})", loc="left", fontsize=9, fontweight="bold")
    fig.tight_layout(w_pad=1.4)
    _save(fig, "fig_validation", d.is_synthetic)


def fig_roc(d, R):
    """Supp: ROC for reject-vs-accept, full-mini (headline) + full (production).
    The AUROC scalars already appear in the headline table and the reliability
    panel shows discrimination at the deployable end, so the curve is supplementary."""
    fig, ax = plt.subplots(figsize=(COL_WIDTH, COL_WIDTH))
    styles = {PRIMARY_CONFIG: "-", PRODUCTION_CONFIG: (0, (4, 1.5))}
    for cfg in (PRIMARY_CONFIG, PRODUCTION_CONFIG):
        df = _primary(d.config_frame(cfg))
        fpr, tpr = roc_points(df["accept_bool"].values, df["overall"].values)
        a = R[cfg]["auroc"]
        ax.plot(fpr, tpr, color=CONFIG_COLORS[cfg], ls=styles[cfg], lw=1.6,
                label=f"{CONFIG_LABELS[cfg]}: AUROC {a['point']:.2f} [{a['lo']:.2f}, {a['hi']:.2f}]")
    ax.plot([0, 1], [0, 1], ":", color="grey", lw=0.8)
    ax.set_xlabel("False positive rate (accepted scored low)")
    ax.set_ylabel("True positive rate (accepted scored high)")
    ax.legend(loc="lower right", fontsize=7.5)
    ax.set_aspect("equal")
    _save(fig, "figS_roc", d.is_synthetic)


def fig_naive_baseline(d, R):
    """F3 (headline, the "why us" result): the structured AIPR pipeline vs a generic
    one-paragraph LLM prompt on the same model + PDF. Left: ROC overlay
    (discrimination). Right: within-paper run-SD distributions (reliability). This
    is the pre-registered primary value comparison (V1); self-skips when the export
    carries no naive gradings."""
    nb = R.get("naive_baseline", {})
    if not nb:
        return
    full = _primary(d.config_frame(PRODUCTION_CONFIG))
    h_ids = set(full["submission_id"])
    naive = _primary(d.config_frame("naive"))
    naive = naive[naive["submission_id"].isin(h_ids)]
    fig, (axl, axr) = plt.subplots(1, 2, figsize=(TEXT_WIDTH, 2.6))

    # Left: ROC overlay (full solid, naive dashed).
    for df, cfg, ls in ((full, PRODUCTION_CONFIG, "-"), (naive, "naive", (0, (4, 1.5)))):
        fpr, tpr = roc_points(df["accept_bool"].values, df["overall"].values)
        a = nb["auroc_full"] if cfg == PRODUCTION_CONFIG else nb["auroc_naive"]
        axl.plot(fpr, tpr, color=CONFIG_COLORS[cfg], ls=ls, lw=1.6,
                 label=f"{CONFIG_LABELS[cfg]}: {a['point']:.2f}")
    axl.plot([0, 1], [0, 1], ":", color="grey", lw=0.8)
    axl.set_xlabel("False positive rate"); axl.set_ylabel("True positive rate")
    axl.set_aspect("equal"); axl.legend(loc="lower right", fontsize=7.5, title="AUROC")
    axl.set_title("(a)", loc="left", fontsize=9, fontweight="bold")

    # Right: within-paper run-to-run SD distributions (full vs naive).
    rv_full = d.run_variance(PRODUCTION_CONFIG); rv_full = rv_full[rv_full["submission_id"].isin(h_ids)]
    rv_naive = d.run_variance("naive"); rv_naive = rv_naive[rv_naive["submission_id"].isin(h_ids)]
    sd_max = float(np.nanmax([rv_full["run_sd"].max(), rv_naive["run_sd"].max(), 1.0]))
    bins = np.linspace(0, sd_max, 16)
    axr.hist(rv_full["run_sd"].dropna(), bins=bins, color=CONFIG_COLORS[PRODUCTION_CONFIG],
             alpha=0.7, label=CONFIG_LABELS[PRODUCTION_CONFIG])
    axr.hist(rv_naive["run_sd"].dropna(), bins=bins, color=CONFIG_COLORS["naive"],
             alpha=0.7, label=CONFIG_LABELS["naive"])
    axr.set_xlabel("Within-paper SD of overall (repeated runs)"); axr.set_ylabel("Submissions")
    axr.legend(fontsize=7.5)
    axr.set_title("(b)", loc="left", fontsize=9, fontweight="bold")
    fig.tight_layout(w_pad=1.4)
    _save(fig, "fig_naive", d.is_synthetic)


def fig_bridge(d, R):
    """F5: full-mini vs full overall on cohort H (the mini->frontier model bridge).
    Left: global agreement. Right: the low-end agreement the global correlation can
    mask — do the two scores flag the SAME bottom quintile?"""
    p = d.paired_frame(PRIMARY_CONFIG, PRODUCTION_CONFIG)
    ids = set(_primary(d.config_frame(PRODUCTION_CONFIG))["submission_id"])
    p = p[p["submission_id"].isin(ids)]
    xs = p[f"overall_{PRIMARY_CONFIG}"].values
    ys = p[f"overall_{PRODUCTION_CONFIG}"].values
    lim = [min(xs.min(), ys.min()) - 2, max(xs.max(), ys.max()) + 2]
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(TEXT_WIDTH, COL_WIDTH))

    # Left: global agreement.
    br = R["bridge"]["spearman"]
    axL.scatter(xs, ys, s=10, alpha=0.5, color=CONFIG_COLORS[PRODUCTION_CONFIG], edgecolors="none")
    axL.plot(lim, lim, "--", color="grey", lw=0.8)
    axL.text(0.03, 0.97, rf"global $\rho={br['point']:.2f}$, $n={R['bridge']['n']}$",
             transform=axL.transAxes, va="top", ha="left", fontsize=7)
    axL.set_xlabel("Full-mini overall"); axL.set_ylabel("Full (GPT-5.4) overall")
    axL.set_xlim(lim); axL.set_ylim(lim); axL.set_aspect("equal")

    # Right: bottom-quintile membership agreement.
    qx, qy = np.quantile(xs, BAND_QUANTILE), np.quantile(ys, BAND_QUANTILE)
    sx, sy = xs <= qx, ys <= qy
    cat_other = ~sx & ~sy
    axR.scatter(xs[cat_other], ys[cat_other], s=9, alpha=0.25, color="0.6", edgecolors="none")
    axR.scatter(xs[sx & sy], ys[sx & sy], s=14, alpha=0.85, color=CONFIG_COLORS[PRODUCTION_CONFIG],
                label="both bottom Q")
    axR.scatter(xs[sx & ~sy], ys[sx & ~sy], s=14, alpha=0.85, color="#CC79A7",
                label="mini-only bottom Q")
    axR.axvline(qx, ls=":", color="grey", lw=0.8); axR.axhline(qy, ls=":", color="grey", lw=0.8)
    ov = R["bridge"]["bottom_overlap"]
    lbr = R["bridge"]["low_band_spearman"]
    axR.text(0.03, 0.97,
             f"bottom-Q recall {100 * ov['recall']:.0f}%\n" + rf"low-band $\rho={lbr['point']:.2f}$",
             transform=axR.transAxes, va="top", ha="left", fontsize=7)
    axR.set_xlabel("Full-mini overall"); axR.set_ylabel("Full (GPT-5.4) overall")
    axR.set_xlim(lim); axR.set_ylim(lim); axR.set_aspect("equal")
    axR.legend(fontsize=6.5, loc="lower right")
    _save(fig, "fig5_bridge", d.is_synthetic)


# ---------------------------------------------------------------------------
# Supplementary figures
# ---------------------------------------------------------------------------
def fig_subscore_auroc(d, R):
    fig, ax = plt.subplots(figsize=(COL_WIDTH, 2.4))
    dims = list(DIMENSIONS)
    pts = [R[PRIMARY_CONFIG]["subscore_auroc"][dim]["point"] for dim in dims]
    err = [[R[PRIMARY_CONFIG]["subscore_auroc"][dim]["point"] - R[PRIMARY_CONFIG]["subscore_auroc"][dim]["lo"] for dim in dims],
           [R[PRIMARY_CONFIG]["subscore_auroc"][dim]["hi"] - R[PRIMARY_CONFIG]["subscore_auroc"][dim]["point"] for dim in dims]]
    y = np.arange(len(dims))
    ax.barh(y, pts, xerr=err, color=CONFIG_COLORS[PRIMARY_CONFIG], alpha=0.85, capsize=2)
    ax.axvline(0.5, ls="--", color="grey", lw=0.8)
    ax.set_yticks(y); ax.set_yticklabels([DIM_LABELS[x] for x in dims])
    ax.set_xlabel("AUROC (reject vs. accept)"); ax.set_xlim(0.4, 1.0)
    ax.set_title("Per-dimension discrimination")
    _save(fig, "figS_subscore_auroc", d.is_synthetic)


def fig_nested_auroc(d, R):
    if not R.get("nested_auroc"):
        return
    fig, ax = plt.subplots(figsize=(COL_WIDTH, 2.3))
    cfgs = [c for c in ("full_mini", "full") if c in R["nested_auroc"]]
    pts = [R["nested_auroc"][c]["point"] for c in cfgs]
    err = [[R["nested_auroc"][c]["point"] - R["nested_auroc"][c]["lo"] for c in cfgs],
           [R["nested_auroc"][c]["hi"] - R["nested_auroc"][c]["point"] for c in cfgs]]
    x = np.arange(len(cfgs))
    ax.errorbar(x, pts, yerr=err, fmt="o", color="black", capsize=3)
    ax.set_xticks(x); ax.set_xticklabels([CONFIG_LABELS[c] for c in cfgs])
    ax.set_ylabel("AUROC (cohort H)"); ax.set_xlabel("Grading configuration")
    _save(fig, "figS_nested_auroc", d.is_synthetic)


def fig_runvar(d, R):
    rv = d.run_variance(PRODUCTION_CONFIG)
    rv = rv[rv["n_runs"] > 1]
    if rv.empty:
        return
    fig, ax = plt.subplots(figsize=(COL_WIDTH, 2.2))
    ax.hist(rv["run_sd"].dropna(), bins=20, color=CONFIG_COLORS[PRODUCTION_CONFIG], alpha=0.8)
    ax.axvline(R["run_variance_full"]["median_sd"], color="black", ls="--", lw=0.9)
    ax.set_xlabel("Within-paper SD of overall score (full, repeated runs)")
    ax.set_ylabel("Submissions")
    ax.set_title("Run-to-run scoring noise")
    _save(fig, "figS_run_variance", d.is_synthetic)


def fig_prevalence(d, R):
    """Supp: bottom-quintile reject precision vs. assumed natural accept rate.

    AUROC is prevalence-invariant; the flag's precision is not. We re-weight the
    balanced cohort to a range of natural accept rates and show the low-score
    flag stays well above base rate throughout."""
    df = _primary(d.config_frame(PRIMARY_CONFIG))
    score, acc = df["overall"].values, df["accept_bool"].values
    thr = np.quantile(score, BAND_QUANTILE)
    bottom = score <= thr
    accept_rates = np.linspace(0.10, 0.40, 13)
    rng = np.random.default_rng(7)
    prec, base = [], []
    for ar in accept_rates:
        # importance weights to hit target accept prevalence
        cur = acc.mean()
        w = np.where(acc == 1, ar / cur, (1 - ar) / (1 - cur))
        w = w / w.sum()
        idx = rng.choice(len(acc), size=4000, p=w)
        prec.append(100 * (acc[idx][bottom[idx]] == 0).mean())
        base.append(100 * (acc[idx] == 0).mean())
    fig, ax = plt.subplots(figsize=(COL_WIDTH, 2.3))
    ax.plot(accept_rates, prec, "o-", ms=3, color=CONFIG_COLORS[PRIMARY_CONFIG], label="bottom quintile")
    ax.plot(accept_rates, base, "s--", ms=3, color="grey", label="base rate")
    ax.set_xlabel("Assumed natural accept rate")
    ax.set_ylabel("Reject rate (%)")
    ax.set_title("Low-score flag under prevalence shift")
    ax.legend(fontsize=7)
    _save(fig, "figS_prevalence", d.is_synthetic)


def fig_replication(d, R):
    """Supp: reject/accept ROC on the replication venue (generalization)."""
    rep = d.config_frame(PRIMARY_CONFIG)
    rep = rep[(rep["venue"] == REPLICATION_VENUE[0]) & (rep["year"] == REPLICATION_VENUE[1])]
    if len(rep) == 0 or rep["accept_bool"].nunique() < 2:
        return
    fig, ax = plt.subplots(figsize=(COL_WIDTH, COL_WIDTH))
    fpr, tpr = roc_points(rep["accept_bool"].values, rep["overall"].values)
    label = f"{REPLICATION_VENUE[0]} {REPLICATION_VENUE[1]}"
    a = R.get("replication", {}).get("auroc")
    leg = f"{label}: AUROC {a['point']:.2f} [{a['lo']:.2f}, {a['hi']:.2f}]" if a else label
    ax.plot(fpr, tpr, color=CONFIG_COLORS[PRIMARY_CONFIG], label=leg)
    ax.plot([0, 1], [0, 1], "--", color="grey", lw=0.8)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title(f"Replication ({label}, full-mini)")
    ax.legend(loc="lower right", fontsize=7)
    ax.set_aspect("equal")
    _save(fig, "figS_replication", d.is_synthetic)


def fig_contamination(d, R):
    """Supp: temporal leakage controls. Full-mini AUROC on the clean primary cohort,
    the pre-cutoff replication venue (contaminated contrast), and the primary
    cohort excluding pre-cutoff arXiv papers. The signal of interest: the clean
    cohort is no weaker than the contaminated one and is unchanged by the
    arXiv exclusion, so memorization/leakage is not driving the result."""
    bars = R.get("contamination", {}).get("bars", {})
    order = [c for c in ("primary", "replication", "arxiv_no_prior") if c in bars]
    if len(order) < 2:
        return
    color = {"primary": CONFIG_COLORS["full"], "replication": "#D55E00", "arxiv_no_prior": "#999999"}
    fig, ax = plt.subplots(figsize=(COL_WIDTH, 2.3))
    y = np.arange(len(order))
    pts = [bars[c]["auroc"]["point"] for c in order]
    err = [[bars[c]["auroc"]["point"] - bars[c]["auroc"]["lo"] for c in order],
           [bars[c]["auroc"]["hi"] - bars[c]["auroc"]["point"] for c in order]]
    ax.barh(y, pts, xerr=err, color=[color.get(c, "#777") for c in order], alpha=0.85, capsize=2)
    ax.axvline(0.5, ls="--", color="grey", lw=0.8)
    ax.set_yticks(y); ax.set_yticklabels([bars[c]["label"] for c in order])
    ax.set_xlabel("AUROC (reject vs. accept)"); ax.set_xlim(0.4, 1.0)
    ax.invert_yaxis()
    _save(fig, "figS_contamination", d.is_synthetic)


def fig_weight_robustness(d, R):
    """Supp: headline AUROC under deployed / equal / leave-one-out weightings.
    Shows the result does not hinge on the proprietary weighting."""
    wr = R.get("weight_robustness")
    if not wr:
        return
    fig, ax = plt.subplots(figsize=(COL_WIDTH, 2.4))
    labels = ["Deployed", "Equal"] + [f"−{DIM_LABELS[dd]}" for dd in DIMENSIONS]
    dep = R[PRIMARY_CONFIG]["auroc"]
    ests = [dep, wr["equal_weight"]["auroc"]] + [wr["leave_one_out"][dd]["auroc"] for dd in DIMENSIONS]
    x = np.arange(len(labels))
    pts = [e["point"] for e in ests]
    err = [[e["point"] - e["lo"] for e in ests], [e["hi"] - e["point"] for e in ests]]
    cols = [CONFIG_COLORS["full"], "#777"] + [CONFIG_COLORS["full_mini"]] * len(DIMENSIONS)
    ax.errorbar(x, pts, yerr=err, fmt="o", color="black", capsize=2, ls="none")
    ax.scatter(x, pts, c=cols, s=22, zorder=3)
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("AUROC (reject vs. accept)")
    ax.set_ylim(0.8, 1.0)
    _save(fig, "figS_weight_robustness", d.is_synthetic)


def fig_cost(d, R):
    """Supp: mean tokens used per grading config (the cost-design story)."""
    cost = R.get("cost", {})
    order = [c for c in ("full_mini", "full", "naive") if c in cost]
    if len(order) < 2:
        return
    fig, ax = plt.subplots(figsize=(COL_WIDTH, 2.4))
    x = np.arange(len(order))
    inp = [cost[c]["input"] / 1000 for c in order]
    out = [cost[c]["output"] / 1000 for c in order]
    ax.bar(x, inp, 0.6, color="#999999", label="input")
    ax.bar(x, out, 0.6, bottom=inp, color=CONFIG_COLORS["full"], label="output")
    ax.set_xticks(x); ax.set_xticklabels([CONFIG_LABELS[c] for c in order], rotation=30, ha="right")
    ax.set_ylabel("Tokens used per grading (thousands)")
    ax.legend(fontsize=7, loc="upper right")
    _save(fig, "figS_cost", d.is_synthetic)


def fig_dummy_layout(d, R):
    """A pure formatting probe: a 2x2 grid mirroring the planned main layout, so
    column widths/margins are verifiable before real figures exist."""
    fig, axes = plt.subplots(2, 2, figsize=(TEXT_WIDTH, 4.4))
    for ax, name in zip(axes.flat, ["F1 tiers", "F2 ROC", "F3 reliability", "F4 rating"]):
        ax.text(0.5, 0.5, name, ha="center", va="center", fontsize=12)
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("Main-text figure layout probe")
    _save(fig, "figS_layout_probe", d.is_synthetic)


def _ptxt(p: float) -> str:
    return "<0.0001" if p < 1e-4 else f"{p:.4f}"


def _pfrag(p: float) -> str:
    """A correctly-typeset p fragment for a title: ``p<0.0001`` (not ``p=<0.0001``)."""
    return "p<0.0001" if p < 1e-4 else f"p={p:.4f}"


def render_all(d, R):
    apply_style()
    # Main figures: orient (design) -> prove the score recovers the outcome
    # (validation panel) -> show why the engineered pipeline matters (naive).
    fig_design(d, R)
    fig_validation_panel(d, R)
    fig_naive_baseline(d, R)
    fig_bridge(d, R)
    # Supplementary figures.
    fig_roc(d, R)
    fig_subscore_auroc(d, R)
    fig_nested_auroc(d, R)
    fig_runvar(d, R)
    fig_prevalence(d, R)
    fig_replication(d, R)
    fig_contamination(d, R)
    fig_weight_robustness(d, R)
    fig_cost(d, R)
    # fig_dummy_layout: a pre-figure layout probe; not part of the paper.
    print(f"rendered figures -> {FIG_DIR}")
