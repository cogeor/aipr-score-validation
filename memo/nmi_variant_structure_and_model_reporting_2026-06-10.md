# NMI Variant Plan: Model Reporting, Analysis Reporting, and Structure

Date: 2026-06-10  
Purpose: define what the paper must say about the models and analysis, and how
to build a separate Nature Machine Intelligence variant without weakening the
arXiv version.

## Executive Recommendation

Create a separate NMI manuscript variant rather than trying to make the arXiv
paper serve both jobs.

Best path:

1. Keep the arXiv paper as the complete technical validation record.
2. Create an NMI **Analysis** variant with a short main text, online Methods, and
   Supplementary Information.
3. Make model identity and analysis reproducibility explicit in the NMI Methods.
4. Keep proprietary prompt/rubric details confidential but auditable on request.
5. Use ICLR 2026 as the primary clean cohort and ICLR 2025 as within-venue
   temporal replication / contaminated contrast.

The NMI variant should read as a paper about controlled AI assistance in peer
review, not as a long product-validation paper.

## What Must Be Clear About the Model

The current manuscript often says "cheap model" and "frontier model." That is
acceptable in a general introduction but too vague for Methods.

The paper should explicitly report:

- model identifiers used in each configuration;
- pipeline version;
- run dates or at least the frozen study tag/time window;
- knowledge cutoff evidence/source;
- which model saw which input;
- which tools were available to which pass;
- whether the model was trained/fine-tuned/tuned on the evaluation venue;
- what is proprietary and what can be disclosed to editors/reviewers.

From the current data export:

| Config in CSV | Model | Pipeline version | Role |
|---|---|---|---|
| `full_mini` | `gpt-5.4-mini` | `v6` | large-N cheap-model full pipeline |
| `full_full` | `gpt-5.4` | `v6` | production/frontier full pipeline |
| `naive` | `gpt-5.4` | `naive` | one-paragraph baseline |

Important cleanup: the manuscript/schema often call the frontier config `full`,
but the real CSV uses `full_full`. Either normalize the export to `full` or state
that `full_full` is the exported name for the manuscript's `full` configuration.
For NMI, prefer one name everywhere.

### Recommended Methods Wording

Use a compact paragraph like this in the NMI Methods:

> All AIPR grades were produced by a single frozen pipeline version, v6. The
> large cohort used the full two-pass pipeline with reviewer model
> `gpt-5.4-mini` (`full_mini`); the production/frontier cohort used the same
> pipeline with reviewer model `gpt-5.4` (`full`/`full_full` in the export). The
> naive baseline used `gpt-5.4` on the same submitted PDFs with a single
> one-paragraph prompt and no rubric or citation audit. No model was trained,
> fine-tuned, or tuned on the venue, decisions, ratings, or evaluation labels.
> The scorer received the submitted PDF bytes; it did not receive OpenReview
> reviews, decisions, venue tags, reviewer ratings, or author identities.

Then add:

> The exact production prompts, rubric text, and model configuration are retained
> under the frozen study tag and can be provided confidentially to editors,
> reviewers, or auditors. Publicly released materials include the model
> identifiers, pipeline version, scoring dimensions, overall-score formula,
> output schema, de-identified scores, labels, and all analysis code.

This is the best compromise between proprietary constraints and scientific
inspectability.

## Knowledge Cutoff Constraint

The paper currently asserts an August 2025 model cutoff. For NMI, this needs an
evidence source or a softer wording.

Best case:

- cite or archive the official model-card/provider metadata showing the cutoff;
- state exact cutoff date;
- state exact ICLR 2026 decision/review release month/date;
- explain that manuscript-text leakage is distinct from outcome/review leakage.

If the official model-card source cannot be public:

> Based on provider model metadata available at grading time, the `gpt-5.4` model
> family had a documented knowledge cutoff of 31 August 2025. Because ICLR 2026
> decisions and reviews were released in January 2026, the primary outcome and
> review text could not have been memorized through pretraining. Residual
> manuscript-text familiarity is bounded by the arXiv-before-cutoff sensitivity
> split.

Do not overstate this as a total leakage closure. It closes outcome/review
memorization for ICLR 2026; it does not eliminate topic priors or preprint-text
familiarity.

## What Must Be Clear About the Analysis

The current paper is strong on analysis, but NMI needs a cleaner "how analysis
was done" story in Methods rather than scattered across appendix sections.

Report in one Methods subsection:

- two-table data contract: `submissions.csv` and `gradings.csv`;
- cohort construction and exclusions;
- primary endpoint and hypotheses;
- how repeated grading runs are collapsed;
- how confidence intervals are computed;
- which tests are confirmatory vs descriptive;
- how robustness analyses are generated;
- exact command or pipeline stage that regenerates figures/tables.

