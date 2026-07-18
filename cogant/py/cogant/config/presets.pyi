from typing import Any

from .schema import ProjectConfig

PRESETS: Any

def get_preset(name: str) -> ProjectConfig: ...
def list_presets() -> list[str]: ...
