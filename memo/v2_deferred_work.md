# Deferred to v2 — "new analysis" work from the 2026-06-10 AIPR self-review

The AIPR review of this manuscript (`review-pdf-29f9cd7f`) raised several
weaknesses whose remedy is **new analysis or new data collection**, not prose.
Per the v1 decision (no new analysis spend, no live external-API probing, single
ICLR-2026 cohort), these are recorded here and deliberately **not** built for v1.
v1 instead rebuts each in-text (the result already stands without them).

Status legend: ⬜ not started · 🔶 seam left in code/paper · ✅ landed elsewhere.

## 1. V1 (pipeline vs. naive prompt) — power & interpretation
- ⬜ Prospective power analysis for ΔAUROC on cohort H (currently only H1–H4 are
  powered). Either enlarge cohort H or reframe V1 as **exploratory** rather than
  the "primary value" test.
- ⬜ Add a minimum effect of practical interest / equivalence-style (TOST)
  analysis so the unresolved gap has an operational interpretation.
- ⬜ One **intermediate baseline** (rubric-only single-pass, or a lightly
  optimized few-shot prompt) to localize where the pipeline's gain comes from —
  current design only contrasts bare-prompt vs. full pipeline.

*v1 stance:* the headline is the **validation** (AUROC ~0.87, monotone tiers,
low-band triage), which holds whichever grader produces the signal; V1 asks
*where* the signal comes from, not *whether* it exists. See §5 reframe.

## 2. External validity
- 🔶 Second-venue / second-field replication (validates against continuous
  reviewer rating since venues publishing rejects are rare). Reported separately.
- 🔶 ICLR-2025 within-family **contaminated contrast** (year-to-year stability;
  if the relationship is no stronger pre-cutoff, memorization isn't driving it).
  `run_all.py` replication section self-activates when 2025 rows are present;
  `figS_replication` already exists (commented in appendix). Paper seam = closed
  Results subsection + Methods stub + display slot.
- ⬜ Prospective cohort (grade a future venue before decisions release) — the only
  check that closes leakage logically.

## 3. Ground-truth quality
- ⬜ Per-review reliability ceiling using individual reviewer scores; alternate
  rating aggregations (median / trimmed mean). The released two-CSV carries only
  the mean rating — needs the per-review export.
- ⬜ AI-contaminated-ground-truth sensitivity: bound the H4 ceiling by review
  date, reviewer-text markers, or a manually checked subsample.

## 4. Citation subscore — corrected re-grade
- ✅ **Pipeline fix landed in `aipr`** (branch `fix/v6-audit-drop-citation`):
  `run_audit_phase` now tracks whether the audit grounded (≥1 OpenAlex search
  returning records); `_update_citation_score` pins 100 **only** when grounded,
  else keeps the pass-1 heuristic — no more phantom-100 on an empty/failed audit.
- ⬜ **Re-grade** the citation channel on the search-backed config and report
  citation AUROC before/after, then fold the corrected dimension back into the
  validated overall (currently citation is isolated; headline is unchanged with
  it dropped: AUROC `\aurocDropCitationFull` vs `\aurocFull`).

## 5. Subscore independence (halo)
- ⬜ Independent per-dimension elicitation (separate isolated judgments aggregated
  after the fact) vs. the current single holistic pass, to decorrelate the
  verdict from the parts; plus an order-perturbation probe to measure anchoring
  directly. Discussed qualitatively in v1 (§ Discussion, "Do the subscores
  reflect independent assessment?").

---
*Not deferred (shipped in v1 as prose/clean-fix):* central-question reframe in §5
(validation is the headline; V1 is secondary); bibliography editorial-note removal;
W4 weight-provenance sentence (empirical internal validation, no ICLR data any
year/paper) in §4.1.
