"""Wave 20 mutation-kill tests.

Tests in this file were added after running mutmut against
``py/cogant/translate/engine.py`` and ``py/cogant/markov/blanket.py``
in the Wave 20 sweep (2026-04-11). Each test targets a specific
surviving mutation and asserts real behavioural output so that the
corresponding arithmetic/boundary/comparison mutation can no longer
pass silently.

Design rules:
* No mocks, no MagicMock, no patching — build real ``ProgramGraph``
  objects and real ``SemanticMapping`` objects.
* Each test has a docstring pointing back to the mutation family it
  kills (e.g. ``"kills key_a >= key_b -> key_a > key_b"``).
* Tests are cheap: <10ms each, no I/O, deterministic.
"""

from __future__ import annotations

from cogant.markov.blanket import (
    BlanketRole,
    MarkovBlanket,
    _bidirectional_adjacency,
    partition_by_seeds,
    serialize_blanket,
)
from cogant.schemas.core import Node, NodeKind
from cogant.schemas.graph import Edge, EdgeKind, GraphMetadata, ProgramGraph
from cogant.schemas.semantic import (
    ConfidenceTier,
    MappingKind,
    SemanticMapping,
)
from cogant.translate.engine import TranslationEngine


# ---------------------------------------------------------------------------
# helpers (no mocks — real graph fabrication)
# ---------------------------------------------------------------------------


def _make_graph() -> ProgramGraph:
    return ProgramGraph(metadata=GraphMetadata(repo_uri="wave20-test"))


def _add_node(graph: ProgramGraph, node_id: str, name: str | None = None) -> Node:
    real_name = name or node_id
    node = Node(
        id=node_id,
        kind=NodeKind.FUNCTION,
        name=real_name,
        qualified_name=f"virtual.{real_name}",
        path=f"virtual/{real_name}.py",
    )
    graph.nodes[node.id] = node
    return node


def _add_edge(
    graph: ProgramGraph,
    src: str,
    tgt: str,
    kind: EdgeKind = EdgeKind.CALLS,
) -> Edge:
    edge_id = f"{src}->{tgt}:{kind.value}"
    edge = Edge(id=edge_id, source_id=src, target_id=tgt, kind=kind)
    graph.edges[edge.id] = edge
    return edge


def _mapping(
    mapping_id: str,
    node_ids: list[str],
    score: float,
    tier: ConfidenceTier = ConfidenceTier.STATIC_ONLY,
    kind: MappingKind = MappingKind.OBSERVATION,
) -> SemanticMapping:
    return SemanticMapping(
        id=mapping_id,
        kind=kind,
        graph_fragment_node_ids=node_ids,
        confidence_score=score,
        confidence_tier=tier,
        semantic_label=f"label-{mapping_id}",
        provenance="wave20-test",
    )


# ---------------------------------------------------------------------------
# TranslationEngine._resolve_conflicts mutation kills
# ---------------------------------------------------------------------------


def test_resolve_conflicts_priority_dominates_confidence() -> None:
    """Higher rule priority wins even when confidence is lower.

    Kills mutations that swap ``(priority, confidence)`` ordering, e.g.
    ``key_a >= key_b`` → ``key_a > key_b`` (ties resolving wrong way)
    and ``pri_a, score_a`` → ``score_a, pri_a`` (ordering flip).
    """
    engine = TranslationEngine()
    low_pri_high_conf = _mapping("m1", ["n1", "n2"], score=0.95)
    high_pri_low_conf = _mapping("m2", ["n2", "n3"], score=0.10)

    engine.mappings[low_pri_high_conf.id] = low_pri_high_conf
    engine.mappings[high_pri_low_conf.id] = high_pri_low_conf
    engine._rule_priority[low_pri_high_conf.id] = 0
    engine._rule_priority[high_pri_low_conf.id] = 5  # priority dominates

    engine._resolve_conflicts()

    survivors = set(engine.mappings.keys())
    assert survivors == {"m2"}, (
        "High priority mapping must win regardless of confidence. "
        f"survivors={survivors}"
    )


