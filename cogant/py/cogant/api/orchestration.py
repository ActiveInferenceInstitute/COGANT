"""Shared pipeline orchestration: ingest → graph → translate → export.

CLI, Session, and PipelineRunner delegate here so behavior stays consistent.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from cogant.graph.builder import ProgramGraphBuilder
from cogant.ingest.repo import RepoIngester, RepoSnapshot
from cogant.normalize.canonical import CanonicalNormalizer, LanguageFact
from cogant.process.extractor import ProcessExtractor
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import SemanticMapping
from cogant.statespace.compiler import StateSpaceCompiler
from cogant.static.parser import PythonASTParser
from cogant.translate.confidence import ConfidenceModel
from cogant.translate.engine import TranslationEngine
from cogant.translate.review import ReviewManager
from cogant.translate.rules import (
    ActionRule,
    CircuitBreakerRule,
    ConfigRule,
    ContainmentRule,
    ContextRule,
    DataPipelineRule,
    ErrorBoundaryRule,
    EventBusRule,
    FeatureFlagRule,
    InheritanceRule,
    MutatingSubsystemRule,
    ObservationRule,
    OrchestratorRule,
    PolicyRule,
    PreferenceRule,
    ReadOnlyInputRule,
    RetryPatternRule,
    SingletonAccessRule,
    TestAssertionRule,
)
from cogant.validate.schema_check import SchemaValidator

logger = logging.getLogger(__name__)


def _repo_uri(target: str) -> str:
    """Normalize a target into a canonical repository URI.

    Args:
        target: Local path or URI string.

    Returns:
        A ``file://`` URI when ``target`` is an existing local path,
        otherwise the original string unchanged.
    """
    p = Path(target).expanduser().resolve()
    if p.exists():
        return p.as_uri()
    return target


def _serialize_node(n: Any) -> dict[str, Any]:
    """Convert a program graph Node dataclass into a JSON-friendly dict.

    Args:
        n: A ``Node`` dataclass with at least ``kind`` and optional ``created_at``.

    Returns:
        Dict with enum fields coerced to strings and datetimes ISO-formatted.
    """
    d = asdict(n)
    d["kind"] = n.kind.value if hasattr(n.kind, "value") else str(n.kind)
    if "created_at" in d and isinstance(d["created_at"], datetime):
        d["created_at"] = d["created_at"].isoformat()
    return d


def _serialize_edge(e: Any) -> dict[str, Any]:
    """Convert a program graph Edge dataclass into a JSON-friendly dict.

    Args:
        e: An ``Edge`` dataclass with a ``kind`` enum or string.

    Returns:
        Dict with the kind enum coerced to its string value.
    """
    d = asdict(e)
    d["kind"] = e.kind.value if hasattr(e.kind, "value") else str(e.kind)
    return d


def program_graph_to_dict(pg: ProgramGraph, statistics: dict[str, Any] | None = None) -> dict[str, Any]:
    """JSON-friendly program graph summary."""
    return {
        "type": "program_graph",
        "metadata": {
            "repo_uri": pg.metadata.repo_uri,
            "languages": sorted(pg.metadata.languages),
            "version": pg.metadata.version,
        },
        "nodes": {nid: _serialize_node(n) for nid, n in pg.nodes.items()},
        "edges": {eid: _serialize_edge(e) for eid, e in pg.edges.items()},
        "statistics": statistics or {},
    }


def _default_translation_engine() -> TranslationEngine:
    """Construct a TranslationEngine seeded with the full default rule set.

    Registers every translation rule shipped with COGANT so that the
    default pipeline produces the maximum number of real semantic
    mappings. Callers that want a restricted set can construct their
    own engine and register the subset they need.

    Returns:
        A ready-to-use ``TranslationEngine`` instance with all 18 rules.
    """
    eng = TranslationEngine()
    eng.register_rule(ReadOnlyInputRule())
    eng.register_rule(MutatingSubsystemRule())
    eng.register_rule(OrchestratorRule())
    eng.register_rule(TestAssertionRule())
    eng.register_rule(RetryPatternRule())
    eng.register_rule(EventBusRule())
    eng.register_rule(ConfigRule())
    eng.register_rule(FeatureFlagRule())
    eng.register_rule(ObservationRule())
    eng.register_rule(ActionRule())
    eng.register_rule(PolicyRule())
    eng.register_rule(PreferenceRule())
    eng.register_rule(ContextRule())
    eng.register_rule(InheritanceRule())
    eng.register_rule(ContainmentRule())
    eng.register_rule(DataPipelineRule())
    eng.register_rule(ErrorBoundaryRule())
    eng.register_rule(SingletonAccessRule())
    eng.register_rule(CircuitBreakerRule())
    return eng


def run_ingest(bundle_target: str, bundle: Any) -> dict[str, Any]:
    """Run the ingest stage: snapshot a local repository into the bundle.

    Walks the target path with ``RepoIngester`` (including test files,
    without checksums for speed), stores the ``RepoSnapshot`` under
    ``bundle.artifacts['repo_snapshot']``, and computes a per-language
    file count distribution.

    Args:
        bundle_target: Local path (or path-like string) to the repository root.
        bundle: Pipeline bundle used to accumulate stage artifacts.

    Returns:
        Stage result dict with ``type``, ``target``, ``file_count``,
        ``language_distribution``, and resolved ``root`` path.
    """
    root = Path(bundle_target).expanduser().resolve()
    ingester = RepoIngester()
    snapshot = ingester.ingest_local(root, include_test_files=True, compute_checksums=False)
    bundle.artifacts["repo_snapshot"] = snapshot

    lang_dist: dict[str, int] = {}
    for f in snapshot.files:
        if f.language:
            lang_dist[f.language] = lang_dist.get(f.language, 0) + 1

    return {
        "type": "ingest",
        "target": bundle_target,
        "file_count": len(snapshot.files),
        "language_distribution": lang_dist,
        "root": str(snapshot.root_path),
    }


def run_static(bundle: Any) -> dict[str, Any]:
    """Run the static analysis stage: parse every Python file with the AST parser.

    Uses ``PythonASTParser`` to build a ``ParsedModule`` per Python source
    file in the previously-ingested snapshot, recording function, class,
    import, and error counts. Detailed per-module summaries are stored in
    ``bundle.artifacts['parsed_modules_detail']`` for downstream stages.

    Args:
        bundle: Pipeline bundle; must already contain ``repo_snapshot``.

    Returns:
        Stage result dict with type, empty node/edge placeholders,
        a ``symbols`` count, and detailed ``modules`` list.

    Raises:
        RuntimeError: If the ingest stage has not yet populated ``repo_snapshot``.
    """
    snapshot: RepoSnapshot | None = bundle.artifacts.get("repo_snapshot")
    if snapshot is None:
        raise RuntimeError("ingest stage must run before static")

    parser = PythonASTParser()
    modules: list[dict[str, Any]] = []
    for finfo in snapshot.files:
        if finfo.language != "python":
            continue
        mod = parser.parse_file(Path(finfo.path))
        modules.append(
            {
                "path": str(mod.file_path),
                "relative_path": finfo.relative_path,
                "functions": len(mod.functions),
                "classes": len(mod.classes),
                "imports": len(mod.imports),
                "errors": list(mod.errors),
            }
        )

    bundle.artifacts["parsed_modules_detail"] = modules
    return {
        "type": "static_analysis",
        "nodes": [],
        "edges": [],
        "symbols": {"python_modules_parsed": len(modules)},
        "modules": modules,
    }


def run_normalize(bundle: Any) -> dict[str, Any]:
    """Run the normalize stage: canonicalize language-specific facts.

    For every Python file in the snapshot, re-parses the module and emits
    ``LanguageFact`` objects for the module, its classes, its functions,
    and every method inside each class. Each fact is passed through
    ``CanonicalNormalizer`` to produce a ``NormalizedFact`` with a
    stable ``qualified_name``. Accumulated normalized facts are stored in
    ``bundle.artifacts['normalized_facts']``.

    Args:
        bundle: Pipeline bundle; must already contain ``repo_snapshot``.

    Returns:
        Stage result dict with the ``fact_count`` and the list of normalized
        facts as the ``nodes`` field.

    Raises:
        RuntimeError: If the ingest stage has not run.
    """
    snapshot: RepoSnapshot | None = bundle.artifacts.get("repo_snapshot")
    if snapshot is None:
        raise RuntimeError("ingest stage must run before normalize")

    parser = PythonASTParser()
    normalizer = CanonicalNormalizer()
    facts_out: list[dict[str, Any]] = []

    for finfo in snapshot.files:
        if finfo.language != "python":
            continue
        mod = parser.parse_file(Path(finfo.path))
        rel = finfo.relative_path
        mod_qn = rel.replace("/", ".").removesuffix(".py").removesuffix("__init__")

        lf_mod = LanguageFact(
            fact_type="module",
            language="python",
            data={
                "name": Path(rel).stem,
                "qualified_name": mod_qn or Path(rel).stem,
                "path": rel,
            },
        )
        nf = normalizer.normalize(lf_mod)
        if nf:
            facts_out.append({"kind": nf.node_kind.value, "qualified_name": nf.qualified_name, "path": rel})

        for cls in mod.classes:
            lf = LanguageFact(
                fact_type="class",
                language="python",
                data={
                    "name": cls.name,
                    "qualified_name": f"{mod_qn}.{cls.name}" if mod_qn else cls.name,
                    "path": rel,
                    "visibility": "public",
                    "decorators": cls.decorators,
                },
            )
            nfx = normalizer.normalize(lf)
            if nfx:
                facts_out.append(
                    {"kind": nfx.node_kind.value, "qualified_name": nfx.qualified_name, "path": rel}
                )

        for fn in mod.functions:
            lf = LanguageFact(
                fact_type="function",
                language="python",
                data={
                    "name": fn.name,
                    "qualified_name": f"{mod_qn}.{fn.name}" if mod_qn else fn.name,
                    "path": rel,
                },
            )
            nfx = normalizer.normalize(lf)
            if nfx:
                facts_out.append(
                    {"kind": nfx.node_kind.value, "qualified_name": nfx.qualified_name, "path": rel}
                )

        for cls in mod.classes:
            for meth in cls.methods:
                lf = LanguageFact(
                    fact_type="method",
                    language="python",
                    data={
                        "name": meth.name,
                        "qualified_name": f"{mod_qn}.{cls.name}.{meth.name}" if mod_qn else f"{cls.name}.{meth.name}",
                        "path": rel,
                    },
                )
                nfx = normalizer.normalize(lf)
                if nfx:
                    facts_out.append(
                        {"kind": nfx.node_kind.value, "qualified_name": nfx.qualified_name, "path": rel}
                    )

    bundle.artifacts["normalized_facts"] = facts_out
    return {
        "type": "normalized",
        "nodes": facts_out,
        "edges": [],
        "fact_count": len(facts_out),
    }


def run_graph(bundle: Any, target: str) -> dict[str, Any]:
    """Run the graph stage: build a typed ``ProgramGraph`` with real edges.

    Re-parses every Python module in the snapshot and builds a typed
    ``ProgramGraph`` with:

    * ``MODULE``/``CLASS``/``METHOD``/``FUNCTION`` nodes
    * ``CONTAINS`` edges - module → class, class → method, module → function
    * ``IMPORTS`` edges - module → imported in-repo module
    * ``INHERITS`` edges - class → base class (resolved in-repo)
    * ``READS``/``WRITES`` edges - method → enclosing class via
      ``self.attr`` dataflow

    The finalized graph is stored under
    ``bundle.artifacts['_program_graph']``. Without edges the translate
    and statespace stages degenerate to zero mappings, so this stage
    deliberately mirrors the ``build_rich_graph`` helper used by the
    thin examples.

    Args:
        bundle: Pipeline bundle; must already contain ``repo_snapshot``.
        target: Repository target (local path or URI) used to stamp the
            graph metadata via ``_repo_uri``.

    Returns:
        JSON-friendly program graph dict (see ``program_graph_to_dict``).

    Raises:
        RuntimeError: If the ingest stage has not populated
            ``repo_snapshot``.
    """
    import ast as _ast

    snapshot: RepoSnapshot | None = bundle.artifacts.get("repo_snapshot")
    if snapshot is None:
        raise RuntimeError("ingest stage must run before graph")

    # Ensure normalized_facts exists for downstream consumers even if we
    # don't drive graph construction off it.
    if bundle.artifacts.get("normalized_facts") is None:
        run_normalize(bundle)

    repo_uri = _repo_uri(target)
    repo_root = Path(target).expanduser().resolve()
    builder = ProgramGraphBuilder(repo_uri=repo_uri)

    parser = PythonASTParser()
    parsed: dict[Path, Any] = {}
    for finfo in snapshot.files:
        if finfo.language != "python":
            continue
        path = Path(finfo.path)
        parsed[path] = parser.parse_file(path)

    module_nodes: dict[str, Any] = {}
    class_nodes: dict[str, Any] = {}

    # AST cache: avoid re-parsing the same file for every method it contains.
    # Without caching, _emit_dataflow_edges called ast.parse() once per
    # method, so a file with N methods was parsed N times (O(files × methods)
    # compile calls). With the cache each file is parsed at most once.
    _ast_cache: dict[Path, Any] = {}

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(repo_root))
        except Exception:
            return str(p)

    for file_path, module in parsed.items():
        rel = _rel(file_path)
        module_name = file_path.stem
        module_node = builder.add_node(
            kind=NodeKind.MODULE,
            name=module_name,
            qualified_name=module_name,
            path=rel,
            language="python",
        )
        module_nodes[module_name] = module_node

        for cls in getattr(module, "classes", []) or []:
            class_qname = f"{module_name}.{cls.name}"
            class_node = builder.add_node(
                kind=NodeKind.CLASS,
                name=cls.name,
                qualified_name=class_qname,
                path=rel,
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
                    path=rel,
                    language="python",
                    metadata={"is_method": True},
                )
                builder.add_edge(class_node.id, method_node.id, EdgeKind.CONTAINS)
                _emit_dataflow_edges(
                    builder, method_node, class_node, method.name, file_path, _ast,
                    ast_cache=_ast_cache,
                )

        for func in getattr(module, "functions", []) or []:
            func_qname = f"{module_name}.{func.name}"
            func_node = builder.add_node(
                kind=NodeKind.FUNCTION,
                name=func.name,
                qualified_name=func_qname,
                path=rel,
                language="python",
            )
            builder.add_edge(module_node.id, func_node.id, EdgeKind.CONTAINS)

        # IMPORTS edges by in-repo name match
        for imp in getattr(module, "imports", []) or []:
            target_name = getattr(imp, "module", None) or getattr(imp, "name", None)
            if not target_name:
                continue
            head = str(target_name).split(".")[0]
            if head in module_nodes and head != module_name:
                builder.add_edge(
                    module_node.id, module_nodes[head].id, EdgeKind.IMPORTS
                )

    # INHERITS edges.
    # Build a name→node index first so lookup is O(1) instead of O(|classes|)
    # per base class. The original nested loop was O(|classes|² × |bases|),
    # which is tolerable for small repos but degrades for large ones.
    class_by_name: dict[str, Any] = {}
    for other_qname, other_node in class_nodes.items():
        # Later definitions override earlier ones; for duplicate simple
        # names we keep the last-seen (arbitrary but deterministic).
        class_by_name[other_node.name] = other_node

    for class_qname, class_node in class_nodes.items():
        bases = (class_node.metadata or {}).get("bases", [])
        for base in bases:
            other_node = class_by_name.get(base)
            if other_node is not None and other_node.id != class_node.id:
                builder.add_edge(
                    class_node.id, other_node.id, EdgeKind.INHERITS
                )

    pg = builder.finalize()
    bundle.artifacts["_program_graph"] = pg

    stats = builder.get_statistics()
    return program_graph_to_dict(pg, statistics=stats)


def _emit_dataflow_edges(
    builder: ProgramGraphBuilder,
    method_node: Any,
    class_node: Any,
    method_name: str,
    file_path: Path,
    ast_mod: Any,
    ast_cache: dict[Path, Any] | None = None,
) -> None:
    """Emit ``READS``/``WRITES`` edges from a method to its enclosing class.

    Walks the method body for ``self.attr = ...`` (writes) and
    ``self.attr`` (reads). Mirrors ``_add_dataflow_edges`` in
    ``examples/thin_orchestrated/_common.py``.

    Args:
        ast_cache: Optional dict mapping ``Path`` → parsed AST tree.
            When supplied, each file is parsed at most once regardless of
            how many methods it contains. This reduces graph-stage time
            from O(files × methods) AST-compile calls to O(files).
    """
    if ast_cache is not None and file_path in ast_cache:
        tree = ast_cache[file_path]
        if tree is None:
            return  # Previously failed to parse
    else:
        try:
            tree = ast_mod.parse(file_path.read_text())
        except (SyntaxError, UnicodeDecodeError, OSError) as e:
            logger.debug("Skipping dataflow edges for %s: %s", file_path, e)
            if ast_cache is not None:
                ast_cache[file_path] = None  # Cache the failure
            return
        if ast_cache is not None:
            ast_cache[file_path] = tree

    for node in ast_mod.walk(tree):
        if not isinstance(
            node, (ast_mod.FunctionDef, ast_mod.AsyncFunctionDef)
        ):
            continue
        if node.name != method_name:
            continue

        writes = 0
        reads = 0
        # Track Attribute nodes that are pure assignment targets so we
        # don't double-count them as reads. AugAssign targets (``self.x +=
        # 1``) are both a read and a write, so they stay outside this set.
        write_targets: set[int] = set()
        for child in ast_mod.walk(node):
            if isinstance(child, ast_mod.Assign):
                for tgt in child.targets:
                    if (
                        isinstance(tgt, ast_mod.Attribute)
                        and isinstance(tgt.value, ast_mod.Name)
                        and tgt.value.id == "self"
                    ):
                        writes += 1
                        write_targets.add(id(tgt))
            if isinstance(child, ast_mod.AugAssign):
                if (
                    isinstance(child.target, ast_mod.Attribute)
                    and isinstance(child.target.value, ast_mod.Name)
                    and child.target.value.id == "self"
                ):
                    writes += 1

        for child in ast_mod.walk(node):
            if isinstance(child, ast_mod.Attribute):
                if (
                    isinstance(child.value, ast_mod.Name)
                    and child.value.id == "self"
                    and id(child) not in write_targets
                ):
                    # AugAssign targets are also reads (they read-modify-write)
                    reads += 1

        if writes > 0:
            builder.add_edge(method_node.id, class_node.id, EdgeKind.WRITES)
        if reads > 0:
            builder.add_edge(method_node.id, class_node.id, EdgeKind.READS)
        return


def run_translate(bundle: Any) -> dict[str, Any]:
    """Run the translate stage: apply rules to produce semantic mappings.

    If the bundle has not already installed a custom translation engine,
    one is built with ``_default_translation_engine``. Every rule matches
    on the program graph and emits ``SemanticMapping`` records. The
    mappings are then scored with ``ConfidenceModel`` and registered
    with a ``ReviewManager`` so a human review loop can later layer on
    accept/edit/reject actions.

    Args:
        bundle: Pipeline bundle; must already contain ``_program_graph``.

    Returns:
        Stage result dict with a GNN-oriented shape: ``node_features``
        (one entry per mapping), ``edge_indices``, ``embeddings``, and
        counts.

    Raises:
        RuntimeError: If the graph stage has not run.
    """
    pg: ProgramGraph | None = bundle.artifacts.get("_program_graph")
    if pg is None:
        raise RuntimeError("graph stage must run before translate")

    engine = bundle.artifacts.get("_translation_engine")
    if engine is None:
        engine = _default_translation_engine()
        bundle.artifacts["_translation_engine"] = engine

    mappings = engine.translate(pg)
    bundle.artifacts["_semantic_mappings"] = {m.id: m for m in mappings}

    model = ConfidenceModel()
    model.score_batch(mappings)
    review = ReviewManager()
    for m in mappings:
        review.add_mapping(m)

    return {
        "type": "gnn_model",
        "node_features": [{"id": m.id, "kind": m.kind.value} for m in mappings],
        "edge_indices": [],
        "embeddings": {},
        "mapping_count": len(mappings),
        "mapping_ids": [m.id for m in mappings],
    }


def run_statespace(bundle: Any, target: str) -> dict[str, Any]:
    """Run the state-space compilation stage.

    Feeds the program graph and semantic mappings into ``StateSpaceCompiler``
    to emit a ``StateSpaceModel`` containing variables, observations,
    actions, transitions, likelihoods, and preferences. The compiled model
    is stored under ``bundle.artifacts['_state_space_model']``.

    Args:
        bundle: Pipeline bundle; must already contain ``_program_graph``.
        target: Repository target used as the ``schema_name`` basis.

    Returns:
        Stage result dict listing top-level state-space identifiers.

    Raises:
        RuntimeError: If the graph stage has not run.
    """
    pg: ProgramGraph | None = bundle.artifacts.get("_program_graph")
    mappings: dict[str, SemanticMapping] = bundle.artifacts.get("_semantic_mappings") or {}
    if pg is None:
        raise RuntimeError("graph stage must run before statespace")

    schema = Path(target).name or "default"
    compiler = StateSpaceCompiler(pg, schema_name=schema)
    model = compiler.compile(mappings)
    bundle.artifacts["_state_space_model"] = model

    return {
        "type": "state_space_model",
        "states": list(model.variables.keys()),
        "observations": list(model.observations.keys()),
        "actions": list(model.actions.keys()),
        "policies": list(model.preferences.keys()),
        "schema_name": model.schema_name,
    }


def run_process(bundle: Any, target: str) -> dict[str, Any]:
    """Run the process extraction stage.

    Uses ``ProcessExtractor`` to derive a ``ProcessModel`` from the program
    graph: workflow stages, connections, and policies. Stored under
    ``bundle.artifacts['_process_model']``.

    Args:
        bundle: Pipeline bundle; must already contain ``_program_graph``.
        target: Repository target used as the ``schema_name`` basis.

    Returns:
        Stage result dict listing stage identifiers and dependency keys.

    Raises:
        RuntimeError: If the graph stage has not run.
    """
    pg: ProgramGraph | None = bundle.artifacts.get("_program_graph")
    if pg is None:
        raise RuntimeError("graph stage must run before process")

    schema = Path(target).name or "default"
    extractor = ProcessExtractor(pg, schema_name=schema)
    pm = extractor.extract()
    bundle.artifacts["_process_model"] = pm

    return {
        "type": "process_model",
        "stages": list(pm.stages.keys()),
        "dependencies": list(pm.connections.keys()),
        "timeline": [],
        "stage_count": len(pm.stages),
    }


def run_export(bundle: Any, output_dir: str) -> dict[str, Any]:
    """Run the export stage: write all intermediate artifacts to disk.

    Writes any available program graph, state-space model, process model,
    and translation result into ``output_dir`` as JSON. Missing artifacts
    are skipped silently; dataclasses that cannot be serialized fall back
    to a minimal identity record. The list of written paths is stored on
    ``bundle.artifacts['export_paths']``.

    Args:
        bundle: Pipeline bundle with whatever artifacts the earlier stages
            have populated.
        output_dir: Destination directory (created if missing).

    Returns:
        Stage result dict with the output directory and the list of
        artifact paths written.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    pg: ProgramGraph | None = bundle.artifacts.get("_program_graph")
    if pg is not None:
        stats: dict[str, Any] = {}
        p = out / "program_graph.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(program_graph_to_dict(pg, statistics=stats), f, indent=2, default=str)
        written.append(str(p))

    ss = bundle.artifacts.get("_state_space_model")
    if ss is not None:
        p = out / "state_space.json"
        with open(p, "w", encoding="utf-8") as f:
            try:
                json.dump(asdict(ss), f, indent=2, default=str)
            except (TypeError, ValueError):
                json.dump({"schema_name": ss.schema_name, "id": ss.id}, f, indent=2)
        written.append(str(p))

    pm = bundle.artifacts.get("_process_model")
    if pm is not None:
        p = out / "process_model.json"
        with open(p, "w", encoding="utf-8") as f:
            try:
                json.dump(asdict(pm), f, indent=2, default=str)
            except (TypeError, ValueError):
                json.dump({"id": pm.id, "schema_name": pm.schema_name}, f, indent=2)
        written.append(str(p))

    tr = bundle.stage_results.get("translate", {})
    if tr:
        p = out / "gnn_model.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(tr, f, indent=2, default=str)
        written.append(str(p))

    # Build the full GNN package when all ingredients are available.
    # This unifies the CLI pipeline with ``examples/orchestrate_roundtrip.py``
    # so that ``cogant translate`` always produces a gnn_package/ directory
    # that can be validated by :class:`GNNValidator`.
    mappings_dict = bundle.artifacts.get("_semantic_mappings") or {}
    if pg is not None and ss is not None and pm is not None:
        try:
            from cogant.gnn.package import GNNPackageBuilder

            package_dir = out / "gnn_package"
            builder = GNNPackageBuilder(pg, ss, pm, mappings_dict)
            manifest = builder.build(str(package_dir))
            written.append(str(package_dir))
            bundle.artifacts["_gnn_package_dir"] = str(package_dir)
            bundle.artifacts["_gnn_package_manifest"] = manifest
        except Exception as e:  # pragma: no cover - defensive
            # A GNN build failure should not abort the entire export stage.
            bundle.artifacts.setdefault("export_warnings", []).append(
                f"GNN package build failed: {e}"
            )

    # Also render PNGs for every Mermaid/SVG/dot/network artifact in the
    # export directory. This unifies ``cogant translate``/``cogant export``
    # and ``examples/orchestrate_roundtrip.py`` on the same raster contract:
    # every visualization gets a PNG. Failures are reported as warnings and
    # never abort the export stage.
    try:
        from cogant.viz.png_export import render_all_pngs

        png_result = render_all_pngs(out, state_space=ss, process_model=pm)
        png_total = sum(len(v) for v in png_result.values())
        bundle.artifacts["png_paths"] = {
            cat: [str(p) for p in paths] for cat, paths in png_result.items()
        }
        if png_total == 0:
            bundle.artifacts.setdefault("export_warnings", []).append(
                "render_all_pngs wrote 0 files"
            )
    except Exception as e:  # pragma: no cover - defensive
        bundle.artifacts.setdefault("export_warnings", []).append(
            f"PNG rendering failed: {e}"
        )

    bundle.artifacts["export_paths"] = written
    return {"type": "export", "output_dir": output_dir, "artifacts": written}


