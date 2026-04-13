"""Translation rules package — family-organised rule modules.

This package exposes every concrete :class:`TranslationRule`
implementation shipped with COGANT. Rules are organised into
five families, each in its own module:

  - :mod:`cogant.translate.rules.structural` — read/write, containment, inheritance, pipelines
  - :mod:`cogant.translate.rules.behavioral` — orchestration, event bus, test assertions
  - :mod:`cogant.translate.rules.control`    — configuration, feature flags
  - :mod:`cogant.translate.rules.semantic`   — observation/action/policy/preference/context
  - :mod:`cogant.translate.rules.resilience` — retry, error boundary, singleton, circuit breaker

The umbrella package re-exports every rule class, so
``from cogant.translate.rules import ReadOnlyInputRule`` and
``from cogant.translate.rules import *`` both continue to work
exactly as they did when this was a single flat file.
"""

from cogant.translate.engine import TranslationRule
from cogant.translate.rules.behavioral import (
    EventBusRule,
    OrchestratorRule,
    StateMachineRule,
    TestAssertionRule,
)
from cogant.translate.rules.control import ConfigRule, FeatureFlagRule, ParameterRule
from cogant.translate.rules.resilience import (
    CircuitBreakerRule,
    ErrorBoundaryRule,
    RateLimiterRule,
    RetryPatternRule,
    SingletonAccessRule,
)
from cogant.translate.rules.semantic import (
    ActionRule,
    ContextRule,
    ObservationRule,
    PolicyRule,
    PreferenceRule,
)
from cogant.translate.rules.structural import (
    ContainmentRule,
    DataPipelineRule,
    InheritanceRule,
    MutatingSubsystemRule,
    ReadOnlyInputRule,
)

__all__ = [
    "TranslationRule",
    "ContainmentRule",
    "DataPipelineRule",
    "InheritanceRule",
    "MutatingSubsystemRule",
    "ReadOnlyInputRule",
    "EventBusRule",
    "OrchestratorRule",
    "StateMachineRule",
    "TestAssertionRule",
    "ConfigRule",
    "FeatureFlagRule",
    "ParameterRule",
    "ActionRule",
    "ContextRule",
    "ObservationRule",
    "PolicyRule",
    "PreferenceRule",
    "CircuitBreakerRule",
    "ErrorBoundaryRule",
    "RateLimiterRule",
    "RetryPatternRule",
    "SingletonAccessRule",
]
