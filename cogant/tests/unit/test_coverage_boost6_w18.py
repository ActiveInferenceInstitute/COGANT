#!/usr/bin/env python3
"""Coverage boost batch 6: schemas modules — base, core, state_space, process_model,
semantic_mapping, gnn_export, validation, provenance, bundle."""

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# schemas/base.py
# ---------------------------------------------------------------------------

class TestCogantBaseModel:
    def test_instantiate(self):
        from cogant.schemas.base import CogantBaseModel
        class Sub(CogantBaseModel):
            x: int = 1
        m = Sub()
        assert m.x == 1

    def test_validate_assignment(self):
        from cogant.schemas.base import CogantBaseModel
        class Sub(CogantBaseModel):
            x: int = 1
        m = Sub()
        m.x = 2
        assert m.x == 2


class TestStableID:
    def test_is_str_subclass(self):
        from cogant.schemas.base import StableID
        sid = StableID("abc123")
        assert isinstance(sid, str)
        assert sid == "abc123"

    def test_comparison(self):
        from cogant.schemas.base import StableID
        a = StableID("x")
        b = StableID("x")
        assert a == b

    def test_in_set(self):
        from cogant.schemas.base import StableID
        s = {StableID("a"), StableID("b")}
        assert StableID("a") in s


class TestSemanticVersion:
    def test_valid_version(self):
        from cogant.schemas.base import SemanticVersion
        v = SemanticVersion("1.2.3")
        assert v == "1.2.3"

    def test_zero_version(self):
        from cogant.schemas.base import SemanticVersion
        v = SemanticVersion("0.0.0")
        assert v == "0.0.0"

    def test_invalid_format_raises(self):
        from cogant.schemas.base import SemanticVersion
        with pytest.raises(ValueError):
            SemanticVersion("1.2")

    def test_invalid_non_digit_raises(self):
        from cogant.schemas.base import SemanticVersion
        with pytest.raises(ValueError):
            SemanticVersion("1.2.a")

    def test_too_many_parts_raises(self):
        from cogant.schemas.base import SemanticVersion
        with pytest.raises(ValueError):
            SemanticVersion("1.2.3.4")


class TestSpan:
    def test_basic(self):
        from cogant.schemas.base import Span
        s = Span(start_line=1, start_col=0, end_line=2, end_col=10)
        assert s.start_line == 1
        assert s.end_col == 10

    def test_same_line(self):
        from cogant.schemas.base import Span
        s = Span(start_line=5, start_col=3, end_line=5, end_col=20)
        assert s.start_line == s.end_line

    def test_negative_raises(self):
        from cogant.schemas.base import Span
        with pytest.raises(Exception):
            Span(start_line=-1, start_col=0, end_line=1, end_col=0)

    def test_end_before_start_raises(self):
        from cogant.schemas.base import Span
        with pytest.raises(Exception):
            Span(start_line=5, start_col=0, end_line=3, end_col=0)


class TestEvidenceRef:
    def test_basic(self):
        from cogant.schemas.base import EvidenceRef
        ref = EvidenceRef(evidence_id="ev1", kind="source_span")
        assert ref.evidence_id == "ev1"
        assert ref.confidence == 1.0

    def test_optional_locator(self):
        from cogant.schemas.base import EvidenceRef
        ref = EvidenceRef(evidence_id="ev2", kind="ast_fact", locator="42:8")
        assert ref.locator == "42:8"

    def test_all_kinds(self):
        from cogant.schemas.base import EvidenceRef
        kinds = ["source_span", "ast_fact", "trace_event", "test_assertion", "config_entry", "commit_event"]
        for k in kinds:
            ref = EvidenceRef(evidence_id="ev", kind=k)
            assert ref.kind == k


class TestTypeInfo:
    def test_basic(self):
        from cogant.schemas.base import TypeInfo
        t = TypeInfo(base_type="str")
        assert t.base_type == "str"
        assert t.is_optional is False
        assert t.is_generic is False

    def test_generic(self):
        from cogant.schemas.base import TypeInfo
        t = TypeInfo(base_type="Dict", is_generic=True, type_parameters=["str", "int"])
        assert t.type_parameters == ["str", "int"]

    def test_collection(self):
        from cogant.schemas.base import TypeInfo
        t = TypeInfo(base_type="List", is_collection=True, collection_element_type="int")
        assert t.collection_element_type == "int"


class TestConfidenceMetric:
    def test_basic(self):
        from cogant.schemas.base import ConfidenceMetric
        m = ConfidenceMetric(score=0.9)
        assert m.score == 0.9

    def test_with_rationale(self):
        from cogant.schemas.base import ConfidenceMetric
        m = ConfidenceMetric(score=0.75, rationale="good evidence", evidence_types=["static_analysis"])
        assert m.rationale == "good evidence"
        assert "static_analysis" in m.evidence_types

    def test_boundary_values(self):
        from cogant.schemas.base import ConfidenceMetric
        low = ConfidenceMetric(score=0.0)
        high = ConfidenceMetric(score=1.0)
        assert low.score == 0.0
        assert high.score == 1.0


class TestLocationInfo:
    def test_basic(self):
        from cogant.schemas.base import LocationInfo
        loc = LocationInfo(path="/some/file.py")
        assert loc.path == "/some/file.py"

    def test_with_span(self):
        from cogant.schemas.base import LocationInfo, Span
        span = Span(start_line=1, start_col=0, end_line=5, end_col=0)
        loc = LocationInfo(path="src/main.py", span=span, language="python")
        assert loc.span.start_line == 1


class TestGenerateStableID:
    def test_deterministic(self):
        from cogant.schemas.base import generate_stable_id
        a = generate_stable_id("module:src/main.py")
        b = generate_stable_id("module:src/main.py")
        assert a == b

    def test_different_inputs(self):
        from cogant.schemas.base import generate_stable_id
        a = generate_stable_id("node_a")
        b = generate_stable_id("node_b")
        assert a != b

    def test_prefix(self):
        from cogant.schemas.base import generate_stable_id
        sid = generate_stable_id("content", prefix="node_")
        assert sid.startswith("node_")

    def test_no_prefix(self):
        from cogant.schemas.base import generate_stable_id
        sid = generate_stable_id("content")
        assert len(sid) == 12  # SHA256[:12]

    def test_returns_stable_id_type(self):
        from cogant.schemas.base import generate_stable_id, StableID
        sid = generate_stable_id("test")
        assert isinstance(sid, StableID)


# ---------------------------------------------------------------------------
# schemas/core.py
# ---------------------------------------------------------------------------

