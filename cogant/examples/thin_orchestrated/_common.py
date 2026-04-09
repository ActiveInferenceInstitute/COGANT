"""Shared helpers for the thin orchestrated examples.

These examples deliberately avoid pulling in the full RoundtripOrchestrator
so each script demonstrates one stage's API in isolation. The two key
helpers below are:

* ``parse_args`` - uniform CLI for every script
* ``build_rich_graph`` - builds a typed ``ProgramGraph`` with both nodes
  and edges (containment, calls, imports, inheritance, dataflow), so the
  downstream stages have something interesting to chew on
"""

from __future__ import annotations

import argparse
import ast as ast_mod
import logging
from pathlib import Path

from cogant.api.bundle import Bundle
from cogant.graph.builder import ProgramGraphBuilder
from cogant.ingest.repo import RepoIngester
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.static.parser import PythonASTParser


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET = REPO_ROOT / "examples" / "control_positive" / "event_pipeline"


def configure_logging() -> None:
    """Set up a quiet logger so the demos focus on stage outputs, not noise."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def parse_args(stage_name: str) -> argparse.Namespace:
    """Parse a uniform CLI for every thin example.

    Every script accepts:

    * ``--target``: repository path (defaults to the event_pipeline fixture,
      which is rich enough that every stage produces visible output)
    * ``--output-dir``: where to write artifacts (defaults to ``output/thin/<stage>``)
    """
    parser = argparse.ArgumentParser(description=f"COGANT thin example: {stage_name}")
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TARGET,
        help="Path to the target repository (default: event_pipeline fixture)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "output" / "thin" / stage_name,
        help="Directory to write artifacts (default: output/thin/<stage>)",
    )
    return parser.parse_args()


def make_bundle(target: Path) -> Bundle:
    """Construct a fresh ``Bundle`` for the given target."""
    return Bundle(target=str(target))


def banner(title: str) -> None:
    """Print a section header so demos read clearly in the terminal."""
    line = "=" * 60
    print(f"\n{line}\n  {title}\n{line}")


def build_rich_graph(repo_path: Path) -> ProgramGraph:
    """Build a typed ``ProgramGraph`` with full edge inference.

    This mirrors the work that ``orchestrate_roundtrip._build_program_graph``
    does, condensed into a single helper. It walks every Python file in
    the repo, creates ``MODULE``/``CLASS``/``METHOD``/``FUNCTION`` nodes,
    and emits the following edge kinds:

    * ``CONTAINS`` - module → class, class → method, module → function
    * ``IMPORTS`` - module → imported module
    * ``INHERITS`` - class → base class
    * ``WRITES``/``READS`` - method → enclosing class via dataflow
      (detected by walking ``self.attr = value`` and ``self.attr`` reads)

    Without these edges the translation rules and state-space compiler
    have nothing to match on, so every thin example past the graph stage
    relies on this helper rather than the bare ``run_graph`` orchestration
    primitive.
    """
    ingester = RepoIngester()
    snapshot = ingester.ingest_local(
        repo_path, include_test_files=True, compute_checksums=False
    )
    parser = PythonASTParser()
    parsed: dict[Path, object] = {}
    for finfo in snapshot.files:
        if finfo.language != "python":
            continue
        path = Path(finfo.path)
        parsed[path] = parser.parse_file(path)

    builder = ProgramGraphBuilder(repo_uri=str(repo_path))
    module_nodes: dict[str, object] = {}
    class_nodes: dict[str, object] = {}

    for file_path, module in parsed.items():
        rel = file_path.relative_to(repo_path)
        module_name = file_path.stem
        module_node = builder.add_node(
            kind=NodeKind.MODULE,
            name=module_name,
            qualified_name=module_name,
            path=str(rel),
            language="python",
        )
        module_nodes[module_name] = module_node

        for cls in getattr(module, "classes", []) or []:
            class_qname = f"{module_name}.{cls.name}"
            class_node = builder.add_node(
                kind=NodeKind.CLASS,
                name=cls.name,
                qualified_name=class_qname,
                path=str(rel),
                language="python",
                metadata={"bases": list(getattr(cls, "bases", []) or [])},
            )
            class_nodes[class_qname] = class_node
            builder.add_edge(module_node.id, class_node.id, EdgeKind.CONTAINS)

            for method in getattr(cls, "methods", []) or []:
                method_qname = f"{class_qname}.{method.name}"
                method_kind = (
                    NodeKind.METHOD if hasattr(NodeKind, "METHOD") else NodeKind.FUNCTION
                )
                method_node = builder.add_node(
                    kind=method_kind,
                    name=method.name,
                    qualified_name=method_qname,
                    path=str(rel),
                    language="python",
                    metadata={"is_method": True},
                )
                builder.add_edge(class_node.id, method_node.id, EdgeKind.CONTAINS)
                _add_dataflow_edges(builder, method_node, class_node, method.name, file_path)

        for func in getattr(module, "functions", []) or []:
            func_qname = f"{module_name}.{func.name}"
            func_node = builder.add_node(
                kind=NodeKind.FUNCTION,
                name=func.name,
                qualified_name=func_qname,
                path=str(rel),
                language="python",
            )
            builder.add_edge(module_node.id, func_node.id, EdgeKind.CONTAINS)

        # IMPORTS edges by name match within the repo
        for imp in getattr(module, "imports", []) or []:
            target_name = getattr(imp, "module", None) or getattr(imp, "name", None)
            if not target_name:
                continue
            head = str(target_name).split(".")[0]
            if head in module_nodes and head != module_name:
                builder.add_edge(module_node.id, module_nodes[head].id, EdgeKind.IMPORTS)

    # INHERITS edges
    for class_qname, class_node in class_nodes.items():
        bases = (class_node.metadata or {}).get("bases", [])
        for base in bases:
            for other_qname, other_node in class_nodes.items():
                if other_node.name == base and other_qname != class_qname:
                    builder.add_edge(class_node.id, other_node.id, EdgeKind.INHERITS)
                    break

    return builder.finalize()


def _add_dataflow_edges(
    builder: ProgramGraphBuilder,
    method_node: object,
    class_node: object,
    method_name: str,
    file_path: Path,
) -> None:
    """Walk a method body to emit ``WRITES``/``READS`` edges to the enclosing class."""
    try:
        tree = ast_mod.parse(file_path.read_text())
    except Exception:
        return

    for node in ast_mod.walk(tree):
        if not isinstance(node, (ast_mod.FunctionDef, ast_mod.AsyncFunctionDef)):
            continue
        if node.name != method_name:
            continue

        writes = 0
        reads = 0
        for child in ast_mod.walk(node):
            if isinstance(child, ast_mod.Assign):
                for target in child.targets:
                    if (
                        isinstance(target, ast_mod.Attribute)
                        and isinstance(target.value, ast_mod.Name)
                        and target.value.id == "self"
                    ):
                        writes += 1
            if isinstance(child, ast_mod.AugAssign):
                if (
                    isinstance(child.target, ast_mod.Attribute)
                    and isinstance(child.target.value, ast_mod.Name)
                    and child.target.value.id == "self"
                ):
                    writes += 1
            if isinstance(child, ast_mod.Attribute):
                if isinstance(child.value, ast_mod.Name) and child.value.id == "self":
                    reads += 1

        if writes > 0:
            builder.add_edge(method_node.id, class_node.id, EdgeKind.WRITES)
        if reads > writes:
            builder.add_edge(method_node.id, class_node.id, EdgeKind.READS)
        return
