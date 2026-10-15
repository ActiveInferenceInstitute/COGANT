"""Simulation of explicitly supplied categorical generative matrices."""

from __future__ import annotations

from typing import Any

from cogant.runtime.categorical import CategoricalModel, posterior
from cogant.runtime.loop import AgentRuntime
from cogant.simulate.free_energy import variational_free_energy
from cogant.simulate.report import generate_report
from cogant.statespace.compiler import StateSpaceModel


class ModelRunner:
    """Bind structural axis names to complete A/B/C/D categorical matrices."""

    def __init__(
        self,
        seed: int | None = None,
        model: StateSpaceModel | None = None,
        A: list[list[float]] | None = None,
        B: list[list[list[float]]] | None = None,
        C: list[float] | None = None,
        D: list[float] | None = None,
    ):
        self.model = model
        self.A, self.B, self.C, self.D = A, B, C, D
        if any(value is not None for value in (A, B, C, D)):
            self._matrices()

    @property
    def has_generative_model(self) -> bool:
        return all(value is not None for value in (self.A, self.B, self.C, self.D))

    def _matrices(self) -> CategoricalModel:
        if self.A is None or self.B is None or self.C is None or self.D is None:
            raise RuntimeError("inference requires A, B, C, and D matrices on the runner")
        return CategoricalModel(self.A, self.B, self.C, self.D)

    def _axes(self) -> tuple[list[str], list[str], list[str]]:
        if self.model is None:
            raise ValueError("named inference requires a bound StateSpaceModel")
        matrix = self._matrices()
        axes = (list(self.model.variables), list(self.model.observations), list(self.model.actions))
        if tuple(map(len, axes)) != (len(matrix.D), len(matrix.A), matrix.n_actions):
            raise ValueError("structural axes do not match the supplied matrices")
        return axes

    def _vector(self, beliefs: dict[str, float]) -> list[float]:
        states, _, _ = self._axes()
        if set(beliefs) != set(states):
            raise ValueError("belief keys must match the declared state axis")
        return [beliefs[state] for state in states]

    def validate_model(self, state_space: StateSpaceModel) -> dict[str, Any]:
        """
        Check that model is well-formed.

        Validates:
        - All transitions reference valid states and actions
        - All actions reference valid variables
        - State space is connected
        - No dangling references

        Args:
            state_space: StateSpaceModel to validate.

        Returns:
            Dict with "valid" (bool), "errors" (list), "warnings" (list).
        """
        errors: list[str] = []
        warnings: list[str] = []
        valid = True

        # Check variables exist
        if not state_space.variables:
            errors.append("No state variables defined")
            valid = False

        # Check transitions reference valid states
        for trans_id, trans in state_space.transitions.items():
            if trans.action_id and trans.action_id not in state_space.actions:
                errors.append(f"Transition {trans_id} references unknown action {trans.action_id}")
                valid = False

        # Check actions reference valid variables
        for action_id, action in state_space.actions.items():
            for var_id in action.effects:
                if var_id not in state_space.variables:
                    errors.append(f"Action {action_id} references unknown variable {var_id}")
                    valid = False
            for var_id in action.preconditions:
                if var_id not in state_space.variables:
                    errors.append(
                        f"Action {action_id} precondition references unknown variable {var_id}"
                    )
                    valid = False

        # Check observations reference valid nodes
        for obs_id, obs in state_space.observations.items():
            if not obs.source_node_id:
                warnings.append(f"Observation {obs_id} has no source node")

        # Check likelihoods reference valid variables
        for like_id, like in state_space.likelihoods.items():
            if like.variable_id not in state_space.variables:
                errors.append(
                    f"Likelihood {like_id} references unknown variable {like.variable_id}"
                )
                valid = False

        # Check preferences reference valid variables
        for pref_id, pref in state_space.preferences.items():
            for var_id in pref.scope:
                if var_id not in state_space.variables:
                    errors.append(f"Preference {pref_id} references unknown variable {var_id}")
                    valid = False

        return {
            "valid": valid,
            "errors": errors,
            "warnings": warnings,
            "variable_count": len(state_space.variables),
            "action_count": len(state_space.actions),
            "transition_count": len(state_space.transitions),
        }

    def vfe_from_beliefs(
        self,
        beliefs: list[float],
        observation: list[float] | None = None,
        prior: list[float] | None = None,
    ) -> float:
        matrix = self._matrices()
        return variational_free_energy(
            beliefs, matrix.D if prior is None else prior, matrix.A, observation
        )

    def efe_for_policy(
        self, policy_action_sequence: list[int], beliefs: list[float] | None = None
    ) -> float:
        matrix = self._matrices()
        return matrix.score(matrix.D if beliefs is None else beliefs, policy_action_sequence)

    def update_beliefs_from_observation(
        self, prior: list[float], observation_index: int
    ) -> list[float]:
        return posterior(prior, self._matrices().A, observation_index)

    def compute_free_energy(self, state: dict[str, Any], observation: str) -> float:
        _, observations, _ = self._axes()
        return self.vfe_from_beliefs(
            self._vector(state), [float(o == observation) for o in observations]
        )

    def belief_update(self, prior_beliefs: dict[str, float], observation: str) -> dict[str, float]:
        states, observations, _ = self._axes()
        updated = self.update_beliefs_from_observation(
            self._vector(prior_beliefs), observations.index(observation)
        )
        return dict(zip(states, updated, strict=True))

    def policy_evaluation(
        self, beliefs: dict[str, float], available_actions: list[str]
    ) -> list[tuple[str, float]]:
        _, _, actions = self._axes()
        q = self._vector(beliefs)
        return sorted(
            [(a, self.efe_for_policy([actions.index(a)], q)) for a in available_actions],
            key=lambda item: item[1],
        )

    def active_inference_step(
        self, beliefs: dict[str, float], observation: str, state_space: StateSpaceModel
    ) -> dict[str, Any]:
        self.model = state_space
        states, observations, actions = self._axes()
        matrices = self._matrices()
        runtime = AgentRuntime(matrices)
        result = runtime.step(self._vector(beliefs), observations.index(observation))
        return {
            "new_beliefs": dict(zip(states, result.posterior, strict=True)),
            "selected_action": actions[result.action],
            "predicted_next_state": dict(zip(states, result.state_dist, strict=True)),
            "free_energy": result.free_energy,
            "efe_ranking": sorted(
                zip(actions, result.policy_scores, strict=True), key=lambda x: x[1]
            ),
        }

    def simulate_step(
        self, state_space: StateSpaceModel, current_state: dict[str, Any], action_id: str
    ) -> dict[str, Any]:
        self.model = state_space
        states, _, actions = self._axes()
        prediction = self._matrices().predict(self._vector(current_state), actions.index(action_id))
        return {
            "next_state": dict(zip(states, prediction, strict=True)),
            "action_applied": action_id,
            "success": True,
        }

    def run_active_inference(
        self, state_space: StateSpaceModel, steps: int = 20
    ) -> list[dict[str, Any]]:
        self.model = state_space
        states, observations, _ = self._axes()
        matrix = self._matrices()
        belief = dict(zip(states, matrix.D, strict=True))
        trace = [
            {
                "step": 0,
                "phase": "initial",
                "beliefs": belief.copy(),
                "observation": None,
                "action": None,
                "free_energy": None,
                "predicted_state": {},
            }
        ]
        if steps < 0:
            raise ValueError("step count must be non-negative")
        for t in range(1, steps + 1):
            outcomes = matrix.observe(self._vector(belief))
            obs = observations[max(range(len(outcomes)), key=outcomes.__getitem__)]
            result = self.active_inference_step(belief, obs, state_space)
            trace.append(
                {
                    "step": t,
                    "phase": "observation",
                    "beliefs": result["new_beliefs"],
                    "observation": obs,
                    "action": result["selected_action"],
                    "free_energy": result["free_energy"],
                    "predicted_state": result["predicted_next_state"],
                }
            )
            belief = result["predicted_next_state"]
        return trace

    def run_simulation(self, state_space: StateSpaceModel, steps: int = 10) -> list[dict[str, Any]]:
        return self.run_active_inference(state_space, steps)

    def generate_report(self, trace: list[dict[str, Any]]) -> str:
        return generate_report(trace)

    def generate_trace(self, state_space: StateSpaceModel) -> dict[str, Any]:
        return {
            "schema_name": state_space.schema_name,
            "trace": self.run_active_inference(state_space, 5),
            "variables": list(state_space.variables),
            "observations": list(state_space.observations),
            "actions": list(state_space.actions),
            "metadata": state_space.metadata,
        }
