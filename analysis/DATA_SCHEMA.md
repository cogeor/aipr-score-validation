# Data contract — the plug-in point for the score-validation study

Everything downstream (statistics, figures, tables, the numbers baked into the
paper) reads **exactly two CSVs** plus two optional files. When the real
OpenReview export lands, drop files matching this schema into
`analysis/data/<dataset>/` and the entire pipeline reproduces with one command
(`python run_all.py --dataset <name>`). No analysis code changes.

Until then, `synth.py` writes schema-conformant **synthetic** data into
`analysis/data/synthetic/` so figures/tables/formatting are verified end-to-end.
Synthetic outputs are watermarked `SYNTHETIC` on every figure and must never
appear in a posted draft.

**Datasets.** `analysis/data/iclr2026/` is the released v1 export (primary
venue, 3-tier). The Phase-2 export will land as `analysis/data/iclr2025/`
(replication / contaminated-contrast venue, 4-tier incl. spotlight; full-mini
cohort only — no 2025 frontier arm — plus the `full_full_p2` Pillar-1 re-grade
keyed to the 2026 cohort-H ids). The synthetic dataset carries BOTH venues in
one frame, so the per-(venue, year) ladders are exercised side by side.

> **Note on configs.** The study-only **`naive`** baseline config is part of the
> contract. The **`blinded`** and **`prior_only`** configs are dropped;
> `schema.validate` still *accepts* them for backward compatibility, so they are
> marked DEPRECATED below rather than deleted — do not produce new
> `blinded`/`prior_only` rows. The AIPR `confidence` field is **not** a column
> (v6 emits a constant); the only `confidence` here is the per-reviewer
> `reviews.csv` field, which is unrelated.

---

## Required: `submissions.csv` — one row per submission (the labels)

