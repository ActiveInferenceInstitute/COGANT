from collections import defaultdict
from collections.abc import Iterable, Mapping
from math import fsum, isclose
from typing import Annotated, Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Label = Annotated[str, Field(strict=True, min_length=1)]
Probability = Annotated[float, Field(strict=True, ge=0, le=1, allow_inf_nan=False)]
FiniteNumber = Annotated[float, Field(strict=True, allow_inf_nan=False)]
MASS_TOLERANCE: Final = 1e-12


class FiniteModelError(ValueError):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class FiniteRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class StateTransition(FiniteRecord):
    state: Label
    action: Label
    next_state: Label
    probability: Probability = 1.0


class StateObservation(FiniteRecord):
    state: Label
    observation: Label
    probability: Probability = 1.0


class StatePrior(FiniteRecord):
    state: Label
    probability: Probability


class ObservationPreference(FiniteRecord):
    observation: Label
    log_preference: FiniteNumber


def unique_labels(name: str, labels: tuple[str, ...]) -> None:
    if len(set(labels)) != len(labels):
        raise FiniteModelError(f"{name} contains duplicate labels")


def unit_mass(values: Iterable[float], context: str) -> None:
    if not isclose(fsum(values), 1.0, rel_tol=0.0, abs_tol=MASS_TOLERANCE):
        raise FiniteModelError(f"{context} must sum to one")


def _complete_kernel(
    groups: Mapping[tuple[str, ...], list[float]],
    expected_count: int,
    name: str,
) -> None:
    if len(groups) != expected_count:
        raise FiniteModelError(
            f"{name} covers {len(groups)} input cases; expected {expected_count}"
        )
    for key, masses in groups.items():
        unit_mass(masses, f"{name}{key}")


class FiniteModelSpec(FiniteRecord):
    """Declared Markov model; omitted outcomes have zero mass and preferences default to zero."""

    schema_version: Literal["1.0"] = "1.0"
    name: Label
    states: tuple[Label, ...] = Field(min_length=1)
    actions: tuple[Label, ...] = Field(min_length=1)
    observations: tuple[Label, ...] = Field(min_length=1)
    transitions: tuple[StateTransition, ...]
    likelihoods: tuple[StateObservation, ...]
    prior: tuple[StatePrior, ...]
    preferences: tuple[ObservationPreference, ...] = ()

    @model_validator(mode="after")
    def validate_kernels(self) -> Self:
        for name, labels in (
            ("states", self.states),
            ("actions", self.actions),
            ("observations", self.observations),
        ):
            unique_labels(name, labels)
        states, actions, observations = set(self.states), set(self.actions), set(self.observations)
        transition_groups: dict[tuple[str, ...], list[float]] = defaultdict(list)
        transition_keys: set[tuple[str, str, str]] = set()
        for row in self.transitions:
            key = (row.state, row.action, row.next_state)
            if row.state not in states or row.next_state not in states or row.action not in actions:
                raise FiniteModelError(f"Undeclared transition reference: {key}")
            if key in transition_keys:
                raise FiniteModelError(f"Duplicate transition: {key}")
            transition_keys.add(key)
            transition_groups[row.state, row.action].append(row.probability)
        _complete_kernel(transition_groups, len(self.states) * len(self.actions), "transitions")
        observation_groups: dict[tuple[str, ...], list[float]] = defaultdict(list)
        observation_keys: set[tuple[str, str]] = set()
        for likelihood in self.likelihoods:
            pair = (likelihood.state, likelihood.observation)
            if likelihood.state not in states or likelihood.observation not in observations:
                raise FiniteModelError(f"Undeclared likelihood reference: {pair}")
            if pair in observation_keys:
                raise FiniteModelError(f"Duplicate likelihood: {pair}")
            observation_keys.add(pair)
            observation_groups[(likelihood.state,)].append(likelihood.probability)
        _complete_kernel(observation_groups, len(self.states), "likelihoods")
        prior_states: set[str] = set()
        for mass in self.prior:
            if mass.state not in states or mass.state in prior_states:
                raise FiniteModelError(f"Undeclared or duplicate prior state: {mass.state}")
            prior_states.add(mass.state)
        unit_mass((mass.probability for mass in self.prior), "prior")
        preference_labels: set[str] = set()
        for preference in self.preferences:
            if (
                preference.observation not in observations
                or preference.observation in preference_labels
            ):
                raise FiniteModelError(
                    f"Undeclared or duplicate preference: {preference.observation}"
                )
            preference_labels.add(preference.observation)
        return self
