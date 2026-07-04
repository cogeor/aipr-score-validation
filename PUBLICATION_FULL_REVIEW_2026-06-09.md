# AIPR Publication Full Review — 2026-06-09

Reviewer: Codex  
Artifacts reviewed:
- `paper/main.pdf` rebuilt and extracted with `pdftotext -layout`
- `paper/sections/*.tex`
- `paper/macros/results_macros.tex`
- `frontend/src/app/publications/page.tsx`
- live website at `http://localhost:3000/publications`
- stale/broken live website at `http://localhost:3939/publications`
- current website screenshot: `C:\Users\costa\src\aipr\artifacts\publications-review-current-3000.png`

## Restated Goal

The goal of this review is to determine whether the AIPR score-validation publication:

1. reads well as a paper;
2. puts forward AIPR's arguments clearly, correctly, and in the best defensible light;
3. uses plots and website companion figures that are coherent, publication-ready, and stylistically aligned, using the website plots as the visual baseline.

I reviewed the compiled PDF, not only the LaTeX source. I also checked the live website rendering, because the website is meant to be the plot-style baseline.

## Executive Judgment

Current readiness: **not publication-ready today because of consistency and rendering blockers**.

Underlying paper quality after fixes: **strong B+ / A- potential**.

The argument itself is good and commercially useful for AIPR: the paper validates a narrow, human-in-the-loop first-pass score and reframes AIPR's product value as reliability, grounding, structured output, and workflow, not raw model superiority. That is the correct posture.

However, the current compiled PDF and current website are not aligned. The PDF I rebuilt from current generated macros reports `ΔAUROC 0.16`, `p=0.00`, and `n=96`, while the intended website baseline reports `ΔAUROC 0.07`, CI crossing zero, `p=0.09`, and `n=100`. This is the top blocker. Until the PDF, macros, plots, and website all agree on the same result snapshot, the paper should not be circulated.

## Blockers

### 1. PDF result snapshot contradicts the intended naive-baseline claim

The user-stated correct interpretation is:

- AIPR vs naive prompt: `p=0.09`
- AIPR was higher, but the comparison was not statistically resolved
- this does not prove equivalence
- the paired cohort was not powered to resolve a small difference over an already strong naive baseline

The current website data at `frontend/src/features/study/data/points.json` matches that:

- `auroc_full = 0.8712`
- `auroc_naive = 0.8008`
- `delta = 0.0704`
- CI `[-0.01122, 0.1552]`
- `p = 0.090477...`
- `n = 100`

But the rebuilt PDF currently says:

- `AIPR full = 0.90`
- `naive = 0.74`
- `ΔAUROC = 0.16`
- CI `[0.06, 0.26]`
- `p=0.00`
- `n=96`

This appears in the abstract, introduction contributions, results, discussion, conclusion, Fig. 3 caption/extracted text, and appendix.

Why this is bad:

- `p=0.00` and CI `[0.06, 0.26]` actually support superiority, not "not powered for a small difference."
- The text still says "not statistically resolved" around a statistically significant result.
- This makes the central argument internally contradictory.
- A reviewer will immediately lose trust because the numbers and interpretation disagree.

Required fix:

- Choose one authoritative result snapshot.
- If the correct result is the website result, regenerate or restore paper macros/figures from that exact data.
- The PDF, website, static paper figures, table values, and captions must all report the same `n`, AUROC, CI, and p-value.

### 2. Current `3939` website route is stale and visually broken

`http://localhost:3939/publications` returns an older page:

- H1: `Research from the AIPR team`
- `recharts-wrapper` count: `0`
- plot regions are blank
- huge social icons dominate the bottom of the page
- screenshot: `C:\Users\costa\src\aipr\artifacts\publications-review-current-3939.png`

This route is not usable as a public companion page. It should not be used for screenshots, review, or launch checks.

### 3. The current PDF still contains old/overstrong "parity" rhetoric in generated figures/captions

Even after the source wording was improved, the rebuilt PDF still contains phrases such as:

- "Scoring parity"
- "AIPR separates accepts from rejects at least as well as the bare prompt, not better."
- "The full pipeline does no better" in the stale extracted PDF before rebuild, and equivalent figure/caption language remains in places.

With the intended `p=0.09` framing, "parity" is risky unless defined very carefully. The statistically correct claim is:

> The observed AIPR AUROC is higher, but the paired comparison was not statistically resolved; the study does not prove superiority or equivalence.

Suggested replacement everywhere:

> Strong naive baseline, unresolved AIPR-vs-naive gap

Avoid:

- "parity"
- "does no better"
- "matches"
- "statistically indistinguishable"
- "at least as well"

Those phrases imply equivalence or non-inferiority, which was not tested.

## Paper Argument Review

### What works well

The paper's core structure is strong:

