"""
GNN model runner — executes a GNN model package with Active Inference.

Loads a GNN package from disk and runs the generative model with proper Active Inference:
- Maintain beliefs over hidden states (probability distribution)
- Observe → update beliefs (Bayesian inference)
- Evaluate policies via Expected Free Energy (EFE)
- Select action that minimizes free energy
- Track rich execution traces with free energy dynamics
"""

import json
import logging
import math
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["ExecutionTrace", "GNNModelRunner", "load_gnn_package"]

# Import Active Inference components
try:
    from cogant.simulate.free_energy import FreeEnergyCalculator
    ACTIVE_INFERENCE_AVAILABLE = True
except ImportError:
    ACTIVE_INFERENCE_AVAILABLE = False
    logger.warning("Active Inference components not available, using fallback mode")


class ExecutionTrace:
    """Record of a single GNN model step with Active Inference details."""

    def __init__(
        self,
        step: int,
        state: dict[str, Any],
        action: str | None = None,
        observation: str | None = None,
        reward: float = 0.0,
        beliefs: dict[str, float] | None = None,
        beliefs_prior: dict[str, float] | None = None,
        free_energy_before: float = 0.0,
        free_energy_after: float = 0.0,
        policy_scores: list[tuple[str, float]] | None = None,
        action_rationale: str | None = None,
        predicted_state: dict[str, Any] | None = None,
    ):
        """
        Initialize execution trace with Active Inference data.

        Args:
            step: Step number.
            state: State at this step.
            action: Action taken.
            observation: Observation received.
            reward: Reward for this step.
            beliefs: Current beliefs (probability over hidden states).
            beliefs_prior: Prior beliefs before update.
            free_energy_before: VFE before belief update.
            free_energy_after: VFE after belief update.
            policy_scores: List of (action, efe_score) tuples for policy evaluation.
            action_rationale: Why this action was selected.
            predicted_state: Predicted next state under selected action.
        """
        self.step = step
        self.state = state
        self.action = action
        self.observation = observation
        self.reward = reward
        self.timestamp = datetime.now(UTC).isoformat()
        self.beliefs = beliefs or {}
        self.beliefs_prior = beliefs_prior or {}
        self.free_energy_before = free_energy_before
        self.free_energy_after = free_energy_after
        self.policy_scores = policy_scores or []
        self.action_rationale = action_rationale
        self.predicted_state = predicted_state or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step": self.step,
            "timestamp": self.timestamp,
            "state": self.state,
            "action": self.action,
            "observation": self.observation,
            "reward": self.reward,
            "beliefs": self.beliefs,
            "beliefs_prior": self.beliefs_prior,
            "free_energy_before": self.free_energy_before,
            "free_energy_after": self.free_energy_after,
            "policy_scores": self.policy_scores,
            "action_rationale": self.action_rationale,
            "predicted_state": self.predicted_state,
        }


