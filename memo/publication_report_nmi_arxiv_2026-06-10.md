# Publication Report: arXiv and Nature Machine Intelligence Strategy

Date: 2026-06-10  
Reviewer stance: demanding but not hostile  
Manuscript reviewed: `paper/` current draft, plus prior root-level reports
(`PUBLICATION_FULL_REVIEW_2026-06-09.md`, `AIPR_VALIDATION_GRADE_REPORT.md`)

## Executive Grade

**arXiv grade: A- potential; B+/A- current.**

The current manuscript is strong enough for arXiv once the result snapshot,
citation-audit caveat, and author/metadata details are clean. It is already more
careful than most AI-peer-review preprints: it is pre-registered, generated from
analysis artifacts, explicit about the naive baseline, and disciplined about
human-in-the-loop deployment.

**Nature Machine Intelligence grade: B+ potential; B-/B current format.**

The study is a credible NMI candidate only after a real journal-shape revision:
short abstract, shorter main text, NMI section order, corrected citation audit,
and a clearer two-year ICLR evidence package. It is not blocked by the proprietary
scorer if the prompts/configs are available confidentially to editors/reviewers,
but that posture must be stated plainly.

## Bottom-Line Recommendation

Submit/post the arXiv version as a bounded validation paper after the citation
audit is handled cleanly. For NMI, prepare an **Analysis**-style manuscript, not a
long arXiv validation report.

The NMI claim should not be "AIPR beats naive prompting." It does not need to. The
stronger and more broadly relevant claim is:

> Frontier LLMs already contain useful first-pass manuscript-evaluation signal in
> public ML peer-review data; the scientific and deployment problem is how to make
> that signal stable, confidential, auditable, grounded, and accountable to human
> reviewers.

AIPR is the concrete system demonstrating the controlled deployment layer.

## Are Two Datasets Required for NMI?

No. Nature Machine Intelligence does not state a formal "two datasets" rule for
Articles or Analyses. NMI's content-type guidance defines Articles/Analyses by
importance, concision, display-item limits, and section structure, not by a
minimum number of datasets.

However, for this paper's specific stance, a second cohort is strategically
important. One clean ICLR year supports:

- AIPR validates on one public OpenReview cohort.
- A frontier model has meaningful score-outcome signal in that cohort.
- Low-score triage is plausible under human oversight.

Two ICLR years support the stronger NMI-relevant claim:

- the result is not a one-year accident;
- temporal leakage can be probed more directly;
- the finding is stable within the same venue family;
- the paper can credibly argue for policy relevance rather than only product
  validation.

This is not "multi-domain generalization." ICLR 2025 and ICLR 2026 are two
temporal cohorts from the same venue ecosystem. The manuscript should call them
"two-year ICLR validation" or "within-venue temporal replication," not two
independent domains.

## Recommended 2025 Cohort Addition

Add ICLR 2025 as a **secondary temporal cohort**, not as a new primary endpoint.

Recommended structure:

1. **Primary cohort: ICLR 2026**
   - clean relative to the model cutoff for decisions/reviews;
   - main pre-registered claim lives here;
   - production/final claims should be anchored here.

2. **Secondary cohort: ICLR 2025**
   - same venue family, previous year;
   - use as temporal replication and contaminated-contrast/sensitivity;
   - do not overclaim it as leakage-free if model cutoff permits prior exposure.

Report the same core statistics:

- low-score reject enrichment;
- reject-vs-accept AUROC;
- Spearman correlation with mean reviewer rating;
- monotone tier trend;
- naive baseline comparison if budget allows;
- citation-drop sensitivity;
- arXiv/pre-cutoff sensitivity split.

Interpretation:

> The ICLR 2025 cohort is not an independent field/domain validation. It tests
> whether the score-outcome relationship recurs in the same open-review venue
> across years and whether the primary 2026 result is an isolated cohort artifact.

If ICLR 2025 is more leakage-prone, say so directly. A reviewer will respect that
more than an inflated "replication" label.

## Citation-Audit Recommendation

The citation subscore should be fixed and re-run, but it does not need to be
treated as invalidating the whole study.

Current problem:

- the citation subscore was pinned/highly degenerate in the original run;
- the audit channel treated an empty/no-result case too generously;
- the overall score is only lightly exposed to citation, and dropping citation
  preserves the headline discrimination.

Recommended framing:

> The original citation-audit channel was affected by retrieval incompleteness and
> an overly permissive empty-result fallback. We therefore do not validate the
> citation subscore in the original run. We isolate the channel, show that the
> headline overall-score result is unchanged without citation, and re-run the
> corrected audit as a separate validation step.

If the true cause is OpenReview API rate limiting, state it precisely:

- rate limiting affected retrieval or audit completeness;
- the scoring fallback then converted missing/empty audit evidence into a high
  citation score;
- the fix is to score empty/failed retrieval as unknown or failed, not perfect.

Do not imply that OpenReview rate limiting alone explains the score pinning if the
fallback semantics were also necessary.

