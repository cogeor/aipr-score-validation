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


def table_subscore_corr(d, R):
    """Pairwise Pearson r among the four informative subscores (citation excluded:
    pinned, zero variance). The halo / anchoring lens — whether the dimensions are
    judged distinctly or move as one latent-quality factor."""
    sc = R["subscore_corr"]
    dims = sc["dims"]
    m = sc["matrix"]
    header = " & ".join(DIM_LABELS[x] for x in dims)
    rows = []
    for a in dims:
        cells = ["1" if a == b else f"{m[a][b]:.2f}" for b in dims]
        rows.append(rf"{DIM_LABELS[a]} & " + " & ".join(cells) + r" \\")
    body = (
        "\\begin{tabular}{l" + "c" * len(dims) + "}\n\\toprule\n"
        + rf" & {header} \\" + "\n\\midrule\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n\\end{tabular}\n"
    )
    _w("tab_subscore_corr.tex", body)


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


def table_covariate_control(d, R):
    """Descriptive (NOT confirmatory) covariate-control CV AUROC: score-only vs
    score+covariates (manuscript surface + primary area) under one stratified
    5-fold protocol, both cohorts. Shows the score-outcome relationship is not
    explained away by the covariate set."""
    cc = R.get("covariate_control", {})
    if not cc:
        return
    rows = []
    for key, label in (("mini", "Full-mini"), ("full", "Frontier")):
        if key in cc:
            c = cc[key]
            rows.append(
                rf"{label} & {c['cv_auc_score_only']:.2f} & {c['cv_auc_covariate']:.2f} & {c['n']} \\"
            )
    body = (
        "\\begin{tabular}{lccc}\n\\toprule\n"
        "Cohort & Score-only AUROC & $+$covariates AUROC & $n$ \\\\\n\\midrule\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n\\end{tabular}\n"
    )
    _w("tab_covariate_control.tex", body)


def table_within_tier(d, R):
    """Descriptive within-subgroup Spearman of the AIPR overall against the mean
    reviewer rating (full-mini cohort). Reject/poster/oral and accepted (poster +
    oral); the within-accepted correlation is expected weak (the score is a
    low-end triage signal, not a fine ranking of strong papers)."""
    wt = R.get("within_tier_rho", {})
    if not wt:
        return
    label = {"reject": "Reject", "poster": "Poster", "oral": "Oral",
             "accepted": "Accepted (poster $+$ oral)"}
    rows = []
    for key in ("reject", "poster", "oral", "accepted"):
        if key in wt:
            rho = wt[key]["rho"]
            cell = "---" if rho != rho else f"{rho:.2f}"
            rows.append(rf"{label[key]} & {wt[key]['n']} & {cell} \\")
    body = (
        "\\begin{tabular}{lcc}\n\\toprule\n"
        "Subgroup & $n$ & Spearman $\\rho$ (overall vs.\\ rating) \\\\\n\\midrule\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n\\end{tabular}\n"
    )
    _w("tab_within_tier.tex", body)


def table_bottom_band_sensitivity(d, R):
    """Descriptive (loop 07) tie/threshold sensitivity of the low-score flag: per
    bottom-band definition (strict quintile, deterministic bottom-K, fixed
    cutoffs) the n, reject rate, lift over base, and oral rate (full-mini). The
    flag holds across rules."""
    bbs = R.get("bottom_band_sensitivity", [])
    if not bbs:
        return
    rows = []
    for r in bbs:
        lift = "---" if r["lift"] != r["lift"] else f"{r['lift']:.2f}"
        rows.append(
            rf"{r['label']} & {r['n']} & {100 * r['reject_rate']:.0f}\% & {lift} & {100 * r['oral_rate']:.0f}\% \\"
        )
    body = (
        "\\begin{tabular}{lcccc}\n\\toprule\n"
        "Bottom-band definition & $n$ & Reject rate & Lift & Oral rate \\\\\n\\midrule\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n\\end{tabular}\n"
    )
    _w("tab_bottom_band_sensitivity.tex", body)


