"""Behavioral tests for cogant.dynamic.coverage.CoverageIngester.

Feeds the ingester real Cobertura XML and real coverage.py SQLite
databases and exercises every public method.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from cogant.dynamic.coverage import CoverageIngester, _decode_numbits

# --------------------------- _decode_numbits ---------------------------- #


def test_decode_numbits_single_byte_all_bits_set():
    """A byte of 0xFF covers lines 0..7."""
    assert _decode_numbits(bytes([0xFF])) == [0, 1, 2, 3, 4, 5, 6, 7]


def test_decode_numbits_multiple_bytes():
    """Each byte encodes 8 consecutive line numbers."""
    # 0x01 in byte 0 → line 0; 0x80 in byte 1 → line 15 (bit 7 of byte 1)
    assert _decode_numbits(bytes([0x01, 0x80])) == [0, 15]


def test_decode_numbits_empty_blob():
    assert _decode_numbits(b"") == []


# --------------------------- Cobertura XML ------------------------------ #


_COBERTURA_XML = """<?xml version="1.0" ?>
<coverage line-rate="0.75" branch-rate="0.5" lines-valid="8" lines-covered="6" branches-valid="2" branches-covered="1">
  <packages>
    <package name="pkg">
      <classes>
        <class name="mymod" filename="pkg/mymod.py" line-rate="0.75" branch-rate="0.5">
          <lines>
            <line number="1" hits="1"/>
            <line number="2" hits="3"/>
            <line number="3" hits="0"/>
            <line number="4" hits="2" branch="true" condition-coverage="50% (1/2)"/>
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""


def test_ingest_coverage_xml_parses_summary_and_classes(tmp_path):
    """Cobertura XML yields summary, file entries, and branch annotations."""
    path = tmp_path / "coverage.xml"
    path.write_text(_COBERTURA_XML)
    ingester = CoverageIngester()
    data = ingester.ingest_coverage_xml(str(path))

    assert data["format"] == "cobertura"
    assert data["summary"]["line_rate"] == 0.75
    assert data["summary"]["branch_rate"] == 0.5
    assert data["summary"]["lines_valid"] == 8
    assert len(data["files"]) == 1

    file = data["files"][0]
    assert file["filename"] == "pkg/mymod.py"
    assert file["covered_lines"] == [1, 2, 4]
    assert file["uncovered_lines"] == [3]
    # Branch row was preserved
    assert len(file["branches"]) == 1
    assert file["branches"][0]["line"] == 4


def test_ingest_coverage_xml_missing_file_returns_empty(tmp_path):
    data = CoverageIngester().ingest_coverage_xml(str(tmp_path / "nope.xml"))
    assert data["files"] == []
    assert data["summary"]["line_rate"] == 0.0


def test_ingest_coverage_xml_malformed_xml_returns_empty(tmp_path):
    path = tmp_path / "bad.xml"
    path.write_text("<coverage><broken")
    data = CoverageIngester().ingest_coverage_xml(str(path))
    assert data["files"] == []


# --------------------------- .coverage SQLite --------------------------- #


