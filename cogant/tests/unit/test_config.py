"""Unit tests for the composable per-stage pydantic config system.

Covers:

- Per-stage sub-configs (IngestConfig, GraphConfig, TranslateConfig,
  StatespaceConfig, GNNConfig, ReverseConfig) — defaults and frozenness.
- Composite ``PipelineConfig`` — defaults, nesting, override semantics,
  dict round-trip, JSON round-trip, and optional YAML round-trip.
- Compatibility-superset guarantee: the exact constructor calls used by the
  old ``cogant.api.pipeline.PipelineConfig`` dataclass still work.

No mocks; everything operates on real pydantic models and real temp
files via the ``tmp_path`` fixture.
"""

from __future__ import annotations

import importlib.util
import json

import pytest
from pydantic import ValidationError

from cogant.config import (
    GNNConfig,
    GraphConfig,
    IngestConfig,
    PipelineConfig,
    ReverseConfig,
    StatespaceConfig,
    TranslateConfig,
)

_HAS_YAML = importlib.util.find_spec("yaml") is not None


# ---------------------------------------------------------------------------
# Per-stage sub-config defaults and frozenness
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ingest_config_defaults():
    cfg = IngestConfig()
    assert cfg.max_file_size_kb == 512
    assert cfg.include_extensions == [".py", ".js", ".ts"]
    assert cfg.exclude_patterns == ["__pycache__", ".git", "node_modules"]
    assert cfg.follow_symlinks is False
    assert cfg.encoding == "utf-8"


@pytest.mark.unit
def test_graph_config_defaults():
    cfg = GraphConfig()
    assert cfg.max_nodes == 10_000
    assert cfg.max_edges == 50_000
    assert cfg.prune_isolated is True
    assert cfg.include_builtins is False


@pytest.mark.unit
def test_translate_config_defaults():
    cfg = TranslateConfig()
    assert cfg.max_iterations == 10
    assert cfg.confidence_threshold == 0.5
    assert cfg.enable_rules == []
    assert cfg.disable_rules == []


@pytest.mark.unit
def test_statespace_config_defaults():
    cfg = StatespaceConfig()
    assert cfg.normalize_matrices is True
    assert cfg.matrix_tolerance == pytest.approx(1e-6)
    assert cfg.max_hidden_states == 512
    assert cfg.max_observations == 2048


@pytest.mark.unit
def test_gnn_config_defaults():
    cfg = GNNConfig()
    assert cfg.include_metadata is True
    assert cfg.include_connections is True
    assert cfg.include_matrices is True
    assert cfg.matrix_format == "dense"


@pytest.mark.unit
def test_reverse_config_defaults():
    cfg = ReverseConfig()
    assert cfg.synthesis_strategy == "minimal"
    assert cfg.include_tests is False
    assert cfg.role_threshold == pytest.approx(0.7)


@pytest.mark.unit
@pytest.mark.parametrize(
    "cls,field,new_value",
    [
        (IngestConfig, "max_file_size_kb", 1024),
        (GraphConfig, "max_nodes", 42),
        (TranslateConfig, "max_iterations", 5),
        (StatespaceConfig, "max_hidden_states", 16),
        (GNNConfig, "include_metadata", False),
        (ReverseConfig, "include_tests", True),
    ],
)
def test_substage_configs_are_frozen(cls, field, new_value):
    cfg = cls()
    with pytest.raises(ValidationError):
        setattr(cfg, field, new_value)


# ---------------------------------------------------------------------------
# Literal / bounds validation on sub-configs
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_gnn_config_rejects_unknown_matrix_format():
    with pytest.raises(ValidationError):
        GNNConfig(matrix_format="tensor")  # type: ignore[arg-type]


@pytest.mark.unit
def test_reverse_config_rejects_unknown_strategy():
    with pytest.raises(ValidationError):
        ReverseConfig(synthesis_strategy="aggressive")  # type: ignore[arg-type]


@pytest.mark.unit
def test_translate_config_threshold_bounds():
    with pytest.raises(ValidationError):
        TranslateConfig(confidence_threshold=1.5)
    with pytest.raises(ValidationError):
        TranslateConfig(confidence_threshold=-0.1)


# ---------------------------------------------------------------------------
# Composite PipelineConfig — defaults and nesting
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_pipeline_config_defaults_and_nesting():
    cfg = PipelineConfig()
    # Default stage list
    assert cfg.stages == [
        "ingest",
        "static",
        "normalize",
        "graph",
        "translate",
    ]
    assert cfg.skip_dynamic is True
    # Nested sub-config access
    assert isinstance(cfg.ingest, IngestConfig)
    assert isinstance(cfg.graph, GraphConfig)
    assert isinstance(cfg.translate, TranslateConfig)
    assert isinstance(cfg.statespace, StatespaceConfig)
    assert isinstance(cfg.gnn, GNNConfig)
    assert isinstance(cfg.reverse, ReverseConfig)
    # Nested field reachable via dotted access
    assert cfg.translate.max_iterations == 10
    assert cfg.ingest.max_file_size_kb == 512
    assert cfg.gnn.matrix_format == "dense"


@pytest.mark.unit
def test_pipeline_config_is_frozen():
    cfg = PipelineConfig()
    with pytest.raises(ValidationError):
        cfg.skip_dynamic = False  # type: ignore[misc]


@pytest.mark.unit
def test_pipeline_config_sub_configs_are_still_frozen():
    cfg = PipelineConfig()
    with pytest.raises(ValidationError):
        cfg.translate.max_iterations = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# override()
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_override_changes_scalar_field():
    cfg = PipelineConfig()
    new_cfg = cfg.override(skip_dynamic=False)
    assert new_cfg.skip_dynamic is False
    # Original is untouched (immutability)
    assert cfg.skip_dynamic is True
    # A new object is returned
    assert new_cfg is not cfg