def test_resolve_conflicts_confidence_tiebreaker_at_equal_priority() -> None:
    """Equal priority → higher confidence wins.

    Kills the ``confidence_score`` → constant mutation and the
    ``key_a >= key_b`` → ``key_a <= key_b`` mutation.
    """
    engine = TranslationEngine()
    low = _mapping("low", ["shared"], score=0.2)
    high = _mapping("high", ["shared"], score=0.8)
    engine.mappings[low.id] = low
    engine.mappings[high.id] = high
    engine._rule_priority[low.id] = 0
    engine._rule_priority[high.id] = 0

    engine._resolve_conflicts()

    assert list(engine.mappings.keys()) == ["high"], (
        f"Expected high confidence to win, got {list(engine.mappings.keys())}"
    )


def test_resolve_conflicts_tie_breaks_deterministically_on_first_inserted() -> None:
    """Equal priority + equal score → mapping_a wins via ``>=`` comparator.

    Kills ``key_a >= key_b`` → ``key_a > key_b`` (which would flip
    the tie to mapping_b).
    """
    engine = TranslationEngine()
    # Insertion order determines (a, b) pairing in the conflict set.
    first = _mapping("aaa", ["shared"], score=0.5)
    second = _mapping("bbb", ["shared"], score=0.5)
    engine.mappings[first.id] = first
    engine.mappings[second.id] = second
    engine._rule_priority[first.id] = 0
    engine._rule_priority[second.id] = 0

    engine._resolve_conflicts()

    # With (a, b) sorted as ("aaa", "bbb") and key_a >= key_b → keep a
    assert list(engine.mappings.keys()) == ["aaa"]


def test_resolve_conflicts_no_overlap_keeps_all() -> None:
    """Non-overlapping fragments never touch the conflict resolver.

    Kills any mutation that deletes mappings unconditionally.
    """
    engine = TranslationEngine()
    a = _mapping("a", ["n1", "n2"], score=0.1)
    b = _mapping("b", ["n3", "n4"], score=0.1)
    engine.mappings[a.id] = a
    engine.mappings[b.id] = b
    engine._rule_priority[a.id] = 0
    engine._rule_priority[b.id] = 0

    engine._resolve_conflicts()

    assert set(engine.mappings.keys()) == {"a", "b"}


def test_resolve_conflicts_logs_removal_event() -> None:
    """Conflict resolution must emit a match_log entry on removal.

    Kills mutations that drop the ``_log_match`` call or change its
    event type.
    """
    engine = TranslationEngine()
    a = _mapping("a", ["x"], score=0.9)
    b = _mapping("b", ["x"], score=0.1)
    engine.mappings[a.id] = a
    engine.mappings[b.id] = b
    engine._rule_priority[a.id] = 0
    engine._rule_priority[b.id] = 0

    engine._resolve_conflicts()

    events = [e for e in engine.get_match_log() if e["event_type"] == "conflict_resolved"]
    assert len(events) == 1
    assert "removed=b" in events[0]["detail"]
    assert "kept=a" in events[0]["detail"]


# ---------------------------------------------------------------------------
# TranslationEngine.get_coverage_report mutation kills
# ---------------------------------------------------------------------------


def test_coverage_report_empty_graph_is_zero_percent() -> None:
    """Empty graph → 0.0 coverage (not crash, not 100).

    Kills mutations that flip ``if total > 0`` → ``if total >= 0``
    causing ZeroDivisionError or constant-0/100 substitutions.
    """
    engine = TranslationEngine()
    graph = _make_graph()

    report = engine.get_coverage_report(graph)

    assert report["total_nodes"] == 0
    assert report["covered_nodes"] == 0
    assert report["uncovered_nodes"] == 0
    assert report["coverage_percent"] == 0.0
    assert report["uncovered_node_ids"] == []


def test_coverage_report_partial_coverage_percentage() -> None:
    """Exactly half covered → 50.0%.

    Kills arithmetic mutations: ``len(covered) / total`` →
    ``len(covered) * total`` and ``* 100.0`` → ``* 10.0``/``/ 100.0``.
    """
    engine = TranslationEngine()
    graph = _make_graph()
    for i in range(4):
        _add_node(graph, f"n{i}")

    mapping = _mapping("m1", ["n0", "n1"], score=0.5)
    engine.mappings[mapping.id] = mapping

    report = engine.get_coverage_report(graph)

    assert report["total_nodes"] == 4
    assert report["covered_nodes"] == 2
    assert report["uncovered_nodes"] == 2
    assert report["coverage_percent"] == 50.0
    assert report["uncovered_node_ids"] == ["n2", "n3"]