class TestNodeKindEnum:
    def test_all_values_accessible(self):
        from cogant.schemas.core import NodeKind
        assert NodeKind.FUNCTION == "function"
        assert NodeKind.CLASS == "class"
        assert NodeKind.MODULE == "module"
        assert NodeKind.REPO == "repo"
        assert NodeKind.FILE == "file"
        assert NodeKind.METHOD == "method"
        assert NodeKind.VARIABLE == "variable"

    def test_endpoint_event_param(self):
        from cogant.schemas.core import NodeKind
        assert NodeKind.ENDPOINT == "endpoint"
        assert NodeKind.EVENT == "event"
        assert NodeKind.PARAMETER == "parameter"
        assert NodeKind.RETURN_VALUE == "return_value"

    def test_data_config(self):
        from cogant.schemas.core import NodeKind
        assert NodeKind.DATA_STRUCTURE == "data_structure"
        assert NodeKind.CONFIGURATION == "configuration"
        assert NodeKind.FEATURE_FLAG == "feature_flag"

    def test_semantic_nodes(self):
        from cogant.schemas.core import NodeKind
        assert NodeKind.TEST == "test"
        assert NodeKind.ASSERTION == "assertion"
        assert NodeKind.POLICY == "policy"
        assert NodeKind.ACTION == "action"


class TestEdgeKindEnum:
    def test_structural(self):
        from cogant.schemas.core import EdgeKind
        assert EdgeKind.CONTAINS == "contains"
        assert EdgeKind.IMPORTS == "imports"
        assert EdgeKind.INHERITS == "inherits"
        assert EdgeKind.IMPLEMENTS == "implements"
        assert EdgeKind.DEPENDS_ON == "depends_on"

    def test_data_flow(self):
        from cogant.schemas.core import EdgeKind
        assert EdgeKind.READS == "reads"
        assert EdgeKind.WRITES == "writes"
        assert EdgeKind.RETURNS == "returns"
        assert EdgeKind.CALLS == "calls"

    def test_control_flow(self):
        from cogant.schemas.core import EdgeKind
        assert EdgeKind.THROWS == "throws"
        assert EdgeKind.CATCHES == "catches"
        assert EdgeKind.YIELDS == "yields"

    def test_semantic(self):
        from cogant.schemas.core import EdgeKind
        assert EdgeKind.OBSERVES == "observes"
        assert EdgeKind.MUTATES == "mutates"
        assert EdgeKind.GUARDS == "guards"
        assert EdgeKind.TRIGGERS == "triggers"

    def test_provenance(self):
        from cogant.schemas.core import EdgeKind
        assert EdgeKind.EVIDENCE_FROM_STATIC == "evidence_from_static"
        assert EdgeKind.EVIDENCE_FROM_DYNAMIC == "evidence_from_dynamic"


class TestNode:
    def test_basic(self):
        from cogant.schemas.core import Node, NodeKind
        n = Node(id="n1", kind=NodeKind.FUNCTION, name="foo", qualified_name="pkg.foo")
        assert n.id == "n1"
        assert n.kind == NodeKind.FUNCTION
        assert n.name == "foo"

    def test_hash(self):
        from cogant.schemas.core import Node, NodeKind
        n = Node(id="n1", kind=NodeKind.FUNCTION, name="foo", qualified_name="pkg.foo")
        assert hash(n) == hash("n1")

    def test_eq(self):
        from cogant.schemas.core import Node, NodeKind
        n1 = Node(id="n1", kind=NodeKind.FUNCTION, name="foo", qualified_name="pkg.foo")
        n2 = Node(id="n1", kind=NodeKind.CLASS, name="bar", qualified_name="pkg.bar")
        assert n1 == n2

    def test_neq(self):
        from cogant.schemas.core import Node, NodeKind
        n1 = Node(id="n1", kind=NodeKind.FUNCTION, name="foo", qualified_name="pkg.foo")
        n2 = Node(id="n2", kind=NodeKind.FUNCTION, name="foo", qualified_name="pkg.foo")
        assert n1 != n2

    def test_eq_non_node(self):
        from cogant.schemas.core import Node, NodeKind
        n = Node(id="n1", kind=NodeKind.FUNCTION, name="foo", qualified_name="pkg.foo")
        assert n.__eq__("not_a_node") is NotImplemented

    def test_with_metadata(self):
        from cogant.schemas.core import Node, NodeKind
        n = Node(id="n1", kind=NodeKind.CLASS, name="MyClass", qualified_name="pkg.MyClass",
                 path="src/main.py", language="python",
                 source_range={"start": 10, "end": 50},
                 metadata={"decorators": ["@dataclass"]})
        assert n.path == "src/main.py"
        assert n.language == "python"
        assert n.metadata["decorators"] == ["@dataclass"]

    def test_in_set(self):
        from cogant.schemas.core import Node, NodeKind
        n1 = Node(id="n1", kind=NodeKind.FUNCTION, name="foo", qualified_name="pkg.foo")
        n2 = Node(id="n2", kind=NodeKind.FUNCTION, name="bar", qualified_name="pkg.bar")
        s = {n1, n2}
        assert len(s) == 2


class TestEdge:
    def test_basic(self):
        from cogant.schemas.core import Edge, EdgeKind
        e = Edge(id="e1", source_id="n1", target_id="n2", kind=EdgeKind.CALLS)
        assert e.id == "e1"
        assert e.kind == EdgeKind.CALLS
        assert e.weight == 1.0

    def test_hash(self):
        from cogant.schemas.core import Edge, EdgeKind
        e = Edge(id="e1", source_id="n1", target_id="n2", kind=EdgeKind.CALLS)
        assert hash(e) == hash("e1")

    def test_eq(self):
        from cogant.schemas.core import Edge, EdgeKind
        e1 = Edge(id="e1", source_id="n1", target_id="n2", kind=EdgeKind.CALLS)
        e2 = Edge(id="e1", source_id="x", target_id="y", kind=EdgeKind.IMPORTS)
        assert e1 == e2

    def test_neq(self):
        from cogant.schemas.core import Edge, EdgeKind
        e1 = Edge(id="e1", source_id="n1", target_id="n2", kind=EdgeKind.CALLS)
        e2 = Edge(id="e2", source_id="n1", target_id="n2", kind=EdgeKind.CALLS)
        assert e1 != e2

    def test_eq_non_edge(self):
        from cogant.schemas.core import Edge, EdgeKind
        e = Edge(id="e1", source_id="n1", target_id="n2", kind=EdgeKind.CALLS)
        assert e.__eq__("not_an_edge") is NotImplemented

    def test_with_metadata(self):
        from cogant.schemas.core import Edge, EdgeKind
        e = Edge(id="e1", source_id="n1", target_id="n2", kind=EdgeKind.READS,
                 weight=2.5, metadata={"static": True},
                 evidence_sources=["ast"])
        assert e.weight == 2.5
        assert e.evidence_sources == ["ast"]


