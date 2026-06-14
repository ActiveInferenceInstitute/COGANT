from dataclasses import dataclass
from pathlib import Path

from cogant.reverse.parser import ReverseGNNModel
from cogant.reverse.planner import PackagePlan

__all__ = [
    "synthesize_package",
    "synthesize_stable_minimal_package",
    "synthesize_with_validation",
    "supports_stable_minimal_profile",
    "SynthesisResult",
]

@dataclass
class SynthesisResult:
    code: str = ...
    parse_ok: bool = ...
    issues: list[str] = ...
    role_counts: dict[str, int] = ...
    filename: str = ...

def synthesize_package(
    plan: PackagePlan, model: ReverseGNNModel, output_dir: str | Path
) -> Path: ...
def synthesize_stable_minimal_package(
    plan: PackagePlan, model: ReverseGNNModel, output_dir: str | Path
) -> Path: ...
def synthesize_with_validation(
    plan: PackagePlan, model: ReverseGNNModel, output_dir: str | Path
) -> tuple[str, list[str]]: ...
def supports_stable_minimal_profile(plan: PackagePlan, model: ReverseGNNModel) -> bool: ...
