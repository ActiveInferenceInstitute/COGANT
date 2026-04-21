#!/usr/bin/env python3
"""Thin example: Wave-21 translation rules (ParameterRule, StateMachineRule, RateLimiterRule).

This script builds a synthetic ProgramGraph with patterns that specifically
trigger the three "wave-21" rules from the resilience family:

  1. **ParameterRule** — detects functions with default arguments or
     parameter objects, emits PARAMETER mappings.
  2. **StateMachineRule** — detects class hierarchies or enum-like patterns,
     emits HIDDEN_STATE mappings.
  3. **RateLimiterRule** — detects decorator patterns or timing-guard clauses,
     emits ACTION mappings for rate-limiting logic.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/23_wave21_rules.py \\
        --output-dir output/thin/wave21_rules
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, configure_logging, parse_args  # noqa: E402

from cogant.graph.builder import ProgramGraphBuilder  # noqa: E402
from cogant.schemas.core import EdgeKind, NodeKind  # noqa: E402
from cogant.translate.confidence import ConfidenceModel  # noqa: E402
from cogant.translate.engine import TranslationEngine  # noqa: E402
from cogant.translate.rules import (  # noqa: E402
    ParameterRule,
    RateLimiterRule,
    StateMachineRule,
)


def _build_synthetic_graph():
    """Build a synthetic ProgramGraph with patterns for the three wave-21 rules."""
    builder = ProgramGraphBuilder(repo_uri="synthetic://wave21_demo")

    # Module node
    module_node = builder.add_node(
        kind=NodeKind.MODULE,
        name="demo_module",
        qualified_name="demo_module",
        path="demo.py",
        language="python",
    )

    # ParameterRule trigger: class with __init__ that has default arguments
    param_class = builder.add_node(
        kind=NodeKind.CLASS,
        name="ConfigManager",
        qualified_name="demo_module.ConfigManager",
        path="demo.py",
        language="python",
        metadata={"has_default_args": True, "param_count": 3},
    )
    builder.add_edge(module_node.id, param_class.id, EdgeKind.CONTAINS)

    init_method = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="__init__",
        qualified_name="demo_module.ConfigManager.__init__",
        path="demo.py",
        language="python",
        metadata={"is_method": True, "param_names": ["timeout", "retries", "backoff"]},
    )
    builder.add_edge(param_class.id, init_method.id, EdgeKind.CONTAINS)

    # StateMachineRule trigger: state enum-like class with multiple constants
    state_class = builder.add_node(
        kind=NodeKind.CLASS,
        name="ConnectionState",
        qualified_name="demo_module.ConnectionState",
        path="demo.py",
        language="python",
        metadata={"is_enum": True, "constants": ["IDLE", "CONNECTING", "CONNECTED", "ERROR"]},
    )
    builder.add_edge(module_node.id, state_class.id, EdgeKind.CONTAINS)

    # StateMachineRule trigger: class with state-transition methods
    fsm_class = builder.add_node(
        kind=NodeKind.CLASS,
        name="ConnectionFSM",
        qualified_name="demo_module.ConnectionFSM",
        path="demo.py",
        language="python",
        metadata={"is_state_machine": True},
    )
    builder.add_edge(module_node.id, fsm_class.id, EdgeKind.CONTAINS)

    transition_method = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="transition",
        qualified_name="demo_module.ConnectionFSM.transition",
        path="demo.py",
        language="python",
        metadata={"is_method": True, "references_state": True},
    )
    builder.add_edge(fsm_class.id, transition_method.id, EdgeKind.CONTAINS)
    builder.add_edge(transition_method.id, state_class.id, EdgeKind.READS)

    # RateLimiterRule trigger: function with timing decorator or rate-limit check
    rate_limited_func = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="handle_request",
        qualified_name="demo_module.handle_request",
        path="demo.py",
        language="python",
        metadata={"has_rate_limit_decorator": True, "time_check_pattern": True},
    )
    builder.add_edge(module_node.id, rate_limited_func.id, EdgeKind.CONTAINS)

    # Another rate-limiter pattern: method that checks time.time()
    throttled_method = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="send_data",
        qualified_name="demo_module.ConnectionFSM.send_data",
        path="demo.py",
        language="python",
        metadata={"is_method": True, "has_time_guard": True},
    )
    builder.add_edge(fsm_class.id, throttled_method.id, EdgeKind.CONTAINS)

    return builder.finalize()


def main() -> int:
    """Entry point for the wave-21 rules demo."""
    args = parse_args("wave21_rules")
    configure_logging()
    banner("Stage 23: Wave-21 translation rules")

    # Build synthetic graph
    pg = _build_synthetic_graph()
    print("  synthetic graph:")
    print(f"    nodes={pg.node_count()}  edges={pg.edge_count()}")

    # Register only the three wave-21 rules
    engine = TranslationEngine()
    rules_to_test = [
        ParameterRule(),
        StateMachineRule(),
        RateLimiterRule(),
    ]
    for rule in rules_to_test:
        engine.register_rule(rule)

    print(f"\n  rules registered: {len(rules_to_test)}")
    for rule in rules_to_test:
        print(f"    - {rule.__class__.__name__}")

    # Translate
    mappings_list = engine.translate(pg)
    print(f"\n  mappings produced: {len(mappings_list)}")

    # Score with confidence model
    ConfidenceModel().score_batch(mappings_list)

    # Organize mappings by rule and node
    rule_to_mappings: dict[str, list] = {}
    for m in mappings_list:
        rule_name = m.provenance.rule_name if hasattr(m.provenance, "rule_name") else "unknown"
        if rule_name not in rule_to_mappings:
            rule_to_mappings[rule_name] = []
        rule_to_mappings[rule_name].append(m)

    # Print results table: rule → mapping_kind → count → avg_confidence
    print("\n  results table:")
    print(f"  {'Rule':<25} {'Mapping Kind':<20} {'Count':<6} {'Avg Confidence':<15}")
    print(f"  {'-' * 25} {'-' * 20} {'-' * 6} {'-' * 15}")

    for rule_name in sorted(rule_to_mappings.keys()):
        mappings = rule_to_mappings[rule_name]
        kind_groups: dict[str, list] = {}
        for m in mappings:
            kind = m.mapping_kind if hasattr(m, "mapping_kind") else "UNKNOWN"
            if kind not in kind_groups:
                kind_groups[kind] = []
            kind_groups[kind].append(m)

        for kind in sorted(kind_groups.keys()):
            group = kind_groups[kind]
            count = len(group)
            # Extract confidence; use getattr with default
            confidences = [getattr(m, "confidence", 0.5) for m in group]
            avg_conf = sum(confidences) / count if confidences else 0.0
            print(f"  {rule_name:<25} {kind:<20} {count:<6} {avg_conf:.3f}")

    # Print per-node summary
    print("\n  per-node mapping summary:")
    node_to_mappings: dict[str, list] = {}
    for m in mappings_list:
        node_id = m.node_id if hasattr(m, "node_id") else "unknown"
        if node_id not in node_to_mappings:
            node_to_mappings[node_id] = []
        node_to_mappings[node_id].append(m)

    for node_id in sorted(node_to_mappings.keys())[:10]:  # Show first 10 nodes
        node = pg.get_node(node_id)
        mappings = node_to_mappings[node_id]
        node_name = node.name if node else "?"
        mapping_kinds = [m.mapping_kind if hasattr(m, "mapping_kind") else "?" for m in mappings]
        print(f"    {node_name:<25} → {', '.join(mapping_kinds)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n  output dir: {args.output_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