# ---------------------------------------------------------------------------
# schemas/state_space.py
# ---------------------------------------------------------------------------

def _make_type_info():
    from cogant.schemas.base import TypeInfo
    return TypeInfo(base_type="float")


class TestStateSpaceKind:
    def test_values(self):
        from cogant.schemas.state_space import StateSpaceKind
        assert StateSpaceKind.DISCRETE == "discrete"
        assert StateSpaceKind.CONTINUOUS == "continuous"
        assert StateSpaceKind.HYBRID == "hybrid"


class TestStateVariable:
    def test_basic(self):
        from cogant.schemas.state_space import StateVariable
        sv = StateVariable(var_id="v1", name="temperature", value_type=_make_type_info())
        assert sv.var_id == "v1"
        assert sv.name == "temperature"
        assert sv.is_observable is False

    def test_observable(self):
        from cogant.schemas.state_space import StateVariable
        sv = StateVariable(var_id="v2", name="speed", value_type=_make_type_info(),
                          is_observable=True, is_controllable=True)
        assert sv.is_observable is True
        assert sv.is_controllable is True

    def test_discrete_domain(self):
        from cogant.schemas.state_space import StateVariable
        sv = StateVariable(var_id="v3", name="mode", value_type=_make_type_info(),
                          is_discrete=True, domain={"values": [0, 1, 2]},
                          default_value=0)
        assert sv.is_discrete is True
        assert sv.default_value == 0


class TestObservationModality:
    def test_basic(self):
        from cogant.schemas.state_space import ObservationModality
        om = ObservationModality(modality_id="obs1", name="camera",
                                 observation_type=_make_type_info())
        assert om.modality_id == "obs1"
        assert om.name == "camera"

    def test_with_noise(self):
        from cogant.schemas.state_space import ObservationModality
        om = ObservationModality(modality_id="obs2", name="lidar",
                                 observation_type=_make_type_info(),
                                 noise_model="gaussian",
                                 noise_parameters={"stddev": 0.1},
                                 observation_frequency=100.0)
        assert om.noise_model == "gaussian"
        assert om.observation_frequency == 100.0


class TestAction:
    def test_basic(self):
        from cogant.schemas.state_space import Action
        a = Action(action_id="act1", name="retry", action_type=_make_type_info())
        assert a.action_id == "act1"
        assert a.is_deterministic is True

    def test_stochastic(self):
        from cogant.schemas.state_space import Action
        a = Action(action_id="act2", name="probe", action_type=_make_type_info(),
                  is_deterministic=False, cost=0.5)
        assert a.is_deterministic is False
        assert a.cost == 0.5


class TestTransition:
    def test_basic(self):
        from cogant.schemas.state_space import Transition
        t = Transition(transition_id="tr1")
        assert t.transition_id == "tr1"
        assert t.is_deterministic is True

    def test_full(self):
        from cogant.schemas.state_space import Transition
        t = Transition(transition_id="tr2", source_state_id="s0", target_state_id="s1",
                      trigger_action="act1", probability=0.9,
                      state_updates={"x": 1})
        assert t.source_state_id == "s0"
        assert t.probability == 0.9


class TestLikelihood:
    def test_observation(self):
        from cogant.schemas.state_space import Likelihood
        lk = Likelihood(likelihood_id="lk1", kind="observation_likelihood",
                        distribution_type="gaussian")
        assert lk.kind == "observation_likelihood"

    def test_transition(self):
        from cogant.schemas.state_space import Likelihood
        lk = Likelihood(likelihood_id="lk2", kind="transition_probability",
                        distribution_type="categorical",
                        parameters={"alpha": 1.0},
                        conditioned_on=["state_var1"])
        assert lk.distribution_type == "categorical"


class TestStateSpaceModel:
    def _make_state_space_model(self):
        from cogant.schemas.state_space import StateSpaceModel, StateSpaceKind, StateVariable
        from cogant.schemas.base import StableID
        return StateSpaceModel(
            model_id=StableID("ssm1"),
            kind=StateSpaceKind.DISCRETE,
            name="Test Model",
            state_variables=[
                StateVariable(var_id="v1", name="x", value_type=_make_type_info())
            ],
        )

    def test_basic(self):
        m = self._make_state_space_model()
        assert m.model_id == "ssm1"
        assert m.name == "Test Model"

    def test_with_observations_actions(self):
        from cogant.schemas.state_space import (
            StateSpaceModel, StateSpaceKind, StateVariable,
            ObservationModality, Action, Transition, Likelihood
        )
        from cogant.schemas.base import StableID
        m = StateSpaceModel(
            model_id=StableID("ssm2"),
            kind=StateSpaceKind.HYBRID,
            name="Full Model",
            state_variables=[
                StateVariable(var_id="v1", name="speed", value_type=_make_type_info()),
            ],
            observation_modalities=[
                ObservationModality(modality_id="obs1", name="cam",
                                    observation_type=_make_type_info()),
            ],
            actions=[
                Action(action_id="act1", name="brake", action_type=_make_type_info()),
            ],
            transitions=[
                Transition(transition_id="tr1", trigger_action="brake"),
            ],
            likelihoods=[
                Likelihood(likelihood_id="lk1", kind="observation_likelihood",
                           distribution_type="gaussian"),
            ],
            preferences={"goal_state": "v1=0"},
            tags=["autonomous"],
        )
        assert len(m.observation_modalities) == 1
        assert len(m.actions) == 1
        assert m.preferences is not None


# ---------------------------------------------------------------------------
# schemas/process_model.py
# ---------------------------------------------------------------------------

class TestProcessKind:
    def test_values(self):
        from cogant.schemas.process_model import ProcessKind
        assert ProcessKind.SEQUENTIAL == "sequential"
        assert ProcessKind.PARALLEL == "parallel"
        assert ProcessKind.PIPELINE == "pipeline"
        assert ProcessKind.STATE_MACHINE == "state_machine"


class TestTriggerKind:
    def test_values(self):
        from cogant.schemas.process_model import TriggerKind
        assert TriggerKind.AUTOMATIC == "automatic"
        assert TriggerKind.EVENT == "event"
        assert TriggerKind.TIME_BASED == "time_based"


