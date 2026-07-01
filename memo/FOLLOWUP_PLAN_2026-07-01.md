# Follow-up experiments + writing plan (post-reviewer, 2026-07-01)

**Status: DRAFT for owner sign-off.** Two follow-up gradings + a paper revision
pass, driven by the reviewer notes in
`review-d5a63268…md`. Nothing runs until the forks in §9 are locked.

Both new gradings **deviate from the frozen `prereg-iclr2026-v2` plan** (new
Direct-mini arm; balanced rather than reject-heavy strata) and are therefore
**post-hoc follow-ups, labelled as such** — not pre-registered primary results.
See §4.

---

## 0. How the study is actually produced (recap, so the plan is grounded)

Two repos, a clean producer→consumer split:

- **Producer — `aipr` repo, one CLI group `aipr openreview …`** (`src/aipr/cli/openreview.py`, 2372 lines):
  - `labels` → fetches OpenReview decisions + ratings → `submissions.csv` manifest (+ out-of-pop sidecar). `--pdf-metrics/--with-arxiv/--with-reviews` enrich.
  - `select-cohort` → deterministic seeded draw (`STUDY_SAMPLE_SEED=20260601`), writes `cohort_M.ids` / `cohort_H.ids`, **H ⊆ M by construction**. Splits are frozen: M `{rej150/pos100/oral50}` (n=300), H `{50/30/20}` (n=100).
  - `grade-sample --config <cfg> --runs N [--flex] [--ids …]` → runs the full v6 two-pass pipeline, appends to `gradings.csv` after each DB commit (resumable on `(submission_id,config,run_index)`).
  - `grade-naive --runs N [--flex]` → the one-paragraph baseline. **Currently hardcodes the `full` (frontier gpt-5.4) profile** (`_grade_naive:1996`); writes `config="naive"`, `pipeline_version="naive"`, overall-only.
  - `sync-to-pub` → copies the 4-file allowlist into `score-validation/analysis/data/<dataset>/`. PDFs + findings never cross.
  - Config→model wiring (`resolve_grading_config:1035`): `full`=gpt-5.4 both slots; `full_mini`=gpt-5.4-mini both slots; naive uses the `full` reviewer model.
- **Consumer — `score-validation` repo, `analysis/`** (`aiprval` CLI): reads the two CSVs, `run_all.py` computes every number → `results.json` → `paper/macros/results_macros.tex` → `\input` in the paper. **No number is hand-typed.** Re-pointing `--dataset` reproduces everything. New arms = new rows + (here) small analysis extensions.

Current headline numbers (`results.json`): AIPR-frontier AUROC **0.87** (n=100), AIPR-mini **0.82** (n=300), Direct-frontier **0.80** (n=100). Paired ΔAUROC(AIPR−Direct)=**0.07, CI [−0.01, 0.16], p=0.09** (n=100, criterion not met). Reliability: within-paper SD **0.7 vs 2.8**, Wilcoxon p=0.014 (n=10 variance papers, frontier + Direct-frontier only).

**Cost (verified, `memo/grading_api_cost_and_caching.md`):** full ≈ $0.47/paper, full_mini ≈ $0.15, naive-frontier ≈ $0.16, naive-mini ≈ $0.05. Flex tier (default) = 50% off. Everything below is < $50.

---

## 1. Reviewer notes — triage