def test_coverage_report_stale_mapping_ids_are_dropped() -> None:
    """Mappings referencing missing nodes do not inflate coverage.

    Kills the mutation that removes the ``covered_node_ids &= all_node_ids``
    intersection.
    """
    engine = TranslationEngine()
    graph = _make_graph()
    _add_node(graph, "real_node")

    stale = _mapping("stale", ["real_node", "ghost_node"], score=0.5)
    engine.mappings[stale.id] = stale

    report = engine.get_coverage_report(graph)

    assert report["covered_nodes"] == 1  # ghost_node filtered out
    assert report["total_nodes"] == 1
    assert report["coverage_percent"] == 100.0
    assert report["uncovered_node_ids"] == []


def test_coverage_report_full_coverage_is_100() -> None:
    """Every node covered → 100.0 exactly (not 99.9, not 0).

    Kills ``coverage_pct = ...`` → constant mutations and the round-to-2
    mutation that might shave 100 → 99.
    """
    engine = TranslationEngine()
    graph = _make_graph()
    for i in range(3):
        _add_node(graph, f"n{i}")
    mapping = _mapping("m", ["n0", "n1", "n2"], score=0.5)
    engine.mappings[mapping.id] = mapping

    report = engine.get_coverage_report(graph)

    assert report["coverage_percent"] == 100.0
    assert report["uncovered_nodes"] == 0


# ---------------------------------------------------------------------------
# TranslationEngine.get_mappings_by_kind / by_confidence mutation kills
# ---------------------------------------------------------------------------


def test_get_mappings_by_kind_filters_exactly() -> None:
    """Kind filter must compare equality, not inequality.

    Kills ``m.kind == kind`` → ``m.kind != kind`` mutation.
    """
    engine = TranslationEngine()
    obs = _mapping("obs", ["n1"], score=0.5, kind=MappingKind.OBSERVATION)
    act = _mapping("act", ["n2"], score=0.5, kind=MappingKind.ACTION)
    engine.mappings[obs.id] = obs
    engine.mappings[act.id] = act

    only_obs = engine.get_mappings_by_kind(MappingKind.OBSERVATION)
    only_act = engine.get_mappings_by_kind(MappingKind.ACTION)

    assert [m.id for m in only_obs] == ["obs"]
    assert [m.id for m in only_act] == ["act"]


def test_get_mappings_by_confidence_filters_by_tier() -> None:
    """Confidence tier filter compares tier by identity, not kind."""
    engine = TranslationEngine()
    hi = _mapping("hi", ["n1"], score=0.9, tier=ConfidenceTier.HUMAN_REVIEWED)
    lo = _mapping("lo", ["n2"], score=0.1, tier=ConfidenceTier.STATIC_ONLY)
    engine.mappings[hi.id] = hi
    engine.mappings[lo.id] = lo

    result = engine.get_mappings_by_confidence(ConfidenceTier.HUMAN_REVIEWED)
    result_lo = engine.get_mappings_by_confidence(ConfidenceTier.STATIC_ONLY)

    assert [m.id for m in result] == ["hi"]
    assert [m.id for m in result_lo] == ["lo"]


def test_get_mapping_by_id_returns_none_for_missing() -> None:
    """Missing id returns None, not raises, not returns first mapping."""
    engine = TranslationEngine()
    engine.mappings["real"] = _mapping("real", ["n1"], score=0.5)

    assert engine.get_mapping("ghost") is None
    assert engine.get_mapping("real") is not None
    assert engine.get_mapping("real").id == "real"


# ---------------------------------------------------------------------------
# TranslationEngine.get_statistics mutation kills
# ---------------------------------------------------------------------------


