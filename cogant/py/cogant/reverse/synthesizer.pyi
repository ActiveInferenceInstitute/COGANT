from pathlib import Path

from cogant.reverse.parser import ReverseGNNModel
from cogant.reverse.planner import PackagePlan

__all__ = ['synthesize_package']

def synthesize_package(plan: PackagePlan, model: ReverseGNNModel, output_dir: str | Path) -> Path: ...
