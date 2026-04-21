"""Unit tests for DAG-based pipeline execution engine.

Tests cover topological sort (Kahn's algorithm), cycle detection,
dependency propagation, failure cascading, and result completeness.
All tests use real data and computation -- no mocks.
"""

from __future__ import annotations

import pytest

from cogant.pipeline.dag import DAGResult, PipelineDAG, Stage, StageStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _identity_stage(name: str, deps: list[str] | None = None) -> Stage:
    """Stage that does nothing and returns an empty dict."""
    return Stage(name=name, fn=lambda ctx: {}, deps=deps or [])


def _stage_that_sets(name: str, key: str, value: object, deps: list[str] | None = None) -> Stage:
    """Stage that writes *key*=*value* into the context."""
    return Stage(name=name, fn=lambda ctx: {key: value}, deps=deps or [])


def _failing_stage(name: str, deps: list[str] | None = None) -> Stage:
    """Stage that always raises RuntimeError."""

    def _boom(ctx: dict) -> dict:
        raise RuntimeError("stage exploded")

    return Stage(name=name, fn=_boom, deps=deps or [])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPipelineDAG:
    """Test suite for PipelineDAG."""

    def test_dag_empty_run(self) -> None:
        """Empty DAG runs without error and returns zero-stage result."""
        dag = PipelineDAG()
        result = dag.run({})

        assert isinstance(result, DAGResult)
        assert result.stage_results == {}
        assert result.errors == []
        assert result.elapsed >= 0.0

    def test_dag_linear_chain(self) -> None:
        """A -> B -> C executes in strict order."""
        execution_order: list[str] = []

        def _recorder(name: str):
            def _fn(ctx: dict) -> dict:
                execution_order.append(name)
                return {}

            return _fn

        dag = PipelineDAG()
        dag.add_stage(Stage(name="A", fn=_recorder("A")))
        dag.add_stage(Stage(name="B", fn=_recorder("B"), deps=["A"]))
        dag.add_stage(Stage(name="C", fn=_recorder("C"), deps=["B"]))

        result = dag.run({})

        assert execution_order == ["A", "B", "C"]
        assert all(result.stage_results[s].status == StageStatus.SUCCESS for s in ("A", "B", "C"))

    def test_dag_parallel_stages(self) -> None:
        """A and B with no deps both run (order is deterministic via sort)."""
        dag = PipelineDAG()
        dag.add_stage(_identity_stage("B"))
        dag.add_stage(_identity_stage("A"))

        result = dag.run({})

        assert set(result.stage_results.keys()) == {"A", "B"}
        assert all(sr.status == StageStatus.SUCCESS for sr in result.stage_results.values())

    def test_dag_dependency_propagation(self) -> None:
        """Context produced by A is visible to B."""
        dag = PipelineDAG()
        dag.add_stage(_stage_that_sets("A", "x", 42))
        dag.add_stage(
            Stage(
                name="B",
                fn=lambda ctx: {"y": ctx["x"] + 1},
                deps=["A"],
            )
        )

        result = dag.run({})

        assert result.stage_results["B"].status == StageStatus.SUCCESS
        assert result.stage_results["B"].output == {"y": 43}

    def test_dag_cycle_detection(self) -> None:
        """A -> B -> A raises ValueError mentioning cycle."""
        dag = PipelineDAG()
        dag.add_stage(Stage(name="A", fn=lambda ctx: {}, deps=["B"]))
        dag.add_stage(Stage(name="B", fn=lambda ctx: {}, deps=["A"]))

        with pytest.raises(ValueError, match="[Cc]ycle"):
            dag.run({})

    def test_dag_stage_failure_skips_dependents(self) -> None:
        """If A fails, B (dep=A) is SKIPPED, not FAILED."""
        dag = PipelineDAG()
        dag.add_stage(_failing_stage("A"))
        dag.add_stage(_identity_stage("B", deps=["A"]))

        result = dag.run({})

        assert result.stage_results["A"].status == StageStatus.FAILED
        assert result.stage_results["A"].error is not None
        assert result.stage_results["B"].status == StageStatus.SKIPPED
        assert len(result.errors) >= 1

    def test_dag_topological_sort_deterministic(self) -> None:
        """Same graph gives same topological order on repeated calls."""
        dag = PipelineDAG()
        dag.add_stage(_identity_stage("C"))
        dag.add_stage(_identity_stage("A"))
        dag.add_stage(_identity_stage("B"))

        order1 = dag._topological_sort()
        order2 = dag._topological_sort()

        assert order1 == order2

    def test_dag_result_has_all_stages(self) -> None:
        """DAGResult.stage_results has an entry for every registered stage."""
        dag = PipelineDAG()
        names = ["alpha", "beta", "gamma", "delta"]
        for n in names:
            dag.add_stage(_identity_stage(n))

        result = dag.run({})

        assert set(result.stage_results.keys()) == set(names)

    def test_dag_unknown_dependency_raises(self) -> None:
        """A stage referencing a non-existent dependency raises ValueError."""
        dag = PipelineDAG()
        dag.add_stage(Stage(name="A", fn=lambda ctx: {}, deps=["ghost"]))

        with pytest.raises(ValueError, match="ghost"):
            dag.run({})

    def test_dag_duplicate_stage_raises(self) -> None:
        """Adding two stages with the same name raises ValueError."""
        dag = PipelineDAG()
        dag.add_stage(_identity_stage("A"))
        with pytest.raises(ValueError, match="A"):
            dag.add_stage(_identity_stage("A"))

    def test_dag_diamond_dependency(self) -> None:
        """Diamond: A -> B, A -> C, B -> D, C -> D all succeed."""
        dag = PipelineDAG()
        dag.add_stage(_stage_that_sets("A", "a", 1))
        dag.add_stage(_stage_that_sets("B", "b", 2, deps=["A"]))
        dag.add_stage(_stage_that_sets("C", "c", 3, deps=["A"]))
        dag.add_stage(
            Stage(
                name="D",
                fn=lambda ctx: {"d": ctx["a"] + ctx["b"] + ctx["c"]},
                deps=["B", "C"],
            )
        )

        result = dag.run({})

        assert result.stage_results["D"].status == StageStatus.SUCCESS
        assert result.stage_results["D"].output == {"d": 6}
