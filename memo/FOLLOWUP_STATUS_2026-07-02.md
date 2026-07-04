# Follow-up — status + remaining work (pre-compaction handoff, 2026-07-02)

**Read this first after compaction.** Companion to
`memo/FOLLOWUP_PLAN_2026-07-01.md` (the original plan). This file is the
authoritative state: what ran, what it found, what's left, and the exact
commands + git state to resume.

---

## 0. TL;DR

- **Exp B (Direct-mini @300) is DONE.** Result is a clean **powered null**:
  at the mini tier the one-paragraph Direct prompt discriminates *identically*
  to the full AIPR pipeline (ΔAUROC = **0.00**, 95% CI [−0.05, 0.05], **p=0.91**,
  n=300).
- **The FINDING is the contrast, and it goes IN the paper** (owner decision
  2026-07-02, revised from "keep out"): mini = *clear* null; frontier (V1, n=100)
  = *suggestive* gap (Δ=0.07, p=0.09). The pipeline's discrimination benefit
  shows up **only when the model is strong enough to use it** → "intelligence
  (model tier), not prompt elaborateness, is the bottleneck." Points in our
  direction.
- **Most important experiment still to do: Exp A** — the balanced four-arm
  **reliability** rerun (30 papers, 10/10/10, ×3 runs). Reliability is the
  paper's actual value claim; Exp B only settled discrimination.
- **New work defined below (§4): additional model-separating tests** (ordinal /
  multilabel / interaction) — most need **ZERO new grading** (all 4 arms already
  exist on the 100 cohort-H papers).
- All code built this session is **green** (aipr 40+18 study tests; sv 57
  analysis tests) and **uncommitted**. Producer changes on aipr branch
  `fix/send-review-public-consistency`; consumer + synced data on sv `main`.

---

## 1. The Exp B result (numbers, verified)

Paired, same papers, stratified bootstrap. From `results.json`:

| Comparison | AIPR | Direct | ΔAUROC (AIPR−Direct) | 95% CI | p |
|---|---|---|---|---|---|
| **Follow-up B — mini, n=300 (powered)** | 0.82 | 0.82 | **0.003** | [−0.047, 0.052] | **0.91** |
| V1 — frontier, n=100 (underpowered) | 0.87 | 0.80 | 0.070 | [−0.011, 0.155] | 0.09 |

Also: AIPR-frontier 0.87 > AIPR-mini 0.82 (model tier moves discrimination;
prompt elaborateness does not). 300/300 graded, **0 failures**, Flex tier,
~$5–8. Macros emitted: `\aurocNaiveMini{}=0.82`, `\aurocNaiveMiniFull{}`,
`\aurocDiffMiniMini{}=0.00`, `\aurocDiffMiniCI{}=[-0.05,0.05]`,
`\aurocDiffMiniPrel{}=p=0.91`, `\naiveMiniN{}=300`.

**Owner interpretation (verbatim intent, 2026-07-02):** the elaborate pipeline
instructions are "probably not even taken into account by the model"; output
quality is **not bound by prompt quality** (though the prompt may still help
*consistency* → tested by Exp A). The mini↔frontier difference is suggestive and
worth chasing with richer metrics (§4).

---

## 2. Pre-registration (locked, tagged)

`prereg-iclr2026-phase3` tag pushed to the public remote (commit `d75b72e`) —
the run trigger, honored (no grading ran before it). Addendum text is in
`DECISIONS.md` (FROZEN status). Both follow-ups are **post-hoc, labelled as
such**; no v1/Phase-2 number is recomputed.

> Caveat recorded: that commit also swept in 4 already-staged `nmi_*.tex`
> deletions from the prior NMI session (6 files, not 2). Legitimate deletions,
> broader than the message; NOT re-tagged (a public prereg anchor must not be
> force-moved).

---

## 3. What was DONE this session

