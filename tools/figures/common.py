"""Small data-conversion helpers for manuscript figures."""

from __future__ import annotations

import json
from pathlib import Path


def _string_values(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for key, nested in value.items():
            out.append(str(key))
            out.extend(_string_values(nested))
        return out
    if isinstance(value, (list, tuple, set)):
        out = []
        for nested in value:
            out.extend(_string_values(nested))
        return out
    if value is None:
        return []
    return [str(value)]


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _as_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return default
    return default


def _as_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _int_dict(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, int] = {}
    for key, raw in value.items():
        if isinstance(raw, bool):
            continue
        if isinstance(raw, int | float):
            out[str(key)] = int(raw)
    return out
