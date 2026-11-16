#!/usr/bin/env python3
"""Run the producer's real importer verdict under independent source admission."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cogant.gnn.upstream_bridge.qualification import invoke


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--require-pointer", action="store_true")
    parser.add_argument("--workflow")
    parser.add_argument("--job")
    args = parser.parse_args()
    response = invoke(
        "importer-check", args.repo,
        require_pointer=args.require_pointer, pointer_workflow=args.workflow, pointer_job=args.job,
    )
    report = response["value"]
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("ok") and report.get("qualified") else 1


if __name__ == "__main__":
    raise SystemExit(main())
