# AIPR Score-Validation Publication Grade Report

PDF reviewed: `paper/main.pdf`

Manuscript: **"Intelligence Is Not the Bottleneck: Results from the AIPR Study"**

## Grade

**Overall: 78/100, B+**

| Dimension | Score | Rationale |
|---|---:|---|
| Novelty | 76 | Strong positioning around extrinsic score validation rather than comment quality, plus the pipeline-vs-naive result. Not field-defining, but a clear contribution. |
| Rigor | 74 | Pre-registration, deterministic analysis, CIs, permutation tests, bridge analysis, and failure-mode review are strong. Held down by a generated table bug and the uninformative citation subscore. |
| Applicability | 82 | The result is directly useful for positioning AIPR: the product value is reliability, grounding, and workflow, not merely raw model intelligence. |
| Clarity | 75 | The argument is readable and well structured, but several claims are worded more broadly than the evidence supports. |
| Citation | 80 | Related work is credible and clearly positions the paper. I did not perform a full citation audit, so this is a manuscript-level score, not a verified bibliography score. |

## Main Judgment

This is a publication-worthy draft with a strong core claim: AIPR's score tracks human peer-review outcomes, but the most important result is that the raw frontier model already has much of the discriminative signal. AIPR's contribution is therefore not raw judgment accuracy; it is reliability, grounding, structured review output, and deployment discipline.

The paper is held below A range by one serious generated-result issue, one real scoring-system limitation, and several over-broad phrasings that should be tightened before submission.

## Must Fix

### 1. Table 3 oral-rate bug

Rendered Table 3 reports `0%` oral rate in every score quintile:

```text
Q1 ... Oral rate 0%
Q2 ... Oral rate 0%
Q3 ... Oral rate 0%
Q4 ... Oral rate 0%
Q5 ... Oral rate 0%
```

That is impossible because Table 1 says the full-mini cohort contains 50 oral papers. A quick check against `analysis/data/iclr2026` shows oral papers do appear across score bands, including the top band. The generated file with the impossible values is:

```text
paper/tables/tab_score_bands.tex
```

Likely source:

```text
analysis/stats.py
```

In `score_band_table`, oral rate is computed with:

```python
orr = float((tier_rank[mask] == 3).mean()) if n else 0.0
```

But the visible schema uses `tier_rank` values consistent with `reject=0`, `poster=1`, `oral=2`. If so, this should use the actual oral rank constant, not hard-coded `3`.

Do not submit until this is fixed and all dependent statements are regenerated.

### 2. Citation subscore fallback

The manuscript handles this honestly, but it is still a meaningful limitation: the frontier citation score is pinned at 100% of papers because empty audit output is scored as perfect. This weakens any claim that "five dimensions" are validated equally. The current manuscript mostly contains it, but I would make the caveat more prominent wherever the five-dimensional score is described.

## Exact Wording Changes

These are the exact wording changes I mean. I am giving replacement text, not just high-level advice.

### Abstract: narrow the "trustworthy" claim

Current wording:

```text
With or without our prompt, a frontier model is already intelligent enough to produce a trustworthy first-pass reviewing signal: intelligence is not the bottleneck, and the human keeps the decision.
```

Replace with:

```text
Within this ICLR cohort, with or without our prompt, a frontier model already produces a first-pass reviewing signal that agrees substantially with human outcomes; intelligence is not the observed bottleneck, and the human keeps the decision.
```

Reason: "trustworthy" is too broad unless immediately tied to this cohort and the measured outcome agreement.

### Introduction: soften universal framing

Current wording:

```text
with or without our prompt, a frontier model is already intelligent enough to produce a trustworthy first-pass reviewing signal, so intelligence is not the bottleneck, and the reviewer keeps the decision.
```

Replace with:

```text
with or without our prompt, a frontier model already produces a first-pass reviewing signal that substantially tracks the human outcome in this setting, so raw model intelligence is not the observed bottleneck, and the reviewer keeps the decision.
```

Reason: the study supports "in this setting" better than a general claim about peer review.

### Contributions item 3: avoid "review competently" as a broad claim

Current wording:

```text
so a frontier model is already intelligent enough to review competently with or without our prompt---intelligence is not the bottleneck.
```

Replace with:

```text
so a frontier model already carries much of the outcome-aligned judgment signal with or without our prompt - raw intelligence is not the observed bottleneck.
```