def table_disagreement(d, R):
    """Descriptive (loop 07) reviewer-disagreement moderation, both cohorts: the
    residual-vs-rating_std Spearman and the low/high-disagreement AUROC split
    (median split of rating SD). Weak moderation throughout."""
    dm = R.get("disagreement_moderation", {})
    if not dm:
        return
    rows = []
    for key, label in (("mini", "Full-mini"), ("full", "Frontier")):
        if key in dm:
            c = dm[key]

            def cell(x):
                return "---" if x != x else f"{x:.2f}"

            rows.append(
                rf"{label} & {cell(c['rho_resid_std'])} & {cell(c['auroc_low_std'])} & "
                rf"{cell(c['auroc_high_std'])} & {c['n_low']}/{c['n_high']} \\"
            )
    body = (
        "\\begin{tabular}{lcccc}\n\\toprule\n"
        "Cohort & Residual--SD $\\rho$ & AUROC (low disagr.) & AUROC (high disagr.) & "
        "$n$ low/high \\\\\n\\midrule\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n\\end{tabular}\n"
    )
    _w("tab_disagreement.tex", body)


def table_area_subgroup(d, R):
    """Descriptive (loop 07) per-area subgroup audit (full-mini): accept rate,
    mean AIPR score, score--rating Spearman, and AUROC per primary area, with
    small areas pooled into ``other``. Cells are noisy; no single area carries the
    headline."""
    asg = R.get("area_subgroup", [])
    if not asg:
        return
    rows = []
    for r in asg:
        rho = "---" if r["rho_score_rating"] != r["rho_score_rating"] else f"{r['rho_score_rating']:.2f}"
        au = "---" if r["auroc"] != r["auroc"] else f"{r['auroc']:.2f}"
        ms = "---" if r["mean_score"] != r["mean_score"] else f"{r['mean_score']:.1f}"
        area = r["area"].replace("_", "\\_").replace("&", "\\&")
        rows.append(
            rf"{area} & {r['n']} & {100 * r['accept_rate']:.0f}\% & {ms} & {rho} & {au} \\"
        )
    # p{} first column so the long ICLR area names wrap instead of overrunning the
    # margin (an "l" column ran 250pt past the text block); \small keeps it compact.
    body = (
        "{\\small\n\\begin{tabular}{p{2.4in}ccccc}\n\\toprule\n"
        "Primary area & $n$ & Accept rate & Mean score & $\\rho$ (score--rating) & AUROC \\\\\n\\midrule\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n\\end{tabular}}\n"
    )
    _w("tab_area_subgroup.tex", body)


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


def table_population_boundary(d, R):
    """The sample/population boundary: the in-population eligible set (and the
    graded sample drawn from it) beside the eligible-but-excluded ledger, broken
    down by exclusion reason. Evidences the DECISIONS.md §4 "every eligible
    submission is accounted for, never silently dropped" contract. Self-skips when
    the export carries no ledger."""
    pbd = R.get("population_boundary", {})
    if not pbd:
        return
    reason_label = {"withdrawn": "Withdrawn before review",
                    "desk_rejected": "Desk-rejected"}
    rows = []
    for row in pbd["by_reason"]:
        label = reason_label.get(row["reason"], row["reason"].replace("_", "\\_"))
        rows.append(rf"\quad {label} & {row['n']} & {100 * row['share']:.1f}\% \\")
    body = (
        "\\begin{tabular}{lrr}\n\\toprule\n"
        "Disposition & Submissions & Share of excluded \\\\\n\\midrule\n"
        + rf"In-population (eligible, not excluded) & {pbd['n_in_population']} & --- \\" + "\n"
        + rf"\quad of which graded (cohort M sample) & {pbd['n_graded']} & --- \\" + "\n"
        + "\\midrule\n"
        + rf"\textbf{{Eligible-but-excluded}} & \textbf{{{pbd['n_excluded']}}} & \textbf{{100.0\%}} \\" + "\n"
        + "\n".join(rows) + "\n"
        + "\\midrule\n"
        + rf"\textbf{{Total eligibility-screened}} & \textbf{{{pbd['n_eligible']}}} & --- \\" + "\n"
        "\\bottomrule\n\\end{tabular}\n"
    )
    _w("tab_population_boundary.tex", body)


def write_all(d, R):
    table_sample(d, R)
    table_headline(d, R)
    table_bands(d, R)
    table_subscores(d, R)
    table_subscore_corr(d, R)
    table_contamination(d, R)
    table_weight_robustness(d, R)
    table_length_confound(d, R)
    table_covariate_control(d, R)
    table_within_tier(d, R)
    table_bottom_band_sensitivity(d, R)
    table_disagreement(d, R)
    table_area_subgroup(d, R)
    table_cost(d, R)
    table_naive_baseline(d, R)
    table_population_boundary(d, R)
    print(f"wrote tables -> {TAB_DIR}")
