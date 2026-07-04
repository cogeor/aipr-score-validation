# Pre-registration / DECISIONS — score-validation study

**Status: FROZEN** (3-tier design, re-frozen 2026-06-04; supersedes the
`prereg-iclr2026-v1` freeze — see the 2026-06-04 revision note below). This file
is the commitment device, reproduced verbatim in the paper's appendix and the
reference a reviewer checks the analysis against. The authoritative freeze anchor
is the **public timestamp** of this commit + the `prereg-iclr2026-v2` tag on the
open remote (`github.com/cogeor/aipr-score-validation`); the in-file stamps below
are the human-readable marker (commit dates are forgeable — the push/tag time on
the remote is the evidence). **No AIPR score was joined to any decision outcome
before this freeze** — the 3-tier revision is a pre-data design change: the cohort
manifest has not been drawn and no grading has run.

> **Revised 2026-06-02 (pre-data):** the cheap single-call `scan` config was
> dropped — it is the SCAN-mode prompt, not how AIPR grades, so it does not belong
> in a study validating the grading pipeline. The study now grades the **full
> two-pass pipeline at two model tiers**: `full-mini` (cheap model, primary
> large-N cohort, n≈300) and `full` (frontier model, n=100). The cohorts collapse
> from S/M/H to **M ⊇ H** and the H5 bridge becomes mini→frontier.

> **Revised 2026-06-04 (pre-data, 3-tier):** a live audit of the primary venue
> (`ICLR.cc/2026/Conference`) found it awards **Poster + Oral only — there is no
> Spotlight tier** (5,128 posters / 224 orals / 0 spotlights). The design drops to
> **three ordinal tiers `reject < poster < oral`** (ranks 0/1/2). Cohort splits
> are revised to **M = 150 / 100 / 50** (reject/poster/oral, n=300) and
> **H = 50 / 30 / 20** (n=100, ⊆ M). The **ICLR 2025 replication is deferred** —
> the first analysis is ICLR 2026 only (ICLR 2025 *does* have a spotlight tier and
> would need a separate collapse decision; reinstated as future work). This is a
> pre-data change → **re-freeze required** (new tag, e.g. `prereg-iclr2026-v2`).

> **Contamination scope (decided 2026-06-02):** the load-bearing control is the
> model knowledge cutoff (GPT-5.4, Aug 31 2025) preceding the ICLR 2026 decision
> release (Jan 2026) — the outcome cannot have been in training. A prospective
> ICLR 2027 arm is **not required** and is dropped as a dependency (it would only
> strengthen analyst-blinding, already covered by this frozen plan + the fully
> scripted deterministic pipeline). Two standing conditions: confirm the cutoff
> against the model card, and ensure the grading run has no inference-time access
> to the venue's decision pages.

- **Frozen (v2, 3-tier):** tag `prereg-iclr2026-v2`, date `2026-06-04` (run
  `git rev-parse prereg-iclr2026-v2` for the commit; the tag on the remote is the anchor)
- **Prior freeze (superseded):** tag `prereg-iclr2026-v1`, commit `375ccb8`, date `2026-06-02`
- **Approved by:** `cgeor (costa.georgantas@gmail.com)`

---

## 1. Object of study
The AIPR v6 paper-scoring pipeline, treated as a fixed black box. Five 0--100
dimension scores (novelty, rigor, applicability, clarity, citation) and the
server-computed weighted overall (Eq. 1 in the paper). The model is not tuned on
the venue, decisions, or ratings, and no model is trained/fine-tuned on the
evaluation data. **Pipeline version v6 only**, never mixed in a cohort.

