# Running AIPR through ReviewBench (the real-data path)

The upstream pipeline benchmarks four hardcoded sources. To add AIPR as a fifth
source and run the comparison on a self-hosted snapshot, apply the diffs below.
Until the real grading run, `../../analysis/secondary.py` reproduces the
comparison on synthetic comment data so the figure/table/prose are verified.

## 1. Register AIPR as a source

`src/processor/types.py`:
```python
SOURCES = ["human", "r3", "gemini-3-pro", "gpt-5.2", "aipr"]
SOURCE_LABELS = ["Human", "R3", "Gemini 3 Pro", "GPT-5.2", "AIPR"]
# add human-aipr (and other) pairs to SOURCE_PAIRS as needed
```

`src/db/schema.py` — extend BOTH CHECK constraints (they are hardcoded):
```sql
-- comments.source and assessments.source:
source TEXT NOT NULL CHECK (source IN ('human','r3','gemini-3-pro','gpt-5.2','aipr'))
```
(Run a one-off `ALTER TABLE ... DROP CONSTRAINT ... ADD CONSTRAINT ...` on the
self-hosted snapshot, or recreate from `migrate()`.)

## 2. Ingest AIPR comments

AIPR's in-depth review yields weaknesses + OpenAlex-backed missing-citation
findings (our `findings.jsonl`). Insert each as a `comments` row
(`source='aipr'`, `content=<weakness or citation recommendation text>`,
`paper_id=<shared id>`). The existing `assess_comments` step then scores them
with the same prompts as every other source — apples to apples on their metrics.
No new generator is required if AIPR reviews are pre-computed; if you want
on-the-fly generation, clone `src/generators/control_gpt.py` to
`control_aipr.py`.

## 3. Swap the judge (required, non-circular)

Assessment model is set in the generators/processor (Gemini 3 Pro, temp 0). For a
defensible comparison, run assessment with a **non-Gemini** judge and a human
spot-check on a sample; report both. Never let the judge be the same model family
as a source under test.

## 4. Add the correctness axis (what upstream omits)

Upstream metrics are presence/intent rates only. Our extension
(`../../analysis/secondary.py`) adds, per source:
- **citation groundedness** — % of recommended references that resolve to a real,
  relevant record (AIPR: ~100% by construction via the OpenAlex audit);
- **anchor fidelity** — % of comment anchors that appear verbatim in the paper
  (AIPR quotes are verifier-checked);
- **comment correctness (spot-checked)** — of `is_consequential` comments, the %
  that are *actually correct* — the check upstream explicitly skips
  (`claim_mapping.md`: "assess what the reviewer is saying, not whether they are
  correct").

These are computed from AIPR's own findings + the paper text + an external index,
independent of the upstream Gemini judge.

## Provenance to verify before publishing a shared-cohort claim
- `papers.decision` is only `accepted/rejected/unknown` (no tiers/ratings) — fine
  for our binary cross-check but not a substitute for the OpenReview pull that
  the score paper uses.
- Confirm the ICLR-2025 set uses **submitted** PDFs and the accept/reject split.
