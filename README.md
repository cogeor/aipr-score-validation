# Validating an Automated Paper-Scoring System Against Peer-Review Outcomes

Reproducible analysis and manuscript for a pre-registered study that validates
an automated LLM paper-scoring system (AIPR) against the public peer-review
outcomes of a major machine-learning venue (ICLR on OpenReview): the decision
tier of each submission (reject / poster / oral) and its mean
reviewer rating.

Every number, figure, and table in the paper is generated from the data by a
single command. Nothing is hand-typed.

## What is open here, and what is not

| | |
|---|---|
| **Open (this repository)** | the analysis code, the LaTeX manuscript, the pre-registration ([`DECISIONS.md`](DECISIONS.md)), the data contract ([`analysis/DATA_SCHEMA.md`](analysis/DATA_SCHEMA.md)), and — when a real run lands — the de-identified scored tables. |
| **Proprietary (not in this repository)** | the AIPR grading method: its rubric, prompts, model configuration, and the OpenReview ingestion + grading pipeline that produces the scores. The scoring function is treated here as a fixed black box and is audited through its outputs, not re-implemented. |

The two boundaries meet at exactly two CSV files (`submissions.csv` +
`gradings.csv`). Any pipeline that emits files conforming to
[`analysis/DATA_SCHEMA.md`](analysis/DATA_SCHEMA.md) reproduces the study; this
repository contains no code that calls AIPR.

## Layout

```
DECISIONS.md                 pre-registration / commitment device (frozen before unblinding)
README.md  LICENSE
build.ps1                    one-shot wrapper (creates the venv, runs the full build)
analysis/
  DATA_SCHEMA.md             the two-CSV data contract — the plug-in point
  cli.py                     `aiprval` toolchain: synth | analyze | simulate | paper | check | all
  synth.py                   schema-conformant SYNTHETIC data (formatting verification only)
  schema.py                  load + validate a dataset
  stats.py figures.py tables.py run_all.py   estimators, figures, tables, macro emission
  simulation.py              pre-data power analysis + estimator self-validation
  secondary.py               secondary comment-quality comparison (ReviewBench axis)
  requirements.txt           pinned environment
  data/<name>/               datasets (see analysis/data/README.md)
paper/
  main.tex  macros.tex  refs.bib  sections/*.tex     manuscript sources
  figures/ tables/ macros/   generated artifacts (gitignored)
external/
  reviewbench-results/       snapshot of the secondary-benchmark results + adapter notes
```

## Quickstart (synthetic, no real data needed)

The synthetic path verifies the entire toolchain end to end. Every output is
watermarked `SYNTHETIC` and is not a result.

```powershell
# Windows / PowerShell — creates analysis/.venv on first run, then builds
./build.ps1
```

```bash
# any platform, manually
cd analysis
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # POSIX: .venv/bin/pip
.venv/Scripts/python cli.py all --dataset synthetic
```

`cli.py all` runs: `synth` → `analyze` → `simulate` → `paper` → `check`. The
`check` stage is the integrity gate: it validates the data contract, lints for
undefined LaTeX macros, verifies every referenced figure/table exists, and
fails if any generated macro still holds a placeholder. Compiling the paper
requires a TeX distribution (`pdflatex` + `bibtex`) on `PATH`.

Individual stages:

```bash
python cli.py analyze --dataset synthetic   # results.json + macros + tables + figures
python cli.py paper                          # compile paper/main.tex -> main.pdf
python cli.py check  --dataset synthetic     # integrity checks (no compile)
python cli.py test                           # analysis unit tests
```

## Producing the real data

The real `submissions.csv` / `gradings.csv` are produced by the AIPR OpenReview
exporter (proprietary, not in this repository). The export is two steps,
deliberately split so the cheap, robust labels and the expensive, fallible
grades regenerate independently:

1. **labels** — fetch each submission's decision tier (from its OpenReview venue
   tag) and reviewer ratings; no grading. Produces `submissions.csv`.
2. **grade-sample** — grade only the manifest rows under a chosen config
   (`scan` / `full_mini` / `full`, plus the `naive` baseline), resumable and
   committed per grade. Produces `gradings.csv`.

The exporter must emit files conforming to
[`analysis/DATA_SCHEMA.md`](analysis/DATA_SCHEMA.md); the schema is the contract
between the (closed) producer and this (open) consumer, and it is validated on
load. See [`analysis/data/README.md`](analysis/data/README.md) for the drop-in
procedure.

## The turnkey loop

```bash
# 1. produce the export with the AIPR exporter (closed pipeline)
# 2. drop the CSVs in place
cp submissions.csv gradings.csv  analysis/data/iclr2026/
# 3. regenerate everything
python cli.py all --dataset iclr2026
```

Adding more data later (more submissions, a re-grade after a failure, an extra
venue) is the same loop: more rows in the same CSVs, then re-run. The
pre-registered hypotheses in [`DECISIONS.md`](DECISIONS.md) are what is frozen;
the data volume and the supplementary analyses are expected to grow without
changing the core claims.

## Reproducibility and integrity

- Every figure, table, and reported number is generated by `run_all.py`; none
  is transcribed by hand.
- Analysis is deterministic under a fixed seed; the environment is pinned in
  `analysis/requirements.txt`.
- Estimator validity (bootstrap coverage, trend-test Type-I error) is
  established a priori in `simulation.py`, independent of the data.
- The pre-registration ([`DECISIONS.md`](DECISIONS.md)) fixes the primary
  metric, the low-score threshold, and the hypotheses before any score is joined
  to any outcome, and is reproduced verbatim in the paper's appendix.

## License

Code is released under the MIT License ([`LICENSE`](LICENSE)). The manuscript
text and figures are intended for open release under CC BY 4.0; confirm the
final manuscript license before posting.

The vendored ReviewBench results under `external/reviewbench-results/` derive
from an MIT-licensed upstream project; see that directory's `FORK_NOTICE.md`.
