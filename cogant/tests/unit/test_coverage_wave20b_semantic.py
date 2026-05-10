"""Wave 20b coverage boost: cogant.gnn.formatter.semantic missing lines.

Targets uncovered lines (123, 125-126, 129-133, 185, 210, 230, 233, 235):
- Line 123: kwargs["module_names"] when state_space metadata has markov_blanket_modules
- Lines 125-126: kwargs["mapping_kinds"] + semantic_mappings when both supplied
- Lines 129-133: exception path in MarkovBlanketExtractor.extract
- Line 185: _member_label fallback when node missing from graph
- Line 210: '... and N more' when role member count exceeds max_members (8)
- Line 230: chosen_module / module_name in blanket metadata
- Line 233: score in blanket metadata
- Line 235: trailing empty line when chosen or score
"""

from __future__ import annotations

import pytest

from cogant.gnn.formatter.semantic import _SemanticSectionsMixin
from cogant.process.extractor import ProcessModel
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.statespace.compiler import StateSpaceModel
from cogant.statespace.temporal import TimeRegime

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _Formatter(_SemanticSectionsMixin):
    """Concrete formatter that satisfies the mixin's attribute contract."""


def _empty_graph() -> ProgramGraph:
    return ProgramGraph(metadata=GraphMetadata(repo_uri="test://repo"))


def _graph_with_module() -> ProgramGraph:
    """Build a graph with one MODULE node containing several functions."""
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="test://repo"))
    mod = Node(
        id="mod1",
        kind=NodeKind.MODULE,
        name="my_module",
        qualified_name="my_module",
        path="my_module.py",
    )
    g.add_node(mod)
    for i in range(12):
        f = Node(
            id=f"fn{i}",
            kind=NodeKind.FUNCTION,
            name=f"func_{i}",
            qualified_name=f"my_module.func_{i}",
            path="my_module.py",
        )
        g.add_node(f)
        g.add_edge(
            Edge(id=f"contains_{i}", source_id="mod1", target_id=f"fn{i}", kind=EdgeKind.CONTAINS)
        )
    return g


def _make_state_space(metadata: dict | None = None) -> StateSpaceModel:
    return StateSpaceModel(
        id="ss",
        schema_name="test",
        variables={},
        observations={},
        actions={},
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
        metadata=metadata or {},
    )


def _make_formatter(graph: ProgramGraph, state_space: StateSpaceModel, mappings=None) -> _Formatter:
    fmt = _Formatter()
    fmt.graph = graph
    fmt.state_space = state_space
    fmt.process = ProcessModel(id="pm", schema_name="test", stages={}, connections={})
    fmt.mappings = mappings or {}
    return fmt


# ---------------------------------------------------------------------------
# Lines 123, 129-133: module_names path + extract raises (because empty graph
# has no module nodes matching the requested names).
# ---------------------------------------------------------------------------


def test_format_markov_blanket_with_module_names_metadata() -> None:
    """Line 123: module_names is forwarded to the extractor."""
    g = _graph_with_module()
    ss = _make_state_space(
        {
            "markov_blanket_strategy": "module",
            "markov_blanket_modules": ["my_module"],
        }
    )
    fmt = _make_formatter(g, ss)
    result = fmt._format_markov_blanket()
    assert "Markov Blanket" in result
    # module strategy populated module_names
    assert "module" in result.lower()


def test_format_markov_blanket_extract_raises_unknown_strategy() -> None:
    """Lines 129-133: MarkovBlanketExtractor.extract raises ValueError on unknown strategy."""
    g = _empty_graph()
    ss = _make_state_space({"markov_blanket_strategy": "definitely_not_a_real_strategy"})
    fmt = _make_formatter(g, ss)
    result = fmt._format_markov_blanket()
    assert "extraction unavailable" in result.lower() or "unavailable" in result.lower()


def test_format_markov_blanket_extract_raises_module_no_modules() -> None:
    """Strategy='module' without modules raises ValueError → exception path."""
    g = _empty_graph()
    ss = _make_state_space({"markov_blanket_strategy": "module"})
    # No markov_blanket_modules → kwargs["module_names"] not set → extractor.extract
    # raises ValueError at line 124 of extractor.
    fmt = _make_formatter(g, ss)
    result = fmt._format_markov_blanket()
    assert "unavailable" in result.lower()


# ---------------------------------------------------------------------------
# Lines 125-126: mapping_kinds + semantic_mappings path
# ---------------------------------------------------------------------------


def test_format_markov_blanket_with_mapping_kinds_metadata() -> None:
    """Lines 125-126: mapping_kinds + self.mappings forwarded to extractor."""
    from cogant.schemas.semantic import MappingKind

    class FakeMapping:
        def __init__(self, mapping_id: str, node_id: str, kind: MappingKind):
            self.id = mapping_id
            self.kind = kind
            self.semantic_label = mapping_id
            self.description = "test"
            self.graph_fragment_node_ids = [node_id]
            self.graph_fragment_edge_ids = []
            self.confidence_score = 0.9
            self.confidence_tier = None
            self.evidence_count = 1
            self.status = "active"

    g = _graph_with_module()
    mappings = {
        "m1": FakeMapping("m1", "fn0", MappingKind.HIDDEN_STATE),
        "m2": FakeMapping("m2", "fn1", MappingKind.HIDDEN_STATE),
    }
    ss = _make_state_space(
        {
            "markov_blanket_strategy": "mapping_kind",
            "markov_blanket_mapping_kinds": ["hidden_state"],
        }
    )
    fmt = _make_formatter(g, ss, mappings)
    result = fmt._format_markov_blanket()
    assert "Markov Blanket" in result


