# Editorial Review: Prose, Figures, Flow, and Cut Plan

Date: 2026-06-10  
Scope: current arXiv manuscript in `paper/sections/*.tex`; what should stay in
main text, move to supplement, or be cut for an NMI variant.

## Executive Diagnosis

The paper has the right scientific material, but the current manuscript is
over-explanatory. It reads like a careful validation dossier, not yet like a
high-impact journal article.

The main content problem is repetition. The same claims recur in the abstract,
introduction, results, discussion, limitations, and conclusion:

- low-score triage, not replacement;
- naive frontier baseline already strong;
- AIPR adds deployability/reliability;
- citation subscore is not validated;
- scorer is proprietary but outputs/analysis are open;
- leakage is bounded but not eliminated.

Each of these points is important, but NMI needs each point once in the right
place, with the technical proof moved to Methods/Supplement.

Current approximate main-section word counts:

| Section | Approx. words | Editorial action |
|---|---:|---|
| Abstract | 360 | cut to 100-150 |
| Introduction | 1,075 | cut to 600-750 |
| Related Work | 597 | fold into intro, 250-350 |
| Data | 547 | move mostly to Methods |
| Methods | 795 | move after Discussion; tighten |
| Results | 1,641 | keep core, cut repetition |
| Failure Modes | 564 | compress to one Results/Discussion subsection |
| Discussion | 1,299 | cut by half, remove subheading sprawl |
| Limitations | 943 | move most to Discussion/Supplement |
| Conclusion | 398 | cut entirely for NMI or reduce to final paragraph |
| Appendix | 3,936 | convert to Supplementary Information |

## Prose Review

### What works

The prose is unusually honest for an AI-system validation paper. It does not hide
the naive baseline, the failed citation subscore, the proprietary scorer, or the
human-in-the-loop boundary. That is a strength and should remain.

The best sentences are the ones that name the real contribution:

> What the engineered pipeline adds is therefore not validity but deployability.

This idea should be the spine of the paper.

### What weakens the prose

1. **The paper over-explains its non-claims.**

   The repeated disclaimers start to sound defensive. Say them once strongly:
   low-score triage, no automated rejection, no acceptance prediction.

2. **The slogan appears too often.**

   "Intelligence is not the bottleneck" is memorable but should not carry the
   technical meaning every time. Use it once in Discussion, not as a repeated
   substitute for the exact finding.

3. **AIPR is too central too early.**

   The NMI version should start with the peer-review/AI-policy problem, then
   introduce AIPR as the instrument. Current draft introduces AIPR like the paper
   is primarily product validation.

4. **The prose sometimes uses too many paired abstractions.**

   Examples: "reliability, grounding, and accountable presentation"; "stability,
   grounding, and accountable presentation"; "grounded, anchored, rubric-anchored."
   Pick one canonical triad and keep it stable:

   > reliability, grounding, and auditability

5. **The result narrative is too cautious in places where the evidence is strong.**

   Low-score relative triage is not merely an analytical artifact. It is a
   deployment design: a venue chooses the share of papers that need extra human
   attention. State that confidently.

## Flow Review

### Current flow

The current flow is:

1. Problem and motivation.
2. Related work.
3. Data.
4. Methods.
5. Results.
6. Failure modes.
7. Discussion.
8. Limitations.
9. Conclusion.

This is fine for arXiv but too segmented for NMI. It creates repeated ramps into
the same argument.

### Better NMI flow

1. **Opening / Introduction**
   - Peer review is under strain.
   - AI use is already present but publisher concerns are real.
   - Existing NMI work shows LLM feedback can improve reviews.
   - Missing question: does a first-pass numeric manuscript score align with human
     outcomes?
   - We test this using AIPR on public ICLR outcomes.

2. **Results**
   - A first-pass score tracks human outcomes.
   - Low-score triage is the defensible operating point.
   - A naive frontier prompt already carries much of the signal.
   - AIPR adds reliability/auditability, not proven higher discrimination.
   - Failure modes define where human review is non-negotiable.
   - Two-year ICLR contrast/replication if added.

3. **Discussion**
   - Implication: controlled AI assistance should be evaluated, not categorically
     rejected.
   - Boundary: no automated decisions.
   - Constraints: same venue, proprietary scorer, citation audit, leakage, noisy
     ground truth.

4. **Methods**
   - cohorts;
   - model/pipeline configs;
   - pre-registration;
   - statistical analysis;
   - reproducibility/audit posture.

## Section-By-Section Cut Plan

### Abstract

Current: about 360 words.

Cut:

