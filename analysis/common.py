"""Shared paths, constants, and plotting style for the score-validation analysis.

Single source of truth for the dimension vocabulary, the decision-tier order,
the canonical AIPR-score column, and a LaTeX-matching matplotlib style so every
figure is visually consistent and drops straight into the paper.
"""

from __future__ import annotations

from pathlib import Path

# ----------------------------------------------------------------------------
# Paths (all relative to the analysis/ directory)
# ----------------------------------------------------------------------------
ANALYSIS_DIR = Path(__file__).resolve().parent
PAPER_DIR = ANALYSIS_DIR.parent / "paper"
DATA_DIR = ANALYSIS_DIR / "data"
RESULTS_DIR = ANALYSIS_DIR / "results"
FIG_DIR = PAPER_DIR / "figures"
TAB_DIR = PAPER_DIR / "tables"
MACRO_DIR = PAPER_DIR / "macros"

for _d in (RESULTS_DIR, FIG_DIR, TAB_DIR, MACRO_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------------
# Domain vocabulary — must match the deployed AIPR scoring vocabulary.
# ----------------------------------------------------------------------------
DIMENSIONS = ("novelty", "rigor", "applicability", "clarity", "citation")
DIM_LABELS = {
    "novelty": "Novelty",
    "rigor": "Rigor",
    "applicability": "Applicability",
    "clarity": "Clarity",
    "citation": "Citation",
}

# v6 overall = weighted mean of the five subscores.
SCORE_WEIGHTS = {"novelty": 4.0, "rigor": 2.0, "applicability": 4.0, "clarity": 1.0, "citation": 0.5}

TIER_ORDER = ("reject", "poster", "spotlight", "oral")
TIER_RANK = {t: i for i, t in enumerate(TIER_ORDER)}
TIER_LABELS = {"reject": "Reject", "poster": "Poster", "spotlight": "Spotlight", "oral": "Oral"}

# The cost ladder: two strictly nested grading configs. BOTH run the full v6
# pipeline (reviewer pass + audit/grounding); they differ ONLY in the reviewer
# model — `full_mini` on the cheap model, `full` on the frontier model. Cohort
# nesting (H subset M) is asserted over these two; the naive baseline below is
# an extra grading on cohort H and does not participate in the nesting invariant.
# (A former `scan` config — a cheap single-call SCAN-mode grade, NOT the grading
# pipeline — was dropped: that prompt is not how AIPR grades, so it never
# belonged in a study validating the grading pipeline. The study now grades the
# real pipeline at two model tiers.)
CONFIGS = ("full_mini", "full")
# Naive-judge baseline (the "why us" experiment): the SAME model as `full`, the
# SAME PDF input, but a single one-paragraph prompt with no rubric/audit/grounding
# — what a researcher gets pasting a paper into ChatGPT. Graded on cohort H so it
# is paired with the full-pipeline score; this is rung 0 of the naive->full_mini->full
# value ladder. It honestly produces only an OVERALL grade (no calibrated
# subscores), so naive rows carry `overall` and leave the five subscores blank.
# (The former `blinded`/`prior_only` leakage configs were dropped; leakage is now
# handled by the temporal contamination controls plus a standalone
# prestige-perturbation experiment — see the paper's Methods and appendix.)
BASELINE_CONFIGS = ("naive",)
ALL_CONFIGS = CONFIGS + BASELINE_CONFIGS
CONFIG_LABELS = {
    "full_mini": "Full (mini)",
    "full": "Full (GPT-5.4)",
    "naive": "Naive judge",
}

# The config whose numbers become the paper's headline. Full-mini carries the
# statistical power (large N: cohort M, n=300); the frontier `full` cohort
# (n=100) confirms it. See the paper's Methods for the mini->frontier bridge
# argument that licenses the large-N full-mini results as a proxy for the
# production (frontier) score.
PRIMARY_CONFIG = "full_mini"
PRODUCTION_CONFIG = "full"

# ----------------------------------------------------------------------------
# Locked study design — single source of truth (see DECISIONS.md).
# Everything that referenced a hardcoded venue/split now reads these.
# ----------------------------------------------------------------------------
# Primary = ICLR 2026: decisions/reviews released Jan 2026, AFTER the grading
# model's Aug-31-2025 knowledge cutoff -> the OUTCOME cannot be memorized
# (contamination check, see DECISIONS.md). Replication = ICLR 2025, which is
# fully pre-cutoff and therefore serves as a deliberate *contaminated contrast*
# (and the settled citation-outcome secondary).
PRIMARY_VENUE = ("ICLR", 2026)       # decision 1 (revised for contamination)
REPLICATION_VENUE = ("ICLR", 2025)   # contaminated contrast + citation secondary
# Cohort M (full-mini, primary large-N) = 3x the frontier split, so H ⊆ M with
# identical stratum proportions; Cohort H (full, frontier) ⊆ M.
COHORT_M_SPLIT = {"reject": 135, "poster": 75, "spotlight": 45, "oral": 45}  # full-mini, n=300
COHORT_H_SPLIT = {"reject": 45, "poster": 25, "spotlight": 15, "oral": 15}   # full, n=100 (⊆ M)
VARIANCE_SUBSTUDY_PAPERS = 10        # decision 3: ~10 papers re-graded for run variance
BAND_QUANTILE = 0.2                  # primary low-end band = bottom quintile
RELIABILITY_BINS = 10                # deciles for the reliability curve
N_BOOT = 4000                        # bootstrap resamples for CIs
N_PERM = 10000                       # permutations for the Monte Carlo trend test

# Real ICLR 2026 population prevalence, for the natural-prevalence reweighting
# point estimate (the balanced cohort over-samples the accept tiers). Source:
# ICLR 2026 review-process retrospective — 13,763 submissions, 5,355 accepted,
# 8,408 rejected, 27.4% acceptance. The figS_prevalence sweep stays as the
# sensitivity band; this is the single headline operating point.
NAT_ACCEPT_RATE = 0.274

# ICLR-like subject areas, for the exploratory area-confounding check (whether
# AIPR systematically scores some areas higher). Real export fills the true
# OpenReview primary-area field; synth samples from this list.
SUBJECT_AREAS = (
    "Deep Learning",
    "Reinforcement Learning",
    "Generative Models",
    "Optimization",
    "Theory",
    "Applications",
)

# Colour-blind-safe palette (Okabe-Ito), tier-ordered light->dark by quality.
TIER_COLORS = {
    "reject": "#D55E00",     # vermillion
    "poster": "#E69F00",     # orange
    "spotlight": "#56B4E9",  # sky blue
    "oral": "#0072B2",       # blue
}
CONFIG_COLORS = {
    "full_mini": "#56B4E9",  # sky blue — the primary large-N cohort
    "full": "#0072B2",       # blue — the frontier (production) cohort
    "naive": "#F0E442",      # yellow — the baseline floor
}
ACCENT = "#0072B2"
NEUTRAL = "#555555"

GLOBAL_SEED = 20260601


def apply_style() -> None:
    """Apply a clean, publication-grade matplotlib style (serif, vector-friendly)."""
    import matplotlib as mpl

    mpl.rcParams.update(
        {
            "figure.dpi": 130,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "font.family": "serif",
            "font.serif": ["DejaVu Serif", "Times New Roman", "Computer Modern Roman"],
            "font.size": 9,
            "axes.titlesize": 9,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linewidth": 0.5,
            "axes.axisbelow": True,
            "lines.linewidth": 1.4,
            "legend.frameon": False,
            "pdf.fonttype": 42,  # editable text in vector output
            "ps.fonttype": 42,
        }
    )


# Single-column / double-column widths for a typical conference style (inches).
COL_WIDTH = 3.35
TEXT_WIDTH = 6.9


def watermark(fig, is_synthetic: bool) -> None:
    """Stamp SYNTHETIC across a figure so dummy-data renders can never be mistaken
    for results. No-op for real data."""
    if not is_synthetic:
        return
    fig.text(
        0.5,
        0.5,
        "SYNTHETIC",
        fontsize=44,
        color="red",
        alpha=0.10,
        ha="center",
        va="center",
        rotation=30,
        zorder=1000,
        transform=fig.transFigure,
    )
