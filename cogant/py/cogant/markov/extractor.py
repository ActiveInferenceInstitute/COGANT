"""High-level Markov blanket extractor for COGANT program graphs.

:class:`MarkovBlanketExtractor` is the primary user-facing entry point.
It wraps :func:`cogant.markov.blanket.partition_by_seeds` with a set of
seed-selection *strategies* so that callers can either supply their own
"system of interest" or ask COGANT to discover one automatically.

Supported strategies:

``"explicit"``
    Use an explicit list of node ids provided by the caller.

``"module"``
    Treat a named module (or modules) and everything they transitively
    contain as the system of interest. This is the most common choice
    when analysing a library or package.

``"kind"``
    Treat every node of a given :class:`NodeKind` (e.g. every
    ``CLASS`` node, every ``FUNCTION`` node) as part of the seed set.

``"auto"``
    Pick the module with the highest internal cohesion / external
    coupling ratio, which usually corresponds to the repo's "core"
    package. This is deterministic and depends only on the graph
    structure.

``"mapping_kind"``
    Seed from semantic mappings: every node that participates in a
    mapping whose :class:`~cogant.schemas.semantic.MappingKind` is in
    a user-specified set (default: ``HIDDEN_STATE``) is included.
    This links the Markov blanket back to the Active Inference state
    space produced earlier in the pipeline.

Every strategy returns a fully-populated :class:`MarkovBlanket`, so
callers never need to know which branch was taken to get back a
partition ready for serialization into the GNN bundle.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from typing import Any, Literal

from cogant.markov.blanket import (
    MarkovBlanket,
    _bidirectional_adjacency,
    partition_by_seeds,
)
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph

logger = logging.getLogger(__name__)


SeedStrategy = Literal["explicit", "module", "kind", "auto", "mapping_kind"]


class MarkovBlanketExtractor:
    """Build Markov blankets from program graphs.

    The extractor is stateless beyond a reference to the source graph
    and a handful of default knobs. Invoke :meth:`extract` with the
    desired strategy and parameters and it returns a
    :class:`MarkovBlanket` ready to feed into the GNN bundle.

    Args:
        graph: The program graph to partition.
        prefer_boundary: When set, a node marked as boundary AND
            present in at least ``prefer_boundary`` mapping kinds will
            be recorded in the resulting blanket's ``metadata``.
    """

    def __init__(self, graph: ProgramGraph, *, prefer_boundary: int = 1):
        self.graph = graph
        self.prefer_boundary = prefer_boundary
        self._adjacency = _bidirectional_adjacency(graph)

    def extract(
        self,
        *,
        strategy: SeedStrategy = "auto",
        seeds: Iterable[str] | None = None,
        module_names: Sequence[str] | None = None,
        kinds: Sequence[NodeKind] | None = None,
        mapping_kinds: Sequence[str] | None = None,
        semantic_mappings: dict[str, Any] | None = None,
    ) -> MarkovBlanket:
        """Compute a Markov blanket.

        Args:
            strategy: Seed selection strategy. See module docstring.
            seeds: Explicit node ids (required when ``strategy="explicit"``).
            module_names: Module/package names to anchor on
                (``strategy="module"``).
            kinds: Node kinds to aggregate (``strategy="kind"``).
            mapping_kinds: Mapping-kind strings such as ``"hidden_state"``
                (``strategy="mapping_kind"``).
            semantic_mappings: Optional mapping dict from
                ``orchestration.run_translate`` (required when
                ``strategy="mapping_kind"``).

        Returns:
            A :class:`MarkovBlanket` with metadata recording the
            strategy and inputs that produced it.

        Example:
            >>> from cogant.schemas.graph import ProgramGraph, GraphMetadata
            >>> from cogant.markov.extractor import MarkovBlanketExtractor
            >>> graph = ProgramGraph(metadata=GraphMetadata(repo_uri="demo"))
            >>> extractor = MarkovBlanketExtractor(graph)
            >>> blanket = extractor.extract(strategy="auto")
            >>> blanket.metadata["strategy"]
            'auto'
        """
        if strategy == "explicit":
            if not seeds:
                raise ValueError("strategy='explicit' requires a non-empty seeds list")
            seed_set = set(seeds)

        elif strategy == "module":
            if not module_names:
                raise ValueError("strategy='module' requires module_names")
            seed_set = self._seeds_from_modules(module_names)

        elif strategy == "kind":
            if not kinds:
                raise ValueError("strategy='kind' requires kinds")
            seed_set = self._seeds_from_kinds(kinds)

        elif strategy == "mapping_kind":
            seed_set = self._seeds_from_mapping_kinds(
                semantic_mappings or {}, mapping_kinds or ["hidden_state"]
            )

        elif strategy == "auto":
            seed_set, auto_meta = self._seeds_auto()
        else:
            raise ValueError(f"Unknown strategy: {strategy!r}")

        blanket = partition_by_seeds(
            self.graph, seed_set, adjacency=self._adjacency
        )
        blanket.metadata["strategy"] = strategy
        blanket.metadata["requested_seed_count"] = len(list(seed_set))
        if strategy == "module":
            blanket.metadata["module_names"] = list(module_names or [])
        if strategy == "kind":
            blanket.metadata["kinds"] = [
                k.value if hasattr(k, "value") else str(k) for k in (kinds or [])
            ]
        if strategy == "mapping_kind":
            blanket.metadata["mapping_kinds"] = list(mapping_kinds or [])
        if strategy == "auto":
            blanket.metadata.update(auto_meta)
        return blanket

    # ---------------------- Seed strategy helpers ---------------------- #

    def _seeds_from_modules(self, module_names: Sequence[str]) -> set[str]:
        """Collect module nodes + everything they ``CONTAINS``-reach."""
        targets = {m.lower() for m in module_names}
        seeds: set[str] = set()
        module_nodes = self.graph.get_nodes_by_kind(NodeKind.MODULE)
        for node in module_nodes:
            name_match = (node.name or "").lower()
            qn_match = (node.qualified_name or "").lower()
            if any(t in name_match or t in qn_match for t in targets):
                seeds.add(node.id)
                seeds.update(self._descend_contains(node.id))
        return seeds

    def _descend_contains(self, root_id: str) -> set[str]:
        """Return the transitive CONTAINS-closure of ``root_id``."""
        collected: set[str] = set()
        frontier = [root_id]
        while frontier:
            cur = frontier.pop()
            for edge in self.graph.get_edges_from(cur):
                if edge.kind is EdgeKind.CONTAINS and edge.target_id not in collected:
                    collected.add(edge.target_id)
                    frontier.append(edge.target_id)
        return collected

    def _seeds_from_kinds(self, kinds: Sequence[NodeKind]) -> set[str]:
        seeds: set[str] = set()
        for kind in kinds:
            for node in self.graph.get_nodes_by_kind(kind):
                seeds.add(node.id)
        return seeds

    def _seeds_from_mapping_kinds(
        self,
        semantic_mappings: dict[str, Any],
        mapping_kinds: Sequence[str],
    ) -> set[str]:
        wanted = {mk.lower() for mk in mapping_kinds}
        seeds: set[str] = set()
        for mapping in semantic_mappings.values():
            kind_value = getattr(mapping, "kind", None)
            if kind_value is None:
                continue
            kv = kind_value.value if hasattr(kind_value, "value") else str(kind_value)
            if kv.lower() not in wanted:
                continue
            node_ids = getattr(mapping, "graph_fragment_node_ids", None) or []
            for nid in node_ids:
                if nid in self.graph.nodes:
                    seeds.add(nid)
        return seeds

    def _seeds_auto(self) -> tuple[set[str], dict[str, Any]]:
        """Pick the best cohesion/coupling seed set automatically.

        The heuristic has two tiers:

        1. **Module tier.** For every ``MODULE`` node we compute::

               cohesion  = edges inside the module's contains-closure
               coupling  = edges crossing the closure boundary
               score     = cohesion / (cohesion + coupling + 1)

           and take the argmax. Ties are broken by higher total node
           count so tiny helper modules do not win by accident.

        2. **Class tier fallback.** When there are no modules, or when
           the best module contains the entire graph (making the
           partition degenerate — every node is internal, the blanket
           is empty), we fall back to the largest ``CLASS`` node. Its
           :meth:`~cogant.markov.extractor.MarkovBlanketExtractor._descend_contains`
           closure becomes the seed set. If there are no classes
           either, we fall back to every ``CLASS`` node taken together.

        The returned metadata always records which tier was used, which
        candidate won, and the scoreboard for every module considered,
        so downstream reports can explain *why* this partition was
        selected.
        """
        total_nodes = len(self.graph.nodes)
        modules = self.graph.get_nodes_by_kind(NodeKind.MODULE)

        # Tier 2: no modules at all.
        if not modules:
            return self._auto_class_fallback(reason="no modules present")

        best_score = -1.0
        best_id: str | None = None
        best_size = 0
        scoreboard: list[dict[str, Any]] = []

        for module in modules:
            closure = {module.id} | self._descend_contains(module.id)
            cohesion = 0
            coupling = 0
            for nid in closure:
                for edge in self.graph.get_edges_from(nid):
                    if edge.target_id in closure:
                        cohesion += 1
                    else:
                        coupling += 1
                for edge in self.graph.get_edges_to(nid):
                    if edge.source_id not in closure:
                        coupling += 1
            score = cohesion / (cohesion + coupling + 1)
            scoreboard.append(
                {
                    "module_id": module.id,
                    "module_name": module.name or module.qualified_name,
                    "closure_size": len(closure),
                    "cohesion": cohesion,
                    "coupling": coupling,
                    "score": round(score, 4),
                }
            )
            if score > best_score or (score == best_score and len(closure) > best_size):
                best_score = score
                best_id = module.id
                best_size = len(closure)

        if best_id is None:
            return set(), {"auto_reason": "no candidate modules scored above 0"}

        # Tier 2: best module swallows the whole graph → degenerate
        # partition with no boundary. Fall back to a class-level seed.
        if best_size >= total_nodes:
            fallback = self._auto_class_fallback(
                reason="only module spans whole graph; fell back to class tier"
            )
            fallback_seeds, fallback_meta = fallback
            fallback_meta["module_scoreboard"] = scoreboard
            fallback_meta["fallback_from_module_id"] = best_id
            return fallback_seeds, fallback_meta

        seeds = {best_id} | self._descend_contains(best_id)
        meta = {
            "auto_reason": "argmax of cohesion/(cohesion+coupling+1) over modules",
            "auto_tier": "module",
            "chosen_module_id": best_id,
            "chosen_score": best_score,
            "chosen_closure_size": best_size,
            "candidate_modules": len(modules),
            "scoreboard": scoreboard,
        }
        logger.info(
            "Markov blanket auto-seed chose module %s (score=%.3f, nodes=%d)",
            best_id, best_score, best_size,
        )
        return seeds, meta

    def _auto_class_fallback(self, *, reason: str) -> tuple[set[str], dict[str, Any]]:
        """Pick the largest ``CLASS`` closure as the auto seed set.

        Chooses the class whose ``CONTAINS``-closure size is largest
        (ties broken by node id for determinism). If there are no
        classes, returns every class node — which, when the graph has
        none, yields an empty seed set and a degenerate (all-external)
        blanket; this is the correct honest answer for such a graph.
        """
        classes = self.graph.get_nodes_by_kind(NodeKind.CLASS)
        if not classes:
            return set(), {
                "auto_reason": f"{reason}; no classes to fall back to",
                "auto_tier": "empty",
                "candidate_classes": 0,
            }

        best_cls_id: str | None = None
        best_closure: set[str] = set()
        for cls in sorted(classes, key=lambda c: c.id):
            closure = {cls.id} | self._descend_contains(cls.id)
            if len(closure) > len(best_closure):
                best_cls_id = cls.id
                best_closure = closure

        if best_cls_id is None or len(best_closure) <= 1:
            # Classes exist but none have methods/members → aggregate all classes.
            seeds = {c.id for c in classes}
            return seeds, {
                "auto_reason": f"{reason}; no class has non-trivial closure, used all CLASS nodes",
                "auto_tier": "class_aggregate",
                "candidate_classes": len(classes),
            }

        return best_closure, {
            "auto_reason": reason,
            "auto_tier": "class",
            "chosen_class_id": best_cls_id,
            "chosen_closure_size": len(best_closure),
            "candidate_classes": len(classes),
        }
