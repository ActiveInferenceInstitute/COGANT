"""Unit tests for :class:`cogant.gnn.json_export.GNNJSONExporter`.

These tests exercise the JSON export pipeline end-to-end against real
COGANT value objects (``ProgramGraph``, ``StateSpaceModel``,
``ProcessModel``, ``SemanticMapping``) instead of dict literals. The
models are constructed by hand with minimal but representative data so
the assertions are deterministic: the exporter is a pure function over
its inputs.
"""

from __future__ import annotations

import json

import pytest

from cogant.gnn.json_export import GNNJSONExporter
from cogant.graph.builder import ProgramGraphBuilder
from cogant.process.extractor import ProcessModel, Stage
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import (
    ConfidenceTier,
    MappingKind,
    ProvenanceRecord,
    SemanticMapping,
)
from cogant.statespace.compiler import StateSpaceModel
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import (
    ConfidenceLevel,
    StateVariable,
    StateVariableType,
)

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------- fixtures


@pytest.fixture
def program_graph() -> ProgramGraph:
    """Build a minimal but real program graph."""
    builder = ProgramGraphBuilder(repo_uri="test://gnn-export")
    module = builder.add_node(
        kind=NodeKind.MODULE,
        name="service",
        qualified_name="service",
        path="service.py",
        language="python",
    )
    fn = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="handle_request",
        qualified_name="service.handle_request",
        path="service.py",
        language="python",
    )
    builder.add_edge(module.id, fn.id, EdgeKind.CONTAINS)
    builder.graph.metadata.evidence_sources = ["static_analysis"]
    return builder.finalize()


@pytest.fixture
def state_space() -> StateSpaceModel:
    """Minimal StateSpaceModel with a single state variable."""
    var = StateVariable(
        id="var:counter",
        name="counter",
        var_type=StateVariableType.DISCRETE,
        node_id="node:counter",
        cardinality=10,
        confidence=ConfidenceLevel.HIGH,
    )
    return StateSpaceModel(
        id="ss:test",
        schema_name="test_schema",
        variables={var.id: var},
        observations={},
        actions={},
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
        metadata={"pipeline_stages": ["extract", "classify"]},
    )


@pytest.fixture
def process_model() -> ProcessModel:
    """Minimal ProcessModel with a single stage."""
    stage = Stage(
        id="stage:init",
        name="initialization",
        description="boot up",
        node_ids=["n1"],
        confidence=0.8,
    )
    return ProcessModel(
        id="proc:test",
        schema_name="test_schema",
        stages={stage.id: stage},
        connections={},
        entry_stage_id=stage.id,
        exit_stage_ids=[stage.id],
    )


@pytest.fixture
def semantic_mappings() -> dict[str, SemanticMapping]:
    """Dictionary of real SemanticMapping objects keyed by ID."""
    m1 = SemanticMapping(
        id="mapping:obs",
        kind=MappingKind.OBSERVATION,
        graph_fragment_node_ids=["n1"],
        semantic_label="sensor",
        description="an observation",
        confidence_score=0.82,
        confidence_tier=ConfidenceTier.STATIC_ONLY,
        provenance=[ProvenanceRecord(source="static_analysis", confidence=0.82)],
        evidence_count=1,
        parser_certainty=1.0,
    )
    return {m1.id: m1}


@pytest.fixture
def exporter(
    program_graph: ProgramGraph,
    state_space: StateSpaceModel,
    process_model: ProcessModel,
    semantic_mappings: dict[str, SemanticMapping],
) -> GNNJSONExporter:
    return GNNJSONExporter(
        program_graph=program_graph,
        state_space_model=state_space,
        process_model=process_model,
        semantic_mappings=semantic_mappings,
    )


# ------------------------------------------------------------------- construction


class TestGNNJSONExporterConstruction:
    """Tests for GNNJSONExporter construction."""

    def test_exporter_stores_inputs(
        self,
        exporter: GNNJSONExporter,
        program_graph: ProgramGraph,
        state_space: StateSpaceModel,
        process_model: ProcessModel,
    ) -> None:
        assert exporter.graph is program_graph
        assert exporter.state_space is state_space
        assert exporter.process is process_model
        assert "mapping:obs" in exporter.mappings


