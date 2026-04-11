"""Unit tests for the ``cogant explain`` CLI subcommand.

These tests exercise :mod:`cogant.cli.explain` end-to-end against a
small, hand-rolled Python repository written into a ``tmp_path``
directory. No mocks are used: the pipeline runs for real (ingest,
static, normalize, graph, translate), and the assertions inspect the
same ``ExplainResult`` object that the CLI formatter consumes.

The repository written by :func:`_write_calculator_repo` is a trimmed
version of ``examples/control_positive/calculator/calculator.py``. It
is small enough to translate in well under a second, which keeps this
test file cheap to run as part of the unit suite.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cogant.cli.explain import (
    ExplainResult,
    NodeNotFoundError,
    explain_node,
    format_json,
    format_text,
)

CALCULATOR_SOURCE = '''
"""Minimal stateful calculator used by test_explain.py."""

from typing import List, Optional


class Calculator:
    """A calculator that holds mutable state and exposes actions."""

    def __init__(self) -> None:
        self.display = "0"
        self.operand = 0
        self.operator: Optional[str] = None
        self.history: List[str] = []

    def set_operand(self, value: int) -> None:
        """Action: update the current operand."""
        self.operand = value
        self.history.append(f"set_operand({value})")

    def set_operator(self, op: str) -> None:
        """Action: update the current operator."""
        self.operator = op
        self.history.append(f"set_operator({op})")

    def clear(self) -> None:
        """Action: reset the calculator to its initial state."""
        self.display = "0"
        self.operand = 0
        self.operator = None
        self.history.append("clear()")

    def calculate_result(self) -> int:
        """Action: fold operand + operator into the display."""
        result = self.operand
        self.display = str(result)
        self.history.append("calculate_result()")
        return result

    def get_display(self) -> str:
        """Observation: current display string."""
        return self.display

    def get_history(self) -> List[str]:
        """Observation: operation history."""
        return list(self.history)
'''


def _write_calculator_repo(tmp_path: Path) -> Path:
    """Write a minimal stateful-calculator repo to ``tmp_path``.

    Returns:
        Absolute path to the repo root (which is just ``tmp_path``).
    """
    (tmp_path / "calculator.py").write_text(CALCULATOR_SOURCE, encoding="utf-8")
    return tmp_path


def test_explain_returns_explanation_for_known_node(tmp_path: Path) -> None:
    """A known calculator action should be explained with WRITES evidence."""
    repo = _write_calculator_repo(tmp_path)

    result = explain_node(str(repo), "calculate_result")

    assert isinstance(result, ExplainResult)
    assert result.node_name == "calculate_result"
    # At least one rule must have fired.
    assert result.rules_fired, "expected at least one rule to fire"
    fired_names = {rx.rule_name for rx in result.rules_fired}
    # The action rule should fire because 'calculate' isn't in the action
    # keyword list, but the method writes self.display, self.history; and
    # the observation rule should NOT fire for this mutator. We assert
    # that either the action or mutating_subsystem pathway fires, and
    # that the reason mentions WRITES.
    assert ("action" in fired_names) or ("mutating_subsystem" in fired_names) or (
        "data_pipeline" in fired_names
    )
    joined_reasons = " | ".join(rx.reason for rx in result.rules_fired)
    joined_evidence = " | ".join(
        ev for rx in result.rules_fired for ev in rx.evidence
    )
    assert ("WRITES" in joined_reasons) or ("WRITES" in joined_evidence), (
        f"expected WRITES evidence in fired rules, got reasons={joined_reasons!r} "
        f"evidence={joined_evidence!r}"
    )

    # Some rules must have been considered-but-not-fired too; the engine
    # ships ~19 rules and only a couple can fire on a single node.
    assert len(result.rules_considered) >= 5


def test_explain_json_output_has_required_keys(tmp_path: Path) -> None:
    """The JSON output must expose the contract keys used by the CLI."""
    repo = _write_calculator_repo(tmp_path)

    result = explain_node(str(repo), "calculate_result")
    blob = json.loads(format_json(result))

    # These keys form the public contract of the explain subcommand.
    required_keys = {
        "node_name",
        "assigned_role",
        "rules_fired",
        "rules_considered",
        "blanket_role",
    }
    assert required_keys.issubset(blob.keys()), (
        f"missing keys: {required_keys - set(blob.keys())}"
    )

    # rules_fired must be a list of dicts with the RuleExplanation schema.
    assert isinstance(blob["rules_fired"], list)
    if blob["rules_fired"]:
        first = blob["rules_fired"][0]
        assert "rule_name" in first
        assert "priority" in first
        assert "fired" in first
        assert "reason" in first
        assert "evidence" in first

    # Considered rules follow the same schema.
    assert isinstance(blob["rules_considered"], list)
    for rx in blob["rules_considered"]:
        assert rx["fired"] is False


def test_explain_fuzzy_match(tmp_path: Path) -> None:
    """A substring query should resolve to the best-matching node."""
    repo = _write_calculator_repo(tmp_path)

    # "calc" is a prefix of 'calculate_result' but also of the file stem
    # 'calculator' and the class name 'Calculator'. The substring
    # resolver prefers the shortest node name, so the deterministic
    # winner is whichever short name contains 'calc'. We assert the
    # returned node name contains the query as a case-insensitive
    # substring and that the explain runs to completion.
    result = explain_node(str(repo), "calc")

    assert isinstance(result, ExplainResult)
    assert "calc" in result.node_name.lower()
    # Regardless of which exact node was chosen, both fired and
    # considered lists must be populated lists (never None).
    assert isinstance(result.rules_fired, list)
    assert isinstance(result.rules_considered, list)


def test_explain_unknown_node_raises_friendly_error(tmp_path: Path) -> None:
    """An unresolvable node name raises :class:`NodeNotFoundError`."""
    repo = _write_calculator_repo(tmp_path)

    with pytest.raises(NodeNotFoundError) as excinfo:
        explain_node(str(repo), "nonexistent_node_xyz_12345")

    msg = str(excinfo.value)
    # The error must be actionable: it should mention the query and
    # list a sample of candidate names so the caller can retry.
    assert "nonexistent_node_xyz_12345" in msg
    assert "candidates" in msg.lower() or "sample" in msg.lower()


def test_explain_text_format_runs_without_error(tmp_path: Path, capsys) -> None:
    """``format_text`` should render an ``ExplainResult`` with no exceptions."""
    repo = _write_calculator_repo(tmp_path)

    result = explain_node(str(repo), "get_display")
    format_text(result)

    captured = capsys.readouterr()
    # The report must include the node name and at least a rules-fired
    # header (even when no rules fired, a status line is printed).
    assert "get_display" in captured.out


def test_resolve_node_prefers_exact_match(tmp_path: Path) -> None:
    """``resolve_node`` must prefer exact matches over substring hits."""
    repo = _write_calculator_repo(tmp_path)

    # Run the pipeline once so we can reuse the graph for a pure
    # resolver test without re-running the full pipeline.
    result = explain_node(str(repo), "clear")
    assert result.node_name == "clear", (
        f"expected exact match on 'clear', got {result.node_name!r}"
    )
