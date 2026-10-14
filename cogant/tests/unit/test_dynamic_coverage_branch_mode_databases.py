"""coverage.py databases written in branch mode yield executed lines.

With ``--branch`` (or ``branch = true`` / ``--cov-branch``) coverage.py
records executed *arcs* in the ``arc`` table and leaves ``line_bits``
empty. Both tables always exist in the schema, so the ingester has to
derive executed lines from the arcs instead of silently returning no
files.

The databases here are written by coverage.py's own ``CoverageData``
API, so the schema is the real one rather than a hand-built imitation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.dynamic.coverage import CoverageIngester

coverage = pytest.importorskip("coverage")


def _write_branch_db(path: Path, arcs: dict[str, list[tuple[int, int]]]) -> Path:
    data = coverage.CoverageData(basename=str(path))
    data.add_arcs(arcs)
    data.write()
    return path


@pytest.mark.unit
def test_branch_mode_database_reports_lines_from_arcs(tmp_path: Path) -> None:
    """Executed lines come from arc endpoints; negative entry/exit markers are dropped."""
    mod = str(tmp_path / "pkg" / "mod.py")
    db = _write_branch_db(
        tmp_path / ".coverage",
        {mod: [(-1, 1), (1, 2), (2, 5), (5, 6), (6, -1)]},
    )

    data = CoverageIngester().ingest_coverage_py(str(db))

    assert [f["filename"] for f in data["files"]] == [mod]
    assert data["files"][0]["covered_lines"] == [1, 2, 5, 6]
    assert data["summary"]["covered_lines"] == 4


@pytest.mark.unit
def test_branch_mode_database_produces_spans_for_enrichment(tmp_path: Path) -> None:
    """Spans derived from arcs are available to graph enrichment."""
    mod = str(tmp_path / "mod.py")
    db = _write_branch_db(tmp_path / ".coverage", {mod: [(-1, 3), (3, 4), (4, -3)]})

    ingester = CoverageIngester()
    ingester.ingest_coverage_py(str(db))
    spans = ingester.map_coverage_to_spans()

    assert sorted(span["start_line"] for span in spans) == [3, 4]
    assert all(span["covered"] for span in spans)
