"""coverage.py summaries stay honest under dynamic contexts and partial runs.

A coverage.py database stores one row per (file, context) and records only
*executed* lines, never the statement total. The ingester therefore has to
merge every context of a file into one entry and must not report a
coverage percentage the database cannot support.

Databases are written with coverage.py's own ``CoverageData`` API.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.dynamic.coverage import CoverageIngester

coverage = pytest.importorskip("coverage")


@pytest.mark.unit
def test_contexts_of_one_file_merge_into_a_single_entry(tmp_path: Path) -> None:
    """Lines measured under several test contexts are unioned per file."""
    mod = str(tmp_path / "mod.py")
    data = coverage.CoverageData(basename=str(tmp_path / ".coverage"))
    data.set_context("test_a")
    data.add_lines({mod: [1, 7, 8]})
    data.set_context("test_b")
    data.add_lines({mod: [2, 4]})
    data.set_context("test_c")
    data.add_lines({mod: [2, 3]})
    data.write()

    ingester = CoverageIngester()
    result = ingester.ingest_coverage_py(str(tmp_path / ".coverage"))

    assert [f["filename"] for f in result["files"]] == [mod]
    assert result["files"][0]["covered_lines"] == [1, 2, 3, 4, 7, 8]
    assert result["summary"]["covered_lines"] == 6
    file_cov = ingester.get_file_coverage(mod)
    assert file_cov is not None
    assert file_cov["covered_lines"] == [1, 2, 3, 4, 7, 8]


@pytest.mark.unit
def test_partial_run_does_not_claim_full_coverage(tmp_path: Path) -> None:
    """Without statement totals the percentage is unknown, not 100%."""
    mod = str(tmp_path / "mod.py")
    data = coverage.CoverageData(basename=str(tmp_path / ".coverage"))
    data.add_lines({mod: [1, 2, 5]})
    data.write()

    summary = CoverageIngester().ingest_coverage_py(str(tmp_path / ".coverage"))["summary"]

    assert summary["covered_lines"] == 3
    assert summary["total_lines"] is None
    assert summary["percent_covered"] is None