### Producer (aipr repo, branch `fix/send-review-public-consistency`)
`src/aipr/cli/openreview.py` + `tests/test_cli/test_openreview_study_helpers.py`
(uncommitted):
- `NAIVE_CONFIG_BY_TIER` map (all 4 STUDY_CONFIGS → naive/naive_mini).
- `grade-naive --config {full,full_mini}` → writes `naive`/`naive_mini` rows
  (model = that tier's reviewer). **This ran Exp B.**
- `build_naive_grading_row(config=...)` parameterized.
- `grade-sample --with-naive` derives `naive_mini` for the mini arm (Exp A 4-arm).
- `select-followup-cohort` command + `draw_balanced_followup()` +
  `FOLLOWUP_BALANCED_SPLIT={reject:10,poster:10,oral:10}` (Exp A balanced draw,
  disjoint from cohort M/H, distinct seed namespace). **Built, not yet run.**
- 6 new tests (naive_mini row, tier map exhaustiveness, 3 balanced-draw tests).
  Study suites green: 40 helper + 18 flow.

### Consumer (score-validation repo, branch `main`, uncommitted)
- `analysis/common.py` — `naive_mini` in BASELINE_CONFIGS, CONFIG_LABELS
  ("Direct (GPT-5.4-mini)"), CONFIG_COLORS.
- `analysis/schema.py` — invariants #5/#7/#9 generalized to BASELINE_CONFIGS;
  `naive_mini ⊆ cohort M` nesting asserted.
- `analysis/DATA_SCHEMA.md` — documented `naive_mini`.
- `analysis/run_all.py` — `_naive_baseline_mini()` (powered AIPR-mini vs
  Direct-mini on cohort M) + its macros.
- `analysis/figures.py` — 4th ROC curve (`naive_mini`) in ROC_OVERLAY +
  `fig_naive_baseline` (static paper figure).
- `analysis/cli.py` — macro-lint whitelist for `\ifnmibuild` (pre-existing NMI
  lint failure, fixed on entry).
- `analysis/data/iclr2026/{gradings,submissions,submissions_out_of_population}.csv`
  — **synced from aipr** (`sync-to-pub`); gradings.csv now has 300 `naive_mini`
  rows. 57 analysis tests green.

### Reverted (was overcomplication)
- `analysis/synth.py` — the synthetic `naive_mini` generator was **reverted**
  (`git checkout`). It dragged in 2025-arm venue-gating scaffolding for a phantom
  cohort (only 2026 exists). Real `iclr2026` data is the verifier. The
  previously-"failing" `test_synthetic_iclr2025_arm_and_vocabulary` was correct;
  the synth edit was wrong. **Lesson: don't scaffold the synthetic generator for
  a config the real single-year dataset already carries.**

---

## 4. What's LEFT (in priority order)

### 4.1 Exp A — balanced four-arm reliability rerun  ★ MOST IMPORTANT
Reliability is the paper's value claim; Exp B only settled discrimination.
- Producer code is BUILT (`select-followup-cohort`, `grade-sample --with-naive`
  mini→naive_mini). Not yet run.
- Steps:
  1. `select-followup-cohort` → `cohort_followup.ids` (30, disjoint from M/H).
  2. Grade 4 arms ×3 runs on a **new dataset `iclr2026_followup`**:
     `grade-sample --config full --with-naive --runs 3` and
     `grade-sample --config full_mini --with-naive --runs 3` (the `--with-naive`
     rides Direct on the same PDF; full→naive, full_mini→naive_mini).
  3. `sync-to-pub --dataset iclr2026_followup`.
  4. **Consumer reliability 2×2 analysis is NOT built yet** — need a per-arm
     within-paper-SD block + table/figure on the followup dataset (median SD for
     each of {AIPR,Direct}×{frontier,mini}, balanced across tiers; paired
     Wilcoxon per tier). Mirror `run_variance` / the existing reliability block.
  - Cost ≈ $37 Flex. ~15–20 min/arm at Flex latency (~12s/grade observed).
  - Outcome-neutral rule (addendum): reported ALONGSIDE the pre-registered n=10
    variance result, not replacing it.

### 4.2 Additional model-separating tests (owner-requested 2026-07-02) — mostly NO new grading
Binary reject/accept AUROC may be too coarse to reveal the pipeline's or the
model's edge. All four arms already cover the SAME 100 cohort-H papers (verified),
so these are **re-analyses**:

- **(a) Model×pipeline interaction (difference-in-differences) — the rigorous
  "contrast."** On cohort H (n=100): `DiD = [AUROC(full) − AUROC(naive)] −
  [AUROC(full_mini) − AUROC(naive_mini)]`, paired stratified bootstrap CI.
  Point ≈ 0.07 − 0.00 = 0.07. Tests directly: *does the pipeline help the
  frontier model more than the mini model?* This is "clear-null vs suggestive"
  made into one number with a CI. **No new grading.**
- **(b) Ordinal / multilabel discrimination.** Replace binary AUROC with an
  ordinal metric that uses all three tiers: Somers' D / Kendall τ-b(score,
  tier_rank), or the mean of adjacent-boundary AUROCs (reject|poster,
  poster|oral). `stats.adjacent_boundary_aurocs` already exists. Paired
  pipeline-vs-prompt on this, per model tier — the poster|oral boundary is where
  fine discrimination lives and where a pipeline/model edge could surface that
  binary reject/accept saturates away. **No new grading.**
