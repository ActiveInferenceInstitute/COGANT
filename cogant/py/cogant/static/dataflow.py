"""Data flow analysis: track variable reads/writes and build data flow edges.

This module extracts READ, WRITE, MUTATE, and DEPENDS_ON relationships from
Python source. It drives several translation rules that need to know which
symbols a function modifies or observes.

The analyzer works at two levels:

* ``DataFlowAnalyzer`` — top-level orchestrator. Walks a parsed module and
  launches a ``DataFlowVisitor`` for module-level code, every function body,
  and every method body.
* ``DataFlowVisitor`` — an :class:`ast.NodeVisitor` that records reads/writes
  inside a single scope. It understands simple assignments, annotated
  assignments, augmented assignments, attribute writes, attribute reads, free
  ``Name`` loads, function calls, and return statements.

All operations are resilient: malformed source or unexpected AST shapes are
logged at debug level and skipped rather than aborting extraction.
"""

import ast
import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cogant.static.parser import PythonASTParser
from cogant.static.symbols import SymbolExtractor

logger = logging.getLogger(__name__)


@dataclass
class DataFlowEdge:
    """A data flow relationship between symbols."""

    id: str
    """Unique edge identifier."""

    source_symbol: str
    """Source symbol ID or name."""

    target_symbol: str
    """Target symbol ID or name."""

    edge_type: str
    """Edge type: reads, writes, mutates, depends_on."""

    file_path: Path
    """Source file path."""

    line_num: int
    """Line number where flow occurs."""

    context: str = "module"
    """Context (module, function name, class.method)."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""


@dataclass
class DataFlowGraph:
    """Directed graph of data flow relationships."""

    edges: list[DataFlowEdge] = field(default_factory=list)
    """List of data flow edges."""

    nodes: set[str] = field(default_factory=set)
    """Set of all node names."""

    def add_edge(self, edge: DataFlowEdge) -> None:
        """Add an edge to the graph.

        Args:
            edge: DataFlowEdge to add.
        """
        self.edges.append(edge)
        self.nodes.add(edge.source_symbol)
        self.nodes.add(edge.target_symbol)

    def find_sources(self) -> list[str]:
        """Find nodes with no incoming data flow (entry points).

        Returns:
            List of source node names.
        """
        sources_with_incoming = {e.target_symbol for e in self.edges}
        return sorted([n for n in self.nodes if n not in sources_with_incoming])

    def find_sinks(self) -> list[str]:
        """Find nodes with no outgoing data flow (final consumers).

        Returns:
            List of sink node names.
        """
        sinks_with_outgoing = {e.source_symbol for e in self.edges}
        return sorted([n for n in self.nodes if n not in sinks_with_outgoing])

    def get_taint_paths(self, source: str, sink: str) -> list[list[str]]:
        """Find all paths from source to sink node.

        Args:
            source: Source node name.
            sink: Sink node name.

        Returns:
            List of paths (each path is a list of node names).
        """
        # Build adjacency list
        adj: dict[str, set[str]] = {}
        for node in self.nodes:
            adj[node] = set()
        for edge in self.edges:
            adj[edge.source_symbol].add(edge.target_symbol)

        # DFS to find all paths
        all_paths: list[list[str]] = []

        def dfs(current: str, target: str, path: list[str]) -> None:
            """Depth-first search for paths.

            Args:
                current: Current node.
                target: Target node.
                path: Current path.
            """
            if current == target:
                all_paths.append(path[:])
                return
            if current not in adj:
                return
            for neighbor in adj[current]:
                if neighbor not in path:  # Prevent cycles
                    path.append(neighbor)
                    dfs(neighbor, target, path)
                    path.pop()

        if source in self.nodes:
            dfs(source, sink, [source])

        return all_paths

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph to dictionary.

        Returns:
            Dictionary representation of the graph.
        """
        return {
            "nodes": sorted(self.nodes),
            "edges": [
                {
                    "id": e.id,
                    "source": e.source_symbol,
                    "target": e.target_symbol,
                    "type": e.edge_type,
                    "file": str(e.file_path),
                    "line": e.line_num,
                    "context": e.context,
                }
                for e in self.edges
            ],
        }