class TestSideEffect:
    def test_basic(self):
        from cogant.schemas.process_model import SideEffect
        se = SideEffect(effect_id="se1", description="writes to DB",
                        effect_type="database_write")
        assert se.effect_id == "se1"
        assert se.is_persistent is False


class TestProcessStage:
    def test_basic(self):
        from cogant.schemas.process_model import ProcessStage
        ps = ProcessStage(stage_id="st1", name="parse")
        assert ps.stage_id == "st1"
        assert ps.name == "parse"

    def test_full(self):
        from cogant.schemas.process_model import ProcessStage, ProcessKind, TriggerKind, SideEffect
        se = SideEffect(effect_id="se1", description="log", effect_type="log")
        ps = ProcessStage(
            stage_id="st2", name="execute",
            kind=ProcessKind.PARALLEL,
            predecessors=["st1"],
            successors=["st3"],
            trigger_kind=TriggerKind.EVENT,
            input_parameters={"x": "int"},
            output_parameters={"y": "str"},
            side_effects=[se],
            typical_duration=0.5,
            timeout=10.0,
            error_handlers={"ValueError": "handle_value_error"},
            is_compensatable=True,
            compensation_stage_id="st_rollback",
        )
        assert ps.kind == ProcessKind.PARALLEL
        assert ps.is_compensatable is True


class TestProcessPolicy:
    def test_basic(self):
        from cogant.schemas.process_model import ProcessPolicy
        pp = ProcessPolicy(policy_id="p1", name="retry", policy_type="retry")
        assert pp.policy_id == "p1"

    def test_with_rules(self):
        from cogant.schemas.process_model import ProcessPolicy
        pp = ProcessPolicy(policy_id="p2", name="lb", policy_type="load_balancing",
                          applies_to_stages=["st1", "st2"],
                          rules=[{"max": 10}], parameters={"algo": "rr"})
        assert len(pp.rules) == 1


class TestProcessTimeline:
    def test_basic(self):
        from cogant.schemas.process_model import ProcessTimeline
        pt = ProcessTimeline(timeline_id="tl1", name="main_timeline")
        assert pt.timeline_id == "tl1"
        assert pt.time_unit == "milliseconds"

    def test_real_time(self):
        from cogant.schemas.process_model import ProcessTimeline
        pt = ProcessTimeline(timeline_id="tl2", name="rt_timeline",
                            is_real_time=True, deadline=100.0,
                            deadline_type="hard", period=10.0, jitter=1.0,
                            stage_timings={"st1": 5.0})
        assert pt.is_real_time is True
        assert pt.deadline_type == "hard"


class TestProcessModel:
    def test_basic(self):
        from cogant.schemas.process_model import ProcessModel, ProcessKind, ProcessStage
        from cogant.schemas.base import StableID
        m = ProcessModel(
            process_id=StableID("pm1"),
            name="My Pipeline",
            kind=ProcessKind.PIPELINE,
            stages=[ProcessStage(stage_id="st1", name="ingest")],
        )
        assert m.process_id == "pm1"
        assert len(m.stages) == 1

    def test_full(self):
        from cogant.schemas.process_model import (
            ProcessModel, ProcessKind, ProcessStage, ProcessPolicy,
            ProcessTimeline
        )
        from cogant.schemas.base import StableID
        m = ProcessModel(
            process_id=StableID("pm2"),
            name="Full Process",
            kind=ProcessKind.STATE_MACHINE,
            stages=[
                ProcessStage(stage_id="s1", name="start"),
                ProcessStage(stage_id="s2", name="end", predecessors=["s1"]),
            ],
            root_stage_id="s1",
            leaf_stage_ids=["s2"],
            policies=[ProcessPolicy(policy_id="p1", name="r", policy_type="retry")],
            timelines=[ProcessTimeline(timeline_id="tl1", name="t")],
            concurrency_constraints={"max": 5},
            resource_constraints={"memory_mb": 512},
            tags=["production"],
        )
        assert m.root_stage_id == "s1"
        assert len(m.policies) == 1
        assert m.tags == ["production"]


# ---------------------------------------------------------------------------
# schemas/semantic_mapping.py
# ---------------------------------------------------------------------------

class TestSemanticRole:
    def test_mdp_roles(self):
        from cogant.schemas.semantic_mapping import SemanticRole
        assert SemanticRole.HIDDEN_STATE == "hidden_state"
        assert SemanticRole.OBSERVATION == "observation"
        assert SemanticRole.ACTION == "action"
        assert SemanticRole.POLICY == "policy"

    def test_objective_roles(self):
        from cogant.schemas.semantic_mapping import SemanticRole
        assert SemanticRole.PREFERENCE == "preference"
        assert SemanticRole.UTILITY == "utility"
        assert SemanticRole.OBJECTIVE == "objective"

    def test_temporal_roles(self):
        from cogant.schemas.semantic_mapping import SemanticRole
        assert SemanticRole.TEMPORAL_INDEX == "temporal_index"
        assert SemanticRole.PROCESS_STAGE == "process_stage"
        assert SemanticRole.TRANSITION == "transition"
        assert SemanticRole.OUTCOME == "outcome"

    def test_system_roles(self):
        from cogant.schemas.semantic_mapping import SemanticRole
        assert SemanticRole.COMPONENT == "component"
        assert SemanticRole.INTERFACE == "interface"
        assert SemanticRole.CONFIGURATION == "configuration"
        assert SemanticRole.CONSTRAINT == "constraint"


class TestMappingRule:
    def test_basic(self):
        from cogant.schemas.semantic_mapping import MappingRule, SemanticRole
        mr = MappingRule(rule_type="pattern_match",
                         source_pattern="@action decorator",
                         target_role=SemanticRole.ACTION)
        assert mr.rule_type == "pattern_match"
        assert mr.priority == 100

    def test_with_transformation(self):
        from cogant.schemas.semantic_mapping import MappingRule, SemanticRole
        mr = MappingRule(rule_type="annotation",
                         source_pattern="state.*",
                         target_role=SemanticRole.HIDDEN_STATE,
                         transformation="extract_return_value",
                         priority=50)
        assert mr.transformation == "extract_return_value"


class TestSourceGraphElement:
    def test_basic(self):
        from cogant.schemas.semantic_mapping import SourceGraphElement
        from cogant.schemas.base import StableID
        el = SourceGraphElement(element_id=StableID("fn1"), element_type="node",
                                label="authenticate", element_kind="function")
        assert el.element_id == "fn1"
        assert el.element_type == "node"