# ---------------------------------------------------------------------------
# Line 185: _member_label fallback when node missing from graph
# ---------------------------------------------------------------------------


def test_format_markov_blanket_member_label_unknown_node(monkeypatch) -> None:
    """Build a blanket whose internal_ids reference a node not in graph.nodes.

    Patch the extractor to inject a phantom ID into internal_ids so the
    _member_label closure falls through to line 185 (returns bare node_id).
    """
    from cogant.markov import MarkovBlanketExtractor
    from cogant.markov.blanket import MarkovBlanket

    g = _graph_with_module()
    ss = _make_state_space(
        {"markov_blanket_strategy": "module", "markov_blanket_modules": ["my_module"]}
    )
    fmt = _make_formatter(g, ss)

    real_extract = MarkovBlanketExtractor.extract

    def patched_extract(self, *args, **kwargs):
        b: MarkovBlanket = real_extract(self, *args, **kwargs)
        # Inject phantom node ID NOT in graph.nodes
        b.internal_ids.add("aaa_phantom")
        return b

    monkeypatch.setattr(MarkovBlanketExtractor, "extract", patched_extract)
    result = fmt._format_markov_blanket()
    assert "Markov Blanket" in result
    # The phantom id should be surfaced as a bare ID since graph.nodes lacks it
    assert "aaa_phantom" in result


# ---------------------------------------------------------------------------
# Line 210: '... and N more' when total > max_members
# ---------------------------------------------------------------------------


def test_format_markov_blanket_more_than_eight_members() -> None:
    """A module with 12 functions yields 12 internal members → triggers the
    '… and N more' branch (line 210) when shown > max_members = 8."""
    g = _graph_with_module()  # has 12 function nodes contained by mod1
    ss = _make_state_space(
        {"markov_blanket_strategy": "module", "markov_blanket_modules": ["my_module"]}
    )
    fmt = _make_formatter(g, ss)
    result = fmt._format_markov_blanket()
    assert "more" in result  # triggered the "… and N more" line


# ---------------------------------------------------------------------------
# Lines 230, 233, 235: chosen_module / score / trailing newline
# ---------------------------------------------------------------------------


def test_format_markov_blanket_auto_strategy_runs_to_completion() -> None:
    """Auto strategy runs without raising and yields a Markov Blanket section.

    The chosen_module / score branches are exercised via the explicit monkeypatch
    tests below; this test just confirms the auto-path completes successfully.
    """
    g = _graph_with_module()
    ss = _make_state_space()  # no metadata → defaults to "auto"
    fmt = _make_formatter(g, ss)
    result = fmt._format_markov_blanket()
    assert "Markov Blanket" in result
    assert "Partition Summary" in result


def test_format_markov_blanket_score_only_branch(monkeypatch) -> None:
    """Inject a blanket with only `score` (no `chosen_module`) to hit line 233+235."""
    from cogant.markov import MarkovBlanketExtractor
    from cogant.markov.blanket import MarkovBlanket

    g = _graph_with_module()
    ss = _make_state_space({"markov_blanket_strategy": "auto"})
    fmt = _make_formatter(g, ss)

    real_extract = MarkovBlanketExtractor.extract

    def patched_extract(self, *args, **kwargs):
        b: MarkovBlanket = real_extract(self, *args, **kwargs)
        # Drop chosen_module and module_name; keep a numeric score
        for k in ("chosen_module", "module_name"):
            b.metadata.pop(k, None)
        b.metadata["score"] = 0.42
        return b

    monkeypatch.setattr(MarkovBlanketExtractor, "extract", patched_extract)
    result = fmt._format_markov_blanket()
    assert "Cohesion score" in result
    assert "0.420" in result


def test_format_markov_blanket_chosen_only_branch(monkeypatch) -> None:
    """Inject a blanket with chosen_module but no score to hit line 230 + 235."""
    from cogant.markov import MarkovBlanketExtractor
    from cogant.markov.blanket import MarkovBlanket

    g = _graph_with_module()
    ss = _make_state_space({"markov_blanket_strategy": "auto"})
    fmt = _make_formatter(g, ss)

    real_extract = MarkovBlanketExtractor.extract

    def patched_extract(self, *args, **kwargs):
        b: MarkovBlanket = real_extract(self, *args, **kwargs)
        b.metadata.pop("score", None)
        b.metadata["chosen_module"] = "my_module"
        return b

    monkeypatch.setattr(MarkovBlanketExtractor, "extract", patched_extract)
    result = fmt._format_markov_blanket()
    assert "Chosen module" in result
    assert "my_module" in result