@pytest.mark.unit
def test_override_can_replace_nested_sub_config():
    cfg = PipelineConfig()
    new_translate = TranslateConfig(max_iterations=3, confidence_threshold=0.9)
    new_cfg = cfg.override(translate=new_translate)
    assert new_cfg.translate.max_iterations == 3
    assert new_cfg.translate.confidence_threshold == pytest.approx(0.9)
    # Unrelated sub-configs are preserved
    assert new_cfg.ingest == cfg.ingest
    assert new_cfg.graph == cfg.graph


@pytest.mark.unit
def test_override_rejects_unknown_fields():
    cfg = PipelineConfig()
    with pytest.raises(ValueError, match="Unknown PipelineConfig fields"):
        cfg.override(not_a_field=123)


# ---------------------------------------------------------------------------
# to_dict / from_dict round-trip
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_dict_round_trip_defaults():
    cfg = PipelineConfig()
    as_dict = cfg.to_dict()
    assert isinstance(as_dict, dict)
    assert "stages" in as_dict
    assert "translate" in as_dict
    assert isinstance(as_dict["translate"], dict)
    assert as_dict["translate"]["max_iterations"] == 10

    restored = PipelineConfig.from_dict(as_dict)
    assert restored == cfg


@pytest.mark.unit
def test_dict_round_trip_with_overrides():
    cfg = PipelineConfig(
        stages=["ingest", "graph"],
        skip_dynamic=False,
        translate=TranslateConfig(max_iterations=7),
        gnn=GNNConfig(matrix_format="sparse"),
    )
    restored = PipelineConfig.from_dict(cfg.to_dict())
    assert restored == cfg
    assert restored.translate.max_iterations == 7
    assert restored.gnn.matrix_format == "sparse"
    assert restored.skip_dynamic is False


@pytest.mark.unit
def test_from_dict_accepts_nested_plain_dicts():
    payload = {
        "stages": ["ingest", "graph", "translate"],
        "skip_dynamic": False,
        "ingest": {"max_file_size_kb": 1024, "encoding": "latin-1"},
        "graph": {"max_nodes": 42, "include_builtins": True},
    }
    cfg = PipelineConfig.from_dict(payload)
    assert cfg.ingest.max_file_size_kb == 1024
    assert cfg.ingest.encoding == "latin-1"
    assert cfg.graph.max_nodes == 42
    assert cfg.graph.include_builtins is True
    assert cfg.skip_dynamic is False


# ---------------------------------------------------------------------------
# JSON round-trip (stdlib-only, always runs)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_json_round_trip(tmp_path):
    cfg = PipelineConfig(
        stages=["ingest", "graph"],
        skip_dynamic=False,
        translate=TranslateConfig(max_iterations=4),
    )
    path = tmp_path / "pipeline.json"
    cfg.to_json(path)

    # File is valid JSON and structurally equivalent.
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["stages"] == ["ingest", "graph"]
    assert raw["translate"]["max_iterations"] == 4

    restored = PipelineConfig.from_json(path)
    assert restored == cfg


# ---------------------------------------------------------------------------
# YAML round-trip (only if pyyaml is installed)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.skipif(not _HAS_YAML, reason="pyyaml not installed")
def test_yaml_round_trip(tmp_path):
    cfg = PipelineConfig(
        stages=["ingest", "graph", "translate"],
        skip_dynamic=False,
        ingest=IngestConfig(include_extensions=[".py"]),
        translate=TranslateConfig(max_iterations=2, confidence_threshold=0.8),
    )
    path = tmp_path / "pipeline.yaml"
    cfg.to_yaml(path)

    restored = PipelineConfig.from_yaml(path)
    assert restored == cfg
    assert restored.ingest.include_extensions == [".py"]
    assert restored.translate.confidence_threshold == pytest.approx(0.8)


@pytest.mark.unit
@pytest.mark.skipif(not _HAS_YAML, reason="pyyaml not installed")
def test_from_yaml_rejects_non_mapping(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must be a mapping"):
        PipelineConfig.from_yaml(path)


# ---------------------------------------------------------------------------
# Compatibility-superset: the old dataclass constructor kwargs still work
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_compatibility_kwargs_still_construct():
    """The exact signatures used by the old api.pipeline.PipelineConfig."""
    cfg = PipelineConfig(
        stages=["ingest", "static", "graph"],
        skip_stages=["export", "validate"],
        skip_dynamic=True,
        output_dir="/tmp/out",
        verbose=True,
        dry_run=False,
        layout_output=True,
        plugins={"dynamic": {"coverage_path": "/tmp/.coverage"}},
        coverage_path="/tmp/.coverage",
        trace_path="/tmp/trace.json",
    )
    assert cfg.stages == ["ingest", "static", "graph"]
    assert cfg.skip_stages == ["export", "validate"]
    assert cfg.skip_dynamic is True
    assert cfg.output_dir == "/tmp/out"
    assert cfg.verbose is True
    assert cfg.layout_output is True
    assert cfg.plugins == {"dynamic": {"coverage_path": "/tmp/.coverage"}}
    assert cfg.coverage_path == "/tmp/.coverage"
    assert cfg.trace_path == "/tmp/trace.json"


@pytest.mark.unit
def test_compatibility_default_skip_dynamic_shape():
    """Default stages/skip_dynamic must match the task-spec signature.

    Task spec: ``PipelineConfig(stages=[...], skip_dynamic=True)`` — so
    the default skip_dynamic is ``True`` on the new pydantic config.
    """
    cfg = PipelineConfig()
    assert cfg.skip_dynamic is True
    assert "ingest" in cfg.stages
    assert cfg.skip_stages == []
    assert cfg.plugins == {}