class TestTargetSemanticElement:
    def test_basic(self):
        from cogant.schemas.semantic_mapping import TargetSemanticElement, SemanticRole
        el = TargetSemanticElement(semantic_id="obs_auth",
                                   role=SemanticRole.OBSERVATION,
                                   label="user_authenticated",
                                   model_type="pomdp")
        assert el.semantic_id == "obs_auth"
        assert el.role == SemanticRole.OBSERVATION


class TestReviewStatus:
    def test_values(self):
        from cogant.schemas.semantic_mapping import ReviewStatus
        assert ReviewStatus.UNREVIEWED == "unreviewed"
        assert ReviewStatus.APPROVED == "approved"
        assert ReviewStatus.REJECTED == "rejected"
        assert ReviewStatus.FLAGGED == "flagged"


class TestSemanticMapping:
    def _make_mapping(self):
        from cogant.schemas.semantic_mapping import (
            SemanticMapping, SemanticRole, SourceGraphElement,
            TargetSemanticElement, MappingRule
        )
        from cogant.schemas.base import ConfidenceMetric, StableID
        src = SourceGraphElement(element_id=StableID("fn1"), element_type="node",
                                  label="auth_check", element_kind="function")
        tgt = TargetSemanticElement(semantic_id="obs1", role=SemanticRole.OBSERVATION,
                                     label="auth_status", model_type="pomdp")
        conf = ConfidenceMetric(score=0.9)
        return SemanticMapping(
            mapping_id=StableID("map1"),
            source_graph_elements=[src],
            target_semantic_elements=[tgt],
            confidence=conf,
        )

    def test_basic(self):
        m = self._make_mapping()
        assert m.mapping_id == "map1"
        assert m.confidence.score == 0.9

    def test_review_status(self):
        from cogant.schemas.semantic_mapping import ReviewStatus
        m = self._make_mapping()
        assert m.review_status == ReviewStatus.UNREVIEWED


class TestSemanticMappingCollection:
    def test_empty(self):
        from cogant.schemas.semantic_mapping import SemanticMappingCollection
        from cogant.schemas.base import StableID
        c = SemanticMappingCollection(collection_id=StableID("col1"),
                                       program_graph_id=StableID("pg1"))
        assert c.collection_id == "col1"
        assert c.mappings == []

    def test_with_mappings(self):
        from cogant.schemas.semantic_mapping import (
            SemanticMappingCollection, SemanticMapping, SemanticRole,
            SourceGraphElement, TargetSemanticElement
        )
        from cogant.schemas.base import ConfidenceMetric, StableID
        src = SourceGraphElement(element_id=StableID("fn1"), element_type="node",
                                  label="x", element_kind="function")
        tgt = TargetSemanticElement(semantic_id="obs1", role=SemanticRole.ACTION,
                                     label="y", model_type="mdp")
        m = SemanticMapping(mapping_id=StableID("m1"), source_graph_elements=[src],
                            target_semantic_elements=[tgt],
                            confidence=ConfidenceMetric(score=0.8))
        c = SemanticMappingCollection(collection_id=StableID("col2"),
                                       program_graph_id=StableID("pg2"),
                                       mappings=[m],
                                       mapping_statistics={"total": 1})
        assert len(c.mappings) == 1


# ---------------------------------------------------------------------------
# schemas/validation.py
# ---------------------------------------------------------------------------

class TestCheckLevelStatus:
    def test_check_level(self):
        from cogant.schemas.validation import CheckLevel
        assert CheckLevel.INFO == "info"
        assert CheckLevel.WARNING == "warning"
        assert CheckLevel.ERROR == "error"

    def test_check_status(self):
        from cogant.schemas.validation import CheckStatus
        assert CheckStatus.PASSED == "passed"
        assert CheckStatus.FAILED == "failed"
        assert CheckStatus.SKIPPED == "skipped"
        assert CheckStatus.INCONCLUSIVE == "inconclusive"


class TestValidationCheck:
    def test_basic(self):
        from cogant.schemas.validation import ValidationCheck, CheckStatus
        vc = ValidationCheck(check_id="c1", name="Schema Validity",
                             check_type="schema_validity", status=CheckStatus.PASSED)
        assert vc.check_id == "c1"
        assert vc.status == CheckStatus.PASSED

    def test_failed_with_issues(self):
        from cogant.schemas.validation import ValidationCheck, CheckStatus, CheckLevel
        vc = ValidationCheck(check_id="c2", name="Integrity",
                             check_type="referential_integrity",
                             status=CheckStatus.FAILED,
                             level=CheckLevel.ERROR,
                             details="Found 3 dangling refs",
                             issues=["ref_001", "ref_002"],
                             affected_elements=["n1", "n2"],
                             recommendation="Fix references")
        assert vc.level == CheckLevel.ERROR
        assert len(vc.issues) == 2


class TestValidationMetrics:
    def test_defaults(self):
        from cogant.schemas.validation import ValidationMetrics
        m = ValidationMetrics()
        assert m.node_count == 0
        assert m.confidence_mean == 0.0

    def test_full(self):
        from cogant.schemas.validation import ValidationMetrics
        m = ValidationMetrics(
            node_count=250, edge_count=1200, mapping_count=150,
            state_variable_count=20, process_stage_count=10,
            provenance_record_count=500,
            node_provenance_coverage=0.95,
            edge_provenance_coverage=0.88,
            mapping_review_coverage=0.7,
            observable_state_coverage=0.9,
            unresolved_reference_count=3,
            unresolved_reference_fraction=0.012,
            confidence_mean=0.87, confidence_min=0.6,
            confidence_stddev=0.15,
            graph_density=0.023, average_node_degree=4.8,
            largest_strongly_connected_component_size=50,
            custom_metrics={"my_metric": 42},
        )
        assert m.node_count == 250
        assert m.custom_metrics["my_metric"] == 42


class TestValidationRecommendation:
    def test_basic(self):
        from cogant.schemas.validation import ValidationRecommendation
        r = ValidationRecommendation(recommendation_id="r1",
                                     category="coverage",
                                     title="Add provenance",
                                     description="12% of edges lack provenance")
        assert r.recommendation_id == "r1"
        assert r.priority == "medium"

    def test_critical(self):
        from cogant.schemas.validation import ValidationRecommendation
        r = ValidationRecommendation(recommendation_id="r2",
                                     category="completeness",
                                     priority="critical",
                                     title="Missing state vars",
                                     description="No state variables found",
                                     estimated_effort="large")
        assert r.priority == "critical"


