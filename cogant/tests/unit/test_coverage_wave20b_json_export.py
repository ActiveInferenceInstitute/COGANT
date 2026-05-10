"""Wave 20b coverage boost for ``cogant.gnn.json_export``.

Targets the residual uncovered branches in ``json_export.py``:

* Line 73 — ``self.mappings`` is neither dict nor list (set type), reset to ``{}``.
* Lines 137-144 — ``_export_matrices`` ValueError/AttributeError exception path.
* Lines 196 / 215 / 232 — Optional metadata fields:
  - ``meta.custom_metadata`` populated → ``"custom"`` block
  - ``state_space.metadata["extraction_time_ms"]`` propagated
  - repository-metadata ``custom`` field round-trip
* Lines 334-335 / 668-669 — Variables carry non-empty ``factors`` so the
  ``var_by_factor`` accumulator path runs.
* Lines 376 / 394 / 716 / 728 — Sections that only execute when the
  state space has likelihoods / preferences / transitions populated.
* Lines 479-485 — ``_export_markov_blanket`` AttributeError exception path
  (a graph whose attributes are missing).
* Lines 788-789 — ``_export_process_model`` runs the connection branch.
* Lines 909-932 / 945-970 — Module-level ``export_for_pymdp`` and
  ``export_summary`` helpers.

All tests build real COGANT value objects (no mocks).
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from cogant.gnn.json_export import (
    GNNJSONExporter,
    export_for_pymdp,
    export_summary,
)
from cogant.graph.builder import ProgramGraphBuilder
from cogant.process.extractor import ProcessConnection, ProcessModel, Stage
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import (
    ConfidenceTier,
    MappingKind,
    SemanticMapping,
)
from cogant.statespace.compiler import (
    Action,
    Likelihood,
    ObservationModality,
    Preference,
    StateSpaceModel,
    Transition,
)
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import (
    ConfidenceLevel,
    StateVariable,
    StateVariableType,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------- helpers


def _build_program_graph(custom_meta: dict[str, Any] | None = None) -> ProgramGraph:
    """A tiny but real program graph with metadata."""
    builder = ProgramGraphBuilder(repo_uri="test://wave20b-export")
    module = builder.add_node(
        kind=NodeKind.MODULE,
        name="m",
        qualified_name="m",
        path="m.py",
        language="python",
    )
    fn = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="f",
        qualified_name="m.f",
        path="m.py",
        language="python",
    )
    builder.add_edge(module.id, fn.id, EdgeKind.CONTAINS)
    builder.graph.metadata.evidence_sources = ["unit_test"]
    if custom_meta is not None:
        builder.graph.metadata.custom_metadata = custom_meta
    return builder.finalize()


def _build_state_space(
    *,
    with_factors: bool = False,
    with_transitions: bool = False,
    with_likelihoods: bool = False,
    with_preferences: bool = False,
    with_observations: bool = False,
    with_actions: bool = False,
    with_extraction_time: bool = False,
) -> StateSpaceModel:
    """Return a state space with selectively-populated sections."""
    var = StateVariable(
        id="var:counter",
        name="counter",
        var_type=StateVariableType.DISCRETE,
        node_id="node:counter",
        cardinality=10,
        confidence=ConfidenceLevel.HIGH,
        factors=["F1"] if with_factors else None,
    )
    obs: dict[str, ObservationModality] = {}
    if with_observations:
        obs["obs:s"] = ObservationModality(
            id="obs:s",
            name="sensor",
            source_node_id="node:s",
            modality_type="sensor",
            cardinality=2,
            confidence=ConfidenceLevel.MEDIUM,
        )
    actions: dict[str, Action] = {}
    if with_actions:
        actions["act:do"] = Action(
            id="act:do",
            name="do",
            controller_id="node:do",
            confidence=ConfidenceLevel.HIGH,
        )
    transitions: dict[str, Transition] = {}
    if with_transitions:
        transitions["t1"] = Transition(
            id="t1",
            source_state={"var:counter": "pre"},
            target_state={"var:counter": "post"},
            action_id="act:do" if with_actions else None,
            triggered_by="event",
            probability=1.0,
            confidence=ConfidenceLevel.HIGH,
        )
    likelihoods: dict[str, Likelihood] = {}
    if with_likelihoods:
        likelihoods["lk1"] = Likelihood(
            id="lk1",
            variable_id="var:counter",
            distribution_type="categorical",
            parameters={"p": 0.5},
            confidence=ConfidenceLevel.HIGH,
        )
    preferences: dict[str, Preference] = {}
    if with_preferences:
        preferences["pref1"] = Preference(
            id="pref1",
            name="goal_state",
            description="prefer counter > 0",
            scope=["var:counter"],
            expression="counter > 0",
            weight=2.0,
            source="node:test",
            confidence=ConfidenceLevel.MEDIUM,
        )
    metadata: dict[str, Any] = {"pipeline_stages": ["a", "b"]}
    if with_extraction_time:
        metadata["extraction_time_ms"] = 12.5

    return StateSpaceModel(
        id="ss:test",
        schema_name="schema",
        variables={var.id: var},
        observations=obs,
        actions=actions,
        transitions=transitions,
        likelihoods=likelihoods,
        preferences=preferences,
        time_regime=TimeRegime.SYNCHRONOUS,
        metadata=metadata,
    )


def _build_process_model(*, with_connection: bool = False) -> ProcessModel:
    s1 = Stage(
        id="stage:1",
        name="first",
        description="initial",
        node_ids=["n1"],
        confidence=0.9,
    )
    s2 = Stage(
        id="stage:2",
        name="second",
        description="next",
        node_ids=["n2"],
        confidence=0.7,
    )
    connections: dict[str, ProcessConnection] = {}
    if with_connection:
        connections["conn:12"] = ProcessConnection(
            id="conn:12",
            source_stage_id=s1.id,
            target_stage_id=s2.id,
            trigger="completion",
            condition="success",
            success_rate=0.95,
        )
    return ProcessModel(
        id="proc:test",
        schema_name="schema",
        stages={s1.id: s1, s2.id: s2},
        connections=connections,
        entry_stage_id=s1.id,
        exit_stage_ids=[s2.id],
    )


def _build_mappings() -> dict[str, SemanticMapping]:
    m = SemanticMapping(
        id="m1",
        kind=MappingKind.OBSERVATION,
        graph_fragment_node_ids=["n1"],
        semantic_label="x",
        description="d",
        confidence_score=0.7,
        confidence_tier=ConfidenceTier.STATIC_ONLY,
    )
    return {m.id: m}


# ============================================================ mappings reset path


class TestMappingsTypeNormalization:
    """Cover line 73: non-dict, non-list mappings reset to ``{}``."""

    def test_set_mappings_reset_to_empty_dict(self) -> None:
        """A set is neither dict nor list — exporter resets to {}."""
        graph = _build_program_graph()
        ss = _build_state_space()
        proc = _build_process_model()
        # Bypass the type-checker by passing a set (still iterable).
        exporter = GNNJSONExporter(
            program_graph=graph,
            state_space_model=ss,
            process_model=proc,
            semantic_mappings={"unused"},  # type: ignore[arg-type]
        )
        out = exporter.export()
        # Mappings reset to {} → no mapping IDs in the canonical output.
        assert out["mappings"]["summary"]["total_mappings"] == 0


# ============================================================ matrices exception


class TestMatricesExceptionPath:
    """Cover lines 137-144: GNNMatrices raising AttributeError → empty payload."""

    def test_matrices_attribute_error_returns_empty(self) -> None:
        """Pass mappings whose entries lack the ``.kind`` attribute.

        ``GNNMatrices.__init__`` enumerates ``m.kind`` for each mapping;
        a ``str`` mapping value triggers the AttributeError branch.
        """
        graph = _build_program_graph()
        ss = _build_state_space()
        proc = _build_process_model()
        # Use a list of strings as the mappings — GNNMatrices will iterate
        # ``mappings.values()`` (when dict) or list directly; in either case
        # the enumerator dereferences ``m.kind`` and raises AttributeError.
        bad_mappings = {"x": "not-a-mapping"}  # type: ignore[dict-item]
        exporter = GNNJSONExporter(
            program_graph=graph,
            state_space_model=ss,
            process_model=proc,
            semantic_mappings=bad_mappings,  # type: ignore[arg-type]
        )
        matrices = exporter._export_matrices()
        assert matrices["A"] == []
        assert matrices["B"] == []
        assert matrices["C"] == []
        assert matrices["D"] == []
        assert matrices["dimensions"]["n_states"] == 0


# ============================================================ metadata branches


class TestMetadataOptionalSections:
    """Cover the optional-metadata branches in ``_export_metadata`` and
    ``_export_repository_metadata``."""

    def test_custom_metadata_is_propagated(self) -> None:
        """Cover line 196 (model_metadata.repository.custom) and 230 (repo metadata)."""
        graph = _build_program_graph(custom_meta={"team": "platform", "owner": "alice"})
        ss = _build_state_space()
        proc = _build_process_model()
        exporter = GNNJSONExporter(
            program_graph=graph,
            state_space_model=ss,
            process_model=proc,
            semantic_mappings=_build_mappings(),
        )
        out = exporter.export()
        assert out["model_metadata"]["repository"]["custom"] == {
            "team": "platform",
            "owner": "alice",
        }
        assert out["repository_metadata"]["custom"] == {
            "team": "platform",
            "owner": "alice",
        }

    def test_extraction_time_is_propagated(self) -> None:
        """Cover line 215: state_space.metadata['extraction_time_ms'] passes through."""
        graph = _build_program_graph()
        ss = _build_state_space(with_extraction_time=True)
        proc = _build_process_model()
        exporter = GNNJSONExporter(
            program_graph=graph,
            state_space_model=ss,
            process_model=proc,
            semantic_mappings=_build_mappings(),
        )
        out = exporter.export()
        assert out["model_metadata"]["extraction_time_ms"] == pytest.approx(12.5)


# ============================================================ factors / sections


class TestVariablesWithFactors:
    """Cover lines 334-335 (factors section) and 668-669 (state_space block)."""

    def test_factor_indexing_runs_when_variables_have_factors(self) -> None:
        graph = _build_program_graph()
        ss = _build_state_space(with_factors=True)
        proc = _build_process_model()
        exporter = GNNJSONExporter(
            program_graph=graph,
            state_space_model=ss,
            process_model=proc,
            semantic_mappings=_build_mappings(),
        )
        out = exporter.export()
        # _export_factors_section runs the inner factor loop.
        assert "F1" in out["factors"]["factors"]
        assert "var:counter" in out["factors"]["factorization"]["F1"]
        # _export_state_space also runs the duplicate factor loop.
        assert "F1" in out["state_space"]["summary"]["factorization"]


# ============================================================ likelihoods/prefs


class TestLikelihoodAndPreferenceSections:
    """Cover lines 376/394 (canonical sections) and 716/728 (state_space block)."""

    def test_likelihood_and_preference_blocks_run(self) -> None:
        graph = _build_program_graph()
        ss = _build_state_space(
            with_likelihoods=True,
            with_preferences=True,
        )
        proc = _build_process_model()
        exporter = GNNJSONExporter(
            program_graph=graph,
            state_space_model=ss,
            process_model=proc,
            semantic_mappings=_build_mappings(),
        )
        out = exporter.export()
        # Canonical likelihood_structure section
        assert out["likelihood_structure"]["count"] == 1
        assert "lk1" in out["likelihood_structure"]["likelihoods"]
        # Canonical preferences_constraints section
        assert out["preferences_constraints"]["count"] == 1
        assert "pref1" in out["preferences_constraints"]["preferences"]
        # state_space block also serializes them
        assert "lk1" in out["state_space"]["likelihoods"]
        assert "pref1" in out["state_space"]["preferences"]


# ============================================================ transition/observation/action


class TestTransitionsAndModalities:
    """Exercise ``_export_transition_structure``, observations and actions."""

    def test_transitions_observations_actions_export(self) -> None:
        graph = _build_program_graph()
        ss = _build_state_space(
            with_observations=True,
            with_actions=True,
            with_transitions=True,
        )
        proc = _build_process_model()
        exporter = GNNJSONExporter(
            program_graph=graph,
            state_space_model=ss,
            process_model=proc,
            semantic_mappings=_build_mappings(),
        )
        out = exporter.export()
        assert out["transition_structure"]["count"] == 1
        # _is_deterministic handled probability=1.0 case
        assert out["transition_structure"]["deterministic"] is True
        assert out["observation_modalities"]["count"] == 1
        # symbolic vs sensor modality
        assert "sensor" in out["observation_modalities"]["modalities"]
        assert out["actions_policies"]["count"] == 1


# ============================================================ markov blanket


class TestMarkovBlanketExceptionPath:
    """Cover lines 479-485: ``_export_markov_blanket`` exception fallback."""

    def test_markov_blanket_fallback_on_value_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Force MarkovBlanketExtractor.extract to raise ValueError.

        Patch the exact __globals__ dict that _export_markov_blanket uses for
        name lookup — robust to prior-test module reloads that may have left
        stale class references in sys.modules vs. live method globals.
        """

        class _ErrorExtractor:
            def __init__(self, graph: object) -> None:
                pass

            def extract(self, **kwargs: object) -> object:
                raise ValueError("forced for coverage")

        method_globals = GNNJSONExporter._export_markov_blanket.__globals__
        monkeypatch.setitem(method_globals, "MarkovBlanketExtractor", _ErrorExtractor)

        graph = _build_program_graph()
        ss = _build_state_space()
        proc = _build_process_model()
        exporter = GNNJSONExporter(
            program_graph=graph,
            state_space_model=ss,
            process_model=proc,
            semantic_mappings=_build_mappings(),
        )
        blanket = exporter._export_markov_blanket()
        assert blanket["partition"] == {
            "internal": [],
            "sensory": [],
            "active": [],
            "external": [],
        }
        assert blanket["seed_strategy"] == "auto"
        assert blanket["boundary_ratio"] == 0.0

    def test_markov_blanket_fallback_on_attribute_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AttributeError is also caught and produces the same fallback."""

        class _AttrErrorExtractor:
            def __init__(self, graph: object) -> None:
                pass

            def extract(self, **kwargs: object) -> object:
                raise AttributeError("simulated upstream attr error")

        method_globals = GNNJSONExporter._export_markov_blanket.__globals__
        monkeypatch.setitem(method_globals, "MarkovBlanketExtractor", _AttrErrorExtractor)

        graph = _build_program_graph()
        ss = _build_state_space()
        proc = _build_process_model()
        exporter = GNNJSONExporter(
            program_graph=graph,
            state_space_model=ss,
            process_model=proc,
            semantic_mappings=_build_mappings(),
        )
        blanket = exporter._export_markov_blanket()
        assert blanket["partition"]["internal"] == []
        assert blanket["seed_strategy"] == "auto"


# ============================================================ process connections


class TestProcessConnections:
    """Cover lines 786-796 (process connection block)."""

    def test_process_model_with_connection(self) -> None:
        graph = _build_program_graph()
        ss = _build_state_space()
        proc = _build_process_model(with_connection=True)
        exporter = GNNJSONExporter(
            program_graph=graph,
            state_space_model=ss,
            process_model=proc,
            semantic_mappings=_build_mappings(),
        )
        out = exporter.export()
        assert out["process_model"]["summary"]["connection_count"] == 1
        conn = out["process_model"]["connections"]["conn:12"]
        assert conn["source_stage_id"] == "stage:1"
        assert conn["target_stage_id"] == "stage:2"
        assert conn["success_rate"] == pytest.approx(0.95)


# ============================================================ export_for_pymdp


class TestExportForPyMDP:
    """Cover lines 909-932: module-level ``export_for_pymdp`` helper."""

    def test_export_for_pymdp_basic(self) -> None:
        bundle = {
            "matrices": {
                "A": [[0.9, 0.1], [0.1, 0.9]],
                "B": [[[1.0]], [[0.0]]],
                "C": [0.5, -0.5],
                "D": [0.6, 0.4],
                "n_states": 2,
                "n_obs": 2,
                "n_actions": 1,
            }
        }
        result = export_for_pymdp(bundle)
        assert result["A"] == [[0.9, 0.1], [0.1, 0.9]]
        assert result["B"] == [[[1.0]], [[0.0]]]
        assert result["C"] == [0.5, -0.5]
        assert result["D"] == [0.6, 0.4]
        assert result["metadata"]["n_states"] == 2
        assert result["metadata"]["n_obs"] == 2
        assert result["metadata"]["n_actions"] == 1
        assert isinstance(result["metadata"]["exported_at"], str)
        # No truncation key in this branch.
        assert "b_truncation" not in result["metadata"]

    def test_export_for_pymdp_with_truncation(self) -> None:
        bundle = {
            "matrices": {
                "A": [],
                "B": [],
                "C": [],
                "D": [],
                "n_states": 100,
                "n_obs": 0,
                "n_actions": 0,
                "b_truncated": True,
                "b_n_states_full": 100,
                "b_n_states_kept": 32,
            }
        }
        result = export_for_pymdp(bundle)
        # Truncation metadata is propagated.
        assert result["metadata"]["b_truncation"]["truncated"] is True
        assert result["metadata"]["b_truncation"]["n_states_full"] == 100
        assert result["metadata"]["b_truncation"]["n_states_kept"] == 32

    def test_export_for_pymdp_empty_bundle(self) -> None:
        """Missing matrices key → defaults are used."""
        result = export_for_pymdp({})
        assert result["A"] == []
        assert result["B"] == []
        assert result["C"] == []
        assert result["D"] == []
        assert result["metadata"]["n_states"] == 0


# ============================================================ export_summary


class TestExportSummary:
    """Cover lines 945-970: module-level ``export_summary`` helper."""

    def test_summary_with_full_bundle(self) -> None:
        bundle = {
            "model_id": "ss:test",
            "schema_name": "test_schema",
            "matrices": {"n_states": 4, "n_obs": 3, "n_actions": 2},
            "state_space": {"model_name": "demo"},
            "program_graph": {"nodes": {"n1": {}, "n2": {}}},
            "mappings": {"mappings": [{"id": "m1"}, {"id": "m2"}]},
            "provenance": {"timestamp": "2026-01-01T00:00:00"},
        }
        out = export_summary(bundle)
        assert out["model_id"] == "ss:test"
        assert out["model_name"] == "demo"
        assert out["schema_version"] == "test_schema"
        assert out["dimensions"] == {"n_states": 4, "n_obs": 3, "n_actions": 2}
        assert out["matrix_shapes"]["A"] == "(3, 4)"
        assert out["matrix_shapes"]["B"] == "(4, 4, 2)"
        assert out["matrix_shapes"]["C"] == "(3,)"
        assert out["matrix_shapes"]["D"] == "(4,)"
        assert out["coverage"]["total_nodes"] == 2
        assert out["coverage"]["total_mappings"] == 2
        assert out["timestamp"] == "2026-01-01T00:00:00"

    def test_summary_with_minimal_bundle(self) -> None:
        out = export_summary({})
        assert out["model_id"] is None
        assert out["model_name"] == "unknown"
        assert out["schema_version"] == "unknown"
        assert out["dimensions"] == {"n_states": 0, "n_obs": 0, "n_actions": 0}
        # Fallback timestamp
        assert out["timestamp"] == "unknown"


# ============================================================ end-to-end


class TestMappingsListConversion:
    """Cover line 71: list of mappings is converted into a dict by id."""

    def test_list_of_mappings_converted_to_dict(self) -> None:
        graph = _build_program_graph()
        ss = _build_state_space()
        proc = _build_process_model()
        m1 = SemanticMapping(
            id="lm1",
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=["n1"],
            confidence_score=0.5,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
        )
        m2 = SemanticMapping(
            id="lm2",
            kind=MappingKind.ACTION,
            graph_fragment_node_ids=["n2"],
            confidence_score=0.6,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
        )
        # Pass as a list; export() should convert to a dict on first call.
        exporter = GNNJSONExporter(
            program_graph=graph,
            state_space_model=ss,
            process_model=proc,
            semantic_mappings=[m1, m2],  # type: ignore[arg-type]
        )
        out = exporter.export()
        # Conversion ran inside export(); the dict round-trip is visible.
        assert isinstance(exporter.mappings, dict)
        assert set(exporter.mappings.keys()) == {"lm1", "lm2"}
        # Mappings section reflects the converted dict.
        assert out["mappings"]["summary"]["total_mappings"] == 2


class TestRepositoryMetadataNoneBranch:
    """Cover line 232: ``_export_repository_metadata`` returns ``{}`` when meta is None."""

    def test_no_metadata_returns_empty_dict(self) -> None:
        """Cover line 232: metadata=None branch in repository_metadata."""
        # Build a real graph then strip metadata to None.
        graph = _build_program_graph()
        graph.metadata = None  # type: ignore[assignment]
        ss = _build_state_space()
        proc = _build_process_model()
        exporter = GNNJSONExporter(
            program_graph=graph,
            state_space_model=ss,
            process_model=proc,
            semantic_mappings={},
        )
        result = exporter._export_repository_metadata()
        assert result == {}

    def test_compute_coverage_empty_graph_zero(self) -> None:
        """Cover line 246: empty nodes → 0.0 coverage."""
        graph = _build_program_graph()
        # Strip nodes to empty dict.
        graph.nodes = {}
        ss = _build_state_space()
        proc = _build_process_model()
        exporter = GNNJSONExporter(
            program_graph=graph,
            state_space_model=ss,
            process_model=proc,
            semantic_mappings={},
        )
        assert exporter._compute_coverage() == 0.0


class TestNumericConfidenceSuccessPath:
    """Cover lines 531/540/557/568: float() succeeds on numeric ``confidence``."""

    def test_average_confidence_with_numeric_values(self) -> None:
        """A variable + observation with numeric confidence floats survive
        the ``try: float(...)`` branch, hitting append() in success path."""
        graph = _build_program_graph()
        var = StateVariable(
            id="v1",
            name="v1",
            var_type=StateVariableType.DISCRETE,
            node_id="n1",
            cardinality=2,
            confidence=0.85,  # type: ignore[arg-type] # runtime float
        )
        obs = ObservationModality(
            id="o1",
            name="o1",
            source_node_id="n1",
            modality_type="sensor",
            confidence=0.6,  # type: ignore[arg-type]
        )
        action = Action(
            id="a1",
            name="a1",
            controller_id="n1",
            confidence=0.75,  # type: ignore[arg-type]
        )
        transition = Transition(
            id="t1",
            source_state={},
            target_state={},
            confidence=0.9,  # type: ignore[arg-type]
        )
        ss = StateSpaceModel(
            id="ss:n",
            schema_name="schema",
            variables={var.id: var},
            observations={obs.id: obs},
            actions={action.id: action},
            transitions={transition.id: transition},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
            metadata={},
        )
        proc = _build_process_model()
        exporter = GNNJSONExporter(
            program_graph=graph,
            state_space_model=ss,
            process_model=proc,
            semantic_mappings={},
        )
        avg = exporter._compute_average_confidence()
        # Numeric values were appended; mean of {0.85, 0.6} = 0.725
        assert avg == pytest.approx(0.725)
        # Component-specific too
        var_conf = exporter._compute_component_confidence("variables")
        obs_conf = exporter._compute_component_confidence("observations")
        action_conf = exporter._compute_component_confidence("actions")
        trans_conf = exporter._compute_component_confidence("transitions")
        unknown = exporter._compute_component_confidence("unknown_component")
        assert var_conf == pytest.approx(0.85)
        assert obs_conf == pytest.approx(0.6)
        assert action_conf == pytest.approx(0.75)
        assert trans_conf == pytest.approx(0.9)
        assert unknown == 0.5


class TestMappingProvenance:
    """Cover line 875: mappings with provenance list are serialized."""

    def test_mapping_with_provenance_appears_in_export(self) -> None:
        from cogant.schemas.semantic import ProvenanceRecord

        graph = _build_program_graph()
        ss = _build_state_space()
        proc = _build_process_model()
        prov = ProvenanceRecord(source="static_analysis", confidence=0.9)
        mapping = SemanticMapping(
            id="prov_mapping",
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=["n1"],
            confidence_score=0.7,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[prov],
        )
        exporter = GNNJSONExporter(
            program_graph=graph,
            state_space_model=ss,
            process_model=proc,
            semantic_mappings={mapping.id: mapping},
        )
        out = exporter._export_mappings()
        assert "provenance" in out["mappings"]["prov_mapping"]
        assert out["mappings"]["prov_mapping"]["provenance"][0]["source"] == "static_analysis"
        assert out["mappings"]["prov_mapping"]["provenance"][0]["confidence"] == pytest.approx(0.9)


class TestEndToEnd:
    """Sanity: full export round-trips through JSON cleanly."""

    def test_export_roundtrips_through_json(self) -> None:
        graph = _build_program_graph(custom_meta={"k": "v"})
        ss = _build_state_space(
            with_factors=True,
            with_transitions=True,
            with_likelihoods=True,
            with_preferences=True,
            with_observations=True,
            with_actions=True,
            with_extraction_time=True,
        )
        proc = _build_process_model(with_connection=True)
        exporter = GNNJSONExporter(
            program_graph=graph,
            state_space_model=ss,
            process_model=proc,
            semantic_mappings=_build_mappings(),
        )
        s = exporter.export_to_string(indent=None)
        # Compact form has no newlines.
        assert "\n" not in s
        parsed = json.loads(s)
        # Sanity sample: factor, likelihood, preference, transition.
        assert "F1" in parsed["state_space"]["summary"]["factorization"]
        assert parsed["likelihood_structure"]["count"] == 1
        assert parsed["preferences_constraints"]["count"] == 1
        assert parsed["transition_structure"]["count"] == 1
