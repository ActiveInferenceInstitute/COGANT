from pathlib import Path
from typing import Any

class ValidationResult:
    valid: Any
    errors: list[str]
    warnings: list[str]
    score: Any
    details: dict[str, Any]
    section_scores: dict[str, float]
    def __init__(
        self,
        valid: bool = False,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        score: float = 0.0,
    ) -> None: ...
    def to_dict(self) -> dict[str, Any]: ...
    def to_markdown(self) -> str: ...
    def badge_svg(self) -> str: ...

class GNNValidator:
    REQUIRED_FILES: Any
    CANONICAL_SECTIONS: Any
    UPSTREAM_SECTIONS: Any
    result: ValidationResult
    package_dir: Path
    _upstream_gnn: bool
    def __init__(self) -> None: ...
    def validate_package(
        self, package_dir: str, *, upstream_gnn: bool | None = None
    ) -> ValidationResult: ...
    def validate_markdown(self, markdown: str) -> list[str]: ...
    def validate_state_space(self, state_space_json: dict[str, Any]) -> list[str]: ...
    def validate_matrices(self, matrices_json: dict[str, Any]) -> list[str]: ...
    def validate_provenance(self, provenance_json: dict[str, Any]) -> list[str]: ...
    def generate_validation_badge(self, result: ValidationResult) -> str: ...