class TestValidationReport:
    def test_empty(self):
        from cogant.schemas.validation import ValidationReport
        from cogant.schemas.base import StableID
        vr = ValidationReport(report_id=StableID("rpt1"), bundle_id="bnd1")
        assert vr.report_id == "rpt1"
        assert vr.is_valid is True

    def test_full(self):
        from cogant.schemas.validation import (
            ValidationReport, ValidationCheck, ValidationMetrics,
            ValidationRecommendation, CheckStatus
        )
        from cogant.schemas.base import StableID
        vc = ValidationCheck(check_id="c1", name="Test", check_type="test",
                             status=CheckStatus.PASSED)
        m = ValidationMetrics(node_count=100)
        rec = ValidationRecommendation(recommendation_id="r1", category="cov",
                                        title="T", description="D")
        vr = ValidationReport(
            report_id=StableID("rpt2"), bundle_id="bnd2",
            checks=[vc], metrics=m, recommendations=[rec],
            is_valid=False, overall_quality_score=0.75,
            summary="Some issues found", validation_config={"strict": True}
        )
        assert vr.is_valid is False
        assert vr.overall_quality_score == 0.75
        assert len(vr.checks) == 1


# ---------------------------------------------------------------------------
# schemas/provenance.py
# ---------------------------------------------------------------------------

class TestEvidenceKind:
    def test_all_kinds(self):
        from cogant.schemas.provenance import EvidenceKind
        expected = ["source_span", "ast_fact", "trace_event", "test_assertion",
                    "config_entry", "commit_event", "type_signature",
                    "static_analysis", "dataflow", "control_flow",
                    "semantic_annotation", "documentation"]
        for k in expected:
            assert EvidenceKind(k) == k


class TestProvenanceRecord:
    def test_source_span(self):
        from cogant.schemas.provenance import ProvenanceRecord, EvidenceKind
        r = ProvenanceRecord(kind=EvidenceKind.SOURCE_SPAN,
                             uri="src/auth.py",
                             element_id="fn_auth")
        assert r.kind == EvidenceKind.SOURCE_SPAN
        assert r.uri == "src/auth.py"
        assert r.confidence == 1.0

    def test_ast_fact(self):
        from cogant.schemas.provenance import ProvenanceRecord, EvidenceKind
        r = ProvenanceRecord(kind=EvidenceKind.AST_FACT, uri="src/main.py",
                             ast_node_type="FunctionDef",
                             ast_properties={"name": "main"})
        assert r.ast_node_type == "FunctionDef"

    def test_trace_event(self):
        from cogant.schemas.provenance import ProvenanceRecord, EvidenceKind
        r = ProvenanceRecord(kind=EvidenceKind.TRACE_EVENT, uri="trace://1",
                             event_name="function_call",
                             event_data={"fn": "auth"})
        assert r.event_name == "function_call"

    def test_test_assertion(self):
        from cogant.schemas.provenance import ProvenanceRecord, EvidenceKind
        r = ProvenanceRecord(kind=EvidenceKind.TEST_ASSERTION, uri="tests/test_auth.py",
                             test_name="test_auth_pass",
                             assertion_type="equals",
                             assertion_passed=True)
        assert r.assertion_passed is True

    def test_config_entry(self):
        from cogant.schemas.provenance import ProvenanceRecord, EvidenceKind
        r = ProvenanceRecord(kind=EvidenceKind.CONFIG_ENTRY, uri="config.yaml",
                             config_key="max_retries", config_value="3")
        assert r.config_key == "max_retries"

    def test_commit_event(self):
        from cogant.schemas.provenance import ProvenanceRecord, EvidenceKind
        r = ProvenanceRecord(kind=EvidenceKind.COMMIT_EVENT, uri="git://repo",
                             commit_hash="abc123", commit_author="Alice",
                             commit_message="fix: auth bug")
        assert r.commit_hash == "abc123"

    def test_with_span(self):
        from cogant.schemas.provenance import ProvenanceRecord, EvidenceKind
        from cogant.schemas.base import Span
        span = Span(start_line=10, start_col=0, end_line=10, end_col=40)
        r = ProvenanceRecord(kind=EvidenceKind.SOURCE_SPAN, uri="src/x.py",
                             span=span, excerpt="def foo():",
                             excerpt_hash="abc123",
                             generated_by="ast_visitor",
                             generator_version="1.0",
                             tags=["auth"], notes="critical function")
        assert r.span.start_line == 10
        assert r.generated_by == "ast_visitor"


class TestProvenanceStore:
    def test_empty(self):
        from cogant.schemas.provenance import ProvenanceStore
        store = ProvenanceStore()
        assert store.records == []
        assert store.evidence_index == {}

    def test_add_record(self):
        from cogant.schemas.provenance import ProvenanceStore, ProvenanceRecord, EvidenceKind
        store = ProvenanceStore()
        r = ProvenanceRecord(kind=EvidenceKind.SOURCE_SPAN, uri="src/main.py")
        store.add_record(r)
        assert len(store.records) == 1
        assert r.evidence_id in store.evidence_index
        assert "src/main.py" in store.uri_index

    def test_get_record(self):
        from cogant.schemas.provenance import ProvenanceStore, ProvenanceRecord, EvidenceKind
        store = ProvenanceStore()
        r = ProvenanceRecord(kind=EvidenceKind.AST_FACT, uri="src/x.py")
        store.add_record(r)
        fetched = store.get_record(r.evidence_id)
        assert fetched is r

    def test_get_record_missing(self):
        from cogant.schemas.provenance import ProvenanceStore
        store = ProvenanceStore()
        result = store.get_record("nonexistent_id")
        assert result is None

    def test_get_by_uri(self):
        from cogant.schemas.provenance import ProvenanceStore, ProvenanceRecord, EvidenceKind
        store = ProvenanceStore()
        r1 = ProvenanceRecord(kind=EvidenceKind.SOURCE_SPAN, uri="src/auth.py")
        r2 = ProvenanceRecord(kind=EvidenceKind.AST_FACT, uri="src/auth.py")
        r3 = ProvenanceRecord(kind=EvidenceKind.SOURCE_SPAN, uri="src/other.py")
        for r in [r1, r2, r3]:
            store.add_record(r)
        results = store.get_by_uri("src/auth.py")
        assert len(results) == 2

    def test_get_by_uri_missing(self):
        from cogant.schemas.provenance import ProvenanceStore
        store = ProvenanceStore()
        results = store.get_by_uri("nonexistent.py")
        assert results == []

    def test_get_by_kind(self):
        from cogant.schemas.provenance import ProvenanceStore, ProvenanceRecord, EvidenceKind
        store = ProvenanceStore()
        for i in range(3):
            store.add_record(ProvenanceRecord(kind=EvidenceKind.SOURCE_SPAN, uri=f"src/f{i}.py"))
        store.add_record(ProvenanceRecord(kind=EvidenceKind.AST_FACT, uri="src/x.py"))
        results = store.get_by_kind(EvidenceKind.SOURCE_SPAN)
        assert len(results) == 3

    def test_get_by_kind_missing(self):
        from cogant.schemas.provenance import ProvenanceStore, EvidenceKind
        store = ProvenanceStore()
        results = store.get_by_kind(EvidenceKind.COMMIT_EVENT)
        assert results == []

    def test_kind_index_populated(self):
        from cogant.schemas.provenance import ProvenanceStore, ProvenanceRecord, EvidenceKind
        store = ProvenanceStore()
        r = ProvenanceRecord(kind=EvidenceKind.TRACE_EVENT, uri="trace://1")
        store.add_record(r)
        assert "trace_event" in store.kind_index


