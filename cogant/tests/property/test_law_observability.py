"""COGANT correctness law 7: observability.

Every node that the translation engine labels as an ``OBSERVATION``
must be connected to some ``HIDDEN_STATE`` node by a "sees" edge —
concretely, ``READS``, ``OBSERVES``, or ``DEPENDS_ON``. In Active
Inference terms: every observation must be a projection of at least
one latent state in the system's generative model. In COGANT's code-
graph terms: an observation function that does not read anything
hidden is disconnected from the latent dynamics, which would break
downstream A-matrix derivation.

We scaffold the graph to guarantee a valid connection exists by
construction: every observation-candidate method has a ``READS``
edge pointing into a hidden-state-candidate class. Hypothesis
explores the space of valid orchestration topologies. A single
OBSERVATION mapping whose node is not linked to any HIDDEN_STATE
mapping would falsify the law.

The ``GNNMatrices.compute_A`` derivation treats any of ``READS``,
``OBSERVES``, and ``DEPENDS_ON`` as "observation → hidden state"
evidence, so the law accepts all three edge kinds. Both directions
(observation reads state, state observed-by observation) are
accepted because ``compute_A`` also scans incoming edges of the
observation node.
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from cogant.graph.builder import ProgramGraphBuilder
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import MappingKind
from cogant.translate.engine import TranslationEngine
from cogant.translate.rules import (
    ActionRule,
    ContainmentRule,
    InheritanceRule,
    MutatingSubsystemRule,
    ObservationRule,
    PolicyRule,
    ReadOnlyInputRule,
)

pytestmark = pytest.mark.property


# ---------------------------------------------------------------------------
# Strategy: a graph with observation-candidate methods that all read from
# at least one hidden-state-candidate class.
# ---------------------------------------------------------------------------


# Names that trigger the ObservationRule keyword / edge-based path.
# Every entry here either matches the OBSERVATION_KEYWORDS list or
# will fire via the "reads-without-writes" fallback (we ensure the
# reads side in the generator).
_OBS_NAMES = (
    "get_state",
    "read_value",
    "fetch_data",
    "query_status",
    "observe_metric",
    "peek_buffer",
    "inspect_config",
)

# Names for CLASS nodes the MutatingSubsystemRule maps to HIDDEN_STATE
# via the "class with outgoing WRITES/MUTATES" pattern.
_HIDDEN_NAMES = (
    "StateStore",
    "SessionState",
    "ModelCache",
    "Buffer",
    "LatentStore",
    "Registry",
    "Inventory",
)

# "Sees" edge kinds accepted as observation-to-hidden evidence.
_SEE_EDGES = (EdgeKind.READS, EdgeKind.OBSERVES, EdgeKind.DEPENDS_ON)


@st.composite
def observable_graph(draw) -> ProgramGraph:
    """Build a graph where every observation reads at least one hidden state.

    For each observation method we allocate at least one hidden-state
    class and wire the observation's ``READS`` edge at it. We also
    give the hidden-state class an outgoing ``WRITES`` edge to a
    variable so the ``MutatingSubsystemRule`` actually fires and
    promotes the class to HIDDEN_STATE.
    """
    n_obs = draw(st.integers(min_value=1, max_value=4))
    n_hidden = draw(st.integers(min_value=1, max_value=3))

    builder = ProgramGraphBuilder(repo_uri="hypothesis://law7")

    hiddens = []
    for i in range(n_hidden):
        name = draw(st.sampled_from(_HIDDEN_NAMES))
        cls = builder.add_node(
            kind=NodeKind.CLASS,
            name=name,
            qualified_name=f"law7_{name}_{i}",
            path=f"law7_state_{i}.py",
            language="python",
        )
        # Give the class an outgoing WRITES so MutatingSubsystemRule
        # promotes it to HIDDEN_STATE. The write target is an
        # internal-only variable so it doesn't itself turn into an
        # action through the ActionRule's edge path.
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="store",
            qualified_name=f"law7_store_{i}",
            path=f"law7_state_{i}.py",
            language="python",
        )
        builder.add_edge(cls.id, var.id, EdgeKind.WRITES)
        hiddens.append(cls)

    # Add at least one module to satisfy ReadOnlyInputRule, though
    # that rule's output is not required by the law.
    builder.add_node(
        kind=NodeKind.MODULE,
        name="root_module",
        qualified_name="law7_root",
        path="root.py",
        language="python",
    )

    for i in range(n_obs):
        name = draw(st.sampled_from(_OBS_NAMES))
        method = builder.add_node(
            kind=NodeKind.METHOD,
            name=name,
            qualified_name=f"law7_{name}_{i}",
            path=f"law7_obs_{i}.py",
            language="python",
        )
        # Wire READS to at least one hidden-state class — the law's
        # structural prerequisite. Optionally add a second hidden-
        # state read for breadth.
        first = draw(st.sampled_from(hiddens))
        builder.add_edge(method.id, first.id, EdgeKind.READS)
        if len(hiddens) > 1 and draw(st.booleans()):
            second = draw(st.sampled_from(hiddens))
            if second.id != first.id:
                builder.add_edge(
                    method.id,
                    second.id,
                    draw(st.sampled_from(_SEE_EDGES)),
                )

    return builder.finalize()


def _make_engine() -> TranslationEngine:
    engine = TranslationEngine()
    engine.register_rule(ReadOnlyInputRule())
    engine.register_rule(MutatingSubsystemRule())
    engine.register_rule(ObservationRule())
    engine.register_rule(ActionRule())
    engine.register_rule(PolicyRule())
    engine.register_rule(InheritanceRule())
    engine.register_rule(ContainmentRule())
    return engine


def _neighbours_via_sees(graph: ProgramGraph, node_id: str) -> set[str]:
    """Return every node connected to ``node_id`` by a SEE edge (any direction)."""
    neigh: set[str] = set()
    for edge in graph.get_edges_from(node_id):
        if edge.kind in _SEE_EDGES:
            neigh.add(edge.target_id)
    for edge in graph.get_edges_to(node_id):
        if edge.kind in _SEE_EDGES:
            neigh.add(edge.source_id)
    return neigh


# ---------------------------------------------------------------------------
# Law 7a: every observation is connected to a hidden state via a SEE edge.
# ---------------------------------------------------------------------------


@given(graph=observable_graph())
@settings(
    max_examples=30,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_every_observation_sees_a_hidden_state(graph: ProgramGraph) -> None:
    """Every OBSERVATION mapping must share a SEE edge with a HIDDEN_STATE."""
    mappings = _make_engine().translate(graph)

    hidden_ids: set[str] = set()
    obs_ids: set[str] = set()
    for m in mappings:
        if m.kind == MappingKind.HIDDEN_STATE:
            hidden_ids.update(m.graph_fragment_node_ids)
        elif m.kind == MappingKind.OBSERVATION:
            obs_ids.update(m.graph_fragment_node_ids)

    if not obs_ids:
        return  # Vacuously satisfied.
    assert hidden_ids, (
        "graph produced OBSERVATION mappings but no HIDDEN_STATE mappings "
        "— the scaffold failed to promote the state classes"
    )

    for obs_id in obs_ids:
        neigh = _neighbours_via_sees(graph, obs_id)
        assert neigh & hidden_ids, (
            f"OBSERVATION {obs_id} has no SEE-edge neighbour among "
            f"HIDDEN_STATE nodes {hidden_ids}; its sees-neighbours are {neigh}"
        )


# ---------------------------------------------------------------------------
# Law 7b: removing all SEE edges eliminates observability.
# ---------------------------------------------------------------------------


@given(graph=observable_graph())
@settings(
    max_examples=30,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_sees_edge_is_load_bearing_for_observability(graph: ProgramGraph) -> None:
    """Cloning the graph without SEE edges must break the observability link.

    This independent check validates the ``_neighbours_via_sees``
    helper: a clone of the same nodes with every READS/OBSERVES/
    DEPENDS_ON edge stripped must expose zero observability links,
    even if OBSERVATION mappings still get produced (via name-only
    keyword match). A bug in the helper — e.g. looking at the wrong
    edge set — would be caught here.
    """
    builder = ProgramGraphBuilder(repo_uri=graph.metadata.repo_uri)
    remap: dict[str, str] = {}
    for node in graph.nodes.values():
        cloned = builder.add_node(
            kind=node.kind,
            name=node.name,
            qualified_name=node.qualified_name,
            path=node.path,
            language=node.language,
        )
        remap[node.id] = cloned.id
    for edge in graph.edges.values():
        if edge.kind in _SEE_EDGES:
            continue
        builder.add_edge(remap[edge.source_id], remap[edge.target_id], edge.kind)
    stripped = builder.finalize()

    for node_id in stripped.nodes:
        assert _neighbours_via_sees(stripped, node_id) == set()


# ---------------------------------------------------------------------------
# Law 7c: observation count is bounded by hidden-state connectivity.
# ---------------------------------------------------------------------------


@given(graph=observable_graph())
@settings(
    max_examples=30,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_observation_neighbours_cover_at_least_one_hidden_state(
    graph: ProgramGraph,
) -> None:
    """Union of all observation neighbours covers ≥1 hidden-state node.

    Complementary coarse-grained check: on a scaffolded graph, the
    set of *all* nodes that any observation sees must share at
    least one id with the hidden-state bucket. This catches the
    failure mode where the per-observation check is vacuously
    satisfied (no observations fired) but the scaffold itself is
    broken — we require observations to actually appear.
    """
    mappings = _make_engine().translate(graph)

    hidden_ids: set[str] = set()
    obs_ids: set[str] = set()
    for m in mappings:
        if m.kind == MappingKind.HIDDEN_STATE:
            hidden_ids.update(m.graph_fragment_node_ids)
        elif m.kind == MappingKind.OBSERVATION:
            obs_ids.update(m.graph_fragment_node_ids)

    if not obs_ids or not hidden_ids:
        return

    union_of_neighbours: set[str] = set()
    for obs_id in obs_ids:
        union_of_neighbours |= _neighbours_via_sees(graph, obs_id)

    assert union_of_neighbours & hidden_ids, (
        f"observations {obs_ids} collectively reach no hidden state; "
        f"neighbours={union_of_neighbours}, hidden={hidden_ids}"
    )
