"""Data-pipeline fixture with explicit load, transform, and summarize stages."""

from __future__ import annotations


def load_rows() -> list[dict[str, int | str]]:
    return [
        {"team": "alpha", "value": 2},
        {"team": "beta", "value": 5},
        {"team": "alpha", "value": 7},
    ]


def transform_rows(rows: list[dict[str, int | str]]) -> list[dict[str, int | str]]:
    transformed = []
    for row in rows:
        transformed.append({**row, "value": int(row["value"]) * 10})
    return transformed


def summarize(rows: list[dict[str, int | str]]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for row in rows:
        team = str(row["team"])
        totals[team] = totals.get(team, 0) + int(row["value"])
    return totals


def run_pipeline() -> dict[str, int]:
    return summarize(transform_rows(load_rows()))
