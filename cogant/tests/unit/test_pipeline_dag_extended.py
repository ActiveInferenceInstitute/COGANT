"""Extended behavioral tests for cogant.pipeline.dag — edge cases and deep chains.

Covers: deep dependency chains, fan-out/fan-in, multi-failure cascading,
stage timing, non-dict return values, context isolation, wide DAGs,
three-node cycle detection message, and stages with no deps at end.
"""

from __future__ import annotations

import time

import pytest

from cogant.pipeline.dag import PipelineDAG, Stage, StageStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _counter_stage(name: str, execution_log: list[str], deps: list[str] | None = None) -> Stage:
    """Stage that appends its name to execution_log."""

    def _fn(ctx: dict) -> dict:
        execution_log.append(name)
        return {}

    return Stage(name=name, fn=_fn, deps=deps or [])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPipelineDAGExtended:
    """Extended edge-case tests for PipelineDAG."""

    def test_deep_chain_10_stages(self) -> None:
        """A linear chain of 10 stages executes in strict order."""
        log: list[str] = []
        dag = PipelineDAG()
        names = [f"s{i}" for i in range(10)]
        for i, name in enumerate(names):
            deps = [names[i - 1]] if i > 0 else []
            dag.add_stage(_counter_stage(name, log, deps))

        result = dag.run({})
        assert log == names
        assert all(result.stage_results[n].status == StageStatus.SUCCESS for n in names)

    def test_fan_out_fan_in(self) -> None:
        """Root -> 5 parallel -> sink. All succeed."""
        dag = PipelineDAG()
        dag.add_stage(Stage(name="root", fn=lambda ctx: {"root": True}))
        fan_names = [f"fan_{i}" for i in range(5)]
        for fn_name in fan_names:
            dag.add_stage(Stage(name=fn_name, fn=lambda ctx: {}, deps=["root"]))
        dag.add_stage(Stage(name="sink", fn=lambda ctx: {}, deps=fan_names))

        result = dag.run({})
        assert result.stage_results["sink"].status == StageStatus.SUCCESS
        assert all(result.stage_results[n].status == StageStatus.SUCCESS for n in fan_names)

    def test_multi_failure_cascading(self) -> None:
        """Multiple independent failures each skip their dependents."""
        dag = PipelineDAG()
        dag.add_stage(
            Stage(name="a", fn=lambda ctx: (_ for _ in ()).throw(RuntimeError("a fails")), deps=[])
        )
        dag.add_stage(
            Stage(name="b", fn=lambda ctx: (_ for _ in ()).throw(RuntimeError("b fails")), deps=[])
        )
        dag.add_stage(Stage(name="c", fn=lambda ctx: {}, deps=["a"]))
        dag.add_stage(Stage(name="d", fn=lambda ctx: {}, deps=["b"]))

        # Need to fix: lambda with generator throw doesn't work. Use proper failing fns.
        dag2 = PipelineDAG()

        def _fail_a(ctx: dict) -> dict:
            raise RuntimeError("a fails")

        def _fail_b(ctx: dict) -> dict:
            raise RuntimeError("b fails")

        dag2.add_stage(Stage(name="a", fn=_fail_a))
        dag2.add_stage(Stage(name="b", fn=_fail_b))
        dag2.add_stage(Stage(name="c", fn=lambda ctx: {}, deps=["a"]))
        dag2.add_stage(Stage(name="d", fn=lambda ctx: {}, deps=["b"]))

        result = dag2.run({})
        assert result.stage_results["a"].status == StageStatus.FAILED
        assert result.stage_results["b"].status == StageStatus.FAILED
        assert result.stage_results["c"].status == StageStatus.SKIPPED
        assert result.stage_results["d"].status == StageStatus.SKIPPED
        assert len(result.errors) == 2

    def test_stage_elapsed_time_recorded(self) -> None:
        """Each stage result records non-negative elapsed time."""
        dag = PipelineDAG()
        dag.add_stage(Stage(name="slow", fn=lambda ctx: time.sleep(0.01) or {}))

        result = dag.run({})
        assert result.stage_results["slow"].elapsed >= 0.01
        assert result.elapsed >= 0.01

    def test_non_dict_return_treated_as_empty(self) -> None:
        """A stage that returns None (not a dict) doesn't crash the pipeline."""
        dag = PipelineDAG()
        dag.add_stage(Stage(name="returns_none", fn=lambda ctx: None))
        dag.add_stage(Stage(name="after", fn=lambda ctx: {}, deps=["returns_none"]))

        result = dag.run({})
        assert result.stage_results["returns_none"].status == StageStatus.SUCCESS
        assert result.stage_results["after"].status == StageStatus.SUCCESS

    def test_context_accumulates_across_stages(self) -> None:
        """Context from multiple independent stages merges for a shared dependent."""
        dag = PipelineDAG()
        dag.add_stage(Stage(name="a", fn=lambda ctx: {"x": 10}))
        dag.add_stage(Stage(name="b", fn=lambda ctx: {"y": 20}))
        dag.add_stage(
            Stage(
                name="c",
                fn=lambda ctx: {"sum": ctx.get("x", 0) + ctx.get("y", 0)},
                deps=["a", "b"],
            )
        )

        result = dag.run({})
        assert result.stage_results["c"].output["sum"] == 30

    def test_initial_context_passed_to_first_stage(self) -> None:
        """Initial context dict is available to the first stage."""
        dag = PipelineDAG()
        dag.add_stage(
            Stage(
                name="check",
                fn=lambda ctx: {"got_seed": ctx.get("seed")},
            )
        )

        result = dag.run({"seed": 42})
        assert result.stage_results["check"].output["got_seed"] == 42

    def test_three_node_cycle_detection(self) -> None:
        """Three-node cycle A->B->C->A raises ValueError with cycle info."""
        dag = PipelineDAG()
        dag.add_stage(Stage(name="A", fn=lambda ctx: {}, deps=["C"]))
        dag.add_stage(Stage(name="B", fn=lambda ctx: {}, deps=["A"]))
        dag.add_stage(Stage(name="C", fn=lambda ctx: {}, deps=["B"]))

        with pytest.raises(ValueError, match="[Cc]ycle"):
            dag.run({})

    def test_wide_dag_20_independent_stages(self) -> None:
        """20 independent stages all succeed with deterministic ordering."""
        dag = PipelineDAG()
        for i in range(20):
            dag.add_stage(Stage(name=f"stage_{i:02d}", fn=lambda ctx: {}))

        result = dag.run({})
        assert len(result.stage_results) == 20
        assert all(sr.status == StageStatus.SUCCESS for sr in result.stage_results.values())

    def test_stage_result_error_message_contains_exception_text(self) -> None:
        """StageResult.error contains the original exception message."""
        dag = PipelineDAG()
        dag.add_stage(Stage(name="boom", fn=lambda ctx: 1 / 0))

        result = dag.run({})
        assert result.stage_results["boom"].status == StageStatus.FAILED
        assert "division by zero" in result.stage_results["boom"].error

    def test_dag_result_elapsed_nonnegative(self) -> None:
        """DAGResult.elapsed is always non-negative."""
        dag = PipelineDAG()
        result = dag.run({})
        assert result.elapsed >= 0.0