1. Peer review is noisy and strained.
2. Most AI-review studies evaluate generated text, not the validity of a numeric score.
3. AIPR is evaluated as a fixed deployed instrument.
4. The score is validated against public ICLR decision tiers and mean reviewer ratings.
5. The validated claim is bounded: weak-work triage, not acceptance prediction or reviewer replacement.
6. The naive prompt comparison reframes the product value: intelligence is already present in the frontier model; AIPR adds stability, grounding, structure, and deployability.

This is a good story for AIPR. It puts AIPR in a credible light because it avoids the bad startup posture of overclaiming "AI reviewer beats humans." It instead says:

> We can measure a useful first-pass signal, and we can package it into a reliable, grounded, human-controlled review workflow.

That is both scientifically more defensible and commercially stronger.

### What is currently too broad

The title and repeated phrase "Intelligence is not the bottleneck" are memorable, but they need disciplined support. The paper should consistently attach this to:

- this ICLR cohort;
- first-pass score-outcome agreement;
- the frontier model used here;
- human-in-the-loop triage.

Avoid letting the sentence read as:

> LLMs can review papers.

Better:

> In this ICLR cohort, a frontier model already produced a meaningful first-pass score signal; the harder deployment problem is reliability, grounding, and accountable presentation.

### The "validity" wording needs care

The paper sometimes treats "validity" as the score-outcome relationship and sometimes as the pipeline's overall review quality. Keep "validity" tied to measurement:

- valid for weak-submission triage;
- valid as criterion-related evidence against ICLR outcomes;
- not valid as acceptance-probability prediction;
- not valid as independent proof of every subdimension.

Suggested language:

> The score is validated for one interpretation and use: prioritizing manuscripts for human attention when the score is low relative to the venue bar.

### Citation dimension caveat is handled honestly but should be more visibly separated

The citation subscore failure is a real blemish:

- frontier citation score pinned at 100%;
- chance AUROC;
- empty audit treated as perfect bibliography.

The manuscript handles this with honesty, which helps trust. But the abstract says AIPR emits five dimensions and then validates the overall score. Readers may infer that all five dimensions are validated. The paper should state early:

> The overall score is validated; the citation subscore is not validated in this cohort.

This does not sink the paper because citation is lightly weighted and dropping it preserves the headline. But it must not be visually or rhetorically buried.

## Readability Review

### Strengths

- The introduction is clear and persuasive.
- The paper states non-claims explicitly, which is good.
- The Methods section is unusually disciplined for an applied AI validation paper.
- The failure-mode section makes the paper more credible; it reads like a validation, not a sales deck.
- The conclusion lands the right boundary: human attention, not replacement.

### Weaknesses

1. The paper is long for the central claim.

   The appendix is large, and the pre-registration verbatim block creates layout/overfull issues. This is acceptable for a technical appendix, but the main paper should stay leaner.

2. The current PDF has production polish issues:

   - multiple overfull boxes;
   - pre-registration table lines run far past margins;
   - some extracted equations/macros render awkwardly, e.g. the low-end bridge CI in limitations;
   - stale or regenerated macro values contradict the intended story.

3. The naive-baseline discussion still needs one clean canonical paragraph.

   Recommended canonical version:

   > The bare one-paragraph prompt already separated rejected from accepted submissions. AIPR's observed AUROC was higher, but the paired comparison was not statistically resolved (`ΔAUROC 0.07`, 95% CI crossing zero, `p=0.09`). This is not evidence of equivalence. It shows that the naive baseline is already strong and that this paired cohort was not powered to resolve a small performance gap. AIPR's demonstrated advantage in this study is reliability and deployable review structure, not proven higher discrimination.

## Plot And Figure Review

### Additional Needed Support Figure: Score vs Non-Identifying Covariate

Add one support-only plot showing AIPR overall score on the y-axis against a non-identifying manuscript covariate on the x-axis.

Recommended paper version:

- one compact appendix/support figure;
- y-axis: AIPR overall score;
- x-axis: paper length or another non-identifying manuscript-surface variable;
- preferred x variable for the static paper panel: `word_count` or `page_count`;
- optional color: decision tier, if visually readable;
- annotate Spearman rho and 95% CI;
- keep it out of the main result flow because the paper is already long.

Recommended website version:

- same y-axis: AIPR overall score;
- interactive x-axis selector for non-identifying variables:
  - page count;
  - word count;
  - token count if present;
  - number of references;
  - number of figures;
  - possibly reviewer-rating SD, but label this separately because it is a review-process variable, not a manuscript-surface variable.
- hover can show the usual point metadata, but avoid exposing identifying fields if this is framed as a non-identifying covariate check.

Why this matters:

- It gives reviewers an immediate visual answer to "is AIPR just rewarding long/polished papers?"
- It makes the already-existing covariate controls tangible.
- It is safer than putting another headline AUROC figure in the main paper.
- It supports the credibility of the score without lengthening the narrative.