**Need new data (this plan's experiments):**

| # | Note | Answered by |
|---|------|-------------|
| Fig p.5 | "include gpt-mini Direct" on the left ROC | **Exp B** (Direct-mini curve) |
| p.1 abstract | 0.87 vs naive p=0.09 — mention the direct comparison; mini = "paying less for inference" | **Exp B** powers this + prose |
| — | "check if we can use mini as proxy for 'our thing is better'" | **Exp B** (powered AIPR-mini vs Direct-mini @300) |
| — | 3rd variant / clean reliability rerun, 4 arms, balanced tiers | **Exp A** (2×2 reliability) |

**Prose / analysis-only edits (no new grading) — folded into §7:**

- p.1 — email `costa@aipr.pub`.
- p.4 — note the baseline is **ICLR-specific** ("grade for ICLR") while AIPR's rubric is field-general and never ICLR-tuned: we handicap ourselves, which *strengthens* the "model already carries the signal" reading.
- p.7 — delete "The strongest threats follow"; sweep for sibling throat-clearing ("we now turn to", "in what follows", etc.).
- p.9 — drop the "instruction footprint" excerpt; instead **estimate the count of check-items in the AIPR prompt**, note they are **field-partitioned** and **benchmarked across many scientific fields**.
- p.20 — **novelty is the lowest subscore AUROC**: offer a hypothesis (novelty is the most reference/prior-art-dependent dimension and ICLR's own rubric down-weights it relative to soundness — plausibly the hardest to judge from the PDF alone without live retrieval, which this frozen config lacked).
- p.20 — length confound: don't just say "weak"; **compare AIPR's score–length rank correlation against human reviewers' rating–length correlation** on the same cohort (we have `reviews.csv`), so "weak" is calibrated against the human benchmark.

---

## 2. Experiment B — Direct-mini on 300 (the reviewer's ROC curve + the powered "we're better" test)

**Do this first: cheapest, highest-value, reuses the frozen cohort M (no new draw).**

**Design.** Grade the one-paragraph Direct baseline with the **mini** model
(gpt-5.4-mini) on **all 300 cohort-M papers**. Because H ⊆ M, this yields the
cohort-H subset (100) for free.

**What it delivers:**
1. **Direct-mini ROC curve** on cohort H (reviewer's Fig p.5 ask) — subset of the 300.
2. **Direct-mini AUROC on n=300**, tight CI (vs the current n=100 Direct at 0.80 [0.70–0.88]).
3. **The powered proxy test:** paired ΔAUROC(**AIPR-mini − Direct-mini**) on the full 300. If its CI excludes 0, we have a properly-powered demonstration that the *pipeline* adds discrimination — using the cheap model as the affordable proxy, exactly the reviewer's "can mini stand in for 'our thing is better'." At n=100 frontier the gap is p=0.09 ns; n=300 roughly triples power.
4. Completes the 2×2 `{AIPR, Direct} × {frontier, mini}` on discrimination.

**Outcome-neutral reading (declare before running):** if the mini ΔAUROC CI still straddles 0, report it plainly as "the pipeline's discrimination edge is not resolved even at n=300; the value is reliability + grounding" — no metric-shopping. If it clears 0, it becomes a supporting (not headline) powered result, clearly flagged as a post-v1 follow-up.

**Producer commands (aipr):**
```
# after the naive_mini path is added (§6):
aipr openreview grade-naive --config full_mini --dataset iclr2026 \
    --ids var/score-validation/iclr2026/cohort_M.ids --runs 1 --flex
aipr openreview sync-to-pub --dataset iclr2026
```
**Cost:** 300 × ~$0.05 × 0.5 (Flex) ≈ **$7–8**.

---

## 3. Experiment A — balanced 2×2 reliability rerun (the "from scratch" follow-up)

**Design.** A fresh, **tier-balanced** cohort graded under **all four arms**
(AIPR-frontier, AIPR-mini, Direct-frontier, Direct-mini), **each paper re-graded
3×** so within-paper SD is estimated from 3 runs rather than 2.

- Recommended: **30 papers, 10 reject / 10 poster / 10 oral** (see §9 for the size fork).
- Source: **fresh draw excluding the existing cohort M/H ids** (independent of the pre-registered cohort), or a balanced subset within M (cheaper — reuses existing AIPR scores). Fork in §9.

**What it delivers:**
- The **reliability 2×2**: median within-paper SD for each of the 4 arms, balanced across tiers → the strongest form of "intelligence is not the bottleneck; reliability is." Replaces/augments the current thin n=10, 2-run, frontier-only variance figure.
- A **balanced discrimination sanity check** (n=30 is under-powered for AUROC — illustrative only; the *powered* discrimination lives in Exp B @300). State the n=30 CI honestly, never headline it.

**Producer commands (aipr):**
```
# balanced id list drawn into cohort_followup.ids (new small draw, §6)
aipr openreview grade-sample  --config full      --ids …/cohort_followup.ids --runs 3 --flex --with-naive
aipr openreview grade-sample  --config full_mini --ids …/cohort_followup.ids --runs 3 --flex --with-naive
aipr openreview sync-to-pub   --dataset iclr2026_followup
```
`--with-naive` shares the ForkSession so each arm's naive rides on the same PDF upload. Lands as a **separate dataset** `iclr2026_followup` (balanced strata ≠ frozen cohort; keeping it separate protects the primary).

**Cost:** 30 × 3 × ($0.47+$0.15+$0.16+$0.05) × 0.5 ≈ **$37** (Flex). 20 papers ≈ $25.

---

## 4. Pre-registration integrity

Both experiments are **post-hoc** (planned after seeing v1 results, at reviewer
request). We do **not** dress them as pre-registration — that would be a
contract lie. Handling:

- Label both in the paper as **"post-review follow-up (not pre-registered)"**, in the same sentence that reports them.
- The frozen v1 numbers stand **unmodified**; Exp B/A are *additional* rows and *additional* figure curves, never a recompute of a v1 macro (same discipline as the Phase-2 `full_full_p2` pillar).
- Keep the pre-registered n=10 variance result reported (it is what was pre-declared); present the fresh balanced 2×2 as a stronger post-hoc confirmation that agrees with it.
- Optional (owner call, §9): a short **`prereg-iclr2026-phase3` addendum** to `DECISIONS.md` stating the two follow-ups' metrics + outcome-neutral rules *before* running them — lighter than a re-freeze, but it timestamps the intent. Recommended for the powered ΔAUROC test (Exp B) so "we ran it until it was significant" can't be alleged.

---

## 5. Analysis code changes (`score-validation/analysis/`)

Adding the **`naive_mini`** config (Direct-mini) touches the invariant sites that
currently special-case the single string `"naive"`:

- `common.py`: add `naive_mini` to `BASELINE_CONFIGS`; `CONFIG_LABELS["naive_mini"]="Direct (GPT-5.4-mini)"`; a `CONFIG_COLORS` entry.
- `schema.py`:
  - inv. #5 (pipeline_version): generalize `config != "naive"` → `~config.isin({"naive","naive_mini"})`; naive_mini carries `pipeline_version="naive"`.
  - inv. #7 (subscores may be blank): extend the naive exemption to `naive_mini`.
  - inv. #9 (nesting): naive nests in H; **naive_mini nests in M** (n=300). Add the assertion.
- `DATA_SCHEMA.md`: document `naive_mini` in the config enum + its nesting rule.
- `run_all.py`: a `_naive_baseline_mini(d, mini)` block mirroring `_naive_baseline` but on cohort M with the AIPR-mini pair → AUROC(Direct-mini)@300, paired ΔAUROC(AIPR-mini − Direct-mini)@300 (+CI+p). New macros `aurocNaiveMini*`, `aurocDiffMiniMini*`.
- `figures.py`: add the 4th curve to `ROC_OVERLAY`/`fig_naive_baseline`; add a Direct-mini series where AIPR-mini already appears (`fig_nested_auroc`). Consider a small 2×2 reliability panel fed by the `iclr2026_followup` dataset.
- Exp A: the fresh dataset loads through the same contract; the 2×2 reliability table is a new `tables.py` entry + a `run_all` block computing per-arm median SD on `iclr2026_followup`.

## 6. Producer code changes (`aipr/src/aipr/cli/openreview.py`)

- `grade-naive` / `_grade_naive`: add a `--config {full,full_mini}` (or `--model-tier`) option so the baseline can resolve the **mini** profile instead of the hardcoded `full` (`:1996`). When mini, `build_naive_grading_row` writes `config="naive_mini"`, `model_name=gpt-5.4-mini`, `pipeline_version="naive"`.
- `STUDY_CONFIGS` / `CONFIG_LABELS` mirror: register `naive_mini`.
- A small balanced-draw helper (or reuse `select-cohort` with a `--balanced --exclude cohort_M.ids --n-per-tier 10` mode) to emit `cohort_followup.ids`.
- Keep the `score-validation/common.py::CONFIG_*` and `aipr` registries in lockstep (the existing lockstep-mirror discipline).

## 7. Paper folding (`score-validation/paper/`) — section by section

- **Abstract** (`sections/nmi_00_abstract.tex` + arXiv `00_abstract`): merge to **two results** — (1) validity: AUROC 0.87 frontier / 0.82 @300, **and vs the Direct one-paragraph prompt p=0.09 ns on 100** (mini framed as "how little we can pay for inference"); (2) reliability: SD 0.7 vs 2.8. Add the powered mini ΔAUROC if Exp B clears 0.
- **Results §res-value** (`05_results.tex`): add Direct-mini to the "model already carries the signal" para; report the powered @300 ΔAUROC; add the p.4 handicap note (ICLR-specific baseline vs field-general AIPR). Update `fig:naive` caption to 4 curves + the 2×2 reliability.
- **Methods** (`04_methods.tex`): add the `naive_mini` arm + the p.9 rewrite (prompt-item count, field-partitioned, multi-field benchmarked) — replacing the instruction-footprint excerpt.
- **Discussion / Limitations** (`06b_discussion.tex`): novelty-lowest-AUROC hypothesis (p.20); length-confound vs human-reviewer correlation (p.20); **sweep and delete throat-clearing** ("The strongest threats follow", siblings) (p.7).
- **Appendix**: 2×2 reliability figure/table (Exp A); the post-hoc follow-up disclosure (§4); power note for the @300 comparison.
- **Macros**: all new numbers flow through `results_macros.tex` — none typed.
- **Both builds** (arXiv `main.tex` + `main_nmi.tex`) share the section files, so edits land once.

## 8. Execution order + gate

1. Lock §9 forks.
2. (opt.) Write + tag `prereg-iclr2026-phase3` addendum.
3. aipr §6 changes → `grade-naive --config full_mini` on cohort M (Exp B) → `sync-to-pub`.
4. score-validation §5 changes → `aiprval analyze && paper && check` → inspect Exp B numbers.
5. Fresh balanced draw → Exp A 4-arm ×3 grading → `sync-to-pub` (`iclr2026_followup`).
6. §5 reliability 2×2 → analyze.
7. §7 paper folding → full `aiprval all` → both PDFs build clean.
8. New Zenodo version once CSVs + paper are final.

**Total grading spend ≈ $45 (Flex).**

## 9. Open decisions — LOCKED 2026-07-01

1. **Exp B model** → **Direct-mini on 300** (pairs with AIPR-mini; powers the "mini proxy" test; ~$8).
2. **Exp A size** → **30 papers (10/10/10) ×3.**
3. **Exp A source** → **fresh draw outside cohort M** — treated as an additional, independent follow-up; **reliability is the object**, discrimination on n=30 illustrative only.
4. **Phase-3 prereg addendum** → **write + tag before running** (`prereg-iclr2026-phase3`, drafted in `DECISIONS.md`). The owner's tag push is the run trigger.