def test_get_statistics_counts_by_kind_and_tier() -> None:
    """Statistics group by .value and increment by 1 (not 0 or 2).

    Kills ``by_kind[kind] = by_kind.get(kind, 0) + 1`` → ``+ 0``/``+ 2``
    and the ``kind.value`` → ``kind.name`` / ``str(kind)`` mutations.
    """
    engine = TranslationEngine()
    engine.mappings["m1"] = _mapping("m1", ["a"], 0.5, ConfidenceTier.HUMAN_REVIEWED, MappingKind.OBSERVATION)
    engine.mappings["m2"] = _mapping("m2", ["b"], 0.5, ConfidenceTier.HUMAN_REVIEWED, MappingKind.OBSERVATION)
    engine.mappings["m3"] = _mapping("m3", ["c"], 0.5, ConfidenceTier.STATIC_ONLY, MappingKind.ACTION)

    stats = engine.get_statistics()

    assert stats["total_mappings"] == 3
    assert stats["mappings_by_kind"][MappingKind.OBSERVATION.value] == 2
    assert stats["mappings_by_kind"][MappingKind.ACTION.value] == 1
    assert stats["mappings_by_confidence_tier"][ConfidenceTier.HUMAN_REVIEWED.value] == 2
    assert stats["mappings_by_confidence_tier"][ConfidenceTier.STATIC_ONLY.value] == 1
    assert stats["rules_registered"] == 0


def test_get_statistics_rules_registered_counts_registrations() -> None:
    """``rules_registered`` must equal ``len(self.rules)``.

    Kills ``len(self.rules)`` → ``len(self.mappings)``.
    """

    class _NullRule:
        name = "null"
        priority = 0
        mapping_kind = MappingKind.OBSERVATION

        def matches(self, *_: object, **__: object) -> list:  # pragma: no cover
            return []

        def apply(self, *_: object, **__: object) -> None:  # pragma: no cover
            return None

    engine = TranslationEngine()
    engine.rules.append(_NullRule())  # type: ignore[arg-type]
    engine.rules.append(_NullRule())  # type: ignore[arg-type]

    stats = engine.get_statistics()

    assert stats["rules_registered"] == 2
    assert stats["total_mappings"] == 0


# ---------------------------------------------------------------------------
# TranslationEngine._log_match / get_match_log mutation kills
# ---------------------------------------------------------------------------


def test_log_match_appends_and_get_returns_copy() -> None:
    """``get_match_log`` returns a copy, not the live list.

    Kills ``return self._match_log.copy()`` → ``return self._match_log``.
    """
    engine = TranslationEngine()
    engine._log_match("evt1", "rule_a", "detail one")
    engine._log_match("evt2", "rule_b", "detail two")

    log = engine.get_match_log()
    assert len(log) == 2
    assert log[0]["event_type"] == "evt1"
    assert log[0]["rule_name"] == "rule_a"
    assert log[1]["detail"] == "detail two"

    # Mutating the returned list must not affect the engine's internal log.
    log.clear()
    assert len(engine.get_match_log()) == 2


def test_translate_clears_prior_state_on_each_call() -> None:
    """``translate`` clears mappings / match_log / rule_priority.

    Kills mutations removing ``self.mappings.clear()`` etc.
    """
    engine = TranslationEngine(max_iterations=1)
    # Seed stale state.
    engine.mappings["stale"] = _mapping("stale", ["x"], 0.5)
    engine._match_log.append({"event_type": "old", "rule_name": "x", "detail": "y"})
    engine._rule_priority["stale"] = 9

    graph = _make_graph()
    _add_node(graph, "n1")
    result = engine.translate(graph)

    assert result == []
    assert "stale" not in engine.mappings
    assert not any(e["event_type"] == "old" for e in engine.get_match_log())
    assert "stale" not in engine._rule_priority


def test_translate_max_iterations_one_still_logs_iteration_complete() -> None:
    """With no rules, iteration 1 completes and is logged exactly once.

    Kills off-by-one in ``range(1, max_iterations + 1)``.
    """
    engine = TranslationEngine(max_iterations=1)
    graph = _make_graph()
    _add_node(graph, "n")

    engine.translate(graph)

    iteration_events = [
        e for e in engine.get_match_log() if e["event_type"] == "iteration_complete"
    ]
    assert len(iteration_events) == 1
    assert "iteration=1" in iteration_events[0]["detail"]


