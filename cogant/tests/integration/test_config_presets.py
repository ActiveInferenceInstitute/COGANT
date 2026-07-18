"""Integration coverage for typed presets and a real repository pipeline."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PY_ROOT = _REPO_ROOT / "py"
if str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))

from cogant.api.bundle import Bundle
from cogant.api.orchestration import (
    run_graph,
    run_ingest,
    run_normalize,
    run_process,
    run_statespace,
    run_static,
    run_translate,
)
from cogant.config import ProjectConfig
from cogant.config.presets import PRESETS, get_preset


def test_all_presets_are_valid_project_models() -> None:
    assert set(PRESETS) == {
        "default",
        "minimal",
        "standard",
        "comprehensive",
        "gnn-focused",
        "security",
    }
    for name, config in PRESETS.items():
        assert isinstance(config, ProjectConfig), name
        assert config.pipeline.stages, name


def test_security_preset_requires_loopback_safe_defaults() -> None:
    config = get_preset("security")
    assert config.server.host == "127.0.0.1"
    assert config.server.allow_absolute_paths is False
    assert config.server.auth_token is None
    assert config.server.rate_limit_requests > 0


def test_preset_configuration_is_consistent_across_reads() -> None:
    for name in PRESETS:
        first = get_preset(name)
        second = get_preset(name)
        assert first.model_dump(mode="json") == second.model_dump(mode="json")


@pytest.mark.parametrize(
    "fixture_name", ["flask_mini", "calculator", "event_pipeline"]
)
def test_real_fixture_executes_core_pipeline(fixture_name: str) -> None:
    repo_path = _REPO_ROOT / "examples" / "control_positive" / fixture_name
    if not repo_path.is_dir():
        pytest.skip(f"fixture not present: {fixture_name}")
    with tempfile.TemporaryDirectory():
        bundle = Bundle(target=str(repo_path), metadata={"config": get_preset("standard").model_dump(mode="json")})
        run_ingest(str(repo_path), bundle)
        run_static(bundle)
        run_normalize(bundle)
        run_graph(bundle, str(repo_path))
        run_translate(bundle)
        run_statespace(bundle, str(repo_path))
        run_process(bundle, str(repo_path))
        assert bundle.errors == []
        assert "_program_graph" in bundle.artifacts
        assert "_semantic_mappings" in bundle.artifacts
        assert "_state_space_model" in bundle.artifacts
        assert "_process_model" in bundle.artifacts
