from _typeshed import Incomplete
from pydantic import BaseModel
from typing import Literal, ClassVar

class ReverseConfig(BaseModel):
    synthesis_strategy: Literal['minimal', 'full']
    include_tests: bool
    role_threshold: float
    model_config: ClassVar[Incomplete]
