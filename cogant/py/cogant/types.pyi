from typing import Any, Literal, TypedDict

__all__ = [
    "NodeAttrs",
    "EdgeAttrs",
    "GNNBundle",
    "MatrixDict",
    "PipelineResultDict",
    "RuleResultDict",
    "ValidationIssue",
    "ComplexityEntry",
    "CouplingEntry",
    "DeadCodeEntry",
    "HalsteadDict",
    "GraphMetricsDict",
    "ExportResultDict",
    "AnalysisBundleDict",
    "VisualizationResult",
    "NodeId",
    "EdgeKind",
    "RoleName",
    "FilePath",
    "ConfidenceScore",
    "AMatrix",
    "BMatrix",
    "CVector",
    "DVector",
    "MermaidStr",
    "DotStr",
    "JsonStr",
    "CentralityDict",
]

class NodeAttrs(TypedDict, total=False):
    id: str
    kind: str
    name: str
    file: str
    line: int
    role: str
    confidence: float

class EdgeAttrs(TypedDict, total=False):
    src: str
    dst: str
    kind: str
    weight: float

class MatrixDict(TypedDict, total=False):
    A: list[list[float]]
    B: list[list[list[float]]]
    C: list[float]
    D: list[float]

class GNNBundle(TypedDict, total=False):
    version: str
    source_hash: str
    matrices: MatrixDict
    roles: dict[str, str]
    metadata: dict[str, Any]

class PipelineResultDict(TypedDict, total=False):
    status: str
    timing: dict[str, float]
    warnings: list[str]
    gnn_bundle: GNNBundle
    validator_score: int

class RuleResultDict(TypedDict, total=False):
    rule_name: str
    node_id: str
    role: str
    confidence: float
    evidence: str

class ValidationIssue(TypedDict, total=False):
    severity: Literal["error", "warning", "info"]
    message: str
    location: str

NodeId = str
EdgeKind = str
RoleName = str
FilePath = str
ConfidenceScore = float
AMatrix = list[list[float]]
BMatrix = list[list[list[float]]]
CVector = list[float]
DVector = list[float]
MermaidStr = str
DotStr = str
JsonStr = str
CentralityDict = dict[str, float]

class ComplexityEntry(TypedDict, total=False):
    function: str
    complexity: int
    file: str
    line: int

class CouplingEntry(TypedDict, total=False):
    source: str
    target: str
    weight: float
    kind: str

class DeadCodeEntry(TypedDict, total=False):
    name: str
    kind: str
    file: str
    line: int

class HalsteadDict(TypedDict, total=False):
    vocabulary: int
    length: int
    volume: float
    difficulty: float
    effort: float

class GraphMetricsDict(TypedDict, total=False):
    node_count: int
    edge_count: int
    density: float
    connected_components: int

class ExportResultDict(TypedDict, total=False):
    path: str
    format: str
    success: bool
    error: str

class AnalysisBundleDict(TypedDict, total=False):
    static: dict[str, Any]
    dynamic: dict[str, Any]
    graph: dict[str, Any]
    gnn: GNNBundle

class VisualizationResult(TypedDict, total=False):
    path: str
    format: str
    title: str
    metadata: dict[str, Any]