# ---------------------------------------------------------------------------
# RuleExplanation.to_dict mutation kills
# ---------------------------------------------------------------------------


def test_rule_explanation_to_dict_preserves_all_fields() -> None:
    """``to_dict`` serializes every field, evidence is a fresh list."""
    from cogant.translate.engine import RuleExplanation

    exp = RuleExplanation(
        rule_name="r1",
        priority=3,
        fired=True,
        reason="because",
        evidence=["e1", "e2"],
        mapping_kind="observation",
    )
    doc = exp.to_dict()

    assert doc == {
        "rule_name": "r1",
        "priority": 3,
        "fired": True,
        "reason": "because",
        "evidence": ["e1", "e2"],
        "mapping_kind": "observation",
        "confidence": 0.0,
        "contradictions": [],
    }
    # evidence must be a copy, not the live list
    doc["evidence"].append("e3")
    assert exp.evidence == ["e1", "e2"]


# ---------------------------------------------------------------------------
# markov/blanket.py — _bidirectional_adjacency mutation kills
# ---------------------------------------------------------------------------


def test_bidirectional_adjacency_excludes_self_loops() -> None:
    """Self-loops (s == t) are excluded from both in and out sets.

    Kills ``if s == t: continue`` → ``if s != t: continue`` /
    ``if s == t: pass``.
    """
    graph = _make_graph()
    _add_node(graph, "a")
    _add_node(graph, "b")
    _add_edge(graph, "a", "a")  # self-loop
    _add_edge(graph, "a", "b")

    adj = _bidirectional_adjacency(graph)

    in_a, out_a = adj["a"]
    in_b, out_b = adj["b"]
    assert "a" not in in_a, "self-loop should not appear in in-adjacency"
    assert "a" not in out_a, "self-loop should not appear in out-adjacency"
    assert out_a == {"b"}
    assert in_b == {"a"}
    assert out_b == set()


def test_bidirectional_adjacency_separates_in_and_out() -> None:
    """``in_adj`` and ``out_adj`` must not be merged into one set.

    Kills ``in_adj[t].add(s)`` → ``in_adj[t].add(t)`` and the mutation
    that merges in/out into a single undirected set.
    """
    graph = _make_graph()
    _add_node(graph, "src")
    _add_node(graph, "mid")
    _add_node(graph, "dst")
    _add_edge(graph, "src", "mid")
    _add_edge(graph, "mid", "dst")

    adj = _bidirectional_adjacency(graph)

    assert adj["src"] == (set(), {"mid"})
    assert adj["mid"] == ({"src"}, {"dst"})
    assert adj["dst"] == ({"mid"}, set())


# ---------------------------------------------------------------------------
# markov/blanket.py — partition_by_seeds mutation kills
# ---------------------------------------------------------------------------


def test_partition_internal_node_has_only_seed_neighbours() -> None:
    """Pure internal: seed node with all neighbours inside seed set.

    Kills ``if not (ext_in or ext_out):`` → ``if ext_in or ext_out:``.
    """
    graph = _make_graph()
    for nid in ("s1", "s2", "s3"):
        _add_node(graph, nid)
    _add_edge(graph, "s1", "s2")
    _add_edge(graph, "s2", "s3")

    blanket = partition_by_seeds(graph, seeds={"s1", "s2", "s3"})

    assert blanket.roles["s1"] == BlanketRole.INTERNAL
    assert blanket.roles["s2"] == BlanketRole.INTERNAL
    assert blanket.roles["s3"] == BlanketRole.INTERNAL
    assert blanket.internal_ids == {"s1", "s2", "s3"}
    assert blanket.boundary_ids == set()


