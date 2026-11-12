#!/usr/bin/env python3
"""Render the COGANT manuscript to PDF from the injected Markdown tree.

This is the authoritative render entry point.  It follows the parent template's
conventions without importing the template package:

* Pandoc Markdown sections under ``manuscript/`` in discovery order
  (``00_``–``10_`` main sections, then ``S0*`` appendices, then ``98_``
  glossary, then other files, then ``99_`` references last).
* Declared variables: ``{{TOKEN}}`` placeholders are resolved by
  ``scripts/z_generate_manuscript_variables.py`` from
  ``cogant/evaluation/METRICS.yaml``; this script refuses to render a document
  with surviving placeholders.
* Figure registry: ``tools/manuscript_figure_registry.py`` entries are checked
  against the generated files by ``tools/manuscript_figures.py --strict``.
* One render command: pandoc + pandoc-crossref + citeproc over
  ``output/manuscript/`` with ``output/figures/`` on the resource path.

Usage (from the COGANT project root)::

    uv run python scripts/render_manuscript.py
    uv run python scripts/render_manuscript.py --skip-generate
    python run_gate.py manuscript        # same command, measured as a gate arm

Exit codes: ``0`` rendered, ``1`` generation/validation/render failure,
``2`` a required external tool is unavailable.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MANUSCRIPT_DIR = ROOT / "manuscript"
OUTPUT_DIR = ROOT / "output"
INJECTED_DIR = OUTPUT_DIR / "manuscript"
FIGURES_DIR = OUTPUT_DIR / "figures"
GENERATOR = ROOT / "scripts" / "z_generate_manuscript_variables.py"
FIGURE_CHECK = ROOT / "tools" / "manuscript_figures.py"
COMBINED_NAME = "_render_combined.md"
PREAMBLE_TEX_NAME = "_render_preamble.tex"
DEFAULT_PDF = INJECTED_DIR / "COGANT.pdf"

# Mirrors infrastructure/rendering/manuscript_discovery.py EXCLUDE_NAMES.
EXCLUDE_NAMES = {
    "preamble.md",
    "AGENTS.md",
    "README.md",
    "SYNTAX.md",
    "MANUSCRIPT_STATUS.md",
    "config.yaml",
    "config.yaml.example",
    "references.bib",
    COMBINED_NAME,
}
LATEX_BLOCK = re.compile(r"```latex\n(.*?)```", re.DOTALL)
PLACEHOLDER = re.compile(r"\{\{[^{}\n]{1,120}\}\}")

# Characters that appear in manuscript prose but are absent from the default
# Latin Modern text fonts. ``newunicodechar`` maps them to math glyphs in text
# mode, so code spans and prose keep the character instead of dropping it.
UNICODE_REMAP = {
    "ε": r"\ensuremath{\varepsilon}",
    "ρ": r"\ensuremath{\rho}",
    "π": r"\ensuremath{\pi}",
    "≤": r"\ensuremath{\leq}",
    "≥": r"\ensuremath{\geq}",
    "∈": r"\ensuremath{\in}",
    "≈": r"\ensuremath{\approx}",
    "∎": r"\ensuremath{\blacksquare}",
    "⟺": r"\ensuremath{\Longleftrightarrow}",
    "↔": r"\ensuremath{\leftrightarrow}",
    "⊆": r"\ensuremath{\subseteq}",
    "η": r"\ensuremath{\eta}",
    "λ": r"\ensuremath{\lambda}",
    "μ": r"\ensuremath{\mu}",
    "τ": r"\ensuremath{\tau}",
}


def _fail(message: str) -> int:
    print(f"render_manuscript: {message}", file=sys.stderr)
    return 1


def _run(argv: list[str], *, cwd: Path) -> int:
    print(f"render_manuscript: {' '.join(argv)}")
    completed = subprocess.run(argv, cwd=cwd, check=False)
    return completed.returncode


def generate_injected_manuscript() -> int:
    if not GENERATOR.is_file():
        return _fail(f"missing variable generator: {GENERATOR}")
    return _run([sys.executable, str(GENERATOR)], cwd=ROOT)


def validate_figure_registry() -> int:
    if not FIGURE_CHECK.is_file():
        return _fail(f"missing figure checker: {FIGURE_CHECK}")
    return _run([sys.executable, str(FIGURE_CHECK), "--strict"], cwd=ROOT)


def discover(source_dir: Path) -> list[Path]:
    """Order manuscript files exactly like the parent template renderer."""
    files = [
        path
        for path in source_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".md" and path.name not in EXCLUDE_NAMES
    ]
    main: list[Path] = []
    supplemental: list[Path] = []
    glossary: list[Path] = []
    references: list[Path] = []
    other: list[Path] = []
    for path in files:
        stem = path.stem
        if stem.startswith("99_"):
            references.append(path)
        elif stem.startswith("98_"):
            glossary.append(path)
        elif stem.startswith("S"):
            supplemental.append(path)
        elif stem and stem[0].isdigit():
            main.append(path)
        else:
            other.append(path)
    ordered = (
        sorted(main, key=lambda p: p.stem)
        + sorted(supplemental, key=lambda p: p.stem)
        + sorted(glossary, key=lambda p: p.stem)
        + sorted(other, key=lambda p: p.stem)
        + sorted(references, key=lambda p: p.stem)
    )
    return ordered


def load_config(source_dir: Path) -> dict:
    path = source_dir / "config.yaml"
    if not path.is_file():
        raise SystemExit(f"render_manuscript: missing {path}; run the variable generator first")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return loaded if isinstance(loaded, dict) else {}


def extract_preamble(source_dir: Path) -> str | None:
    path = source_dir / "preamble.md"
    if not path.is_file():
        return None
    blocks = LATEX_BLOCK.findall(path.read_text(encoding="utf-8"))
    if not blocks:
        return None
    body = "\n".join(block.strip() for block in blocks) + "\n"
    body += "\n\\usepackage{newunicodechar}\n"
    for char, replacement in UNICODE_REMAP.items():
        body += f"\\newunicodechar{{{char}}}{{{replacement}}}\n"
    target = source_dir / PREAMBLE_TEX_NAME
    target.write_text(body, encoding="utf-8")
    return str(target)


def pandoc_metadata(config: dict) -> list[str]:
    paper = config.get("paper") or {}
    metadata = config.get("metadata") or {}
    args: list[str] = ["--metadata=linkReferences:true", "--metadata=link-citations:true"]
    if isinstance(paper, dict):
        if paper.get("title"):
            args.append(f"--metadata=title:{paper['title']}")
        if paper.get("subtitle"):
            args.append(f"--metadata=subtitle:{paper['subtitle']}")
        date = paper.get("date") or dt.date.today().isoformat()
        args.append(f"--metadata=date:{date}")
    names = [
        str(author["name"])
        for author in config.get("authors") or []
        if isinstance(author, dict) and author.get("name")
    ]
    if names:
        args.append(f"--metadata=author:{'; '.join(names)}")
    language = str(metadata.get("language") or "en") if isinstance(metadata, dict) else "en"
    args.append(f"--metadata=lang:{language}")
    return args


def pandoc_command(
    *,
    pandoc: str,
    combined: Path,
    pdf: Path,
    preamble_tex: str | None,
    config: dict,
    crossref: str | None,
) -> list[str]:
    command = [
        pandoc,
        str(combined),
        "-o",
        str(pdf),
        "--from=markdown+tex_math_dollars+raw_tex+header_attributes+pipe_tables+citations",
        "--pdf-engine=xelatex",
        "--standalone",
        "--number-sections",
        # Resource paths first, then filters, then citation machinery: the
        # template's documented ordering contract.
        f"--resource-path={INJECTED_DIR}",
        f"--resource-path={FIGURES_DIR}",
        f"--resource-path={OUTPUT_DIR}",
        *pandoc_metadata(config),
    ]
    metadata = config.get("metadata") or {}
    if isinstance(metadata, dict) and metadata.get("geometry"):
        command.extend(["-V", f"geometry:{metadata['geometry']}"])
    command.extend(["-V", "documentclass:article", "-V", "fontsize:11pt"])
    if preamble_tex:
        command.append(f"--include-in-header={preamble_tex}")
    if crossref:
        command.extend(["--filter", crossref])
    bibliography = INJECTED_DIR / "references.bib"
    if bibliography.is_file():
        # The PDF lane uses natbib (the preamble loads it), matching the parent
        # template's combined-PDF command; pandoc drives bibtex itself.
        command.extend(["--natbib", f"--bibliography={bibliography}"])
    return command


def tool_error(names: list[str]) -> int:
    missing = [name for name in names if shutil.which(name) is None]
    if not missing:
        return 0
    print(
        "render_manuscript: required tool(s) unavailable: " + ", ".join(missing),
        file=sys.stderr,
    )
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--skip-generate",
        action="store_true",
        help="use the existing output/manuscript/ tree instead of re-injecting variables",
    )
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF, help="PDF output path")
    parser.add_argument(
        "--skip-figure-check",
        action="store_true",
        help="skip the figure-registry validation (renders with whatever assets exist)",
    )
    parser.add_argument(
        "--keep-combined",
        action="store_true",
        help="keep the combined Markdown and preamble used for the render",
    )
    args = parser.parse_args(argv)

    status = tool_error(["pandoc"])
    if status:
        return status
    crossref = shutil.which("pandoc-crossref")
    if not crossref:
        print("render_manuscript: pandoc-crossref unavailable; cross-references will not resolve", file=sys.stderr)

    if not args.skip_generate:
        if generate_injected_manuscript() != 0:
            return _fail("variable injection failed")
    if not INJECTED_DIR.is_dir():
        return _fail(f"missing injected manuscript tree: {INJECTED_DIR} (run without --skip-generate)")
    if not args.skip_figure_check:
        if validate_figure_registry() != 0:
            return _fail(
                "figure registry is not backed by generated files; run the batch pipeline "
                "(cogant/ -> uv run python ../run_all.py --targets calculator,flask_app) first"
            )

    ordered = discover(INJECTED_DIR)
    if not ordered:
        return _fail(f"no manuscript files found in {INJECTED_DIR}")
    print(f"render_manuscript: {len(ordered)} section file(s), first={ordered[0].name}, last={ordered[-1].name}")

    combined = INJECTED_DIR / COMBINED_NAME
    combined.write_text(
        "\n\n".join(path.read_text(encoding="utf-8").strip() for path in ordered) + "\n",
        encoding="utf-8",
    )
    survived = sorted(set(PLACEHOLDER.findall(combined.read_text(encoding="utf-8"))))
    if survived:
        return _fail("unresolved placeholders remain: " + ", ".join(survived[:20]))

    config = load_config(INJECTED_DIR)
    preamble_tex = extract_preamble(INJECTED_DIR)
    if shutil.which("xelatex") is None:
        return tool_error(["xelatex"])

    command = pandoc_command(
        pandoc=shutil.which("pandoc") or "pandoc",
        combined=combined,
        pdf=args.pdf,
        preamble_tex=preamble_tex,
        config=config,
        crossref=crossref,
    )
    print("render_manuscript: " + " ".join(command))
    completed = subprocess.run(command, cwd=INJECTED_DIR, check=False)
    if completed.returncode != 0:
        return _fail(
            f"pandoc exited {completed.returncode}; combined source kept at {combined}"
        )
    if not args.keep_combined:
        combined.unlink(missing_ok=True)
        if preamble_tex:
            Path(preamble_tex).unlink(missing_ok=True)
    if not args.pdf.is_file() or args.pdf.stat().st_size < 10_000:
        return _fail(f"PDF was not produced (or is implausibly small): {args.pdf}")
    print(f"render_manuscript: wrote {args.pdf} ({args.pdf.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
