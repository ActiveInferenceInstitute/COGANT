from typing import ClassVar

from _typeshed import Incomplete as Incomplete
from pydantic import BaseModel

class GraphConfig(BaseModel):
    max_nodes: int
    max_edges: int
    prune_isolated: bool
    include_builtins: bool
    model_config: ClassVar[Incomplete]
