"""Unit tests for type definitions."""

import pytest
from typing import get_type_hints

from cogant.types import (
    NodeAttrs,
    EdgeAttrs,
    GNNBundle,
    MatrixDict,
    PipelineResultDict,
    RuleResultDict,
    ValidationIssue,
    NodeId,
    EdgeKind,
    RoleName,
    FilePath,
    ConfidenceScore,
    AMatrix,
    BMatrix,
    CVector,
    DVector,
)
from cogant.translate.types import (
    SemanticRole,
    RuleFamily,
    FixpointStatus,
    TranslationTier,
)


@pytest.mark.unit
class TestNodeAttrs:
    """Test NodeAttrs TypedDict."""

    def test_node_attrs_creation(self) -> None:
        """Test creating NodeAttrs."""
        attrs: NodeAttrs = {
            "id": "node1",
            "kind": "function",
            "name": "my_function",
            "file": "test.py",
            "line": 10,
            "role": "HIDDEN_STATE",
            "confidence": 0.95,
        }
        assert attrs["id"] == "node1"
        assert attrs["kind"] == "function"
        assert attrs["confidence"] == 0.95

    def test_node_attrs_optional_fields(self) -> None:
        """Test NodeAttrs with only required fields (all are optional in this TypedDict)."""
        attrs: NodeAttrs = {"id": "node1"}
        assert attrs["id"] == "node1"

    def test_node_attrs_partial(self) -> None:
        """Test NodeAttrs with partial fields."""
        attrs: NodeAttrs = {
            "id": "node1",
            "kind": "class",
            "name": "MyClass",
        }
        assert len(attrs) == 3


@pytest.mark.unit
class TestEdgeAttrs:
    """Test EdgeAttrs TypedDict."""

    def test_edge_attrs_creation(self) -> None:
        """Test creating EdgeAttrs."""
        attrs: EdgeAttrs = {
            "src": "node1",
            "dst": "node2",
            "kind": "calls",
            "weight": 0.8,
        }
        assert attrs["src"] == "node1"
        assert attrs["dst"] == "node2"
        assert attrs["weight"] == 0.8

    def test_edge_attrs_minimal(self) -> None:
        """Test EdgeAttrs with minimal fields."""
        attrs: EdgeAttrs = {"src": "A", "dst": "B"}
        assert attrs["src"] == "A"


@pytest.mark.unit
class TestMatrixDict:
    """Test MatrixDict TypedDict."""

    def test_matrix_dict_creation(self) -> None:
        """Test creating MatrixDict."""
        matrices: MatrixDict = {
            "A": [[0.9, 0.1], [0.1, 0.9]],
            "B": [[[0.8, 0.2], [0.3, 0.7]]],
            "C": [1.0, 0.0],
            "D": [0.5, 0.5],
        }
        assert len(matrices["A"]) == 2
        assert matrices["C"] == [1.0, 0.0]

    def test_matrix_dict_partial(self) -> None:
        """Test MatrixDict with partial matrices."""
        matrices: MatrixDict = {
            "A": [[0.9, 0.1]],
            "D": [1.0],
        }
        assert "A" in matrices
        assert "B" not in matrices


@pytest.mark.unit
class TestGNNBundle:
    """Test GNNBundle TypedDict."""

    def test_gnn_bundle_creation(self) -> None:
        """Test creating a GNNBundle."""
        bundle: GNNBundle = {
            "version": "0.5.0",
            "source_hash": "abc123",
            "matrices": {
                "A": [[0.9, 0.1]],
                "D": [0.5],
            },
            "roles": {"node1": "HIDDEN_STATE", "node2": "OBSERVATION"},
            "metadata": {"created_at": "2026-04-13", "analyzer": "cogant"},
        }
        assert bundle["version"] == "0.5.0"
        assert bundle["roles"]["node1"] == "HIDDEN_STATE"

    def test_gnn_bundle_all_fields(self) -> None:
        """Test GNNBundle with all fields populated."""
        bundle: GNNBundle = {
            "version": "1.0.0",
            "source_hash": "xyz789",
            "matrices": {
                "A": [[1.0, 0.0], [0.0, 1.0]],
                "B": [[[1.0, 0.0], [0.0, 1.0]]],
                "C": [1.0, 0.0],
                "D": [0.5, 0.5],
            },
            "roles": {
                "state1": "HIDDEN_STATE",
                "obs1": "OBSERVATION",
                "act1": "ACTION",
            },
            "metadata": {
                "created_at": "2026-04-13",
                "version": "0.5.0",
                "timestamp": 1234567890,
            },
        }
        assert len(bundle["roles"]) == 3