- **(c) Continuous-outcome agreement.** Paired Spearman ρ(AIPR, mean_rating) vs
  ρ(Direct, mean_rating), per tier. Higher resolution than binary. **No new
  grading.**
- **(d) Within-accept fine ranking.** poster-vs-oral AUROC, paired
  pipeline-vs-prompt — does the pipeline help rank the TOP (where review itself
  is weakest)? **No new grading.**
- **(e) OPTIONAL, needs grading — power the FRONTIER comparison.** Direct-frontier
  is only n=100. To match Exp B's power at the frontier: Direct-frontier @300
  (`grade-naive --config full` on cohort_M.ids, ~$16) AND AIPR-frontier @300
  (`grade-sample --config full` on cohort M, ~$140). Only if (a)–(d) don't
  resolve the interaction. Expensive; likely unnecessary.

Recommendation: do (a)–(d) first (cheap, fast, already-collected data); they may
be enough to publish the model×pipeline contrast rigorously.

### 4.3 Paper folding (some depends on the above)
Reviewer notes from `review-…278…md`, mapped in FOLLOWUP_PLAN §7. Data-dependent:
- Fold Exp B via **the contrast** (§1): abstract + Results value section. Frame:
  discrimination is model-bound not prompt-bound; the pipeline's value is
  reliability (+ grounding). Include Direct-mini in the ROC figure (4 curves,
  done in `figures.py`).
- **Macros must be always-emitted with `--` placeholders** when a config is
  absent (mirror the phase2 pattern) so `check --dataset synthetic` stays green
  WITHOUT re-adding synth scaffolding. Currently `naive_mini` macros emit only
  inside `if nbm:` — change to always-emit before the paper references them.
Prose-only (no data): p.1 email→costa@aipr.pub; p.4 ICLR-specific-baseline
handicap note; p.7 delete "The strongest threats follow" + sweep siblings; p.9
prompt-item-count rewrite (drop the instruction-footprint excerpt); p.20
novelty-lowest-AUROC hypothesis; p.20 length-confound vs human-reviewer corr.

### 4.4 Web companion
Owner said YES to matching the paper (4 curves). `run_all._points`
`discrimination.roc` still emits only {full, mini, naive} — add `naive_mini`.
Single-source-of-truth discipline (paper + page never drift).

### 4.5 Commits / hygiene
- Commit the **aipr** producer change (branch `fix/send-review-public-consistency`,
  2 files, self-contained, green) — offered, owner hasn't said go.
- score-validation `main` is tangled: this session's analysis changes + synced
  data CSVs + the big **pre-existing NMI-translation session** (paper sections,
  refs, README, deleted nmi_*.tex) all uncommitted together. Untangle into
  coherent commits (analysis/naive_mini; data refresh; NMI session).
