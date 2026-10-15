from hashlib import sha256
from typing import Annotated, Final, Literal, Self

from pydantic import Field, TypeAdapter, model_validator

from cogant.runtime.loop import AgentRuntime
from cogant.statespace.finite_spec import (
    FiniteModelError,
    FiniteModelSpec,
    FiniteNumber,
    FiniteRecord,
    Label,
    Probability,
    unique_labels,
    unit_mass,
)

MAX_DENSE_ENTRIES: Final = 1_000_000
_ENTRY_LIMIT = TypeAdapter(Annotated[int, Field(strict=True, gt=0)])


def specification_digest(spec: FiniteModelSpec) -> str:
    return sha256(spec.model_dump_json().encode("utf-8")).hexdigest()


class FiniteModel(FiniteRecord):
    """Immutable matrices with `A[o][s]`, `B[next][current][action]`, `C[o]`, and `D[s]` axes."""

    schema_version: Literal["1.0"] = "1.0"
    semantics: Literal["declared_finite_model"] = "declared_finite_model"
    name: Label
    states: tuple[Label, ...] = Field(min_length=1)
    actions: tuple[Label, ...] = Field(min_length=1)
    observations: tuple[Label, ...] = Field(min_length=1)
    A: tuple[tuple[Probability, ...], ...]
    B: tuple[tuple[tuple[Probability, ...], ...], ...]
    C: tuple[FiniteNumber, ...]
    D: tuple[Probability, ...]
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_axes(self) -> Self:
        ns, na, no = len(self.states), len(self.actions), len(self.observations)
        for name, labels in (
            ("states", self.states),
            ("actions", self.actions),
            ("observations", self.observations),
        ):
            unique_labels(name, labels)
        if len(self.A) != no or any(len(row) != ns for row in self.A):
            raise FiniteModelError("A shape must be [observations][states]")
        if len(self.B) != ns or any(
            len(row) != ns or any(len(cell) != na for cell in row) for row in self.B
        ):
            raise FiniteModelError("B shape must be [next state][current state][action]")
        if len(self.C) != no or len(self.D) != ns:
            raise FiniteModelError("C and D must match their observation and state axes")
        for state in range(ns):
            unit_mass((row[state] for row in self.A), f"A column {state}")
            for action in range(na):
                unit_mass((row[state][action] for row in self.B), f"B column {(state, action)}")
        unit_mass(self.D, "D")
        return self

    def to_runtime(self) -> AgentRuntime:
        """Create a runtime with mutable copies, preserving the compiled artifact."""
        return AgentRuntime.from_matrices_dict(
            {
                "A": [list(row) for row in self.A],
                "B": [[list(cell) for cell in row] for row in self.B],
                "C": list(self.C),
                "D": list(self.D),
            }
        )


def compile_finite_model(
    spec: FiniteModelSpec, *, max_entries: int = MAX_DENSE_ENTRIES
) -> FiniteModel:
    """Lower a total finite specification without pruning, smoothing, or renormalizing its kernels."""
    limit = _ENTRY_LIMIT.validate_python(max_entries)
    ns, na, no = len(spec.states), len(spec.actions), len(spec.observations)
    entries = ns * ns * na + no * ns + no + ns
    if entries > limit:
        raise FiniteModelError(f"Model needs {entries} dense entries; allocation limit is {limit}")
    state_index = {name: i for i, name in enumerate(spec.states)}
    action_index = {name: i for i, name in enumerate(spec.actions)}
    observation_index = {name: i for i, name in enumerate(spec.observations)}
    A = [[0.0] * ns for _ in range(no)]
    B = [[[0.0] * na for _ in range(ns)] for _ in range(ns)]
    C = [0.0] * no
    D = [0.0] * ns
    for transition in spec.transitions:
        B[state_index[transition.next_state]][state_index[transition.state]][
            action_index[transition.action]
        ] = transition.probability
    for likelihood in spec.likelihoods:
        A[observation_index[likelihood.observation]][state_index[likelihood.state]] = (
            likelihood.probability
        )
    for preference in spec.preferences:
        C[observation_index[preference.observation]] = preference.log_preference
    for mass in spec.prior:
        D[state_index[mass.state]] = mass.probability
    return FiniteModel(
        name=spec.name,
        states=spec.states,
        actions=spec.actions,
        observations=spec.observations,
        A=tuple(tuple(row) for row in A),
        B=tuple(tuple(tuple(cell) for cell in row) for row in B),
        C=tuple(C),
        D=tuple(D),
        source_sha256=specification_digest(spec),
    )
