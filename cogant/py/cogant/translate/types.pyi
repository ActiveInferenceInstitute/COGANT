from typing import Literal

__all__ = ["SemanticRole", "RuleFamily", "FixpointStatus", "TranslationTier"]

SemanticRole = Literal[
    "HIDDEN_STATE",
    "OBSERVATION",
    "ACTION",
    "POLICY",
    "PREFERENCE",
    "CONTEXT",
    "PARAMETER",
    "CONSTRAINT",
    "DATA_FLOW",
    "ERROR_HANDLING",
    "ORCHESTRATION",
]
RuleFamily = Literal["structural", "semantic", "control", "behavioral", "resilience"]
FixpointStatus = Literal["converged", "max_iterations_exceeded", "empty_graph"]
TranslationTier = Literal["core", "supplementary", "degraded"]
