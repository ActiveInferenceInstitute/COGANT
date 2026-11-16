"""Real-file cache acceptance for exactly the evidence the dynamic stage consumes."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from coverage import CoverageData

from cogant.api.pipeline import PipelineConfig, PipelineRunner

pytestmark = pytest.mark.unit


def _git(repo: Path, *args: str) -> None:
    env = os.environ.copy()
    env.update(
        GIT_AUTHOR_NAME="Test",
        GIT_AUTHOR_EMAIL="test@example.com",
        GIT_COMMITTER_NAME="Test",
        GIT_COMMITTER_EMAIL="test@example.com",
    )
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        env=env,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "work.py").write_text(
        "def work():\n    value = 1\n    return value\n", encoding="utf-8"
    )
    _git(root, "init", "-q", "-b", "main")
    _git(root, "add", "work.py")
    _git(root, "commit", "-q", "-m", "initial")
    return root


def _config(tmp_path: Path, **updates) -> PipelineConfig:
    return PipelineConfig(
        stages=["ingest", "static", "normalize", "graph", "dynamic", "export"],
        incremental_since="HEAD",
        cache_dir=str(tmp_path / "cache"),
        output_dir=str(tmp_path / "out"),
        render_visualizations=False,
        **updates,
    )


def _trace(path: Path, duration: int) -> None:
    path.write_text(
        json.dumps({"traceEvents": [{"name": "work", "ph": "X", "ts": 0, "dur": duration}]}),
        encoding="utf-8",
    )


def _coverage(path: Path, repo: Path, lines: set[int]) -> None:
    data = CoverageData(basename=str(path))
    data.add_lines({str(repo / "work.py"): lines})
    data.write()


def _xml(path: Path, lines: set[int]) -> None:
    entries = "".join(f'<line number="{line}" hits="1"/>' for line in sorted(lines))
    path.write_text(
        '<coverage><packages><package name="repo"><classes>'
        '<class name="work" filename="work.py"><lines>'
        + entries
        + "</lines></class></classes></package></packages></coverage>",
        encoding="utf-8",
    )


def _graph(config: PipelineConfig) -> dict:
    return json.loads((Path(config.output_dir) / "program_graph.json").read_text(encoding="utf-8"))


def _work(config: PipelineConfig, qualified_name: str = "work.work") -> dict:
    return next(
        node
        for node in _graph(config)["nodes"].values()
        if node["kind"] == "function" and node["qualified_name"] == qualified_name
    )


def _semantic(value):
    if isinstance(value, dict):
        return {
            key: _semantic(item)
            for key, item in value.items()
            if key not in {"created_at", "generated_at", "timestamp"}
        }
    if isinstance(value, list):
        return [_semantic(item) for item in value]
    return value


def _assert_matches_fresh(repo: Path, config: PipelineConfig) -> None:
    incremental = _semantic(_graph(config))
    fresh = config.override(
        incremental_since=None, output_dir=str(Path(config.output_dir).with_name("fresh"))
    )
    result = PipelineRunner().run(str(repo), fresh)
    assert result.errors == []
    assert _semantic(_graph(fresh)) == incremental


def test_changed_trace_bytes_invalidate_same_path_and_unchanged_hits(repo, tmp_path):
    path = tmp_path / "trace.json"
    _trace(path, 1000)
    config = _config(tmp_path, trace_path=str(path))
    runner = PipelineRunner()
    assert runner.run(str(repo), config).errors == []
    assert _work(config)["metadata"]["avg_duration_ms"] == 1.0
    assert runner.run(str(repo), config).metadata["incremental_stats"]["cache_hit"] is True
    _trace(path, 7000)
    changed = runner.run(str(repo), config)
    assert changed.errors == []
    assert changed.metadata["incremental_stats"]["cache_hit"] is False
    assert _work(config)["metadata"]["avg_duration_ms"] == 7.0
    _assert_matches_fresh(repo, config)


@pytest.mark.parametrize("format", ["xml", "sqlite"])
def test_changed_coverage_bytes_invalidate_same_path(repo, tmp_path, format):
    path = tmp_path / ("coverage.xml" if format == "xml" else ".coverage")
    writer = (
        (lambda lines: _xml(path, lines))
        if format == "xml"
        else (lambda lines: _coverage(path, repo, lines))
    )
    writer({2})
    config = _config(tmp_path, coverage_path=str(path))
    runner = PipelineRunner()
    assert runner.run(str(repo), config).errors == []
    assert _work(config)["metadata"]["coverage_hits"] == 1
    writer({2, 3})
    changed = runner.run(str(repo), config)
    assert changed.errors == []
    assert changed.metadata["incremental_stats"]["cache_hit"] is False
    assert _work(config)["metadata"]["coverage_hits"] == 2
    _assert_matches_fresh(repo, config)


def test_autodetected_coverage_arrival_and_removal_change_consumed_snapshot(repo, tmp_path):
    runner = PipelineRunner()
    config = _config(tmp_path)
    assert runner.run(str(repo), config).stage_results["dynamic"]["skipped"] is True
    path = repo / ".coverage"
    _coverage(path, repo, {2})
    arrived = runner.run(str(repo), config)
    assert arrived.metadata["incremental_stats"]["cache_hit"] is False
    assert _work(config)["metadata"]["coverage_hits"] == 1
    path.unlink()
    removed = runner.run(str(repo), config)
    assert removed.stage_results["dynamic"]["skipped"] is True
    assert "coverage_hits" not in _work(config)["metadata"]
    _assert_matches_fresh(repo, config)


def test_explicit_then_plugin_then_autodetection_precedence(repo, tmp_path):
    explicit = tmp_path / "explicit.xml"
    plugin = tmp_path / "plugin.xml"
    _xml(explicit, {2, 3})
    _xml(plugin, {2})
    _coverage(repo / ".coverage", repo, {3})
    config = _config(
        tmp_path, coverage_path=str(explicit), plugins={"dynamic": {"coverage_path": str(plugin)}}
    )
    runner = PipelineRunner()
    assert runner.run(str(repo), config).errors == []
    assert _work(config)["metadata"]["coverage_hits"] == 2
    # Shadowed plugin/autodetected data is not part of the consumed identity.
    _xml(plugin, set())
    _coverage(repo / ".coverage", repo, {2, 3})
    assert runner.run(str(repo), config).metadata["incremental_stats"]["cache_hit"] is True
    plugin_config = config.override(coverage_path=None)
    assert runner.run(str(repo), plugin_config).stage_results["dynamic"]["coverage_path"] == str(
        plugin
    )
    assert "coverage_hits" not in _work(plugin_config)["metadata"]
    auto_config = plugin_config.override(plugins={})
    assert runner.run(str(repo), auto_config).stage_results["dynamic"]["coverage_path"] == str(
        repo / ".coverage"
    )
    assert _work(auto_config)["metadata"]["coverage_hits"] == 2
    _assert_matches_fresh(repo, auto_config)


@pytest.mark.parametrize("mode", ["skip_dynamic", "skip_stage", "not_requested"])
def test_disabled_dynamic_inputs_do_not_invalidate_cache(repo, tmp_path, mode):
    config = _config(tmp_path, trace_path=str(tmp_path / "missing.json"))
    if mode == "skip_dynamic":
        config = config.override(skip_dynamic=True)
    elif mode == "skip_stage":
        config = config.override(skip_stages=["dynamic"])
    else:
        config = config.override(stages=[stage for stage in config.stages if stage != "dynamic"])
    runner = PipelineRunner()
    assert runner.run(str(repo), config).errors == []
    _trace(tmp_path / "other.json", 8000)
    _coverage(repo / ".coverage", repo, {2})
    changed = config.override(
        trace_path=str(tmp_path / "other.json"),
        plugins={"dynamic": {"coverage_path": "absent.xml"}},
    )
    assert runner.run(str(repo), changed).metadata["incremental_stats"]["cache_hit"] is True


def test_explicit_missing_present_corrupt_and_removed_trace_never_replays_old_nodes(repo, tmp_path):
    path = tmp_path / "trace.json"
    config = _config(tmp_path, trace_path=str(path))
    runner = PipelineRunner()
    assert runner.run(str(repo), config).stage_results["dynamic"]["trace_nodes_enriched"] == 0
    _trace(path, 2000)
    assert runner.run(str(repo), config).stage_results["dynamic"]["trace_nodes_enriched"] == 1
    path.write_text("{broken", encoding="utf-8")
    assert runner.run(str(repo), config).stage_results["dynamic"]["trace_nodes_enriched"] == 0
    assert "call_count" not in _work(config)["metadata"]
    path.unlink()
    assert runner.run(str(repo), config).stage_results["dynamic"]["trace_nodes_enriched"] == 0
    _assert_matches_fresh(repo, config)


def test_source_rename_and_delete_keep_full_snapshot_semantics(repo, tmp_path):
    config = _config(tmp_path)
    runner = PipelineRunner()
    assert runner.run(str(repo), config).errors == []
    (repo / "work.py").rename(repo / "moved.py")
    renamed = runner.run(str(repo), config)
    assert renamed.errors == []
    assert _work(config, "moved.work")["path"] == "moved.py"
    _assert_matches_fresh(repo, config)
    (repo / "moved.py").unlink()
    deleted = runner.run(str(repo), config)
    assert deleted.errors == []
    assert not any(node["name"] == "work" for node in _graph(config)["nodes"].values())
    _assert_matches_fresh(repo, config)


def test_xml_symlink_preserves_configured_format_and_content_identity(repo, tmp_path):
    target = tmp_path / "coverage-payload"
    _xml(target, {2})
    path = tmp_path / "coverage.xml"
    path.symlink_to(target)
    config = _config(tmp_path, coverage_path=str(path))
    runner = PipelineRunner()

    first = runner.run(str(repo), config)
    assert first.errors == []
    assert _work(config)["metadata"]["coverage_hits"] == 1
    assert runner.run(str(repo), config).metadata["incremental_stats"]["cache_hit"] is True
    _xml(target, {2, 3})
    changed = runner.run(str(repo), config)
    assert changed.errors == []
    assert changed.metadata["incremental_stats"]["cache_hit"] is False
    assert _work(config)["metadata"]["coverage_hits"] == 2
    _assert_matches_fresh(repo, config)


def test_retained_sqlite_wal_is_consumed_without_mutating_evidence(repo, tmp_path):
    path = tmp_path / ".coverage"
    subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            "import os, sqlite3, sys; "
            "connection = sqlite3.connect(sys.argv[1]); "
            "connection.execute('PRAGMA journal_mode=WAL'); "
            "connection.execute('CREATE TABLE file (id INTEGER, path TEXT)'); "
            "connection.execute('CREATE TABLE line_bits (file_id INTEGER, numbits BLOB)'); "
            "connection.execute('INSERT INTO file VALUES (1, ?)', (sys.argv[2],)); "
            "connection.execute('INSERT INTO line_bits VALUES (1, ?)', (bytes([4]),)); "
            "connection.commit(); os._exit(0)",
            str(path),
            str(repo / "work.py"),
        ],
        check=True,
        stdin=subprocess.DEVNULL,
    )
    wal = Path(str(path) + "-wal")
    before = (path.read_bytes(), wal.read_bytes())
    runner = PipelineRunner()
    config = _config(tmp_path, coverage_path=str(path))

    first = runner.run(str(repo), config)
    assert first.errors == []
    assert _work(config)["metadata"]["coverage_hits"] == 1
    assert (path.read_bytes(), wal.read_bytes()) == before
    assert runner.run(str(repo), config).metadata["incremental_stats"]["cache_hit"] is True
    _assert_matches_fresh(repo, config)
    assert (path.read_bytes(), wal.read_bytes()) == before
