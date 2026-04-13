from typing import ClassVar

from pydantic import BaseModel

class IngestConfig(BaseModel):
    max_file_size_kb: int
    include_extensions: list[str]
    exclude_patterns: list[str]
    follow_symlinks: bool
    encoding: str
    model_config: ClassVar[Incomplete]