@pytest.mark.unit
class TestPipelineResultDict:
    """Test PipelineResultDict TypedDict."""

    def test_pipeline_result_dict_creation(self) -> None:
        """Test creating a PipelineResultDict."""
        result: PipelineResultDict = {
            "status": "success",
            "timing": {"extract": 1.5, "translate": 2.5, "export": 0.5},
            "warnings": ["warning1"],
            "gnn_bundle": {"version": "0.5.0", "roles": {}},
            "validator_score": 95,
        }
        assert result["status"] == "success"
        assert result["validator_score"] == 95

    def test_pipeline_result_dict_failure_status(self) -> None:
        """Test PipelineResultDict with failure status."""
        result: PipelineResultDict = {
            "status": "failed",
            "timing": {},
            "warnings": ["error1", "error2"],
        }
        assert result["status"] == "failed"


@pytest.mark.unit
class TestRuleResultDict:
    """Test RuleResultDict TypedDict."""

    def test_rule_result_dict_creation(self) -> None:
        """Test creating a RuleResultDict."""
        rule_result: RuleResultDict = {
            "rule_name": "rule_hidden_state_from_class",
            "node_id": "ClassNode_1",
            "role": "HIDDEN_STATE",
            "confidence": 0.92,
            "evidence": "Class definition with state attributes",
        }
        assert rule_result["rule_name"] == "rule_hidden_state_from_class"
        assert rule_result["confidence"] == 0.92

    def test_rule_result_dict_low_confidence(self) -> None:
        """Test RuleResultDict with low confidence."""
        rule_result: RuleResultDict = {
            "rule_name": "rule_action_from_method",
            "node_id": "method_1",
            "role": "ACTION",
            "confidence": 0.6,
            "evidence": "Heuristic match on method name pattern",
        }
        assert rule_result["confidence"] == 0.6


@pytest.mark.unit
class TestValidationIssue:
    """Test ValidationIssue TypedDict."""

    def test_validation_issue_error(self) -> None:
        """Test ValidationIssue with error severity."""
        issue: ValidationIssue = {
            "severity": "error",
            "message": "Missing observation variable",
            "location": "file.py:42",
        }
        assert issue["severity"] == "error"

    def test_validation_issue_warning(self) -> None:
        """Test ValidationIssue with warning severity."""
        issue: ValidationIssue = {
            "severity": "warning",
            "message": "Low confidence in assignment",
            "location": "module.class:method",
        }
        assert issue["severity"] == "warning"

    def test_validation_issue_info(self) -> None:
        """Test ValidationIssue with info severity."""
        issue: ValidationIssue = {
            "severity": "info",
            "message": "Analyzed 42 nodes",
            "location": "global",
        }
        assert issue["severity"] == "info"


@pytest.mark.unit
class TestTypeAliases:
    """Test type aliases are properly defined."""

    def test_node_id_is_str(self) -> None:
        """Test that NodeId is str."""
        node_id: NodeId = "node_12345"
        assert isinstance(node_id, str)

    def test_edge_kind_is_str(self) -> None:
        """Test that EdgeKind is str."""
        edge_kind: EdgeKind = "calls"
        assert isinstance(edge_kind, str)

    def test_role_name_is_str(self) -> None:
        """Test that RoleName is str."""
        role: RoleName = "HIDDEN_STATE"
        assert isinstance(role, str)

    def test_file_path_is_str(self) -> None:
        """Test that FilePath is str."""
        path: FilePath = "/path/to/file.py"
        assert isinstance(path, str)

    def test_confidence_score_is_float(self) -> None:
        """Test that ConfidenceScore is float."""
        score: ConfidenceScore = 0.95
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_a_matrix_is_list_of_lists(self) -> None:
        """Test that AMatrix is list of lists of floats."""
        a: AMatrix = [[0.9, 0.1], [0.1, 0.9]]
        assert isinstance(a, list)
        assert all(isinstance(row, list) for row in a)

    def test_b_matrix_is_3d_list(self) -> None:
        """Test that BMatrix is 3D list of floats."""
        b: BMatrix = [[[0.8, 0.2], [0.3, 0.7]]]
        assert isinstance(b, list)
        assert all(isinstance(item, list) for item in b)

    def test_c_vector_is_list(self) -> None:
        """Test that CVector is list of floats."""
        c: CVector = [1.0, 0.0, 0.5]
        assert isinstance(c, list)
        assert all(isinstance(val, (int, float)) for val in c)

    def test_d_vector_is_list(self) -> None:
        """Test that DVector is list of floats."""
        d: DVector = [0.5, 0.5, 0.0]
        assert isinstance(d, list)
        assert all(isinstance(val, (int, float)) for val in d)