# ---------------------------------------------------------------------------
# schemas/gnn_export.py
# ---------------------------------------------------------------------------

class TestGNNMetadata:
    def test_basic(self):
        from cogant.schemas.gnn_export import GNNMetadata
        m = GNNMetadata(export_id="ex1", bundle_id="bnd1")
        assert m.export_id == "ex1"
        assert m.export_version == "1.0.0"

    def test_with_framework(self):
        from cogant.schemas.gnn_export import GNNMetadata
        m = GNNMetadata(export_id="ex2", bundle_id="bnd2",
                        gnn_framework="pytorch_geometric")
        assert m.gnn_framework == "pytorch_geometric"


class TestRepositoryMetadata:
    def test_basic(self):
        from cogant.schemas.gnn_export import RepositoryMetadata
        m = RepositoryMetadata(repository_name="myrepo", primary_language="python")
        assert m.repository_name == "myrepo"
        assert m.commit_hash is None

    def test_full(self):
        from cogant.schemas.gnn_export import RepositoryMetadata
        m = RepositoryMetadata(
            repository_name="myrepo", primary_language="python",
            repository_url="https://github.com/org/repo",
            commit_hash="abc123def456",
            supported_languages=["python", "javascript"],
            analysis_scope="full"
        )
        assert m.repository_url == "https://github.com/org/repo"
        assert len(m.supported_languages) == 2


class TestSourceCoverage:
    def test_defaults(self):
        from cogant.schemas.gnn_export import SourceCoverage
        sc = SourceCoverage()
        assert sc.total_files == 0
        assert sc.coverage_percentage == 0.0

    def test_full(self):
        from cogant.schemas.gnn_export import SourceCoverage
        sc = SourceCoverage(total_files=100, total_lines=5000,
                            analyzed_files=95, analyzed_lines=4800,
                            coverage_percentage=96.0,
                            excluded_patterns=["test_*.py"])
        assert sc.coverage_percentage == 96.0


class TestGraphSection:
    def test_defaults(self):
        from cogant.schemas.gnn_export import GraphSection
        gs = GraphSection()
        assert gs.node_count == 0
        assert gs.edge_list == []

    def test_full(self):
        from cogant.schemas.gnn_export import GraphSection
        gs = GraphSection(
            node_count=10, edge_count=20,
            node_features={"x": [1.0, 2.0]},
            edge_features={"weight": 1.0},
            edge_list=[[0, 1], [1, 2]],
            node_types={0: "function", 1: "class"},
            edge_types={0: "calls"}
        )
        assert gs.node_count == 10
        assert len(gs.edge_list) == 2


class TestObservationModalitySection:
    def test_basic(self):
        from cogant.schemas.gnn_export import ObservationModalitySection
        om = ObservationModalitySection(modality_id="m1", name="cam")
        assert om.modality_id == "m1"
        assert om.observation_space_type == "continuous"


class TestActionPolicySection:
    def test_basic(self):
        from cogant.schemas.gnn_export import ActionPolicySection
        a = ActionPolicySection(action_id="a1", action_name="retry")
        assert a.action_id == "a1"
        assert a.action_space_type == "discrete"


class TestConnectionSection:
    def test_basic(self):
        from cogant.schemas.gnn_export import ConnectionSection
        c = ConnectionSection(source_node_index=0, target_node_index=1, edge_type="calls")
        assert c.edge_weight == 1.0


class TestFactorSection:
    def test_basic(self):
        from cogant.schemas.gnn_export import FactorSection
        f = FactorSection(factor_id="f1", factor_type="unary",
                          variables=["v1"], cardinalities=[2])
        assert f.factor_id == "f1"
        assert f.potentials is None


class TestTransitionStructureSection:
    def test_defaults(self):
        from cogant.schemas.gnn_export import TransitionStructureSection
        t = TransitionStructureSection()
        assert t.source_state_id is None
        assert t.transition_probability is None

    def test_full(self):
        from cogant.schemas.gnn_export import TransitionStructureSection
        t = TransitionStructureSection(source_state_id="s0", target_state_id="s1",
                                        trigger_action="act1",
                                        transition_probability=0.8)
        assert t.transition_probability == 0.8


class TestLikelihoodStructureSection:
    def test_basic(self):
        from cogant.schemas.gnn_export import LikelihoodStructureSection
        lss = LikelihoodStructureSection(kind="observation_likelihood",
                                          distribution_type="gaussian")
        assert lss.distribution_type == "gaussian"


class TestPreferenceConstraintSection:
    def test_basic(self):
        from cogant.schemas.gnn_export import PreferenceConstraintSection
        pcs = PreferenceConstraintSection(constraint_id="c1",
                                           constraint_type="safety",
                                           expression="x > 0")
        assert pcs.priority == "medium"

    def test_critical(self):
        from cogant.schemas.gnn_export import PreferenceConstraintSection
        pcs = PreferenceConstraintSection(constraint_id="c2",
                                           constraint_type="safety",
                                           expression="speed < 100",
                                           priority="critical",
                                           variables=["v_speed"])
        assert pcs.priority == "critical"


class TestTimeSettingSection:
    def test_defaults(self):
        from cogant.schemas.gnn_export import TimeSettingSection
        ts = TimeSettingSection()
        assert ts.is_continuous_time is False
        assert ts.time_unit is None

    def test_full(self):
        from cogant.schemas.gnn_export import TimeSettingSection
        ts = TimeSettingSection(is_continuous_time=False, time_unit="steps",
                                time_step=0.1, max_episode_length=1000)
        assert ts.time_step == 0.1


class TestParameterizationSection:
    def test_defaults(self):
        from cogant.schemas.gnn_export import ParameterizationSection
        ps = ParameterizationSection()
        assert ps.parameters == {}

    def test_with_data(self):
        from cogant.schemas.gnn_export import ParameterizationSection
        ps = ParameterizationSection(
            parameters={"alpha": 0.1},
            parameter_ranges={"alpha": {"min": 0.0, "max": 1.0, "default": 0.5}}
        )
        assert ps.parameters["alpha"] == 0.1


