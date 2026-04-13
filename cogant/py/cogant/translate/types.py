"""Translation engine type definitions for COGANT.

This module defines types specific to the translation pipeline,
including semantic roles, rule families, fixpoint status, and tiers.
"""

from __future__ import annotations

from typing import Literal

__all__ = [
    "SemanticRole",
    "RuleFamily",
    "FixpointStatus",
    "TranslationTier",
]


# ============================================================================
# Semantic Role Literal Type
# ============================================================================

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
"""Semantic role assigned to a program element by translation rules.

The 11 core semantic role types used in active inference modeling:

- HIDDEN_STATE: Internal belief variable (not directly observable).
- OBSERVATION: Observable variable (sensory input to the agent).
- ACTION: Controllable variable (motor output from the agent).
- POLICY: Mapping from beliefs to actions (decision logic).
- PREFERENCE: Desirability or valence over observations.
- CONTEXT: Configuration or environmental parameter.
- PARAMETER: Tunable value (hyperparameter, magic number, constant).
- CONSTRAINT: Boundary condition or validity check.
- DATA_FLOW: Information flow (reads/writes of data).
- ERROR_HANDLING: Exception handling, recovery, or fault tolerance.
- ORCHESTRATION: Coordination or composition of other elements.
"""


# ============================================================================
# Rule Family Literal Type
# ============================================================================

RuleFamily = Literal[
    "structural",
    "semantic",
    "control",
    "behavioral",
    "resilience",
]
"""Category of translation rules.

Rules are organized into five families based on the aspect of the
program they analyze:

- structural: Rules based on code structure (class, function, module).
- semantic: Rules based on semantic patterns (names, types, annotations).
- control: Rules based on control flow (loops, conditionals, exceptions).
- behavioral: Rules based on behavior (calls, state changes, I/O).
- resilience: Rules based on error handling and fault tolerance.
"""


# ============================================================================
# Fixpoint Status Literal Type
# ============================================================================

FixpointStatus = Literal[
    "converged",
    "max_iterations_exceeded",
    "empty_graph",
]
"""Outcome of the fixpoint iteration in the translation engine.

- converged: Fixpoint reached; no more rules fire.
- max_iterations_exceeded: Maximum iteration limit hit before fixpoint.
- empty_graph: Graph had no nodes to translate.
"""


# ============================================================================
# Translation Tier Literal Type
# ============================================================================

TranslationTier = Literal[
    "core",
    "supplementary",
    "degraded",
]
"""Confidence tier for semantic mappings.

Indicates the quality and source of evidence supporting a mapping:

- core: High confidence from strong static or dynamic evidence.
- supplementary: Moderate confidence from additional evidence sources.
- degraded: Lower confidence or fallback behavior (identity-biased,
  identity matrices, uniform distributions, etc.).
"""
