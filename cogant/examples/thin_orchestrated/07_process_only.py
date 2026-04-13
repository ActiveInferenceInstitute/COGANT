#!/usr/bin/env python3
"""Thin example: process extraction only.

Extracts a ``ProcessModel`` from the program graph and prints stage and
connection summaries.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/07_process_only.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, build_rich_graph, configure_logging, parse_args  # noqa: E402

from cogant.process.extractor import ProcessExtractor  # noqa: E402


def main() -> int:
    args = parse_args("process")
    configure_logging()
    banner("Stage 7: process extraction")

    target = args.target.expanduser().resolve()
    pg = build_rich_graph(target)

    extractor = ProcessExtractor(pg, schema_name=target.name)
    pm = extractor.extract()

    print(f"  schema name : {pm.schema_name}")
    print(f"  stages      : {len(pm.stages)}")
    print(f"  connections : {len(pm.connections)}")
    print(f"  entry stage : {pm.entry_stage_id}")
    print(f"  exit stages : {len(pm.exit_stage_ids)}")

    if pm.stages:
        print("\n  process stages (first 8):")
        for stage in list(pm.stages.values())[:8]:
            entry = len(getattr(stage, "entry_points", []) or [])
            exit_ = len(getattr(stage, "exit_points", []) or [])
            pattern = getattr(stage, "pattern_type", None) or "?"
            print(f"    {stage.name:<32} pattern={pattern:<10} in={entry} out={exit_}")

    if pm.connections:
        print("\n  connections (first 5):")
        for conn in list(pm.connections.values())[:5]:
            trig = getattr(conn, "trigger", None) or "-"
            print(f"    {conn.source_stage_id} -> {conn.target_stage_id}  trigger={trig}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out = args.output_dir / "process_summary.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(
            {
                "schema_name": pm.schema_name,
                "stages": len(pm.stages),
                "connections": len(pm.connections),
                "entry_stage": pm.entry_stage_id,
                "exit_stages": pm.exit_stage_ids,
            },
            f,
            indent=2,
            default=str,
        )

    full = args.output_dir / "process_model.json"
    try:
        with open(full, "w", encoding="utf-8") as f:
            json.dump(asdict(pm), f, indent=2, default=str)
    except (TypeError, ValueError):
        with open(full, "w", encoding="utf-8") as f:
            json.dump({"id": pm.id, "schema_name": pm.schema_name}, f, indent=2)

    print(f"\n  wrote: {out}")
    print(f"  wrote: {full}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
