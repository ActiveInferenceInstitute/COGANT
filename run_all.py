#!/usr/bin/env python3
"""Run COGANT against configured example repos and emit all practical CLI outputs.

Each target writes under ``output_root/<id>/`` (bundle, ``gnn_package/``, scans, site,
PNGs, validation). Local targets use ``path``; remote targets use ``git_url`` (clone to
``<id>/_git_source/``). See README.md (Batch outputs)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.run_all_runner import DEFAULT_CONFIG, RunBatchOptions, run_batch

STAGING_ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Run COGANT pipeline + GNN outputs.")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--log", type=Path, default=None)
    parser.add_argument("--print-default-config", action="store_true")
    parser.add_argument(
        "--targets",
        type=str,
        default=None,
        help="Comma-separated target ids to run (subset of the config). Default: all.",
    )
    args = parser.parse_args()
    if args.print_default_config:
        print(json.dumps(DEFAULT_CONFIG, indent=2))
        return 0
    # C1: main()'s exit code must be failure-aware. ``failures`` is bound
    # before the try so the final return references a defined name on every
    # non-early-return path (and mypy --strict sees no possibly-unbound name).
    failures: list[str] = []
    try:
        rc = run_batch(RunBatchOptions.from_namespace(args))
    except KeyboardInterrupt:
        print("run_all: interrupted", file=sys.stderr)
        return 130
    if rc != 0:
        failures.append(f"run_batch exit={rc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
