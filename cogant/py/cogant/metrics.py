"""Public metrics API for COGANT.

Loads and exposes values from cogant/evaluation/METRICS.yaml,
providing a stable programmatic interface for scripts, tests, and
manuscript injection tooling.

Usage::

    from cogant.metrics import version, coverage, isomorphic_count

    print(version())          # "0.4.0"
    print(coverage())         # 83.42
    print(isomorphic_count()) # 14
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml  # pyyaml — already a dev dep

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


def isomorphic_count() -> int:
    """Return the number of ISOMORPHIC roundtrip targets."""
    return int(_get("evaluation.roundtrip.isomorphic_count", 0))


def total_targets() -> int:
    """Return the total number of roundtrip evaluation targets."""
    return int(_get("evaluation.roundtrip.total_targets", 0))


def mean_epsilon() -> float:
    """Return the mean epsilon across all roundtrip targets."""
    return float(_get("evaluation.roundtrip.mean_epsilon", 0.0))


def epsilon_for(name: str) -> float | None:
    """Return epsilon for a specific roundtrip target by name.

    Args:
        name: Repository/target name (e.g. "01_simple_state", "requests").

    Returns:
        Epsilon value in [0, 1] if found, else None.
    """
    targets = _get("evaluation.roundtrip.per_target", [])
    for t in targets:
        if isinstance(t, dict) and t.get("name") == name:
            return float(t["epsilon"])
    return None


def bibliography_entries() -> int:
    """Return the number of bibliography entries in LITERATURE.md."""
    return int(_get("literature.bibliography_entries", 0))
