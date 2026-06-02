# Vendored fork — ReviewBench

Upstream: `https://github.com/researchbites/reviewbench` (MIT License, retained).
Vendored snapshot taken 2026-06-01 for use as a **secondary** comment-quality
comparison in the score-validation study. The inner `.git` was removed so this is
a flat vendored copy, not a submodule.

**Why it is here (and the guardrails):** we use it only as a *secondary*
"on the standard benchmark" comparison, never as primary evidence or
infrastructure. Specifically:

1. **Self-hosted, not their live DB.** Upstream reads a hosted Postgres
   (`34.28.98.243`). Do not depend on it for any published number — snapshot to a
   local store first.
2. **Judge must be swapped/augmented.** Upstream judges every assessment with
   Gemini 3 Pro (temp 0). That is circular (a competitor-chosen LLM judging an
   LLM) — re-run with a non-Gemini judge and human spot-checks; report robustness.
3. **Their metrics measure form + intent, not correctness.** Confirmed in
   `src/prompts/claim_mapping.md`: *"Be objective: assess what the reviewer is
   saying, not whether they are correct."* and in `src/processor/metrics.py`
   (`anchored_rate` etc. are presence rates). We extend with a correctness axis —
   see `ADAPTER_AIPR.md` and `../../analysis/secondary.py`.

**Local modifications:** none to `src/` yet (kept pristine for diffing against
upstream). All AIPR integration + the correctness-axis metrics live outside this
folder in `analysis/secondary.py`, with the exact upstream patch documented in
`ADAPTER_AIPR.md`.