def _make_coverage_db_line_bits(tmp_path: Path) -> Path:
    """Create a coverage.py >= 5.x style database with line_bits."""
    path = tmp_path / ".coverage"
    conn = sqlite3.connect(str(path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE file (id INTEGER PRIMARY KEY, path TEXT)")
    cursor.execute("CREATE TABLE line_bits (file_id INTEGER, numbits BLOB)")
    cursor.execute("INSERT INTO file (id, path) VALUES (1, 'pkg/a.py')")
    # Bit-encoded: 0xFF -> lines 0..7
    cursor.execute("INSERT INTO line_bits (file_id, numbits) VALUES (1, ?)", (bytes([0xFF]),))
    conn.commit()
    conn.close()
    return path


def _make_coverage_db_line_table(tmp_path: Path) -> Path:
    """Create an older coverage.py schema with an explicit line table."""
    path = tmp_path / "old.coverage"
    conn = sqlite3.connect(str(path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE file (id INTEGER PRIMARY KEY, path TEXT)")
    cursor.execute("CREATE TABLE line (file_id INTEGER, lineno INTEGER)")
    cursor.execute("INSERT INTO file (id, path) VALUES (1, 'pkg/b.py')")
    for lineno in (10, 20, 30):
        cursor.execute("INSERT INTO line (file_id, lineno) VALUES (?, ?)", (1, lineno))
    conn.commit()
    conn.close()
    return path


def test_ingest_coverage_py_line_bits_schema(tmp_path):
    path = _make_coverage_db_line_bits(tmp_path)
    ingester = CoverageIngester()
    data = ingester.ingest_coverage_py(str(path))
    assert data["format"] == "coverage_py"
    assert len(data["files"]) == 1
    assert data["files"][0]["filename"] == "pkg/a.py"
    assert data["files"][0]["line_count"] == 8
    assert data["summary"]["covered_lines"] == 8
    assert data["summary"]["percent_covered"] == 100.0


def test_ingest_coverage_py_line_table_schema(tmp_path):
    path = _make_coverage_db_line_table(tmp_path)
    data = CoverageIngester().ingest_coverage_py(str(path))
    assert len(data["files"]) == 1
    assert data["files"][0]["covered_lines"] == [10, 20, 30]
    assert data["summary"]["covered_lines"] == 3


def test_ingest_coverage_py_missing_file_returns_empty(tmp_path):
    data = CoverageIngester().ingest_coverage_py(str(tmp_path / "nope.cov"))
    assert data["files"] == []
    assert data["summary"]["percent_covered"] == 0.0


def test_ingest_coverage_py_unknown_schema(tmp_path):
    """A SQLite file without a 'file' table is handled gracefully."""
    path = tmp_path / "weird.cov"
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE other (id INTEGER)")
    conn.commit()
    conn.close()
    data = CoverageIngester().ingest_coverage_py(str(path))
    assert data["files"] == []


def test_ingest_coverage_py_non_sqlite_file_returns_empty(tmp_path):
    """A file that isn't a SQLite database triggers the error path."""
    path = tmp_path / "fake.cov"
    path.write_text("not a db")
    data = CoverageIngester().ingest_coverage_py(str(path))
    assert data["files"] == []


# --------------------------- span mapping + queries -------------------- #


def test_map_coverage_to_spans_from_cobertura(tmp_path):
    """Covered and uncovered spans are produced; branch info propagates."""
    path = tmp_path / "coverage.xml"
    path.write_text(_COBERTURA_XML)
    ingester = CoverageIngester()
    ingester.ingest_coverage_xml(str(path))
    spans = ingester.map_coverage_to_spans()

    # 3 covered + 1 uncovered = 4 spans
    assert len(spans) == 4
    branch_spans = [s for s in spans if s.get("is_branch")]
    assert len(branch_spans) == 1
    assert branch_spans[0]["start_line"] == 4


def test_get_coverage_summary_returns_summary_dict(tmp_path):
    """get_coverage_summary returns the summary section as a dict."""
    path = tmp_path / "coverage.xml"
    path.write_text(_COBERTURA_XML)
    ingester = CoverageIngester()
    ingester.ingest_coverage_xml(str(path))
    summary = ingester.get_coverage_summary()
    assert summary["line_rate"] == 0.75
    assert summary["branches_valid"] == 2


def test_get_coverage_summary_empty_state():
    """Fresh ingester reports an empty summary."""
    assert CoverageIngester().get_coverage_summary() == {}


def test_get_file_coverage_found_and_missing(tmp_path):
    """get_file_coverage returns the matching file record or None."""
    path = tmp_path / "coverage.xml"
    path.write_text(_COBERTURA_XML)
    ingester = CoverageIngester()
    ingester.ingest_coverage_xml(str(path))
    assert ingester.get_file_coverage("pkg/mymod.py") is not None
    assert ingester.get_file_coverage("bogus/nope.py") is None
