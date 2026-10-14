"""The empirical claim demo must only report what its roundtrip run showed."""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_DEMO = _PACKAGE_ROOT / "scripts" / "empirical_claim_demo.py"
_GNN_FIXTURE = _PACKAGE_ROOT / "examples" / "zoo" / "04_pomdp_minimal" / "model.gnn.md"


def _load_demo() -> ModuleType:
    spec = importlib.util.spec_from_file_location("empirical_claim_demo_under_test", _DEMO)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _roundtrip_section(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], rt_result: dict
) -> str:
    demo = _load_demo()

    def fake_forward(_target: Path, output_dir: Path) -> Path:
        gnn = output_dir / "gnn_package" / "model.gnn.md"
        gnn.parent.mkdir(parents=True)
        shutil.copyfile(_GNN_FIXTURE, gnn)
        return gnn

    monkeypatch.setattr(demo, "run_forward_pipeline", fake_forward)
    monkeypatch.setattr(demo, "run_roundtrip", lambda _target: rt_result)

    demo.main()

    out = capsys.readouterr().out
    return out.split("[2] Roundtrip isomorphism check", 1)[1].split("[3]", 1)[0]


def test_unparsed_roundtrip_is_not_reported_as_confirmed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # ``run_roundtrip`` returns this fallback when the CLI output has no JSON.
    fallback = {"structurally_isomorphic": "unknown", "role_preservation_score": "unknown"}

    section = _roundtrip_section(monkeypatch, capsys, fallback)

    assert "confirmed" not in section.lower()
    assert "preserves structure" not in section


def test_drifting_roundtrip_is_not_reported_as_confirmed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    drift = {
        "roundtrip_status": "DRIFT",
        "structurally_isomorphic": False,
        "role_preservation_score": 0.4,
    }

    section = _roundtrip_section(monkeypatch, capsys, drift)

    assert "confirmed" not in section.lower()
    assert "DRIFT" in section


def test_isomorphic_roundtrip_reports_preserved_structure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    iso = {
        "roundtrip_status": "STRUCTURALLY_ISOMORPHIC",
        "structurally_isomorphic": True,
        "role_preservation_score": 1.0,
    }

    section = _roundtrip_section(monkeypatch, capsys, iso)

    assert "STRUCTURALLY_ISOMORPHIC" in section
    assert "structure preserved" in section.lower()
