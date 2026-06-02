"""LaTeX tables. `write_all(d, R)` writes booktabs tables into paper/tables/.

Tables are generated, never hand-typed, so they cannot drift from the data.
Each is a standalone {tabular} fragment \\input by the paper inside a {table}.
"""

from __future__ import annotations

from common import (
    CONFIG_LABELS,
    DIM_LABELS,
    DIMENSIONS,
    PRIMARY_CONFIG,
    PRIMARY_VENUE,
    PRODUCTION_CONFIG,
    TAB_DIR,
    TIER_LABELS,
    TIER_ORDER,
)


def _primary(df):
    return df[(df["venue"] == PRIMARY_VENUE[0]) & (df["year"] == PRIMARY_VENUE[1])].reset_index(drop=True)


def _w(name: str, body: str):
    (TAB_DIR / name).write_text(body, encoding="utf-8")


def table_sample(d, R):
    mini = _primary(d.config_frame(PRIMARY_CONFIG, include_excluded=True))
    rows = []
    for t in TIER_ORDER:
        n = int((mini["decision_tier"] == t).sum())
        rows.append(rf"{TIER_LABELS[t]} & {n} \\")
    body = (
        "\\begin{tabular}{lr}\n\\toprule\n"
        "Decision tier & Submissions (cohort M) \\\\\n\\midrule\n"
        + "\n".join(rows)
        + "\n\\midrule\n"
        + rf"\textbf{{Total full-mini (cohort M)}} & \textbf{{{R['sample']['n_mini']}}} \\" + "\n"
        + rf"Full / GPT-5.4 (cohort H, $\subseteq$ M) & {R['sample']['n_full']} \\" + "\n"
        "\\bottomrule\n\\end{tabular}\n"
    )
    _w("tab_sample.tex", body)


def table_headline(d, R):
    def row(label, mi, fu):
        return rf"{label} & {mi} & {fu} \\"

    mi, fu = R[PRIMARY_CONFIG], R[PRODUCTION_CONFIG]

    def ci(e):
        return f"{e['point']:.2f} [{e['lo']:.2f}, {e['hi']:.2f}]"

    p_mi = "<0.0001" if mi["trend"]["p_permutation"] < 1e-4 else f"{mi['trend']['p_permutation']:.4f}"
    body = (
        "\\begin{tabular}{lcc}\n\\toprule\n"
        rf"Metric & {CONFIG_LABELS[PRIMARY_CONFIG]} ($n={R['sample']['n_mini']}$) & {CONFIG_LABELS[PRODUCTION_CONFIG]} ($n={R['sample']['n_full']}$) \\" + "\n\\midrule\n"
        + row("AUROC (reject vs.\\ accept)", ci(mi["auroc"]), ci(fu["auroc"])) + "\n"
        + row("Spearman $\\rho$ (reviewer rating)", ci(mi["spearman_rating"]), ci(fu["spearman_rating"])) + "\n"
        + row("Cohen's $d$ (accept$-$reject)", f"{mi['cohens_d_acc_vs_rej']:.2f}", f"{fu['cohens_d_acc_vs_rej']:.2f}") + "\n"
        + row("Cliff's $\\delta$", f"{mi['cliffs_delta']:.2f}", f"{fu['cliffs_delta']:.2f}") + "\n"
        + row("Trend $\\rho$ (across tiers)", f"{mi['trend']['spearman_rho']:.2f}", f"{fu['trend']['spearman_rho']:.2f}") + "\n"
        + rf"Trend test $p$ & {p_mi} & --- \\" + "\n"
        "\\bottomrule\n\\end{tabular}\n"
    )
    _w("tab_headline.tex", body)


def table_bands(d, R):
    rows = []
    for b in R["score_bands"]:
        ci = f"[{100 * b['reject_ci'][0]:.0f}, {100 * b['reject_ci'][1]:.0f}]"
        lci = f"[{b['lift_ci'][0]:.2f}, {b['lift_ci'][1]:.2f}]"
        rows.append(
            rf"{b['band']} & {b['n']} & {b['lo_score']:.0f}--{b['hi_score']:.0f} & "
            rf"{100 * b['reject_rate']:.0f}\% {ci} & {b['lift']:.2f} {lci} & {100 * b['oral_rate']:.0f}\% \\"
        )
    body = (
        "\\begin{tabular}{lccccc}\n\\toprule\n"
        "Band & $n$ & Score range & Reject rate [95\\% CI] & Lift [95\\% CI] & Oral rate \\\\\n\\midrule\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n\\end{tabular}\n"
    )
    _w("tab_score_bands.tex", body)


def table_subscores(d, R):
    bh = R.get("subscore_bh", {})
    rows = []
    for dim in DIMENSIONS:
        e = R[PRIMARY_CONFIG]["subscore_auroc"][dim]
        q = bh.get(dim, {}).get("q")
        qcell = f"{q:.3f}" if q is not None else "---"
        rows.append(rf"{DIM_LABELS[dim]} & {e['point']:.2f} [{e['lo']:.2f}, {e['hi']:.2f}] & {qcell} \\")
    body = (
        "\\begin{tabular}{lcc}\n\\toprule\n"
        "Dimension & AUROC (reject vs.\\ accept) & BH $q$ \\\\\n\\midrule\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n\\end{tabular}\n"
    )
    _w("tab_subscores.tex", body)


