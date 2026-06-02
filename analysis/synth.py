"""Synthetic data generator — schema-conformant DUMMY data for formatting checks.

Generates a plausible monotone signal (a latent paper "quality" drives the
decision tier, the reviewer rating, and — more noisily — the AIPR subscores) so
the full pipeline, every figure, and every table render exactly as they will on
real data. Output is watermarked SYNTHETIC and tagged ``model_name=*-synthetic``.

NOT a simulation study and NOT evidence of anything: the effect sizes here are
hand-set so the layout is exercised across the realistic range. Replace
``data/synthetic/`` with the real OpenReview export and rerun — no code changes.
"""

from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

from common import (
    COHORT_H_SPLIT,
    COHORT_M_SPLIT,
    DATA_DIR,
    DIMENSIONS,
    GLOBAL_SEED,
    SCORE_WEIGHTS,
    SUBJECT_AREAS,
    TIER_ORDER,
    TIER_RANK,
)

# Per-tier latent-quality mean (sd shared) — drives separation across tiers.
TIER_Q_MEAN = {"reject": -0.9, "poster": 0.0, "spotlight": 0.6, "oral": 1.1}
Q_SD = 0.6

# Dimension loadings on latent quality (novelty/applicability strong; citation weak),
# mirroring the v6 weighting rationale.
DIM_LOAD = {"novelty": 1.15, "rigor": 0.75, "applicability": 1.05, "clarity": 0.55, "citation": 0.40}
DIM_BASE = {"novelty": 60, "rigor": 63, "applicability": 60, "clarity": 66, "citation": 70}

# Per-config noise SD and signal gain. Both pipeline configs run the full v6
# pipeline; `full` (frontier model) is tightest, `full_mini` (cheap model)
# slightly noisier — the model is the only difference. `naive` is the "why us"
# baseline: the SAME model as full but a single one-paragraph prompt with no
# rubric/audit — hand-set NOISIER and WEAKER than full so its AUROC sits clearly
# below full (the pipeline adds discrimination) and its run-to-run SD sits clearly
# above full (the pipeline adds reliability).
CONFIG_NOISE = {"full_mini": 7.0, "full": 6.0, "naive": 12.0}
CONFIG_GAIN = {"full_mini": 12.5, "full": 13.5, "naive": 8.0}
CONFIG_MODEL = {
    "full_mini": "gpt-5.4-mini-synthetic",
    "full": "gpt-5.4-synthetic",
    "naive": "gpt-5.4-synthetic",  # same model as full — only the pipeline differs
}
CONFIG_RUNS = {"full_mini": 1, "full": 2, "naive": 3}

# Naive overall = single noisy draw on latent quality (no five-subscore averaging,
# so its run SD is larger than full's by construction).
NAIVE_BASE = 62.0

# Synthetic grading token usage ("tokens used"). Both pipeline configs are
# two-pass (reviewer + audit) so read the manuscript twice; naive reads it once
# (single prompt). Output reflects how much the config writes (the audit pass
# adds findings/citations).
CONFIG_PASSES = {"full_mini": 2, "full": 2, "naive": 1}
CONFIG_INPUT_OVERHEAD = {"full_mini": 2500, "full": 2500, "naive": 1000}
CONFIG_OUTPUT_MEAN = {"full_mini": 1500, "full": 2500, "naive": 400}


def _usage(token_count: int, config: str, rng: np.random.Generator) -> tuple[int, int]:
    inp = CONFIG_PASSES[config] * token_count + CONFIG_INPUT_OVERHEAD[config] + rng.normal(0, 200)
    out = CONFIG_OUTPUT_MEAN[config] + rng.normal(0, 120)
    return int(max(0, inp)), int(max(0, out))


def _naive_overall(q: float, rng: np.random.Generator) -> float:
    """A single noisy overall grade from latent quality — the naive judge's only
    output (no subscores). Weaker gain + larger noise than full by design."""
    val = NAIVE_BASE + CONFIG_GAIN["naive"] * q + rng.normal(0, CONFIG_NOISE["naive"])
    return float(np.clip(val, 0, 100))