### Recommended Methods Subsections for NMI

1. **Study cohorts and outcomes**
   - ICLR 2026 primary; ICLR 2025 secondary if added.
   - Submitted PDFs only.
   - Decision tier and mean reviewer rating.
   - Balanced sampling by tier, prevalence reweighting reported separately.

2. **AIPR scoring configurations**
   - v6 pipeline.
   - `gpt-5.4-mini`, `gpt-5.4`, naive `gpt-5.4`.
   - Two-pass review/audit; naive one-prompt baseline.
   - Overall formula.

3. **Pre-registration and endpoints**
   - H1 low-end flagging as primary.
   - H2 AUROC, H3 monotone tier trend, H4 rating correlation, H5 bridge.
   - V1 pipeline-vs-naive comparison.
   - State fixed before score-outcome join.

4. **Statistical analysis**
   - AUROC with stratified bootstrap.
   - Spearman with bootstrap CI.
   - Jonckheere-Terpstra with Monte Carlo permutation.
   - Wilson intervals for rates.
   - BCa bootstrap, 4,000 resamples.
   - Multiple comparisons only for per-dimension exploratory tests.
   - Descriptive covariate/area/disagreement analyses not confirmatory.

5. **Reproducibility and audit**
   - all numbers generated from code;
   - exact CSV contract;
   - public code/data release;
   - scorer prompts/config retained for confidential audit.

### Recommended Analysis Wording

> All reported statistics are generated from the released `submissions` and
> `gradings` tables by the analysis pipeline. Confirmatory analyses use the
> pre-registered endpoints: bottom-quintile reject enrichment, reject-vs-accept
> AUROC, monotone trend across tiers, correlation with mean reviewer rating, the
> mini-to-frontier bridge, and the paired frontier-vs-naive comparison. We report
> effect sizes with 95% confidence intervals. AUROC intervals use stratified BCa
> bootstrap resampling that preserves the observed accept/reject counts; trend
> tests use a Monte Carlo permutation implementation of Jonckheere-Terpstra; rates
> use Wilson intervals. Secondary covariate, area, weighting, and disagreement
> analyses are descriptive and are not used to redefine the primary claim.

## Constraints to State Honestly

Do not hide these; state them once cleanly.

1. **Proprietary scorer**
   - Open analysis, closed manuscript-to-score function.
   - Confidential disclosure available.
   - No claim of independent reimplementation.

2. **Same-venue evidence**
   - ICLR 2025 + 2026 is temporal replication, not cross-field generalization.
   - Validates ML/OpenReview-style peer review.

3. **Citation audit**
   - Original citation channel had retrieval/fallback failure.
   - Overall score survives citation drop.
   - Corrected citation audit should be re-run or citation moved outside the
     validated score claim.

4. **Relative threshold**
   - Bottom quintile is a triage capacity allocation, not universal rejection
     cutoff.
   - The action is human attention.

5. **Model cutoff and leakage**
   - Outcome/review leakage controlled for 2026 if cutoff evidence is documented.
   - Manuscript preprint familiarity and topic priors remain residual risks.

6. **Publisher policy**
   - Do not imply reviewers should upload confidential manuscripts to public AI
     tools.
   - The stance is controlled, disclosed, venue-approved AI assistance.

## Best-Case NMI Structure

Target type: **Analysis**.

### Front Matter

- Title: field-level, not product-first.
- Abstract: 100-150 words.
- Main claim: controlled AI assistance has measurable first-pass signal and should
  be governed/evaluated, not categorically dismissed.

Possible title:

> Frontier language models provide useful first-pass signals for manuscript triage

Possible subtitle or deck:

> A validation study of AIPR on public ICLR peer-review outcomes

### Main Text Order

NMI format expects:

1. Introduction (usually no visible `Introduction` heading)
2. Results
3. Discussion
4. Methods

The current arXiv order is:

1. Abstract
2. Introduction
3. Related work
4. Data
5. Methods
6. Results
7. Failure modes
8. Discussion
9. Limitations
10. Conclusion
11. Appendix

For NMI, collapse and reorder.

### NMI Main Text Skeleton

**Opening / Introduction, no heading**

- Peer review is strained and AI use is already present.
- Current policy concern is justified: confidentiality, accountability, errors.
- Existing studies mostly evaluate feedback/review text.
- This study evaluates a numeric first-pass signal against public human outcomes.
- Claim boundary: human triage, not replacement.

**Results**

Subsections:

1. **A first-pass score tracks human outcomes**
   - H1-H4.
   - Fig. 1/2.

2. **The signal is strongest for low-score triage**
   - relative threshold as capacity allocation.
   - low-score harm rate.

