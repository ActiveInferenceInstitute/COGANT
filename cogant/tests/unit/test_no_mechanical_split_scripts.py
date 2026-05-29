"""Guard against reintroducing mechanical line-range split generators."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"


def test_scripts_dir_has_no_mechanical_split_generators() -> None:
    offenders = sorted(_SCRIPTS_DIR.glob("split_*.py"))
    assert offenders == [], (
        "Mechanical split_*.py generators are banned (wave-3 debris). "
        f"Remove: {[p.name for p in offenders]}"
    )