def table_contamination(d, R):
    """Temporal leakage: clean primary cohort vs the pre-cutoff replication venue
    (contaminated contrast) vs the primary cohort with pre-cutoff arXiv papers
    excluded. All full-mini AUROC, so directly comparable."""
    bars = R.get("contamination", {}).get("bars", {})
    if len(bars) < 2:
        return

    def ci(e):
        return f"{e['point']:.2f} [{e['lo']:.2f}, {e['hi']:.2f}]"

    rows = [
        rf"{bars[k]['label']} & {bars[k]['n']} & {ci(bars[k]['auroc'])} \\"
        for k in ("primary", "replication", "arxiv_no_prior")
        if k in bars
    ]
    body = (
        "\\begin{tabular}{lcc}\n\\toprule\n"
        "Cohort & $n$ & AUROC (reject vs.\\ accept) \\\\\n\\midrule\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n\\end{tabular}\n"
    )
    _w("tab_contamination.tex", body)


def table_weight_robustness(d, R):
    """Headline AUROC under the deployed weights, equal weights, and each
    leave-one-dimension-out weighting, with rank agreement vs the deployed score."""
    wr = R.get("weight_robustness")
    if not wr:
        return

    def ci(e):
        return f"{e['point']:.2f} [{e['lo']:.2f}, {e['hi']:.2f}]"

    dep = R[PRIMARY_CONFIG]["auroc"]
    rows = [rf"Deployed weights & {ci(dep)} & --- \\"]
    ew = wr["equal_weight"]
    rows.append(rf"Equal weights & {ci(ew['auroc'])} & {ew['rho_vs_deployed']:.2f} \\")
    rows.append("\\midrule")
    for dim in DIMENSIONS:
        e = wr["leave_one_out"][dim]
        rows.append(rf"Drop {DIM_LABELS[dim].lower()} & {ci(e['auroc'])} & {e['rho_vs_deployed']:.2f} \\")
    body = (
        "\\begin{tabular}{lcc}\n\\toprule\n"
        "Weighting & AUROC (reject vs.\\ accept) & $\\rho$ vs.\\ deployed \\\\\n\\midrule\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n\\end{tabular}\n"
    )
    _w("tab_weight_robustness.tex", body)


def table_length_confound(d, R):
    """Rank correlation of the AIPR overall with manuscript-length metrics."""
    lc = R.get("length_confound", {})
    if not lc:
        return
    label = {"page_count": "Page count", "word_count": "Word count",
             "n_references": "Reference count", "n_figures": "Figure count"}
    rows = []
    for col in ("page_count", "word_count", "n_references", "n_figures"):
        if col in lc:
            e = lc[col]
            rows.append(rf"{label[col]} & {e['point']:.2f} [{e['lo']:.2f}, {e['hi']:.2f}] \\")
    body = (
        "\\begin{tabular}{lc}\n\\toprule\n"
        "Manuscript metric & Spearman $\\rho$ with AIPR overall \\\\\n\\midrule\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n\\end{tabular}\n"
    )
    _w("tab_length_confound.tex", body)


def table_cost(d, R):
    """Mean tokens used per grading config (the cost-design numbers)."""
    cost = R.get("cost", {})
    if not cost:
        return

    def k(x):
        return f"{x / 1000:.1f}k"

    rows = []
    for cfg in ("full_mini", "full", "naive"):
        if cfg in cost:
            c = cost[cfg]
            rows.append(rf"{CONFIG_LABELS[cfg]} & {k(c['input'])} & {k(c['output'])} & {k(c['total'])} & {c['n']} \\")
    body = (
        "\\begin{tabular}{lcccc}\n\\toprule\n"
        "Configuration & Input & Output & Total & $n$ runs \\\\\n\\midrule\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n\\end{tabular}\n"
    )
    _w("tab_cost.tex", body)


def table_naive_baseline(d, R):
    """The "why us" comparison: AIPR full vs the naive one-paragraph judge —
    discrimination (AUROC), the AIPR@60 operating point (balanced accuracy), and
    run-to-run reliability (median within-paper SD). Self-skips with no naive data."""
    nb = R.get("naive_baseline", {})
    if not nb:
        return

    def ci(e):
        return f"{e['point']:.2f} [{e['lo']:.2f}, {e['hi']:.2f}]"

    def pct(x):
        return f"{100 * x:.1f}"

    op = nb["op_at60"]
    rel = nb["reliability"]
    rows = [
        rf"AUROC (reject vs.\ accept) & {ci(nb['auroc_full'])} & {ci(nb['auroc_naive'])} \\",
        rf"Balanced accuracy @ 60 & {pct(op['full']['balanced_accuracy'])}\% & {pct(op['naive']['balanced_accuracy'])}\% \\",
        rf"Median run-to-run SD & {rel['full_median_sd']:.1f} & {rel['naive_median_sd']:.1f} \\",
    ]
    body = (
        "\\begin{tabular}{lcc}\n\\toprule\n"
        "Metric & AIPR (full pipeline) & Naive judge \\\\\n\\midrule\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n\\end{tabular}\n"
    )
    _w("tab_naive_baseline.tex", body)


def write_all(d, R):
    table_sample(d, R)
    table_headline(d, R)
    table_bands(d, R)
    table_subscores(d, R)
    table_contamination(d, R)
    table_weight_robustness(d, R)
    table_length_confound(d, R)
    table_cost(d, R)
    table_naive_baseline(d, R)
    print(f"wrote tables -> {TAB_DIR}")