Reason: "review competently" implies full review quality, while the evidence is primarily score-outcome alignment.

### Results section 5.2: clarify what "validity" means

Current wording:

```text
The validity is therefore not manufactured by the engineering: with or without our prompt, a frontier model is already intelligent enough to produce a trustworthy first-pass reviewing signal---intelligence is not the bottleneck, and the reviewer, not the model, keeps the decision.
```

Replace with:

```text
The score-outcome agreement is therefore not manufactured by the engineering: with or without our prompt, a frontier model already produces a first-pass score that substantially tracks the human outcome in this cohort - raw model intelligence is not the observed bottleneck, and the reviewer, not the model, keeps the decision.
```

Reason: "validity" has a technical meaning in the paper. This sentence should name the measured property directly.

### Discussion: tighten the load-bearing claim

Current wording:

```text
The scoring parity, read on its face as a negative result for the pipeline, is the opposite: with or without our prompt the model is already intelligent enough to produce a trustworthy first-pass reviewing signal---the raw judgment is not what a deployment is short of, and the reviewer still owns the decision.
```

Replace with:

```text
The scoring parity, read on its face as a negative result for the pipeline, points to a different bottleneck: with or without our prompt, the model already produces an outcome-aligned first-pass score in this setting. Raw judgment is not what this deployment is shortest of; stability, grounding, and accountable presentation are.
```

Reason: this preserves the title claim but anchors it to the evidence.

### Discussion: avoid "answers yes" across the field

Current wording:

```text
Framed this way the contribution shifts from ``can an LLM judge quality?''---which our parity result, with a growing literature, answers yes---to ``can a system judge quality reliably and accountably at deployment?''
```

Replace with:

```text
Framed this way the contribution shifts from ``can an LLM produce an outcome-aligned quality signal in this setting?'' - which our parity result answers yes - to ``can a system deliver that signal reliably and accountably at deployment?''
```

Reason: the original reads as a general field-level answer. The study is stronger if it stays inside its design.

### Conclusion: same tightening as abstract

Current wording:

```text
with or without our prompt, a frontier model is already intelligent enough to produce a trustworthy first-pass reviewing signal, so intelligence is not the bottleneck, and the reviewer keeps the decision.
```

Replace with:

```text
with or without our prompt, a frontier model already produces a first-pass reviewing signal that substantially tracks human outcomes in this cohort, so raw model intelligence is not the observed bottleneck, and the reviewer keeps the decision.
```

Reason: this is the cleanest final form of the central claim.

### Methods: add a stronger citation caveat near the scoring formula

After this sentence:

```text
with novelty and applicability carrying the top weight and citation the least; the model does not emit the overall directly.
```

Add:

```text
Because the citation dimension is a lightly weighted audit-derived signal, we report it separately from the main outcome-validity claim and test whether the headline survives dropping it entirely.
```

Reason: this prepares the reader for the later citation-subscore failure and prevents surprise.

### Results section 5.3: make the citation failure more direct

Current wording:

```text
This is a scoring artifact rather than a property of the manuscripts---an empty audit result is recorded as a perfect bibliography---which we diagnose in §7 and treat as a limitation in §8.
```

Replace with:

```text
This is a scoring artifact rather than a property of the manuscripts: in the original study run, an empty audit result was recorded as a perfect bibliography. We therefore do not interpret the citation subscore as validated in this cohort; we diagnose the failure in §7 and treat it as a limitation in §8.
```

Reason: state plainly that the citation subscore itself is not validated here.

### Limitations: proprietary scorer wording

Current wording:

```text
This is the standard posture for validating a deployed instrument: the validation is open even though the instrument is closed.
```

Replace with:

```text
This is a defensible posture for validating a deployed instrument, but weaker than full independent reproducibility of the scorer itself: the validation is open even though the instrument is closed.
```

Reason: "standard posture" sounds too self-exculpatory. This version concedes the real limitation without undermining the study.

## Smaller Issues

1. The paper says the full pipeline is "no worse at the decision itself" while reporting `51.0% vs. 72.0% balanced accuracy at AIPR@60`. That sentence is confusing as written. If the 51.0% belongs to full and 72.0% to naive, the claim is wrong at that operating point. If the direction is reversed or the parenthetical means something subtler, rewrite it.

Current wording:

```text
51.0 % vs. 72.0 % balanced accuracy at the pre-registered AIPR@60 operating point confirms the pipeline is no worse at the decision itself
```

Replace with one of these after verifying the direction:

```text
At the pre-registered AIPR@60 operating point, balanced accuracy is lower for the pipeline than for the naive judge (51.0% vs. 72.0%), so the parity claim rests on threshold-free AUROC and reliability rather than this fixed cutoff.
```

or:

```text
At the pre-registered AIPR@60 operating point, balanced accuracy is higher for the pipeline than for the naive judge (72.0% vs. 51.0%), consistent with the claim that the pipeline pays no fixed-cutoff accuracy penalty.
```

2. The title is good, but it should be treated as a claim about this study's observed bottleneck. The wording changes above are enough; I would not change the title unless reviewers push on it.

3. The single-venue limitation is already present and well handled. Do not weaken the manuscript by apologizing further; just keep the central claim scoped.

## Post-Fix Grade

If the oral-rate bug is fixed, the balanced-accuracy sentence is clarified, and the wording changes above are applied, I would raise the manuscript to:

**81-83/100, A-**

The paper would still have limitations - single venue, proprietary scorer, citation-subscore failure - but they would be acknowledged cleanly and would not undermine the core contribution.

## What Reviewers Could Still Ask For

The study already does the standard validation work well: pre-registration, power/estimator checks before the study, deterministic analysis, bootstrap/permutation inference, null control, model-tier bridge, weighting robustness, length checks, contamination split, naive baseline, and run variance. The likely remaining asks are not "fancier statistics." They are checks against plausible alternative explanations.

### 1. Covariate-control check

Reviewer ask:

```text
Is the AIPR score just picking up area, length, number of references, or reviewer-disagreement artifacts?
```

Add a supplementary descriptive model:

```text
accept_bool ~ AIPR_score + primary_area + page_count + word_count + n_references + n_figures + rating_std + n_reviews
```

Report it as exploratory/descriptive, not confirmatory. The point is not to replace the pre-registered AUROC; it is to show the score survives obvious controls.

Quick check from current CSVs:

```text
full-mini: covariate CV AUC 0.855 vs score-only AUC 0.825
frontier:  covariate CV AUC 0.830 vs score-only AUC 0.871
```

Interpretation:

```text
Adding manuscript-surface and area covariates does not explain away the score-outcome relationship; on the frontier cohort, the covariate model underperforms the score alone.
```

### 2. Area/subfield subgroup audit

Reviewer ask:

```text
Does the result only hold because some ICLR areas are easier to reject or easier for AIPR to score?
```

Use `primary_area`. Add a supplementary table for areas with sufficient sample size:

```text
primary_area, n, accept_rate, mean_score, score-rating rho, AUROC if both classes are present
```

Do not over-interpret small cells. For sparse areas, report only `n`, `accept_rate`, and `mean_score`, or pool into "other."

Suggested wording:

```text
Because the sample spans many OpenReview primary areas, we audited whether the result was concentrated in one subfield. Area-level estimates are noisy and treated as descriptive, but no single area accounts for the headline score-outcome relationship.
```

### 3. Within-tier score-rating agreement

Reviewer ask:

```text
Is AIPR only separating reject from accept, or does it track quality within decision tiers?
```

Add Spearman correlations between AIPR score and mean reviewer rating within:

```text
reject only
poster only
oral only
accepted only = poster + oral
```

This is useful even if the within-tier correlations are weak. Weak within-accepted correlation supports the paper's bounded claim: AIPR is validated for low-end triage, not ranking strong papers.

Suggested wording if weak:

```text
Within-tier correlations are smaller than the cross-tier relationship, especially among accepted papers. This is consistent with the study's claim: the score is most defensible as a low-end triage signal, not as a fine ranking of strong submissions.
```

### 4. Reviewer-disagreement moderation

Reviewer ask:

```text
Does AIPR fail more often when human reviewers disagree?
```

You already have:

```text
rating_std
n_reviews
```

Add two simple checks:

```text
Spearman(abs(score-rating rank residual), rating_std)
AUROC split by low vs high rating_std
```

Quick check from current CSVs:

```text
full-mini: rating_std vs score-rating rank-error rho about 0.09
frontier:  rating_std vs score-rating rank-error rho about 0.12
```

