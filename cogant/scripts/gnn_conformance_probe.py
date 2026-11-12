#!/usr/bin/env python3
"""Pinned upstream GNN conformance probe.

Emits a GNN package from the calculator fixture with the pipeline runner,
validates it at the ``standard`` and ``strict`` levels of the pinned upstream
parser, and runs upstream steps 3, 5 and 6 on the emitted package.  The pin
lives in ``.github/gnn-pin.json`` and the ``upstream`` extra installs it; this
probe reads the pin through ``gnn.importers.read_pin`` and fails when the
revision PEP 610 records for the installed distribution is not that commit, so
the parser exercised here is the pinned one rather than whichever revision the
environment happens to hold.

Run from the inner package root (``run_gate.py gnn`` does this):

    uv run python scripts/gnn_conformance_probe.py
"""

from __future__ import annotations

import json
import tempfile
from importlib import metadata
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

ROOT = Path(__file__).resolve().parents[2]
PIN_PATH = ROOT / ".github" / "gnn-pin.json"


def _installed_upstream_commit() -> str | None:
    """Return the commit PEP 610 records for the installed upstream distribution."""
    try:
        distribution = metadata.distribution("generalized-notation-notation")
        recorded = distribution.read_text("direct_url.json")
    except (metadata.PackageNotFoundError, OSError):
        return None
    try:
        payload = json.loads(recorded or "{}")
    except ValueError:
        return None
    vcs = payload.get("vcs_info") if isinstance(payload, dict) else None
    commit = vcs.get("commit_id") if isinstance(vcs, dict) else None
    return str(commit) if commit else None


def main() -> int:
    if not is_upstream_gnn_available():
        raise SystemExit("optional upstream was requested but is unavailable")
    from gnn.importers import read_pin

    pin = read_pin(PIN_PATH)
    installed_commit = _installed_upstream_commit()
    if installed_commit != pin.commit:
        raise SystemExit(
            "installed upstream "
            f"{installed_commit or '(unrecorded)'} does not match the pin {pin.commit}"
        )
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
        "pin": {
            "path": str(PIN_PATH.relative_to(ROOT)),
            "tag": pin.tag,
            "commit": pin.commit,
        },
        "installed_commit": installed_commit,
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
