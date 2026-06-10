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