Current status in the repo:

- The analysis already has manuscript-length confounding checks:
  - `analysis/run_all.py::_length_confound`
  - `analysis/stats.py` covariate helpers
  - `paper/tables/tab_length_confound.tex`
  - appendix section `Manuscript-length confounding`
- The analysis already has covariate-control AUROC:
  - `analysis/stats.py::covariate_control_auc`
  - `paper/tables/tab_covariate_control.tex`
  - appendix section `Covariate-control discrimination`
- The analysis already has area/subfield subgroup audit:
  - `analysis/stats.py::area_subgroup_audit`
  - `paper/tables/tab_area_subgroup.tex`
  - appendix section `Area/subfield subgroup audit`
- The data schema already supports relevant non-identifying metadata:
  - `primary_area`
  - `page_count`
  - `word_count`
  - `token_count`
  - `n_references`
  - `n_figures`

Clarify the token variables:

- `token_count` is a manuscript-surface/length proxy when present in `submissions.csv`.
- grading/review token usage is a different variable from `gradings.csv` (`input_tokens`, `output_tokens`, and derived cost/token tables).
- For the covariate scatter, manuscript `token_count`, `page_count`, `word_count`, `n_references`, and `n_figures` answer "is the score just tracking paper length/polish?"
- Review/grading tokens answer a different support question: "what did each grading run cost, and does the pipeline spend more tokens under some configurations?" They should **not** be included in the covariate-control study, because they are partly downstream of the grading configuration and model behavior, not a pre-existing manuscript property. Mixing them with manuscript covariates risks bad causal semantics: a reviewer could read the analysis as controlling for something the system itself produced or consumed during scoring.

Protocol/schema status:

- This separation is already fixed in the current protocol/data contract.
- `analysis/schema.py` explicitly says `page_count` / `word_count` / `token_count` are manuscript-length metrics, while grading-side token usage lives in `gradings.csv`.
- `analysis/DATA_SCHEMA.md` defines `token_count` under `submissions.csv` as manuscript length, and `input_tokens` / `output_tokens` under `gradings.csv` as optional grading-run usage for cost summaries.
- `analysis/run_all.py` already treats them separately:
  - `_length_confound(...)` uses manuscript covariates: `page_count`, `word_count`, `n_references`, `n_figures`;
  - `covariate_control_auc(...)` uses manuscript-surface + area covariates;
  - `_cost_by_config(...)` uses `input_tokens` / `output_tokens` for cost-design reporting.

Recommendation:

- Keep review/grading token usage out of the covariate study.
- Keep it in the cost/design appendix and optionally as a separate website view titled something like "Token use by grading run" or "Cost and token usage."
- If the website exposes token usage in the interactive covariate area, visually separate it into a different control group from "Manuscript covariates" and avoid calling it a confound-control variable.

Important implementation note:

The current appendix already reports the table-level check, but a plot would be more reviewer-friendly. This should be a support figure only, not a main-paper figure. The website can carry the richer interactive version; the paper should use a single clean panel. If using one static x-axis in the paper, prefer `word_count` or `page_count`; `n_figures` is also useful as a polish/complexity proxy but may be noisier. Keep review-token usage as a separate cost/support panel, not the primary covariate panel and not part of the covariate-control model.

### Website baseline: `http://localhost:3000/publications`

This is the correct current website baseline. It renders:

- 4 Recharts wrappers;
- clean scatter/variance/bridge plots;
- good restrained typography;
- no giant social icon bug;
- coherent page hierarchy;
- screenshot: `C:\Users\costa\src\aipr\artifacts\publications-review-current-3000.png`.

The website plot style is much better than the static PDF figures:

- lighter visual weight;
- cleaner grid;
- more readable spacing;
- less academic clutter;
- good use of color for reject/poster/oral and accepted/rejected.

The website should be the visual source of truth.

### Website issues

1. The section title still says:

   > The model is already intelligent enough

   This is punchy but slightly too broad. Prefer:

   > The model already carries much of the signal

2. The website text still includes:

   > scoring parity

   That should be removed. Use:

   > unresolved AIPR-vs-naive gap

3. The plot caption/text says:

   > statistically indistinguishable

   This should be avoided. It implies equivalence. Use:

   > not statistically resolved

4. The website conclusion says:

   > whether a model can judge a paper, which it can

   This is too broad. Better:

   > whether a model can produce a meaningful first-pass score in this cohort, which it can

5. The first plot has a blank left-side hover pane that reads as unused space in a static screenshot. For the website this is okay if hover works, but for publication screenshots the plot would be stronger without the empty panel or with a default selected point.

### PDF static figure style

The static PDF plots are serviceable but less polished than the website. Specific concerns:

