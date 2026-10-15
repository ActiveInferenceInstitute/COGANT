from __future__ import annotations

import hashlib
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cogant.runtime.categorical import CategoricalModel, distribution

Probability = Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]
Finite = Annotated[float, Field(allow_inf_nan=False)]
Index = Annotated[int, Field(strict=True, ge=0)]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class InferenceOptions(BaseModel):
    """Admission limits and optional externally supplied observation sequence."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    steps: Annotated[int, Field(ge=1, le=10_000)] = 8
    observations: tuple[Index, ...] | None = None
    max_work_units: Annotated[int, Field(gt=0)] = 100_000_000

    @model_validator(mode="after")
    def observation_count(self) -> Self:
        if self.observations is not None and len(self.observations) != self.steps:
            raise ValueError("observation count must equal the requested steps")
        return self


class MatrixSnapshot(BaseModel):
    """Immutable, admitted A[o,s], B[next,current,action], C[o], D[s]."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    A: tuple[tuple[Probability, ...], ...]
    B: tuple[tuple[tuple[Probability, ...], ...], ...]
    C: tuple[Finite, ...]
    D: tuple[Probability, ...]

    @model_validator(mode="after")
    def categorical_model(self) -> Self:
        CategoricalModel(self.A, self.B, self.C, self.D)
        return self

    def digest(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode("utf-8")).hexdigest()


class InferenceRecord(BaseModel):
    """One observation: incoming prior, filtered posterior, then control prediction."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    t: Index
    prior: tuple[Probability, ...]
    posterior: tuple[Probability, ...]
    predicted_belief: tuple[Probability, ...]
    predicted_observation: tuple[Probability, ...]
    observation: Index
    action: Index
    policy_scores: tuple[Finite, ...]
    free_energy: Finite


class AxisLabels(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    states: tuple[str, ...]
    observations: tuple[str, ...]
    actions: tuple[str, ...]


class InferenceTrace(BaseModel):
    """Versioned execution artifact bound to exact GNN text and parsed matrices."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    schema_version: Literal["2.0"] = "2.0"
    source_sha256: Digest
    matrices_sha256: Digest
    source_artifact: str | None = None
    model_name: str
    mode: Literal["model_rollout", "observations"]
    policy_horizon: Literal[1] = 1
    policy_objective: Literal["risk_plus_ambiguity"] = "risk_plus_ambiguity"
    labels: AxisLabels
    matrices: MatrixSnapshot
    trace: Annotated[tuple[InferenceRecord, ...], Field(min_length=1, max_length=10_000)]

    @model_validator(mode="after")
    def execution_axes(self) -> Self:
        if self.matrices.digest() != self.matrices_sha256:
            raise ValueError("matrix snapshot digest does not match the trace identity")
        ns, no = len(self.matrices.D), len(self.matrices.A)
        na = len(self.matrices.B[0][0])
        if tuple(map(len, (self.labels.states, self.labels.observations, self.labels.actions))) != (
            ns,
            no,
            na,
        ):
            raise ValueError("trace labels do not match the matrix axes")
        if not self.trace:
            raise ValueError("an inference trace must contain at least one observation")
        prior = self.matrices.D
        for t, record in enumerate(self.trace):
            if record.t != t or record.prior != prior:
                raise ValueError("trace timing or incoming prior is inconsistent")
            for vector in (record.prior, record.posterior, record.predicted_belief):
                if len(vector) != ns:
                    raise ValueError("trace belief has incompatible state dimensions")
                distribution(vector, "trace belief")
            if len(record.predicted_observation) != no or record.observation >= no:
                raise ValueError("trace observation has incompatible dimensions")
            distribution(record.predicted_observation, "predicted observation")
            if len(record.policy_scores) != na or record.action >= na:
                raise ValueError("trace policy has incompatible action dimensions")
            prior = record.predicted_belief
        return self