Suggested wording:

```text
Reviewer disagreement does not strongly moderate the score-rating relationship in this cohort, though the analysis is descriptive because reviewer disagreement is itself part of the noisy ground truth.
```

### 5. Low-score harm rate, not accuracy at 60

Reviewer ask:

```text
AUROC is threshold-free. What happens at the operating point that matters for deployment?
```

The relevant deployment harm is not balanced accuracy at a fixed score of 60. AIPR is not being proposed as an accept/reject classifier, and the paper explicitly does not claim a universal acceptance cutoff. The relevant harm is a strong or accepted paper receiving a low score and being misleadingly flagged as weak.

The right operating-point quantities are:

```text
P(low score | accepted)
P(low score | oral)
accepted-paper count in the bottom score band
oral-paper count in the bottom score band
case review of accepted-low papers
```

Quick check from current CSVs, using the current quantile-band implementation:

```text
frontier bottom band:
  n=15
  reject/poster/oral = 15/0/0
  P(low | accepted) = 0/50 = 0.0%
  P(low | oral) = 0/20 = 0.0%

full-mini bottom band:
  n=59
  reject/poster/oral = 53/4/2
  P(low | accepted) = 6/150 = 4.0%
  P(low | oral) = 2/50 = 4.0%
```

Recommended interpretation:

```text
The important safety check is not whether a fixed threshold maximizes balanced accuracy, but whether low scores frequently capture strong work. On the production frontier score, the bottom band contains no accepted or oral papers in this cohort. On the larger full-mini cohort, accepted-low cases are rare but nonzero and should be read qualitatively; these are the cases most likely to reflect rebuttal drift, reviewer forgiveness of a real flaw, or AIPR over-penalizing a concern the community accepted.
```

The fixed `AIPR@60` comparison can still appear as a pre-registered diagnostic, but it should not be framed as the central deployment metric.

Exact replacement for the current problematic sentence:

Current wording:

```text
51.0 % vs. 72.0 % balanced accuracy at the pre-registered AIPR@60 operating point confirms the pipeline is no worse at the decision itself.
```

Replace with:

```text
The fixed AIPR@60 threshold is a pre-registered diagnostic rather than the deployment claim: at that cutoff, the frontier score predicts nearly every paper as accepted and is not venue-calibrated. For triage, the relevant error is the opposite conditional event - accepted or oral papers falling into the low-score band. On the production frontier score, no accepted or oral paper falls in the bottom band; on the larger full-mini cohort, 6/150 accepted papers and 2/50 oral papers do. We therefore treat thresholded accept/reject accuracy as secondary to the low-score harm rate and the qualitative review of accepted-low cases.
```

### 6. Bottom-band tie and threshold sensitivity

Reviewer ask:

```text
Your scores are integer-valued and quintile bands have uneven sizes. Does H1 depend on a tie policy?
```

Current generated bands are uneven because score ties straddle quantile boundaries:

```text
Q1 n=59
Q2 n=52
Q3 n=56
Q4 n=49
Q5 n=84
```

Add a simple sensitivity table:

```text
bottom strict quantile band
bottom K=60 after deterministic tie-break
score <= 63
score <= 64
score <= 65
```

For each:

```text
n, reject_rate, lift, oral_rate
```

Suggested wording:

```text
Because the score is integer-valued, exact quintile membership depends mildly on how ties at the threshold are handled. The low-score flag remains a high-reject-rate region under deterministic K-of-N and adjacent-threshold definitions.
```

### 7. Human-review reliability ceiling

Reviewer ask:

```text
How close is AIPR to human-review reliability?
```

This is one of the strongest possible additions if per-review data can be exported.

Needed optional file:

```text
analysis/data/iclr2026/reviews.csv
```

Compute:

```text
corr(single reviewer rating, mean of other reviewers)
corr(AIPR score, mean reviewer rating)
corr(AIPR score, leave-one-reviewer-out mean rating)
```

Best framing:

```text
Because individual peer reviews are noisy, the relevant benchmark is not perfect agreement with the final mean rating but proximity to the reliability of a single human review. We therefore compare AIPR-rating agreement to single-reviewer versus rest-of-reviewers agreement.
```

This would substantially improve the paper if available.

### 8. Alternative reviewer-rating aggregation

Reviewer ask:

```text
Does the score-rating correlation depend on using the arithmetic mean?
```

