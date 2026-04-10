from cogant.reverse.parser import ReverseGNNModel
from cogant.reverse.planner import PackagePlan
from pathlib import Path

__all__ = ['synthesize_package']

def synthesize_package(plan: PackagePlan, model: ReverseGNNModel, output_dir: str | Path) -> Path: ...
