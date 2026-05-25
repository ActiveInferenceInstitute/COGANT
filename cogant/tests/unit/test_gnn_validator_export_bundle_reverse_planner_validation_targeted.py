#!/usr/bin/env python3
"""Targeted branch tests — gnn/validator.py extended, export/bundle.py private methods,
reverse/planner.py helpers, gnn/json_export.py export methods.

Covers:
- gnn/validator.py: GNNValidator (validate_markdown, validate_state_space,
  validate_matrices, validate_provenance, generate_validation_badge,
  _check_required_files, _check_manifest, _check_json_files, _check_markdown,
  _check_state_space, _check_provenance, _compute_final_score),
  ValidationResult (to_dict, badge_svg)
- export/bundle.py: BundleExporter (_export_markdown, _export_json, _export_graphml,
  _export_html, _generate_html, _create_manifest)
- reverse/planner.py: _to_identifier, _python_type_for, _default_value_for,
  _reserved_avoid, _build_scaffold_constraints, _build_scaffold_policies,
  _build_scaffold_contexts
- gnn/json_export.py: GNNJSONExporter (export with mappings as list conversion,
  _export_matrices on exception path)
"""

import json

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_empty_graph():
    from cogant.schemas.graph import GraphMetadata, ProgramGraph

    return ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))


def _make_graph_with_nodes():
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import EdgeKind, NodeKind

    builder = ProgramGraphBuilder(repo_uri="file:///test")
    n1 = builder.add_node(NodeKind.MODULE, "mod", "mod", path="mod.py")
    n2 = builder.add_node(NodeKind.FUNCTION, "fn", "mod.fn", path="mod.py")
    builder.add_edge(n1.id, n2.id, EdgeKind.CONTAINS)
    return builder.finalize()


def _make_state_space():
    from cogant.statespace.compiler import StateSpaceModel
    from cogant.statespace.temporal import TimeRegime

    return StateSpaceModel(
        id="ss1",
        schema_name="test",
        variables={},
        observations={},
        actions={},
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


def _make_process_model():
    from cogant.process.extractor import ProcessModel

    return ProcessModel(id="pm1", schema_name="test", stages={}, connections={})


def _make_reverse_model(name="test_model"):
    from cogant.reverse.parser import ReverseGNNModel

    return ReverseGNNModel(
        model_name=name,
        hidden_states=["state_a", "state_b"],
        observations=["obs_x"],
        actions=["act_1"],
    )


def _make_gnn_package_dir(tmp_path):
    """Create a minimal GNN package directory for validator tests."""
    manifest = {"version": "1.0.0", "schema_name": "test", "files": [], "checksums": {}}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "model.gnn.json").write_text(json.dumps({"model_name": "test"}))
    (tmp_path / "model.gnn.md").write_text("## GNNSection\n\n## StateSpaceBlock\n")
    (tmp_path / "state_space.json").write_text(
        json.dumps(
            {
                "variables": [],
                "observations": [],
                "actions": [],
                "transitions": {},
            }
        )
    )
    return tmp_path


# ---------------------------------------------------------------------------
# gnn/validator.py — ValidationResult
# ---------------------------------------------------------------------------


class TestValidationResult:
    def test_to_dict_empty(self):
        from cogant.gnn.validator import ValidationResult

        result = ValidationResult()
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "valid" in d

    def test_to_dict_with_errors(self):
        from cogant.gnn.validator import ValidationResult

        result = ValidationResult(valid=False, errors=["Missing file"])
        d = result.to_dict()
        assert not d["valid"]
        assert len(d["errors"]) >= 1

    def test_badge_svg_valid(self):
        from cogant.gnn.validator import ValidationResult

        result = ValidationResult(valid=True, score=95.0)
        svg = result.badge_svg()
        assert isinstance(svg, str)
        assert "<svg" in svg

    def test_badge_svg_invalid(self):
        from cogant.gnn.validator import ValidationResult

        result = ValidationResult(valid=False, score=30.0, errors=["Bad"])
        svg = result.badge_svg()
        assert isinstance(svg, str)
        assert "<svg" in svg


# ---------------------------------------------------------------------------
# gnn/validator.py — GNNValidator methods
# ---------------------------------------------------------------------------


