from typing import ClassVar, Literal

from pydantic import BaseModel

class GNNConfig(BaseModel):
    include_metadata: bool
    include_connections: bool
    include_matrices: bool
    matrix_format: Literal['dense', 'sparse']
    model_config: ClassVar[Incomplete]