@pytest.mark.unit
class TestSemanticRole:
    """Test SemanticRole Literal type."""

    def test_semantic_role_hidden_state(self) -> None:
        """Test HIDDEN_STATE role."""
        role: SemanticRole = "HIDDEN_STATE"
        assert role == "HIDDEN_STATE"

    def test_semantic_role_observation(self) -> None:
        """Test OBSERVATION role."""
        role: SemanticRole = "OBSERVATION"
        assert role == "OBSERVATION"

    def test_semantic_role_action(self) -> None:
        """Test ACTION role."""
        role: SemanticRole = "ACTION"
        assert role == "ACTION"

    def test_semantic_role_policy(self) -> None:
        """Test POLICY role."""
        role: SemanticRole = "POLICY"
        assert role == "POLICY"

    def test_semantic_role_preference(self) -> None:
        """Test PREFERENCE role."""
        role: SemanticRole = "PREFERENCE"
        assert role == "PREFERENCE"

    def test_semantic_role_context(self) -> None:
        """Test CONTEXT role."""
        role: SemanticRole = "CONTEXT"
        assert role == "CONTEXT"

    def test_semantic_role_parameter(self) -> None:
        """Test PARAMETER role."""
        role: SemanticRole = "PARAMETER"
        assert role == "PARAMETER"

    def test_semantic_role_constraint(self) -> None:
        """Test CONSTRAINT role."""
        role: SemanticRole = "CONSTRAINT"
        assert role == "CONSTRAINT"

    def test_semantic_role_data_flow(self) -> None:
        """Test DATA_FLOW role."""
        role: SemanticRole = "DATA_FLOW"
        assert role == "DATA_FLOW"

    def test_semantic_role_error_handling(self) -> None:
        """Test ERROR_HANDLING role."""
        role: SemanticRole = "ERROR_HANDLING"
        assert role == "ERROR_HANDLING"

    def test_semantic_role_orchestration(self) -> None:
        """Test ORCHESTRATION role."""
        role: SemanticRole = "ORCHESTRATION"
        assert role == "ORCHESTRATION"


@pytest.mark.unit
class TestRuleFamily:
    """Test RuleFamily Literal type."""

    def test_rule_family_structural(self) -> None:
        """Test structural rule family."""
        family: RuleFamily = "structural"
        assert family == "structural"

    def test_rule_family_semantic(self) -> None:
        """Test semantic rule family."""
        family: RuleFamily = "semantic"
        assert family == "semantic"

    def test_rule_family_control(self) -> None:
        """Test control rule family."""
        family: RuleFamily = "control"
        assert family == "control"

    def test_rule_family_behavioral(self) -> None:
        """Test behavioral rule family."""
        family: RuleFamily = "behavioral"
        assert family == "behavioral"

    def test_rule_family_resilience(self) -> None:
        """Test resilience rule family."""
        family: RuleFamily = "resilience"
        assert family == "resilience"


@pytest.mark.unit
class TestFixpointStatus:
    """Test FixpointStatus Literal type."""

    def test_fixpoint_status_converged(self) -> None:
        """Test converged status."""
        status: FixpointStatus = "converged"
        assert status == "converged"

    def test_fixpoint_status_max_iterations(self) -> None:
        """Test max_iterations_exceeded status."""
        status: FixpointStatus = "max_iterations_exceeded"
        assert status == "max_iterations_exceeded"

    def test_fixpoint_status_empty_graph(self) -> None:
        """Test empty_graph status."""
        status: FixpointStatus = "empty_graph"
        assert status == "empty_graph"


@pytest.mark.unit
class TestTranslationTier:
    """Test TranslationTier Literal type."""

    def test_translation_tier_core(self) -> None:
        """Test core tier."""
        tier: TranslationTier = "core"
        assert tier == "core"

    def test_translation_tier_supplementary(self) -> None:
        """Test supplementary tier."""
        tier: TranslationTier = "supplementary"
        assert tier == "supplementary"

    def test_translation_tier_degraded(self) -> None:
        """Test degraded tier."""
        tier: TranslationTier = "degraded"
        assert tier == "degraded"
