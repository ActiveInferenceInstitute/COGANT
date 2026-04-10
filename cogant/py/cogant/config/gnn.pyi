from _typeshed import Incomplete
from pydantic import BaseModel
from typing import Literal, ClassVar

class GNNConfig(BaseModel):
    include_metadata: bool
    include_connections: bool
    include_matrices: bool
    matrix_format: Literal['dense', 'sparse']
    model_config: ClassVar[Incomplete]
