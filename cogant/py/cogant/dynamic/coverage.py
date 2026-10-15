"""CoverageIngester: Parse coverage files and map to source."""

import logging
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _decode_numbits(numbits_blob: bytes) -> list[int]:
    """Decode a coverage.py numbits blob into a list of line numbers.

    The numbits format stores executed line numbers as a compressed
    bitmap. Each byte encodes 8 line numbers; bytes are stored in
    little-endian order.

    Args:
        numbits_blob: Raw bytes from the line_bits.numbits column.

    Returns:
        Sorted list of 1-based line numbers that were executed.
    """
    lines: list[int] = []
    for byte_index, byte_val in enumerate(numbits_blob):
        for bit_index in range(8):
            if byte_val & (1 << bit_index):
                lines.append(byte_index * 8 + bit_index)
    return sorted(lines)


class CoverageIngester:
    """
    Parse coverage data and map to source code spans.

    Supports:
      - coverage.py (.coverage files)
      - coverage.xml (Cobertura format)
      - Custom coverage formats
    """

    def __init__(self) -> None:
        """Initialize coverage ingester."""
        self.coverage_data: dict[str, Any] = {}

    def ingest_coverage_xml(self, xml_path: str) -> dict[str, Any]:
        """
        Parse Cobertura coverage.xml file.

        Args:
            xml_path: Path to coverage.xml file.

        Returns:
            Coverage data mapped to source spans.
        """
        logger.info(f"Parsing coverage.xml from {xml_path}")

        path = Path(xml_path)
        if not path.exists():
            logger.error(f"Coverage XML file not found: {xml_path}")
            self.coverage_data = {
                "type": "coverage",
                "format": "cobertura",
                "files": [],
                "summary": {
                    "line_rate": 0.0,
                    "branch_rate": 0.0,
                    "lines_valid": 0,
                    "lines_covered": 0,
                    "branches_valid": 0,
                    "branches_covered": 0,
                },
            }
            return self.coverage_data

        try:
            tree = ET.parse(xml_path)
        except ET.ParseError as exc:
            logger.error(f"Malformed XML in {xml_path}: {exc}")
            self.coverage_data = {
                "type": "coverage",
                "format": "cobertura",
                "files": [],
                "summary": {
                    "line_rate": 0.0,
                    "branch_rate": 0.0,
                    "lines_valid": 0,
                    "lines_covered": 0,
                    "branches_valid": 0,
                    "branches_covered": 0,
                },
            }
            return self.coverage_data

        root = tree.getroot()

        # Top-level summary attributes
        line_rate = float(root.get("line-rate", "0"))
        branch_rate = float(root.get("branch-rate", "0"))
        lines_valid = int(root.get("lines-valid", "0"))
        lines_covered = int(root.get("lines-covered", "0"))
        branches_valid = int(root.get("branches-valid", "0"))
        branches_covered = int(root.get("branches-covered", "0"))

        files: list[dict[str, Any]] = []

        for package_el in root.iter("package"):
            package_name = package_el.get("name", "")
            for class_el in package_el.iter("class"):
                filename = class_el.get("filename", "")
                class_name = class_el.get("name", "")
                class_line_rate = float(class_el.get("line-rate", "0"))
                class_branch_rate = float(class_el.get("branch-rate", "0"))

                covered_lines: list[int] = []
                uncovered_lines: list[int] = []
                branches: list[dict[str, Any]] = []

                lines_el = class_el.find("lines")
                if lines_el is not None:
                    for line_el in lines_el.findall("line"):
                        line_num = int(line_el.get("number", "0"))
                        hits = int(line_el.get("hits", "0"))
                        is_branch = line_el.get("branch", "false").lower() == "true"

                        if hits > 0:
                            covered_lines.append(line_num)
                        else:
                            uncovered_lines.append(line_num)

                        if is_branch:
                            condition_coverage = line_el.get("condition-coverage", "")
                            branches.append(
                                {
                                    "line": line_num,
                                    "hits": hits,
                                    "condition_coverage": condition_coverage,
                                }
                            )

                files.append(
                    {
                        "filename": filename,
                        "class_name": class_name,
                        "package": package_name,
                        "line_rate": class_line_rate,
                        "branch_rate": class_branch_rate,
                        "covered_lines": sorted(covered_lines),
                        "uncovered_lines": sorted(uncovered_lines),
                        "branches": branches,
                    }
                )

        logger.info(
            f"Parsed {len(files)} classes, line_rate={line_rate:.2%}, branch_rate={branch_rate:.2%}"
        )

        self.coverage_data = {
            "type": "coverage",
            "format": "cobertura",
            "files": files,
            "summary": {
                "line_rate": line_rate,
                "branch_rate": branch_rate,
                "lines_valid": lines_valid,
                "lines_covered": lines_covered,
                "branches_valid": branches_valid,
                "branches_covered": branches_covered,
            },
        }

        return self.coverage_data

    def ingest_coverage_py(self, coverage_file: str) -> dict[str, Any]:
        """
        Parse .coverage file from coverage.py.

        Line-mode (``line_bits``) and branch-mode (``arc``) schemas
        are supported. Rows recorded under different
        dynamic contexts are merged, so each file appears once with the
        union of its executed lines.

        Args:
            coverage_file: Path to .coverage file.

        Returns:
            Coverage data mapped to source spans. The database stores
            executed lines only, so ``summary["covered_lines"]`` counts
            distinct executed lines while ``summary["total_lines"]`` and
            ``summary["percent_covered"]`` are ``None`` (unknown) for a
            database that was read; they are ``0`` / ``0.0`` when the file
            is missing or unreadable.
        """
        logger.info(f"Parsing .coverage file from {coverage_file}")

        path = Path(coverage_file)
        if not path.exists():
            logger.error(f"Coverage file not found: {coverage_file}")
            self.coverage_data = {
                "type": "coverage",
                "format": "coverage_py",
                "files": [],
                "summary": {
                    "total_lines": 0,
                    "covered_lines": 0,
                    "percent_covered": 0.0,
                },
            }
            return self.coverage_data

        executed_by_file: dict[str, set[int]] = {}

        try:
            conn = sqlite3.connect(coverage_file)
            cursor = conn.cursor()

            # coverage.py SQLite schema: tables 'file', 'line_bits' and 'arc'
            # 'file' has columns: id, path
            # 'line_bits' has columns: file_id, context_id, numbits
            # numbits is a binary blob encoding which lines were executed.
            # 'arc' has columns: file_id, context_id, fromno, tono and is the
            # only populated table when coverage ran in branch mode
            # (``--branch`` / ``--cov-branch``); both tables always exist.

            # Check which tables exist to handle schema variations.
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

            if "file" not in tables:
                logger.warning(
                    f"No 'file' table in {coverage_file}; may not be a coverage.py database"
                )
                conn.close()
                self.coverage_data = {
                    "type": "coverage",
                    "format": "coverage_py",
                    "files": [],
                    "summary": {
                        "total_lines": 0,
                        "covered_lines": 0,
                        "percent_covered": 0.0,
                    },
                }
                return self.coverage_data

            # Rows are stored per (file, context): with dynamic contexts
            # (``--cov-context=test``) one file has many rows, so executed
            # lines are unioned per file before any entry is emitted.
            if "line_bits" in tables or "arc" in tables:
                # coverage.py >= 5.x schema with line_bits blob
                if "line_bits" in tables:
                    cursor.execute(
                        "SELECT f.path, lb.numbits FROM file f "
                        "JOIN line_bits lb ON f.id = lb.file_id ORDER BY f.id"
                    )
                    for filepath, numbits_blob in cursor.fetchall():
                        executed_by_file.setdefault(filepath, set()).update(
                            _decode_numbits(numbits_blob)
                        )
                if "arc" in tables:
                    # Branch-mode databases store executed arcs instead of
                    # line bitmaps. Every positive arc endpoint is an executed
                    # line; negative endpoints mark code-object entry/exit.
                    cursor.execute(
                        "SELECT f.path, a.fromno, a.tono FROM file f "
                        "JOIN arc a ON f.id = a.file_id ORDER BY f.id"
                    )
                    for filepath, fromno, tono in cursor.fetchall():
                        executed_by_file.setdefault(filepath, set()).update(
                            n for n in (fromno, tono) if n > 0
                        )
            else:
                logger.warning(
                    f"Unrecognized coverage.py schema in {coverage_file}; "
                    f"available tables: {tables}"
                )

            conn.close()
        except sqlite3.DatabaseError as exc:
            logger.error(f"Failed to read coverage database {coverage_file}: {exc}")
            self.coverage_data = {
                "type": "coverage",
                "format": "coverage_py",
                "files": [],
                "summary": {
                    "total_lines": 0,
                    "covered_lines": 0,
                    "percent_covered": 0.0,
                },
            }
            return self.coverage_data

        files: list[dict[str, Any]] = [
            {
                "filename": filepath,
                "covered_lines": sorted(executed),
                "uncovered_lines": [],
                "line_count": len(executed),
            }
            for filepath, executed in executed_by_file.items()
        ]
        covered_lines_total = sum(f["line_count"] for f in files)

        if not files:
            logger.warning(f"Coverage database {coverage_file} contains no executed lines")
        logger.info(f"Parsed {len(files)} files, {covered_lines_total} executed lines")

        # A coverage.py database records executed lines only; the statement
        # total (and hence a percentage) needs source analysis it does not
        # store, so both are reported as unknown rather than guessed.
        self.coverage_data = {
            "type": "coverage",
            "format": "coverage_py",
            "files": files,
            "summary": {
                "total_lines": None,
                "covered_lines": covered_lines_total,
                "percent_covered": None,
            },
        }

        return self.coverage_data

    def map_coverage_to_spans(self) -> list[dict[str, Any]]:
        """
        Map coverage data to source code spans.

        Returns:
            List of covered spans with metadata.
        """
        logger.debug("Mapping coverage to source spans")

        spans = []
        for file_data in self.coverage_data.get("files", []):
            filename = file_data.get("filename")

            # Build a set of branch lines for enrichment
            branch_lines: dict[int, dict[str, Any]] = {}
            for branch in file_data.get("branches", []):
                branch_lines[branch["line"]] = branch

            # Create span records for each covered line
            for line_num in file_data.get("covered_lines", []):
                span: dict[str, Any] = {
                    "file": filename,
                    "start_line": line_num,
                    "end_line": line_num,
                    "covered": True,
                }
                if line_num in branch_lines:
                    span["is_branch"] = True
                    span["branch_hits"] = branch_lines[line_num].get("hits", 0)
                    span["condition_coverage"] = branch_lines[line_num].get(
                        "condition_coverage", ""
                    )
                spans.append(span)

            # Also record uncovered lines
            for line_num in file_data.get("uncovered_lines", []):
                span = {
                    "file": filename,
                    "start_line": line_num,
                    "end_line": line_num,
                    "covered": False,
                }
                if line_num in branch_lines:
                    span["is_branch"] = True
                    span["branch_hits"] = 0
                    span["condition_coverage"] = branch_lines[line_num].get(
                        "condition_coverage", ""
                    )
                spans.append(span)

        return spans

    def get_coverage_summary(self) -> dict[str, Any]:
        """Get coverage summary statistics."""
        summary = self.coverage_data.get("summary", {})
        return dict(summary) if isinstance(summary, dict) else {}

    def get_file_coverage(self, filepath: str) -> dict[str, Any] | None:
        """Get coverage for specific file."""
        for file_data in self.coverage_data.get("files", []):
            if file_data.get("filename") == filepath:
                return dict(file_data) if isinstance(file_data, dict) else None
        return None
