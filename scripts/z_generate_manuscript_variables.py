#!/usr/bin/env python3
"""Generate ``manuscript_variables.json`` and substituted manuscript markdown.

This is the *thin orchestrator* that binds METRICS.yaml → the published
manuscript. It performs the following steps, in order:

1. **(optional) Regenerate metrics** — if ``--regenerate-metrics`` is passed,
   shell out to ``tools/regenerate_metrics.py`` before reading the YAML so
   the output reflects the live repository state.
2. **Load** ``cogant/evaluation/METRICS.yaml``.
3. **Build** a flat ``{NAME: formatted_str}`` dict from the registered
   placeholders in :mod:`tools.manuscript_vars` and **write**
   ``output/data/manuscript_variables.json`` with provenance metadata.
4. **Clean and substitute** every ``{{VAR}}`` in ``manuscript/*.md`` and write
   the result to ``output/manuscript/*.md``. The cleanup removes stale generated
   Markdown fragments so section renames cannot leave duplicate render inputs.
   Links that intentionally point from source fragments into sibling project
   files are rebased so they remain valid after the fragment is copied under
   ``output/manuscript/``.
5. **Copy** ``config.yaml``, ``references.bib``, ``preamble.md`` into
   ``output/manuscript/`` (renderer expects them there).
6. **Copy figures** — move curated real run PNGs from ``cogant/output`` into
   ``output/figures/`` for template PDF/HTML rendering. With ``--strict``,
   missing registered figures or incomplete figure metadata are fatal.
7. **Validate** — scan every written file for surviving ``{{PLACEHOLDER}}``
   tokens. Warnings are always logged; with ``--strict`` the process also
   exits non-zero (suitable for CI on pure-template manuscripts).

Invocation is directory-independent: all paths are anchored on ``__file__``.

Exit codes
----------
* ``0`` — everything succeeded (unresolved tokens become warnings).
* ``1`` — METRICS.yaml missing / malformed, regenerate step failed,
          manuscript dir empty, or (with ``--strict``) unresolved
          placeholders / missing registered figures were written to
          ``output/manuscript/`` or ``output/figures/``.

Usage::

    uv run python scripts/z_generate_manuscript_variables.py
    uv run python projects/cogant/scripts/z_generate_manuscript_variables.py  # parent template root
    uv run python scripts/z_generate_manuscript_variables.py --regenerate-metrics
    uv run python scripts/z_generate_manuscript_variables.py --strict
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

# Repository template root (parent of projects/)
_SCRIPT = Path(__file__).resolve()
COGANT_STAGING_ROOT = _SCRIPT.parent.parent
TEMPLATE_ROOT = COGANT_STAGING_ROOT.parent.parent
_TOOLS = COGANT_STAGING_ROOT / "tools"

if str(TEMPLATE_ROOT) not in sys.path:
    sys.path.insert(0, str(TEMPLATE_ROOT))
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

try:
    from infrastructure.core.logging.utils import get_logger  # type: ignore[import-not-found]  # noqa: E402
except ModuleNotFoundError:  # standalone passive checkout without parent template package

    def get_logger(name: str) -> logging.Logger:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
        return logging.getLogger(name)

from manuscript_vars import (  # noqa: E402
    build_flat_variables,
    find_unresolved_placeholders,
    substitute_text,
)
from manuscript_figures import copy_manuscript_figures  # noqa: E402

logger = get_logger(__name__)

MANUSCRIPT_DIR = COGANT_STAGING_ROOT / "manuscript"
OUTPUT_DIR = COGANT_STAGING_ROOT / "output"
DATA_DIR = OUTPUT_DIR / "data"
INJECTED_MS_DIR = OUTPUT_DIR / "manuscript"
METRICS_PATH = COGANT_STAGING_ROOT / "cogant" / "evaluation" / "METRICS.yaml"
REGENERATE_SCRIPT = _TOOLS / "regenerate_metrics.py"

AUX_COPY_NAMES = ("config.yaml", "references.bib", "preamble.md")


def clean_injected_manuscript_dir() -> None:
    """Remove generated Markdown from prior injections.

    The renderer discovers files by walking ``output/manuscript`` directly. If a
    source section is renamed, leaving the previous generated ``*.md`` file in
    place produces duplicate sections and duplicate cross-reference labels. Keep
    non-Markdown auxiliaries, then copy/write the current source set below.
    """

    if not INJECTED_MS_DIR.exists():
        return
    for old_md in INJECTED_MS_DIR.glob("*.md"):
        old_md.unlink()


def rebase_generated_links(text: str) -> str:
    """Adjust source-relative markdown links for ``output/manuscript``.

    The manuscript source lives at ``manuscript`` in this project root
    (or ``projects/cogant/manuscript`` when vendored into the parent template);
    generated fragments live one directory deeper at ``output/manuscript``.
    Figure links already
    target ``../figures`` and should stay unchanged. Links back to package,
    tooling, template infrastructure, or project roots need one additional
    ``..`` segment so rendered HTML/PDF sources do not contain broken paths.
    """

    replacements = {
        "](../cogant/": "](../../cogant/",
        "](../cogant)": "](../../cogant)",
        "](../tools/": "](../../tools/",
        "](../tools)": "](../../tools)",
        "](../scripts/": "](../../scripts/",
        "](../scripts)": "](../../scripts)",
        "](../PROMOTION.md": "](../../PROMOTION.md",
        "](../output/data/": "](../data/",
        "](../../../infrastructure/": "](../../../../infrastructure/",
        "](../../../projects/": "](../../../../projects/",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def load_metrics() -> dict:
    """Load METRICS.yaml with clear errors for missing / malformed files."""
    if not METRICS_PATH.exists():
        msg = (
            f"METRICS.yaml not found at {METRICS_PATH}. Run "
            "tools/regenerate_metrics.py first, or pass --regenerate-metrics."
        )
        logger.error(msg)
        raise FileNotFoundError(msg)
    try:
        with open(METRICS_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise SystemExit(f"ERROR: could not parse {METRICS_PATH}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(
            f"ERROR: {METRICS_PATH} did not parse to a mapping (got {type(data).__name__})"
        )
    return data


def regenerate_metrics() -> None:
    """Shell out to ``tools/regenerate_metrics.py`` and surface failures loudly."""
    if not REGENERATE_SCRIPT.is_file():
        raise SystemExit(f"ERROR: regenerate script not found at {REGENERATE_SCRIPT}")
    logger.info("Running %s ...", REGENERATE_SCRIPT)
    result = subprocess.run(
        [sys.executable, str(REGENERATE_SCRIPT)],
        cwd=COGANT_STAGING_ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"ERROR: regenerate_metrics.py exited {result.returncode}; "
            "see its stderr above for the underlying failure."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Thin orchestrator: regenerate metrics (optional), write "
            "manuscript_variables.json, substitute manuscript templates, and "
            "validate that no {{PLACEHOLDER}} tokens remain unresolved."
        ),
    )
    parser.add_argument(
        "--regenerate-metrics",
        action="store_true",
        help="Run tools/regenerate_metrics.py before reading METRICS.yaml.",
    )
    parser.add_argument(
        "--strict",
        dest="strict",
        action="store_true",
        default=False,
        help=(
            "Exit non-zero if any {{PLACEHOLDER}} remains unresolved in "
            "output/manuscript/ or any registered manuscript figure is "
            "missing/incompletely described. Off by default because manuscript/README.md "
            "and manuscript/AGENTS.md contain literal ``{{PLACEHOLDER}}`` "
            "tokens as documentation. Use in CI when you know the manuscript "
            "files are pure templates and the package figures have been generated."
        ),
    )
    parser.add_argument(
        "--strict-figures",
        action="store_true",
        help=(
            "Fail on missing or incompletely described registered manuscript "
            "figures even when placeholder strictness is disabled."
        ),
    )
    args = parser.parse_args(argv)

    if args.regenerate_metrics:
        regenerate_metrics()

    metrics = load_metrics()
    flat = build_flat_variables(metrics)

    provenance = {
        "schema_version": metrics.get("schema_version", "1.0"),
        "metrics_path": str(METRICS_PATH.relative_to(TEMPLATE_ROOT)),
        "metrics_generated_at": metrics.get("generated_at", ""),
        "generator_git_sha": metrics.get("generator_git_sha", ""),
        "injected_at": datetime.now(timezone.utc).isoformat(),
        "variables": flat,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    INJECTED_MS_DIR.mkdir(parents=True, exist_ok=True)
    clean_injected_manuscript_dir()

    out_json = DATA_DIR / "manuscript_variables.json"
    out_json.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    logger.info("Wrote %s (%d variables)", out_json, len(flat))

    md_files = sorted(MANUSCRIPT_DIR.glob("*.md"))
    if not md_files:
        msg = f"No manuscript/*.md files found under {MANUSCRIPT_DIR}"
        logger.error(msg)
        raise SystemExit(f"ERROR: {msg}")

    unresolved_by_file: dict[str, list[str]] = {}
    for src in md_files:
        text = src.read_text(encoding="utf-8")
        new_text, subs = substitute_text(text, metrics)
        new_text = rebase_generated_links(new_text)
        if subs:
            logger.debug("%s: %d substitution(s)", src.name, len(subs))
        dest = INJECTED_MS_DIR / src.name
        dest.write_text(new_text, encoding="utf-8")
        remaining = find_unresolved_placeholders(new_text)
        if remaining:
            unresolved_by_file[src.name] = remaining

    for name in AUX_COPY_NAMES:
        p = MANUSCRIPT_DIR / name
        if p.is_file():
            (INJECTED_MS_DIR / name).write_bytes(p.read_bytes())
            logger.info("Copied %s to output/manuscript/", name)
        else:
            logger.warning("Optional manuscript auxiliary not found: %s", p)

    figure_manifest = copy_manuscript_figures(
        COGANT_STAGING_ROOT,
        strict=args.strict or args.strict_figures,
    )
    logger.info("Prepared manuscript figures: %s", figure_manifest)

    print(str(out_json))
    print(str(INJECTED_MS_DIR))
    print(str(figure_manifest))

    if unresolved_by_file:
        msg_lines = [
            "Unresolved {{PLACEHOLDER}} tokens remained after substitution:",
        ]
        for name, tokens in sorted(unresolved_by_file.items()):
            msg_lines.append(f"  {name}: {', '.join(tokens)}")
        if args.strict:
            msg_lines.append(
                "Register the placeholders in tools/manuscript_vars.py::MANUSCRIPT_VARS "
                "or add the missing entries to METRICS.yaml."
            )
            print("\n".join(msg_lines), file=sys.stderr)
            return 1
        for line in msg_lines:
            logger.warning("%s", line)

    return 0


if __name__ == "__main__":
    sys.exit(main())