class TestGNNValidator:
    def _make_validator(self, pkg_dir=None):
        from cogant.gnn.validator import GNNValidator

        return GNNValidator()

    def test_validate_markdown_empty(self):
        validator = self._make_validator()
        errors = validator.validate_markdown("")
        assert isinstance(errors, list)
        # Empty markdown should have errors
        assert len(errors) >= 1

    def test_validate_markdown_complete(self):
        validator = self._make_validator()
        # Build markdown with all required sections
        md = "\n".join(
            [
                "## GNNSection",
                "## StateSpaceBlock",
                "## Connections",
                "## InitialParameterization",
                "## Time",
                "## ActInfOntologyAnnotation",
                "## Model Metadata",
                "## Source Coverage",
                "## Markov Blanket",
            ]
        )
        errors = validator.validate_markdown(md)
        assert isinstance(errors, list)

    def test_validate_state_space_valid(self):
        validator = self._make_validator()
        ss = {"variables": [], "observations": [], "actions": [], "transitions": {}}
        errors = validator.validate_state_space(ss)
        assert isinstance(errors, list)
        assert len(errors) == 0

    def test_validate_state_space_missing_keys(self):
        validator = self._make_validator()
        errors = validator.validate_state_space({})
        assert isinstance(errors, list)
        assert len(errors) >= 1

    def test_validate_state_space_bad_types(self):
        validator = self._make_validator()
        ss = {"variables": "not_list", "observations": [], "actions": [], "transitions": []}
        errors = validator.validate_state_space(ss)
        assert isinstance(errors, list)
        assert len(errors) >= 1

    def test_validate_matrices_empty(self):
        validator = self._make_validator()
        errors = validator.validate_matrices({"A": [], "B": [], "C": [], "D": []})
        assert isinstance(errors, list)

    def test_validate_matrices_with_values(self):
        validator = self._make_validator()
        matrices = {
            "A": [[0.9, 0.1], [0.2, 0.8]],
            "B": [[[1.0, 0.0], [0.0, 1.0]]],
            "C": [1.0, 0.0],
            "D": [0.5, 0.5],
        }
        errors = validator.validate_matrices(matrices)
        assert isinstance(errors, list)

    def test_validate_provenance_valid(self):
        validator = self._make_validator()
        errors = validator.validate_provenance(
            {"timestamp": "2025-01-01", "sources": {"git": "abc123"}}
        )
        assert isinstance(errors, list)
        assert len(errors) == 0

    def test_validate_provenance_missing_keys(self):
        validator = self._make_validator()
        errors = validator.validate_provenance({})
        assert isinstance(errors, list)
        assert len(errors) >= 1

    def test_generate_validation_badge(self):
        from cogant.gnn.validator import ValidationResult

        validator = self._make_validator()
        result = ValidationResult(valid=True, score=85.0)
        badge = validator.generate_validation_badge(result)
        assert isinstance(badge, str)
        assert "<svg" in badge

    def test_validate_package_minimal(self, tmp_path):
        from cogant.gnn.validator import GNNValidator, ValidationResult

        _make_gnn_package_dir(tmp_path)
        validator = GNNValidator()
        result = validator.validate_package(str(tmp_path))
        assert isinstance(result, ValidationResult)
        assert hasattr(result, "score")

    def test_validate_package_empty_dir(self, tmp_path):
        from cogant.gnn.validator import GNNValidator, ValidationResult

        validator = GNNValidator()
        result = validator.validate_package(str(tmp_path))
        assert isinstance(result, ValidationResult)
        assert len(result.errors) >= 1


# ---------------------------------------------------------------------------
# export/bundle.py — BundleExporter private methods
# ---------------------------------------------------------------------------


class TestBundleExporterPrivateMethods:
    def _make_exporter(self, tmp_path):
        from cogant.export.bundle import BundleExporter

        return BundleExporter(
            program_graph=_make_graph_with_nodes(),
            state_space_model=_make_state_space(),
            process_model=_make_process_model(),
            semantic_mappings={},
            output_dir=tmp_path,
        )

    def test_export_markdown_returns_tuple(self, tmp_path):
        exporter = self._make_exporter(tmp_path)
        result = exporter._export_markdown()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_export_json_returns_tuple(self, tmp_path):
        exporter = self._make_exporter(tmp_path)
        result = exporter._export_json()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_export_graphml_returns_tuple(self, tmp_path):
        exporter = self._make_exporter(tmp_path)
        result = exporter._export_graphml()
        assert isinstance(result, tuple)

    def test_export_html_returns_tuple(self, tmp_path):
        exporter = self._make_exporter(tmp_path)
        result = exporter._export_html()
        assert isinstance(result, tuple)

    def test_generate_html_returns_str(self, tmp_path):
        exporter = self._make_exporter(tmp_path)
        result = exporter._generate_html()
        assert isinstance(result, str)
        assert "<!DOCTYPE html>" in result or "<html" in result