- most numeric detail;
- repeated citation caveat unless necessary;
- long AUROC/CI/p-value sentence for naive comparison;
- "weighted overall score" details.

Keep:

- problem;
- cohort;
- headline score-outcome agreement;
- naive baseline insight;
- AIPR deployment value;
- human-in-the-loop boundary.

Target:

100-150 words for NMI, 180-220 for arXiv if desired.

### Introduction

Keep:

- peer review strain;
- text-vs-score evaluation gap;
- AIPR as instrument;
- bounded use case;
- naive baseline as central value question.

Cut or move:

- detailed contribution list of five bullets;
- operational website URL from main intro;
- most pre-registration/reproducibility detail.

Add:

- explicit comparison to Thakkar et al. NMI feedback study;
- publisher-policy-safe framing: controlled AI assistance, not informal uploads.

For NMI, the intro should be roughly 6-8 paragraphs, not a full mini-review.

### Related Work

For NMI, cut the standalone section.

Move into intro as three compact paragraphs:

1. LLM feedback/review-text assistance, including Thakkar et al.
2. Peer-review noise and why low-end triage is the right claim.
3. Acceptance prediction and why manuscript-only score validation is different.

Cut:

- detailed descriptions of MARG, AI Scientist, AMPERE, NLPeer unless directly
  needed;
- Spearman/Bradley-Terry/calibration methodology citations from main text;
- citation-count literature from main text unless citation audit remains central.

Keep those in Supplement or Methods references.

### Data

For NMI, move into Methods.

Keep in main Results only the minimum:

- public ICLR submissions;
- submitted PDFs;
- decision tiers and mean reviewer ratings;
- ICLR 2026 primary, ICLR 2025 secondary if added.

Move to Methods/Supplement:

- raw exclusion details;
- data contract;
- manifest explanation;
- PDF SHA details;
- population ledger.

### Methods

For NMI, Methods moves after Discussion.

Keep:

- exact model identifiers;
- pipeline version;
- scoring formula;
- cohort construction;
- endpoint definitions;
- statistical analysis;
- reproducibility and audit posture.

Cut from main Methods:

- long justification of BCa coverage simulations;
- detailed list of all secondary analyses;
- repeated explanation that no model was trained/fine-tuned.

Move to Supplement:

- power/estimator simulations;
- schema invariants;
- full pre-registration.

### Results

This is the strongest section but too long.

Keep in main:

1. headline table or compact metric panel;
2. low-score triage paragraph;
3. AUROC/rating/tier agreement;
4. mini-to-frontier bridge;
5. naive baseline and reliability;
6. citation audit summary only if fixed or isolated;
7. failure-mode summary.

Cut or move:

- named paper exemplars in main text;
- long explanation of AIPR@60;
- most details about prevalence reweighting;
- detailed citation-pinning mechanics;
- repeated "not superiority or equivalence" phrasing after the first clear
  statement.

For NMI, name no individual ICLR submissions in main text unless absolutely
necessary. It distracts and raises courtesy/ethics surface. Keep examples
de-identified in supplement.

### Failure Modes

Compress into one subsection:

> Failure modes define the human-machine boundary

Keep:

- correctly flagged weak work aligns at defect level;
- false negatives: contribution-level novelty and invisible defects;
- false positives: real but forgivable concerns in strong papers;
- deployment consequence asymmetry.

Move:

- table with verbatim excerpts to Supplement;
- named examples to Supplement or remove entirely.

### Discussion

Current discussion has too many paragraph-headed mini-essays.

Keep only four ideas:

1. A frontier model already has useful first-pass signal.
2. AIPR's value is reliability, grounding, and auditability.
3. Controlled AI assistance should be governed/evaluated, not categorically
   rejected.
4. Limits: same venue, proprietary scorer, citation audit, leakage/noisy human
   signal.

Move to Supplement:

- subscore halo/correlation discussion;
- detailed ReviewBench relation;
- detailed acceptance-prediction relation;
- detailed contamination mechanics;
- long citation-audit diagnosis if not a main result.

### Limitations

For NMI, do not keep a separate long limitations section.

Fold into Discussion:

- same venue/field;
- proprietary scorer;
- citation audit;
- leakage;
- noisy/AI-assisted human ground truth.

Move to Supplement:

- sample-vs-eligible representativeness;
- per-review sensitivities;
- post-rebuttal drift;
- citation relevance vs groundedness.

### Conclusion

For NMI, cut the standalone conclusion.

Use one final Discussion paragraph:

> These results do not license automated editorial decisions. They show that
> first-pass AI signals can be validated and bounded, and that the remaining
> problem is controlled deployment.

