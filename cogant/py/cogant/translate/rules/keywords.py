"""Shared keyword lists for the COGANT translation rule families.

All lexical heuristics used across the 22 translation rules are defined
here as module-level constants so that calibration sweeps and corpus
analyses can target a single file rather than hunting through five rule
modules.

Calibration reference: ``docs/evaluation/CALIBRATION.md``.
Corpus basis: PEP 8 naming conventions + 20-repo audit 2026-04-09.
"""

from __future__ import annotations

__all__ = [
    "OBSERVATION_KEYWORDS",
    "ACTION_KEYWORDS",
    "POLICY_KEYWORDS",
    "PREFERENCE_KEYWORDS",
    "CONTEXT_KEYWORDS",
    "CONFIG_KEYWORDS",
    "FEATURE_FLAG_KEYWORDS",
    "CIRCUIT_BREAKER_KEYWORDS",
    "RETRY_KEYWORDS",
    "SINGLETON_KEYWORDS",
    "PARAMETER_KEYWORDS",
    "STATE_MACHINE_KEYWORDS",
    "RATE_LIMITER_KEYWORDS",
]

# ---------------------------------------------------------------------------
# Semantic-role keywords  (ObservationRule, ActionRule, PolicyRule, …)
# ---------------------------------------------------------------------------

OBSERVATION_KEYWORDS: list[str] = [
    "get", "read", "fetch", "query", "display", "show", "status", "info", "list",
    "sensor_", "read_", "get_", "fetch_", "receive_", "sense_", "peek", "sample",
    "inspect", "view", "describe",
]
"""Functions/methods that signal an OBSERVATION semantic role.

Canonical accessor prefixes (PEP 8) + UI/introspection verbs.
Corpus gaps closed in wave-21: ``peek``, ``sample``, ``inspect``.
"""

ACTION_KEYWORDS: list[str] = [
    "set", "update", "create", "delete", "send", "push", "execute", "run",
    "process", "handle", "dispatch", "encode", "decode", "dump", "load",
    "act_", "send_", "write_", "execute_", "command_", "emit_", "commit",
    "rollback", "flush", "apply", "perform", "invoke",
]
"""Functions/methods that signal an ACTION semantic role.

CRUD + IO verbs; ``handle``/``dispatch`` straddle ACTION/POLICY intentionally
and are resolved by confidence tie-breaking in ``_resolve_conflicts``.
"""

POLICY_KEYWORDS: list[str] = [
    "route", "dispatch", "handle", "policy", "decide", "choose", "select",
    "route_", "policy_", "decide_", "plan", "strategy", "schedule",
]
"""Functions/methods that signal a POLICY semantic role."""

PREFERENCE_KEYWORDS: list[str] = [
    "prefer", "prefer_", "reward", "cost", "loss", "utility", "score", "rank",
    "objective", "target", "goal", "priority", "weight",
]
"""Functions/methods that signal a PREFERENCE semantic role."""

CONTEXT_KEYWORDS: list[str] = [
    "context", "ctx", "environ", "env", "session", "state", "store", "registry",
    "workspace", "namespace", "scope", "arena",
]
"""Variables/modules that signal a CONTEXT semantic role."""

# ---------------------------------------------------------------------------
# Control-family keywords  (ConfigRule, FeatureFlagRule, ParameterRule)
# ---------------------------------------------------------------------------

CONFIG_KEYWORDS: list[str] = [
    "config", "configuration", "cfg", "settings", "options", "params",
    "toml", "yaml", "ini", "env", "dotenv",
]
"""Names that signal a configuration artifact (ConfigRule)."""

FEATURE_FLAG_KEYWORDS: list[str] = [
    "flag", "feature", "toggle", "switch", "experiment", "ab_test",
    "enabled", "disabled", "rollout", "canary",
]
"""Names that signal a feature-flag artifact (FeatureFlagRule)."""

PARAMETER_KEYWORDS: list[str] = [
    "param", "parameter", "hyper", "hyperparameter", "threshold", "alpha",
    "beta", "gamma", "epsilon", "learning_rate", "temperature", "seed",
]
"""Names that signal a tunable parameter (ParameterRule, wave-21)."""

# ---------------------------------------------------------------------------
# Behavioral-family keywords  (StateMachineRule)
# ---------------------------------------------------------------------------

STATE_MACHINE_KEYWORDS: list[str] = [
    "state", "transition", "machine", "fsm", "automaton", "workflow",
    "status", "phase", "stage", "mode",
]
"""Names that signal a finite-state-machine pattern (StateMachineRule, wave-21)."""

# ---------------------------------------------------------------------------
# Resilience-family keywords  (CircuitBreakerRule, RetryPatternRule,
#                               SingletonAccessRule, RateLimiterRule)
# ---------------------------------------------------------------------------

CIRCUIT_BREAKER_KEYWORDS: list[str] = [
    "circuit", "breaker", "fallback", "bulkhead", "half_open", "open_state",
]
"""Names that signal a circuit-breaker pattern (CircuitBreakerRule)."""

RETRY_KEYWORDS: list[str] = [
    "retry", "backoff", "attempt", "max_retries", "jitter", "exponential",
]
"""Names that signal a retry pattern (RetryPatternRule)."""

SINGLETON_KEYWORDS: list[str] = [
    "singleton", "instance", "_instance", "get_instance", "shared", "global_",
]
"""Names that signal a singleton access pattern (SingletonAccessRule)."""

RATE_LIMITER_KEYWORDS: list[str] = [
    "rate", "limit", "throttle", "quota", "burst", "leaky_bucket",
    "token_bucket", "ratelimit", "ratelimiter",
]
"""Names that signal a rate-limiter pattern (RateLimiterRule, wave-21)."""
