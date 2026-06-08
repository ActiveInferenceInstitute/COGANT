"""Shared pipeline orchestration: ingest → graph → translate → export.

CLI, Session, and PipelineRunner delegate here so behavior stays consistent.
"""

from __future__ import annotations

import json
import logging
import tempfile
from collections.abc import AsyncGenerator
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from cogant.api.bundle import Bundle
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
from cogant.translate.default_engine import (
    default_translation_engine as _default_translation_engine,
)
from cogant.translate.evidence import build_rule_evidence_trace
from cogant.translate.review import ReviewManager
from cogant.validate.schema_check import SchemaValidator

logger = logging.getLogger(__name__)


__all__ = [
    "run_ingest",
    "run_static",
    "run_normalize",
    "run_graph",
    "run_translate",
    "run_statespace",
    "run_process",
    "run_export",
    "run_validate",
    "run_dynamic",
    "program_graph_to_dict",
    "translate_source",
    "translate_stream",
    "translate_batch",
]


# ---------------------------------------------------------------------------
# Language extension mapping for in-memory source translation
# ---------------------------------------------------------------------------

_LANGUAGE_EXTENSIONS: dict[str, str] = {
    "python": "py",
    "javascript": "js",
    "typescript": "ts",
}

_DEFAULT_TRANSLATE_STAGES: tuple[str, ...] = (
    "ingest",
    "static",
    "normalize",
    "graph",
    "translate",
    "statespace",
)


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


