from typing import ClassVar

from _typeshed import Incomplete as Incomplete
from pydantic import BaseModel

class StatespaceConfig(BaseModel):
    normalize_matrices: bool
    matrix_tolerance: float
    max_hidden_states: int
    max_observations: int
    model_config: ClassVar[Incomplete]
