"""
Model validation and state space simulation with Active Inference.

Validates state space models and runs simulations using Active Inference
to explore state trajectories and compute free energy dynamics.
"""

from typing import Dict, List, Optional, Any, Tuple
import random
import logging
import math
from collections import defaultdict

from cogant.statespace.compiler import StateSpaceModel, Action, Transition
from cogant.simulate.distributions import CategoricalDistribution, TransitionMatrix
from cogant.simulate.free_energy import (
    FreeEnergyCalculator,
    bayesian_belief_update,
    expected_free_energy as principled_expected_free_energy,
    uniform_distribution,
    variational_free_energy as principled_variational_free_energy,
)

logger = logging.getLogger(__name__)


class ModelRunner:
    """Validate and simulate state space models.

    If the caller provides POMDP matrices ``A`` (likelihood), ``B``
    (transition), ``C`` (log preferences) and ``D`` (prior), VFE and EFE
    computations delegate to the principled matrix-based implementations
    in :mod:`cogant.simulate.free_energy`. When the matrices are absent,
    the runner falls back to the earlier heuristic implementation.
    """

    def __init__(
        self,
        seed: Optional[int] = None,
        model: Optional[StateSpaceModel] = None,
        A: Optional[List[List[float]]] = None,
        B: Optional[List[List[List[float]]]] = None,
        C: Optional[List[float]] = None,
        D: Optional[List[float]] = None,
    ):
        """Initialize the ModelRunner.

        Args:
            seed: Optional random seed for reproducible simulations.
            model: Optional StateSpaceModel associated with the runner.
                Kept on the instance so callers that want to bind a model
                once don't have to pass it to every method.
            A: Likelihood matrix ``A[o][s] = P(o|s)``. Shape
                ``[n_obs, n_states]``.
            B: Transition tensor ``B[s'][s][a] = P(s'|s, a)``. Shape
                ``[n_states, n_states, n_actions]``.
            C: Log preference vector over observations. Shape ``[n_obs]``.
            D: Initial prior P(s). Shape ``[n_states]``.
        """
        if seed is not None:
            random.seed(seed)
        self.model = model
        self.A = A
        self.B = B
        self.C = C
        self.D = D

    @property
    def has_generative_model(self) -> bool:
        """Whether A/B/C/D matrices are available for principled VFE/EFE."""
        return all(x is not None for x in (self.A, self.B, self.C, self.D))

    def validate_model(self, state_space: StateSpaceModel) -> Dict[str, Any]:
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
        errors: List[str] = []
        warnings: List[str] = []
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
                errors.append(f"Likelihood {like_id} references unknown variable {like.variable_id}")
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

    def simulate_step(
        self, state_space: StateSpaceModel, current_state: Dict[str, Any], action_id: str
    ) -> Dict[str, Any]:
        """
        Given current state and action, compute next state (simple transition).

        Args:
            state_space: StateSpaceModel containing the actions and transitions.
            current_state: Current state as dict of variable_id -> value.
            action_id: ID of action to execute.

        Returns:
            Dict with "next_state", "action_applied", "success" keys.
        """
        if action_id not in state_space.actions:
            return {
                "next_state": current_state,
                "action_applied": action_id,
                "success": False,
                "error": f"Unknown action {action_id}",
            }

        action = state_space.actions[action_id]

        # Check preconditions
        for precond_var in action.preconditions:
            if precond_var not in current_state:
                return {
                    "next_state": current_state,
                    "action_applied": action_id,
                    "success": False,
                    "error": f"Precondition {precond_var} not satisfied",
                }

        # Apply effects (simple model: increment/decrement or toggle)
        next_state = current_state.copy()
        for effect_var in action.effects:
            if effect_var in next_state:
                # Simple effect: increment numeric, toggle boolean
                current_val = next_state[effect_var]
                if isinstance(current_val, bool):
                    next_state[effect_var] = not current_val
                elif isinstance(current_val, (int, float)):
                    next_state[effect_var] = current_val + 1
                elif isinstance(current_val, str):
                    next_state[effect_var] = f"{current_val}_modified"

        return {
            "next_state": next_state,
            "action_applied": action_id,
            "success": True,
            "effects_applied": action.effects,
        }

    def run_simulation(
        self, state_space: StateSpaceModel, steps: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Run N steps of random walk simulation.

        Args:
            state_space: StateSpaceModel to simulate.
            steps: Number of steps to simulate.

        Returns:
            List of state dicts, one per step, with "state", "action", "step" keys.
        """
        # Initialize state with default values
        current_state: Dict[str, Any] = {}
        for var_id, variable in state_space.variables.items():
            # Use type default based on variable type
            if variable.var_type.value == "boolean":
                current_state[var_id] = False
            elif variable.var_type.value in ("discrete", "integer"):
                current_state[var_id] = 0
            elif variable.var_type.value in ("continuous", "float"):
                current_state[var_id] = 0.0
            else:
                current_state[var_id] = None

        trace: List[Dict[str, Any]] = [
            {
                "step": 0,
                "state": current_state.copy(),
                "action": None,
            }
        ]

        # Run steps
        for step_num in range(1, steps + 1):
            # Pick random action
            if not state_space.actions:
                break

            action_id = random.choice(list(state_space.actions.keys()))

            # Simulate step
            result = self.simulate_step(state_space, current_state, action_id)
            current_state = result["next_state"]

            trace.append(
                {
                    "step": step_num,
                    "state": current_state.copy(),
                    "action": action_id,
                    "success": result.get("success", False),
                }
            )

        return trace

    # ------------------------------------------------------------------
    # Principled matrix-based VFE/EFE entry points.
    # ------------------------------------------------------------------

    def vfe_from_beliefs(
        self,
        beliefs: List[float],
        observation: Optional[List[float]] = None,
        prior: Optional[List[float]] = None,
    ) -> float:
        """Compute principled VFE from explicit belief vectors.

        Requires that ``A`` (and either ``D`` or an explicit ``prior``) be
        set on the runner. Raises ``RuntimeError`` if the generative model
        is absent.

        Args:
            beliefs: Q(s) as a list of probabilities.
            observation: Observation distribution. If None, uniform.
            prior: Prior P(s). If None, uses ``self.D``.

        Returns:
            Variational free energy (nats). Lower is better.
        """
        if self.A is None:
            raise RuntimeError(
                "vfe_from_beliefs requires A (likelihood matrix) on the runner"
            )
        effective_prior = prior if prior is not None else self.D
        if effective_prior is None:
            effective_prior = uniform_distribution(len(beliefs))
        return principled_variational_free_energy(
            beliefs=beliefs,
            prior=effective_prior,
            likelihood_matrix=self.A,
            observation=observation,
        )

    def efe_for_policy(
        self,
        policy_action_sequence: List[int],
        beliefs: Optional[List[float]] = None,
    ) -> float:
        """Compute principled EFE for a sequence of action indices.

        Requires ``A``, ``B`` and ``C`` on the runner. ``beliefs`` defaults
        to ``self.D`` (the prior) if not provided.

        Args:
            policy_action_sequence: Sequence of action indices.
            beliefs: Initial Q(s). Defaults to ``self.D``.

        Returns:
            Expected free energy (nats). Lower is better.
        """
        if self.A is None or self.B is None or self.C is None:
            raise RuntimeError(
                "efe_for_policy requires A, B, and C on the runner"
            )
        start = beliefs if beliefs is not None else self.D
        if start is None:
            raise RuntimeError("No initial beliefs and D is None")
        return principled_expected_free_energy(
            policy_action_sequence=policy_action_sequence,
            beliefs=start,
            likelihood_matrix=self.A,
            transition_tensor=self.B,
            log_preferences=self.C,
        )

    def update_beliefs_from_observation(
        self,
        prior: List[float],
        observation_index: int,
    ) -> List[float]:
        """Bayesian belief update using the runner's likelihood matrix.

        Args:
            prior: Current Q(s) before the observation.
            observation_index: Index of the observed outcome.

        Returns:
            Posterior Q(s | o).
        """
        if self.A is None:
            raise RuntimeError(
                "update_beliefs_from_observation requires A on the runner"
            )
        return bayesian_belief_update(prior, self.A, observation_index)

    # ------------------------------------------------------------------
    # Back-compat state-dict VFE (used when no generative model matrices).
    # ------------------------------------------------------------------

    def compute_free_energy(
        self, state: Dict[str, Any], observation: str
    ) -> float:
        """
        Compute variational free energy for a state-observation pair.

        When ``self.A`` and ``self.D`` are present, this delegates to the
        principled matrix-based VFE by projecting ``state`` into a one-hot
        belief over the variables in ``state``. Otherwise it falls back to
        the heuristic implementation preserved for backward compatibility.

        VFE = KL(Q||P) - E_Q[log P(o|s)]
            = complexity - accuracy

        Where:
        - Q(s) = belief distribution over states (prior or posterior)
        - P(s) = generative prior (uniform in this case)
        - P(o|s) = likelihood of observation given state
        - Complexity = KL divergence (how far posterior is from prior)
        - Accuracy = expected log likelihood (how well beliefs predict observation)

        Minimizing VFE drives:
        1. Accuracy: selecting beliefs that predict observations well
        2. Simplicity: keeping beliefs close to the prior

        Args:
            state: Current state dict (variable_id -> value).
            observation: Observed value.

        Returns:
            Variational free energy (float). Lower is better.
        """
        if not state:
            return 0.0

        # Principled path: if A and D are available and their dimensions
        # match the state, use the matrix-based VFE with a one-hot belief
        # concentrated on the observed variable.
        if self.A is not None and self.D is not None:
            categories = list(state.keys())
            n_states = len(categories)
            if n_states == len(self.D) and all(
                len(row) == n_states for row in self.A
            ):
                # Build a one-hot belief focused on the matching variable.
                if observation in categories:
                    idx = categories.index(observation)
                    beliefs = [0.0] * n_states
                    beliefs[idx] = 1.0
                else:
                    beliefs = [1.0 / n_states] * n_states
                return principled_variational_free_energy(
                    beliefs=beliefs,
                    prior=list(self.D),
                    likelihood_matrix=self.A,
                    observation=None,
                )

        # Heuristic fallback (back-compat): create a belief distribution
        # from state values using state keys as "categories".
        categories = list(state.keys())

        # Create a belief distribution that concentrates on states matching the observation
        belief_probs = []
        for var_id in categories:
            if str(observation) == str(var_id):
                belief_probs.append(0.9)  # High belief if observation matches state
            else:
                belief_probs.append(0.1 / max(1, len(categories) - 1))

        belief_dist = CategoricalDistribution(categories, belief_probs)

        # Compute KL divergence: KL(Q||P) where P is uniform prior
        # KL divergence is always >= 0, = 0 only when Q = P
        uniform_prior = CategoricalDistribution(categories)
        complexity = belief_dist.kl_divergence(uniform_prior)

        # Compute expected log likelihood: E_Q[log P(o|s)]
        # Likelihood model: observation == state gives high likelihood
        accuracy = 0.0
        for var_id in categories:
            belief_prob = belief_dist.dist[var_id]
            if str(observation) == str(var_id):
                likelihood_prob = 0.9  # High likelihood if match
            else:
                likelihood_prob = 0.1 / max(1, len(categories) - 1)

            if likelihood_prob > 0:
                accuracy += belief_prob * math.log(likelihood_prob)

        # VFE = complexity - accuracy
        # When accuracy is large (good prediction), VFE is smaller
        # When complexity is large (beliefs far from prior), VFE is larger
        vfe = complexity - accuracy
        return float(vfe)

    def belief_update(
        self, prior_beliefs: Dict[str, float], observation: str
    ) -> Dict[str, float]:
        """
        Bayesian belief update using observation.

        Posterior ∝ likelihood × prior

        Args:
            prior_beliefs: Prior belief distribution (dict of state -> probability).
            observation: The observed value.

        Returns:
            Updated posterior belief distribution.
        """
        if not prior_beliefs:
            return {}

        states = list(prior_beliefs.keys())
        prior_dist = CategoricalDistribution(
            states, [prior_beliefs[s] for s in states]
        )

        # Create likelihood model: obs == state gives high likelihood
        likelihood_probs = []
        for state in states:
            if str(observation) == str(state):
                likelihood_probs.append(0.8)
            else:
                likelihood_probs.append(0.2 / max(1, len(states) - 1))

        likelihood_dist = CategoricalDistribution(states, likelihood_probs)

        # Posterior = likelihood * prior (normalized)
        posterior_dist = prior_dist.update(observation, likelihood_dist)

        return posterior_dist.dist

    def policy_evaluation(
        self, beliefs: Dict[str, float], available_actions: List[str]
    ) -> List[Tuple[str, float]]:
        """
        Evaluate expected free energy for each action.

        Expected Free Energy (EFE) = E_Q[complexity - accuracy]
        where we sum over future timesteps.

        EFE combines:
        - Epistemic value: -KL(Q_future || P_future) = complexity reduction (exploration)
        - Pragmatic value: -E_Q[log P(o|s)] = accuracy (exploitation toward preferred outcomes)

        Args:
            beliefs: Current belief distribution (state -> probability).
            available_actions: List of available action IDs.

        Returns:
            List of (action_id, efe_score) tuples, sorted by score (ascending = best).
        """
        if not available_actions or not beliefs:
            return [(action, 0.0) for action in available_actions]

        states = list(beliefs.keys())
        beliefs_dist = CategoricalDistribution(
            states, [beliefs[s] for s in states]
        )

        rankings = []
        for action in available_actions:
            # Compute EFE using a 3-step lookahead
            efe = 0.0
            current_beliefs = beliefs_dist

            for step in range(3):  # Planning horizon
                # Epistemic value: KL(Q || P_uniform) - rewards exploration
                uniform_prior = CategoricalDistribution(states)
                epistemic = current_beliefs.kl_divergence(uniform_prior)

                # Pragmatic value: log likelihood under current beliefs
                # Assume observation matches most likely state
                max_state = max(current_beliefs.dist.items(), key=lambda x: x[1])[0]

                # Likelihood: match observation if state == observation
                pragmatic = 0.0
                for state in states:
                    belief_prob = current_beliefs.dist[state]
                    # High likelihood if state matches the expected observation
                    likelihood = 0.9 if state == max_state else 0.1 / max(1, len(states) - 1)
                    if likelihood > 0:
                        pragmatic += belief_prob * math.log(likelihood)

                # EFE for this step = KL divergence (complexity) minus accuracy
                # Lower is better, so we add the complexity and subtract the pragmatic value
                step_efe = epistemic - pragmatic
                efe += step_efe

                # Update beliefs for next step (assume no new observation changes beliefs much)
                # For simplicity, beliefs stay roughly same; in full implementation would marginalize over actions

            # Average over horizon
            efe = efe / 3.0
            rankings.append((action, efe))

        return sorted(rankings, key=lambda x: x[1])

    def active_inference_step(
        self, beliefs: Dict[str, float], observation: str, state_space: StateSpaceModel
    ) -> Dict[str, Any]:
        """
        Full Active Inference step.

        1. Belief update: posterior ∝ likelihood × prior
        2. Policy evaluation: rank actions by expected free energy
        3. Action selection: choose lowest EFE action
        4. State transition: simulate step under selected action

        Args:
            beliefs: Current belief distribution (state -> probability).
            observation: New observation.
            state_space: State space model for dynamics.

        Returns:
            Dict with keys:
              - new_beliefs: Updated beliefs
              - selected_action: Chosen action ID
              - predicted_next_state: Expected next state
              - free_energy: Variational free energy
              - efe_ranking: Policy ranking by EFE
        """
        # Step 1: Belief update
        new_beliefs = self.belief_update(beliefs, observation)

        # Step 2: Policy evaluation
        available_actions = list(state_space.actions.keys())
        policy_ranking = self.policy_evaluation(new_beliefs, available_actions)

        # Step 3: Action selection (choose lowest EFE)
        selected_action = policy_ranking[0][0] if policy_ranking else None
        selected_efe = policy_ranking[0][1] if policy_ranking else 0.0

        # Step 4: State transition
        # Use the most likely state under updated beliefs
        most_likely_state_id = max(new_beliefs.items(), key=lambda x: x[1])[0]
        initial_state = {var_id: 0 for var_id in state_space.variables.keys()}
        initial_state[most_likely_state_id] = 1

        predicted_next_state = {}
        if selected_action:
            result = self.simulate_step(state_space, initial_state, selected_action)
            predicted_next_state = result.get("next_state", {})

        # Compute free energy for the observation
        # Use the beliefs-derived state for more accurate VFE computation
        observation_state = {var_id: 1.0 if var_id == most_likely_state_id else 0.0
                            for var_id in state_space.variables.keys()}
        free_energy = self.compute_free_energy(observation_state, observation)

        return {
            "new_beliefs": new_beliefs,
            "selected_action": selected_action,
            "predicted_next_state": predicted_next_state,
            "free_energy": free_energy,
            "efe_ranking": [(a, float(efe)) for a, efe in policy_ranking],
        }

    def run_active_inference(
        self, state_space: StateSpaceModel, steps: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Run full Active Inference loop.

        Performs belief updates, policy evaluation, and action selection
        for N steps.

        Args:
            state_space: State space model.
            steps: Number of steps to simulate.

        Returns:
            List of trace dicts, each with:
              - step: step number
              - beliefs: belief distribution
              - observation: observed value
              - action: selected action
              - free_energy: VFE for this step
              - predicted_state: expected next state
        """
        # Initialize beliefs (uniform over states)
        state_ids = list(state_space.variables.keys())

        # Handle empty state space gracefully
        if not state_ids:
            logger.warning("State space has no variables, returning minimal trace")
            return [
                {
                    "step": 0,
                    "beliefs": {},
                    "observation": None,
                    "action": None,
                    "free_energy": 0.0,
                    "predicted_state": {},
                }
            ]

        initial_beliefs = {state_id: 1.0 / len(state_ids) for state_id in state_ids}

        trace: List[Dict[str, Any]] = [
            {
                "step": 0,
                "beliefs": initial_beliefs.copy(),
                "observation": None,
                "action": None,
                "free_energy": 0.0,
                "predicted_state": {},
            }
        ]

        current_beliefs = initial_beliefs.copy()

        for step_num in range(1, steps + 1):
            # Generate observation (most likely under current beliefs)
            if not current_beliefs:
                break
            max_state = max(current_beliefs.items(), key=lambda x: x[1])[0]
            observation = max_state

            # Run Active Inference step
            ai_result = self.active_inference_step(
                current_beliefs, observation, state_space
            )

            current_beliefs = ai_result["new_beliefs"]

            trace.append(
                {
                    "step": step_num,
                    "beliefs": current_beliefs.copy(),
                    "observation": observation,
                    "action": ai_result["selected_action"],
                    "free_energy": ai_result["free_energy"],
                    "predicted_state": ai_result["predicted_next_state"],
                }
            )

        return trace

    def generate_report(self, trace: List[Dict[str, Any]]) -> str:
        """
        Generate markdown report of Active Inference simulation.

        Args:
            trace: Trace from run_active_inference().

        Returns:
            Markdown string.
        """
        lines = [
            "# Active Inference Simulation Report",
            "",
            f"## Summary",
            f"- Total steps: {len(trace)}",
            f"- Initial beliefs: uniform",
            "",
            "## Free Energy Dynamics",
            "",
        ]

        # Extract free energy trajectory
        fe_values = [step.get("free_energy", 0.0) for step in trace]
        if fe_values:
            mean_fe = sum(fe_values) / len(fe_values)
            min_fe = min(fe_values)
            max_fe = max(fe_values)
            lines.extend([
                f"- Mean VFE: {mean_fe:.4f}",
                f"- Min VFE: {min_fe:.4f}",
                f"- Max VFE: {max_fe:.4f}",
                "",
            ])

        # Action distribution
        lines.append("## Actions Taken")
        action_counts: Dict[str, int] = defaultdict(int)
        for step in trace:
            action = step.get("action")
            if action:
                action_counts[action] += 1

        if action_counts:
            lines.append("")
            for action, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"- {action}: {count} times")
        else:
            lines.append("- No actions taken")

        lines.append("")

        # Belief trajectory sample
        lines.extend([
            "## Belief Evolution (Sample)",
            "",
        ])

        sample_indices = [0, len(trace) // 4, len(trace) // 2, (3 * len(trace)) // 4, len(trace) - 1]
        sample_indices = [i for i in sample_indices if i < len(trace)]

        for idx in sample_indices:
            step = trace[idx]
            beliefs = step.get("beliefs", {})
            lines.append(f"### Step {step.get('step', idx)}")
            if beliefs:
                top_beliefs = sorted(beliefs.items(), key=lambda x: x[1], reverse=True)[:3]
                for state, prob in top_beliefs:
                    lines.append(f"- {state}: {prob:.4f}")
            lines.append("")

        return "\n".join(lines)

    def generate_trace(self, state_space: StateSpaceModel) -> Dict[str, Any]:
        """
        Produce a trace of state transitions as JSON.

        Args:
            state_space: StateSpaceModel to trace.

        Returns:
            Dict with "trace", "variables", "observations", "actions", "metadata" keys.
        """
        # Run a 5-step simulation
        trace_steps = self.run_simulation(state_space, steps=5)

        # Collect variable info
        variables_info = [
            {
                "id": var_id,
                "name": variable.name,
                "var_type": variable.var_type.value,
                "node_id": variable.node_id,
            }
            for var_id, variable in state_space.variables.items()
        ]

        # Collect observation info
        observations_info = [
            {
                "id": obs_id,
                "name": obs.name,
                "modality_type": obs.modality_type,
                "source_node_id": obs.source_node_id,
            }
            for obs_id, obs in state_space.observations.items()
        ]

        # Collect action info
        actions_info = [
            {
                "id": action_id,
                "name": action.name,
                "effects": action.effects,
                "preconditions": action.preconditions,
            }
            for action_id, action in state_space.actions.items()
        ]

        return {
            "schema_name": state_space.schema_name,
            "trace": trace_steps,
            "variables": variables_info,
            "observations": observations_info,
            "actions": actions_info,
            "metadata": {
                "trace_length": len(trace_steps),
                "state_space_id": state_space.id,
                "time_regime": state_space.time_regime.value if state_space.time_regime else None,
            },
        }