class TestOntologyMappingSection:
    def test_basic(self):
        from cogant.schemas.gnn_export import OntologyMappingSection
        om = OntologyMappingSection(mapping_id="m1", source_element_id="fn1",
                                     target_semantic_role="observation")
        assert om.confidence_score == 1.0


class TestProvenanceSection:
    def test_defaults(self):
        from cogant.schemas.gnn_export import ProvenanceSection
        ps = ProvenanceSection()
        assert ps.total_evidence_count == 0
        assert ps.provenance_coverage == 0.0


class TestConfidenceSection:
    def test_defaults(self):
        from cogant.schemas.gnn_export import ConfidenceSection
        cs = ConfidenceSection()
        assert cs.mean_confidence == 0.0
        assert cs.unresolved_elements == 0


class TestRenderingHints:
    def test_defaults(self):
        from cogant.schemas.gnn_export import RenderingHints
        rh = RenderingHints()
        assert rh.recommended_layout is None

    def test_full(self):
        from cogant.schemas.gnn_export import RenderingHints
        rh = RenderingHints(recommended_layout="force-directed",
                            node_color_scheme="by_type",
                            edge_color_scheme="by_weight",
                            node_size_metric="degree",
                            edge_width_metric="weight")
        assert rh.recommended_layout == "force-directed"


class TestValidationNotes:
    def test_defaults(self):
        from cogant.schemas.gnn_export import ValidationNotes
        vn = ValidationNotes()
        assert vn.is_valid is True
        assert vn.issues == []

    def test_with_issues(self):
        from cogant.schemas.gnn_export import ValidationNotes
        vn = ValidationNotes(is_valid=False,
                             issues=["missing_state_vars"],
                             warnings=["low_coverage"],
                             recommendations=["add provenance"])
        assert len(vn.issues) == 1
        assert len(vn.warnings) == 1


class TestGNNExportBundle:
    def _make_bundle(self):
        from cogant.schemas.gnn_export import GNNExportBundle, GNNMetadata, RepositoryMetadata
        return GNNExportBundle(
            metadata=GNNMetadata(export_id="ex1", bundle_id="bnd1"),
            repository_metadata=RepositoryMetadata(
                repository_name="myrepo", primary_language="python"
            )
        )

    def test_basic(self):
        b = self._make_bundle()
        assert b.metadata.export_id == "ex1"
        assert b.repository_metadata.repository_name == "myrepo"

    def test_defaults(self):
        b = self._make_bundle()
        assert b.graph_section.node_count == 0
        assert b.observation_modalities == []
        assert b.state_space is None

    def test_with_graph(self):
        from cogant.schemas.gnn_export import (
            GNNExportBundle, GNNMetadata, RepositoryMetadata,
            GraphSection, ConnectionSection, ObservationModalitySection,
            ActionPolicySection, FactorSection, TransitionStructureSection,
            LikelihoodStructureSection, PreferenceConstraintSection,
            OntologyMappingSection
        )
        b = GNNExportBundle(
            metadata=GNNMetadata(export_id="ex2", bundle_id="bnd2"),
            repository_metadata=RepositoryMetadata(repository_name="r", primary_language="go"),
            graph_section=GraphSection(node_count=5, edge_count=8),
            connections=[ConnectionSection(source_node_index=0,
                                           target_node_index=1, edge_type="calls")],
            observation_modalities=[ObservationModalitySection(modality_id="m1", name="obs")],
            actions_policies=[ActionPolicySection(action_id="a1", action_name="do")],
            factors=[FactorSection(factor_id="f1", factor_type="unary",
                                   variables=["v1"], cardinalities=[2])],
            transition_structure=[TransitionStructureSection()],
            likelihood_structure=[LikelihoodStructureSection(
                kind="transition_probability", distribution_type="categorical")],
            preferences_constraints=[PreferenceConstraintSection(
                constraint_id="c1", constraint_type="safety", expression="x>0")],
            ontology_mapping=[OntologyMappingSection(mapping_id="m1",
                                                      source_element_id="fn1",
                                                      target_semantic_role="obs")],
            state_space={"model_id": "ss1"},
        )
        assert b.graph_section.node_count == 5
        assert len(b.connections) == 1
        assert b.state_space is not None


# ---------------------------------------------------------------------------
# schemas/bundle.py
# ---------------------------------------------------------------------------

class TestTargetLanguage:
    def test_values(self):
        from cogant.schemas.bundle import TargetLanguage
        assert TargetLanguage.PYTHON == "python"
        assert TargetLanguage.JAVASCRIPT == "javascript"
        assert TargetLanguage.RUST == "rust"
        assert TargetLanguage.GO == "go"

    def test_all_languages(self):
        from cogant.schemas.bundle import TargetLanguage
        langs = list(TargetLanguage)
        assert len(langs) == 10


class TestTargetInfo:
    def test_basic(self):
        from cogant.schemas.bundle import TargetInfo, TargetLanguage
        ti = TargetInfo(name="myproject", version="1.0.0",
                        primary_language=TargetLanguage.PYTHON)
        assert ti.name == "myproject"
        assert ti.primary_language == TargetLanguage.PYTHON

    def test_full(self):
        from cogant.schemas.bundle import TargetInfo, TargetLanguage
        ti = TargetInfo(
            name="myproject", version="2.0.0",
            primary_language=TargetLanguage.RUST,
            supported_languages=[TargetLanguage.RUST, TargetLanguage.JAVASCRIPT],
            repository_url="https://github.com/org/repo",
            commit_hash="abc123",
            analysis_scope="public_api"
        )
        assert len(ti.supported_languages) == 2
        assert ti.commit_hash == "abc123"


class TestProvenanceOrigin:
    def test_basic(self):
        from cogant.schemas.bundle import ProvenanceOrigin
        po = ProvenanceOrigin(analyzer_name="cogant", analyzer_version="0.4.0")
        assert po.analyzer_name == "cogant"
        assert po.ingest_host is None

    def test_full(self):
        from cogant.schemas.bundle import ProvenanceOrigin
        po = ProvenanceOrigin(
            analyzer_name="cogant", analyzer_version="0.4.0",
            ingest_host="myhost.local", ingest_user="alice",
            command_line="cogant ingest repo/",
            parameters={"depth": 3}
        )
        assert po.ingest_host == "myhost.local"
        assert po.parameters["depth"] == 3