## 2. Data and ground truth
- **Primary venue:** **ICLR 2026** (open review => rejected submissions public;
  13,763 submissions, 5,355 acc / 8,408 rej, 27.4%). *Revised from ICLR 2025
  after the contamination check:* the grading model **gpt-5.4 has an Aug 31 2025
  knowledge cutoff** (confirm against OpenAI's model card), while ICLR 2026
  decisions and reviews were released **Jan 22 2026** — ~5 months post-cutoff, so
  the model cannot have memorized the outcome. ICLR 2025 (decisions Jan 2025) is
  fully pre-cutoff and was therefore demoted to a deliberate *contaminated
  contrast* (replication, below). Submitted PDFs are used; a subset of ICLR 2026
  papers had arXiv preprints before the cutoff, handled by the arXiv-split
  robustness check below.
- **Ground truths:** (a) decision tier `reject < poster < oral`
  and its binary accept/reject collapse; (b) mean reviewer rating (continuous).
- **PDF version graded:** the **submitted** version (what reviewers saw).
- **Reviewer-rating aggregation:** arithmetic **mean** across a submission's
  reviews; `n_reviews` recorded. *(Sensitivity to median/trimmed-mean reported in
  supplementary, not as the primary.)*

## 3. Sampling and cohorts
Both pipeline cohorts run the identical full two-pass pipeline (reviewer + audit);
they differ only in the reviewer model tier.
- **Cohort M (full pipeline, cheap model):** the primary large-N cohort,
  stratified, n = 300. *Decided split: 150 reject / 100 poster / 50 oral* — H ⊆ M
  nests by construction and the reject-heavy low-end emphasis (where H1 lives) is
  preserved.
- **Cohort H (full pipeline, frontier model):** stratified subset, n = 100,
  **oversampling reject**. *Decided split: 50 reject / 30 poster / 20 oral* —
  keeps both the binary low-end claim (H1/H2) and the three-tier gradient (H3) on
  the frontier cohort. (Power is already saturated for the binary test at n=100,
  so no need to collapse tiers for AUROC power.)
- **Nesting:** H ⊆ M (each frontier grading also has a cheap-model score).
- **Manifest:** the exact submission ids + stratum + assigned config are frozen
  in a committed manifest before any frontier grading. The manifest also flags
  the ~10 papers earmarked for the variance sub-study (below).
- **Budget unit:** *Decided: 100 distinct papers, single frontier run each.*
  Cross-paper metrics use the full n=100; per the power analysis n=100 is amply
  powered single-run.
  - **Variance sub-study (optional augmentation):** additionally re-grade ~10
    pre-selected papers (spanning the score range) 2–3× on the frontier model to
    estimate within-paper run variance directly. This is ~10–20 extra grades on
    top of the 100, not a reallocation; the main cohort stays at 100 distinct
    papers. `analysis` already supports it (`run_variance` uses only the repeated
    subset; `figS_run_variance`).
- **Second-venue replication — DEFERRED (2026-06-04):** the first analysis is
  **ICLR 2026 only**. The ICLR 2025 replication (full-mini, contaminated contrast)
  is reinstated as future work — ICLR 2025 *does* have a spotlight tier, and how to
  collapse it into the 3-tier scale is a separate decision not taken here. The
  analysis pipeline still supports it (run_all's replication section self-activates
  when 2025 rows are present), so reinstating it is additive, not a redesign. (ICLR
  2024 likewise remains available as a future full-mini fold.)

### Contamination controls (added by the contamination check)
1. **Primary cohort decisions postdate the model cutoff** (Jan 2026 vs Aug 2025)
   -> outcome-uncontaminated by construction. This is the main control.
2. **arXiv-split robustness:** flag ICLR 2026 submissions whose arXiv preprint
   predates Aug 31 2025; report the headline metrics with and without them to
   bound residual paper-text leakage. (The self-identity step already detects
   arXiv twins.)
3. **Contaminated contrast — DEFERRED:** the ICLR 2025 (fully pre-cutoff)
   contaminated-contrast run is future work (see §3). The model-cutoff control (#1)
   and the arXiv-split (#2) carry the contamination argument for the 2026-only
   first analysis.
4. **Gold-standard prospective confirmation (optional follow-up): ICLR 2027.**
   Pre-register now, grade submissions when they post (~Sept 2026) **before**
   decisions (~Jan 2027) -> contamination logically impossible. Reported as a
   confirmatory addendum, not a launch dependency.
5. **Confirm the gpt-5.4 cutoff** (Aug 31 2025) against OpenAI's official model
   card before relying on it; if it is later than Jan 2026, escalate to the
   prospective ICLR 2027 design as primary.

## 4. Exclusions (applied before any primary metric)
Excluded and reported with counts/reasons: desk-rejects and
withdrawn-before-review (no reviewer signal); PDF parse failures; submissions the
self-identity step flags as an already-published manuscript under a different
title (arXiv-twin leakage in the citation audit). Excluded rows never enter a
primary metric.

## 5. Hypotheses, metrics, and decision rules
Effect sizes with 95% bootstrap CIs lead every claim. CIs: 4,000-resample
percentile bootstrap. Trend test: Jonckheere--Terpstra, 10,000-resample Monte
Carlo permutation p. Seed fixed (`common.GLOBAL_SEED`).

| # | Hypothesis | Metric | Pre-declared success |
|---|-----------|--------|----------------------|
| **H1 (primary)** | Weak work is flagged | Bottom-quintile reject rate; **lift over base rate** with Wilson CI; oral share in band | Lift CI lower bound > 1; oral share ~0 |
| H2 | Reject/accept separation | AUROC (overall), bootstrap CI | CI excludes 0.5; point ≥ 0.70 pre-declared "strong" |
| H3 | Monotone tier gradient | JT permutation p; Spearman ρ(score, tier) | p < 0.05 AND monotone means AND ρ ≥ 0.4 |
| H4 | Continuous agreement | Spearman ρ(overall, mean rating), CI | CI excludes 0; ρ ≥ 0.4 pre-declared "strong" |
| H5 (gate) | Mini↔frontier bridge | Spearman ρ(full_mini, full) on H | ρ ≥ 0.80 (else lead with H only) |

- **Primary endpoint:** H1 bottom-quintile reject lift. **Score band = lowest
  quintile** (20%), fixed in advance.
- **Confirmatory:** H2--H4. **Secondary/exploratory:** per-dimension AUROC
  (Benjamini--Hochberg FDR across the 5), audit-adds-signal (nested AUROC),
  run variance, prevalence re-weighting, replication, the naive-judge baseline
  (§5b).
- **No post-hoc promotion:** a secondary finding never becomes the headline.

## 5b. Naive-judge baseline (pre-registered value comparison)
Does the full AIPR pipeline out-discriminate a one-paragraph "grade this paper"
prompt run on the **same PDF and same model**? The only variable is the pipeline.
Pre-declared before unblinding (full plan + public prompt in the paper's appendix):
- **Discrimination:** AUROC(naive) vs AUROC(full) on cohort H, bootstrap CIs.
- **Operating point:** accept/reject agreement at **AIPR@60** (overall ≥ 60 ⇒
  predict accept), reported for each method, **plus** each method at its own
  matched accept-rate so the comparison is not an artefact of AIPR's cutoff.
- **Reliability:** run-to-run score-distribution spread (the ~10-paper variance
  sub-study) under `naive` vs `full`.
- **Pre-declared success:** AUROC(full) − AUROC(naive) > 0 with the CI excluding
  0. A null (naive matches full) is reported plainly as a negative product result.

## 6. Outcome-neutral interpretation (declared before results)
- If H1 holds but H2/H4 are weak: report the bounded "flags weak work" claim
  only; explicitly decline any ranking/quality-correlation claim.
- If H5 fails (ρ < 0.8): drop the cheap-model-as-proxy framing; lead with cohort H,
  report wider CIs, and state the cheap model is not a valid stand-in.
- If H1 fails (lift CI includes 1): report the null plainly; the study does not
  support the deployment claim. No metric-shopping.
- A monotone gradient that is significant but small (ρ < 0.4) is reported as
  "detectable but weak," not "strong."

## 7. Integrity guarantees
- Every number generated by `run_all.py`; none hand-typed (macro pipeline).
- Label-shuffle null control asserted (shuffled AUROC ∈ [0.45, 0.55]).
- Estimator validity established a priori (`simulation.py`: bootstrap coverage,
  JT Type-I error).
- Deterministic under the fixed seed; environment pinned (`requirements.txt`).
- De-identified scored table + code + this file released for reproduction.
- Full generated AIPR review text is not publicly released by default. It is a
  controlled audit artifact and can be provided to editors/reviewers if they
  judge it necessary.

## 8. What is explicitly NOT claimed
Acceptance-probability prediction; ranking of strong papers; positive selection;
any consequential decision without a human in the loop; generalization beyond the
studied venue/field.

---

### Sign-off checklist
- [x] Venue (year) confirmed — **ICLR 2026** primary (revised from 2025 for contamination)
- [x] Configs confirmed — **full-mini (n=300) + full (n=100)**; the cheap `scan` config dropped (2026-06-02 revision)
- [x] Cohort M split confirmed — **150 / 100 / 50** (reject / poster / oral), 3-tier
- [x] Cohort H split confirmed — **50 / 30 / 20** (reject / poster / oral), ⊆ M
- [x] Budget unit (papers vs grades) confirmed — **100 distinct frontier papers, single run** (+ ~10-paper variance sub-study)
- [x] Replication venue — **DEFERRED** (2026-only first analysis; ICLR 2025 reinstated as future work)
- [x] Contamination check done — gpt-5.4 cutoff Aug 31 2025 < ICLR 2026 decisions Jan 2026 (confirm cutoff vs model card)
- [x] Prospective ICLR 2027 arm — NOT required (cutoff closes the model-contamination channel for 2026); optional future-work only
- [x] Re-frozen after the 2026-06-02 config revision (commit hash + date recorded above; public anchor = `prereg-iclr2026-v2` tag)
- [x] Manifest committed — the realized cohort manifest (submission ids + stratum + assigned config) is the released `submissions.csv` / `gradings.csv`; public freeze anchor `prereg-iclr2026-v2` (see **Manifest** above). The analysis plan was frozen before any score was joined to an outcome.
- [x] Eng export triggered — released two-CSV export (`submissions.csv` + `gradings.csv`) under `analysis/data/iclr2026/`.

## 2026-06-10 — OpenReview data-use compliance check (pre-arXiv)

**Checked:** OpenReview Terms of Use (openreview.net/legal/terms, last updated
2024-09-24); per-note license fields on the ICLR 2026 venue via the public API
(spot-checked forum M7TNf5J26u: submission, decision, meta-review, and comment
notes all carry `"license": "CC BY 4.0"`); CC BY 4.0 legalcode SS3(a)(1) and
SS2(a)(6); arXiv moderation policy; precedent datasets (PeerRead, NLPeer,
arXiv 2511.15462, AAAI-26 pilot arXiv 2604.13940).

**What the terms say:** OpenReview ToS: "By submitting a Comment or
Configuration Record ... the Submitter agrees that it shall be released to the
public under the Creative Commons Attribution 4.0 International (CC BY 4.0)
license." Official reviews, meta-reviews, and decisions are Comments. The ToS
contains no anti-scraping, bulk-download, or non-commercial restriction; only
access-control circumvention is prohibited (none occurred — all data is
public-access via the documented API). We do not redistribute PDFs or full
review texts regardless.

**Conclusion:** the release unit (submissions.csv / gradings.csv: forum ids,
public decisions, public mean ratings, AIPR scores) is compliant — decision and
rating values are uncopyrightable facts and the source notes are CC BY 4.0.
Verbatim review excerpts in the case-study table are CC BY 4.0 reuse with
attribution (anonymous ICLR 2026 reviewers, forum URIs, ellipsis trims
indicated). Naming exemplar submissions with citation to their public
OpenReview forums is lawful factual citation; arXiv policy permits papers
commenting on identified papers. Commercial use is permitted by CC BY 4.0 and
the ToS, subject to CC BY SS2(a)(6): no statement may imply ICLR or OpenReview
endorses or is affiliated with AIPR.

**Mitigations applied (this date):** Data-licensing paragraph added to
SSData (03_data.tex); CC BY 4.0 attribution added to the tab:casestudy caption;
licensing section added to analysis/data/README.md; "de-identified" wording
replaced by "keyed by public OpenReview submission identifiers" in the
conclusion and data README; no-endorsement sentence added to the competing-
interests paragraph. Naming policy tightened: only submissions the score
places favorably are named (top-scoring oral, highest-scoring reject); the
lowest-scoring reject is described by outcome only.

**Marketing rule (standing):** describe the result as "validated against the
public ICLR 2026 review record on OpenReview" — never "ICLR-validated" or any
wording implying venue endorsement.

## 2026-06-12 — Phase-2 pre-registration addendum (prereg-iclr2026-phase2)

> **Status: DRAFT pending owner approval.** This addendum becomes the frozen
> Phase-2 pre-registration only when the `prereg-iclr2026-phase2` tag is
> created and pushed to the public remote by the owner — neither the tag nor
> any push happens in this change. The tag push is the run trigger: no
> Phase-2 grading call is made before it. (The v1 appendix is unaffected:
> `prereg_verbatim.tex` renders from the `prereg-iclr2026-v2` tag, never the
> working tree.)

**Pillar 1 — citation-audit re-validation (config `full_full_p2`).**
Cohort: the frozen cohort-H ids (the n=100 frontier papers already released
in `gradings.csv`). Config: `full_full_p2` — the current v6 pipeline with the
abstract-based citation audit (post-fix #7), the same frontier model as
`full_full`; single run per paper, Flex tier. Reported metrics:
citation-subscore AUROC (reject vs. accept) and the citation pinned-at-100
rate, each beside the frozen v1 artifact row (pinned rate 1.0, AUROC 0.50).
This is explicitly a **validation of the FIXED pipeline — the frozen v1
result stands unmodified**; the comparison row is labeled new-validation and
no v1 number is recomputed.

**Pillar 2 — ICLR 2025 ordinal arm (pre-declared metrics).**

- Headline triplet, mirroring v1: accept/reject AUROC; bottom-quintile
  reject rate (band 0 of the score-band table); Spearman(score, mean
  reviewer rating).
- Ordinal additions — the reason for the 2025 arm (ICLR 2025 awards FOUR
  decision tiers, reject < poster < spotlight < oral, one tier finer than
  2026): Spearman(score, tier_rank) over the 4-tier ladder;
  adjacent-boundary AUROCs (reject|poster, poster|spotlight, spotlight|oral)
  with BCa CIs; per-tier median score with a monotonicity statement.
- Cohort: stratified full-mini n=300 (mirrors the v1 primary cohort M).
  Strata sized by the observed 2025 tier proportions; the EXACT split is
  recorded in this addendum once the bare `labels` manifest exists —
  labeling is observation, not experiment, and may precede the tag; the tag
  lands before `select-cohort` freezes ids and before any grading. **NO 2025
  frontier arm** (this is a confirmation arm; mini is the deployable tier).
- Spotlight base-rate caveat: spotlights are a small fraction of accepts
  (~5% historically), so the poster|spotlight boundary AUROC is expected to
  be noisy at n=300 — its CI is reported, never headline-claimed.
- Contamination framing, fixed in advance: ICLR 2025 decisions precede the
  grading model's Aug-2025 training cutoff, so the 2025 arm is reported as
  an **in-training-window consistency check**; ICLR 2026 remains the clean
  primary.

**Scope statement.** No other v1 number is re-run or revised by Phase 2.

## 2026-07-01 — Phase-3 pre-registration addendum (prereg-iclr2026-phase3)

> **Status: FROZEN** at tag `prereg-iclr2026-phase3` (owner-approved 2026-07-01).
> The tag on the public remote is the authoritative anchor and the **run
> trigger**: no Phase-3 grading ran before it. (The v1 appendix is unaffected:
> `prereg_verbatim.tex` renders from the `prereg-iclr2026-v2` tag, never the
> working tree.)

**Motivation.** Reviewer request: (1) the Direct one-paragraph baseline at the
**mini** model tier and at larger n, to power the pipeline-vs-prompt
discrimination comparison the v1 frontier cohort left at p=0.09 (n=100); and (2)
a clean, tier-**balanced** reliability comparison across all four
model/pipeline arms. Both are **post-hoc** (planned after v1 unblinding) and are
reported as such. No v1 or Phase-2 number is recomputed.

**Follow-up B — Direct-mini discrimination at scale (config `naive_mini`).**

- Cohort: **all 300 cohort-M ids** (frozen; no new draw). Config `naive_mini` =
  the one-paragraph Direct prompt (byte-identical to `naive`) run on the **mini**
  model (gpt-5.4-mini), single run per paper, Flex. Pairs with the released
  AIPR-mini (`full_mini`) scores on the same 300.
- Pre-declared metrics: AUROC(Direct-mini) with bootstrap CI; the **paired
  ΔAUROC(AIPR-mini − Direct-mini)** on the 300 (stratified bootstrap CI +
  two-sided p); the cohort-H (n=100) subset reported for continuity with the v1
  frontier comparison.
- **Outcome-neutral rule, fixed before running:** success = the paired ΔAUROC CI
  **excludes 0** (the pipeline adds discrimination at the mini tier). A CI
  straddling 0 is reported plainly as "not resolved even at n=300; the pipeline's
  value is reliability + grounding." The metric, cohort, and band are fixed here —
  no threshold shopping, no re-running to significance.

**Follow-up A — balanced four-arm reliability (dataset `iclr2026_followup`).**

- Cohort: a **fresh, tier-balanced** draw of **30 ICLR-2026 papers (10 reject /
  10 poster / 10 oral)**, drawn deterministically with the study seed and
  **disjoint from cohort M/H**. **Reliability is the object of this arm;**
  discrimination on n=30 is illustrative only and is never headline-claimed (its
  CI is wide and reported as such).
- Arms: **all four** — AIPR (`full`, gpt-5.4), AIPR (`full_mini`, gpt-5.4-mini),
  Direct (`naive`, gpt-5.4), Direct (`naive_mini`, gpt-5.4-mini) — each paper
  graded **3×** (run_index 0–2).
- Pre-declared metric: per-arm **median within-paper SD** of the overall across
  the 3 runs; the AIPR-vs-Direct within-paper-SD contrast **at each model tier**
  (paired exact Wilcoxon signed-rank). This mirrors v1's reliability claim
  (AIPR SD ≪ Direct SD) now at both tiers and balanced across outcomes.
- **Outcome-neutral rule:** the fresh balanced result is reported **alongside**
  the pre-registered n=10 variance result, not in place of it; if they disagree,
  both are shown and the discrepancy discussed.

**Follow-up A — outcome-stratified consistency (pre-grading addendum, 2026-07-02).**
Recorded *before* any `iclr2026_followup` grade is run, so the a-priori
hypothesis is timestamped and not read off the results.

- **Secondary, exploratory** pre-declaration (does NOT alter the frozen
  `prereg-iclr2026-phase3` primary metric above; the tag is not moved). The n=30
  balanced draw exists precisely to give each **decision stratum** (reject /
  poster / oral) equal weight, which the pre-registered n=10 set (4/3/3) could
  not.
- **Question:** *where* does the elaborate AIPR prompt buy grading consistency
  over the one-paragraph Direct baseline — i.e. is the AIPR-vs-Direct
  within-paper-SD gap uniform across strata, or concentrated in one?
- **A-priori hypothesis:** the consistency gain is **largest on rejects**
  (rejects are where a reliable low score carries the most decision value and
  where the Direct prompt is expected to be noisiest). Stated now; not derived
  from data.
- **Metric:** median within-paper SD of `overall` per (arm × decision stratum),
  and the AIPR-vs-Direct SD contrast **within each stratum**, at each model tier.
  Reported for all three strata regardless of which is largest — the reject
  emphasis is a prior, not a filter. n per stratum is 10, so per-stratum CIs are
  wide and reported as such; this is descriptive/exploratory, never headline.
- **Outcome-neutral rule:** if the gap is uniform across strata (no reject
  concentration), that is reported plainly; no stratum is promoted post-hoc for
  being the largest.

**Scope statement.** No v1 (`prereg-iclr2026-v2`) or Phase-2 number is re-run or
revised. Every Phase-3 output is an additive grading row (`naive_mini`), an
additional dataset (`iclr2026_followup`), or an additional figure curve, labelled
**post-review follow-up (not pre-registered)** in the manuscript — consistent
with §5's "no post-hoc promotion": a follow-up never becomes the headline.