def _subscores(q: float, config: str, rng: np.random.Generator) -> dict:
    gain, noise = CONFIG_GAIN[config], CONFIG_NOISE[config]
    s = {}
    for d in DIMENSIONS:
        val = DIM_BASE[d] + gain * DIM_LOAD[d] * q + rng.normal(0, noise)
        s[d] = float(np.clip(val, 0, 100))
    overall = sum(SCORE_WEIGHTS[d] * s[d] for d in DIMENSIONS) / sum(SCORE_WEIGHTS.values())
    s["overall"] = float(np.clip(overall, 0, 100))
    return s


def _make_venue(venue: str, year: int, mini_split: dict, full_split: dict | None, rng) -> tuple[list, list, list, list]:
    """Build one venue's synthetic cohorts.

    ``mini_split`` (tier->count) is the full-mini cohort M = the graded
    submission population for this venue (the primary large-N cohort).
    ``full_split`` (tier->count, or None) is the nested frontier cohort H ⊆ M,
    graded additionally by `full` + the `naive` baseline; ``None`` makes a
    full-mini-only venue (the pre-cutoff replication contrast). H ⊆ M holds by
    construction (the first ``full_split[tier]`` papers per tier are also in H).

    Returns (submission_rows, grading_rows, review_rows, findings)."""
    subs, grads, reviews, findings = [], [], [], []
    sid = 0
    for tier in TIER_ORDER:
        n_mini = mini_split[tier]
        n_full = full_split[tier] if full_split else 0
        for k in range(n_mini):
            sid += 1
            sub_id = f"{venue}{year}-{sid:04d}"
            q = rng.normal(TIER_Q_MEAN[tier], Q_SD)
            rating = float(np.clip(3.0 + 1.4 * q + rng.normal(0, 0.8), 1, 10))
            n_rev = int(rng.integers(3, 5))
            rstd = float(np.clip(rng.normal(1.2, 0.4), 0.3, 3.0))
            excluded, reason = 0, ""
            if rng.random() < 0.02:  # ~2% excluded
                excluded = 1
                reason = rng.choice(["arxiv_twin", "parse_fail", "desk_reject"])
            # Manuscript-surface + provenance metadata. Deliberately drawn
            # INDEPENDENT of latent quality q, so the confounding checks render
            # the honest default (AIPR does not merely reward length / area).
            decision_raw = f"{venue}.cc/{year}/Conference/{tier.capitalize()}"
            pdf_sha = hashlib.sha1(f"{sub_id}-submitted".encode()).hexdigest()[:16]
            page_count = int(np.clip(rng.normal(9.5, 1.3), 6, 14))
            word_count = int(np.clip(page_count * rng.normal(680, 60), 2000, 14000))
            token_count = int(word_count * 1.33)  # ~tokens per word for English prose
            subs.append(
                {
                    "submission_id": sub_id, "venue": venue, "year": year,
                    "decision_raw": decision_raw,
                    "decision_tier": tier, "tier_rank": TIER_RANK[tier],
                    "accept_bool": int(TIER_RANK[tier] >= 1),
                    "mean_reviewer_rating": rating, "rating_std": rstd, "n_reviews": n_rev,
                    "stratum": tier, "excluded": excluded, "exclude_reason": reason,
                    "primary_area": str(rng.choice(SUBJECT_AREAS)),
                    "page_count": page_count,
                    "word_count": word_count,
                    "token_count": token_count,
                    "n_references": int(np.clip(rng.normal(45, 12), 10, 120)),
                    "n_figures": int(rng.integers(3, 9)),
                    "arxiv_prior_to_cutoff": int(rng.random() < 0.30),
                    "is_anonymized": 1,  # ICLR submissions are double-blind
                    "pdf_sha": pdf_sha,
                }
            )
            # cohort membership: every paper in this venue is in cohort M
            # (full_mini); the first ``n_full`` per tier are also in cohort H
            # (full + naive). H ⊆ M by construction.
            in_h = k < n_full
            present = ["full_mini"]
            if in_h:
                present.append("full")
                # naive-judge baseline (rung 0), paired on cohort H
                present.append("naive")
            for config in present:
                for run_idx in range(CONFIG_RUNS[config]):
                    in_tok, out_tok = _usage(token_count, config, rng)
                    if config == "naive":
                        # overall only; the five subscores are blank by design
                        # (a one-paragraph judge produces no calibrated subscores)
                        scores = {"overall": _naive_overall(q, rng), **{d: "" for d in DIMENSIONS}}
                    else:
                        s = _subscores(q, config, rng)
                        scores = {"overall": s["overall"], **{d: s[d] for d in DIMENSIONS}}
                    grads.append(
                        {
                            "submission_id": sub_id, "config": config, "run_index": run_idx,
                            "model_name": CONFIG_MODEL[config],
                            # naive is NOT the v6 pipeline (single prompt, no audit) — mark it
                            # honestly so pipeline_version never implies a pipeline it didn't run
                            "pipeline_version": ("naive" if config == "naive" else "v6"),
                            "overall": scores["overall"], **{d: scores[d] for d in DIMENSIONS},
                            "input_tokens": in_tok, "output_tokens": out_tok,
                            "evaluation_id": f"ev-{sub_id}-{config}-{run_idx}", "run_kind": "adhoc",
                        }
                    )
            # minimal reviews + findings for the few H papers (case-study fixtures)
            if in_h:
                for ri in range(n_rev):
                    reviews.append(
                        {
                            "submission_id": sub_id, "reviewer_index": ri,
                            "rating": float(np.clip(rating + rng.normal(0, rstd), 1, 10)),
                            "confidence": int(rng.integers(2, 6)),
                            "text": f"[synthetic review {ri} for {sub_id}] weaknesses noted: limited novelty, missing baselines.",
                        }
                    )
                findings.append(
                    {
                        "submission_id": sub_id, "config": "full",
                        "weaknesses": ["Contribution overlaps prior work", "Evaluation lacks a strong baseline"],
                        "missing_citations": [{"title": "A closely related prior method", "severity": "serious_omission", "doi": "10.0000/synthetic"}],
                        "justifications": {d: f"synthetic justification for {d}" for d in DIMENSIONS},
                    }
                )
    return subs, grads, reviews, findings


