from typing import Any, ClassVar, Literal

from _typeshed import Incomplete
from pydantic import BaseModel
from pydantic import ValidationInfo as ValidationInfo

class CogantBaseModel(BaseModel):
    model_config: ClassVar[Incomplete]

class StableID(str): ...

class SemanticVersion(str):
    def __new__(cls, value: str) -> SemanticVersion: ...

class Span(CogantBaseModel):
    start_line: int
    start_col: int
    end_line: int
    end_col: int
    @classmethod
    def validate_span_bounds(cls, v: int) -> int: ...
    @classmethod
    def validate_end_after_start(cls, v: int, info: ValidationInfo) -> int: ...

class EvidenceRef(CogantBaseModel):
    evidence_id: str
    kind: Literal[
        "source_span", "ast_fact", "trace_event", "test_assertion", "config_entry", "commit_event"
    ]
    confidence: float
    locator: str | None

class TypeInfo(CogantBaseModel):
    base_type: str
    is_optional: bool
    is_generic: bool
    type_parameters: list[str]
    is_collection: bool
    collection_element_type: str | None
    metadata: dict[str, Any]

class ConfidenceMetric(CogantBaseModel):
    score: float
    rationale: str | None
    evidence_types: list[str]

class LocationInfo(CogantBaseModel):
    path: str
    span: Span | None
    language: str | None
    repo_root: str | None

def generate_stable_id(content: str, prefix: str = "") -> StableID: ...
