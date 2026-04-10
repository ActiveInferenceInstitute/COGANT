from pathlib import Path
from typing import Any

from _typeshed import Incomplete

logger: Incomplete

def load_bundle(output_dir: Path) -> dict[str, Any]: ...
def diff_command(output_dir_a: str, output_dir_b: str) -> str: ...
