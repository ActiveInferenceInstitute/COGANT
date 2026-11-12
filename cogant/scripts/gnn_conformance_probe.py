#!/usr/bin/env python3
"""Pinned upstream GNN conformance probe.

Emits a GNN package from the calculator fixture with the pipeline runner,
validates it at the ``standard`` and ``strict`` levels of the pinned upstream
parser, and runs upstream steps 3, 5 and 6 on the emitted package.  The pin
itself lives in ``.github/gnn-pin.json`` and in the ``upstream`` extra of
``pyproject.toml``; this probe only uses whatever that extra installed.

Run from the inner package root (``run_gate.py gnn`` does this):

    uv run python scripts/gnn_conformance_probe.py
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from cogant.api.pipeline import PipelineConfig, PipelineRunner
from cogant.gnn.upstream_bridge import (
    is_upstream_gnn_available,
    run_upstream_validate_gnn,
    upstream_version,
)
from cogant.gnn.upstream_bridge.pipeline import (
    UpstreamPipelineConfig,
    run_upstream_pipeline,
)


def main() -> int:
    if not is_upstream_gnn_available():
        raise SystemExit("optional upstream was requested but is unavailable")
    out = Path(tempfile.mkdtemp(prefix="cogant-upstream-smoke-"))
    PipelineRunner().run("examples/control_positive/calculator", PipelineConfig(output_dir=str(out)))
    package = out / "gnn_package"
    markdown = (package / "model.gnn.md").read_text(encoding="utf-8")
    validation = {
        level: run_upstream_validate_gnn(markdown, validation_level=level).to_dict()
        for level in ("standard", "strict")
    }
    steps = run_upstream_pipeline(
        UpstreamPipelineConfig(target_dir=package, output_dir=out / "upstream", only_steps=[3, 5, 6])
    )
    payload = {
        "version": upstream_version(),
        "validation": validation,
        "steps": steps.to_dict(),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not all(result["ok"] for result in validation.values()):
        raise SystemExit("upstream validation rejected the COGANT package")
    if steps.error or steps.failure_count:
        raise SystemExit("upstream parse/type-check/validation steps failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
