"""Read executed coverage lines while owning SQLite connection and cursor lifetimes."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing


def _decode_numbits(numbits_blob: bytes) -> list[int]:
    """Decode coverage.py's little-endian bitmap into executed line numbers."""
    return [
        byte_index * 8 + bit_index
        for byte_index, byte_value in enumerate(numbits_blob)
        for bit_index in range(8)
        if byte_value & (1 << bit_index)
    ]


def _read_sqlite_coverage(
    coverage_file: str, logger: logging.Logger
) -> list[tuple[str, set[int]]] | None:
    """Return per-file executed lines, or None when the file table is absent.

    SQLite errors propagate to the public ingester's existing error boundary.
    Both database resources close before any return or exception propagates.
    """
    executed_by_file: dict[str, set[int]] = {}
    with (
        closing(sqlite3.connect(coverage_file)) as connection,
        closing(connection.cursor()) as cursor,
    ):
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        if "file" not in tables:
            logger.warning(f"No 'file' table in {coverage_file}; may not be a coverage.py database")
            return None
        if "line_bits" not in tables and "arc" not in tables:
            logger.warning(
                f"Unrecognized coverage.py schema in {coverage_file}; available tables: {tables}"
            )
        if "line_bits" in tables:
            cursor.execute(
                "SELECT f.path, lb.numbits FROM file f "
                "JOIN line_bits lb ON f.id = lb.file_id ORDER BY f.id"
            )
            for filename, bitmap in cursor.fetchall():
                executed_by_file.setdefault(filename, set()).update(_decode_numbits(bitmap))
        if "arc" in tables:
            cursor.execute(
                "SELECT f.path, a.fromno, a.tono FROM file f "
                "JOIN arc a ON f.id = a.file_id ORDER BY f.id"
            )
            for filename, source, target in cursor.fetchall():
                executed_by_file.setdefault(filename, set()).update(
                    line for line in (source, target) if line > 0
                )
    return list(executed_by_file.items())
