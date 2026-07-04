# Main-text trim, restructure, abstract, and naming — assessment + plan

**Date:** 2026-06-10 · **Scope:** arXiv `main.tex` MAIN TEXT only (supplement may grow as
needed). No paper edits made — this is a report. Anchored on current `main.pdf` (41 pp)
and on strong published exemplars pulled for comparison.

---

## 0. TL;DR

The main text is anomalous on three axes at once, and it repeats itself. Concretely:

1. **Too long.** Main-text body ≈ **7,800 words** (excl. abstract/captions/refs); the
   whole PDF is **41 pp**. Strong published anchors run **~3,500–4,500 words** of front
   matter (Nature HB) to **~6,000–7,000** (Thakkar/NMI arXiv body); even appendix-heavy
   ML preprints land at **~20–25 pp total**, half ours.
2. **Over-sectioned.** **9 top-level sections** vs the **4–5** of published anchors
   (Intro → Results → Discussion → Methods).
3. **Over-fragmented.** **11 subsections + 41 `\paragraph` run-ins = ~61 headed units**
   across ~7,800 words → a heading every ~128 words (Limitations: one every ~76). The
   strongest exemplar (Nature HB) uses **flat single-level subsections, 0 sub-subsections,
   and 0 subsections in Discussion**, with fine points as a *handful* of bold run-ins.