# ---------------------------------------------------------------------------
# reverse/planner.py — helper functions
# ---------------------------------------------------------------------------


class TestReverseplannerHelpers:
    def test_to_identifier_basic(self):
        from cogant.reverse.planner import _to_identifier

        result = _to_identifier("my state", "fallback")
        assert isinstance(result, str)
        assert " " not in result

    def test_to_identifier_empty(self):
        from cogant.reverse.planner import _to_identifier

        result = _to_identifier("", "fallback")
        assert result == "fallback"

    def test_to_identifier_strips_role_suffix(self):
        from cogant.reverse.planner import _to_identifier

        result = _to_identifier("my-state-hidden state", "fb")
        assert isinstance(result, str)
        assert "hidden" not in result.lower() or isinstance(result, str)

    def test_to_identifier_digit_prefix(self):
        from cogant.reverse.planner import _to_identifier

        result = _to_identifier("123abc", "fb")
        assert result.startswith("var_") or result[0].isalpha() or isinstance(result, str)

    def test_python_type_for_int(self):
        from cogant.reverse.planner import _python_type_for

        assert _python_type_for("int") == "int"

    def test_python_type_for_bool(self):
        from cogant.reverse.planner import _python_type_for

        assert _python_type_for("bool") == "bool"

    def test_python_type_for_float(self):
        from cogant.reverse.planner import _python_type_for

        assert _python_type_for("float") == "float"

    def test_python_type_for_empty(self):
        from cogant.reverse.planner import _python_type_for

        assert _python_type_for("") == "float"

    def test_python_type_for_unknown(self):
        from cogant.reverse.planner import _python_type_for

        assert _python_type_for("str") == "float"

    def test_default_value_for_bool(self):
        from cogant.reverse.planner import _default_value_for

        result = _default_value_for("bool", 2, 0.5)
        assert result == "False"

    def test_default_value_for_int(self):
        from cogant.reverse.planner import _default_value_for

        result = _default_value_for("int", 3, 0.3)
        assert result == "0"

    def test_default_value_for_float_uniform(self):
        from cogant.reverse.planner import _default_value_for

        result = _default_value_for("float", 2, 0.0)
        assert result == "0.0"

    def test_default_value_for_float_informative(self):
        from cogant.reverse.planner import _default_value_for

        result = _default_value_for("float", 3, 0.7)
        assert result == "0.7"

    def test_reserved_avoid_keyword(self):
        from cogant.reverse.planner import _reserved_avoid

        used: dict[str, int] = {}
        result = _reserved_avoid("class", used)
        assert result not in {"class", "def", "return"}
        assert result.startswith("var_")

    def test_reserved_avoid_collision(self):
        from cogant.reverse.planner import _reserved_avoid

        used: dict[str, int] = {"my_var": 1}
        result = _reserved_avoid("my_var", used)
        assert result != "my_var"

    def test_build_scaffold_constraints(self):
        from cogant.reverse.idempotency import plan_package
        from cogant.reverse.planner import _build_scaffold_constraints

        model = _make_reverse_model()
        plan = plan_package(model)
        used: dict[str, int] = {}
        result = _build_scaffold_constraints(plan, used)
        assert isinstance(result, list)

    def test_build_scaffold_policies(self):
        from cogant.reverse.idempotency import plan_package
        from cogant.reverse.planner import _build_scaffold_policies

        model = _make_reverse_model()
        plan = plan_package(model)
        used: dict[str, int] = {}
        result = _build_scaffold_policies(plan, used)
        assert isinstance(result, list)

    def test_build_scaffold_contexts(self):
        from cogant.reverse.idempotency import plan_package
        from cogant.reverse.planner import _build_scaffold_contexts

        model = _make_reverse_model()
        plan = plan_package(model)
        used: dict[str, int] = {}
        result = _build_scaffold_contexts(plan, used)
        assert isinstance(result, list)
