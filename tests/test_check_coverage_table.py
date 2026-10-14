"""Regression tests for generated manuscript table drift checks."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "check_coverage_table.py"

spec = importlib.util.spec_from_file_location("check_coverage_table", MODULE_PATH)
assert spec is not None
check_coverage_table = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(check_coverage_table)


def _write_metrics_fixture(tmp_path: Path, *, elapsed: str = "1.23") -> tuple[Path, Path]:
    manuscript_dir = tmp_path / "manuscript"
    package_root = tmp_path / "cogant"
    (package_root / "evaluation" / "figures").mkdir(parents=True)
    manuscript_dir.mkdir()
    (package_root / "evaluation" / "figures" / "metrics.json").write_text(
        json.dumps(
            {
                "calculator": {
                    "files": 1,
                    "loc": 120,
                    "nodes": 12,
                    "edges": 25,
                    "mappings_total": 11,
                    "state_variables": 1,
                    "observations": 3,
                    "actions": 6,
                    "transitions": 6,
                    "gnn_sections": 31,
                    "gnn_score": 100.0,
                    "elapsed_s": 1.23,
                    "nodes_by_kind": {"MODULE": 1, "CLASS": 1, "METHOD": 10},
                    "edges_by_kind": {"CONTAINS": 11, "WRITES": 5, "READS": 9},
                    "policies": 1,
                    "gnn_package_files": 27,
                    "gnn_errors": 0,
                    "gnn_warnings": 0,
                }
            }
        ),
        encoding="utf-8",
    )
    (manuscript_dir / "06_03_performance_and_fixture_metrics.md").write_text(
        "\n".join(
            [
                "| Fixture | Files | LOC | Nodes | Edges | Mappings | State vars | Obs | Actions | Transitions | GNN sections | GNN score | Wall-clock (s) |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
                f"| `calculator` | 1 | 120 | 12 | 25 | 11 | 1 | 3 | 6 | 6 | 31 | 100.0 | {elapsed} |",
                ": Repository-level pipeline metrics. {#tbl:repo-pipeline-metrics}",
                "| Fixture | MODULE | CLASS | METHOD | FUNCTION | CONTAINS | WRITES | READS | CALLS | IMPORTS | INHERITS |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
                "| `calculator` | 1 | 1 | 10 | --- | 11 | 5 | 9 | --- | --- | --- |",
                ": Program graph composition by fixture. {#tbl:fixture-graph-metrics}",
                "| Fixture | State variables | Observations | Actions | Transitions | Policies |",
                "|---|---:|---:|---:|---:|---:|",
                "| `calculator` | 1 | 3 | 6 | 6 | 1 |",
                ": State-space compilation outputs. {#tbl:state-space-compilation}",
                "| Fixture | `gnn_package/` files | Validation errors | Validation warnings |",
                "|---|---:|---:|---:|",
                "| `calculator` | 27 | 0 | 0 |",
                ": Output artifacts per run. {#tbl:output-artifacts-per-run}",
            ]
        ),
        encoding="utf-8",
    )
    return manuscript_dir, package_root


def test_metric_json_backed_tables_detect_drift(tmp_path: Path) -> None:
    manuscript_dir, package_root = _write_metrics_fixture(tmp_path, elapsed="9.99")

    findings = check_coverage_table._check_metric_tables(manuscript_dir, package_root)

    assert any("wall_clock_s" in finding for finding in findings)


def test_metric_json_backed_tables_accept_matching_values(tmp_path: Path) -> None:
    manuscript_dir, package_root = _write_metrics_fixture(tmp_path)

    assert check_coverage_table._check_metric_tables(manuscript_dir, package_root) == []


def _write_benchmark_fixture(
    tmp_path: Path, *, median_cell: str, metrics_yaml: bool = True
) -> tuple[Path, Path]:
    manuscript = tmp_path / "06_04_tests_mutation_and_benchmarks.md"
    package_root = tmp_path / "cogant"
    results = package_root / "benchmarks" / "results"
    results.mkdir(parents=True)

    def _suite(median: float) -> str:
        return json.dumps(
            {
                "fixtures": {
                    "calculator": {
                        "wall_ms": {"median": median, "p95": 35.47},
                        "graph": {"nodes": 12, "edges": 25},
                        "mappings_total": 11,
                        "memory_mb": {"peak_delta_median": 0.22},
                    }
                }
            }
        )

    (results / "suite_20260423.json").write_text(_suite(35.34), encoding="utf-8")
    # A newer sidecar that METRICS.yaml does not name must not be compared.
    (results / "suite_20991231.json").write_text(_suite(500.0), encoding="utf-8")
    if metrics_yaml:
        (package_root / "evaluation").mkdir(parents=True)
        (package_root / "evaluation" / "METRICS.yaml").write_text(
            "benchmark:\n  benchmark_suite_file: suite_20260423.md\n",
            encoding="utf-8",
        )
    manuscript.write_text(
        "\n".join(
            [
                "| Fixture | Wall-clock median (ms) | Wall-clock p95 (ms) | Nodes | Edges | Mappings | Peak memory (MB) |",
                "|---|---:|---:|---:|---:|---:|---:|",
                f"| `calculator` | {median_cell} | 35 | 12 | 25 | 11 | 0.2 |",
                ": Benchmark suite results. {#tbl:benchmark-suite-results}",
            ]
        ),
        encoding="utf-8",
    )
    return manuscript, package_root


def test_benchmark_json_backed_table_detects_drift(tmp_path: Path) -> None:
    manuscript, package_root = _write_benchmark_fixture(tmp_path, median_cell="99")

    findings = check_coverage_table._check_benchmark_table(manuscript, package_root)

    assert any("wall_median_ms" in finding for finding in findings)


def test_benchmark_table_is_compared_to_the_sidecar_named_in_metrics(tmp_path: Path) -> None:
    manuscript, package_root = _write_benchmark_fixture(tmp_path, median_cell="35")

    assert check_coverage_table._check_benchmark_table(manuscript, package_root) == []


def test_benchmark_table_check_fails_loudly_without_metrics_yaml(tmp_path: Path) -> None:
    manuscript, package_root = _write_benchmark_fixture(
        tmp_path, median_cell="35", metrics_yaml=False
    )

    with pytest.raises(SystemExit, match="METRICS.yaml missing"):
        check_coverage_table._check_benchmark_table(manuscript, package_root)
