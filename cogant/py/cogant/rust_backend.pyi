from typing import Any

from cogant.schemas.core import Edge, Node

__all__ = [
    "RUST_AVAILABLE",
    "RustProgramGraphAdapter",
    "build_program_graph",
    "compile_matrix_shapes_json",
    "create_example_graph",
    "format_gnn_json",
    "format_gnn_markdown",
    "get_program_graph_impl",
    "graph_summary_json",
    "rust_version",
    "summarize_trace_events_json",
    "translation_rule_predicates_json",
    "write_artifact_atomic",
]

RUST_AVAILABLE: bool

def get_program_graph_impl() -> type[Any]: ...
def rust_version() -> str | None: ...
def create_example_graph() -> Any: ...
def graph_summary_json(graph: Any) -> str: ...
def translation_rule_predicates_json() -> str: ...
def compile_matrix_shapes_json(n_states: int, n_obs: int, n_actions: int) -> str: ...
def format_gnn_json(graph: Any, title: str) -> str: ...
def format_gnn_markdown(graph: Any, title: str) -> str: ...
def write_artifact_atomic(path: str, contents: bytes) -> None: ...
def summarize_trace_events_json(events_json: str) -> str: ...

class RustProgramGraphAdapter:
    repo_uri: Any
    def __init__(self, repo_uri: str) -> None: ...
    def add_node(
        self,
        kind: Any,
        name: str,
        qualified_name: str,
        path: str | None = None,
        language: str | None = None,
        source_range: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Node: ...
    def add_edge(
        self,
        source_id: str,
        target_id: str,
        kind: Any,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
        evidence_sources: list[str] | None = None,
    ) -> Edge | None: ...
    def finalize(self) -> Any: ...
    @property
    def graph(self) -> Any: ...
    def node_count(self) -> int: ...
    def edge_count(self) -> int: ...

def build_program_graph(repo_uri: str = "repo://unknown", use_rust: bool | None = None) -> Any: ...