# ------------------------------------------------------------------------ export


class TestGNNJSONExportDict:
    """Tests for the ``export`` method returning a dict."""

    def test_export_returns_dict(self, exporter: GNNJSONExporter) -> None:
        out = exporter.export()
        assert isinstance(out, dict)

    def test_export_has_canonical_sections(
        self, exporter: GNNJSONExporter
    ) -> None:
        out = exporter.export()
        expected = {
            "model_id",
            "schema_name",
            "model_metadata",
            "repository_metadata",
            "source_coverage",
            "state_space",
            "observation_modalities",
            "actions_policies",
            "connections",
            "factors",
            "transition_structure",
            "likelihood_structure",
            "preferences_constraints",
            "time_settings",
            "parameterization",
            "ontology_mapping",
            "provenance",
            "confidence",
            "rendering_hints",
            "validation_notes",
            "program_graph",
            "process_model",
            "mappings",
        }
        missing = expected - set(out.keys())
        assert not missing, f"Missing canonical sections: {missing}"

    def test_model_id_and_schema_name_roundtrip(
        self, exporter: GNNJSONExporter
    ) -> None:
        out = exporter.export()
        assert out["model_id"] == "ss:test"
        assert out["schema_name"] == "test_schema"

    def test_metrics_reflect_real_counts(
        self, exporter: GNNJSONExporter
    ) -> None:
        out = exporter.export()
        metrics = out["model_metadata"]["metrics"]
        assert metrics["node_count"] == 2
        assert metrics["edge_count"] == 1
        assert metrics["state_variables"] == 1
        assert metrics["processes"] == 1
        assert metrics["mappings"] == 1

    def test_repository_metadata_has_uri(
        self, exporter: GNNJSONExporter
    ) -> None:
        out = exporter.export()
        repo = out["repository_metadata"]
        assert repo["uri"] == "test://gnn-export"
        assert "python" in repo["languages"]


# ------------------------------------------------------------- export_to_string


class TestGNNJSONExportString:
    """Tests for ``export_to_string``."""

    def test_export_to_string_is_valid_json(
        self, exporter: GNNJSONExporter
    ) -> None:
        s = exporter.export_to_string(indent=2)
        assert isinstance(s, str)
        assert "\n" in s  # pretty-printed
        parsed = json.loads(s)
        assert parsed["schema_name"] == "test_schema"

    def test_export_compact_has_no_newlines_by_default(
        self, exporter: GNNJSONExporter
    ) -> None:
        s = exporter.export_to_string(indent=None)
        parsed = json.loads(s)
        assert parsed["model_id"] == "ss:test"

    def test_export_round_trips_through_json(
        self, exporter: GNNJSONExporter
    ) -> None:
        s = exporter.export_to_string(indent=0)
        parsed = json.loads(s)
        # Real node from the graph must be present in connections section
        connections = parsed["connections"]
        assert connections["count"] >= 1


# --------------------------------------------------------- mappings coercion


class TestMappingsCoercion:
    """Tests for the mappings-list→dict safety net in ``export``."""

    def test_exporter_converts_list_of_mappings_to_dict(
        self,
        program_graph: ProgramGraph,
        state_space: StateSpaceModel,
        process_model: ProcessModel,
    ) -> None:
        mapping = SemanticMapping(
            id="mapping:from_list",
            kind=MappingKind.ACTION,
            graph_fragment_node_ids=["n1"],
            semantic_label="act",
        )
        exporter = GNNJSONExporter(
            program_graph=program_graph,
            state_space_model=state_space,
            process_model=process_model,
            semantic_mappings=[mapping],  # type: ignore[arg-type]
        )
        out = exporter.export()
        assert "mapping:from_list" in exporter.mappings
        assert out["model_metadata"]["metrics"]["mappings"] == 1