DECISIONS.md says median/trimmed-mean sensitivity is supplementary. I do not see it implemented in the current generated analysis, likely because per-review ratings are not in the two-CSV core contract.

If `reviews.csv` is available, report:

```text
Spearman(score, mean rating)
Spearman(score, median rating)
Spearman(score, trimmed mean rating)
```

Suggested wording:

```text
The continuous-agreement result is stable to replacing the arithmetic mean reviewer rating with median or trimmed-mean aggregation.
```

If it is not available, do not claim this sensitivity was done.

### 9. Sample representativeness audit

Reviewer ask:

```text
Your sampled 300 papers are balanced across tiers. Are they otherwise strange relative to the full eligible population?
```

Add a descriptive table comparing:

```text
sampled cohort M vs eligible ICLR population
sampled cohort H vs cohort M
```

Columns:

```text
primary_area distribution
page_count
word_count
n_reviews
mean reviewer rating by tier
arxiv_prior_to_cutoff
```

This is not a hypothesis test. It is a sampling audit.

Suggested wording:

```text
The cohort is deliberately stratified by decision tier, so its accept rate is not population-representative. Apart from that designed stratification, we audit manuscript and area metadata to check whether the sampled submissions are unusual relative to the eligible population.
```

## Recommended Additions, Ranked

If time is limited, do these in order:

1. Fix the oral-rate bug and add a regression test for oral-rate computation.
2. Rewrite the AIPR@60 operating-point paragraph as threshold-free rank/triage evidence.
3. Add covariate-control supplement.
4. Add bottom-band tie/threshold sensitivity.
5. Add within-tier score-rating correlations.
6. Add reviewer-disagreement moderation.
7. Add area subgroup audit.
8. Add human-review reliability ceiling if per-review data are available.
9. Add alternate rating aggregation if per-review data are available.

## What Not To Add

Do not add exotic models, causal claims, or a post-hoc optimized acceptance classifier. Those make the study look less pre-registered and less disciplined.

Avoid:

```text
new headline metrics
neural baselines
post-hoc threshold tuning as a primary result
claims of calibrated acceptance probability
claims that AIPR ranks strong accepted papers
```

The clean framing is:

```text
This is criterion validity for rank/triage, not calibrated acceptance prediction.
```

## Broader Reviewer Surface: Non-Statistical Asks

The previous section was mostly statistical. Reviewers can ask for more than that. Below are the other realistic asks, grouped by domain, with what is feasible to add without redesigning the study.

### 1. Data provenance and exact artifact identity

Reviewer ask:

```text
How do we know AIPR graded the same PDF the reviewers saw?
```

Current paper says submitted PDFs are used, and the schema has `pdf_sha`, but the provenance story could be sharper.

Feasible addition:

```text
Add a short "PDF provenance" paragraph/table:
- source URL or OpenReview attachment field used
- whether it was the submitted PDF rather than camera-ready
- pdf_sha recorded for every graded PDF
- parse failure count
- count of papers where the submitted PDF could not be recovered
```

Suggested wording:

```text
For each retained submission we record the SHA-256 hash of the graded PDF and grade the OpenReview submitted manuscript attachment, not the camera-ready version. This pins the artifact to the version available to reviewers at decision time.
```

### 2. Decision-label derivation audit

Reviewer ask:

```text
How were raw OpenReview venue tags converted into reject/poster/oral?
```

The schema has `decision_raw`, and AIPR has `platform/openreview/decisions.py`. Reviewers may still want a transparent mapping table.

Feasible addition:

```text
Add an appendix table mapping raw venue tags to decision_tier and tier_rank.
```

Suggested wording:

```text
Decision labels are derived from raw OpenReview venue tags by a deterministic mapping, reproduced in Appendix X. The raw tag is released in `decision_raw`, so readers can rederive every tier assignment.
```

### 3. Manifest and sampling reproducibility

Reviewer ask:

```text
Where is the frozen cohort manifest, and how do I know the frontier subset was not chosen after seeing scores?
```

DECISIONS.md says the manifest should be frozen, but the sign-off checklist still has:

```text
[ ] Manifest generated and committed
```

This is dangerous. If the manifest exists somewhere else, link it. If not, create and commit it or update the checklist truthfully.

Feasible addition:

