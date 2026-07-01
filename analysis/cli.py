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
import textwrap
from pathlib import Path

from common import ANALYSIS_DIR, FIG_DIR, MACRO_DIR, PAPER_DIR, RESULTS_DIR, TAB_DIR, VENUE_TIERS

# Standard LaTeX/package control sequences the macro-lint must not flag.
_LATEX_BUILTINS = {
    "documentclass", "usepackage", "begin", "end", "section", "subsection", "subsubsection",
    "paragraph", "label", "ref", "input", "includegraphics", "graphicspath", "cite", "citep",
    "citet", "citealp", "itshape", "textbf", "textit", "emph", "texttt", "item", "centering", "footnote", "noindent",
    "textcolor", "fcolorbox", "parbox", "today", "maketitle", "appendix", "bibliography",
    "bibliographystyle", "linewidth", "columnwidth", "textwidth", "toprule", "midrule",
    "bottomrule", "caption", "captionsetup", "TBD", "xspace", "IfFileExists", "providecommand",
    "newcommand", "renewcommand", "description", "itemsep", "title", "author", "date", "mbox",
    "hfill", "vspace", "hspace", "smallskip", "medskip", "bigskip", "ldots", "multicolumn", "small", "large", "Large", "footnotesize", "textsc", "frac", "times", "rho",
    "delta", "Delta", "alpha", "approx", "ge", "le", "ll", "gg", "leq", "geq", "epsilon", "sim", "subseteq",
    "subset", "in", "times", "quad", "qquad", "color", "and", "Verb", "verb", "url", "href",
    "rule", "par", "newline", "\\", "%", "&", "_", "#", "{", "}", "subfigure", "phantom",
    "multicolumn", "cmidrule", "centering", "raggedright", "footnotesize", "scriptsize",
    "toprule", "fboxsep", "fbox", "S", "P",
    # math-mode builtins (amsmath / base)
    "text", "mathrm", "mathbf", "mathcal", "cdot", "sum", "sqrt", "log", "exp", "min", "max",
    "left", "right", "frac", "times", "leq", "geq", "neq", "pm", "mid", "to", "infty",
    "operatorname", "overline", "hat", "bar", "mathit", "mathbb",
    # TeX conditional toggle for the anonymized/named exemplar variant (main.tex).
    "newif", "ifanonymous", "anonymoustrue", "anonymousfalse", "else", "fi",
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


_PREREG_WRAP = 100  # columns; long markdown lines soft-wrap to fit the page at \footnotesize

_PREREG_TAG = "prereg-iclr2026-v2"  # authoritative public freeze anchor (DECISIONS.md §1)


def _render_prereg_verbatim() -> None:
    """Generate ``paper/prereg_verbatim.tex``: ``DECISIONS.md`` as committed at
    the public freeze tag ``prereg-iclr2026-v2`` — NOT the working tree —
    reproduced (ASCII-normalized) in a ``\\footnotesize`` ``verbatim`` block, for
    the appendix ``\\input``. Sourcing the text from the tag makes the appendix's
    "verbatim from the frozen pre-registration" claim true by construction:
    post-freeze bookkeeping edits to the working-tree file can never leak into
    the printed block. The approver's personal e-mail address is redacted; the
    redaction is disclosed in the appendix intro. Written at ``paper/`` root
    (NOT ``sections/``) so the macro-lint — which scans ``sections/*.tex`` —
    never reads the verbatim prose as LaTeX. Markdown paragraphs that exceed
    ``_PREREG_WRAP`` columns are soft-wrapped at word boundaries (a 294-char
    line otherwise overran the margin by 250pt); content and word order are
    otherwise unchanged, only the display line breaks, so the block stays
    faithful to the frozen plan."""
    proc = subprocess.run(
        ["git", "show", f"{_PREREG_TAG}:DECISIONS.md"],
        cwd=ANALYSIS_DIR.parent, capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        raise SystemExit(
            f"git show {_PREREG_TAG}:DECISIONS.md failed — the freeze tag must be"
            f" present locally to build the paper: {proc.stderr.strip()}"
        )
    text = proc.stdout.replace("(costa.georgantas@gmail.com)", "(e-mail redacted)")
    for uni, asc in _PREREG_ASCII.items():
        text = text.replace(uni, asc)
    text = text.encode("ascii", "ignore").decode("ascii")  # drop any stray non-ASCII
    lines: list[str] = []
    for line in text.rstrip().splitlines():
        if len(line) <= _PREREG_WRAP:
            lines.append(line)
            continue
        indent = line[: len(line) - len(line.lstrip())]  # keep list/quote hangs
        lines.extend(textwrap.wrap(
            line, width=_PREREG_WRAP, break_long_words=False,
            break_on_hyphens=False, subsequent_indent=indent) or [""])
    body = ("\\begingroup\\footnotesize\n\\begin{verbatim}\n"
            + "\n".join(lines) + "\n\\end{verbatim}\n\\endgroup\n")
    (PAPER_DIR / "prereg_verbatim.tex").write_text(body, encoding="utf-8")


def cmd_paper(args):
    """Compile the paper. Returns page count; raises on a hard LaTeX error.

    ``--anon`` builds the editor-facing blind variant: it drops
    ``paper/ANONYMOUS.flag`` (which main.tex picks up to swap the three named
    cohort exemplars for outcome-only descriptions), compiles, and copies the
    result to ``main-anon.pdf``. The flag is always removed afterwards so the
    default ``main.pdf`` build is never silently left in anonymized mode.

    ``--nmi`` builds the condensed Nature Machine Intelligence variant
    (``main_nmi.tex`` -> ``main_nmi.pdf``) and returns; it shares the generated
    macros/figures/tables and the appendix-as-SI with the canonical build."""
    if shutil.which("pdflatex") is None:
        raise SystemExit("pdflatex not found on PATH (install MiKTeX/TeX Live).")
    _render_prereg_verbatim()  # frozen DECISIONS.md -> appendix \input (verbatim)
    pdf = PAPER_DIR / "main.pdf"
    flag = PAPER_DIR / "ANONYMOUS.flag"

    def run(tool, *a):
        subprocess.run([tool, *a], cwd=PAPER_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _compile(stem: str, label: str) -> str:
        """One full latexmk-style pass (pdflatex, bibtex, pdflatex x2) on
        ``{stem}.tex``. Returns the page count; raises on a hard LaTeX error or a
        missing PDF."""
        tex = f"{stem}.tex"
        stem_log = PAPER_DIR / f"{stem}.log"
        stem_pdf = PAPER_DIR / f"{stem}.pdf"
        run("pdflatex", "-interaction=nonstopmode", tex)
        if shutil.which("bibtex"):
            run("bibtex", stem)
        run("pdflatex", "-interaction=nonstopmode", tex)
        run("pdflatex", "-interaction=nonstopmode", tex)
        text = stem_log.read_text(errors="ignore") if stem_log.exists() else ""
        errors = [ln for ln in text.splitlines() if ln.startswith("! ")]
        if errors:
            print(f"LaTeX errors ({label}):")
            for e in errors[:10]:
                print("  ", e)
            raise SystemExit("paper failed to compile cleanly")
        if not stem_pdf.exists():
            raise SystemExit(f"no {stem}.pdf produced")
        m = re.search(rf"Output written on {re.escape(stem)}\.pdf \((\d+) page", text)
        return m.group(1) if m else "?"

    # The NMI variant is a separate manuscript; build it and return.
    if getattr(args, "nmi", False):
        nmi_pdf = PAPER_DIR / "main_nmi.pdf"
        pages = _compile("main_nmi", "NMI variant")
        print(f"OK (NMI): {nmi_pdf} ({nmi_pdf.stat().st_size} bytes, {pages} pages)")
        return

    # The flag drives a \IfFileExists branch at TeX time. For --anon we build the
    # blind variant FIRST and copy it aside, THEN fall through to the canonical
    # named build, so main.pdf is ALWAYS the named paper regardless of mode and
    # the flag never lingers to poison a later build.
    if getattr(args, "anon", False):
        flag.write_text("anonymous\n", encoding="utf-8")
        try:
            pages = _compile("main", "anonymized")
        finally:
            if flag.exists():
                flag.unlink()
        out = PAPER_DIR / "main-anon.pdf"
        shutil.copyfile(pdf, out)
        print(f"OK (anonymized): {out} ({out.stat().st_size} bytes, {pages} pages)")

    if flag.exists():
        flag.unlink()  # canonical named build: flag must be absent
    pages = _compile("main", "named")
    print(f"OK: {pdf} ({pdf.stat().st_size} bytes, {pages} pages)")


def _strip_tex_comments(text: str) -> str:
    """Drop unescaped-% TeX comments so deliberately commented-out blocks (e.g.
    the deferred figS_replication figure, sections/09_appendix.tex) are not
    linted as live macro uses or figure/table references."""
    return re.sub(r"(?<!\\)%.*", "", text)


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
        # name the per-(venue, year) ladders the row-wise bijection validated
        # against (common.VENUE_TIERS — the consumer mirror of aipr's
        # decisions.py::_PROFILES); `check --dataset iclr2025` works unmodified
        # once the real export lands.
        for key in sorted({(v, int(y)) for v, y in zip(d.submissions["venue"], d.submissions["year"])}):
            print(f"     tier ladder {key[0]} {key[1]}: {' < '.join(VENUE_TIERS[key])}")
    except Exception as e:
        problems.append(f"data contract: {e}")

    # 2. undefined-macro lint across the paper sources
    defined = _defined_macros() | _LATEX_BUILTINS
    used: set[str] = set()
    srcs = list((PAPER_DIR / "sections").glob("*.tex")) + [PAPER_DIR / "main.tex"]
    for s in srcs:
        used |= set(re.findall(r"\\([a-zA-Z]+)", _strip_tex_comments(s.read_text(encoding="utf-8"))))
    undefined = sorted(used - defined)
    if undefined:
        problems.append(f"undefined macros referenced: {undefined}")
    else:
        print("[ok] no undefined macros in paper sources")

    # 3. referenced figures / tables exist
    missing = []
    for s in srcs:
        body = _strip_tex_comments(s.read_text(encoding="utf-8"))
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
        (MACRO_DIR, "PHASE2.flag"),
        (RESULTS_DIR, "*.json"),
        (PAPER_DIR, "*.aux"), (PAPER_DIR, "*.bbl"), (PAPER_DIR, "*.blg"), (PAPER_DIR, "*.log"),
        (PAPER_DIR, "*.out"), (PAPER_DIR, "*.toc"), (PAPER_DIR, "pass*.log"),
        (PAPER_DIR, "bibtex.log"), (PAPER_DIR, "finalpass.log"), (PAPER_DIR, "main.pdf"),
        (PAPER_DIR, "main-anon.pdf"), (PAPER_DIR, "main_nmi.pdf"), (PAPER_DIR, "ANONYMOUS.flag"),
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
    sp.add_argument("--dataset", default="iclr2026")
    sp.add_argument("--no-figures", action="store_true")
    sp = add("simulate", cmd_simulate, "power analysis + estimator validation")
    sp.add_argument("--quick", action="store_true")
    add("secondary", cmd_secondary, "comment-quality comparison (ReviewBench axis + correctness)")
    add("test", cmd_test, "run the pytest suite")
    sp = add("paper", cmd_paper, "compile the LaTeX paper")
    sp.add_argument("--anon", action="store_true",
                    help="build the anonymized (blind) variant -> main-anon.pdf")
    sp.add_argument("--nmi", action="store_true",
                    help="build the condensed NMI variant -> main_nmi.pdf")
    sp = add("check", cmd_check, "validate data + lint macros + verify refs")
    sp.add_argument("--dataset", default="iclr2026")
    add("clean", cmd_clean, "remove generated artifacts")
    add("freeze", cmd_freeze, "stamp DECISIONS.md with git commit + date")
    sp = add("all", cmd_all, "synth -> analyze -> simulate -> paper -> check")
    sp.add_argument("--dataset", default="iclr2026")
    sp.add_argument("--quick", action="store_true")
    sp.add_argument("--skip-sim", action="store_true")
    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
