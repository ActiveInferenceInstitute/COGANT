"""Real SQLite error paths must not leave connection finalization to garbage collection."""

from __future__ import annotations

import gc
import sqlite3
import sys
import warnings
from contextlib import closing
from pathlib import Path

import pytest

from cogant.dynamic.coverage import CoverageIngester


@pytest.mark.skipif(
    sys.version_info < (3, 13), reason="SQLite resource warnings require Python 3.13+"
)
@pytest.mark.parametrize("invalid_database", [True, False])
def test_failed_database_read_closes_connection(tmp_path: Path, invalid_database: bool) -> None:
    # Given: either unreadable SQLite bytes or a valid database with an invalid schema.
    path = tmp_path / "invalid.coverage"
    if invalid_database:
        path.write_bytes(b"not a SQLite database")
    else:
        with closing(sqlite3.connect(path)) as connection:
            connection.execute("CREATE TABLE file (wrong_column TEXT)")
            connection.execute("CREATE TABLE line_bits (file_id INTEGER, numbits BLOB)")
            connection.commit()
    gc.collect()
    # When: the public ingester handles a real SQLite read error.
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", ResourceWarning)
        result = CoverageIngester().ingest_coverage_py(str(path))
        gc.collect()
    # Then: its existing empty result is retained without leaking an open connection.
    assert result["files"] == []
    assert not [warning for warning in captured if issubclass(warning.category, ResourceWarning)]