```text
Release a manifest file with submission_id, stratum, cohort assignment, variance-substudy flag, and freeze timestamp/tag.
```

Suggested wording:

```text
The exact cohort manifest was committed before frontier grading and contains only submission identifiers, strata, cohort assignment, and variance-substudy flags. It contains no AIPR score or outcome-derived quantities beyond the pre-existing decision stratum used for sampling.
```

If the manifest was not actually frozen before grading, do not claim it was. Say:

```text
The analysis plan was frozen before scores were joined to outcomes; the release includes the realized cohort manifest for audit.
```

### 4. Model cutoff and model-card evidence

Reviewer ask:

```text
Where is the evidence that the model cutoff predates ICLR 2026 decisions?
```

DECISIONS.md says to confirm the gpt-5.4 cutoff against the model card. That needs a citation or artifact.

Feasible addition:

```text
Add an appendix line citing the official model-card cutoff source or include an archived model-card snapshot.
```

Suggested wording:

```text
The grading model's documented knowledge cutoff is August 31, 2025; ICLR 2026 decisions and reviews were released in January 2026. We cite the model card used to verify this cutoff and archive the relevant metadata with the study artifacts.
```

If the model-card evidence cannot be public, weaken the claim:

```text
Based on the provider's documented model metadata available to us at grading time...
```

### 5. Inference-time leakage controls

Reviewer ask:

```text
Even if the model cutoff predates decisions, could the pipeline retrieve decision pages, reviews, OpenReview forum metadata, or public discussion during grading?
```

The paper says no inference-time access to decision pages is required/ensured, but it should state the operational control.

Feasible addition:

```text
Add a "network/tool-access boundary during grading" paragraph:
- PDF bytes supplied
- bibliographic search allowed only for citation audit
- OpenReview decision/review pages unavailable to the grader
- metadata excluded from prompt unless needed
- logs retained for audit
```

Suggested wording:

```text
During grading, the reviewer model received the submitted PDF and did not receive the OpenReview decision, review text, venue tag, or reviewer ratings. The citation-audit tool could query bibliographic records but was not allowed to fetch OpenReview decision or review pages.
```

### 6. AIPR prompt/rubric opacity

Reviewer ask:

```text
How can we evaluate a proprietary scorer if the prompt and rubric are closed?
```

The paper says the scorer is proprietary and audited through outputs. That is defensible, but reviewers may push hard.

Feasible additions:

```text
Release a public high-level rubric summary.
Release a schema for AIPR outputs.
Offer confidential prompt/rubric review to editors/reviewers.
Release hashes of prompt/config files used for grading.
```

Suggested wording:

```text
The exact production prompts and model configuration are proprietary, but we release the scoring dimensions, weighting rule, output schema, pipeline version, model identifiers, and de-identified scores. We retain the exact prompt/config artifacts and can provide them confidentially to editors or auditors.
```

This is much stronger than simply saying "closed."

### 7. Baseline fairness and "naive" prompt construction

Reviewer ask:

```text
Was the naive baseline handicapped, or was it tuned after seeing results?
```

The prompt is pre-registered and public in the appendix, which is good. Still, reviewers may ask if one prompt is enough.

Feasible addition:

```text
Add a short rationale for the naive prompt:
- same model
- same PDF
- no rubric/audit
- mirrors what a real user would paste into a chat assistant
- prompt frozen before unblinding
```

Possible extra if budget allows:

```text
Run 2-3 minor naive prompt variants on the same 10-paper variance subset only, not as a new headline.
```

Do not add a post-hoc optimized naive prompt to the main comparison.

Suggested wording:

```text
The naive prompt is intentionally not optimized: it represents the realistic baseline of asking the same frontier model to grade the same PDF without AIPR's rubric, audit, or structured output. Because the prompt was frozen before unblinding, its purpose is not to maximize baseline performance but to isolate the value of the pipeline.
```

### 8. AIPR output auditability and examples

Reviewer ask:

```text
Can I see what AIPR actually said, not just the score?
```

The paper says full generated review text is retained but not published by default. That may be acceptable, but examples help.

Feasible addition:

```text
Publish 3-5 de-identified examples:
- correctly flagged rejected paper
- false negative
- false positive
- high-scoring accepted paper
- low-scoring rejected paper
```

For each:

```text
AIPR score/subscores
AIPR weakness summary
human-review excerpt
decision tier
```

