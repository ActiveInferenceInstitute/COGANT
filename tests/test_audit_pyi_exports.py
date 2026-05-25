"""Regression tests for the public API stub drift audit."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "tools" / "audit_pyi_exports.py"

spec = importlib.util.spec_from_file_location("audit_pyi_exports", AUDIT_PATH)
assert spec is not None
audit_pyi_exports = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(audit_pyi_exports)


def test_audit_pyi_exports_flags_dataclass_field_and_signature_drift(
    tmp_path: Path, capsys: object
) -> None:
    py_path = tmp_path / "public_api.py"
    pyi_path = tmp_path / "public_api.pyi"
    py_path.write_text(
        "\n".join(
            [
                "from dataclasses import dataclass",
                "__all__ = ['Config', 'run']",
                "@dataclass",
                "class Config:",
                "    enabled: bool",
                "    min_confidence: float = 0.4",
                "def run(config: Config, *, min_confidence: float = 0.4) -> dict[str, int]:",
                "    return {}",
            ]
        ),
        encoding="utf-8",
    )
    pyi_path.write_text(
        "\n".join(
            [
                "from dataclasses import dataclass",
                "@dataclass",
                "class Config:",
                "    enabled: bool",
                "def run(config: Config) -> dict[str, int]: ...",
            ]
        ),
        encoding="utf-8",
    )

    assert audit_pyi_exports.main([str(py_path)]) == 1
    err = capsys.readouterr().err
    assert "dataclass field drift" in err
    assert "signature drift" in err
    assert "Config" in err
    assert "run" in err


def test_audit_pyi_exports_accepts_matching_dataclass_fields_and_signatures(
    tmp_path: Path,
) -> None:
    py_path = tmp_path / "public_api.py"
    pyi_path = tmp_path / "public_api.pyi"
    py_path.write_text(
        "\n".join(
            [
                "from dataclasses import dataclass",
                "__all__ = ['Config', 'run']",
                "@dataclass",
                "class Config:",
                "    enabled: bool",
                "    min_confidence: float = 0.4",
                "def run(config: Config, *, min_confidence: float = 0.4) -> dict[str, int]:",
                "    return {}",
            ]
        ),
        encoding="utf-8",
    )
    pyi_path.write_text(
        "\n".join(
            [
                "from dataclasses import dataclass",
                "@dataclass",
                "class Config:",
                "    enabled: bool",
                "    min_confidence: float = ...",
                "def run(config: Config, *, min_confidence: float = ...) -> dict[str, int]: ...",
            ]
        ),
        encoding="utf-8",
    )

    assert audit_pyi_exports.main([str(py_path)]) == 0
