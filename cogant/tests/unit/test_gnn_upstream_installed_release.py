"""Real installed-package identity checks, separate from bridge routing tests."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from cogant.gnn.upstream_bridge import (
    MIN_UPSTREAM_MAJOR,
    UPSTREAM_DISTRIBUTION,
    is_upstream_gnn_available,
    upstream_version,
)


def test_bridge_ignores_a_retired_src_gnn_provider(tmp_path: Path) -> None:
    # Given: an importable legacy namespace that fails if the bridge selects it.
    legacy = tmp_path / "src"
    legacy.mkdir()
    (legacy / "__init__.py").write_text("", encoding="utf-8")
    (legacy / "gnn.py").write_text(
        "raise AssertionError('retired provider selected')\n", encoding="utf-8"
    )
    # Compare the actual guarded baseline, not version metadata alone.
    env = os.environ.copy()
    source = str(Path(__file__).resolve().parents[2] / "py")
    env["PYTHONPATH"] = os.pathsep.join((str(tmp_path), source))
    program = (
        "import json; from cogant.gnn.upstream_bridge import "
        "is_upstream_gnn_available, upstream_version; "
        "print(json.dumps({'available':is_upstream_gnn_available(),"
        "'version':upstream_version()}))"
    )
    baseline_env = env.copy()
    baseline_env["PYTHONPATH"] = source
    baseline = subprocess.run(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=baseline_env,
        check=True,
    )
    # When: resolving the real COGANT bridge with the conflicting namespace present.
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    # Then: only the installed top-level provider controls availability and version.
    assert json.loads(result.stdout) == json.loads(baseline.stdout)


def test_installed_upstream_matches_locked_release_identity() -> None:
    # Given: the explicitly optional upstream distribution and committed lock.
    if os.environ.get("COGANT_GNN_ORIGIN", "installed") != "installed":
        pytest.skip("explicit source-mode evidence is not installed-origin qualification")
    try:
        distribution = importlib.metadata.distribution(UPSTREAM_DISTRIBUTION)
    except importlib.metadata.PackageNotFoundError:
        pytest.skip("optional upstream gnn dependency not installed")
    root = Path(__file__).resolve().parents[2]
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    locked = next(
        package for package in lock["package"] if package["name"] == UPSTREAM_DISTRIBUTION
    )
    direct_url_text = distribution.read_text("direct_url.json")
    assert direct_url_text is not None
    direct_url = json.loads(direct_url_text)
    # When: resolving the public import through the guarded COGANT bridge.
    assert is_upstream_gnn_available(), "installed upstream failed the bridge availability gate"
    version = upstream_version()
    # Then: metadata, import version, installed source, and lock identify one release.
    assert version is not None
    assert int(version.split(".")[0]) >= MIN_UPSTREAM_MAJOR
    assert version == distribution.version == locked["version"]
    assert direct_url["vcs_info"]["commit_id"] == locked["source"]["git"].rsplit("#", 1)[1]


@pytest.fixture
def reviewed_artifacts():
    from cogant.gnn.upstream_bridge.qualification import BOOTSTRAP_SHA256, MANIFEST_SHA256

    required = {
        "COGANT_GNN_BOOTSTRAP": BOOTSTRAP_SHA256,
        "COGANT_GNN_MANIFEST": MANIFEST_SHA256,
    }
    for name, expected in required.items():
        raw = os.environ.get(name)
        if raw is None:
            pytest.skip(f"prepared reviewed producer input required: {name}")
        assert hashlib.sha256(Path(raw).read_bytes()).hexdigest() == expected


def test_changed_bootstrap_is_refused_before_its_body_runs(tmp_path, monkeypatch):
    from cogant.gnn.upstream_bridge.qualification import load_bootstrap

    marker = tmp_path / "bootstrap-ran"
    bootstrap = tmp_path / "bootstrap.py"
    bootstrap.write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\n", encoding="utf-8"
    )
    monkeypatch.setenv("COGANT_GNN_BOOTSTRAP", str(bootstrap))
    with pytest.raises(ImportError, match="frozen SHA-256"):
        load_bootstrap()
    assert not marker.exists()


def test_changed_manifest_refuses_before_target_import(reviewed_artifacts, tmp_path, monkeypatch):
    from cogant.gnn.upstream_bridge.qualification import qualified_upstream

    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("COGANT_GNN_MANIFEST", str(manifest))
    with pytest.raises(ImportError, match="COGANT_GNN_MANIFEST failed its frozen SHA-256"):
        with qualified_upstream():
            pytest.fail("changed manifest admitted target execution")


def test_current_gnn_shadow_refuses_before_import_marker(reviewed_artifacts, tmp_path, monkeypatch):
    """Hostile import marker only; never a substitute pinned parser fixture."""
    from cogant.gnn.upstream_bridge.qualification import invoke

    marker = tmp_path / "foreign-ran"
    foreign = tmp_path / "gnn"
    foreign.mkdir()
    (foreign / "__init__.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\n", encoding="utf-8"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("COGANT_GNN_ORIGIN", "installed")
    monkeypatch.delenv("COGANT_GNN_SOURCE_ROOT", raising=False)
    with pytest.raises(ImportError, match="source-content-mismatch"):
        invoke("version")
    assert not marker.exists()


def test_preloaded_foreign_module_cannot_authorize_a_later_verdict(tmp_path):
    foreign = tmp_path / "gnn"
    foreign.mkdir()
    marker = tmp_path / "foreign-imported"
    (foreign / "__init__.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\n", encoding="utf-8"
    )
    source = str(Path(__file__).resolve().parents[2] / "py")
    program = (
        "import sys\n"
        f"sys.path.insert(0, {source!r})\n"
        "from cogant.gnn.upstream_bridge.qualification import invoke\n"
        f"sys.path.insert(0, {str(tmp_path)!r})\n"
        "import gnn\n"
        "try:\n    invoke('version')\n"
        "except ImportError as exc:\n    print(str(exc))\n"
        "else:\n    raise AssertionError('preloaded foreign module accepted')\n"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", program],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert marker.is_file()  # The prior foreign import is deliberately observed.
    assert "source-already-imported" in result.stdout


def test_real_calculator_verdicts_finalize_qualification(reviewed_artifacts, tmp_path):
    from cogant.api.pipeline import PipelineConfig, PipelineRunner
    from cogant.gnn.upstream_bridge import run_upstream_validate_gnn

    calculator = Path(__file__).resolve().parents[2] / "examples/control_positive/calculator"
    out = tmp_path / "out"
    bundle = PipelineRunner().run(
        str(calculator),
        PipelineConfig(output_dir=str(out), skip_stages=["validate"], render_visualizations=False),
    )
    assert bundle.errors == []
    markdown = (out / "gnn_package/model.gnn.md").read_text(encoding="utf-8")
    for level in ("standard", "strict"):
        result = run_upstream_validate_gnn(markdown, validation_level=level)
        assert result.available and result.ok, result.to_dict()
        assert result.source_qualification["ok"] is True
        assert result.source_qualification["imports_verified"] is True
        assert result.source_qualification["execution_verified"] is False
        if os.environ.get("COGANT_GNN_ORIGIN", "installed") == "source":
            assert result.source_qualification["origin"]["kind"] == "explicit-source"
            assert result.source_qualification["origin"]["vcs_verified"] is False
        rejected = run_upstream_validate_gnn(markdown.split("##", 1)[0], validation_level=level)
        assert rejected.available and rejected.ok is False
        assert rejected.errors

    from cogant.gnn.upstream_bridge.pipeline import UpstreamPipelineConfig, run_upstream_pipeline

    pipeline = run_upstream_pipeline(
        UpstreamPipelineConfig(
            target_dir=out / "gnn_package",
            output_dir=tmp_path / "upstream",
            only_steps=[3, 5, 6],
        )
    )
    assert pipeline.available and pipeline.error is None, pipeline.to_dict()
    assert pipeline.failure_count == 0
    proof = pipeline.source_qualification
    assert proof["main"]["imports_verified"] is True
    assert {"3_gnn.py", "5_type_checker.py", "6_validation.py"} <= {
        record["entrypoint"] for record in proof["worker_receipts"]
    }
    assert all(
        record["qualification"]["ok"] and record["qualification"]["imports_verified"]
        for record in proof["worker_receipts"]
    )


def test_numbered_worker_refuses_tampered_real_package_before_script_marker(
    reviewed_artifacts, tmp_path, monkeypatch
):
    import shutil

    from cogant.gnn.upstream_bridge import qualification

    raw = os.environ.get("COGANT_GNN_SOURCE_ROOT")
    if raw is None:
        pytest.skip(
            "this source-artifact negative control requires the independently selected source root"
        )
    copied = tmp_path / "source" / "gnn"
    shutil.copytree(Path(raw), copied)
    marker = tmp_path / "unverified-worker-ran"
    script = copied / "6_validation.py"
    script.write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\n"
        + script.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    startup = tmp_path / "startup"
    startup.mkdir()
    (startup / "sitecustomize.py").write_bytes(
        Path(qualification.__file__).with_name("source_startup.py").read_bytes()
    )
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    environment = os.environ.copy()
    environment.update(
        COGANT_GNN_CUSTODY_FILE=qualification.__file__,
        COGANT_GNN_CUSTODY_SHA256=hashlib.sha256(
            Path(qualification.__file__).read_bytes()
        ).hexdigest(),
        COGANT_GNN_CHILD_RECEIPTS=str(receipts),
        COGANT_GNN_ORIGIN="source",
        COGANT_GNN_SOURCE_ROOT=str(copied),
        PYTHONPATH=str(startup),
        PYTHONDONTWRITEBYTECODE="1",
    )
    result = subprocess.run(
        [sys.executable, "-P", str(script), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )
    assert result.returncode == 78, result.stdout + result.stderr
    assert "source-content-mismatch" in result.stderr
    assert not marker.exists()
    assert not list(receipts.glob("*.json"))


def test_live_getters_require_an_explicit_source_lifetime():
    from cogant.gnn import get_upstream_gnn_format_enum, get_upstream_parsing_system

    for getter in (get_upstream_gnn_format_enum, get_upstream_parsing_system):
        with pytest.raises(ImportError, match="qualified_upstream"):
            getter()


def test_live_parser_and_enum_stay_inside_one_fresh_qualified_scope(reviewed_artifacts, tmp_path):
    from cogant.api.pipeline import PipelineConfig, PipelineRunner

    source = Path(__file__).resolve().parents[2] / "py"
    calculator = source.parent / "examples/control_positive/calculator"
    out = tmp_path / "package"
    bundle = PipelineRunner().run(
        str(calculator),
        PipelineConfig(output_dir=str(out), skip_stages=["validate"], render_visualizations=False),
    )
    assert bundle.errors == []
    program = (
        "import json, sys\n"
        f"sys.path.insert(0, {str(source)!r})\n"
        "from cogant.gnn import get_upstream_parsing_system, get_upstream_gnn_format_enum\n"
        "from cogant.gnn.upstream_bridge.qualification import qualified_upstream\n"
        "with qualified_upstream() as (_, receipt):\n"
        "    formats = get_upstream_gnn_format_enum()\n"
        "    parser = get_upstream_parsing_system()\n"
        "    parsed = parser.parse_file(sys.argv[1], formats.MARKDOWN)\n"
        "    assert parsed.success, parsed.errors\n"
        "    names = [variable.name for variable in parsed.model.variables]\n"
        "    assert names\n"
        "    format_name = parsed.model.source_format.name\n"
        "assert receipt['imports_verified'] and receipt['ok']\n"
        "print(json.dumps({'variables': names, 'format': format_name}))\n"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", program, str(out / "gnn_package/model.gnn.md")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    parsed = json.loads(result.stdout)
    assert parsed["format"] == "MARKDOWN"
    assert parsed["variables"]


@pytest.mark.parametrize("action", ["change", "remove"])
def test_python_child_cannot_bypass_an_altered_owned_startup(tmp_path: Path, action: str) -> None:
    source = Path(__file__).resolve().parents[2] / "py"
    startup = tmp_path / "startup"
    startup.mkdir()
    marker = tmp_path / "child-executed"
    mutation = (
        "startup_file.write_bytes(b'this is invalid Python!\\n')"
        if action == "change"
        else "startup_file.unlink()"
    )
    child = f"from pathlib import Path; Path({str(marker)!r}).write_text('executed')"
    program = (
        "import os, subprocess, sys\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(source)!r})\n"
        "from cogant.gnn.upstream_bridge import source_startup\n"
        f"startup = Path({str(startup)!r})\n"
        "startup_file = startup / 'sitecustomize.py'\n"
        "startup_file.write_bytes(Path(source_startup.__file__).read_bytes())\n"
        "os.environ['PYTHONPATH'] = str(startup)\n"
        "source_startup.install_launch_guard([], startup)\n"
        f"{mutation}\n"
        "try:\n"
        f"    subprocess.run([sys.executable, '-P', '-c', {child!r}], "
        "stdin=subprocess.DEVNULL, check=True, timeout=30)\n"
        "except RuntimeError as exc:\n"
        "    assert 'startup source' in str(exc), str(exc)\n"
        "else:\n"
        "    raise AssertionError('Python child launched with altered source startup')\n"
    )
    subprocess.run(
        [sys.executable, "-I", "-c", program],
        stdin=subprocess.DEVNULL,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert not marker.exists()


def test_real_lightweight_process_workers_finalize_source_receipts(reviewed_artifacts, tmp_path):
    import shutil

    from cogant.api.pipeline import PipelineConfig, PipelineRunner
    from cogant.gnn.upstream_bridge.qualification import invoke

    calculator = Path(__file__).resolve().parents[2] / "examples/control_positive/calculator"
    package = tmp_path / "calculator"
    bundle = PipelineRunner().run(
        str(calculator),
        PipelineConfig(output_dir=str(package), skip_stages=["validate"], render_visualizations=False),
    )
    assert bundle.errors == []
    models = tmp_path / "models"
    models.mkdir()
    for name in ("first.gnn.md", "second.gnn.md"):
        shutil.copyfile(package / "gnn_package/model.gnn.md", models / name)
    result = invoke("process_gnn_directory_lightweight", models, tmp_path / "processed", workers=2)
    assert result["value"]["success"], result
    assert result["value"]["files_processed"] == 2
    records = result["worker_qualification"]["worker_receipts"]
    assert len(records) >= 2
    assert all(record["entrypoint"] == "-c" for record in records)
    assert all(
        record["qualification"]["ok"] and record["qualification"]["imports_verified"]
        for record in records
    )


@pytest.mark.parametrize("action", ["change", "remove"])
def test_spawn_child_cannot_bypass_altered_owned_startup(tmp_path: Path, action: str) -> None:
    source = Path(__file__).resolve().parents[2] / "py"
    startup = tmp_path / "startup"
    startup.mkdir()
    marker = tmp_path / "child-executed"
    mutation = (
        "startup_file.write_text('invalid startup!')"
        if action == "change"
        else "startup_file.unlink()"
    )
    program = (
        "import multiprocessing, os, sys\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(source)!r})\n"
        "from cogant.gnn.upstream_bridge import source_startup\n"
        f"startup = Path({str(startup)!r})\n"
        "startup_file = startup / 'sitecustomize.py'\n"
        "startup_file.write_bytes(Path(source_startup.__file__).read_bytes())\n"
        "os.environ['PYTHONPATH'] = str(startup)\n"
        "source_startup.install_launch_guard([], startup)\n"
        f"{mutation}\n"
        "try:\n"
        f"    multiprocessing.get_context('spawn').Process(target=Path({str(marker)!r}).touch).start()\n"
        "except RuntimeError as exc:\n"
        "    assert 'startup source' in str(exc), str(exc)\n"
        "else:\n"
        "    raise AssertionError('multiprocessing worker bypassed startup admission')\n"
    )
    subprocess.run(
        [sys.executable, "-I", "-B", "-c", program],
        stdin=subprocess.DEVNULL,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert not marker.exists()
