#!/usr/bin/env python3
"""Generate manuscript_variables.json and substituted manuscript under output/manuscript/.

Reads ``cogant/evaluation/METRICS.yaml`` and ``tools/manuscript_vars.py``, writes:
  - ``output/data/manuscript_variables.json``
  - ``output/manuscript/*.md`` (templates from ``manuscript/*.md`` with ``{{VAR}}`` filled)
  - copies ``config.yaml``, ``references.bib``, ``preamble.md`` into ``output/manuscript/``

Run from repository root::

    uv run python projects_in_progress/cogant/scripts/z_generate_manuscript_variables.py

Or from ``projects_in_progress/cogant``::

    uv run python scripts/z_generate_manuscript_variables.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

# Repository template root (parent of projects_in_progress/)
_SCRIPT = Path(__file__).resolve()
COGANT_STAGING_ROOT = _SCRIPT.parent.parent
TEMPLATE_ROOT = COGANT_STAGING_ROOT.parent.parent
_TOOLS = COGANT_STAGING_ROOT / "tools"

if str(TEMPLATE_ROOT) not in sys.path:
    sys.path.insert(0, str(TEMPLATE_ROOT))
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from infrastructure.core.logging.utils import get_logger  # noqa: E402

from manuscript_vars import (  # noqa: E402
    build_flat_variables,
    substitute_text,
)

logger = get_logger(__name__)

MANUSCRIPT_DIR = COGANT_STAGING_ROOT / "manuscript"
OUTPUT_DIR = COGANT_STAGING_ROOT / "output"
DATA_DIR = OUTPUT_DIR / "data"
INJECTED_MS_DIR = OUTPUT_DIR / "manuscript"
METRICS_PATH = COGANT_STAGING_ROOT / "cogant" / "evaluation" / "METRICS.yaml"

AUX_COPY_NAMES = ("config.yaml", "references.bib", "preamble.md")


def load_metrics() -> dict:
    if not METRICS_PATH.exists():
        msg = f"METRICS.yaml not found at {METRICS_PATH}. Run tools/regenerate_metrics.py from the cogant package."
        logger.error(msg)
        raise FileNotFoundError(msg)
    with open(METRICS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
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

    out_json = DATA_DIR / "manuscript_variables.json"
    out_json.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    logger.info("Wrote %s (%d variables)", out_json, len(flat))

    md_files = sorted(MANUSCRIPT_DIR.glob("*.md"))
    if not md_files:
        logger.warning("No manuscript/*.md under %s", MANUSCRIPT_DIR)
    for src in md_files:
        text = src.read_text(encoding="utf-8")
        new_text, subs = substitute_text(text, metrics)
        if subs:
            logger.debug("%s: %d substitution(s)", src.name, len(subs))
        dest = INJECTED_MS_DIR / src.name
        dest.write_text(new_text, encoding="utf-8")

    for name in AUX_COPY_NAMES:
        p = MANUSCRIPT_DIR / name
        if p.is_file():
            (INJECTED_MS_DIR / name).write_bytes(p.read_bytes())
            logger.info("Copied %s to output/manuscript/", name)
        else:
            logger.warning("Optional manuscript auxiliary not found: %s", p)

    print(str(out_json))
    print(str(INJECTED_MS_DIR))


if __name__ == "__main__":
    main()
