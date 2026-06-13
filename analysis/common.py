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

# Decision-tier ladders are per-(venue, year). ICLR 2026 — the primary venue —
# awards Poster + Oral only; there is no Spotlight tier (verified live
# 2026-06-04: 5,128 posters / 224 orals / 0 spotlights). ICLR 2025 — the
# Phase-2 replication / contaminated-contrast venue — awards FOUR tiers
# (adds Spotlight between Poster and Oral). ``VENUE_TIERS`` is the
# consumer-side lockstep mirror of the producer's per-venue-year profile
# table at aipr ``platform/openreview/decisions.py::_PROFILES``; any tier
# change lands on BOTH sides in the same change-set, and ``schema.py``'s
# row-wise bijection validates every submission row against its own
# (venue, year) ladder at load.
VENUE_TIERS: dict[tuple[str, int], tuple[str, ...]] = {
    ("ICLR", 2026): ("reject", "poster", "oral"),
    ("ICLR", 2025): ("reject", "poster", "spotlight", "oral"),
}


def tiers_for(venue: str, year: int) -> tuple[str, ...]:
    """The decision-tier ladder (low->high) for ``(venue, year)``.

    Raises ``KeyError`` with a clear message for an unprofiled (venue, year) —
    never a silent fallthrough to another year's ladder (the consumer mirror of
    the producer's ``unknown_venue_year`` refusal)."""
    key = (venue, int(year))
    if key not in VENUE_TIERS:
        raise KeyError(
            f"no tier ladder profiled for (venue, year)={key}; extend common.VENUE_TIERS"
            " in lockstep with aipr platform/openreview/decisions.py::_PROFILES"
        )
    return VENUE_TIERS[key]


def tier_rank_for(venue: str, year: int) -> dict[str, int]:
    """``{tier: ordinal rank}`` under the (venue, year) ladder (reject is 0)."""
    return {t: i for i, t in enumerate(tiers_for(venue, year))}


# The PRIMARY (ICLR 2026) ladder, kept module-level: the primary-cohort
# semantics baked into stats.py and the existing figures all operate on 2026
# frames, so the back-compat names stay pinned to the primary ladder.
TIER_ORDER = VENUE_TIERS[("ICLR", 2026)]
TIER_RANK = {t: i for i, t in enumerate(TIER_ORDER)}
TIER_LABELS = {"reject": "Reject", "poster": "Poster", "spotlight": "Spotlight", "oral": "Oral"}

# Two strictly nested configs, identical pipeline, differing only in MODEL TIER.
# `full_mini` runs every call on the cheap model; the frontier arm runs every
# call on the frontier model. In the released data the frontier config id is
# `full_full` (all-frontier, adopted 2026-06); ``load_dataset`` maps it onto the
# `full` slot used throughout the analysis. (The earlier mixed `full` — frontier
# reviewer, mini editor — is superseded; a former single-call `scan` config was
# also dropped: that prompt is not how AIPR grades.) This is now a clean
# model-tier contrast over an identical pipeline. Cohort nesting (H subset M) is
# asserted over these two; the naive baseline below is an extra grading on
# cohort H and does not participate in the nesting invariant.
CONFIGS = ("full_mini", "full")
# Naive-judge baseline (the "why us" experiment): the SAME model as `full_full`,
# the SAME PDF input, but a single one-paragraph prompt with no rubric/audit/
# grounding — what a researcher gets pasting a paper into ChatGPT. Graded on
# cohort H so it is paired with the full-pipeline score; this is rung 0 of the
# naive->full_mini->full_full value ladder. It honestly produces only an OVERALL
# grade (no calibrated subscores), so naive rows carry `overall` and leave the
# five subscores blank. (The former `blinded`/`prior_only` leakage configs were
# dropped; leakage is now handled by the temporal contamination controls plus a
# standalone prestige-perturbation experiment — see the paper's Methods.)
BASELINE_CONFIGS = ("naive",)
# Pillar-1 re-validation config (Phase 2): the SAME frontier model and v6
# pipeline as the released `full_full`, re-run AFTER the abstract-based
# citation-audit fix (post-#7), single run on the frozen cohort-H ids
# (schema invariant 9b: its ids must nest inside cohort H). Deliberately NOT
# remapped onto the `full` slot (unlike `full_full` -> `full` in
# schema.load_dataset): it is a new-validation arm compared against the
# frozen v1 artifact row, so it keeps its own config id end to end. Mirrors
# the producer registry at aipr ``cli/openreview.py::STUDY_CONFIGS``.
P2_CONFIGS = ("full_full_p2",)
ALL_CONFIGS = CONFIGS + BASELINE_CONFIGS + P2_CONFIGS
# Display labels only (the dict KEYS and the released CSV column keys are unchanged:
# full_mini / full / naive). Scheme: METHOD (model), method primary. "Direct" is the
# neutral standard term for a single-prompt baseline (replaces the strawman-flavored
# "naive"); "AIPR" carries the production system name across both model tiers.
CONFIG_LABELS = {
    "full_mini": "AIPR (GPT-5.4-mini)",
    "full": "AIPR (GPT-5.4)",
    "naive": "Direct (GPT-5.4)",
    "full_full_p2": "AIPR (GPT-5.4, post-fix citation audit)",
}

