"""Labelled execution records and descriptive reports for the package runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict

from pydantic import JsonValue

from cogant.runtime.inference_records import AxisLabels, InferenceRecord, InferenceTrace


@dataclass(frozen=True, slots=True)
class ExecutionTrace:
    """Posterior beliefs and the subsequent action-conditioned prediction."""

    step: int
    state: dict[str, float]
    action: str
    observation: str
    beliefs: dict[str, float]
    beliefs_prior: dict[str, float]
    free_energy_after: float
    policy_scores: list[tuple[str, float]]
    predicted_state: dict[str, float]

    @classmethod
    def from_record(cls, record: InferenceRecord, labels: AxisLabels) -> ExecutionTrace:
        """Attach axis labels without inferring semantics from their spelling."""
        prior = dict(zip(labels.states, record.prior, strict=True))
        return cls(
            step=record.t,
            state=prior.copy(),
            action=labels.actions[record.action],
            observation=labels.observations[record.observation],
            beliefs=dict(zip(labels.states, record.posterior, strict=True)),
            beliefs_prior=prior,
            free_energy_after=record.free_energy,
            policy_scores=list(zip(labels.actions, record.policy_scores, strict=True)),
            predicted_state=dict(zip(labels.states, record.predicted_belief, strict=True)),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        """Return JSON-ready copies so consumers cannot mutate the trace."""
        return {
            "step": self.step,
            "state": dict(self.state),
            "action": self.action,
            "observation": self.observation,
            "beliefs": dict(self.beliefs),
            "beliefs_prior": dict(self.beliefs_prior),
            "free_energy_after": self.free_energy_after,
            "policy_scores": [[action, score] for action, score in self.policy_scores],
            "predicted_state": dict(self.predicted_state),
        }


class RunnerResult(TypedDict):
    success: Literal[True]
    error: None
    steps_completed: int
    source_sha256: str
    matrices_sha256: str
    observation_mode: str
    policy_horizon: int
    policy_objective: str
    traces: list[dict[str, JsonValue]]
    final_state: dict[str, float]
    final_beliefs: dict[str, float]
    statistics: dict[str, float | int]
    free_energy_trajectory: list[float]
    action_distribution: dict[str, int]


def execution_result(
    inference: InferenceTrace, traces: list[ExecutionTrace], counts: dict[str, int]
) -> RunnerResult:
    """Summarize records without synthetic rewards or quality thresholds."""
    energies = [trace.free_energy_after for trace in traces]
    return RunnerResult(
        success=True,
        error=None,
        steps_completed=len(traces),
        source_sha256=inference.source_sha256,
        matrices_sha256=inference.matrices_sha256,
        observation_mode=inference.mode,
        policy_horizon=inference.policy_horizon,
        policy_objective=inference.policy_objective,
        traces=[trace.to_dict() for trace in traces],
        final_state=traces[-1].predicted_state.copy(),
        final_beliefs=traces[-1].beliefs.copy(),
        statistics={
            "unique_actions": len(counts),
            "mean_free_energy": sum(energies) / len(energies),
        },
        free_energy_trajectory=energies,
        action_distribution=counts.copy(),
    )


def render_report(result: RunnerResult) -> str:
    """Render execution evidence and the scope of the model rollout."""
    lines = [
        "# GNN Model Execution Report",
        "",
        "## Execution Summary",
        "",
        f"- Steps completed: {result['steps_completed']}",
        f"- GNN source SHA256: {result['source_sha256']}",
        f"- Matrices SHA256: {result['matrices_sha256']}",
        "- Observations: deterministic modes of predicted observation distributions.",
        "- Policy objective: one-step expected free energy (risk plus ambiguity).",
        "",
        "This is a model rollout, not measured execution of the source program. "
        "The trace establishes matrix inference behavior, not globally optimal control "
        "or adequacy of the source-to-model abstraction.",
        "",
        "## Belief Evolution",
        "",
        "Final posterior: " + str(result["final_beliefs"]),
        "",
        "Next predicted belief: " + str(result["final_state"]),
        "",
        "## Free Energy Dynamics",
        "",
        "Posterior VFE by step (nats): " + str(result["free_energy_trajectory"]),
        "",
        "## Action Selection Statistics",
        "",
        str(result["action_distribution"]),
        "",
        "## Detailed Execution Trace",
        "",
        "| Step | Action | Observation | Posterior VFE |",
        "| --- | --- | --- | --- |",
    ]
    for trace in result["traces"][:30]:
        lines.append(
            f"| {trace['step']} | {trace['action']} | {trace['observation']} | {trace['free_energy_after']} |"
        )
    if len(result["traces"]) > 30:
        lines.append(f"\n... ({len(result['traces']) - 30} more steps) ...")
    return "\n".join(lines) + "\n"
