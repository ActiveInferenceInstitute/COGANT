from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["ReverseGNNModel", "ReverseModelError", "parse_gnn"]

class ReverseModelError(ValueError):
    code: str

@dataclass
class ReverseGNNModel:
    model_name: str = ...
    raw_model_name: str = ...
    hidden_states: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    policies: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    annotations: dict[str, str] = field(default_factory=dict)
    cardinalities: dict[str, int] = field(default_factory=dict)
    types: dict[str, str] = field(default_factory=dict)
    A: list[list[float]] = field(default_factory=list)
    B: list[list[list[float]]] = field(default_factory=list)
    C: list[float] = field(default_factory=list)
    D: list[float] = field(default_factory=list)
    connections: list[str] = field(default_factory=list)
    human_names: dict[str, str] = field(default_factory=dict)
    degraded: bool = False
    diagnostics: list[str] = field(default_factory=list)
    @property
    def n_hidden_factors(self) -> int: ...
    @property
    def n_states(self) -> int: ...
    @property
    def n_obs(self) -> int: ...
    @property
    def n_actions(self) -> int: ...
    def validate(self) -> list[str]: ...

def parse_gnn(gnn: str | Path) -> ReverseGNNModel: ...