1. Fig. 2 is dense.

   It contains three panels, multiple encodings, small text, and long caption. It is acceptable academically, but the website version is more readable.

2. Fig. 3 caption is currently conceptually wrong for the intended `p=0.09` story.

   It should not say "parity" or "not better." It should say "not statistically resolved."

3. Fig. 5 in appendix still uses parity/equivalence-style language.

   This needs cleanup.

4. Static figures should adopt website style:

   - consistent color palette;
   - lighter grid lines;
   - larger labels;
   - less caption burden;
   - no contradictory annotations;
   - no title language implying equivalence.

5. If figures are generated from analysis, the website and paper should share one data source or an explicit export contract.

   Right now the website source and paper macros can drift, and they did.

## Website vs Paper Consistency

Current consistency status:

| Surface | Status |
|---|---|
| Website source (`page.tsx`) | Mostly correct on `p=0.09`; still has some parity wording depending on running server/source version |
| Website data (`points.json`) | Correct intended naive comparison (`Δ=0.0704`, `p=0.09048`, `n=100`) |
| Live `3000` page | Renders plots; visually coherent; text still has parity/indistinguishable language |
| Live `3939` page | Stale and broken; do not use |
| Rebuilt PDF | Compiles, but central numbers drift to `Δ=0.16`, `p=0.00`, `n=96` |
| Paper source text | Mostly corrected conceptually, but generated macros can make it contradictory |
| Static paper figures | Generated from drifted macro/result snapshot; not aligned with website |

This is the main operational issue. The public package needs one source of truth.

## Recommended Fix Plan

### Must Fix Before Circulation

1. Restore one authoritative result snapshot.

   Use the intended website data if `p=0.09` is correct:

   - `full AUROC = 0.8712`
   - `naive AUROC = 0.8008`
   - `ΔAUROC = 0.0704`
   - CI `[-0.011, 0.155]`
   - `p=0.09048`
   - `n=100`

2. Regenerate:

   - `paper/macros/results_macros.tex`
   - `paper/figures/fig_naive.*`
   - any naive-baseline tables
   - website `points.json` only if needed

3. Rebuild PDF and re-run:

   - `pdftotext -layout`
   - grep for `p=0.00`, `0.16`, `n = 96`, `parity`, `does no better`, `statistically indistinguishable`

4. Remove equivalence language from every surface.

5. Retire or rebuild the `3939` page. Do not use it as evidence.

### Should Fix For Publication Polish

1. Rework static figures to match the website baseline.

2. Add one support figure for score vs. non-identifying manuscript covariate.

   The analysis already has length-confound and covariate-control checks. Add a simple visual: y = AIPR score, x = page count or word count in the paper; interactive x-variable selector on the website. Include `n_figures` and `n_references` in the selector. Do not include review/grading input/output tokens in the covariate-control study; keep those as cost-design evidence or a separate website panel.

3. Make the citation-dimension caveat visible in abstract/introduction/methods.

4. Shorten Figure 2 and Figure 3 captions.

5. Fix overfull appendix tables or wrap the verbatim pre-registration in a smaller font/landscape/minipage.

6. Change section headings:

   - from `Scoring parity`
   - to `A strong naive baseline`
   - or `What the pipeline adds beyond a strong model`

7. Avoid "trustworthy" unless immediately bounded:

   - "trustworthy first-pass signal" is too broad;
   - "substantially outcome-aligned first-pass signal in this cohort" is safer.

## Suggested Canonical Claims

Use this wording consistently across paper and website.

### Main Claim

> AIPR's score agrees strongly with human ICLR outcomes for a narrow use: low-score manuscripts are much more likely to be rejected, so the score is useful as a human-reviewed triage signal.

### Naive Baseline Claim

> A bare one-paragraph prompt to the same frontier model already produces a meaningful first-pass score. AIPR's observed AUROC is higher, but the paired comparison is not statistically resolved (`p=0.09`), so the study does not prove superiority or equivalence. AIPR's demonstrated value is reliability and a grounded, rubric-anchored review workflow.

### Product Claim

> AIPR does not replace reviewers. It turns an already-capable model signal into a stable, inspectable first read that a human can question, edit, and use to prioritize attention.

### Citation Claim

> The overall score is validated; the citation subscore is not validated in this cohort because the frozen audit fallback pinned many scores. Dropping citation does not change the headline result.

## Final Grade

Current artifact grade: **B- / 80** because the compiled PDF and website are inconsistent on the central result.

Expected grade after blockers fixed: **A- / 88**.

The paper has a strong, honest argument and puts AIPR in good light when stated correctly. The main risk is not the scientific story; it is artifact consistency. Fix the result snapshot drift, remove equivalence language, and align static figures to the website visual baseline. After that, the publication will read as a credible validation study rather than a product claim dressed as science.
