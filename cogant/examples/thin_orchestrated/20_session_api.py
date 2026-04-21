#!/usr/bin/env python3
"""Thin example: use the high-level Session API.

Drives COGANT via ``cogant.api.Session`` — the canonical session-oriented
entry point. Every call on ``Session`` returns a summary dict, and the
final ``export_all`` writes a full bundle to disk. This is the shortest
"as a library consumer would write it" end-to-end demo.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/20_session_api.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, configure_logging, parse_args  # noqa: E402

from cogant.api import Session  # noqa: E402


def _show(label: str, result) -> None:
    if isinstance(result, dict):
        short = {
            k: (v if not isinstance(v, (list, dict)) else f"<{type(v).__name__}:{len(v)}>")
            for k, v in result.items()
        }
        print(f"  {label}: {short}")
    else:
        print(f"  {label}: {result}")


def main() -> int:
    args = parse_args("session_api")
    configure_logging()
    banner("Higher-order: Session API driven pipeline")

    target = args.target.expanduser().resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    session = Session.from_target(str(target))
    print(f"  session target : {target}\n")

    _show("extract_static", session.extract_static())
    _show("extract_dynamic", session.extract_dynamic())
    _show("build_graph", session.build_graph())
    _show("translate_to_gnn", session.translate_to_gnn())
    _show("compile_state_space", session.compile_state_space())

    export_dir = args.output_dir / "session_bundle"
    session.export_all(str(export_dir), layout=False)

    print(f"\n  exported to : {export_dir}")
    if export_dir.exists():
        files = sorted(p.name for p in export_dir.iterdir() if p.is_file())
        print(f"  top-level files: {len(files)}")
        for name in files[:12]:
            print(f"    - {name}")
        if len(files) > 12:
            print(f"    ... and {len(files) - 12} more")

    summary = {
        "target": str(target),
        "export_dir": str(export_dir),
        "files": (
            sorted(p.name for p in export_dir.iterdir() if p.is_file())
            if export_dir.exists()
            else []
        ),
    }
    out = args.output_dir / "session_summary.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n  wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
