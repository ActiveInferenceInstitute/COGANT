"""Tests for PDFExporter — all six previously-stub methods now produce real PDFs."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Minimal stand-ins for cogant domain objects (avoid heavy pipeline deps)
# ---------------------------------------------------------------------------

@dataclass
class _FakeNode:
    id: str
    kind: str
    name: str


@dataclass
class _FakeEdge:
    id: str
    source_id: str
    target_id: str
    kind: str


@dataclass
class _FakeProgramGraph:
    nodes: dict[str, _FakeNode] = field(default_factory=dict)
    edges: dict[str, _FakeEdge] = field(default_factory=dict)


@dataclass
class _FakeMarkovBlanket:
    internal_ids: set[str] = field(default_factory=set)
    sensory_ids: set[str] = field(default_factory=set)
    active_ids: set[str] = field(default_factory=set)
    external_ids: set[str] = field(default_factory=set)
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass
class _FakeRoundtripResult:
    role_match_score: float = 1.0
    tier: str = "ISOMORPHIC"
    forward_roles: dict[str, int] = field(default_factory=dict)
    reverse_roles: dict[str, int] = field(default_factory=dict)
    elapsed_s: float = 0.123


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def exporter():
    from cogant.viz.pdf_export import PDFExporter
    return PDFExporter()


@pytest.fixture
def small_graph():
    g = _FakeProgramGraph()
    g.nodes = {
        "n1": _FakeNode("n1", "class", "Calculator"),
        "n2": _FakeNode("n2", "method", "add"),
        "n3": _FakeNode("n3", "method", "subtract"),
        "n4": _FakeNode("n4", "module", "math_utils"),
    }
    g.edges = {
        "e1": _FakeEdge("e1", "n4", "n1", "contains"),
        "e2": _FakeEdge("e2", "n1", "n2", "contains"),
        "e3": _FakeEdge("e3", "n1", "n3", "contains"),
        "e4": _FakeEdge("e4", "n2", "n3", "calls"),
    }
    return g


@pytest.fixture
def blanket():
    return _FakeMarkovBlanket(
        internal_ids={"n1", "n2"},
        sensory_ids={"n3"},
        active_ids={"n4"},
        external_ids={"n5", "n6"},
        stats={"coverage": 0.85, "boundary_ratio": 0.25},
    )


@pytest.fixture
def roundtrip_result():
    return _FakeRoundtripResult(
        role_match_score=1.0,
        tier="ISOMORPHIC",
        forward_roles={"HIDDEN_STATE": 2, "OBSERVATION": 3, "ACTION": 1},
        reverse_roles={"HIDDEN_STATE": 2, "OBSERVATION": 4, "ACTION": 2, "POLICY": 1},
        elapsed_s=0.456,
    )


@pytest.fixture
def matrices_dict():
    import numpy as np
    return {
        "A": np.random.rand(4, 4),
        "B": np.random.rand(4, 4, 2),
        "C": np.random.rand(4),
        "D": np.random.rand(4),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_export_program_graph_creates_pdf(exporter, small_graph, tmp_path):
    out = str(tmp_path / "graph.pdf")
    result = exporter.export_program_graph(small_graph, out)
    assert result == out
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


@pytest.mark.unit
def test_export_program_graph_empty_graph(exporter, tmp_path):
    empty = _FakeProgramGraph()
    out = str(tmp_path / "empty_graph.pdf")
    result = exporter.export_program_graph(empty, out)
    assert result == out
    assert Path(out).exists()


@pytest.mark.unit
def test_export_program_graph_dict_input(exporter, tmp_path):
    graph_dict: dict[str, Any] = {"nodes": {}, "edges": {}}
    out = str(tmp_path / "dict_graph.pdf")
    result = exporter.export_program_graph(graph_dict, out)
    # dict doesn't have .nodes attribute so nodes_dict falls back to {}
    assert result == out
    assert Path(out).exists()


@pytest.mark.unit
def test_export_matrices_creates_pdf(exporter, matrices_dict, tmp_path):
    out = str(tmp_path / "matrices.pdf")
    result = exporter.export_matrices(matrices_dict, out)
    assert result == out
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


@pytest.mark.unit
def test_export_matrices_partial_dict(exporter, tmp_path):
    import numpy as np
    partial = {"A": np.eye(3)}
    out = str(tmp_path / "partial_matrices.pdf")
    result = exporter.export_matrices(partial, out)
    assert result == out
    assert Path(out).exists()


@pytest.mark.unit
def test_export_matrices_empty_dict(exporter, tmp_path):
    out = str(tmp_path / "empty_matrices.pdf")
    result = exporter.export_matrices({}, out)
    assert result == out
    assert Path(out).exists()


@pytest.mark.unit
def test_export_markov_blanket_creates_pdf(exporter, blanket, tmp_path):
    out = str(tmp_path / "blanket.pdf")
    result = exporter.export_markov_blanket(blanket, out)
    assert result == out
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


@pytest.mark.unit
def test_export_markov_blanket_dict_input(exporter, tmp_path):
    blanket_dict = {
        "internal_ids": ["a", "b"],
        "sensory_ids": ["c"],
        "active_ids": [],
        "external_ids": ["d", "e", "f"],
    }
    out = str(tmp_path / "blanket_dict.pdf")
    result = exporter.export_markov_blanket(blanket_dict, out)
    assert result == out
    assert Path(out).exists()


@pytest.mark.unit
def test_export_markov_blanket_empty(exporter, tmp_path):
    empty_blanket = _FakeMarkovBlanket()
    out = str(tmp_path / "empty_blanket.pdf")
    result = exporter.export_markov_blanket(empty_blanket, out)
    assert result == out
    assert Path(out).exists()


@pytest.mark.unit
def test_export_pipeline_report_with_timing(exporter, tmp_path):
    result_data = {
        "target": "myrepo",
        "stage_timings": {
            "ingest": 0.1,
            "graph": 0.3,
            "translate": 0.5,
            "validate": 0.05,
        },
        "stage_metrics": {
            "graph": {"node_count": 42, "edge_count": 87},
            "translate": {"rule_firings": 22},
        },
    }
    out = str(tmp_path / "pipeline_report.pdf")
    r = exporter.export_pipeline_report(result_data, out)
    assert r == out
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


@pytest.mark.unit
def test_export_pipeline_report_empty(exporter, tmp_path):
    out = str(tmp_path / "empty_pipeline.pdf")
    r = exporter.export_pipeline_report({}, out)
    assert r == out
    assert Path(out).exists()


@pytest.mark.unit
def test_export_roundtrip_report_creates_pdf(exporter, roundtrip_result, tmp_path):
    out = str(tmp_path / "roundtrip.pdf")
    r = exporter.export_roundtrip_report(roundtrip_result, out)
    assert r == out
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


@pytest.mark.unit
def test_export_roundtrip_report_dict_input(exporter, tmp_path):
    rt_dict = {
        "role_match_score": 0.75,
        "tier": "APPROXIMATE",
        "forward_roles": {"HIDDEN_STATE": 1},
        "reverse_roles": {"HIDDEN_STATE": 1, "OBSERVATION": 2},
        "elapsed_s": 1.0,
    }
    out = str(tmp_path / "roundtrip_dict.pdf")
    r = exporter.export_roundtrip_report(rt_dict, out)
    assert r == out
    assert Path(out).exists()


@pytest.mark.unit
def test_export_roundtrip_report_low_score(exporter, tmp_path):
    rt = _FakeRoundtripResult(
        role_match_score=0.3,
        tier="DIVERGENT",
        forward_roles={"HIDDEN_STATE": 5},
        reverse_roles={"ACTION": 2},
    )
    out = str(tmp_path / "divergent.pdf")
    r = exporter.export_roundtrip_report(rt, out)
    assert r == out
    assert Path(out).exists()


@pytest.mark.unit
def test_export_gnn_bundle_creates_pdf(exporter, tmp_path):
    @dataclass
    class _FakeBundle:
        target: str = "test_repo"
        artifacts: dict[str, Any] = field(default_factory=dict)
        stage_results: dict[str, Any] = field(default_factory=dict)
        metadata: dict[str, Any] = field(default_factory=dict)
        errors: list[str] = field(default_factory=list)

    bundle = _FakeBundle(
        target="calculator",
        metadata={"version": "0.5.0", "timestamp": "2026-04-16"},
        stage_results={
            "ingest": {"elapsed_s": 0.1},
            "translate": {"elapsed_s": 0.3},
        },
    )
    out = str(tmp_path / "bundle.pdf")
    r = exporter.export_gnn_bundle(bundle, out)
    assert r == out
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


@pytest.mark.unit
def test_export_gnn_bundle_with_mappings(exporter, tmp_path):
    @dataclass
    class _Mapping:
        kind: str

    @dataclass
    class _FakeBundle:
        target: str = "repo"
        artifacts: dict[str, Any] = field(default_factory=dict)
        stage_results: dict[str, Any] = field(default_factory=dict)
        metadata: dict[str, Any] = field(default_factory=dict)
        errors: list[str] = field(default_factory=list)

    mappings = {
        "m1": _Mapping("HIDDEN_STATE"),
        "m2": _Mapping("OBSERVATION"),
        "m3": _Mapping("ACTION"),
        "m4": _Mapping("OBSERVATION"),
    }
    bundle = _FakeBundle(
        artifacts={"_semantic_mappings": mappings},
        stage_results={"translate": {"elapsed_s": 0.2}},
    )
    out = str(tmp_path / "bundle_with_roles.pdf")
    r = exporter.export_gnn_bundle(bundle, out)
    assert r == out
    assert Path(out).exists()


@pytest.mark.unit
def test_exporter_init_no_state():
    from cogant.viz.pdf_export import PDFExporter
    e = PDFExporter()
    assert e is not None


@pytest.mark.unit
def test_export_program_graph_returns_empty_on_import_error(tmp_path, monkeypatch):
    import builtins
    real_import = builtins.__import__

    def _mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name in ("matplotlib.pyplot", "matplotlib", "networkx"):
            raise ImportError("blocked")
        return real_import(name, *args, **kwargs)

    from cogant.viz.pdf_export import PDFExporter
    exporter = PDFExporter()
    out = str(tmp_path / "fail.pdf")

    with monkeypatch.context() as m:
        m.setattr(builtins, "__import__", _mock_import)
        result = exporter.export_program_graph(object(), out)

    assert result == ""


# ---------------------------------------------------------------------------
# export_full_analysis_report
# ---------------------------------------------------------------------------

def _full_bundle() -> dict:
    import numpy as np
    return {
        "project_name": "TestProject",
        "timestamp": "2026-04-16",
        "version": "0.5.0",
        "summary_stats": {"nodes": 42, "edges": 55, "rules_fired": 18},
        "pipeline_timing": {"ingest": 0.1, "graph": 0.2, "translate": 0.5, "statespace": 0.3},
        "semantic_roles": {"HIDDEN_STATE": 5, "OBSERVATION": 3, "ACTION": 2},
        "complexity_hotspots": {"mod_a.foo": 12.0, "mod_b.bar": 8.0, "mod_c.baz": 5.0},
        "coupling_metrics": {
            "mod_a": {"abstractness": 0.3, "instability": 0.6},
            "mod_b": {"abstractness": 0.1, "instability": 0.9},
        },
        "matrices": {
            "A": np.eye(3).tolist(),
            "B": np.eye(3).tolist(),
            "C": np.zeros((2, 3)).tolist(),
            "D": np.ones((3,)).tolist(),
        },
        "markov_blanket": {
            "internal": ["n1", "n2"],
            "sensory": ["n3"],
            "active": ["n4"],
            "external": ["n5", "n6"],
        },
        "validator_score": 87.5,
        "validation_findings": ["Degraded A matrix: identity fallback used"],
    }


@pytest.fixture
def full_exporter():
    from cogant.viz.pdf_export import PDFExporter
    return PDFExporter()


@pytest.mark.unit
def test_export_full_analysis_report_creates_pdf(full_exporter, tmp_path):
    out = str(tmp_path / "full_report.pdf")
    result = full_exporter.export_full_analysis_report(_full_bundle(), out)
    assert result == out
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


@pytest.mark.unit
def test_export_full_analysis_report_empty_bundle(full_exporter, tmp_path):
    out = str(tmp_path / "full_report_empty.pdf")
    result = full_exporter.export_full_analysis_report({}, out)
    assert result == out
    assert Path(out).exists()


@pytest.mark.unit
def test_export_full_analysis_report_no_optional_keys(full_exporter, tmp_path):
    bundle = {"project_name": "MinimalProject"}
    out = str(tmp_path / "full_report_minimal.pdf")
    result = full_exporter.export_full_analysis_report(bundle, out)
    assert result == out
    assert Path(out).exists()


@pytest.mark.unit
def test_export_full_analysis_report_with_timing(full_exporter, tmp_path):
    bundle = {
        "project_name": "TimingTest",
        "pipeline_timing": {"stage1": 0.5, "stage2": 1.2, "stage3": 0.3},
        "semantic_roles": {"HIDDEN_STATE": 3, "ACTION": 1},
        "validator_score": 95.0,
    }
    out = str(tmp_path / "full_report_timing.pdf")
    result = full_exporter.export_full_analysis_report(bundle, out)
    assert result == out
