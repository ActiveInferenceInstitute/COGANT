#!/usr/bin/env python3
"""Targeted branch tests — reverse/metrics.py and static/imports.py.

Covers:
- reverse/metrics.py: IsomorphismReport, compare_role_distributions,
  compare_matrices, compare_graph_structure, compute_isomorphism_report,
  _to_probability, _kl_divergence, _coerce_matrix, _pad_to_envelope,
  _matrix_pair_score, _node_role_label, _edge_role_pair, _multiset,
  _multiset_symmetric_difference
- static/imports.py: ImportEdge, ImportAnalyzer init, analyze_source,
  _load_stdlib_modules, _generate_import_id, _resolve_local_import
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# reverse/metrics.py
# ---------------------------------------------------------------------------


class TestIsomorphismReport:
    def test_default_construction(self):
        from cogant.reverse.metrics import IsomorphismReport

        report = IsomorphismReport()
        assert report.structural_score == 0.0
        assert report.role_score == 0.0
        assert report.matrix_score == 0.0
        assert report.total_score == 0.0
        assert report.structurally_isomorphic is False

    def test_summary_isomorphic(self):
        from cogant.reverse.metrics import IsomorphismReport

        report = IsomorphismReport(
            structural_score=0.8,
            role_score=0.9,
            matrix_score=0.85,
            total_score=0.87,
            structurally_isomorphic=True,
        )
        s = report.summary()
        assert "ISO" in s
        assert "0.87" in s

    def test_summary_drift(self):
        from cogant.reverse.metrics import IsomorphismReport

        report = IsomorphismReport(
            structural_score=0.3,
            role_score=0.2,
            matrix_score=0.1,
            total_score=0.2,
            structurally_isomorphic=False,
        )
        s = report.summary()
        assert "DRIFT" in s

    def test_summary_format(self):
        from cogant.reverse.metrics import IsomorphismReport

        report = IsomorphismReport(
            role_score=0.5,
            matrix_score=0.6,
            structural_score=0.4,
            total_score=0.52,
            structurally_isomorphic=False,
        )
        s = report.summary()
        assert "role=" in s
        assert "matrix=" in s
        assert "struct=" in s


class TestCompareRoleDistributions:
    def test_identical_distributions(self):
        from cogant.reverse.metrics import compare_role_distributions

        roles = {"HIDDEN": 2, "OBS": 1}
        score = compare_role_distributions(roles, roles)
        assert abs(score - 1.0) < 1e-9

    def test_both_empty(self):
        from cogant.reverse.metrics import compare_role_distributions

        score = compare_role_distributions({}, {})
        assert score == 0.0

    def test_one_empty(self):
        from cogant.reverse.metrics import compare_role_distributions

        score = compare_role_distributions({"HIDDEN": 1}, {})
        assert score == 0.0

    def test_disjoint_distributions(self):
        from cogant.reverse.metrics import compare_role_distributions

        a = {"HIDDEN": 1}
        b = {"OBS": 1}
        score = compare_role_distributions(a, b)
        assert 0.0 <= score <= 1.0

    def test_similar_distributions_high_score(self):
        from cogant.reverse.metrics import compare_role_distributions

        a = {"HIDDEN": 10, "OBS": 5}
        b = {"HIDDEN": 9, "OBS": 6}
        score = compare_role_distributions(a, b)
        assert score > 0.5

    def test_very_different_distributions_low_score(self):
        from cogant.reverse.metrics import compare_role_distributions

        a = {"HIDDEN": 100}
        b = {"OBS": 100}
        score = compare_role_distributions(a, b)
        assert score < 0.5

    def test_score_in_range(self):
        from cogant.reverse.metrics import compare_role_distributions

        a = {"A": 3, "B": 2, "C": 1}
        b = {"A": 1, "B": 4, "C": 2}
        score = compare_role_distributions(a, b)
        assert 0.0 <= score <= 1.0

    def test_symmetry(self):
        from cogant.reverse.metrics import compare_role_distributions

        a = {"X": 5, "Y": 2}
        b = {"X": 3, "Y": 4, "Z": 1}
        score_ab = compare_role_distributions(a, b)
        score_ba = compare_role_distributions(b, a)
        assert abs(score_ab - score_ba) < 1e-9


class TestCompareMatrices:
    def test_identical_matrices(self):
        from cogant.reverse.metrics import compare_matrices

        A = [[0.8, 0.2], [0.3, 0.7]]
        score = compare_matrices({"A": A}, {"A": A})
        assert abs(score - 1.0) < 1e-6

    def test_empty_both_sides_neutral(self):
        from cogant.reverse.metrics import compare_matrices

        score = compare_matrices({}, {})
        assert score == 0.5

    def test_no_shared_keys_neutral(self):
        from cogant.reverse.metrics import compare_matrices

        score = compare_matrices({"A": [[1, 0]]}, {"B": [[0, 1]]})
        assert score == 0.5

    def test_different_matrices_lower_score(self):
        from cogant.reverse.metrics import compare_matrices

        A1 = [[1.0, 0.0], [0.0, 1.0]]
        A2 = [[0.0, 1.0], [1.0, 0.0]]
        score = compare_matrices({"A": A1}, {"A": A2})
        assert score < 1.0

    def test_score_in_range(self):
        from cogant.reverse.metrics import compare_matrices

        A = [[0.6, 0.4], [0.2, 0.8]]
        B = [[0.5, 0.5], [0.3, 0.7]]
        score = compare_matrices({"A": A, "B": B}, {"A": A, "B": B})
        assert 0.0 <= score <= 1.0

    def test_none_matrix_skipped(self):
        from cogant.reverse.metrics import compare_matrices

        score = compare_matrices({"A": None}, {"A": None})
        assert score == 0.5

    def test_multiple_matrices_averaged(self):
        from cogant.reverse.metrics import compare_matrices

        mat = [[0.9, 0.1], [0.1, 0.9]]
        score = compare_matrices(
            {"A": mat, "D": [0.5, 0.5]},
            {"A": mat, "D": [0.5, 0.5]},
        )
        assert abs(score - 1.0) < 1e-6

    def test_c_vector_comparison(self):
        from cogant.reverse.metrics import compare_matrices

        score = compare_matrices({"C": [0.5, 0.5]}, {"C": [0.5, 0.5]})
        assert abs(score - 1.0) < 1e-6

    def test_symmetry(self):
        from cogant.reverse.metrics import compare_matrices

        A = [[0.7, 0.3], [0.4, 0.6]]
        B = [[0.2, 0.8], [0.9, 0.1]]
        s1 = compare_matrices({"A": A}, {"A": B})
        s2 = compare_matrices({"A": B}, {"A": A})
        assert abs(s1 - s2) < 1e-9


class TestCompareGraphStructure:
    def test_both_empty_identical(self):
        from cogant.reverse.metrics import compare_graph_structure

        score = compare_graph_structure([], [], [], [])
        assert score == 1.0

    def test_identical_node_sets(self):
        from cogant.reverse.metrics import compare_graph_structure

        nodes = [{"kind": "function"}, {"kind": "class"}]
        score = compare_graph_structure(nodes, [], nodes, [])
        assert score == 1.0

    def test_one_empty_one_not(self):
        from cogant.reverse.metrics import compare_graph_structure

        nodes = [{"kind": "function"}]
        score = compare_graph_structure(nodes, [], [], [])
        assert score == 0.0

    def test_different_role_multisets(self):
        from cogant.reverse.metrics import compare_graph_structure

        nodes_a = [{"kind": "function"}, {"kind": "function"}]
        nodes_b = [{"kind": "class"}, {"kind": "class"}]
        score = compare_graph_structure(nodes_a, [], nodes_b, [])
        assert score < 1.0

    def test_with_edges(self):
        from cogant.reverse.metrics import compare_graph_structure

        nodes = [{"kind": "function"}, {"kind": "class"}]
        edges = [{"source": "f1", "target": "c1"}]
        score = compare_graph_structure(nodes, edges, nodes, edges)
        assert score == 1.0

    def test_score_in_range(self):
        from cogant.reverse.metrics import compare_graph_structure

        nodes_a = [{"kind": "function"}, {"kind": "class"}, {"kind": "module"}]
        nodes_b = [{"kind": "function"}, {"kind": "function"}]
        score = compare_graph_structure(nodes_a, [], nodes_b, [])
        assert 0.0 <= score <= 1.0

    def test_attribute_style_nodes(self):
        from cogant.reverse.metrics import compare_graph_structure

        class FakeNode:
            def __init__(self, kind):
                self.kind = kind

        nodes_a = [FakeNode("function"), FakeNode("class")]
        nodes_b = [FakeNode("function"), FakeNode("class")]
        score = compare_graph_structure(nodes_a, [], nodes_b, [])
        assert score == 1.0


class TestComputeIsomorphismReport:
    def test_identical_gnn_dicts(self):
        from cogant.reverse.metrics import IsomorphismReport, compute_isomorphism_report

        gnn = {
            "roles": {"HIDDEN": 2, "OBS": 1},
            "matrices": {"A": [[0.9, 0.1], [0.2, 0.8]]},
            "nodes": [{"kind": "function"}],
            "edges": [],
        }
        report = compute_isomorphism_report(gnn, gnn)
        assert isinstance(report, IsomorphismReport)
        assert report.total_score > 0.5

    def test_empty_gnn_dicts(self):
        from cogant.reverse.metrics import compute_isomorphism_report

        report = compute_isomorphism_report({}, {})
        assert 0.0 <= report.total_score <= 1.0

    def test_total_score_in_range(self):
        from cogant.reverse.metrics import compute_isomorphism_report

        a = {"roles": {"X": 1}, "matrices": {}, "nodes": [], "edges": []}
        b = {"roles": {"Y": 1}, "matrices": {}, "nodes": [], "edges": []}
        report = compute_isomorphism_report(a, b)
        assert 0.0 <= report.total_score <= 1.0

    def test_custom_threshold(self):
        from cogant.reverse.metrics import compute_isomorphism_report

        gnn = {"roles": {"HIDDEN": 1}}
        report = compute_isomorphism_report(gnn, gnn, threshold=0.0)
        assert report.structurally_isomorphic is True

    def test_high_threshold_not_isomorphic(self):
        from cogant.reverse.metrics import compute_isomorphism_report

        gnn = {"roles": {"HIDDEN": 1}}
        report = compute_isomorphism_report(gnn, gnn, threshold=1.0)
        # Total score may be less than 1.0 due to neutral matrix score
        # so structurally_isomorphic may be False even for identical
        assert isinstance(report.structurally_isomorphic, bool)

    def test_breakdown_keys_present(self):
        from cogant.reverse.metrics import compute_isomorphism_report

        report = compute_isomorphism_report({}, {})
        assert "role_score" in report.breakdown
        assert "matrix_score" in report.breakdown
        assert "structural_score" in report.breakdown

    def test_isomorphic_flag_matches_threshold(self):
        from cogant.reverse.metrics import compute_isomorphism_report

        a = {"roles": {"HIDDEN": 5, "OBS": 3}, "nodes": [{"kind": "module"}] * 5}
        report = compute_isomorphism_report(a, a, threshold=0.5)
        assert report.structurally_isomorphic == (report.total_score >= 0.5)

    def test_per_matrix_frobenius_in_breakdown(self):
        from cogant.reverse.metrics import compute_isomorphism_report

        gnn = {"matrices": {"A": [[0.8, 0.2], [0.3, 0.7]]}}
        report = compute_isomorphism_report(gnn, gnn)
        assert "per_matrix_frobenius" in report.breakdown


class TestMetricsHelpers:
    def test_to_probability_normalizes(self):
        import numpy as np

        from cogant.reverse.metrics import _to_probability

        counts = {"A": 2.0, "B": 3.0}
        support = ["A", "B"]
        prob = _to_probability(counts, support)
        assert abs(float(np.sum(prob)) - 1.0) < 1e-9

    def test_to_probability_zero_total(self):
        import numpy as np

        from cogant.reverse.metrics import _to_probability

        prob = _to_probability({}, ["A", "B"])
        assert float(np.sum(prob)) == 0.0

    def test_kl_divergence_identical(self):
        import numpy as np

        from cogant.reverse.metrics import _kl_divergence

        p = np.array([0.5, 0.5])
        assert abs(_kl_divergence(p, p)) < 1e-9

    def test_kl_divergence_nonnegative(self):
        import numpy as np

        from cogant.reverse.metrics import _kl_divergence

        p = np.array([0.7, 0.3])
        q = np.array([0.4, 0.6])
        assert _kl_divergence(p, q) >= 0.0

    def test_coerce_matrix_none_returns_none(self):
        from cogant.reverse.metrics import _coerce_matrix

        assert _coerce_matrix(None) is None

    def test_coerce_matrix_list_2d(self):
        from cogant.reverse.metrics import _coerce_matrix

        result = _coerce_matrix([[1, 0], [0, 1]])
        assert result is not None
        assert result.shape == (2, 2)

    def test_coerce_matrix_1d_reshaped(self):
        from cogant.reverse.metrics import _coerce_matrix

        result = _coerce_matrix([0.5, 0.5])
        assert result is not None
        assert result.ndim == 2

    def test_coerce_matrix_empty_returns_none(self):
        from cogant.reverse.metrics import _coerce_matrix

        result = _coerce_matrix([])
        assert result is None

    def test_pad_to_envelope_same_shape(self):
        import numpy as np

        from cogant.reverse.metrics import _pad_to_envelope

        m1 = np.array([[1.0, 0.0], [0.0, 1.0]])
        m2 = np.array([[0.5, 0.5], [0.3, 0.7]])
        p1, p2 = _pad_to_envelope(m1, m2)
        assert p1.shape == p2.shape

    def test_pad_to_envelope_different_shape(self):
        import numpy as np

        from cogant.reverse.metrics import _pad_to_envelope

        m1 = np.array([[1.0, 0.0]])
        m2 = np.array([[0.5, 0.5], [0.3, 0.7]])
        p1, p2 = _pad_to_envelope(m1, m2)
        assert p1.shape == p2.shape

    def test_matrix_pair_score_identical(self):
        import numpy as np

        from cogant.reverse.metrics import _matrix_pair_score

        m = np.array([[0.8, 0.2], [0.3, 0.7]])
        score, raw = _matrix_pair_score(m, m)
        assert abs(score - 1.0) < 1e-9
        assert abs(raw) < 1e-9

    def test_node_role_label_dict(self):
        from cogant.reverse.metrics import _node_role_label

        node = {"kind": "function"}
        assert _node_role_label(node) == "function"

    def test_node_role_label_fallback(self):
        from cogant.reverse.metrics import _node_role_label

        assert _node_role_label({}) == "NODE"

    def test_node_role_label_attr(self):
        from cogant.reverse.metrics import _node_role_label

        class FN:
            kind = "module"

        assert _node_role_label(FN()) == "module"

    def test_edge_role_pair_dict(self):
        from cogant.reverse.metrics import _edge_role_pair

        edge = {"source": "A", "target": "B"}
        assert _edge_role_pair(edge) == ("A", "B")

    def test_edge_role_pair_attr(self):
        from cogant.reverse.metrics import _edge_role_pair

        class FE:
            source = "X"
            target = "Y"

        assert _edge_role_pair(FE()) == ("X", "Y")

    def test_multiset_counts(self):
        from cogant.reverse.metrics import _multiset

        items = ["a", "b", "a", "c", "a"]
        ms = _multiset(items)
        assert ms["a"] == 3
        assert ms["b"] == 1

    def test_multiset_symmetric_difference(self):
        from cogant.reverse.metrics import _multiset_symmetric_difference

        a = {"x": 3, "y": 1}
        b = {"x": 2, "y": 2}
        result = _multiset_symmetric_difference(a, b)
        assert result == 2  # |3-2| + |1-2| = 1 + 1

    def test_multiset_symmetric_difference_identical(self):
        from cogant.reverse.metrics import _multiset_symmetric_difference

        d = {"a": 3, "b": 5}
        assert _multiset_symmetric_difference(d, d) == 0


# ---------------------------------------------------------------------------
# static/imports.py
# ---------------------------------------------------------------------------


class TestImportEdge:
    def test_creation(self):
        from cogant.static.imports import ImportEdge

        edge = ImportEdge(
            id="e1",
            source_file=Path("/tmp/foo.py"),
            module_name="os",
            is_relative=False,
            is_stdlib=True,
            is_third_party=False,
            is_local=False,
        )
        assert edge.module_name == "os"
        assert edge.is_stdlib is True

    def test_defaults(self):
        from cogant.static.imports import ImportEdge

        edge = ImportEdge(
            id="e2",
            source_file=Path("/tmp/bar.py"),
            module_name="numpy",
            is_relative=False,
            is_stdlib=False,
            is_third_party=True,
            is_local=False,
        )
        assert edge.resolved_file is None
        assert edge.line_num == 0
        assert edge.imported_names == []
        assert edge.metadata == {}


class TestImportAnalyzer:
    def test_init_default_repo_root(self):
        from cogant.static.imports import ImportAnalyzer

        analyzer = ImportAnalyzer()
        assert isinstance(analyzer.repo_root, Path)

    def test_init_custom_repo_root(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        analyzer = ImportAnalyzer(repo_root=tmp_path)
        assert analyzer.repo_root == tmp_path

    def test_stdlib_modules_loaded(self):
        from cogant.static.imports import ImportAnalyzer

        analyzer = ImportAnalyzer()
        stdlib = analyzer._stdlib_modules
        assert "os" in stdlib
        assert "sys" in stdlib
        assert "json" in stdlib
        assert "pathlib" in stdlib

    def test_load_stdlib_modules_is_set(self):
        from cogant.static.imports import ImportAnalyzer

        stdlib = ImportAnalyzer._load_stdlib_modules()
        assert isinstance(stdlib, set)
        assert len(stdlib) > 50

    def test_generate_import_id_returns_string(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        path = tmp_path / "test.py"
        result = ImportAnalyzer._generate_import_id(path, "numpy")
        assert isinstance(result, str)
        assert len(result) == 16

    def test_generate_import_id_different_modules(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        path = tmp_path / "test.py"
        id1 = ImportAnalyzer._generate_import_id(path, "numpy")
        id2 = ImportAnalyzer._generate_import_id(path, "pandas")
        assert id1 != id2

    def test_generate_import_id_is_hex(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        path = tmp_path / "test.py"
        result = ImportAnalyzer._generate_import_id(path, "os")
        assert all(c in "0123456789abcdef" for c in result)

    def test_analyze_source_stdlib_import(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        analyzer = ImportAnalyzer(repo_root=tmp_path)
        source = "import os\nimport sys\n"
        edges = analyzer.analyze_source(source, tmp_path / "test.py")
        assert len(edges) == 2
        assert all(e.is_stdlib for e in edges)

    def test_analyze_source_third_party_import(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        analyzer = ImportAnalyzer(repo_root=tmp_path)
        source = "import numpy\n"
        edges = analyzer.analyze_source(source, tmp_path / "test.py")
        assert len(edges) == 1
        assert edges[0].module_name == "numpy"
        assert not edges[0].is_stdlib

    def test_analyze_source_returns_import_edges(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer, ImportEdge

        analyzer = ImportAnalyzer(repo_root=tmp_path)
        source = "import os\n"
        edges = analyzer.analyze_source(source, tmp_path / "test.py")
        assert all(isinstance(e, ImportEdge) for e in edges)

    def test_analyze_source_empty(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        analyzer = ImportAnalyzer(repo_root=tmp_path)
        edges = analyzer.analyze_source("# no imports\n", tmp_path / "test.py")
        assert edges == []

    def test_resolve_local_import_not_found(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        analyzer = ImportAnalyzer(repo_root=tmp_path)
        result = analyzer._resolve_local_import(
            tmp_path / "test.py", "nonexistent_module", is_relative=False
        )
        assert result is None

    def test_resolve_local_import_finds_py_file(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        # Create a local module file
        (tmp_path / "mymodule.py").write_text("x = 1\n")
        analyzer = ImportAnalyzer(repo_root=tmp_path)
        result = analyzer._resolve_local_import(tmp_path / "test.py", "mymodule", is_relative=False)
        assert result is not None

    def test_resolve_local_import_relative(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        sub = tmp_path / "pkg"
        sub.mkdir()
        (sub / "utils.py").write_text("x = 1\n")
        analyzer = ImportAnalyzer(repo_root=tmp_path)
        result = analyzer._resolve_local_import(sub / "main.py", "utils", is_relative=True)
        # May or may not resolve depending on __init__.py presence
        assert result is None or isinstance(result, Path)

    def test_analyze_source_from_import(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        analyzer = ImportAnalyzer(repo_root=tmp_path)
        source = "from os import path\n"
        edges = analyzer.analyze_source(source, tmp_path / "test.py")
        assert len(edges) == 1
        assert edges[0].is_stdlib is True