def test_partition_active_node_writes_out_of_system() -> None:
    """Seed node with outgoing edge to external → ACTIVE.

    Kills the ``elif ext_out:`` → ``elif ext_in:`` mutation.
    """
    graph = _make_graph()
    _add_node(graph, "seed")
    _add_node(graph, "outside")
    _add_edge(graph, "seed", "outside")  # outgoing from seed

    blanket = partition_by_seeds(graph, seeds={"seed"})

    assert blanket.roles["seed"] == BlanketRole.ACTIVE
    assert blanket.roles["outside"] == BlanketRole.EXTERNAL
    assert blanket.active_ids == {"seed"}
    assert blanket.sensory_ids == set()


def test_partition_sensory_node_reads_from_environment() -> None:
    """Seed node with only incoming external edge → SENSORY.

    Kills ``else: sensory`` → ``else: active`` mutation.
    """
    graph = _make_graph()
    _add_node(graph, "seed")
    _add_node(graph, "env")
    _add_edge(graph, "env", "seed")  # incoming to seed

    blanket = partition_by_seeds(graph, seeds={"seed"})

    assert blanket.roles["seed"] == BlanketRole.SENSORY
    assert blanket.sensory_ids == {"seed"}
    assert blanket.active_ids == set()


def test_partition_bidirectional_seed_is_active_and_tagged() -> None:
    """Seed with both in and out external edges → ACTIVE + bidirectional metadata.

    Kills mutations that flip the bidirectional branch to SENSORY and
    drop the ``bidirectional.add(node_id)`` line.
    """
    graph = _make_graph()
    _add_node(graph, "seed")
    _add_node(graph, "up")
    _add_node(graph, "down")
    _add_edge(graph, "up", "seed")
    _add_edge(graph, "seed", "down")

    blanket = partition_by_seeds(graph, seeds={"seed"})

    assert blanket.roles["seed"] == BlanketRole.ACTIVE
    assert "seed" in blanket.active_ids
    assert "seed" in blanket.metadata["bidirectional_ids"]


def test_partition_external_neighbour_is_tagged() -> None:
    """Non-seed node adjacent to a seed gets EXTERNAL + neighbour metadata.

    Kills mutation: ``if neigh & seed_set:`` → ``if not (neigh & seed_set):``.
    """
    graph = _make_graph()
    _add_node(graph, "inside")
    _add_node(graph, "touching")
    _add_node(graph, "far")
    _add_edge(graph, "inside", "touching")

    blanket = partition_by_seeds(graph, seeds={"inside"})

    assert blanket.roles["touching"] == BlanketRole.EXTERNAL
    assert "touching" in blanket.metadata["external_neighbour_ids"]
    assert "far" in blanket.roles  # role assigned
    assert blanket.roles["far"] == BlanketRole.EXTERNAL
    assert "far" not in blanket.metadata["external_neighbour_ids"]


def test_partition_seed_filtering_drops_unknown_ids() -> None:
    """Seeds not in graph.nodes are silently discarded.

    Kills ``{s for s in seeds if s in graph.nodes}`` → removing the filter.
    """
    graph = _make_graph()
    _add_node(graph, "real")

    blanket = partition_by_seeds(graph, seeds={"real", "ghost1", "ghost2"})

    assert blanket.seeds == {"real"}
    assert blanket.stats["seed_count"] == 1


def test_partition_stats_ratios_sum_to_one_modulo_rounding() -> None:
    """Internal + boundary + external ratios ≈ 1.0.

    Kills the ``/ total`` → ``/ (total + 1)`` and ``round(..., 4)`` →
    ``round(..., 0)`` arithmetic mutations.
    """
    graph = _make_graph()
    for nid in ("s", "o1", "o2", "o3"):
        _add_node(graph, nid)
    _add_edge(graph, "s", "o1")  # s becomes ACTIVE boundary
    # o2, o3 are pure external

    blanket = partition_by_seeds(graph, seeds={"s"})

    stats = blanket.stats
    total = stats["total_nodes"]
    assert total == 4
    total_ratio = stats["internal_ratio"] + stats["boundary_ratio"] + stats["external_ratio"]
    assert abs(total_ratio - 1.0) < 1e-9
    assert stats["boundary_ratio"] == round(1 / 4, 4)
    assert stats["external_ratio"] == round(3 / 4, 4)
    assert stats["internal_ratio"] == 0.0