Suggested wording:

```text
We release de-identified case-study excerpts for representative correct and incorrect score outcomes; full generated reviews are retained as controlled audit artifacts because the submissions and reviews are identifiable on OpenReview.
```

### 9. Ethics and deployment boundary

Reviewer ask:

```text
Could this be used to desk-reject papers automatically or worsen review bias?
```

The paper says human-in-the-loop and no replacement. It could still use a dedicated ethics/deployment paragraph.

Feasible addition:

```text
Add "Deployment boundary" subsection:
- no automatic acceptance/rejection
- no positive selection
- no use without human review
- low-score flag means "needs human attention"
- log and audit model-assisted decisions
- disclose AI assistance to reviewers/authors if deployed in a venue
```

Suggested wording:

```text
The validated action is not rejection. It is prioritization for human attention. A low score should trigger review, not replace it; a high score should not be used for positive selection. Any venue deployment should log model outputs, keep humans accountable for decisions, and disclose the role of automated assistance.
```

### 10. Bias and author/prestige sensitivity

Reviewer ask:

```text
Does AIPR score famous authors, institutions, countries, or topics differently?
```

The paper mentions a separate prestige-perturbation experiment. Reviewers may want at least a pointer and minimal result.

Feasible additions:

```text
If the submitted ICLR PDFs are anonymized, state that author/institution bias is structurally limited in this cohort.
Report is_anonymized rate.
Summarize the separate prestige-perturbation experiment if available.
```

Suggested wording:

```text
The ICLR submitted PDFs in this cohort are double-blind, so printed author and institution identity are not available to the scorer for the primary study. Bias from topic priors can still remain; identity sensitivity is addressed separately by a controlled prestige-perturbation experiment that holds manuscript text fixed and varies only the author/institution block.
```

### 11. Topic prior / hotness confounding

Reviewer ask:

```text
Is AIPR rewarding trendy areas rather than manuscript quality?
```

This differs from author prestige. It can happen even in anonymized PDFs.

Feasible addition:

```text
Area subgroup audit.
Area fixed-effect/covariate control.
Compare score residuals by primary_area.
```

Suggested wording:

```text
Because topic popularity may correlate with both reviewer outcomes and model priors, we treat primary area as a potential confound and report area-adjusted descriptive checks in the supplement.
```

### 12. PDF parsing and extraction failure modes

Reviewer ask:

```text
Did PDF parsing quality affect scores?
```

The pipeline grades PDFs directly, but any extraction/audit layer can fail.

Feasible addition:

```text
Report parse failures and excluded counts.
Report whether page_count/token_count missingness is associated with scores.
Mention OCR/scanned PDFs if any.
```

Suggested wording:

```text
Submissions whose PDFs could not be parsed or graded were excluded under the pre-registered rule and reported with reasons. We do not impute scores for parse failures.
```

### 13. Cost and latency in deployment terms

Reviewer ask:

```text
Is this practically deployable at conference scale?
```

The paper reports token cost. It could translate that into operational terms.

Feasible addition:

```text
Add a small cost/latency table:
- mean input/output tokens per config
- relative cost full vs full-mini vs naive
- estimated total tokens for 10k submissions
- note that frontier is confirmation, mini is large-N proxy
```

Do not invent dollar costs unless pricing is stable and cited.

Suggested wording:

```text
The full-mini configuration establishes that the relationship can be measured at conference scale; the frontier configuration confirms the production score on a budgeted subset. We report token usage rather than dollar cost because model prices change over time.
```

### 14. Failure-mode taxonomy depth

Reviewer ask:

```text
Your failure-mode examples are anecdotal. Can you systematize them?
```

Current failure modes are good but qualitative. A light coding pass would help.

Feasible addition:

```text
For top false negatives and false positives, code the dominant reason:
- contribution-level novelty miss
- unexecuted/reproducibility defect
- overclaimed theory
- weak baselines
- synthetic benchmark concern
- reviewer forgave real flaw due to contribution
```

Report counts, not p-values.

Suggested wording:

```text
We coded the largest score-outcome disagreements into qualitative error classes. The goal is not inference but deployment guidance: identifying which failures require human review because the model cannot resolve them from the PDF alone.
```

### 15. Relationship to ReviewBench and comment correctness

Reviewer ask:

