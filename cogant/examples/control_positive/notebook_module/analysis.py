"""Notebook-export style fixture."""

from __future__ import annotations

# %% load data
SAMPLES = [3, 5, 8, 13]


class AnalysisState:
    """Notebook-export state holder used by the roundtrip fixture."""

    def __init__(self, samples: list[int]) -> None:
        self.samples = samples

    def get_samples(self) -> list[int]:
        return self.samples

    def read_total(self) -> float:
        totals = rolling_total(self.samples)
        return float(totals[-1])


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
    state = AnalysisState(SAMPLES)
    totals = rolling_total(state.get_samples())
    return {"total": state.read_total(), "trajectory": totals}