4. **Repetitive.** Each core claim is restated in **5–8 sections** (the naive/"intelligence
   not the bottleneck" thesis appears in 6 sections; prereg/reproducibility in 8). This is
   the biggest single lever for cutting length without losing content.
5. **Abstract is 406 words** — nearly 2× the ~150–230-word norm of every strong exemplar.

**Targets:** main-text body **7,800 → ~5,000–5,500 words** (~30% cut), **9 → 6–7 sections**,
**41 → ~20 `\paragraph` units**, **abstract 406 → ~200 words**. Achieve most of the cut by
de-duplicating (state each claim once, cross-reference) rather than deleting findings.
Move detail to the (growing) supplement.

**Naming:** drop `full` / `full-mini` / `naive`. Adopt **`AIPR (GPT-5.4)`**,
**`AIPR (GPT-5.4-mini)`**, **`Direct (GPT-5.4)`** (Scheme 1 below). "Direct" is the neutral
standard term; "naive" reads as strawman-stacking to a skeptical reviewer.

---

## 1. Current state — measured

### 1a. Word count per section (texcount, body + headers + captions)

| Section | Body words | Caption words | `\subsection` | `\paragraph` |
|---|---:|---:|---:|---:|
| Abstract | 406 | – | – | – |
| 1 Introduction | 1001 | 80 | 0 | 1 |
| 2 Related Work | 704 | 0 | 0 | 4 |
| 3 Data | 562 | 29 | 0 | 6 |
| 4 Methods | 1088 | 40 | 5 | 0 |
| 5 Results | 1492 | 168 | 3 | 11 |
| 6 Failure Modes | 581 | 0 | 3 | 2 |
| 6b Discussion | 1193 | 0 | 0 | 6 |
| 7 Limitations | 833 | 0 | 0 | 10 |
| 8 Conclusion | 364 | 0 | 0 | 1 |
| **Main total** | **~7,818** | ~317 | **11** | **41** |
| 9 Appendix | 3,122 | 1,141 | (37 headed units, 27 floats) | — |

Top-level sections in main text: **9**. Sub-subsections: **0** (good — keep it flat).

### 1b. Repetition map — how many sections restate each claim

| Core claim | # main sections that state it | Where |
|---|:--:|---|
| Naive baseline already strong | 6 | abs, intro, methods, results(×23 hits), disc, concl |
| "Intelligence is not the bottleneck" | 5 | abs, intro, results, disc, concl |
| AUROC diff not statistically resolved | 5 | abs, intro, results, disc, concl |
| Reliability / run-variance | 9 | everywhere (we just amplified this — now over-stated) |
| Citation audit-fallback artifact | 5 | abs, methods, results, disc, limits |
| "We do not claim … / human keeps decision" | 6 | abs, intro, results, disc, limits, concl |
| Pre-registration / reproducibility | 8 | abs, intro, related, data, methods, results, limits, concl |
| Low-end flag (H1) | 5 | abs, intro, related, results, concl |

This is the core problem: the paper says each of ~8 things ~5 times. **One home + pointers**
is the fix (§5).

---

## 2. Benchmark — strong / comparable papers

Full structural pulls (agent research, sources at end). Front matter = Intro/Main +
Results + Discussion, excluding end-matter Methods.

| Paper | Venue | Top-level §§ | Subsections | Sub-subsec | Main-text words | Abstract |
|---|---|:--:|:--:|:--:|---:|---:|
| **Thakkar et al.** (our closest anchor) | **Nature MI** Article | 5 | 6 | **0** | ~6–7k (arXiv body) | ~210 w |
| **Liang et al.** "useful feedback" | **NEJM AI** | 4–5 | ~10 (mostly Methods) | **0** | ~8–9.5k (Methods end-matter) | structured / ~363 w arXiv |
| **Liang et al.** "Quantifying LLM usage" | **Nature HB** Article | **4** | ~14 flat; **0 in Discussion** | **0** | **~3.5–4.5k** front + ~2k Methods | **~190 w** |
| Liang "Monitoring AI-modified" | ICML 2024 | (measurement-validation twin) | flat | 0 | — | ~166 w |
| ReviewerToo | arXiv | 8 | ~18 | 1 | ~8.5k | ~227 w |
| LLM-as-a-Reviewer | arXiv | 6 | 4 body (+14 appendix) | 9 (appendix) | ~8.5k | ~184 w |
| **OURS (now)** | arXiv | **9** | **11** | 0 | **~7.8k** | **406 w** |

**What the strong published anchors do that we don't:**

- **4–5 top-level sections**, settling on **Intro → Results → Discussion → Methods**
  (Methods as end-matter in Nature-family). Background/Related/Conclusion/Ethics are *not*
  separate top-level sections; they fold into Intro/Discussion.
- **Flat subsections, zero sub-subsections, no subsections in Discussion.** Depth that
  exists lives in **Methods/appendix**, never the front matter.
- **Fine-grained points = a handful of bold run-in lead-ins** (Thakkar: "**Goal:** …
  **Architecture:** …"), not dozens of headed units.
- **Abstracts ~150–230 words, one paragraph.** Our 406 is the outlier (matched only by the
  Liang/NEJM arXiv abstract, which the *published* NEJM version replaced with a structured
  abstract).
- **Spare configuration naming:** one symbol/short name for the measure (NHB's `α`), short
  flat legend labels for arms (NHB "Full vocabulary / ADJ / ADV / Verb"; Thakkar
  "Actor / Aggregator / Critic / Formatter"). Nobody ships a `full`/`full-mini` ladder.

**Note on our `\paragraph` units:** in `article` class `\paragraph{}` *is* the bold run-in
style the exemplars endorse — so the style is fine; the problem is **quantity (41)**.
Exemplars use ~4–8. Cut by merging, not by converting.

---

## 3. Diagnosis — where length and fragmentation come from

1. **Redundancy across sections (≈ the whole overage).** ~8 claims × ~5 restatements.
   Collapsing to one home each recovers an estimated **1,500–2,000 words** with zero loss
   of content.
2. **A separate Data section (562 w, 6 run-ins)** that the published shape folds into
   Methods.
3. **A separate Failure Modes section (581 w)** that is really a Results subsection or a
   Discussion paragraph.
4. **Limitations sprawl (833 w, 10 run-ins).** Strong papers keep ~4–5 limitation points in
   the body and push the rest to the supplement (we already have `app:limits`).
5. **Results §5.2 operating-point paragraph** duplicates `app:naive` almost verbatim.
6. **Contribution enumerate (intro)** restates Results bullet-for-bullet.

---

## 4. Abstract — review + proposed rewrite

**Problem:** 406 w, 3 paragraphs; it re-runs H1–H4 with CIs, the naive comparison with CIs,
the variance result, the citation caveat, *and* the boundary. That is a mini-Results, not an
abstract. Drop: inline CIs, the citation caveat (belongs in body), "compressed high"
mechanics, and one of the two boundary restatements.

**Proposed ~200-word abstract** (macros in braces; "Direct" naming applied):

> Large language model systems are increasingly proposed to assist peer review, yet most
> evaluations judge the prose of machine-generated review *text*, not the validity of the
> numeric *score* a system assigns. We validate AIPR, which reads a submitted manuscript and
> emits five 0–100 quality dimensions and a weighted overall score, against the public
> decision outcomes of a major machine learning venue. Across {NminiPrimary} ICLR
> submissions with public decision tiers and reviewer ratings, graded under a frozen
> pipeline with hypotheses pre-registered before any score met any outcome, the overall
> score separates rejected from accepted submissions (AUROC {aurocMiniFull}), rises
> monotonically across tiers, and tracks the mean reviewer rating. The signal is strongest
> where we claim it: the lowest-scoring fifth is rejected far above the base rate, with oral
> papers absent. Two findings locate the system's value. The validity comes mostly from the
> model: a one-paragraph prompt on the same model already discriminates, statistically
> indistinguishably from the full pipeline. What the engineering adds is *reliability* —
> AIPR's score barely moves across repeated runs ({fullRunSD} vs {naiveRunSD} points SD)
> where the bare prompt swings. Intelligence is not the bottleneck; reliability is, and the
> human keeps the decision.

(~205 words. Cuts the citation caveat, all inline CIs except the two headline numbers, and
the duplicate boundary sentence.)

---

## 5. Concrete cut plan

### 5a. Per-section word budget (target ≈ −33% body)

| Section | Now | Target | How |
|---|---:|---:|---|
| Abstract | 406 | ~200 | rewrite above |
| Introduction | 1001 | ~650 | shrink contribution enumerate (it restates Results); 1 boundary line, not 3 |
| Related Work | 704 | ~550 | light trim; keep (fresh cites earn it) |
| Data → **fold into Methods** | 562 | ~300 | merge 6 run-ins → 2 (venue/ground-truth; sampling+cohorts); rest to appendix |
| Methods | 1088 | ~850 | keep the new pipeline-detail; 5 subsec → 3; H-list stays |
| Results | 1492 | ~1050 | cut §5.2 operating-point dup (→ pointer to `app:naive`); 11 run-ins → ~6 |
| Failure Modes → **fold into Results or Discussion** | 581 | ~300 | keep the 2-error-class summary + table pointer; case detail already in `app:cases` |
| Discussion | 1193 | ~750 | drop overlap with Results/Limitations; 6 run-ins → 4 |
| Limitations | 833 | ~450 | 10 run-ins → ~5 in body; move minor ones to `app:limits` (already exists) |
| Conclusion | 364 | ~200 | stop re-deriving every result; 3–4 sentences + Reproducibility line |
| **Body total** | **~7,818** | **~5,200** | |

### 5b. Section consolidation (9 → 6–7)

Recommended arXiv shape: **Intro → Related Work → Data & Methods → Results (incl. failure
modes) → Discussion → Limitations → Conclusion** (7), or fold Limitations into Discussion
for **6**. This mirrors the published anchors while keeping arXiv conventions (named Related
Work / Limitations are fine for arXiv; Nature would fold further).

### 5c. De-duplication rule (the main lever) — one home per claim

| Claim | Home (state fully once) | Elsewhere |
|---|---|---|
| Naive strong / intelligence-not-bottleneck | Results value subsection | 1 line in Discussion; 1 clause in abstract |
| AUROC diff unresolved | Results value subsection | 1 brief line in Discussion; drop from intro+concl |
| Reliability / run-variance | Results value subsection (+1 lesson line in Discussion) | abstract 1 sentence; **stop restating in 9 places** |
| Citation fallback | Discussion (diagnosis) | Results §5.3 = 1 sentence + pointer; Limitations = 1 sentence + pointer; drop from methods/abstract |
| Pre-reg / reproducible | Methods (+ 1 Reproducibility line in Conclusion) | intro 1 line; drop the other 5 |
| "We do not claim …" boundary | Limitations "What we do not claim" | intro 1 line; drop from results/disc/concl |
| Low-end flag (H1) | Results H1 | abstract + conclusion 1 line each |

### 5d. Fragmentation fix

- Flatten/merge `\paragraph` runs: **Limitations 10 → ~5, Data 6 → 2, Discussion 6 → 4,
  Results 11 → ~6, Related 4 → keep**. Target **~20 total** (from 41).
- Keep **0 sub-subsections** (already true). No subsections in Discussion (already true).
- Methods: **5 subsections → 3** (e.g., "Scoring system & pipeline" [merge 4.1+4.2+4.3],
  "Configurations & cost", "Hypotheses & pre-registration").

### 5e. Move to supplement (supp may grow)

Minor limitations (post-rebuttal drift, citation relevance vs. groundedness — already in
`app:limits`), the operating-point mechanics, and any method micro-detail. Net: shorter
body, richer supplement — exactly the requested trade.

---

## 6. Naming — recommendation (research-backed)

**Drop `full` / `full-mini` / `naive`.** "Full" is uninformative and silently overloads
*full pipeline* and *full-size model*; "naive" reads as strawman-stacking precisely where
the "why us" comparison needs to look *fair*. Use **MODEL + METHOD**, method primary, model
in parens — the field-standard answer for a method×tier design (cf. table rows "GPT-4 (CoT)"
/ "GPT-4 (direct)"; "Direct" is the established neutral single-shot baseline label, e.g.
RAG-Gym).

### Scheme 1 — RECOMMENDED

| Arm | New label | = current |
|---|---|---|
| frontier + full pipeline (production) | **AIPR (GPT-5.4)** | `full` / `full_full` |
| cheap model + same pipeline (large-N proxy) | **AIPR (GPT-5.4-mini)** | `full-mini` |
| frontier + one-paragraph prompt (baseline) | **Direct (GPT-5.4)** | `naive` |

- In prose: *"AIPR (GPT-5.4) and Direct (GPT-5.4) discriminate indistinguishably; AIPR
  (GPT-5.4-mini) recovers the relationship at 1/N the cost."*
- Table stub: `Method (Model)`.
- Gloss once at first use: *"Direct (GPT-5.4): the production model prompted once with a
  single-paragraph instruction, no rubric or audit."*
- **Consistency rule:** fix one factor as the primary token, the other in parens, and never
  mix idioms in one table.

**Alternatives** (if the main results table is wide/model-keyed):
- *Scheme 2 (model-primary):* `GPT-5.4 + AIPR` / `GPT-5.4-mini + AIPR` / `GPT-5.4 (direct)`.
- *Scheme 3 (separate Model column):* System ∈ {AIPR, Direct} × Model column — cleanest in a
  wide table; composes with Scheme 1 labels in prose/figures.

**Export-name footnote stays:** released `gradings.csv` keeps `full_full` / `full_mini` /
`naive`; map to the new display names in one footnote (we already footnote `full_full`).

### Naming change is non-trivial (scope note)

`full` / `full-mini` / `naive` / `frontier` appear in **prose, ~138 macros, figure legends
(`CONFIG_LABELS`, `ROC_OVERLAY`, `CONFIG_COLORS` in `figures.py`), table generators, and the
two-CSV contract**. A rename touches `analysis/common.py` (CONFIG_LABELS), `figures.py`,
`tables.py`, every section `.tex`, and requires a figure/table regen. Do it as one
deliberate pass, not piecemeal. The CSV column keys can stay (display-only rename) to avoid
touching the data contract.

---

## 7. Carry-forward: citation camera-ready check (from the prior freshness pass)

Not length-related, but open: ~5 existing **preprint** entries may now be published
(`darcy2024marg`, `lu2024aiscientist`, `cortes2021inconsistency`, `beygelzimer2023arbitrary`,
`kuznetsov2024whatcan`) and `gao2025reviewagents` still has an `and others` author list.
Verify venues per-entry before camera-ready (no venue guessed in the last pass — no
fabrication).

---

## 8. Open decisions for you

1. **Section consolidation depth:** 7 sections (keep named Related/Limitations) or 6 (fold
   Limitations into Discussion)? I recommend **7** for arXiv.
2. **Failure Modes:** fold into Results (as a subsection) or into Discussion? I recommend
   **Results subsection**.
3. **Naming scheme:** Scheme 1 (recommended) confirmed? And keep CSV keys as-is with a
   display-name footnote?
4. **Word target:** ~5,200-word body acceptable, or push harder toward the Nature ~4,500?
5. **Abstract:** approve the ~200-word draft (or adjust which numbers it keeps)?

Once you pick, I'll execute the trim + restructure + rename in one pass and rebuild.

---

### Sources (exemplars + naming)
Thakkar — Nature MI s42256-026-01188-x / arXiv 2504.09737 · Liang "useful feedback" — NEJM
AI AIoa2400196 / arXiv 2310.01783 · Liang "Quantifying LLM usage" — Nature HB
s41562-025-02273-8 · Liang "Monitoring AI-modified" — arXiv 2403.07183 · ReviewerToo — arXiv
2510.08867 · LLM-as-a-Reviewer — arXiv 2605.25415 · naming: T5/BERT size ladders; GPT-4
(CoT)/(direct) parenthetical (CRUXEval 2401.03065); "Direct" baseline (RAG-Gym 2502.13957).
