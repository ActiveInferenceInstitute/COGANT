"""Public metrics API for COGANT.

Loads and exposes values from cogant/evaluation/METRICS.yaml,
providing a stable programmatic interface for scripts, tests, and
manuscript injection tooling.

Usage::

    from cogant.metrics import version, coverage, role_preserved_count

    print(version())               # "0.6.0"
    print(coverage())              # 90.0
    print(role_preserved_count())  # role-preserved roundtrip targets
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml  # pyyaml — already a dev dep

__all__ = [
    "load",
    "version",
    "test_count",
    "coverage",
    "mypy_errors",
    "role_preserved_count",
    "strict_isomorphism_count",
    "total_targets",
    "mean_role_preservation_score",
    "role_preservation_score_for",
    "bibliography_entries",
]

_METRICS_PATH = Path(__file__).parent.parent.parent / "evaluation" / "METRICS.yaml"


@functools.lru_cache(maxsize=1)
def load() -> dict[str, Any]:
    """Load and return the full METRICS.yaml as a dict."""
    with open(_METRICS_PATH) as f:
        result: dict[str, Any] = yaml.safe_load(f)
        return result


def _get(path: str, default: Any = None) -> Any:
    """Dot-path getter: 'testing.coverage_percent' -> float."""
    data = load()
    parts = path.split(".")
    for part in parts:
        if not isinstance(data, dict):
            return default
        data = data.get(part, default)
        if data is None:
            return default
    return data


def version() -> str:
    """Return the cogant package version string."""
    return str(_get("package.version", "unknown"))


def test_count() -> int:
    """Return the number of passing tests."""
    return int(_get("testing.test_count_passing", 0))


def coverage() -> float:
    """Return code coverage percentage."""
    return float(_get("testing.coverage_percent", 0.0))


def mypy_errors() -> int:
    """Return the number of mypy --strict errors."""
    return int(_get("testing.mypy_strict_errors", 0))


def role_preserved_count() -> int:
    """Return the number of roundtrip targets that preserve GNN roles."""
    return int(_get("evaluation.roundtrip.role_preserved_count", 0))


def strict_isomorphism_count() -> int:
    """Return the number of strict structurally isomorphic roundtrip targets."""
    return int(_get("evaluation.roundtrip.strict_isomorphism_count", 0))


def total_targets() -> int:
    """Return the total number of roundtrip evaluation targets."""
    return int(_get("evaluation.roundtrip.total_targets", 0))


def mean_role_preservation_score() -> float:
    """Return the mean role-preservation score across roundtrip targets."""
    return float(_get("evaluation.roundtrip.mean_role_preservation_score", 0.0))


def role_preservation_score_for(name: str) -> float | None:
    """Return the role-preservation score for a specific roundtrip target."""
    targets = _get("evaluation.roundtrip.per_target", [])
    for target in targets:
        if isinstance(target, dict) and target.get("name") == name:
            value = target.get("role_preservation_score")
            return float(value) if value is not None else None
    return None


def bibliography_entries() -> int:
    """Return the number of bibliography entries in LITERATURE.md."""
    return int(_get("literature.bibliography_entries", 0))