# The config whose numbers become the paper's headline. Full-mini carries the
# statistical power (large N: cohort M, n=300); the frontier `full_full` cohort
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
# Cohort M (full-mini, primary large-N, n=300) ⊇ Cohort H (frontier full_full,
# n=100). H is reject-heavy (low-end emphasis where H1 lives) and oversamples
# the accept tiers slightly relative to M; H ⊆ M is enforced by the nested draw.
# Three tiers — ICLR 2026 has no Spotlight. Mirrors aipr's
# ``cli/openreview.py::COHORT_*_SPLIT`` — keep in lockstep.
COHORT_M_SPLIT = {"reject": 150, "poster": 100, "oral": 50}  # full-mini, n=300
COHORT_H_SPLIT = {"reject": 50, "poster": 30, "oral": 20}    # full_full, n=100 (⊆ M)
# Phase-2 (ICLR 2025) full-mini cohort: stratified n=300 across the FOUR 2025
# tiers. PLACEHOLDER split — it drives the synthetic generator ONLY; the REAL
# split is sized from the observed 2025 tier proportions once the bare
# `labels` manifest exists and is recorded in the DECISIONS.md Phase-2
# addendum (spec §2 ordering note) before `select-cohort` freezes ids.
# NO 2025 frontier arm (confirmation arm; mini is the deployable tier).
COHORT_M25_SPLIT = {"reject": 180, "poster": 85, "spotlight": 15, "oral": 20}  # n=300
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
    "spotlight": "#009E73",  # bluish green — between poster and oral on the 2025 ladder
    "oral": "#0072B2",       # blue
}
CONFIG_COLORS = {
    "full_mini": "#56B4E9",   # sky blue — the primary large-N cohort
    "full": "#0072B2",        # blue — the frontier (production) cohort
    "naive": "#F0E442",       # yellow — the baseline floor
}
ACCENT = "#0072B2"
NEUTRAL = "#555555"

GLOBAL_SEED = 20260601


def apply_style() -> None:
    """Apply a clean, vector-friendly matplotlib style that mirrors the interactive
    ``/publications`` figures (the visual baseline): sans-serif text, a barely-there
    dashed grid (black at ~10\% alpha, matching the web's ``#00000010``), dark-ink
    labels with soft-grey ticks/spines, and the same Okabe--Ito tier palette."""
    import matplotlib as mpl

    mpl.rcParams.update(
        {
            "figure.dpi": 130,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            # Sans-serif + dejavusans mathtext to match the web's clean chart text.
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
            "mathtext.fontset": "dejavusans",
            "font.size": 9,
            "axes.titlesize": 9,
            "axes.labelsize": 10,
            "legend.fontsize": 8,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "text.color": "#1a1a1a",
            "axes.labelcolor": "#1a1a1a",
            "axes.edgecolor": "#6b7280",
            "xtick.color": "#6b7280",
            "ytick.color": "#6b7280",
            "axes.spines.top": False,
            "axes.spines.right": False,
            # Web baseline grid: light, dashed "3 3", sitting under the data.
            "axes.grid": True,
            "grid.color": "#000000",
            "grid.alpha": 0.10,
            "grid.linewidth": 0.6,
            "grid.linestyle": (0, (3, 3)),
            "axes.axisbelow": True,
            "lines.linewidth": 1.6,
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
