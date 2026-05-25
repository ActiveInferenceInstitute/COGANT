"""Tests for :mod:`cogant.viz.batch_dashboard`.

Strict no-mocks policy: every test fabricates a real ``output/`` tree
on disk via ``tmp_path``, populates ``run_manifest.json`` and a small
``bundle.json`` per target, and exercises the generator end-to-end. The
goal is full coverage of the public surface plus its edge cases
(missing manifest, malformed bundle, empty targets, timing fallbacks).
"""

from __future__ import annotations

import csv
import io
import json
import sys
import textwrap
from pathlib import Path

import pytest

# Resolve py/cogant without an editable install
_REPO_ROOT = Path(__file__).resolve().parents[2]
_PY_ROOT = _REPO_ROOT / "py"
if _PY_ROOT.is_dir() and str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))

from cogant.viz.batch_dashboard import (  # noqa: E402
    BatchDashboardGenerator,
    TargetMetrics,
    write_batch_dashboard,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_bundle(run_dir: Path, *, nodes: int, edges: int, mappings: int, score: float) -> Path:
    """Write a minimal bundle.json under ``run_dir/data/``.

    Matches the shape produced by ``cogant translate --layout-output``:
    ``stages.graph.{nodes,edges}`` are dicts keyed by id, and the
    validate score lives at the top level for convenience.
    """
    data_dir = run_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    bundle = {
        "validation_score": score,
        "stages": {
            "graph": {
                "nodes": {f"n{i}": {} for i in range(nodes)},
                "edges": {f"e{i}": {} for i in range(edges)},
            },
            "translate": {
                "mappings": {f"m{i}": {} for i in range(mappings)},
            },
        },
    }
    path = data_dir / "bundle.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    return path


def _write_stage_results_bundle(
    run_dir: Path, *, nodes: int, edges: int, mappings: int, score: float
) -> Path:
    """Write the current COGANT ``stage_results`` bundle layout."""
    data_dir = run_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    bundle = {
        "stage_results": {
            "graph": {
                "nodes": {f"n{i}": {} for i in range(nodes)},
                "edges": {f"e{i}": {} for i in range(edges)},
            },
            "translate": {
                "mapping_count": mappings,
                "mapping_ids": [f"m{i}" for i in range(mappings)],
            },
            "validate": {
                "gnn_validation": {
                    "valid": True,
                    "score": score,
                },
            },
        },
    }
    path = data_dir / "bundle.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    return path


def _write_gnn_package(run_dir: Path, *, file_count: int = 3) -> None:
    pkg = run_dir / "gnn_package"
    pkg.mkdir(parents=True, exist_ok=True)
    for i in range(file_count):
        (pkg / f"file_{i}.md").write_text(f"# file {i}\n", encoding="utf-8")


def _seed_output_tree(tmp_path: Path) -> Path:
    """Build an output_root with three plausible targets + a manifest."""
    output_root = tmp_path / "output"
    output_root.mkdir()

    # Target A — local, fully scored
    a = output_root / "calculator"
    a.mkdir()
    _write_bundle(a, nodes=4, edges=6, mappings=2, score=100.0)
    _write_gnn_package(a, file_count=4)
    (a / "site").mkdir()
    (a / "site" / "inspection_dashboard.html").write_text(
        "<html><body>dashboard</body></html>\n", encoding="utf-8"
    )
    (a / "figures").mkdir()
    (a / "figures" / "graphical_abstract.svg").write_text("<svg />\n", encoding="utf-8")
    (a / "validate.txt").write_text("validation ok\n", encoding="utf-8")
    (a / "scan.json").write_text("{}", encoding="utf-8")
    (a / "roundtrip").mkdir()
    (a / "roundtrip" / "metrics.json").write_text(
        json.dumps({"role_match_score": 1.0}), encoding="utf-8"
    )

    # Target B — remote git_url, lower score
    b = output_root / "remote_thing"
    b.mkdir()
    _write_bundle(b, nodes=12, edges=18, mappings=5, score=85.0)
    (b / "data" / "parser_report.json").write_text(
        json.dumps({"parser_fallback_count": 2}), encoding="utf-8"
    )
    _write_gnn_package(b, file_count=2)

    # Target C — local but with a parse failure (malformed bundle)
    c = output_root / "broken"
    c.mkdir()
    (c / "bundle.json").write_text("{not valid json", encoding="utf-8")

    manifest = {
        "started_at": "2026-05-12T10:00:00Z",
        "finished_at": "2026-05-12T10:01:00Z",
        "summary": {
            "total_wall_time_s": 60.0,
            "target_count": 3,
            "failed_steps": ["translate:broken"],
        },
        "targets": [
            {
                "id": "calculator",
                "run_dir": str(a),
                "path": "/tmp/calculator",
                "commands": [
                    {"cmd": "translate", "step": "translate:calculator", "exit": 0, "wall_time_s": 1.5},
                    {"cmd": "validate", "step": "validate:calculator", "exit": 0, "wall_time_s": 0.5},
                ],
            },
            {
                "id": "remote_thing",
                "run_dir": str(b),
                "git_url": "https://example.com/repo.git",
                "commands": [
                    {"cmd": "translate", "step": "translate:remote_thing", "exit": 0, "wall_time_s": 3.2},
                ],
            },
            {
                "id": "broken",
                "run_dir": str(c),
                "path": "/tmp/broken",
                "failed_steps": ["translate"],
                "commands": [
                    {"cmd": "translate", "step": "translate:broken", "exit": 1, "wall_time_s": 0.1},
                ],
            },
        ],
    }
    (output_root / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return output_root


# ---------------------------------------------------------------------------
# load_manifest / discover_targets
# ---------------------------------------------------------------------------


class TestLoadManifest:
    def test_load_manifest_reads_disk(self, tmp_path: Path) -> None:
        root = _seed_output_tree(tmp_path)
        gen = BatchDashboardGenerator(root)
        man = gen.load_manifest()
        assert isinstance(man, dict)
        assert man["summary"]["target_count"] == 3
        assert len(man["targets"]) == 3

    def test_load_manifest_returns_skeleton_when_absent(self, tmp_path: Path) -> None:
        root = tmp_path / "empty"
        root.mkdir()
        gen = BatchDashboardGenerator(root)
        man = gen.load_manifest()
        assert man == {"targets": [], "summary": {}}

    def test_explicit_manifest_overrides_disk(self, tmp_path: Path) -> None:
        root = _seed_output_tree(tmp_path)
        explicit = {"targets": [], "summary": {"target_count": 0}}
        gen = BatchDashboardGenerator(root, manifest=explicit)
        assert gen.load_manifest() is explicit


class TestDiscoverTargets:
    def test_uses_manifest_when_present(self, tmp_path: Path) -> None:
        root = _seed_output_tree(tmp_path)
        gen = BatchDashboardGenerator(root)
        entries = gen.discover_targets()
        assert [e["id"] for e in entries] == ["calculator", "remote_thing", "broken"]

    def test_scans_filesystem_when_no_manifest(self, tmp_path: Path) -> None:
        root = tmp_path / "output"
        root.mkdir()
        # Three subdirs, one without a bundle
        for name, with_bundle in (("a", True), ("b", True), ("c", False)):
            d = root / name
            d.mkdir()
            if with_bundle:
                _write_bundle(d, nodes=1, edges=0, mappings=0, score=50.0)
        gen = BatchDashboardGenerator(root)
        entries = gen.discover_targets()
        ids = sorted(e["id"] for e in entries)
        assert ids == ["a", "b"]

    def test_handles_missing_output_root(self, tmp_path: Path) -> None:
        gen = BatchDashboardGenerator(tmp_path / "nope")
        assert gen.discover_targets() == []


# ---------------------------------------------------------------------------
# collect_target_metrics
# ---------------------------------------------------------------------------


class TestCollectMetrics:
    def test_collect_basic_counts(self, tmp_path: Path) -> None:
        root = _seed_output_tree(tmp_path)
        gen = BatchDashboardGenerator(root)
        metrics = gen.collect_target_metrics()
        by_id = {m.target_id: m for m in metrics}

        assert by_id["calculator"].score == 100.0
        assert by_id["calculator"].node_count == 4
        assert by_id["calculator"].edge_count == 6
        assert by_id["calculator"].mapping_count == 2
        assert by_id["calculator"].kind == "local"
        assert by_id["calculator"].gnn_package_files == 4
        assert by_id["calculator"].wall_time_s == pytest.approx(2.0)

        assert by_id["remote_thing"].kind == "remote"
        assert by_id["remote_thing"].source.endswith(".git")
        assert by_id["remote_thing"].score == 85.0
        assert by_id["remote_thing"].parser_status == "fallback"

        # Broken bundle.json should not raise — score is None, counts zero
        assert by_id["broken"].score is None
        assert by_id["broken"].node_count == 0
        assert by_id["broken"].failed_steps == ("translate",)
        assert by_id["broken"].parser_status == "unknown"

    def test_presence_flags(self, tmp_path: Path) -> None:
        root = _seed_output_tree(tmp_path)
        metrics = BatchDashboardGenerator(root).collect_target_metrics()
        calc = next(m for m in metrics if m.target_id == "calculator")
        assert calc.presence["site"] is True
        assert calc.presence["inspection_dashboard"] is True
        assert calc.presence["graphical_abstract"] is True
        assert calc.presence["roundtrip"] is True
        assert calc.presence["roundtrip_metrics"] is True
        assert calc.presence["validate_report"] is True
        assert calc.presence["scan_json"] is True
        rem = next(m for m in metrics if m.target_id == "remote_thing")
        assert rem.presence["site"] is False

    def test_collects_current_stage_results_bundle_shape(self, tmp_path: Path) -> None:
        output_root = tmp_path / "output"
        run_dir = output_root / "stage_results_target"
        _write_stage_results_bundle(run_dir, nodes=7, edges=9, mappings=4, score=96.5)
        (output_root / "run_manifest.json").write_text(
            json.dumps(
                {
                    "summary": {},
                    "targets": [
                        {
                            "id": "stage_results_target",
                            "run_dir": str(run_dir),
                            "path": "/tmp/stage-results-target",
                            "commands": [
                                {
                                    "cmd": "translate",
                                    "step": "translate:stage_results_target",
                                    "exit": 0,
                                    "wall_time_s": 2.25,
                                }
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        [metric] = BatchDashboardGenerator(output_root).collect_target_metrics()

        assert metric.score == 96.5
        assert metric.node_count == 7
        assert metric.edge_count == 9
        assert metric.mapping_count == 4
        assert metric.wall_time_s == pytest.approx(2.25)

    def test_as_jsonable_round_trip(self, tmp_path: Path) -> None:
        m = TargetMetrics(
            target_id="x",
            kind="local",
            source="/tmp/x",
            score=99.0,
            failed_steps=("a", "b"),
            presence={"site": True},
        )
        out = m.as_jsonable()
        # Must serialise round-trip cleanly
        json.loads(json.dumps(out))
        assert out["failed_steps"] == ["a", "b"]


# ---------------------------------------------------------------------------
# Renderers — CSV / JSON / Mermaid / Markdown
# ---------------------------------------------------------------------------


class TestRenderSummary:
    def test_csv_has_header_and_rows(self, tmp_path: Path) -> None:
        root = _seed_output_tree(tmp_path)
        gen = BatchDashboardGenerator(root)
        metrics = gen.collect_target_metrics()
        csv_text = gen.render_summary_csv(metrics)
        rows = list(csv.reader(io.StringIO(csv_text)))
        header = rows[0]
        assert "target_id" in header
        assert "node_count" in header
        assert "parser_status" in header
        assert "has_inspection_dashboard" in header
        assert "has_graphical_abstract" in header
        assert "has_roundtrip_metrics" in header
        assert len(rows) == 1 + len(metrics)

    def test_csv_empty_metrics_still_valid(self, tmp_path: Path) -> None:
        gen = BatchDashboardGenerator(tmp_path)
        csv_text = gen.render_summary_csv([])
        rows = list(csv.reader(io.StringIO(csv_text)))
        assert len(rows) == 1  # header only

    def test_metrics_json_has_top_level_keys(self, tmp_path: Path) -> None:
        root = _seed_output_tree(tmp_path)
        gen = BatchDashboardGenerator(root)
        metrics = gen.collect_target_metrics()
        text = gen.render_metrics_json(metrics)
        payload = json.loads(text)
        assert payload["schema_version"] == "1.0"
        assert payload["summary"]["target_count"] == 3
        assert len(payload["targets"]) == 3
        assert {"target_id", "score", "presence"} <= set(payload["targets"][0])


class TestRenderMermaid:
    def test_node_bar_contains_target_labels(self, tmp_path: Path) -> None:
        root = _seed_output_tree(tmp_path)
        gen = BatchDashboardGenerator(root)
        metrics = gen.collect_target_metrics()
        bar = gen.render_mermaid_node_bar(metrics)
        assert "xychart-beta" in bar
        assert "calculator" in bar
        assert "remote_thing" in bar

    def test_edge_bar_renders_for_empty_metrics(self, tmp_path: Path) -> None:
        gen = BatchDashboardGenerator(tmp_path)
        bar = gen.render_mermaid_edge_bar([])
        assert "xychart-beta" in bar
        assert "(no targets)" in bar

    def test_score_distribution_buckets(self, tmp_path: Path) -> None:
        root = _seed_output_tree(tmp_path)
        gen = BatchDashboardGenerator(root)
        metrics = gen.collect_target_metrics()
        chart = gen.render_mermaid_score_pie(metrics)
        assert "xychart-beta" in chart
        assert '"100"' in chart  # calculator
        assert '"70-89"' in chart  # remote_thing (85)
        assert '"no-score"' in chart  # broken

    def test_visual_completeness_distribution_buckets(self, tmp_path: Path) -> None:
        root = _seed_output_tree(tmp_path)
        gen = BatchDashboardGenerator(root)
        metrics = gen.collect_target_metrics()
        chart = gen.render_mermaid_visual_completeness_pie(metrics)
        assert "xychart-beta" in chart
        assert "Visual workbench completeness" in chart
        assert '"dashboard+abstract+roundtrip"' in chart
        assert '"missing"' in chart

    def test_parser_status_distribution_buckets(self, tmp_path: Path) -> None:
        root = _seed_output_tree(tmp_path)
        gen = BatchDashboardGenerator(root)
        metrics = gen.collect_target_metrics()
        chart = gen.render_mermaid_parser_status_pie(metrics)
        assert "xychart-beta" in chart
        assert "Parser status distribution" in chart
        assert '"parsed"' in chart
        assert '"fallback"' in chart
        assert '"unknown"' in chart

    def test_gantt_has_section_per_target(self, tmp_path: Path) -> None:
        root = _seed_output_tree(tmp_path)
        gen = BatchDashboardGenerator(root)
        gantt = gen.render_mermaid_gantt()
        assert gantt.startswith("gantt")
        assert "section calculator" in gantt
        assert "section remote_thing" in gantt

    def test_gantt_fallback_when_no_timing(self, tmp_path: Path) -> None:
        # Manifest with commands but no wall_time_s
        manifest = {
            "targets": [
                {"id": "a", "commands": [{"cmd": "translate", "exit": 0}]}
            ],
            "summary": {},
        }
        gen = BatchDashboardGenerator(tmp_path, manifest=manifest)
        gantt = gen.render_mermaid_gantt()
        assert "no-data" in gantt
        assert gantt.startswith("gantt")


class TestRenderMarkdown:
    def test_markdown_includes_headline_and_table(self, tmp_path: Path) -> None:
        root = _seed_output_tree(tmp_path)
        gen = BatchDashboardGenerator(root)
        metrics = gen.collect_target_metrics()
        md = gen.render_markdown_dashboard(metrics)
        assert "# COGANT batch dashboard" in md
        assert "| Target |" in md
        assert "`calculator`" in md
        # Four Mermaid embeds: nodes, edges, score buckets, visual completeness.
        assert md.count("```mermaid") >= 4
        assert "Visual workbench complete" in md
        assert "Parser status distribution" in md

    def test_markdown_handles_empty_metrics(self, tmp_path: Path) -> None:
        gen = BatchDashboardGenerator(tmp_path)
        md = gen.render_markdown_dashboard([])
        assert "(no targets discovered)" in md
        assert "Mean validation score" in md


# ---------------------------------------------------------------------------
# write_all + functional shortcut
# ---------------------------------------------------------------------------


class TestWriteAll:
    def test_write_all_creates_every_artifact(self, tmp_path: Path) -> None:
        root = _seed_output_tree(tmp_path)
        gen = BatchDashboardGenerator(root)
        written = gen.write_all()
        expected = {
            "summary_csv",
            "metrics_json",
            "node_count_bar",
            "edge_count_bar",
            "score_distribution",
            "visual_completeness",
            "parser_status_distribution",
            "role_distribution",
            "confidence_distribution",
            "roundtrip_status",
            "failure_reasons",
            "run_gantt",
            "dashboard_md",
        }
        assert set(written) == expected
        for path in written.values():
            assert path.is_file()
            assert path.stat().st_size > 0

    def test_write_all_respects_custom_dest(self, tmp_path: Path) -> None:
        root = _seed_output_tree(tmp_path)
        dest = tmp_path / "elsewhere"
        gen = BatchDashboardGenerator(root)
        written = gen.write_all(dest)
        for path in written.values():
            assert path.parent == dest

    def test_functional_shortcut(self, tmp_path: Path) -> None:
        root = _seed_output_tree(tmp_path)
        written = write_batch_dashboard(root)
        assert (root / "dashboard" / "dashboard.md").is_file()
        assert "dashboard_md" in written


# ---------------------------------------------------------------------------
# Misc — round-trip via the actual script
# ---------------------------------------------------------------------------


class TestScriptEntryPoint:
    def test_script_module_runs_against_seeded_tree(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        root = _seed_output_tree(tmp_path)
        # Import the script via its on-disk path (it lives outside py/).
        import importlib.util

        script_path = (
            Path(__file__).resolve().parents[3]
            / "scripts"
            / "batch_dashboard.py"
        )
        if not script_path.is_file():
            pytest.skip(f"scripts/batch_dashboard.py not present at {script_path}")
        spec = importlib.util.spec_from_file_location("cogant_batch_dashboard", script_path)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        rc = mod.main(["--output-root", str(root), "--quiet"])
        captured = capsys.readouterr()
        assert rc == 0
        # stdout should list at least one written artifact
        assert "dashboard.md" in captured.out
        assert (root / "dashboard" / "summary.csv").is_file()

    def test_script_fails_on_missing_output_root(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import importlib.util

        script_path = (
            Path(__file__).resolve().parents[3]
            / "scripts"
            / "batch_dashboard.py"
        )
        if not script_path.is_file():
            pytest.skip(f"scripts/batch_dashboard.py not present at {script_path}")
        spec = importlib.util.spec_from_file_location("cogant_batch_dashboard", script_path)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        rc = mod.main(["--output-root", str(tmp_path / "absent"), "--quiet"])
        assert rc == 2


# ---------------------------------------------------------------------------
# Doc-friendly snapshot test
# ---------------------------------------------------------------------------


def test_dashboard_md_snapshot_shape(tmp_path: Path) -> None:
    """Cheap regression check that the rendered markdown keeps its shape.

    We only assert on top-of-file sections to avoid being brittle when
    the table widens.
    """
    root = _seed_output_tree(tmp_path)
    gen = BatchDashboardGenerator(root)
    md = gen.render_markdown_dashboard(gen.collect_target_metrics())
    head = "\n".join(md.splitlines()[:5])
    assert head.startswith("# COGANT batch dashboard")
    # The four bulleted headline points must all appear in the top block
    assert "Targets:" in md
    assert "Total program-graph nodes" in md
    # Mermaid section title is the expected one
    assert "## Visualisations" in textwrap.dedent(md)
