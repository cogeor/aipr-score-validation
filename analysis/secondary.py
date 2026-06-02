"""Secondary analysis — comment-quality comparison on the ReviewBench axis.

ReviewBench (results snapshot in ../external/reviewbench-results) scores review *comments* by the
PRESENCE of structure (specification / justification / remedy / anchor) and by an
LLM-judged `is_consequential` flag whose prompt explicitly says "assess what the
reviewer is saying, not whether they are correct." It never checks correctness.

This module reproduces their metrics AND adds the axis they omit -- correctness
and grounding -- across sources including AIPR, so the story is: parity on form,
AIPR wins on truth. Like the rest of the study it runs on SYNTHETIC comment data
now (watermarked) and is replaced by the real run per
external/reviewbench-results/ADAPTER_AIPR.md. This is a SECONDARY comparison, not
primary evidence.
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from common import ACCENT, FIG_DIR, GLOBAL_SEED, MACRO_DIR, RESULTS_DIR, TAB_DIR, TEXT_WIDTH, apply_style, watermark
from stats import wilson_interval

# Order: humans + competitor AI sources (their four) + AIPR (ours).
SOURCES = ["human", "gpt-5.2", "gemini-3-pro", "r3", "aipr"]
SOURCE_LABELS = {"human": "Human", "gpt-5.2": "GPT-5.2", "gemini-3-pro": "Gemini 3 Pro", "r3": "R3", "aipr": "AIPR"}

# Their metrics (presence/intent rates) -- AI near ceiling, R3 leads on consequential.
THEIR_RATES = {
    #            spec  just  remedy anchor conseq
    "human":     (0.78, 0.74, 0.55, 0.86, 0.62),
    "gpt-5.2":   (0.97, 0.96, 0.98, 0.71, 0.80),
    "gemini-3-pro": (0.98, 0.97, 0.99, 0.72, 0.81),
    "r3":        (0.98, 0.97, 0.99, 0.74, 0.91),
    "aipr":      (0.97, 0.96, 0.98, 0.93, 0.86),
}
# Our correctness axis (what ReviewBench omits): anchor fidelity, citation
# groundedness, correctness-of-consequential. AIPR leads via the OpenAlex audit +
# quote verifier; R3 leads on consequential RATE but trails on correctness.
OUR_RATES = {
    #            anchor_fidelity  citation_grounded  correctness
    "human":     (0.88, 0.95, 0.85),
    "gpt-5.2":   (0.70, 0.58, 0.63),
    "gemini-3-pro": (0.71, 0.60, 0.64),
    "r3":        (0.72, 0.64, 0.66),
    "aipr":      (0.97, 0.99, 0.82),
}
N_COMMENTS = 600  # synthetic comments per source

THEIR_KEYS = ["specification", "justification", "remedy", "anchor", "consequential"]
OUR_KEYS = ["anchor_fidelity", "citation_grounded", "correctness"]


def _draw(rate: float, n: int, rng) -> np.ndarray:
    return (rng.random(n) < rate).astype(int)


def generate() -> dict:
    """Synthetic per-comment booleans per source; clearly synthetic."""
    rng = np.random.default_rng(GLOBAL_SEED + 99)
    data = {}
    for s in SOURCES:
        cols = {}
        for k, r in zip(THEIR_KEYS, THEIR_RATES[s]):
            cols[k] = _draw(r, N_COMMENTS, rng)
        for k, r in zip(OUR_KEYS, OUR_RATES[s]):
            cols[k] = _draw(r, N_COMMENTS, rng)
        data[s] = cols
    return data


def _rate_ci(arr: np.ndarray):
    k, n = int(arr.sum()), len(arr)
    lo, hi = wilson_interval(k, n)
    return {"rate": k / n, "lo": lo, "hi": hi, "n": n}


def compute(data: dict) -> dict:
    R = {"sources": {}, "is_synthetic": True}
    for s in SOURCES:
        m = {k: _rate_ci(data[s][k]) for k in THEIR_KEYS + OUR_KEYS}
        m["structure_avg"] = float(np.mean([m[k]["rate"] for k in ("specification", "justification", "remedy", "anchor")]))
        R["sources"][s] = m
    return R


# ---------------------------------------------------------------------------
def render_figure(R: dict):
    apply_style()
    labels = [SOURCE_LABELS[s] for s in SOURCES]
    x = np.arange(len(SOURCES))
    colors = ["#999999", "#56B4E9", "#009E73", "#E69F00", ACCENT]
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(TEXT_WIDTH, 2.8))

    # Left: their axis (structure avg + consequential) — near parity.
    struct = [R["sources"][s]["structure_avg"] * 100 for s in SOURCES]
    conseq = [R["sources"][s]["consequential"]["rate"] * 100 for s in SOURCES]
    w = 0.38
    axL.bar(x - w / 2, struct, w, color=colors, alpha=0.55, label="structure (avg)")
    axL.bar(x + w / 2, conseq, w, color=colors, alpha=0.95, label="consequential")
    axL.set_xticks(x); axL.set_xticklabels(labels, rotation=20, ha="right")
    axL.set_ylabel("%"); axL.set_ylim(0, 105)
    axL.set_title("ReviewBench axis: form + intent")
    axL.legend(fontsize=7, loc="lower left")

    # Right: correctness axis (what they omit) — AIPR wins.
    metrics = [("anchor_fidelity", "anchor fidelity"), ("citation_grounded", "citation grounded"), ("correctness", "correctness")]
    mw = 0.26
    for i, (key, lab) in enumerate(metrics):
        vals = [R["sources"][s][key]["rate"] * 100 for s in SOURCES]
        err = [[100 * (R["sources"][s][key]["rate"] - R["sources"][s][key]["lo"]) for s in SOURCES],
               [100 * (R["sources"][s][key]["hi"] - R["sources"][s][key]["rate"]) for s in SOURCES]]
        axR.bar(x + (i - 1) * mw, vals, mw, yerr=err, capsize=1.5, label=lab, alpha=0.9)
    axR.set_xticks(x); axR.set_xticklabels(labels, rotation=20, ha="right")
    axR.set_ylabel("%"); axR.set_ylim(0, 105)
    axR.set_title("Correctness axis (ReviewBench omits)")
    axR.legend(fontsize=7, loc="lower left")

    watermark(fig, True)
    for ext in ("pdf", "png"):
        fig.savefig(FIG_DIR / f"figS_comment_quality.{ext}")
    plt.close(fig)


def write_table(R: dict):
    rows = []
    for s in SOURCES:
        m = R["sources"][s]
        rows.append(
            rf"{SOURCE_LABELS[s]} & {100 * m['structure_avg']:.0f}\% & {100 * m['consequential']['rate']:.0f}\% & "
            rf"{100 * m['anchor_fidelity']['rate']:.0f}\% & {100 * m['citation_grounded']['rate']:.0f}\% & "
            rf"{100 * m['correctness']['rate']:.0f}\% \\"
        )
    body = (
        "\\begin{tabular}{lccccc}\n\\toprule\n"
        " & \\multicolumn{2}{c}{ReviewBench axis} & \\multicolumn{3}{c}{Correctness axis (omitted by ReviewBench)} \\\\\n"
        "\\cmidrule(lr){2-3}\\cmidrule(lr){4-6}\n"
        "Source & Structure & Consequential & Anchor fid. & Cite grounded & Correctness \\\\\n\\midrule\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n\\end{tabular}\n"
    )
    (TAB_DIR / "tab_comment_quality.tex").write_text(body, encoding="utf-8")


def write_macros(R: dict):
    L = ["% AUTO-GENERATED by analysis/secondary.py — DO NOT EDIT."]

    def cmd(name, val):
        L.append(rf"\newcommand{{\{name}}}{{{val}\xspace}}")

    def pct(s, k):
        return f"{100 * R['sources'][s][k]['rate']:.0f}"

    cmd("aiprConsequential", pct("aipr", "consequential"))
    cmd("rThreeConsequential", pct("r3", "consequential"))
    cmd("aiprGroundedness", pct("aipr", "citation_grounded"))
    cmd("rThreeGroundedness", pct("r3", "citation_grounded"))
    cmd("aiprAnchorFidelity", pct("aipr", "anchor_fidelity"))
    cmd("rThreeAnchorFidelity", pct("r3", "anchor_fidelity"))
    cmd("aiprCorrectness", pct("aipr", "correctness"))
    cmd("rThreeCorrectness", pct("r3", "correctness"))
    (MACRO_DIR / "secondary_macros.tex").write_text("\n".join(L) + "\n", encoding="utf-8")


def run():
    data = generate()
    R = compute(data)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "secondary.json").write_text(json.dumps(R, indent=2), encoding="utf-8")
    render_figure(R)
    write_table(R)
    write_macros(R)
    print("secondary analysis (comment-quality / ReviewBench axis) written:")
    print(f"  AIPR correctness {100 * R['sources']['aipr']['correctness']['rate']:.0f}% vs "
          f"R3 {100 * R['sources']['r3']['correctness']['rate']:.0f}%; "
          f"AIPR citation-grounded {100 * R['sources']['aipr']['citation_grounded']['rate']:.0f}% vs "
          f"R3 {100 * R['sources']['r3']['citation_grounded']['rate']:.0f}%")
    return R


if __name__ == "__main__":
    run()