```text
Why not compare directly to ReviewBench or evaluate comment quality?
```

The current secondary analysis is synthetic. Be careful: do not present synthetic comment-quality results as real evidence.

Feasible addition:

```text
Keep ReviewBench positioning conceptual unless real AIPR comment-quality labels exist.
If real labels do not exist, remove or clearly defer synthetic secondary outputs from manuscript claims.
```

Suggested wording:

```text
We do not use ReviewBench as primary evidence because it evaluates intrinsic comment properties rather than score validity against external outcomes. A direct comment-quality comparison is complementary and left to future work.
```

### 16. Independent reproduction of AIPR scores

Reviewer ask:

```text
Can another lab reproduce the actual AIPR scores if the scorer is proprietary?
```

This is a hard limitation. Best feasible answer:

```text
Release all labels/scores/code.
Release hashes/config IDs for scorer artifacts.
Provide API or controlled evaluation route for new manuscripts.
Offer escrow/confidential audit of prompts/configs.
```

Suggested wording:

```text
The score-to-outcome analysis is fully reproducible from released data; the proprietary manuscript-to-score function is not independently reimplementable from the paper. We therefore provide scorer version identifiers and retain the exact grading artifacts for controlled audit.
```

### 17. Conflict of interest and self-validation

Reviewer ask:

```text
Is this just AIPR validating itself?
```

The paper already acknowledges single-author/proprietary-instrument concerns. Make it more direct.

Feasible addition:

```text
Add a conflict-of-interest / independence paragraph.
Make the data/code release prominent.
Offer independent rerun or third-party audit.
```

Suggested wording:

```text
Because this is an author-led validation of a proprietary system, the design emphasizes pre-registration, frozen cohorts, generated analyses, released labels/scores, and explicit failure-mode reporting. Independent replication on another venue remains the strongest next step.
```

### 18. Generalization beyond ICLR

Reviewer ask:

```text
Does this generalize to other fields, journals, non-ML venues, or closed-review settings?
```

Current answer: no, not yet. Good.

Feasible addition:

```text
State which part should generalize and which should not:
- score-vs-reviewer-rating can generalize to venues with ratings
- reject-class validation needs venues publishing rejected papers
- author/prestige issues differ in non-blind venues
```

Suggested wording:

```text
The design generalizes most directly to venues that publish both rejected submissions and review ratings. In venues that publish only accepted work, the low-score reject-flag claim cannot be tested directly; only continuous rating agreement can be evaluated.
```

### 19. Rebuttal/post-review drift

Reviewer ask:

```text
Reviewer ratings and decisions may reflect rebuttal discussion, not only the submitted PDF. Is that unfair to AIPR?
```

The paper mentions this in limitations. Could be sharper.

Feasible addition:

```text
Report whether ratings are initial ratings or final ratings if OpenReview exposes both.
If only final mean is available, state that explicitly.
```

Suggested wording:

```text
The score is computed from the submitted PDF, while the public decision may incorporate rebuttal and discussion. This mismatch likely lowers measured agreement where papers improve or reviewer opinions change after rebuttal; it is therefore a conservative source of noise for manuscript-only scoring.
```

### 20. What the system cannot see

Reviewer ask:

```text
Can AIPR detect fabricated results, unreleased code problems, or proof errors?
```

Failure modes mention this. Make it a deployment boundary.

Suggested wording:

```text
AIPR reads the manuscript; it does not execute code, rerun experiments, inspect private data, or mechanically verify proofs. Errors whose evidence is absent from the PDF remain human-review responsibilities.
```

## Broader Additions, Ranked

If the goal is to make the paper harder to attack without bloating it, prioritize:

1. Manifest/provenance cleanup: cohort manifest, PDF hashes, raw decision mapping.
2. Inference-time leakage paragraph: exactly what the grader could and could not access.
3. Threshold calibration honesty: rank/triage, not universal AIPR@60.
4. Bias/deployment boundary: human-in-the-loop, no automatic rejection, anonymized PDFs.
5. Proprietary scorer audit posture: version IDs, prompt/config hashes, confidential audit option.
6. Human-review reliability ceiling if per-review data are available.
7. Area/topic and covariate controls.
8. Failure-mode coding counts.
9. Cost/scale table in tokens.
10. Sample representativeness audit.

These are all possible within the existing study shape. None requires changing the core pre-registered analysis.