def generate() -> None:
    rng = np.random.default_rng(GLOBAL_SEED)
    out = DATA_DIR / "synthetic"
    out.mkdir(parents=True, exist_ok=True)

    # Primary venue (ICLR 2026, post-cutoff): full-mini cohort M (n=300) with a
    # nested frontier cohort H (n=100) + naive baseline.
    s1, g1, r1, f1 = _make_venue("ICLR", 2026, COHORT_M_SPLIT, COHORT_H_SPLIT, rng)
    # Replication venue (ICLR 2025, pre-cutoff contaminated contrast): full-mini
    # only — the cheap large-N config now that scan is gone.
    rep_split = {"reject": 90, "poster": 50, "spotlight": 30, "oral": 30}
    s2, g2, r2, f2 = _make_venue("ICLR", 2025, rep_split, None, rng)

    subs = pd.DataFrame(s1 + s2)
    grads = pd.DataFrame(g1 + g2)
    subs.to_csv(out / "submissions.csv", index=False)
    grads.to_csv(out / "gradings.csv", index=False)
    pd.DataFrame(r1 + r2).to_csv(out / "reviews.csv", index=False)
    with open(out / "findings.jsonl", "w", encoding="utf-8") as fh:
        for rec in f1 + f2:
            fh.write(json.dumps(rec) + "\n")

    print(f"wrote {len(subs)} submissions, {len(grads)} gradings -> {out}")
    print("cohort sizes (primary ICLR2026):")
    g_primary = grads[grads["submission_id"].str.startswith("ICLR2026")]
    for c in ("full_mini", "full", "naive"):
        print(f"  {c:10s}: {g_primary[g_primary['config'] == c]['submission_id'].nunique()} submissions")


if __name__ == "__main__":
    generate()