def program_graph_to_dict(
    pg: ProgramGraph, statistics: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Serialize a ProgramGraph to a JSON-friendly summary dict.

    Converts all node and edge dataclasses to plain dicts with enum
    values coerced to strings. The result is suitable for ``json.dump``
    without a custom encoder.

    Args:
        pg: The finalized program graph to serialize.
        statistics: Optional statistics dict (e.g. from
            ``ProgramGraphBuilder.get_statistics()``) to embed under
            the ``"statistics"`` key.

    Returns:
        Dict with keys ``type``, ``metadata``, ``nodes``, ``edges``,
        and ``statistics``.
    """
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


def _filter_semantic_mappings(
    mappings: list[SemanticMapping],
    *,
    min_confidence: float,
) -> list[SemanticMapping]:
    """Keep only mappings whose scored confidence meets ``min_confidence``."""
    return [m for m in mappings if float(m.confidence_score) >= min_confidence]


def run_ingest(bundle_target: str, bundle: Any) -> dict[str, Any]:
    """Run the ingest stage: snapshot a local repository into the bundle.

    Walks the target path with ``RepoIngester`` (including test files,
    without checksums for speed), stores the ``RepoSnapshot`` under
    ``bundle.artifacts['repo_snapshot']``, and computes a per-language
    file count distribution.

    When ``bundle.metadata['_incremental']`` is present, the snapshot's
    ``files`` list is filtered down to just the subset whose absolute
    paths appear in ``changed_files``. This lets downstream stages
    re-parse only the modified subset of a large repository.

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

    # Honor incremental mode by shrinking the file list to the changed
    # subset. We preserve the snapshot's metadata and dependency info,
    # so downstream stages still see a complete-looking RepoSnapshot
    # object, just with fewer ``files`` entries to iterate.
    incremental = (
        getattr(bundle, "metadata", {}).get("_incremental") if hasattr(bundle, "metadata") else None
    )
    total_files = len(snapshot.files)
    if incremental and incremental.get("changed_files"):
        changed_set = {str(Path(p).resolve()) for p in incremental["changed_files"]}
        filtered = [f for f in snapshot.files if str(Path(f.path).resolve()) in changed_set]
        snapshot.files = filtered

    bundle.artifacts["repo_snapshot"] = snapshot

    lang_dist: dict[str, int] = {}
    for f in snapshot.files:
        if f.language:
            lang_dist[f.language] = lang_dist.get(f.language, 0) + 1

    result: dict[str, Any] = {
        "type": "ingest",
        "target": bundle_target,
        "file_count": len(snapshot.files),
        "language_distribution": lang_dist,
        "root": str(snapshot.root_path),
    }
    if incremental:
        result["incremental"] = {
            "changed_count": incremental.get("changed_count", 0),
            "total_before_filter": total_files,
        }
    return result


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
            facts_out.append(
                {"kind": nf.node_kind.value, "qualified_name": nf.qualified_name, "path": rel}
            )

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
                        "qualified_name": f"{mod_qn}.{cls.name}.{meth.name}"
                        if mod_qn
                        else f"{cls.name}.{meth.name}",
                        "path": rel,
                    },
                )
                nfx = normalizer.normalize(lf)
                if nfx:
                    facts_out.append(
                        {
                            "kind": nfx.node_kind.value,
                            "qualified_name": nfx.qualified_name,
                            "path": rel,
                        }
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

    # First pass: add MODULE nodes for every parsed file so that IMPORTS
    # edges (processed in the second pass below) can resolve their targets
    # regardless of the order in which files are walked. Previously the
    # IMPORTS resolver ran inside this same loop, which silently dropped
    # any import whose target file was visited *after* the importing
    # module — a non-trivial fraction of dotted-import drops traced to this
    # ordering hazard. See TODO #2 sub-fix.
    parsed_module_meta: dict[Path, tuple[str, str]] = {}
    for file_path, _module in parsed.items():
        rel = _rel(file_path)
        module_name = file_path.stem
        # Build the dotted package-qualified module name (e.g.
        # ``pkg/deep/x.py`` → ``pkg.deep.x``). When a file lives at the
        # repo root, ``dotted_name`` collapses to the bare stem. The
        # dotted form is what ``from pkg.deep import x`` and
        # ``import pkg.util as u`` resolve against — see TODO #2
        # "graph normalization around imports".
        rel_path = Path(rel)
        parts = list(rel_path.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        dotted_name = ".".join(parts) if parts else module_name
        module_node = builder.add_node(
            kind=NodeKind.MODULE,
            name=module_name,
            qualified_name=dotted_name,
            path=rel,
            language="python",
        )
        # Index under both the bare stem and the dotted package-qualified name.
        # Downstream IMPORTS resolution tries the dotted form first, then falls
        # back to the head segment for single-file modules.
        module_nodes[module_name] = module_node
        if dotted_name and dotted_name != module_name:
            module_nodes[dotted_name] = module_node
        parsed_module_meta[file_path] = (rel, dotted_name)

    for file_path, module in parsed.items():
        rel, dotted_name = parsed_module_meta[file_path]
        module_name = file_path.stem
        # Resolve module_node from the index built in the first pass.
        module_node = (
            module_nodes[dotted_name] if dotted_name in module_nodes else module_nodes[module_name]
        )

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
                method_kind = NodeKind.METHOD if hasattr(NodeKind, "METHOD") else NodeKind.FUNCTION
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
                    builder,
                    method_node,
                    class_node,
                    method.name,
                    file_path,
                    _ast,
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

        # IMPORTS edges by in-repo name match.
        #
        # Python's ``from A.B import C`` semantics: ``C`` may be either an
        # attribute *defined in* ``A.B/__init__.py`` OR a submodule at
        # ``A/B/C.py``. Both are valid resolutions; we emit edges to whichever
        # we have in the graph. The candidate sequence prefers the most
        # specific match first.
        #
        # Resolution order:
        #   1. Full dotted "module + imported_name":  ``from pkg.deep import x``
        #      tried as ``pkg.deep.x`` before ``pkg.deep`` — this is the
        #      submodule-name case.
        #   2. Successive parent packages of the bare target:
        #      ``pkg.deep.x`` → ``pkg.deep`` → ``pkg``
        #   3. Bare head segment (single-file module alias).
        #
        # The first hit in ``module_nodes`` (excluding self) wins. This closes
        # the dotted-import under-linking documented in TODO #2
        # (``from pkg.deep import X`` previously missed when ``pkg.deep`` was
        # indexed by file stem only).
        for imp in getattr(module, "imports", []) or []:
            target_name = str(getattr(imp, "module_name", "") or "").lstrip(".")
            import_names = [str(n).lstrip(".") for n in (getattr(imp, "names", []) or [])]
            if not target_name and import_names:
                target_name = import_names[0]
                import_names = []
            if not target_name:
                continue

            candidates: list[str] = []
            # Candidate set 1: target + each imported name (submodule case)
            for n in import_names:
                if n:
                    candidates.append(f"{target_name}.{n}")
            # Candidate set 2: target itself + parent packages
            parts = target_name.split(".")
            for i in range(len(parts), 0, -1):
                candidates.append(".".join(parts[:i]))
            # Candidate set 3: bare head (single-file module alias)
            head = parts[0] if parts else target_name
            if head and head not in candidates:
                candidates.append(head)

            for candidate in candidates:
                if candidate in module_nodes and candidate != dotted_name:
                    builder.add_edge(
                        module_node.id,
                        module_nodes[candidate].id,
                        EdgeKind.IMPORTS,
                    )
                    break

    # INHERITS edges.
    # Build a name→node index first so lookup is O(1) instead of O(|classes|)
    # per base class. The original nested loop was O(|classes|² × |bases|),
    # which is tolerable for small repos but degrades for large ones.
    class_by_name: dict[str, Any] = {}
    for other_node in class_nodes.values():
        # Later definitions override earlier ones; for duplicate simple
        # names we keep the last-seen (arbitrary but deterministic).
        class_by_name[other_node.name] = other_node

    for class_node in class_nodes.values():
        bases = (class_node.metadata or {}).get("bases", [])
        for base in bases:
            other_node = class_by_name.get(base)
            if other_node is not None and other_node.id != class_node.id:
                builder.add_edge(class_node.id, other_node.id, EdgeKind.INHERITS)

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
        if not isinstance(node, ast_mod.FunctionDef | ast_mod.AsyncFunctionDef):
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


def run_translate(
    bundle: Any,
    *,
    min_confidence: float = ConfidenceModel.RUNTIME_ONLY_THRESHOLD,
) -> dict[str, Any]:
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

    model = ConfidenceModel()
    model.score_batch(mappings)
    filtered_mappings = _filter_semantic_mappings(mappings, min_confidence=min_confidence)
    bundle.artifacts["_semantic_mappings"] = {m.id: m for m in filtered_mappings}
    review = ReviewManager()
    for m in filtered_mappings:
        review.add_mapping(m)
    bundle.artifacts["_rule_evidence_trace"] = build_rule_evidence_trace(
        filtered_mappings,
        graph=pg,
        match_log=engine.get_match_log(),
    )

    return {
        "type": "gnn_model",
        "node_features": [{"id": m.id, "kind": m.kind.value} for m in filtered_mappings],
        "edge_indices": [],
        "embeddings": {},
        "mapping_count": len(filtered_mappings),
        "mapping_ids": [m.id for m in filtered_mappings],
        "min_confidence": float(min_confidence),
        "filtered_out_count": len(mappings) - len(filtered_mappings),
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


def run_export(
    bundle: Any,
    output_dir: str,
    *,
    render_visualizations: bool = True,
) -> dict[str, Any]:
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
        render_visualizations: When true, rasterize Mermaid/SVG/dot/network
            artifacts under ``output_dir`` into PNG files. Set false for
            machine-readable summary calls that should not re-render a large
            pre-existing output tree.

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

    trace = bundle.artifacts.get("_rule_evidence_trace")
    if trace:
        p = out / "rule_evidence_trace.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(trace, f, indent=2, default=str)
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
    if render_visualizations:
        try:
            from cogant.viz.png import render_all_pngs

            png_result = render_all_pngs(out, state_space=ss, process_model=pm)
            visualization_paths = {
                cat: [str(p) for p in paths] for cat, paths in png_result.items()
            }
            bundle.artifacts["visualization_paths"] = visualization_paths
            bundle.artifacts["png_paths"] = {
                cat: [path for path in paths if Path(path).suffix.lower() == ".png"]
                for cat, paths in visualization_paths.items()
            }
            visualization_total = sum(len(v) for v in visualization_paths.values())
            if visualization_total == 0:
                bundle.artifacts.setdefault("export_warnings", []).append(
                    "render_all_pngs wrote 0 visualization files"
                )
        except Exception as e:  # pragma: no cover - defensive
            bundle.artifacts.setdefault("export_warnings", []).append(
                f"Visualization rendering failed: {e}"
            )
    else:
        bundle.artifacts["visualization_paths"] = {}
        bundle.artifacts["png_paths"] = {}

    bundle.artifacts["export_paths"] = written
    return {"type": "export", "output_dir": output_dir, "artifacts": written}


def run_validate(
    bundle: Any,
    *,
    upstream_gnn: bool | None = None,
    upstream_pipeline: bool = False,
    upstream_pipeline_output_dir: Path | None = None,
    upstream_pipeline_only_steps: list[int] | None = None,
    upstream_pipeline_skip_steps: list[int] | None = None,
    upstream_pipeline_frameworks: str = "lite",
    upstream_pipeline_llm_model: str | None = None,
) -> dict[str, Any]:
    """Run the validate stage: schema-check the program graph.

    Runs ``SchemaValidator.validate_program_graph`` and partitions issues
    into warnings and errors. A missing program graph returns a synthetic
    "no graph" validation result rather than raising, so this stage is
    always safe to call.

    When ``upstream_pipeline`` is ``True`` and a GNN package directory is
    present at ``bundle.artifacts['_gnn_package_dir']``, the upstream 25-step
    pipeline (Active Inference Institute ``src.main.execute_pipeline_step``)
    is driven over that directory; results are recorded as
    ``bundle.artifacts['upstream_pipeline_steps']`` /
    ``['upstream_pipeline_summary']`` and surfaced as ``warnings`` only —
    upstream failures never fail the validate stage.

    Args:
        bundle: Pipeline bundle; ``_program_graph`` is optional.
        upstream_gnn: Passed to :meth:`cogant.gnn.validator.GNNValidator.validate_package`
            when a GNN package is present (``None`` = default: upstream on unless
            ``COGANT_DISABLE_UPSTREAM_GNN`` is set).
        upstream_pipeline: Master switch for the 25-step pass.
        upstream_pipeline_output_dir: Where upstream writes per-step output.
            Defaults to ``<gnn_package_dir>/../upstream_pipeline``.
        upstream_pipeline_only_steps: Restrict to these step indices.
        upstream_pipeline_skip_steps: Drop these step indices (defaults to
            ``[11, 12]`` when ``None``).
        upstream_pipeline_frameworks: Forwarded to upstream render/execute.
        upstream_pipeline_llm_model: Override ``OLLAMA_MODEL`` for step 13.

    Returns:
        Stage result dict with ``passed`` boolean, issue counts, warnings,
        and up to the first 50 issues as structured dicts. When the upstream
        pass ran, ``upstream_pipeline`` carries its summary.
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
            from cogant.gnn.upstream_bridge import parse_upstream_model_gnn_md
            from cogant.gnn.validator import GNNValidator

            result = GNNValidator().validate_package(str(gnn_pkg), upstream_gnn=upstream_gnn)
            parse_summary: dict[str, Any] | None = None
            try:
                parse_summary = parse_upstream_model_gnn_md(str(gnn_pkg))
            except Exception as parse_exc:  # pragma: no cover - defensive
                parse_summary = {"error": str(parse_exc)}
            gnn_result = {
                "valid": result.valid,
                "score": result.score,
                "error_count": len(result.errors),
                "warning_count": len(result.warnings),
                "package_dir": str(gnn_pkg),
                "details": result.to_dict().get("details", {}),
                "upstream_parse_summary": parse_summary,
            }
        except Exception as e:  # pragma: no cover - defensive
            gnn_result = {"error": str(e), "package_dir": str(gnn_pkg)}

    upstream_pipeline_summary: dict[str, Any] | None = None
    if upstream_pipeline and gnn_pkg:
        try:
            from cogant.gnn.upstream_bridge.pipeline import (
                UpstreamPipelineConfig,
                run_upstream_pipeline,
            )

            target_pkg = Path(gnn_pkg).resolve()
            out_dir = (
                upstream_pipeline_output_dir
                if upstream_pipeline_output_dir is not None
                else target_pkg.parent / "upstream_pipeline"
            )
            cfg = UpstreamPipelineConfig(
                target_dir=target_pkg,
                output_dir=out_dir,
                only_steps=upstream_pipeline_only_steps,
                skip_steps=(
                    list(upstream_pipeline_skip_steps)
                    if upstream_pipeline_skip_steps is not None
                    else [11, 12]
                ),
                frameworks=upstream_pipeline_frameworks,
                llm_model=upstream_pipeline_llm_model,
            )
            pipeline_result = run_upstream_pipeline(cfg)
            upstream_pipeline_summary = pipeline_result.to_dict()
            bundle.artifacts["upstream_pipeline_steps"] = [
                s.to_dict() for s in pipeline_result.steps
            ]
            bundle.artifacts["upstream_pipeline_summary"] = upstream_pipeline_summary
            for step in pipeline_result.steps:
                if not step.success:
                    msg = f"upstream step {step.step_index:02d} {step.script}: {step.status}"
                    if step.error:
                        msg += f" — {step.error}"
                    warnings.append(msg)
            if not pipeline_result.available and pipeline_result.error:
                warnings.append(f"upstream pipeline unavailable: {pipeline_result.error}")
        except Exception as exc:  # pragma: no cover - defensive
            warnings.append(f"upstream pipeline pass failed: {exc}")

    payload: dict[str, Any] = {
        "type": "validation",
        "passed": len(errors) == 0,
        "checks": {"issue_count": len(issues), "error_count": len(errors)},
        "warnings": warnings,
        "issues": [asdict(i) for i in issues[:50]],
    }
    if gnn_result is not None:
        payload["gnn_validation"] = gnn_result
    if upstream_pipeline_summary is not None:
        payload["upstream_pipeline"] = upstream_pipeline_summary
    return payload


def run_dynamic(
    bundle: Any, coverage_path: str | None = None, trace_path: str | None = None
) -> dict[str, Any]:
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


# ---------------------------------------------------------------------------
# Streaming and batch orchestration
# ---------------------------------------------------------------------------


def _materialize_source_dir(language: str, source_code: str) -> tempfile.TemporaryDirectory:  # type: ignore[type-arg]
    """Write ``source_code`` to a temp directory matching ``language``.

    The pipeline operates on directory paths (the ingest stage walks a
    repository tree). For in-memory translation we materialize the
    snippet into a single file under a fresh temp directory whose
    extension matches the language. Caller is responsible for calling
    ``.cleanup()`` on the returned ``TemporaryDirectory``.

    Args:
        language: One of ``"python"``, ``"javascript"``, ``"typescript"``.
        source_code: Non-empty source text.

    Returns:
        A ``tempfile.TemporaryDirectory`` containing one source file.

    Raises:
        ValueError: If ``language`` is unsupported or ``source_code`` is empty.
    """
    if not source_code or not source_code.strip():
        raise ValueError("source_code must be a non-empty string")
    ext = _LANGUAGE_EXTENSIONS.get(language)
    if ext is None:
        supported = ", ".join(sorted(_LANGUAGE_EXTENSIONS))
        raise ValueError(f"unsupported language: {language!r} (supported: {supported})")
    tmpdir = tempfile.TemporaryDirectory(prefix="cogant_translate_")
    (Path(tmpdir.name) / f"main.{ext}").write_text(source_code, encoding="utf-8")
    return tmpdir


def _summarize_bundle(bundle: Any, language: str) -> dict[str, Any]:
    """Reduce a :class:`Bundle` to a compact JSON-safe response dict.

    Pulls the validator score, mapping role distribution, GNN markdown
    payload, and stage-completion list off the bundle. Used by both
    :func:`translate_stream` and :func:`translate_batch` to return real
    pipeline output rather than stub strings.
    """
    semantic_mappings = bundle.get_artifact("_semantic_mappings") or {}
    role_counts: dict[str, int] = {}
    for mapping in semantic_mappings.values():
        kind = getattr(getattr(mapping, "kind", None), "value", None) or str(
            getattr(mapping, "kind", "UNKNOWN")
        )
        role_counts[str(kind)] = role_counts.get(str(kind), 0) + 1
    validate_result = bundle.stage_results.get("validate", {})
    score = validate_result.get("score") or validate_result.get("validator_score")
    return {
        "language": language,
        "gnn_bundle": bundle.gnn_markdown(),
        "semantic_mappings_count": len(semantic_mappings),
        "roles": role_counts,
        "validator_score": score,
        "stages_completed": sorted(bundle.stage_results.keys()),
        "errors": list(bundle.errors),
    }


def translate_source(
    language: str,
    source_code: str,
    *,
    stages: list[str] | None = None,
) -> Bundle:
    """Run the COGANT pipeline on an in-memory source string.

    Materializes ``source_code`` to a temp directory and delegates to
    :class:`cogant.api.pipeline.PipelineRunner`. Returns the populated
    :class:`Bundle` so callers can inspect any artifact (program graph,
    semantic mappings, state-space model, GNN markdown, validation
    report). The temp directory is cleaned up before returning.

    Args:
        language: ``"python"``, ``"javascript"``, or ``"typescript"``.
        source_code: Source text to translate.
        stages: Optional explicit pipeline stages. Defaults to the
            hermetic analyse stages (no dynamic, no export, no validate)
            so the function is fast and side-effect free.

    Returns:
        A populated :class:`cogant.api.bundle.Bundle`.

    Raises:
        ValueError: If ``language`` or ``source_code`` is invalid.
    """
    # Lazy import to avoid the orchestration↔pipeline import cycle at module load.
    from cogant.api.pipeline import PipelineConfig, PipelineRunner

    tmpdir = _materialize_source_dir(language, source_code)
    try:
        runner = PipelineRunner()
        config = PipelineConfig(
            stages=list(stages) if stages else list(_DEFAULT_TRANSLATE_STAGES),
            skip_dynamic=True,
        )
        return runner.run(tmpdir.name, config)
    finally:
        tmpdir.cleanup()


async def translate_stream(
    sources: list[tuple[str, str]], options: dict[str, Any] | None = None
) -> AsyncGenerator[dict[str, Any]]:
    """Stream stage-by-stage progress for multiple translation jobs.

    Async generator suitable for WebSocket / Server-Sent-Event endpoints.
    For each ``(language, source_code)`` pair, runs the COGANT pipeline
    in a worker thread (so the event loop stays responsive) and yields:

    * ``translation_start`` — before each job, with overall percent.
    * ``stage_complete`` — once per pipeline stage, with the stage name
      and the new overall percent.
    * ``translation_complete`` — after a successful run, carrying the
      summary dict from :func:`_summarize_bundle`.
    * ``translation_error`` — when a job raises; processing continues
      with the next source.
    * ``progress`` — final overall percent after each job.

    Args:
        sources: List of ``(language, source_code)`` tuples.
        options: Optional knobs. Recognised keys:

            ``stages``
                Override the per-job stage list (default = hermetic
                analyse stages).

    Yields:
        Progress event dicts as described above.
    """
    import asyncio

    options = options or {}
    job_stages: list[str] = list(options.get("stages") or _DEFAULT_TRANSLATE_STAGES)
    total_work = len(sources)
    if total_work == 0:
        yield {"event": "progress", "percent_complete": 100, "processed": 0, "total": 0}
        return

    for idx, (language, source_code) in enumerate(sources):
        start_pct = int(100 * idx / total_work)
        yield {
            "event": "translation_start",
            "index": idx,
            "percent_complete": start_pct,
            "language": language,
        }

        try:
            bundle = await asyncio.to_thread(
                translate_source, language, source_code, stages=job_stages
            )
        except Exception as exc:
            logger.exception("translation failed for source %d", idx)
            yield {
                "event": "translation_error",
                "index": idx,
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
            }
        else:
            for stage_idx, stage in enumerate(job_stages, start=1):
                if stage in bundle.stage_results:
                    sub_pct = start_pct + int((100 / total_work) * (stage_idx / len(job_stages)))
                    yield {
                        "event": "stage_complete",
                        "index": idx,
                        "stage": stage,
                        "percent_complete": min(sub_pct, 100),
                    }
            yield {
                "event": "translation_complete",
                "index": idx,
                "percent_complete": int(100 * (idx + 1) / total_work),
                "status": "success",
                "result": _summarize_bundle(bundle, language),
            }

        yield {
            "event": "progress",
            "percent_complete": int(100 * (idx + 1) / total_work),
            "processed": idx + 1,
            "total": total_work,
        }


def translate_batch(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Execute batch translation over multiple source snippets.

    Each request is run independently through :func:`translate_source`
    and reduced via :func:`_summarize_bundle`. Errors in one request do
    not stop processing of the rest.

    Args:
        requests: List of request dicts, each with keys ``"language"``
            and ``"source_code"``. An optional ``"stages"`` list may
            override the default analyse stages for that request.

    Returns:
        List of response dicts with keys ``"index"``, ``"status"`` (one
        of ``"success"``, ``"error"``), and either ``"result"`` (the
        :func:`_summarize_bundle` dict) or ``"error"`` (string message).
    """
    results: list[dict[str, Any]] = []

    for idx, request in enumerate(requests):
        language = request.get("language")
        source_code = request.get("source_code")
        if not isinstance(language, str) or not isinstance(source_code, str):
            results.append(
                {
                    "index": idx,
                    "status": "error",
                    "error": "missing or non-string language / source_code",
                }
            )
            continue
        try:
            bundle = translate_source(
                language,
                source_code,
                stages=request.get("stages"),
            )
        except Exception as exc:
            logger.exception("batch translation error at index %d", idx)
            results.append(
                {
                    "index": idx,
                    "status": "error",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
        else:
            results.append(
                {
                    "index": idx,
                    "status": "success",
                    "result": _summarize_bundle(bundle, language),
                }
            )

    return results