def test_partition_total_nodes_zero_uses_one_for_division_guard() -> None:
    """Empty graph must not divide by zero — ratios default to 0.

    Kills ``total = len(graph.nodes) or 1`` → ``total = len(graph.nodes)``.
    """
    graph = _make_graph()

    blanket = partition_by_seeds(graph, seeds=set())

    stats = blanket.stats
    assert stats["total_nodes"] == 0
    assert stats["internal_ratio"] == 0.0
    assert stats["boundary_ratio"] == 0.0
    assert stats["external_ratio"] == 0.0


def test_partition_counts_match_id_set_sizes() -> None:
    """``*_count`` stats equal ``len(*_ids)`` — no off-by-one.

    Kills ``len(internal)`` → ``len(internal) + 1`` and similar.
    """
    graph = _make_graph()
    for nid in ("a", "b", "c", "d", "e"):
        _add_node(graph, nid)
    _add_edge(graph, "a", "b")  # inside seed -> still internal (both in seed)
    _add_edge(graph, "b", "c")  # boundary: b writes to c (outside)
    _add_edge(graph, "d", "a")  # external neighbour writes in — a gets sensory

    seeds = {"a", "b"}
    blanket = partition_by_seeds(graph, seeds=seeds)

    assert blanket.stats["internal_count"] == len(blanket.internal_ids)
    assert blanket.stats["sensory_count"] == len(blanket.sensory_ids)
    assert blanket.stats["active_count"] == len(blanket.active_ids)
    assert blanket.stats["external_count"] == len(blanket.external_ids)
    # sanity: every node classified exactly once
    all_assigned = (
        blanket.internal_ids
        | blanket.sensory_ids
        | blanket.active_ids
        | blanket.external_ids
    )
    assert all_assigned == set(graph.nodes.keys())


def test_partition_uses_provided_adjacency_instead_of_rebuilding() -> None:
    """Caller-supplied adjacency must be honoured without rebuild.

    Kills ``if adjacency is None:`` → ``if adjacency is not None:``.
    We supply a deliberately wrong adjacency and check the partition
    reflects the supplied data, not the real edges.
    """
    graph = _make_graph()
    _add_node(graph, "s")
    _add_node(graph, "x")
    _add_edge(graph, "s", "x")  # real edge: s writes to x

    # Lie to the partitioner: claim s has NO neighbours.
    fake_adjacency = {"s": (set(), set()), "x": (set(), set())}

    blanket = partition_by_seeds(graph, seeds={"s"}, adjacency=fake_adjacency)

    # With empty adjacency, s has no external neighbours → INTERNAL
    assert blanket.roles["s"] == BlanketRole.INTERNAL


# ---------------------------------------------------------------------------
# markov/blanket.py — MarkovBlanket.role_of / ids_by_role mutation kills
# ---------------------------------------------------------------------------


def test_role_of_defaults_to_external_for_unknown_node() -> None:
    """Unknown id must map to EXTERNAL, not None, not raise.

    Kills ``return self.roles.get(node_id, BlanketRole.EXTERNAL)`` →
    ``return self.roles[node_id]`` / ``return BlanketRole.INTERNAL``.
    """
    blanket = MarkovBlanket(roles={"known": BlanketRole.INTERNAL}, seeds={"known"})

    assert blanket.role_of("known") is BlanketRole.INTERNAL
    assert blanket.role_of("unknown") is BlanketRole.EXTERNAL


def test_ids_by_role_routes_each_role_to_correct_bucket() -> None:
    """Each role returns the matching id set.

    Kills mutations that swap the ``if role is …`` branches.
    """
    blanket = MarkovBlanket(
        roles={},
        seeds=set(),
        internal_ids={"i1"},
        sensory_ids={"s1"},
        active_ids={"a1"},
        external_ids={"e1"},
    )

    assert blanket.ids_by_role(BlanketRole.INTERNAL) == {"i1"}
    assert blanket.ids_by_role(BlanketRole.SENSORY) == {"s1"}
    assert blanket.ids_by_role(BlanketRole.ACTIVE) == {"a1"}
    assert blanket.ids_by_role(BlanketRole.EXTERNAL) == {"e1"}