Minimum additional citation-audit outputs:

- citation-score distribution before/after fix;
- citation AUROC before/after fix;
- overall AUROC with original citation, corrected citation, and citation dropped;
- count/share of audit failures or unknowns;
- rule: empty or failed audit is no longer scored as perfect.

For NMI, this should move from "limitation only" to "fixed engineering failure,
isolated and revalidated."

## Does the Broader Stance Stay Relevant?

Yes, but it must be stated in a way that does not collide with publisher policy.

Springer Nature/NMI policy currently asks peer reviewers not to upload manuscripts
into general generative AI tools because of confidentiality, accountability, and
reliability concerns, while also acknowledging exploration of safe AI tools and
asking for transparent declaration when AI supports evaluation. That means the
paper should not argue "reviewers should just use ChatGPT."

The defensible stance is:

> Blanket rejection of AI assistance in peer review is no longer evidence-based.
> Useful signal exists. The right question is which controlled, disclosed,
> confidential, auditable, human-accountable systems can improve peer review
> without replacing reviewers.

This is highly relevant to NMI because NMI covers both machine intelligence and
the societal/scientific implications of AI systems. It is also timely because NMI
has already published adjacent work on LLM feedback in peer review; this paper
must distinguish itself as score-validity and deployment-control evidence, not
another comment-quality study.

## Position Relative to Existing Work

The manuscript already cites much of the right literature: LLM review generation,
ReviewBench, AI-review prevalence, peer-review noise, PeerRead/NLPeer, and
acceptance-prediction work.

The missing positioning is sharper:

- prior work asks whether LLMs can produce useful **feedback** or human-like
  review text;
- this paper asks whether a first-pass **numeric manuscript-quality score** has
  criterion validity against human outcomes;
- prior work and publisher policy raise concerns about uncontrolled AI use;
- this paper argues for controlled systems, not informal reviewer uploads.

## Citations Worth Adding

Add these selectively; do not bloat the reference list.

### 1. Thakkar et al., 2026, NMI randomized peer-review feedback study

Why add:

- direct NMI-adjacent precedent;
- same broad topic: LLM assistance in peer review;
- distinguishes feedback/comment quality from score validity;
- proves the journal is willing to publish rigorous AI-peer-review work.

Use for:

> Recent randomized evidence shows that LLM-generated feedback can improve review
> informativeness and reviewer-author engagement; our study asks a complementary
> question about numeric score validity against outcomes.

Candidate bibliographic details to verify before insertion:

- Nitya Thakkar, Mert Yuksekgonul, Jake Silberg, Animesh Garg, Nanyun Peng, Fei
  Sha, Rose Yu, Carl Vondrick, James Zou.
- "A large-scale randomized study of large language model feedback in peer
  review."
- Nature Machine Intelligence, 2026.
- DOI reported in search results: `10.1038/s42256-026-01188-x`.

### 2. Nature/Springer Nature AI-in-peer-review policy

Why add:

- supports the policy stance;
- lets the paper say "current publisher policy is cautious for reasons we accept";
- sharpens the distinction between uncontrolled uploads and approved systems.

Use for:

> Current publisher policies restrict reviewer use of general generative AI tools
> because of confidentiality and accountability, but leave room for controlled,
> disclosed tools.

This may be cited as a policy URL rather than a formal paper, depending on style.

### 3. Hidden prompts / prompt-injection work in manuscripts

Why add:

- shows why uncontrolled AI-assisted review is risky;
- strengthens the argument for controlled, auditable systems;
- helps avoid sounding naive/pro-AI-at-any-cost.

Use sparingly:

> Prompt-injection incidents in manuscripts illustrate that AI-assisted review must
> be designed as a controlled system with adversarial and confidentiality controls,
> not as unregulated reviewer uploads.

Candidate:

- Zhicheng Lin. "Hidden Prompts in Manuscripts Exploit AI-Assisted Peer Review."
  arXiv:2507.06185, 2025. Verify final version before citation.

### 4. Update Russo Latona et al. AI Review Lottery entry

The repository already has this citation, but the BibTeX appears to be an arXiv
entry with a verification note. It should be updated if the CSCW/PACM HCI version
is now final.

Useful details from search results:

- "The AI Review Lottery: Widespread AI-Assisted Peer Reviews Boost Paper Scores
  and Acceptance Rates."
- Proceedings of the ACM on Human-Computer Interaction, 2025, 9(7).
- DOI: `10.1145/3757667`.

Use for:

> AI-assisted reviews are already present and consequential at major ML venues,
> making controlled evaluation urgent.

### 5. Optional: COPE or publisher guidance on AI in peer review

Only add if the discussion needs broader ethics-policy ballast. If using Nature's
own policy, COPE may be redundant.

## What Not to Add

Do not add:

- a post-hoc optimized acceptance classifier;
- many prompt variants that blur the pre-registered naive baseline;
- causal claims that AI improves final decisions;
- claims that the score predicts acceptance probability;
- claims of cross-field generalization from ICLR-only data;
- excessive apology for using relative thresholds.

