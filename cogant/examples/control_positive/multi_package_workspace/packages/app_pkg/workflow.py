"""Application package that consumes the core package."""

from __future__ import annotations

try:
    from core_pkg import score
except ImportError:  # pragma: no cover - fixture remains parseable without PYTHONPATH
    from packages.core_pkg import score  # type: ignore[no-redef]


def run(values: list[int]) -> dict[str, int | str]:
    total = score(values)
    status = "large" if total > 20 else "small"
    return {"score": total, "status": status}
