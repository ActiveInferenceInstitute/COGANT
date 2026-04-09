"""Temporary placeholder — real implementation arrives in the next step."""
from pathlib import Path
from typing import Union

from cogant.reverse.planner import PackagePlan
from cogant.reverse.parser import ReverseGNNModel


def synthesize_package(
    plan: PackagePlan,
    model: ReverseGNNModel,
    output_dir: Union[str, Path],
) -> Path:
    p = Path(output_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p