| column | type | values / units | notes |
|--------|------|----------------|-------|
| `submission_id` | str | venue-unique id | join key |
| `venue` | str | e.g. `ICLR` | |
| `year` | int | e.g. `2025` | |
| `decision_raw` | str | literal OpenReview venue tag | e.g. `ICLR.cc/2026/Conference/Oral`, `ICLR 2025 Spotlight`; lets a third party re-derive `decision_tier` from the raw label + the documented map |
| `decision_tier` | str | `reject` \| `poster` \| `spotlight` \| `oral` | the ordinal ground truth, restricted to the row's **(venue, year) ladder** (`common.VENUE_TIERS`): ICLR 2026 is 3-tier (no spotlight); ICLR 2025 is 4-tier (reject < poster < spotlight < oral) |
| `tier_rank` | int | ladder index | the tier's index in the row's (venue, year) ladder — 2026: reject=0, poster=1, oral=2; 2025: reject=0, poster=1, spotlight=2, oral=3. Must agree row-wise with `decision_tier` |
| `accept_bool` | int | `0`/`1` | `1` iff tier_rank ≥ 1 |
| `mean_reviewer_rating` | float | venue rating scale (e.g. 1–10) | continuous ground truth (H4) |
| `rating_std` | float | same units | dispersion across reviewers |
| `n_reviews` | int | ≥1 | |
| `stratum` | str | sampling stratum label | usually == decision_tier |
| `excluded` | int | `0`/`1` | `1` = drop from primary (desk-reject, parse-fail, arxiv-twin) |
| `exclude_reason` | str | free text or empty | required non-empty iff `excluded==1` |
| `primary_area` | str | OpenReview primary-area label | exploratory area-confounding check (#10) |
| `page_count` | int | main+appendix pages | manuscript length; length/formatting confounding (#11) |
| `word_count` | int | manuscript word count | manuscript length metric (#11) |
| `token_count` | int | manuscript length in tokens | manuscript length metric; also the input base for grading token usage |
| `n_references` | int | bibliography size | citation-density confounding (#11) |
| `n_figures` | int | figures in the manuscript | polish/length proxy (#11) |
| `arxiv_prior_to_cutoff` | int | `0`/`1` | `1` = an arXiv preprint of this paper predates the model cutoff. Drives the contamination *sensitivity* split on **retained** papers (headline metric with/without), distinct from the `arxiv_twin` *exclusion* |
| `is_anonymized` | int | `0`/`1` | `1` = the graded PDF is the double-blind submitted version (no author block). At ICLR this is uniformly `1`, so it is recorded as a venue fact, not a per-row driver. The prestige/topic-prior confound on non-blind papers is probed by the sandboxed prestige-perturbation experiment (see the paper's appendix), not a grading config |
| `pdf_sha` | str | hash of the graded PDF | provenance — pins the exact submitted version reviewers saw (not camera-ready / post-rebuttal) |

The seven metadata columns are **optional**: an export predating them still loads
(missing columns are backfilled to NaN/empty, and any confounding check that
needs an all-NaN column self-skips). The synthetic generator emits all of them.

Cohort membership (S/M/H) is **derived**, not stored: a submission is in cohort
H iff it has a `full` grading in `gradings.csv`, in M iff it has a `full_mini`
grading, in S iff it has a `scan` grading. H ⊆ M ⊆ S is asserted at load.

**Population boundary.** Only papers with a real decision tier appear in
`submissions.csv`. Tierless out-of-population papers (withdrawn / desk-rejected /
untagged) are written by `aipr openreview labels` to a separate
`submissions_out_of_population.csv` (with `decision_raw` + reason) and reported —
never silently dropped (`DECISIONS.md §4`), never given a fake tier. The
`excluded`/`exclude_reason` columns here are therefore for **tiered** papers
dropped from a primary metric for a different reason (arXiv-twin, parse failure).

## Required: `gradings.csv` — one row per AIPR grading run

| column | type | values / units | notes |
|--------|------|----------------|-------|
| `submission_id` | str | FK → submissions | |
| `config` | str | `scan` \| `full_mini` \| `full` \| `naive` \| `full_full_p2` \| ~~`blinded`~~ \| ~~`prior_only`~~ | grading profile. `scan`/`full_mini`/`full` are the cost ladder (cohort nesting). **`naive`** = study-only one-paragraph "grade this paper" baseline on the same PDF + model (rung 0 of the value ladder); it emits `overall` only (subscores blank) and carries `pipeline_version=naive`. **`full_full_p2`** = the Phase-2 Pillar-1 re-validation: the same frontier model and v6 pipeline as `full_full` but with the post-fix abstract-based citation audit; carries all five subscores, `pipeline_version=v6`, single run on the frozen cohort-H ids (its ids must nest inside H — invariant 9b). It is **not** remapped onto `full` at load (unlike `full_full`); it stays its own slot, compared against the frozen v1 artifact row. **DEPRECATED (dropped):** `blinded` (full pipeline on a blinded PDF) and `prior_only` (metadata-only). Still accepted by `validate` for backward compatibility; do not emit new rows |
| `run_index` | int | `0`-based | multiple rows per (submission,config) when re-graded |
| `model_name` | str | e.g. `gpt-5.4-mini`, `gpt-5.4` | |
| `pipeline_version` | str | `v6` (or `naive` for `config=naive`) | **must be uniform within the non-naive rows** — never mix v6 with another pipeline version |
| `overall` | float | 0–100 | server-computed weighted mean of the 5 subscores (the single naive output) |
| `novelty` | float | 0–100 | blank for `config=naive` (the naive judge emits no subscores) |
| `rigor` | float | 0–100 | blank for `config=naive` |
| `applicability` | float | 0–100 | blank for `config=naive` |
| `clarity` | float | 0–100 | blank for `config=naive` |
| `citation` | float | 0–100 | audit-adjusted in FULL configs; blank for `config=naive` |
| `input_tokens` | int | tokens | **optional** — prompt/input tokens the grading run consumed ("tokens used"). Drives the cost-design summary; backfilled to NaN if absent |
| `output_tokens` | int | tokens | **optional** — generated output tokens the grading run consumed. With `input_tokens`, the per-config cost numbers |
| `evaluation_id` | str | DB id | provenance |
| `run_kind` | str | `adhoc` | must be `adhoc` (study grades never touch leaderboard) |

When a (submission, config) has multiple `run_index` rows, the analysis uses the
**per-(submission,config) mean** for point estimates and the **within-pair SD**
for the run-variance supplementary figure.

## Optional: `reviews.csv` — human reviews (failure-mode case studies only)

| column | type | notes |
|--------|------|-------|
| `submission_id` | str | FK |
| `reviewer_index` | int | |
| `rating` | float | per-reviewer score |
| `confidence` | float | reviewer self-confidence |
| `text` | str | review body (used for AIPR-vs-human alignment) |

## Optional: `findings.jsonl` — AIPR in-depth output (failure-mode case studies only)

One JSON object per line:
```json
{"submission_id": "...", "config": "full", "weaknesses": ["...", "..."],
 "missing_citations": [{"title": "...", "severity": "serious_omission", "doi": "..."}],
 "justifications": {"novelty": "...", "rigor": "...", ...}}
```

---

## Invariants asserted at load (`schema.py::validate`)

0. Required columns present in each table (clear error naming the missing ones).
1. One row per `submission_id`; `(submission_id, config, run_index)` unique.
2. **Row-wise** `tier_rank` ↔ `decision_tier` bijection under the row's **(venue, year) ladder** (`common.VENUE_TIERS`, the consumer mirror of aipr `decisions.py::_PROFILES`): an unprofiled (venue, year) fails loudly (never a silent fallthrough to another year's ladder), and a tier outside the row's ladder (e.g. spotlight under ICLR 2026) fails. `accept_bool == (tier_rank >= 1)` is ladder-independent (reject is rank 0 in every ladder).
3. `decision_raw` non-empty on every row; `n_reviews ≥ 1`.
4. `pipeline_version` is `v6` across all non-`naive` rows (`full_full_p2` included — never mixed with another version); `config=naive` rows carry `pipeline_version=naive`.
5. `config` ∈ {scan, full_mini, full, naive, full_full_p2} (plus the DEPRECATED `blinded`/`prior_only`, still accepted pending cleanup); `run_index` a nonnegative integer.
6. `overall` ∈ `[0,100]` on every row; the five dimension scores ∈ `[0,100]` where present — they may be **blank only for `config=naive`** (the naive judge emits no subscores; `full_full_p2` carries all five).
7. Every `gradings.submission_id` exists in `submissions`.
8. Cohort nesting H ⊆ M ⊆ S (cost ladder); `naive` (and the deprecated `blinded`/`prior_only`) ⊆ H, so each pairs with a full-text score; **9b:** `full_full_p2` ids ⊆ H (the Pillar-1 re-grade runs on the frozen cohort-H ids only).
9. `excluded==1` ⇒ non-empty `exclude_reason`.
10. `run_kind == 'adhoc'` for every grading row.
11. Metadata domains when present: `arxiv_prior_to_cutoff`/`is_anonymized` ∈ {0,1}; `page_count`/`word_count`/`token_count`/`n_references`/`n_figures` ≥ 0; `input_tokens`/`output_tokens` ≥ 0.

A load that violates any invariant raises — the paper never renders from
malformed data.
