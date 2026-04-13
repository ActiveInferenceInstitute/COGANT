#!/usr/bin/env python3
"""Thin example: Complete custom TranslationRule subclass.

Demonstrates writing a production-quality custom rule end-to-end:

1. Subclass ``TranslationRule`` and implement all three contract methods:
   ``matches()``, ``apply()``, and ``explain()``.
2. Register the rule with ``TranslationEngine``.
3. Run the fixpoint engine on a real fixture.
4. Inspect the mappings produced by the custom rule.

The custom rule, ``FactoryMethodRule``, detects static/class methods whose
names start with ``create_``, ``from_``, or ``build_`` — a common factory
pattern — and emits an ACTION mapping with a meaningful label.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/27_custom_translation_rule.py \\
        --target examples/control_positive/calculator \\
        --output-dir output/thin/custom_rule
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, configure_logging, parse_args  # noqa: E402

from cogant.schemas.core import NodeKind  # noqa: E402
from cogant.schemas.semantic_mapping import MappingKind, SemanticMapping  # noqa: E402
from cogant.translate.engine import TranslationEngine, TranslationRule  # noqa: E402
from cogant.translate.rules import (  # noqa: E402
    ActionRule,
    MutatingSubsystemRule,
    ObservationRule,
    ReadOnlyInputRule,
)


# ---------------------------------------------------------------------------
# Custom rule implementation
# ---------------------------------------------------------------------------

FACTORY_PREFIXES = ("create_", "from_", "build_", "make_", "new_", "of_")


class FactoryMethodRule(TranslationRule):
    """Detects factory methods and emits ACTION mappings.

    A factory method is a ``staticmethod`` or ``classmethod`` whose name
    begins with one of the canonical factory prefixes (``create_``, ``from_``,
    ``build_``, ``make_``, ``new_``, ``of_``).

    Factory methods are semantic *actions*: they actively construct state
    rather than merely reading it, making them natural candidates for the
    ACTION mapping kind in the Active Inference state space.
    """

    #: Human-readable name used in log output and rule-filter lists.
    name: str = "FactoryMethodRule"

    #: Priority for conflict resolution — slightly above the base ActionRule
    #: (which has priority 10) so factory methods win when both rules fire.
    priority: int = 15

    #: Confidence score assigned to mappings emitted by this rule.
    confidence_score: float = 0.82

    def matches(self, graph: Any, query: Any) -> list[Any]:
        """Return graph node IDs that look like factory methods.

        Args:
            graph: ``ProgramGraph`` instance.
            query: ``GraphQuery`` helper (ignored — we scan directly).

        Returns:
            List of node IDs for FUNCTION/METHOD nodes whose names start with
            a factory prefix and are decorated as ``staticmethod`` or
            ``classmethod``.
        """
        hits: list[Any] = []
        for node_id, node in graph.nodes.items():
            if node.kind not in (NodeKind.FUNCTION, NodeKind.METHOD):
                continue
            name: str = (node.name or "").lower()
            if not any(name.startswith(p) for p in FACTORY_PREFIXES):
                continue
            # Accept static / class methods *and* plain functions at module
            # scope (module-level factories are common in builder modules).
            is_static_or_class = (
                "staticmethod" in (node.metadata or {}).get("decorators", [])
                or "classmethod" in (node.metadata or {}).get("decorators", [])
                or node.kind == NodeKind.FUNCTION  # module-scope factory
            )
            if is_static_or_class:
                hits.append(node_id)
        return hits

    def apply(self, graph: Any, match: Any) -> SemanticMapping | None:
        """Produce an ACTION SemanticMapping for a matched factory node.

        Args:
            graph: ``ProgramGraph`` instance.
            match: A node ID returned by :meth:`matches`.

        Returns:
            A ``SemanticMapping`` with kind ACTION, or ``None`` if the node
            has been removed from the graph since the match was collected.
        """
        node = graph.nodes.get(match)
        if node is None:
            return None

        label = f"factory:{node.name}"
        # Stable ID: rule name + node id, hashed to 8 hex chars.
        uid = hashlib.sha1(f"factory:{match}".encode()).hexdigest()[:8]
        mapping_id = f"fact_{uid}"

        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.ACTION,
            graph_fragment_node_ids=[match],
            semantic_label=label,
            confidence_score=self.confidence_score,
            provenance=[],
            evidence_count=1,
            evidence_diversity=0.5,
            parser_certainty=0.9,
            status="auto_proposed",
            source_rule=self.name,
        )

    def explain(self, graph: Any, match: Any) -> str:
        """Return a human-readable explanation of why this node was matched.

        Args:
            graph: ``ProgramGraph`` instance.
            match: A node ID returned by :meth:`matches`.

        Returns:
            A one-paragraph explanation string.
        """
        node = graph.nodes.get(match)
        if node is None:
            return f"Node {match!r} no longer in graph."
        name = node.name or "<unknown>"
        prefix = next((p for p in FACTORY_PREFIXES if name.lower().startswith(p)), "")
        return (
            f"Node '{name}' (id={match}) was matched by FactoryMethodRule because its "
            f"name begins with the factory prefix '{prefix}'. Factory methods actively "
            f"construct and return new objects, making them semantic *actions* in the "
            f"Active Inference sense — they change the world state by instantiating new "
            f"entities. Confidence: {self.confidence_score:.2f}."
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:  # noqa: C901
    args = parse_args(description="27 — custom TranslationRule (FactoryMethodRule)")
    configure_logging(args.verbose)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    banner("Custom TranslationRule — FactoryMethodRule")

    # ---- 1. Build program graph from target fixture ----------------------
    from cogant.pipeline.runner import PipelineRunner  # noqa: E402
    from cogant.config.pipeline import PipelineConfig  # noqa: E402

    config = PipelineConfig(target=Path(args.target), output_dir=output_dir)
    runner = PipelineRunner(config)
    result = runner.run(stages=["ingest", "static", "graph"])

    program_graph = result.program_graph
    if program_graph is None:
        print("ERROR: could not build program graph from target.")
        sys.exit(1)

    total_nodes = len(program_graph.nodes)
    total_edges = len(program_graph.edges)
    print(f"\n  Graph: {total_nodes} nodes, {total_edges} edges")

    # ---- 2. Build engine with standard rules + custom rule --------------
    engine = TranslationEngine(max_iterations=10)

    standard_rules = [
        ReadOnlyInputRule(),
        MutatingSubsystemRule(),
        ObservationRule(),
        ActionRule(),
    ]
    custom_rule = FactoryMethodRule()

    for rule in standard_rules:
        engine.register_rule(rule)
    engine.register_rule(custom_rule)

    print(f"\n  Rules registered: {len(standard_rules)} standard + 1 custom")

    # ---- 3. Run fixpoint translation ------------------------------------
    mappings = engine.translate(program_graph)

    standard_mappings = [m for m in mappings if m.source_rule != "FactoryMethodRule"]
    custom_mappings = [m for m in mappings if m.source_rule == "FactoryMethodRule"]

    banner(f"Results: {len(mappings)} total mappings")
    print(f"  Standard rules:  {len(standard_mappings)} mappings")
    print(f"  FactoryMethodRule: {len(custom_mappings)} mappings")

    # ---- 4. Show custom mappings ----------------------------------------
    if custom_mappings:
        print("\n  Factory method mappings:")
        for m in custom_mappings:
            node_id = m.graph_fragment_node_ids[0] if m.graph_fragment_node_ids else "?"
            explanation = custom_rule.explain(program_graph, node_id)
            print(f"\n    [{m.id}] {m.semantic_label}")
            print(f"    kind={m.kind.value}  confidence={m.confidence_score:.2f}")
            print(f"    Explanation: {explanation[:120]}...")
    else:
        print(
            "\n  No factory methods found in this fixture. Try a fixture with "
            "create_*/from_*/build_* patterns (e.g. examples/event_pipeline)."
        )

    # ---- 5. Persist results ---------------------------------------------
    import json

    out = {
        "target": str(args.target),
        "total_mappings": len(mappings),
        "custom_rule_mappings": [
            {
                "id": m.id,
                "label": m.semantic_label,
                "kind": m.kind.value,
                "confidence": m.confidence_score,
                "nodes": m.graph_fragment_node_ids,
            }
            for m in custom_mappings
        ],
    }
    out_path = output_dir / "custom_rule_results.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n  Results → {out_path}")
    banner("Done")


if __name__ == "__main__":
    main()