class DataFlowAnalyzer:
    """Analyze data flow: track variable reads, writes, and mutations."""

    def __init__(self, repo_root: Path | None = None):
        """Initialize data flow analyzer.

        Args:
            repo_root: Root path of repository.
        """
        self.repo_root = Path(repo_root or "/")
        self.parser = PythonASTParser()
        self.symbol_extractor = SymbolExtractor(repo_root)

    def analyze_file(self, file_path: Path) -> list[DataFlowEdge]:
        """Analyze data flow in a Python file.

        Args:
            file_path: Path to Python file.

        Returns:
            List of DataFlowEdge for data flow relationships.
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
        except OSError as e:
            logger.debug(f"Failed to read {file_path}: {e}")
            return []

        return self.analyze_source(source, file_path)

    def analyze_source(self, source: str, file_path: Path) -> list[DataFlowEdge]:
        """Analyze data flow in Python source code.

        Args:
            source: Python source code.
            file_path: Path for reference.

        Returns:
            List of DataFlowEdge for data flow relationships.
        """
        flows: list[DataFlowEdge] = []

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            logger.debug(f"Syntax error parsing data flow in {file_path}: {e}")
            return flows
        except ValueError as e:
            logger.debug(f"Parse error parsing data flow in {file_path}: {e}")
            return flows

        # Module-level statements (no function bodies)
        module_stmts = [
            stmt
            for stmt in tree.body
            if not isinstance(
                stmt,
                ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
            )
        ]
        if module_stmts:
            visitor = DataFlowVisitor(file_path, "module", module_stmts)
            flows.extend(visitor.flows)

        # Top-level functions
        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                visitor = DataFlowVisitor(file_path, node.name, node.body)
                flows.extend(visitor.flows)
            elif isinstance(node, ast.ClassDef):
                # Analyze class body (attribute defaults, AnnAssigns)
                class_body_stmts = [
                    item
                    for item in node.body
                    if not isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef)
                ]
                if class_body_stmts:
                    visitor = DataFlowVisitor(file_path, node.name, class_body_stmts)
                    flows.extend(visitor.flows)

                # Analyze methods
                for item in node.body:
                    if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                        context = f"{node.name}.{item.name}"
                        visitor = DataFlowVisitor(file_path, context, item.body)
                        flows.extend(visitor.flows)

        return flows

    def build_flow_graph(self, file_path: Path) -> DataFlowGraph:
        """Build a data flow graph from a Python file.

        Args:
            file_path: Path to Python file.

        Returns:
            DataFlowGraph instance.
        """
        edges = self.analyze_file(file_path)
        graph = DataFlowGraph()
        for edge in edges:
            graph.add_edge(edge)
        return graph

    def build_flow_graph_from_source(self, source: str, file_path: Path) -> DataFlowGraph:
        """Build a data flow graph from source code.

        Args:
            source: Python source code.
            file_path: Path for reference.

        Returns:
            DataFlowGraph instance.
        """
        edges = self.analyze_source(source, file_path)
        graph = DataFlowGraph()
        for edge in edges:
            graph.add_edge(edge)
        return graph


class DataFlowVisitor(ast.NodeVisitor):
    """AST visitor to extract data flow edges from one scope.

    A visitor is scoped to one function, method, class body, or the module
    body. It tracks which names have been written (assigned) and which have
    been read, and emits ``DataFlowEdge`` instances describing each flow.

    Handled node kinds:

    * ``ast.Assign`` — plain assignment; targets are WRITES, sources are
      READS from each RHS name.
    * ``ast.AugAssign`` — augmented assignment (``x += 1``); target is both
      READ and MUTATED.
    * ``ast.AnnAssign`` — annotated assignment (``x: int = 5``); target is a
      WRITE, RHS names are READS. Handles ``x: int`` without a value too.
    * ``ast.Attribute`` in Store context — attribute writes (``self.x = 1``)
      produce a WRITE edge to the dotted name.
    * ``ast.Attribute`` in Load context — attribute reads produce a READ
      edge.
    * ``ast.Name`` in Load context — a free-standing name read (e.g. a loop
      condition) produces a READ edge.
    * ``ast.Call`` — argument names are READ; method calls on ``self``
      additionally emit a MUTATES edge to ``self.<attr>`` if the callee is
      on an attribute (potential mutation).
    * ``ast.Return`` — return value names are READ against the synthetic
      ``<return>`` target.
    """

    def __init__(
        self,
        file_path: Path,
        context: str,
        body: list[ast.stmt],
        symbol_extractor: Any | None = None,
    ):
        """Initialize data flow visitor.

        Args:
            file_path: Source file path.
            context: Context (function/method name or ``"module"``).
            body: AST body nodes to analyze.
            symbol_extractor: Optional SymbolExtractor for symbol resolution.
                Kept for backwards compatibility; not required for edge
                emission.
        """
        self.file_path = file_path
        self.context = context
        self.symbol_extractor = symbol_extractor
        self.flows: list[DataFlowEdge] = []
        self._assignments: dict[str, int] = {}
        self._reads: set[str] = set()
        # Track which Name nodes have already been emitted as reads via an
        # enclosing construct so we don't double-count them when generic_visit
        # eventually reaches them.
        self._handled_nodes: set[int] = set()

        for node in body:
            self.visit(node)

    # ------------------------------------------------------------------
    # Statement-level handlers
    # ------------------------------------------------------------------

    def visit_Assign(self, node: ast.Assign) -> None:
        """Handle a plain assignment statement.

        Args:
            node: AST Assign node.
        """
        # Extract targets (may be Name, Attribute, Tuple/List unpack, Subscript)
        target_names = self._extract_targets(node.targets)

        # Extract RHS names as reads
        source_names = self._extract_loads(node.value)
        # Mark value subtree as handled so generic_visit doesn't re-emit it
        self._mark_handled(node.value)

        for target in target_names:
            self._assignments[target] = node.lineno
            self._emit_write(target, node.lineno)
            for source in source_names:
                self._emit(
                    source_symbol=source,
                    target_symbol=target,
                    edge_type="depends_on",
                    line_num=node.lineno,
                )
                self._reads.add(source)
                self._emit(
                    source_symbol=source,
                    target_symbol=self.context,
                    edge_type="reads",
                    line_num=node.lineno,
                )

        # Don't recurse into target subtrees — they are stores, not loads.
        for target_node in node.targets:
            self._mark_handled(target_node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Handle an annotated assignment (``x: int = 5`` or ``x: int``).

        Args:
            node: AST AnnAssign node.
        """
        target_names = self._extract_targets([node.target])

        source_names: set[str] = set()
        if node.value is not None:
            source_names = self._extract_loads(node.value)
            self._mark_handled(node.value)

        for target in target_names:
            self._assignments[target] = node.lineno
            self._emit_write(target, node.lineno)
            for source in source_names:
                self._emit(
                    source_symbol=source,
                    target_symbol=target,
                    edge_type="depends_on",
                    line_num=node.lineno,
                )
                self._reads.add(source)
                self._emit(
                    source_symbol=source,
                    target_symbol=self.context,
                    edge_type="reads",
                    line_num=node.lineno,
                )

        self._mark_handled(node.target)
        if node.annotation is not None:
            self._mark_handled(node.annotation)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Handle an augmented assignment (``x += 1``).

        Args:
            node: AST AugAssign node.
        """
        target_name = self._target_name(node.target)
        sources = self._extract_loads(node.value)
        self._mark_handled(node.value)

        if target_name:
            # Target is read (augmented side)
            self._reads.add(target_name)
            self._emit(
                source_symbol=target_name,
                target_symbol=self.context,
                edge_type="reads",
                line_num=node.lineno,
            )
            # RHS sources are reads
            for source in sources:
                self._reads.add(source)
                self._emit(
                    source_symbol=source,
                    target_symbol=target_name,
                    edge_type="depends_on",
                    line_num=node.lineno,
                )
                self._emit(
                    source_symbol=source,
                    target_symbol=self.context,
                    edge_type="reads",
                    line_num=node.lineno,
                )

            # Target is mutated
            self._emit(
                source_symbol=self.context,
                target_symbol=target_name,
                edge_type="mutates",
                line_num=node.lineno,
            )
            self._emit_write(target_name, node.lineno)

        self._mark_handled(node.target)

    def visit_Return(self, node: ast.Return) -> None:
        """Handle a return statement.

        Args:
            node: AST Return node.
        """
        if node.value is not None:
            names = self._extract_loads(node.value)
            self._mark_handled(node.value)
            for name in names:
                self._reads.add(name)
                self._emit(
                    source_symbol=name,
                    target_symbol="<return>",
                    edge_type="reads",
                    line_num=node.lineno,
                )

    def visit_Call(self, node: ast.Call) -> None:
        """Handle a function or method call.

        Args:
            node: AST Call node.
        """
        # Argument names are reads
        for arg in node.args:
            names = self._extract_loads(arg)
            self._mark_handled(arg)
            for name in names:
                self._reads.add(name)
                self._emit(
                    source_symbol=name,
                    target_symbol="<call>",
                    edge_type="reads",
                    line_num=node.lineno,
                )
        # Keyword arguments are reads
        for kw in node.keywords:
            if kw.value is not None:
                names = self._extract_loads(kw.value)
                self._mark_handled(kw.value)
                for name in names:
                    self._reads.add(name)
                    self._emit(
                        source_symbol=name,
                        target_symbol="<call>",
                        edge_type="reads",
                        line_num=node.lineno,
                    )

        # Method call on an attribute (``obj.method(...)``) is a potential
        # mutation of ``obj``.
        if isinstance(node.func, ast.Attribute):
            receiver = self._attribute_root(node.func.value)
            if receiver:
                self._emit(
                    source_symbol=self.context,
                    target_symbol=receiver,
                    edge_type="mutates",
                    line_num=node.lineno,
                )
            self._mark_handled(node.func)
        elif isinstance(node.func, ast.Name):
            self._mark_handled(node.func)

        # Allow generic_visit for anything we didn't explicitly handle (e.g.
        # nested calls inside arguments).
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Handle a bare ``Name`` load (e.g., ``if x:``).

        Args:
            node: AST Name node.
        """
        if id(node) in self._handled_nodes:
            return
        if isinstance(node.ctx, ast.Load):
            self._reads.add(node.id)
            self._emit(
                source_symbol=node.id,
                target_symbol=self.context,
                edge_type="reads",
                line_num=node.lineno,
            )

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Handle an ``Attribute`` access.

        Stores (e.g., ``self.x = 1``) are handled by :meth:`visit_Assign`;
        this covers loads (``return self.x``).

        Args:
            node: AST Attribute node.
        """
        if id(node) in self._handled_nodes:
            return
        if isinstance(node.ctx, ast.Load):
            dotted = self._ast_to_dotted(node)
            if dotted:
                self._reads.add(dotted)
                self._emit(
                    source_symbol=dotted,
                    target_symbol=self.context,
                    edge_type="reads",
                    line_num=node.lineno,
                )
            # Stop recursion so inner Name doesn't double-count.
            self._mark_handled(node.value)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _emit_write(self, target: str, line_num: int) -> None:
        """Emit a WRITE edge from current scope to target."""
        self._emit(
            source_symbol=self.context,
            target_symbol=target,
            edge_type="writes",
            line_num=line_num,
        )

    def _emit(
        self,
        source_symbol: str,
        target_symbol: str,
        edge_type: str,
        line_num: int,
    ) -> None:
        """Append a DataFlowEdge to the flows list."""
        edge = DataFlowEdge(
            id=self._generate_flow_id(source_symbol, target_symbol, edge_type, line_num),
            source_symbol=source_symbol,
            target_symbol=target_symbol,
            edge_type=edge_type,
            file_path=self.file_path,
            line_num=line_num,
            context=self.context,
        )
        self.flows.append(edge)

    def _extract_targets(self, targets: list[ast.expr]) -> set[str]:
        """Extract target names from assignment targets.

        Handles ``Name``, ``Attribute``, and ``Tuple``/``List`` unpacking.
        """
        names: set[str] = set()
        for target in targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
            elif isinstance(target, ast.Attribute):
                dotted = self._ast_to_dotted(target)
                if dotted:
                    names.add(dotted)
            elif isinstance(target, ast.Tuple | ast.List):
                for elt in target.elts:
                    if isinstance(elt, ast.Name):
                        names.add(elt.id)
                    elif isinstance(elt, ast.Attribute):
                        dotted = self._ast_to_dotted(elt)
                        if dotted:
                            names.add(dotted)
            elif isinstance(target, ast.Subscript):
                # ``arr[0] = v`` — treat base name as target
                base = self._attribute_root(target.value)
                if base:
                    names.add(base)
        return names

    def _target_name(self, target: ast.expr) -> str | None:
        """Return a single target name for an AugAssign target."""
        if isinstance(target, ast.Name):
            return target.id
        if isinstance(target, ast.Attribute):
            return self._ast_to_dotted(target)
        return None

    @staticmethod
    def _extract_loads(node: ast.AST | None) -> set[str]:
        """Extract names that are *loaded* inside an expression subtree.

        Includes simple ``Name`` loads and dotted attribute loads so that
        ``self.x`` appears alongside ``y``.
        """
        if node is None:
            return set()

        names: set[str] = set()

        class Collector(ast.NodeVisitor):
            """Collect Name/Attribute loads."""

            def visit_Name(self, inner: ast.Name) -> None:
                """Record plain identifier loads (e.g. ``x``) into the outer name set."""
                if isinstance(inner.ctx, ast.Load):
                    names.add(inner.id)

            def visit_Attribute(self, inner: ast.Attribute) -> None:
                """Record dotted attribute loads (e.g. ``self.x``) into the outer name set."""
                if isinstance(inner.ctx, ast.Load):
                    dotted = DataFlowVisitor._ast_to_dotted_static(inner)
                    if dotted:
                        names.add(dotted)
                    # Don't descend further — we already have the full chain.
                    return
                self.generic_visit(inner)

        Collector().visit(node)
        return names

    def _mark_handled(self, node: ast.AST | None) -> None:
        """Mark a subtree as already-handled to prevent double emission."""
        if node is None:
            return
        for sub in ast.walk(node):
            self._handled_nodes.add(id(sub))

    def _ast_to_dotted(self, node: ast.AST) -> str | None:
        """Return a dotted-string representation of an attribute chain."""
        return self._ast_to_dotted_static(node)

    @staticmethod
    def _ast_to_dotted_static(node: ast.AST) -> str | None:
        """Static variant of ``_ast_to_dotted`` (used by closures)."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            base = DataFlowVisitor._ast_to_dotted_static(node.value)
            if base is None:
                return None
            return f"{base}.{node.attr}"
        return None

    def _attribute_root(self, node: ast.AST) -> str | None:
        """Return the root name of an attribute/subscript chain."""
        while isinstance(node, ast.Attribute | ast.Subscript):
            node = node.value
        if isinstance(node, ast.Name):
            return node.id
        return None

    @staticmethod
    def _generate_flow_id(source: str, target: str, flow_type: str, line_num: int) -> str:
        """Generate a deterministic flow edge ID.

        Args:
            source: Source symbol name.
            target: Target symbol name.
            flow_type: Edge type (reads/writes/mutates/depends_on).
            line_num: Line number where the flow occurs.

        Returns:
            16-char hex identifier.
        """
        content = f"{source}→{target}:{flow_type}:{line_num}"
        hash_obj = hashlib.sha256(content.encode())
        return hash_obj.hexdigest()[:16]