The relative threshold is defensible. The validated action is not rejection. It is
allocating a venue-chosen share of manuscripts to additional human attention.

## NMI Format Requirements to Plan Around

Current manuscript is not NMI-shaped.

Known NMI Article/Analysis expectations:

- abstract: 100-150 words or up to 150 words depending content type;
- main text: up to 3,500 words, excluding abstract, Methods, references and
  figure legends;
- display items: up to 6 figures/tables;
- structure: Introduction without heading, Results, Discussion, Methods;
- Results and Methods can have topical subheadings;
- Discussion should not be subdivided with many paragraph headings;
- references guideline: up to 50.

Current draft:

- abstract is roughly 377 words;
- main narrative is far over NMI length;
- display items are at the limit;
- section order is arXiv-style;
- appendix is fine for arXiv but should become Supplementary Information for NMI.

For NMI, target **Analysis** unless an editor advises Article.

## NMI Rewrite Plan

Main text should be re-centered around five moves:

1. Peer review is strained; uncontrolled AI use is already happening; publisher
   caution is justified.
2. The relevant empirical question is not "should AI replace reviewers?" but
   whether controlled AI assistance provides useful, validated signal.
3. On two ICLR cohorts, first-pass LLM/AIPR scores align with human outcomes,
   especially at the low end.
4. The naive frontier baseline already carries substantial signal; therefore the
   bottleneck is not raw model intelligence.
5. The remaining problem is deployment control: reliability, grounding,
   confidentiality, auditability, and human accountability.

Move most robustness to Supplementary Information:

- preregistration verbatim;
- estimator simulations;
- weight robustness;
- detailed failure-mode cases;
- covariate controls;
- area subgroup audit;
- bottom-band threshold sensitivity;
- cost tables;
- exact schema.

## Recommended Main Figures for NMI

Keep no more than six display items:

1. Study design and controlled deployment boundary.
2. Main validation: score by tier, reject rate by score band, score vs reviewer
   rating.
3. Naive vs AIPR: ROC and run-to-run reliability.
4. Two-year replication/temporal contrast, if 2025 is added.
5. Failure-mode / low-score harm summary.
6. Optional table of headline metrics, or fold into figure panels if space is
   tight.

Do not spend a main display item on citation unless the corrected audit becomes a
positive methodological result. Otherwise report citation in Methods/Supplement.

## Specific Claims to Use

Use:

> The validated action is prioritization for human attention, not automated
> rejection.

Use:

> The low-score threshold is relative because reviewer attention is a venue-level
> capacity allocation problem; the venue chooses the share to inspect.

Use:

> The two-year ICLR result supports within-venue temporal robustness, not
> cross-field generalization.

Use:

> AIPR's demonstrated contribution is reliability, grounding, and auditability
> around a signal that a frontier model already largely contains.

Avoid:

> AI should be used in peer review.

Prefer:

> Controlled, disclosed, human-accountable AI assistance should be evaluated and
> governed rather than categorically dismissed.

Avoid:

> AIPR validates five dimensions.

Prefer:

> The overall score is validated; citation is isolated and revalidated after the
> audit fix.

Avoid:

> Two datasets prove generalization.

Prefer:

> Two ICLR years test temporal robustness within the same venue ecosystem.

## Final Recommendation

For arXiv:

1. Fix or clearly isolate the citation audit.
2. Ensure the naive baseline numbers and wording are internally consistent.
3. Post with the bounded claim.

For NMI:

1. Add ICLR 2025 as temporal replication/contrast.
2. Re-run corrected citation audit, or formally move citation outside the
   validated score claim.
3. Add the Thakkar et al. NMI paper and publisher-policy/prompt-injection
   citations.
4. Reframe as an Analysis about controlled AI assistance in peer review, with AIPR
   as the instrument.
5. Cut the manuscript to NMI format and move most technical detail to Supplement.

Final expected grade after those changes: **A- arXiv, B+/A- NMI submission
candidate**. The paper will not be an automatic NMI accept, but it is strong enough
to be taken seriously if the claim is scoped as controlled first-pass triage in ML
peer review rather than general AI replacement of reviewers.

## Sources Checked

- Nature Machine Intelligence content types and format guidance:
  https://www.nature.com/natmachintell/content
- Nature Machine Intelligence AI policy:
  https://www.nature.com/natmachintell/editorial-policies/ai
- Nature Machine Intelligence peer-review policy:
  https://www.nature.com/natmachintell/editorial-policies/peer-review
- NMI research listing showing the 2026 randomized LLM-feedback peer-review paper:
  https://www.nature.com/natmachintell/research-articles
- AI Review Lottery arXiv / ACM information:
  https://arxiv.org/abs/2405.02150
- Hidden prompts / AI-assisted peer-review prompt injection:
  https://arxiv.org/abs/2507.06185
