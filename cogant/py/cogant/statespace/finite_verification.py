from collections.abc import Iterator

from cogant.statespace.finite_model import FiniteModel, specification_digest
from cogant.statespace.finite_spec import FiniteModelSpec, FiniteRecord


class FiniteVerification(FiniteRecord):
    passed: bool
    checked_entries: int
    mismatch_count: int
    counterexamples: tuple[str, ...]


def _matrix_comparisons(
    spec: FiniteModelSpec, model: FiniteModel
) -> Iterator[tuple[str, float, float]]:
    transitions = {(r.state, r.action, r.next_state): r.probability for r in spec.transitions}
    likelihoods = {(r.state, r.observation): r.probability for r in spec.likelihoods}
    preferences = {r.observation: r.log_preference for r in spec.preferences}
    prior = {r.state: r.probability for r in spec.prior}
    for state_index, state in enumerate(spec.states):
        for next_index, next_state in enumerate(spec.states):
            for action_index, action in enumerate(spec.actions):
                yield (
                    f"B[{next_index}][{state_index}][{action_index}]",
                    transitions.get((state, action, next_state), 0.0),
                    model.B[next_index][state_index][action_index],
                )
        for obs_index, observation in enumerate(spec.observations):
            yield (
                f"A[{obs_index}][{state_index}]",
                likelihoods.get((state, observation), 0.0),
                model.A[obs_index][state_index],
            )
        yield f"D[{state_index}]", prior.get(state, 0.0), model.D[state_index]
    for obs_index, observation in enumerate(spec.observations):
        yield f"C[{obs_index}]", preferences.get(observation, 0.0), model.C[obs_index]


def verify_finite_model(spec: FiniteModelSpec, model: FiniteModel) -> FiniteVerification:
    """Compare every matrix entry against sparse declarations, including implied zeros."""
    differences: list[str] = []
    for axis, expected, actual in (
        ("states", spec.states, model.states),
        ("actions", spec.actions, model.actions),
        ("observations", spec.observations, model.observations),
    ):
        if expected != actual:
            differences.append(f"{axis}: expected {expected}, got {actual}")
    if specification_digest(spec) != model.source_sha256:
        differences.append("source_sha256 does not match the normalized specification")
    if spec.name != model.name:
        differences.append("name does not match the specification")
    if differences:
        return FiniteVerification(
            passed=False,
            checked_entries=0,
            mismatch_count=len(differences),
            counterexamples=tuple(differences),
        )
    checked = 0
    mismatches = 0
    for coordinate, expected_mass, actual_mass in _matrix_comparisons(spec, model):
        checked += 1
        if expected_mass != actual_mass:
            mismatches += 1
            if len(differences) < 32:
                differences.append(f"{coordinate}: expected {expected_mass}, got {actual_mass}")
    return FiniteVerification(
        passed=mismatches == 0,
        checked_entries=checked,
        mismatch_count=mismatches,
        counterexamples=tuple(differences),
    )