3. **A frontier model already carries much of the signal**
   - naive baseline.
   - unresolved AUROC gap.
   - reliability advantage.

4. **The finding is stable across the venue family**
   - ICLR 2025 temporal cohort if added.
   - contamination caveat.

5. **Failure modes define the deployment boundary**
   - false negatives / false positives.
   - what the model cannot see.

**Discussion**

No many subheadings. Keep it as a narrative:

- Do not reject AI assistance categorically.
- Do not automate decisions.
- The bottleneck is controlled deployment.
- AIPR demonstrates stability, grounding, and auditability.
- Remaining limits: same venue, proprietary scorer, citation audit, leakage, human
  ground-truth noise.

**Methods**

Use the five subsections listed above.

## NMI Variant File/Repo Plan

Recommended file layout:

```text
paper/
  main.tex                  # arXiv/full technical version
  main_nmi.tex              # NMI variant wrapper
  sections/
    nmi_00_abstract.tex
    nmi_01_intro.tex
    nmi_02_results.tex
    nmi_03_discussion.tex
    nmi_04_methods.tex
  supplement/
    nmi_supplement.tex      # appendix material reorganized as SI
```

Alternative lower-maintenance layout:

```text
paper/
  variants/
    nmi_main.tex
    nmi_supplement.tex
```

Do not over-engineer with conditionals at first. The NMI paper should be a
separate manuscript with shared generated figures/tables/macros.

Shared inputs:

- `paper/macros/results_macros.tex`
- `paper/macros/sim_macros.tex`
- selected figures from `paper/figures/`
- selected tables from `paper/tables/`

NMI-specific inputs:

- shortened abstract;
- NMI structure and figure set;
- supplement curated from current appendix.

## Display Item Plan

Keep at or below six display items.

Best main set:

1. **Study design / data flow**: controlled inputs, model configs, outcomes.
2. **Primary validation figure**: score by tier, reject rate by decile, rating
   correlation.
3. **Naive baseline and reliability**: ROC + repeated-run variance.
4. **Two-year temporal validation**: ICLR 2026 vs 2025 headline metrics.
5. **Low-score triage / failure modes**: accepted/oral-in-bottom-band plus
   qualitative error classes.
6. **Headline metrics table** or a compact operating-boundary table.

If space is tight, merge the headline table into Fig. 2 or Supplement.

## Abstract Constraint

Current abstract is about 377 words. NMI needs roughly 100-150 words.

Target abstract shape:

1. Problem: AI peer review is controversial; evaluations often focus on review
   text rather than score validity.
2. Method: validate AIPR/LLM first-pass scores on public ICLR outcomes.
3. Result: scores track human decisions/ratings, especially low-end triage; naive
   frontier prompt already works; AIPR adds reliability/auditability.
4. Boundary: no automated decisions; controlled human-in-the-loop use only.

## What to Keep Out of Main Text

Move to supplement:

- full preregistration;
- long data schema;
- estimator simulations;
- full robustness suite;
- detailed covariate models;
- all per-area tables;
- all threshold sensitivity tables;
- long failure-mode excerpts;
- population ledger;
- token/cost details unless used as a deployment claim;
- citation audit details unless corrected audit becomes a main result.

## What to Add Before NMI Submission

Required:

1. Normalize/report exact model identifiers.
2. Add model cutoff citation or soften cutoff claim.
3. Add ICLR 2025 temporal cohort.
4. Fix/re-run citation audit or remove citation from validated claim.
5. Add NMI-adjacent citations:
   - Thakkar et al. 2026 NMI randomized LLM feedback in peer review.
   - Nature/Springer AI-in-peer-review policy.
   - hidden-prompt / prompt-injection work.
   - update AI Review Lottery to final ACM/PACM HCI record if applicable.

Strongly recommended:

1. Human-review reliability ceiling if per-review ratings can be exported.
2. Explicit model/tool access boundary figure/table.
3. Short conflict-of-interest / audit posture in Methods or Competing Interests.

Optional:

1. Controlled prompt-injection robustness note if the system strips hidden text or
   defends against it.
2. Cost-at-scale paragraph in Supplement.

## Final Constraint / Best-Case Summary

The best NMI version is not the most complete version. It is the most disciplined
version:

- exact model identities;
- exact analysis pipeline;
- bounded two-year ICLR evidence;
- corrected or isolated citation audit;
- clear human-in-the-loop deployment boundary;
- no claim that AI replaces peer reviewers;
- no claim of cross-field generalization;
- no hidden dependence on proprietary internals without confidential audit access.

If written this way, the paper becomes a serious NMI Analysis candidate. If the
NMI version remains a long arXiv-style validation with vague model labels and a
buried citation-audit issue, it will read as underformatted and self-validating
even if the underlying evidence is good.
