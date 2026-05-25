from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from cogant.viz.png.config import (
    DEFAULT_CONFIG,
    RenderConfig,
    draw_color_legend,
    draw_footer,
    draw_metadata_banner,
    downsample_graph,
    sha256_file,
    truncate,
    timestamp,
    write_figure_sidecar,
)

logger = logging.getLogger(__name__)


def read_json(p: Path) -> Any | None:
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None
    except (OSError, ValueError):
        return None


def load_state_space_from_json(p: Path) -> Any | None:
    """Load a state_space JSON into an object that ``_state_space_entities``
    can read via ``getattr``. Returns ``None`` when not found or invalid."""
    from types import SimpleNamespace

    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return SimpleNamespace(
        variables=data.get("variables") or data.get("state_variables") or [],
        observations=data.get("observations") or data.get("observation_modalities") or [],
        actions=data.get("actions") or [],
        model_id=data.get("model_id"),
        kind=data.get("kind"),
    )


def load_process_model_from_json(p: Path) -> Any | None:
    """Load a process_model JSON into an attribute-accessible object."""
    from types import SimpleNamespace

    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return SimpleNamespace(
        process_id=data.get("process_id"),
        stages=data.get("stages") or [],
        policies=data.get("policies") or [],
        timelines=data.get("timelines") or [],
    )


def discover_state_space_json(run_dir: Path) -> Path | None:
    candidates = [
        run_dir / "state_space.json",
        run_dir / "gnn_package" / "state_space.json",
        run_dir / "gnn_pipeline" / "state_space.json",
        run_dir / "statespace" / "state_space_model.json",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def discover_process_model_json(run_dir: Path) -> Path | None:
    candidates = [
        run_dir / "process_model.json",
        run_dir / "gnn_package" / "process_model.json",
        run_dir / "gnn_pipeline" / "process_model.json",
        run_dir / "process" / "process_model.json",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def first_existing(run_dir: Path, relative_candidates: Iterable[str]) -> Path | None:
    """Return the first existing artifact under ``run_dir`` from a candidate list."""
    for candidate in relative_candidates:
        path = run_dir / candidate
        if path.is_file():
            return path
    return None
