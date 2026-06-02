"""aiprval — the score-validation paper toolchain.

One entry point for every step of producing the paper, so the whole artifact is
reproducible from a single command and each stage is independently runnable.

    python cli.py <command> [options]

Commands
    synth      generate schema-conformant SYNTHETIC data (formatting only)
    analyze    compute results.json + LaTeX macros + tables + figures
    simulate   pre-data power analysis + estimator self-validation
    test       run the analysis unit-test suite (pytest)
    paper      compile paper/main.tex -> main.pdf (pdflatex + bibtex)
    check      validate data contract, lint undefined macros, verify fig/table refs
    clean      remove generated artifacts (figures, tables, macros, LaTeX aux, pdf)
    freeze     stamp DECISIONS.md with the current git commit + date
    all        synth(if synthetic) -> analyze -> simulate -> paper -> check

Examples
    python cli.py all --dataset synthetic
    python cli.py all --dataset iclr2025 --quick
    python cli.py analyze --dataset iclr2025 && python cli.py paper && python cli.py check
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from common import ANALYSIS_DIR, FIG_DIR, MACRO_DIR, PAPER_DIR, RESULTS_DIR, TAB_DIR

# Standard LaTeX/package control sequences the macro-lint must not flag.
_LATEX_BUILTINS = {
    "documentclass", "usepackage", "begin", "end", "section", "subsection", "subsubsection",
    "paragraph", "label", "ref", "input", "includegraphics", "graphicspath", "cite", "citep",
    "citet", "textbf", "textit", "emph", "texttt", "item", "centering", "footnote", "noindent",
    "textcolor", "fcolorbox", "parbox", "today", "maketitle", "appendix", "bibliography",
    "bibliographystyle", "linewidth", "columnwidth", "textwidth", "toprule", "midrule",
    "bottomrule", "caption", "captionsetup", "TBD", "xspace", "IfFileExists", "providecommand",
    "newcommand", "renewcommand", "description", "itemsep", "title", "author", "date", "mbox",
    "hfill", "vspace", "hspace", "small", "large", "Large", "textsc", "frac", "times", "rho",
    "delta", "alpha", "approx", "ge", "le", "ll", "gg", "leq", "geq", "epsilon", "sim", "subseteq",
    "subset", "in", "times", "quad", "qquad", "color", "and", "Verb", "verb", "url", "href",
    "rule", "par", "newline", "\\", "%", "&", "_", "#", "{", "}", "subfigure", "phantom",
    "multicolumn", "cmidrule", "centering", "raggedright", "footnotesize", "scriptsize",
    "toprule", "fboxsep", "fbox", "S", "P",
    # math-mode builtins (amsmath / base)
    "text", "mathrm", "mathbf", "mathcal", "cdot", "sum", "sqrt", "log", "exp", "min", "max",
    "left", "right", "frac", "times", "leq", "geq", "neq", "pm", "mid", "to", "infty",
    "operatorname", "overline", "hat", "bar", "mathit", "mathbb",
}


def _py() -> str:
    return sys.executable


def cmd_synth(args):
    import synth

    synth.generate()


def cmd_analyze(args):
    import run_all

    sys.argv = ["run_all.py", "--dataset", args.dataset] + (["--no-figures"] if args.no_figures else [])
    run_all.main()


def cmd_simulate(args):
    import simulation

    sys.argv = ["simulation.py"] + (["--quick"] if args.quick else [])
    simulation.main()


def cmd_secondary(args):
    import secondary

    secondary.run()


def cmd_test(args):
    r = subprocess.run(
        [_py(), "-m", "pytest", "-c", "pytest.ini", "tests/"], cwd=ANALYSIS_DIR
    )
    if r.returncode != 0:
        raise SystemExit(r.returncode)


# Unicode chars used in DECISIONS.md -> ASCII, so the verbatim pre-registration
# appendix compiles under plain pdflatex (the verbatim environment does not get
# inputenc's UTF-8 handling).
_PREREG_ASCII = {
    "⊆": " subset of ", "⊇": " superset of ", "≈": "~",
    "→": "->", "—": "--", "–": "-", "’": "'",
    "‘": "'", "“": '"', "”": '"', "…": "...",
    "×": "x", "∈": " in ", "≥": ">=", "≤": "<=", "•": "-",
}


def _render_prereg_verbatim() -> None:
    """Generate ``paper/prereg_verbatim.tex``: the frozen ``DECISIONS.md``
    reproduced verbatim (ASCII-normalized) in a ``verbatim`` block, for the
    appendix ``\\input``. Generated + gitignored, so the appendix always shows the
    committed pre-registration. Written at ``paper/`` root (NOT ``sections/``) so
    the macro-lint — which scans ``sections/*.tex`` — never reads the verbatim
    prose as LaTeX."""
    text = (ANALYSIS_DIR.parent / "DECISIONS.md").read_text(encoding="utf-8")
    for uni, asc in _PREREG_ASCII.items():
        text = text.replace(uni, asc)
    text = text.encode("ascii", "ignore").decode("ascii")  # drop any stray non-ASCII
    body = "\\begin{verbatim}\n" + text.rstrip() + "\n\\end{verbatim}\n"
    (PAPER_DIR / "prereg_verbatim.tex").write_text(body, encoding="utf-8")


def cmd_paper(args):
    """Compile the paper. Returns page count; raises on a hard LaTeX error."""
    if shutil.which("pdflatex") is None:
        raise SystemExit("pdflatex not found on PATH (install MiKTeX/TeX Live).")
    _render_prereg_verbatim()  # frozen DECISIONS.md -> appendix \input (verbatim)
    log = PAPER_DIR / "main.log"

    def run(tool, *a):
        subprocess.run([tool, *a], cwd=PAPER_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    run("pdflatex", "-interaction=nonstopmode", "main.tex")
    if shutil.which("bibtex"):
        run("bibtex", "main")
    run("pdflatex", "-interaction=nonstopmode", "main.tex")
    run("pdflatex", "-interaction=nonstopmode", "main.tex")

    text = log.read_text(errors="ignore") if log.exists() else ""
    errors = [ln for ln in text.splitlines() if ln.startswith("! ")]
    m = re.search(r"Output written on main\.pdf \((\d+) page", text)
    pages = m.group(1) if m else "?"
    if errors:
        print("LaTeX errors:")
        for e in errors[:10]:
            print("  ", e)
        raise SystemExit("paper failed to compile cleanly")
    pdf = PAPER_DIR / "main.pdf"
    if not pdf.exists():
        raise SystemExit("no main.pdf produced")
    print(f"OK: {pdf} ({pdf.stat().st_size} bytes, {pages} pages)")


def _defined_macros() -> set[str]:
    names: set[str] = set()
    for f in ("macros.tex", "macros/results_macros.tex", "macros/sim_macros.tex", "macros/secondary_macros.tex"):
        p = PAPER_DIR / f
        if p.exists():
            names |= set(re.findall(r"\\(?:new|provide)command\{\\([a-zA-Z]+)\}", p.read_text(encoding="utf-8")))
    return names


def cmd_check(args):
    """Static integration checks that need no compile: data contract, undefined
    macros, and that every referenced figure/table file exists."""
    problems: list[str] = []

    # 1. data contract
    try:
        import schema

        d = schema.load_dataset(args.dataset)
        c = d.cohort_counts()
        print(f"[ok] data contract valid; cohorts {c}")
    except Exception as e:
        problems.append(f"data contract: {e}")

    # 2. undefined-macro lint across the paper sources
    defined = _defined_macros() | _LATEX_BUILTINS
    used: set[str] = set()
    srcs = list((PAPER_DIR / "sections").glob("*.tex")) + [PAPER_DIR / "main.tex"]
    for s in srcs:
        used |= set(re.findall(r"\\([a-zA-Z]+)", s.read_text(encoding="utf-8")))
    undefined = sorted(used - defined)
    if undefined:
        problems.append(f"undefined macros referenced: {undefined}")
    else:
        print("[ok] no undefined macros in paper sources")

    # 3. referenced figures / tables exist
    missing = []
    for s in srcs:
        body = s.read_text(encoding="utf-8")
        for fig in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", body):
            stem = fig.split("/")[-1]
            if not (FIG_DIR / f"{stem}.pdf").exists():
                missing.append(f"figure {stem}.pdf")
        for tab in re.findall(r"\\input\{tables/([^}]+)\}", body):
            if not (TAB_DIR / f"{tab}.tex").exists():
                missing.append(f"table {tab}.tex")
    if missing:
        problems.append(f"referenced but missing: {sorted(set(missing))}")
    else:
        print("[ok] all referenced figures/tables exist")

    # 4. placeholder leak: generated macros must carry real values, not [??]
    rm = MACRO_DIR / "results_macros.tex"
    if rm.exists() and ("TBD" in rm.read_text() or "??" in rm.read_text()):
        problems.append("results_macros.tex contains placeholder [??] values")
    else:
        print("[ok] no placeholder values in generated macros")

    if problems:
        print("\nCHECK FAILED:")
        for p in problems:
            print("  -", p)
        raise SystemExit(1)
    print("\nall checks passed.")


def cmd_clean(args):
    patterns = [
        (FIG_DIR, "*.pdf"), (FIG_DIR, "*.png"), (TAB_DIR, "*.tex"),
        (MACRO_DIR, "results_macros.tex"), (MACRO_DIR, "sim_macros.tex"),
        (MACRO_DIR, "secondary_macros.tex"), (MACRO_DIR, "SYNTHETIC.flag"),
        (RESULTS_DIR, "*.json"),
        (PAPER_DIR, "*.aux"), (PAPER_DIR, "*.bbl"), (PAPER_DIR, "*.blg"), (PAPER_DIR, "*.log"),
        (PAPER_DIR, "*.out"), (PAPER_DIR, "*.toc"), (PAPER_DIR, "pass*.log"),
        (PAPER_DIR, "bibtex.log"), (PAPER_DIR, "finalpass.log"), (PAPER_DIR, "main.pdf"),
    ]
    n = 0
    for d, pat in patterns:
        for f in Path(d).glob(pat):
            f.unlink()
            n += 1
    print(f"removed {n} generated files (sources untouched).")


def cmd_freeze(args):
    """Stamp DECISIONS.md with the current git commit + ISO date (idempotent)."""
    dec = ANALYSIS_DIR.parent / "DECISIONS.md"
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ANALYSIS_DIR, text=True).strip()
        date = subprocess.check_output(["git", "log", "-1", "--format=%cI"], cwd=ANALYSIS_DIR, text=True).strip()
    except Exception as e:
        raise SystemExit(f"git not available: {e}")
    txt = dec.read_text(encoding="utf-8")
    if "`__________`" not in txt:
        print("DECISIONS.md already stamped (no blank placeholders found).")
        return
    txt = txt.replace("**Frozen at commit:** `__________`", f"**Frozen at commit:** `{sha}`", 1)
    txt = txt.replace("**Frozen on date:** `__________`", f"**Frozen on date:** `{date}`", 1)
    dec.write_text(txt, encoding="utf-8")
    print(f"stamped DECISIONS.md: commit {sha}, date {date}. Commit this file to complete the freeze.")


def cmd_all(args):
    import schema

    if args.dataset == "synthetic":
        cmd_synth(args)
    cmd_analyze(argparse.Namespace(dataset=args.dataset, no_figures=False))
    cmd_secondary(args)
    if not args.skip_sim:
        cmd_simulate(argparse.Namespace(quick=args.quick))
    cmd_paper(args)
    cmd_check(argparse.Namespace(dataset=args.dataset))
    print("\n== all done ==")
    _ = schema  # keep import for early failure if schema module is broken


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aiprval", description="Score-validation paper toolchain")
    sub = p.add_subparsers(dest="command", required=True)

    def add(name, fn, help_):
        sp = sub.add_parser(name, help=help_)
        sp.set_defaults(func=fn)
        return sp

    add("synth", cmd_synth, "generate synthetic data")
    sp = add("analyze", cmd_analyze, "compute results + macros + tables + figures")
    sp.add_argument("--dataset", default="synthetic")
    sp.add_argument("--no-figures", action="store_true")
    sp = add("simulate", cmd_simulate, "power analysis + estimator validation")
    sp.add_argument("--quick", action="store_true")
    add("secondary", cmd_secondary, "comment-quality comparison (ReviewBench axis + correctness)")
    add("test", cmd_test, "run the pytest suite")
    add("paper", cmd_paper, "compile the LaTeX paper")
    sp = add("check", cmd_check, "validate data + lint macros + verify refs")
    sp.add_argument("--dataset", default="synthetic")
    add("clean", cmd_clean, "remove generated artifacts")
    add("freeze", cmd_freeze, "stamp DECISIONS.md with git commit + date")
    sp = add("all", cmd_all, "synth -> analyze -> simulate -> paper -> check")
    sp.add_argument("--dataset", default="synthetic")
    sp.add_argument("--quick", action="store_true")
    sp.add_argument("--skip-sim", action="store_true")
    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