def run_validate(bundle: Any) -> dict[str, Any]:
    """Run the validate stage: schema-check the program graph.

    Runs ``SchemaValidator.validate_program_graph`` and partitions issues
    into warnings and errors. A missing program graph returns a synthetic
    "no graph" validation result rather than raising, so this stage is
    always safe to call.

    Args:
        bundle: Pipeline bundle; ``_program_graph`` is optional.

    Returns:
        Stage result dict with ``passed`` boolean, issue counts, warnings,
        and up to the first 50 issues as structured dicts.
    """
    pg: ProgramGraph | None = bundle.artifacts.get("_program_graph")
    if pg is None:
        return {
            "type": "validation",
            "passed": False,
            "checks": {"program_graph": "missing"},
            "warnings": ["No program graph to validate"],
        }

    validator = SchemaValidator()
    issues = validator.validate_program_graph(pg)
    warnings = [f"{i.category}: {i.message}" for i in issues if i.severity == "warning"]
    errors = [i for i in issues if i.severity == "error"]

    # If a GNN package was just built during export, run the full GNN
    # validator over it and surface the result alongside the schema check.
    gnn_pkg = bundle.artifacts.get("_gnn_package_dir")
    gnn_result: dict[str, Any] | None = None
    if gnn_pkg:
        try:
            from cogant.gnn.validator import GNNValidator

            result = GNNValidator().validate_package(str(gnn_pkg))
            gnn_result = {
                "valid": result.valid,
                "score": result.score,
                "error_count": len(result.errors),
                "warning_count": len(result.warnings),
                "package_dir": str(gnn_pkg),
            }
        except Exception as e:  # pragma: no cover - defensive
            gnn_result = {"error": str(e), "package_dir": str(gnn_pkg)}

    payload: dict[str, Any] = {
        "type": "validation",
        "passed": len(errors) == 0,
        "checks": {"issue_count": len(issues), "error_count": len(errors)},
        "warnings": warnings,
        "issues": [asdict(i) for i in issues[:50]],
    }
    if gnn_result is not None:
        payload["gnn_validation"] = gnn_result
    return payload


def run_dynamic(bundle: Any, coverage_path: str | None = None, trace_path: str | None = None) -> dict[str, Any]:
    """Enrich the program graph with coverage and trace data.

    Args:
        bundle: Pipeline bundle containing the program graph.
        coverage_path: Path to coverage data (Cobertura XML or .coverage SQLite).
        trace_path: Path to Chrome DevTools trace JSON.

    Returns:
        Enrichment summary with counts of enriched nodes and edges.
    """
    pg = bundle.artifacts.get("_program_graph")
    if pg is None:
        return {"type": "dynamic_enrichment", "skipped": True, "reason": "no program graph"}
    from cogant.dynamic.enrichment import enrich_graph
    summary = enrich_graph(pg, coverage_path=coverage_path, trace_path=trace_path)
    return {"type": "dynamic_enrichment", **summary}