def test_boundary_ids_is_union_of_sensory_and_active() -> None:
    """``boundary_ids`` = sensory ∪ active, not intersection or just one.

    Kills ``self.sensory_ids | self.active_ids`` → ``& `` / single-operand.
    """
    blanket = MarkovBlanket(
        roles={},
        seeds=set(),
        sensory_ids={"s1", "both"},
        active_ids={"a1", "both"},
    )

    assert blanket.boundary_ids == {"s1", "a1", "both"}


# ---------------------------------------------------------------------------
# markov/blanket.py — serialize_blanket mutation kills
# ---------------------------------------------------------------------------


def test_serialize_blanket_schema_version_is_one_zero_zero() -> None:
    """Schema version literal is exactly ``"1.0.0"``.

    Kills any string-constant mutation of the schema version.
    """
    graph = _make_graph()
    blanket = partition_by_seeds(graph, seeds=set())

    doc = serialize_blanket(blanket, graph)

    assert doc["schema_version"] == "1.0.0"
    assert sorted(doc["roles"].keys()) == ["active", "external", "internal", "sensory"]


def test_serialize_blanket_respects_max_nodes_per_role() -> None:
    """``max_nodes_per_role=1`` keeps exactly one id per role.

    Kills ``ids = ids[:max_nodes_per_role]`` → ``ids = ids[max_nodes_per_role:]``
    and the ``is not None`` guard flip.
    """
    graph = _make_graph()
    for nid in ("x1", "x2", "x3"):
        _add_node(graph, nid)

    blanket = partition_by_seeds(graph, seeds=set())
    doc = serialize_blanket(blanket, graph, max_nodes_per_role=1)

    assert len(doc["roles"]["external"]) == 1
    # deterministic: sorted order means "x1" wins over x2/x3
    assert doc["roles"]["external"][0]["id"] == "x1"


def test_serialize_blanket_include_rationale_flag_toggles_field() -> None:
    """``include_rationale=False`` drops the rationale key.

    Kills mutation that inverts the ``include_rationale`` flag.
    """
    graph = _make_graph()
    _add_node(graph, "n")
    blanket = partition_by_seeds(graph, seeds={"n"})
    # n is a seed with no neighbours → INTERNAL with a rationale string
    assert "n" in blanket.rationale

    with_rat = serialize_blanket(blanket, graph, include_rationale=True)
    without_rat = serialize_blanket(blanket, graph, include_rationale=False)

    internal_with = with_rat["roles"]["internal"][0]
    internal_without = without_rat["roles"]["internal"][0]
    assert internal_with["rationale"] == blanket.rationale["n"]
    assert "rationale" not in internal_without


def test_serialize_blanket_unknown_node_kind_and_name_are_none() -> None:
    """Nodes absent from the graph serialize with ``kind=None, name=None``.

    Kills the ``if node else None`` branch deletion.
    """
    graph = _make_graph()
    _add_node(graph, "real")
    # Craft a blanket that references a ghost id that is NOT in graph.nodes.
    ghost_blanket = MarkovBlanket(
        roles={"real": BlanketRole.INTERNAL, "ghost": BlanketRole.INTERNAL},
        seeds={"real"},
        internal_ids={"real", "ghost"},
    )

    doc = serialize_blanket(ghost_blanket, graph)
    records = {r["id"]: r for r in doc["roles"]["internal"]}

    assert records["real"]["kind"] == NodeKind.FUNCTION.value
    assert records["real"]["name"] == "real"
    assert records["ghost"]["kind"] is None
    assert records["ghost"]["name"] is None
    assert records["ghost"]["path"] is None


def test_serialize_blanket_ids_are_sorted_deterministically() -> None:
    """Output node lists per role are sorted by id.

    Kills ``sorted(node_ids)`` → ``list(node_ids)`` / ``sorted(..., reverse=True)``.
    """
    graph = _make_graph()
    for nid in ("z", "a", "m"):
        _add_node(graph, nid)

    blanket = partition_by_seeds(graph, seeds=set())
    doc = serialize_blanket(blanket, graph)

    ids = [r["id"] for r in doc["roles"]["external"]]
    assert ids == ["a", "m", "z"]
