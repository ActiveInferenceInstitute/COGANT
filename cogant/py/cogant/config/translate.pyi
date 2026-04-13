from typing import ClassVar

from pydantic import BaseModel

class TranslateConfig(BaseModel):
    max_iterations: int
    confidence_threshold: float
    enable_rules: list[str]
    disable_rules: list[str]
    model_config: ClassVar[Incomplete]