For arXiv, keep a shorter conclusion but remove the reproducibility paragraph
because that belongs in Data/Code availability.

## Figure Review

### Current main display items

Main text has:

- Fig. 0/design;
- Table sample;
- Table headline;
- Table score bands;
- Fig. validation;
- Fig. naive.

That is six display items if counted strictly. NMI permits up to six, but the mix
is table-heavy and not yet optimized.

### Figure 0 / study design

Keep, but redesign for NMI.

It should show:

- submitted PDFs;
- no OpenReview reviews/decisions in model input;
- AIPR full-mini/full and naive model configs;
- outcomes used only after scoring;
- human-in-the-loop deployment boundary.

Add exact model names in the figure or caption.

### Table sample

Move to Methods or Supplement.

For NMI main text, sample counts can be reported in prose or in the headline
metrics table. This table is useful but not worth a main display slot.

### Table headline

Keep or convert to a figure inset.

This is one of the clearest displays. If NMI allows six items, keep it. If not,
fold it into Fig. validation or a compact Extended Data table.

### Table score bands

Move to Supplement or convert into Fig. validation panel.

The decile/quintile reject-rate plot already communicates the idea better. The
table is redundant in main text.

### Fig. validation

Keep as main figure.

This should be the core empirical figure:

- score by tier;
- reject rate by score band;
- score vs reviewer rating.

Improve:

- lighter captions;
- less repetition of H1-H4 labels;
- show exact cohort and model in the panel title/caption;
- make bottom-band threshold clearly relative/capacity-based.

### Fig. naive

Keep as main figure.

It is central to novelty. The caption must avoid equivalence language.

Caption should say:

> The naive frontier prompt is already strong; AIPR's observed AUROC is higher but
> the paired difference is not statistically resolved. AIPR's demonstrated
> advantage is lower run-to-run variance and structured/auditable output.

### Bridge figure

Currently supplementary. For NMI, main only if the cheap-model/proxy design is
central. If 2025 is added, bridge likely moves to Supplement and the temporal
cohort figure takes its slot.

### Citation figures

Do not use a main figure unless the corrected citation audit becomes a positive
result. Otherwise it is a Methods/Supplement limitation.

### Failure-mode table

Supplement for NMI. It is valuable but too detailed and quote-heavy for main text.

## Recommended NMI Display Set

Use these six:

1. **Design / model-access boundary** figure.
2. **Primary validation** figure.
3. **Naive baseline + reliability** figure.
4. **Two-year ICLR temporal validation** figure/table if 2025 is added.
5. **Failure-mode / operating-boundary** compact figure.
6. **Headline metrics** table, or move to Extended Data if figure 4/5 carries the
   numbers.

If forced to five:

- cut the sample table;
- cut the score-band table;
- fold headline metrics into Fig. 2.

## What To Cut Outright

Cut from NMI main text:

- long contribution list;
- standalone Related Work section;
- standalone Conclusion;
- named ICLR case exemplars;
- full pre-registration discussion;
- power simulation details;
- estimator validation details;
- long citation-count literature discussion;
- repeated disclaimers about non-replacement;
- repeated "not superiority or equivalence" caveats after one precise statement;
- website/interactive companion mentions unless allowed and polished.

Do not cut entirely, but move to Supplement:

- pre-registration verbatim;
- schema/data contract;
- exclusion ledger;
- PDF SHA/provenance details;
- covariate controls;
- area subgroup audit;
- within-tier correlations;
- threshold sensitivity;
- reviewer-disagreement moderation;
- cost/token table;
- long failure examples.

## What To Add To Main Text

Add:

1. one paragraph comparing directly to the NMI randomized LLM-feedback study;
2. exact model identifiers and access boundary in Methods;
3. explicit policy-safe stance: controlled, disclosed, human-accountable AI
   assistance;
4. ICLR 2025 temporal validation if available;
5. short operating-boundary sentence explaining relative triage thresholds as
   capacity allocation.

## Suggested Main-Text Target Length

For NMI:

- Abstract: 120-150 words.
- Introduction: 700 words.
- Results: 1,500-1,800 words.
- Discussion: 700-900 words.
- Methods: can be longer and separate, but keep readable.

For arXiv:

- Current length is acceptable after consistency fixes, but still benefit from
  cutting 15-20% repetition.

## Final Editorial Grade

Prose quality: **B+**  
Figure quality: **B**  
Current flow: **B- for NMI, B+ for arXiv**  
After NMI restructuring: **A-/B+ potential**

The paper does not need more caveats. It needs sharper placement of caveats, fewer
repeated explanations, and a cleaner distinction between main story and audit
record.