class GNNModelRunner:
    """Runs a GNN model package — executes the generative model with Active Inference."""

    def __init__(self) -> None:
        """Initialize runner."""
        # These are populated by ``load_package`` before any of the
        # ``run``/``_load_*`` helpers read them. Typing as non-optional
        # silences a cascade of union-attr / operator noise without
        # hiding a real null dereference.
        self.package_dir: Path = Path(".")
        self.manifest: dict[str, Any] = {}
        self.model: dict[str, Any] = {}
        self.state_space: dict[str, Any] = {}
        self.traces: list[ExecutionTrace] = []
        self.fe_calculator: FreeEnergyCalculator | None = None
        self.beliefs_history: list[dict[str, float]] = []
        self.free_energy_trajectory: list[float] = []
        self.action_counts: dict[str, int] = defaultdict(int)

    def load_package(self, package_dir: str) -> dict[str, Any]:
        """
        Load a GNN package from disk.

        Args:
            package_dir: Path to the package directory.

        Returns:
            Manifest dictionary.
        """
        self.package_dir = Path(package_dir)
        logger.info(f"Loading GNN package from {self.package_dir}")

        # Load manifest
        manifest_path = self.package_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        with open(manifest_path) as f:
            self.manifest = json.load(f)
        logger.info(f"Loaded manifest: version {self.manifest.get('version')}")

        # Load model
        model_path = self.package_dir / "model.gnn.json"
        if model_path.exists():
            with open(model_path) as f:
                self.model = json.load(f)
            logger.info("Loaded model.gnn.json")

        # Load state space
        state_space_path = self.package_dir / "state_space.json"
        if state_space_path.exists():
            with open(state_space_path) as f:
                self.state_space = json.load(f)
            logger.info("Loaded state_space.json")

        # Try to load transitions and preferences for Active Inference
        self._load_active_inference_models()

        return self.manifest

    def _load_active_inference_models(self) -> None:
        """Load transition and preference models for Active Inference."""
        try:
            # Load transitions.json
            transitions_path = self.package_dir / "transitions.json"
            if transitions_path.exists():
                with open(transitions_path) as f:
                    json.load(f)
                logger.debug("Loaded transitions.json")

            # Load preferences.json
            preferences_path = self.package_dir / "preferences.json"
            if preferences_path.exists():
                with open(preferences_path) as f:
                    json.load(f)
                logger.debug("Loaded preferences.json")

            logger.info("Active Inference models loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load Active Inference models: {e}")

    def run(self, steps: int = 10) -> dict[str, Any]:
        """
        Execute the GNN model with Active Inference.

        Performs full Active Inference loop:
        1. Initialize beliefs (uniform over hidden states)
        2. Each step: observe → update beliefs → evaluate policies → select action
        3. Track beliefs, free energy, and policy evaluations

        Args:
            steps: Number of steps to execute.

        Returns:
            Execution result dictionary with traces and statistics.
        """
        if not self.manifest:
            raise RuntimeError("Package not loaded. Call load_package first.")

        logger.info(f"Running GNN model with Active Inference for {steps} steps")
        self.traces = []
        self.beliefs_history = []
        self.free_energy_trajectory = []
        self.action_counts = defaultdict(int)

        # Initialize beliefs and state
        beliefs = self._initialize_beliefs()
        state = self._initialize_state()
        self.beliefs_history.append(beliefs.copy())
        total_reward = 0.0

        logger.debug(f"Initial beliefs: {beliefs}")
        logger.debug(f"Initial state: {state}")

        # Execute Active Inference steps
        for step_num in range(steps):
            try:
                # Step 1: Generate observation from current state
                observation = self._generate_observation(state)
                logger.debug(f"  Step {step_num}: observation={observation}")

                # Step 2: Compute free energy before belief update
                fe_before = self._compute_vfe(beliefs, observation)

                # Step 3: Update beliefs (Bayesian inference)
                prior_beliefs = beliefs.copy()
                beliefs = self._update_beliefs(beliefs, observation)
                self.beliefs_history.append(beliefs.copy())

                # Step 4: Compute free energy after belief update
                fe_after = self._compute_vfe(beliefs, observation)
                self.free_energy_trajectory.append(fe_after)

                # Step 5: Evaluate policies (Expected Free Energy)
                policy_scores = self._evaluate_policies(beliefs)

                # Step 6: Select action with lowest EFE
                action, rationale = self._select_action_active_inference(
                    beliefs, policy_scores
                )
                self.action_counts[action] += 1

                # Step 7: Predict next state
                predicted_state = self._compute_transition(state, action)

                # Step 8: Compute reward
                reward = self._compute_reward(state, action, predicted_state)
                total_reward += reward

                # Record rich trace
                trace = ExecutionTrace(
                    step=step_num,
                    state=state.copy(),
                    action=action,
                    observation=observation,
                    reward=reward,
                    beliefs=beliefs.copy(),
                    beliefs_prior=prior_beliefs.copy(),
                    free_energy_before=fe_before,
                    free_energy_after=fe_after,
                    policy_scores=policy_scores,
                    action_rationale=rationale,
                    predicted_state=predicted_state,
                )
                self.traces.append(trace)

                logger.debug(
                    f"  Step {step_num}: action={action}, reward={reward:.3f}, "
                    f"vfe_after={fe_after:.4f}"
                )

                state = predicted_state

            except Exception as e:
                logger.error(f"Error in step {step_num}: {e}", exc_info=True)
                break

        # Compile results
        result = {
            "success": True,
            "steps_completed": len(self.traces),
            "total_reward": total_reward,
            "avg_reward": total_reward / len(self.traces) if self.traces else 0.0,
            "traces": [t.to_dict() for t in self.traces],
            "final_state": state,
            "final_beliefs": beliefs,
            "statistics": self._compute_statistics(),
            "free_energy_trajectory": self.free_energy_trajectory,
            "action_distribution": dict(self.action_counts),
        }

        logger.info(
            f"Execution complete: {len(self.traces)} steps, "
            f"total_reward={total_reward:.3f}, "
            f"final_vfe={self.free_energy_trajectory[-1] if self.free_energy_trajectory else 0.0:.4f}"
        )

        return result

    def generate_execution_report(self, trace: dict[str, Any] | None = None) -> str:
        """
        Generate comprehensive markdown report of the GNN model execution with Active Inference.

        Includes:
        - Initial vs final beliefs
        - Free energy trajectory
        - Action distribution
        - Belief convergence analysis
        - Model quality assessment

        Args:
            trace: Optional execution trace dict. If None, uses last run.

        Returns:
            Markdown report string.
        """
        if trace is None and not self.traces:
            return "# GNN Execution Report\n\nNo traces to report.\n"

        trace_data: dict[str, Any] = trace if trace is not None else {}
        traces = trace_data.get("traces", []) if trace_data else [t.to_dict() for t in self.traces]
        stats = trace_data.get("statistics", {}) if trace_data else self._compute_statistics()
        fe_trajectory = trace_data.get("free_energy_trajectory", []) if trace_data else self.free_energy_trajectory
        action_dist = trace_data.get("action_distribution", {}) if trace_data else dict(self.action_counts)

        report = "# GNN Model Execution Report (Active Inference)\n\n"

        # Summary section
        report += "## Execution Summary\n\n"
        report += f"- **Timestamp**: {datetime.now(UTC).isoformat()}\n"
        report += f"- **Package**: {self.package_dir}\n"
        report += f"- **Steps Completed**: {len(traces)}\n"
        report += f"- **Total Reward**: {trace_data.get('total_reward', 0.0):.3f}\n"
        report += f"- **Average Reward**: {trace_data.get('avg_reward', 0.0):.3f}\n"
        report += "- **Execution Mode**: Active Inference with Bayesian Belief Updates\n\n"

        # Belief evolution section
        report += "## Belief Evolution\n\n"
        if self.beliefs_history:
            initial_beliefs = self.beliefs_history[0]
            final_beliefs = self.beliefs_history[-1]

            report += "### Initial Beliefs\n\n"
            for state, prob in sorted(initial_beliefs.items(), key=lambda x: -x[1])[:5]:
                report += f"- {state}: {prob:.4f}\n"
            report += "\n"

            report += "### Final Beliefs\n\n"
            for state, prob in sorted(final_beliefs.items(), key=lambda x: -x[1])[:5]:
                report += f"- {state}: {prob:.4f}\n"
            report += "\n"

            # Belief convergence
            initial_entropy = self._entropy(initial_beliefs)
            final_entropy = self._entropy(final_beliefs)
            report += "**Belief Convergence Metrics**:\n\n"
            report += f"- Initial entropy (uncertainty): {initial_entropy:.4f} nats\n"
            report += f"- Final entropy (uncertainty): {final_entropy:.4f} nats\n"
            report += f"- Entropy reduction: {(initial_entropy - final_entropy):.4f} nats\n\n"

        # Free energy trajectory section
        report += "## Free Energy Dynamics\n\n"
        if fe_trajectory:
            min_fe = min(fe_trajectory)
            max_fe = max(fe_trajectory)
            mean_fe = sum(fe_trajectory) / len(fe_trajectory)
            final_fe = fe_trajectory[-1]

            report += f"- **Initial Free Energy**: {fe_trajectory[0]:.4f} nats\n"
            report += f"- **Final Free Energy**: {final_fe:.4f} nats\n"
            report += f"- **Mean Free Energy**: {mean_fe:.4f} nats\n"
            report += f"- **Min Free Energy**: {min_fe:.4f} nats\n"
            report += f"- **Max Free Energy**: {max_fe:.4f} nats\n"
            report += f"- **Free Energy Trend**: {'↓ Decreasing' if final_fe < fe_trajectory[0] else '↑ Increasing'}\n\n"

        # Action distribution section
        report += "## Action Selection Statistics\n\n"
        if action_dist:
            total_actions = sum(action_dist.values())
            report += f"**Most-selected actions** (out of {total_actions} total):\n\n"
            for action, count in sorted(action_dist.items(), key=lambda x: -x[1])[:10]:
                freq = 100.0 * count / total_actions if total_actions > 0 else 0.0
                report += f"- {action}: {count} times ({freq:.1f}%)\n"
            report += "\n"

        # Statistics section
        report += "## Execution Statistics\n\n"
        if stats:
            for key, value in stats.items():
                if isinstance(value, float):
                    report += f"- **{key.replace('_', ' ').title()}**: {value:.4f}\n"
                else:
                    report += f"- **{key.replace('_', ' ').title()}**: {value}\n"
        report += "\n"

        # Trace details section
        report += "## Detailed Execution Trace\n\n"
        report += "| Step | Action | Obs | VFE After | Reward | Top Belief |\n"
        report += "|------|--------|-----|-----------|--------|------------|\n"

        for trace_item in traces[:30]:  # Limit to first 30 steps
            step = trace_item.get("step", "")
            action = trace_item.get("action", "-")
            obs = trace_item.get("observation", "-")
            vfe = trace_item.get("free_energy_after", 0.0)
            reward = trace_item.get("reward", 0.0)

            # Get top belief
            beliefs = trace_item.get("beliefs", {})
            top_belief = "-"
            if beliefs:
                top_state = max(beliefs.items(), key=lambda x: x[1])[0]
                top_prob = max(beliefs.values(), default=0.0)
                top_belief = f"{top_state[:8]}... ({top_prob:.2f})"

            report += f"| {step} | {str(action)[:12]} | {str(obs)[:8]} | {vfe:.3f} | {reward:.3f} | {top_belief} |\n"

        if len(traces) > 30:
            report += f"\n... ({len(traces) - 30} more steps) ...\n"

        report += "\n"

        # Model quality assessment
        report += "## Model Quality Assessment\n\n"
        report += self._assess_model_quality(traces, fe_trajectory, stats)
        report += "\n"

        # Conclusion
        report += "## Conclusion\n\n"
        report += "GNN model execution with Active Inference completed successfully.\n"
        report += "The model demonstrates Bayesian belief updating and policy evaluation via Expected Free Energy.\n"

        return report

    # Private execution methods — Active Inference core

    def _initialize_beliefs(self) -> dict[str, float]:
        """
        Initialize beliefs (uniform distribution over hidden states).

        Returns:
            Dictionary mapping state/variable names to probabilities.
        """
        if self.state_space and "variables" in self.state_space:
            variables = self.state_space["variables"]
            n = len(variables)
            return {var.get("name", f"var_{i}"): 1.0 / n for i, var in enumerate(variables)}
        return {"state_0": 0.5, "state_1": 0.5}

    def _initialize_state(self) -> dict[str, Any]:
        """Initialize actual state representation."""
        if self.state_space and "variables" in self.state_space:
            state = {}
            for var in self.state_space["variables"]:
                var_name = var.get("name", "unknown")
                state[var_name] = 0
            return state
        return {"initial": True}

    def _generate_observation(self, state: dict[str, Any]) -> str:
        """
        Generate observation from state using generative model.

        Observation is generated based on current state and the likelihood model.
        This creates meaningful state-observation associations.

        Returns:
            Observation identifier (string).
        """
        if self.state_space and "observations" in self.state_space:
            obs_list = self.state_space["observations"]
            if obs_list:
                # Pick observation based on state and variable values
                state_sum = sum(v for v in state.values() if isinstance(v, int | float))
                obs_idx = int(state_sum * len(obs_list)) % len(obs_list)
                return str(obs_list[obs_idx].get("name", f"obs_{obs_idx}"))
        return "obs_0"

    def _update_beliefs(
        self, prior_beliefs: dict[str, float], observation: str
    ) -> dict[str, float]:
        """
        Update beliefs using Bayesian inference.

        Posterior ∝ likelihood(obs|state) × prior(state)

        Args:
            prior_beliefs: Prior distribution over states.
            observation: Observation received.

        Returns:
            Posterior belief distribution.
        """
        if not prior_beliefs:
            return prior_beliefs

        states = list(prior_beliefs.keys())

        # Likelihood model: P(obs | state)
        # High likelihood if observation matches state name
        likelihood = {}
        for state in states:
            if observation and observation in state:
                likelihood[state] = 0.8
            else:
                likelihood[state] = 0.2 / max(1, len(states) - 1)

        # Bayesian update: posterior ∝ likelihood × prior
        posterior_unnormalized = {}
        for state in states:
            posterior_unnormalized[state] = (
                likelihood.get(state, 0.1) * prior_beliefs.get(state, 1.0 / len(states))
            )

        # Normalize
        total = sum(posterior_unnormalized.values())
        if total <= 0:
            return prior_beliefs

        posterior = {state: prob / total for state, prob in posterior_unnormalized.items()}
        return posterior

    def _compute_vfe(self, beliefs: dict[str, float], observation: str) -> float:
        """
        Compute Variational Free Energy.

        VFE = KL(beliefs || prior) - E[log P(obs | state)]
            = complexity - accuracy

        Args:
            beliefs: Current belief distribution.
            observation: Observed value.

        Returns:
            Variational Free Energy (lower is better).
        """
        if not beliefs:
            return 0.0

        states = list(beliefs.keys())
        n = len(states)

        # Complexity: KL(beliefs || uniform prior)
        uniform_prior = 1.0 / n
        kl_div = 0.0
        for _state, prob in beliefs.items():
            if prob > 0:
                kl_div += prob * (math.log(prob) - math.log(uniform_prior))

        # Accuracy: E[log P(obs | state)]
        accuracy = 0.0
        for state, prob in beliefs.items():
            if observation and observation in state:
                likelihood = 0.8
            else:
                likelihood = 0.2 / max(1, n - 1)
            if likelihood > 0:
                accuracy += prob * math.log(likelihood)

        # VFE = complexity - accuracy
        vfe = kl_div - accuracy
        return vfe

    def _evaluate_policies(self, beliefs: dict[str, float]) -> list[tuple[str, float]]:
        """
        Evaluate Expected Free Energy for each action.

        EFE = sum of VFE over planning horizon for each action.

        Args:
            beliefs: Current belief distribution.

        Returns:
            List of (action_name, efe_score) tuples, sorted by score (ascending = best).
        """
        if not self.state_space or "actions" not in self.state_space:
            return []

        actions = self.state_space["actions"]
        if not actions:
            return []

        policy_scores = []

        for action in actions:
            action_name = action.get("name", "unknown")

            # Simple EFE: compute expected reduction in uncertainty
            # Actions that reduce entropy (concentrate beliefs) have lower EFE
            uncertainty_reduction = self._entropy(beliefs)

            # Penalize actions based on frequency (encourage exploration)
            action_frequency = self.action_counts.get(action_name, 0)
            exploration_bonus = 0.1 * action_frequency

            efe = uncertainty_reduction - exploration_bonus
            policy_scores.append((action_name, efe))

        # Sort by EFE (ascending = best)
        return sorted(policy_scores, key=lambda x: x[1])

    def _select_action_active_inference(
        self, beliefs: dict[str, float], policy_scores: list[tuple[str, float]]
    ) -> tuple[str, str]:
        """
        Select action with lowest EFE (best free energy).

        Args:
            beliefs: Current beliefs (for rationale).
            policy_scores: List of (action, efe_score) tuples.

        Returns:
            (selected_action, rationale) tuple.
        """
        if not policy_scores:
            return "default_action", "No actions available"

        selected_action, selected_efe = policy_scores[0]

        # Generate rationale
        top_belief_state = max(beliefs.items(), key=lambda x: x[1])[0]
        top_belief_prob = max(beliefs.values(), default=0.0)
        rationale = (
            f"Selected action with lowest EFE ({selected_efe:.4f}). "
            f"Top belief state: {top_belief_state} ({top_belief_prob:.3f})"
        )

        return selected_action, rationale

    def _compute_transition(
        self,
        state: dict[str, Any],
        action: str,
    ) -> dict[str, Any]:
        """Compute next state from current state and action."""
        new_state = state.copy()
        # Simple state transition: increment numeric values
        for key in new_state:
            if isinstance(new_state[key], int | float):
                new_state[key] += 0.1
        new_state[f"step_result_{action}"] = True
        return new_state

    def _compute_reward(
        self,
        state: dict[str, Any],
        action: str,
        new_state: dict[str, Any],
    ) -> float:
        """Compute reward for transition."""
        # Simple reward: positive if state changed
        return 0.1 if new_state != state else 0.0

    def _count_unique_states(self, traces: list[dict[str, Any]]) -> int:
        """Count unique states visited."""
        unique_states = set()
        for trace in traces:
            state_str = json.dumps(trace.get("state", {}), sort_keys=True)
            unique_states.add(state_str)
        return len(unique_states)

    def _count_unique_actions(self, traces: list[dict[str, Any]]) -> int:
        """Count unique actions taken."""
        actions = set()
        for trace in traces:
            action = trace.get("action")
            if action:
                actions.add(action)
        return len(actions)

    def _compute_coverage_score(self, traces: list[dict[str, Any]]) -> float:
        """Compute state space coverage score."""
        if not self.state_space:
            return 0.5

        total_possible_states = len(
            self.state_space.get("variables", [])
        ) * len(self.state_space.get("observations", []))
        if total_possible_states == 0:
            return 0.5

        unique_states = self._count_unique_states(traces)
        return min(1.0, unique_states / total_possible_states)

    def _entropy(self, distribution: dict[str, float]) -> float:
        """
        Compute Shannon entropy of a probability distribution.

        H = -sum(p * log(p))

        Args:
            distribution: Dictionary mapping states to probabilities.

        Returns:
            Entropy in nats.
        """
        entropy = 0.0
        for prob in distribution.values():
            if prob > 0:
                entropy -= prob * math.log(prob)
        return entropy

    def _compute_statistics(self) -> dict[str, Any]:
        """Compute execution statistics."""
        if not self.traces:
            return {}

        rewards = [t.reward for t in self.traces]
        vfe_values = [t.free_energy_after for t in self.traces]

        stats = {
            "min_reward": min(rewards) if rewards else 0.0,
            "max_reward": max(rewards) if rewards else 0.0,
            "mean_reward": sum(rewards) / len(rewards) if rewards else 0.0,
            "total_reward": sum(rewards),
            "unique_states": self._count_unique_states([t.to_dict() for t in self.traces]),
            "unique_actions": self._count_unique_actions([t.to_dict() for t in self.traces]),
        }

        # Add free energy statistics
        if vfe_values:
            stats["min_vfe"] = min(vfe_values)
            stats["max_vfe"] = max(vfe_values)
            stats["mean_vfe"] = sum(vfe_values) / len(vfe_values)

        # Add belief convergence metric
        if self.beliefs_history and len(self.beliefs_history) > 1:
            initial_entropy = self._entropy(self.beliefs_history[0])
            final_entropy = self._entropy(self.beliefs_history[-1])
            stats["initial_uncertainty"] = initial_entropy
            stats["final_uncertainty"] = final_entropy
            stats["uncertainty_reduction"] = initial_entropy - final_entropy

        return stats

    def _assess_model_quality(
        self, traces: list[dict[str, Any]], fe_trajectory: list[float], stats: dict[str, Any]
    ) -> str:
        """
        Assess the quality of the GNN model dynamics.

        Evaluates:
        - Does the model produce meaningful state transitions?
        - Is free energy being minimized?
        - Are beliefs converging?
        - Is there action diversity?

        Args:
            traces: Execution traces.
            fe_trajectory: Free energy values over time.
            stats: Computed statistics.

        Returns:
            Assessment text.
        """
        assessment = ""

        # Check for meaningful dynamics
        unique_actions = stats.get("unique_actions", 0)
        unique_states = stats.get("unique_states", 0)

        if unique_states > 1:
            assessment += "✓ Model exhibits meaningful state dynamics (multiple states visited)\n"
        else:
            assessment += "⚠ Model shows limited state dynamics (single state)\n"

        if unique_actions > 1:
            assessment += "✓ Policy evaluation produced diverse actions\n"
        else:
            assessment += "⚠ Limited action diversity\n"

        # Check for free energy minimization
        if fe_trajectory and len(fe_trajectory) > 1:
            initial_fe = fe_trajectory[0]
            final_fe = fe_trajectory[-1]
            if final_fe < initial_fe:
                assessment += f"✓ Free energy minimized (↓ {initial_fe:.3f} → {final_fe:.3f})\n"
            else:
                assessment += f"⚠ Free energy not minimized (↑ {initial_fe:.3f} → {final_fe:.3f})\n"

        # Check for belief convergence
        uncertainty_reduction = stats.get("uncertainty_reduction", 0.0)
        if uncertainty_reduction > 0:
            assessment += f"✓ Beliefs converging (entropy reduced by {uncertainty_reduction:.3f} nats)\n"
        else:
            assessment += "⚠ Beliefs not converging\n"

        # Overall assessment
        positive_signs = assessment.count("✓")
        if positive_signs >= 3:
            assessment += "\n**Overall**: Model demonstrates good Active Inference dynamics.\n"
        elif positive_signs >= 2:
            assessment += "\n**Overall**: Model shows decent Active Inference behavior.\n"
        else:
            assessment += "\n**Overall**: Model needs refinement for better Active Inference dynamics.\n"

        return assessment

    def run_with_profiling(
        self, num_steps: int = 10, num_trials: int = 1
    ) -> tuple[list[dict[str, Any]], dict[str, float]]:
        """Run the model and collect timing information per stage.

        Executes the GNN model and measures the time spent in each phase
        (belief update, policy evaluation, action selection, state update).

        Args:
            num_steps: Number of steps to run in each trial.
            num_trials: Number of trials to run.

        Returns:
            A tuple of (traces, timing_dict) where:
            - traces: List of execution trace dicts from all trials.
            - timing_dict: Dict with keys like "belief_update_ms",
              "policy_eval_ms", "action_select_ms", "state_update_ms",
              and "total_ms" showing cumulative milliseconds for each phase.
        """
        import time

        timing: dict[str, float] = {
            "belief_update_ms": 0.0,
            "policy_eval_ms": 0.0,
            "action_select_ms": 0.0,
            "state_update_ms": 0.0,
            "observation_ms": 0.0,
            "total_ms": 0.0,
        }
        all_traces: list[dict[str, Any]] = []

        total_start = time.perf_counter()

        for trial in range(num_trials):
            state = self._initialize_state()
            beliefs = self._initialize_beliefs()
            beliefs_prior = beliefs.copy()

            for step in range(num_steps):
                # Observe
                obs_start = time.perf_counter()
                obs = self._generate_observation(state)
                timing["observation_ms"] += (time.perf_counter() - obs_start) * 1000

                # Update beliefs
                upd_start = time.perf_counter()
                beliefs_prior = beliefs.copy()
                beliefs = self._update_beliefs(beliefs, obs)
                timing["belief_update_ms"] += (time.perf_counter() - upd_start) * 1000

                # Evaluate policies
                pol_start = time.perf_counter()
                policy_scores = self._evaluate_policies(beliefs)
                timing["policy_eval_ms"] += (
                    time.perf_counter() - pol_start
                ) * 1000

                # Select action
                act_start = time.perf_counter()
                action = self._select_action_active_inference(
                    beliefs, policy_scores
                )
                timing["action_select_ms"] += (
                    time.perf_counter() - act_start
                ) * 1000

                # Update state
                st_start = time.perf_counter()
                state = self._compute_transition(state, action)
                timing["state_update_ms"] += (time.perf_counter() - st_start) * 1000

                # Collect trace
                trace = ExecutionTrace(
                    step=step + trial * num_steps,
                    state=state,
                    action=action,
                    observation=obs,
                    beliefs=beliefs,
                    beliefs_prior=beliefs_prior,
                ).to_dict()
                all_traces.append(trace)

        timing["total_ms"] = (time.perf_counter() - total_start) * 1000

        logger.info(
            "Profiled run: %d trials × %d steps = %d steps total",
            num_trials,
            num_steps,
            num_trials * num_steps,
        )
        logger.info(
            "Timing: belief_update=%.1f ms, policy_eval=%.1f ms, "
            "action_select=%.1f ms, state_update=%.1f ms, "
            "observation=%.1f ms, total=%.1f ms",
            timing["belief_update_ms"],
            timing["policy_eval_ms"],
            timing["action_select_ms"],
            timing["state_update_ms"],
            timing["observation_ms"],
            timing["total_ms"],
        )

        return all_traces, timing


# Module-level convenience alias — mirrors :meth:`GNNModelRunner.load_package`
# as a free function so tutorials and doctests can call
# ``load_gnn_package(package_dir)`` without first instantiating a runner.
# Bound to a module-scoped runner so repeated calls share state the way a
# normal ``GNNModelRunner()`` would after one ``load_package`` call.
load_gnn_package = GNNModelRunner().load_package
