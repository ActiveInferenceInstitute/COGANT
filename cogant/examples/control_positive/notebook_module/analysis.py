"""Notebook-export style fixture."""

from __future__ import annotations

# %% load data
SAMPLES = [3, 5, 8, 13]


# %% transform
def rolling_total(values: list[int]) -> list[int]:
    totals: list[int] = []
    current = 0
    for value in values:
        current += value
        totals.append(current)
    return totals


# %% report
def build_report() -> dict[str, float | list[int]]:
    totals = rolling_total(SAMPLES)
    return {"total": float(totals[-1]), "trajectory": totals}