- **Open decision:** the released `gradings.csv` now carries 300 `naive_mini`
  rows. Committing/pushing publishes the Exp B data. Owner wanted the *result*
  in the paper but confirm the raw naive_mini rows should go public in the OSS
  data release (they're just scores + ids, CC-BY-compatible like the rest).

---

## 5. Locked decisions
- Exp B model: Direct-mini @300 (done). Exp A: 30 papers 10/10/10 ×3, fresh draw
  **outside** cohort M/H, reliability is the object. Phase-3 addendum tagged
  before running (done).
- Exp B framing: **include in paper via the mini-vs-frontier contrast** (revised
  2026-07-02). Web ROC: 4 curves.

## 6. Open decisions
- Exp A: run now, or after the §4.2 re-analyses? (Re-analyses are free and may
  reshape how Exp A's reliability is framed.)
- §4.2(e) frontier @300: run or not (expensive; probably skip).
- Publish naive_mini raw rows in the OSS data release? (§4.5)
- Commit sequencing across the two repos (§4.5).

## 7. Resume commands (exact)
```bash
# --- Exp A (from aipr repo root) ---
V=ICLR.cc/2026/Conference ; M=var/score-validation/iclr2026
aipr openreview select-followup-cohort --venue $V \
    --manifest $M/submissions.csv --exclude $M/cohort_M.ids
aipr openreview grade-sample --venue $V --manifest $M/submissions.csv \
    --ids $M/cohort_followup.ids --config full      --with-naive --runs 3 --flex \
    --out var/score-validation/iclr2026_followup/gradings.csv
aipr openreview grade-sample --venue $V --manifest $M/submissions.csv \
    --ids $M/cohort_followup.ids --config full_mini --with-naive --runs 3 --flex \
    --out var/score-validation/iclr2026_followup/gradings.csv
# (labels/submissions.csv for the followup dataset: copy the 30 rows, or re-run
#  `labels --ids cohort_followup.ids` — submissions.csv is the same manifest)
aipr openreview sync-to-pub --dataset iclr2026_followup

# --- analysis (from score-validation/analysis) ---
./.venv/Scripts/python.exe cli.py analyze --dataset iclr2026   # Exp B already folds in here
./.venv/Scripts/python.exe cli.py check   --dataset iclr2026
# Exp A needs a NEW reliability-2x2 block in run_all.py first (§4.1.4)

# --- tests ---
# aipr:  aipr test tests/test_cli/test_openreview_study_helpers.py --study --no-db   (40)
#        aipr test tests/test_cli/test_openreview_study.py --study                   (18)
# sv:    ./.venv/Scripts/python.exe -m pytest -c pytest.ini tests/ -p no:cacheprovider  (57)
```

## 8. Git state (as of 2026-07-02)
- **aipr**: branch `fix/send-review-public-consistency`. Modified (uncommitted):
  `src/aipr/cli/openreview.py`, `tests/test_cli/test_openreview_study_helpers.py`.
- **score-validation**: branch `main`. Tag `prereg-iclr2026-phase3` pushed.
  Uncommitted: analysis/{common,schema,run_all,figures,cli}.py, DATA_SCHEMA.md,
  data/iclr2026/*.csv (synced, +300 naive_mini rows) — PLUS the pre-existing NMI
  session (paper/**, refs.bib, README, CITATION.cff, deleted nmi_*.tex) and
  untracked memo/*, paper/submission/, etc.

## 9. Gotchas learned (don't rediscover)
- **Study CLI runs host-side in the native `.venv`**, NOT Docker: `openreview-py`
  is an optional `[study]` extra excluded from the served image. Install with
  **`uv sync --all-extras`** (this is a uv venv, no pip). `uv sync --extra study`
  ALONE strips dev/extraction/monitoring — always `--all-extras`.
- **Background `aipr test` / pytest output buffers** — a run can report exit 0
  while a test actually FAILED. For a definitive result run pytest directly with
  `-p no:cacheprovider` and read the summary line, don't trust the notification's
  exit code alone.
- `aipr test` takes ONE path arg and defaults to a `-m 'not … study'` marker; run
  study tests with `--study`. `-k` on the wrapper matched unexpectedly — prefer a
  path.
- Released `gradings.csv` uses config `full_full` (remapped to `full` on load);
  raw grep for `full` finds 0 — use `schema.load_dataset`.
- `\ifnmibuild` must stay in the `cli.py` macro-lint whitelist (NMI build toggle).
