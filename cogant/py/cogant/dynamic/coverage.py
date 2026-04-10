"""CoverageIngester: Parse coverage files and map to source."""

from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import sqlite3
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


def _decode_numbits(numbits_blob: bytes) -> List[int]:
    """Decode a coverage.py numbits blob into a list of line numbers.

    The numbits format stores executed line numbers as a compressed
    bitmap. Each byte encodes 8 line numbers; bytes are stored in
    little-endian order.

    Args:
        numbits_blob: Raw bytes from the line_bits.numbits column.

    Returns:
        Sorted list of 1-based line numbers that were executed.
    """
    lines: List[int] = []
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

    def __init__(self):
        """Initialize coverage ingester."""
        self.coverage_data: Dict[str, Any] = {}

    def ingest_coverage_xml(self, xml_path: str) -> Dict[str, Any]:
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

        files: List[Dict[str, Any]] = []

        for package_el in root.iter("package"):
            package_name = package_el.get("name", "")
            for class_el in package_el.iter("class"):
                filename = class_el.get("filename", "")
                class_name = class_el.get("name", "")
                class_line_rate = float(class_el.get("line-rate", "0"))
                class_branch_rate = float(class_el.get("branch-rate", "0"))

                covered_lines: List[int] = []
                uncovered_lines: List[int] = []
                branches: List[Dict[str, Any]] = []

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
                            condition_coverage = line_el.get(
                                "condition-coverage", ""
                            )
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
            f"Parsed {len(files)} classes, line_rate={line_rate:.2%}, "
            f"branch_rate={branch_rate:.2%}"
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

    def ingest_coverage_py(self, coverage_file: str) -> Dict[str, Any]:
        """
        Parse .coverage file from coverage.py.

        Args:
            coverage_file: Path to .coverage file.

        Returns:
            Coverage data mapped to source spans.
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

        files: List[Dict[str, Any]] = []
        total_lines = 0
        covered_lines_total = 0

        try:
            conn = sqlite3.connect(coverage_file)
            cursor = conn.cursor()

            # coverage.py SQLite schema: tables 'file' and 'line_bits'
            # 'file' has columns: id, path
            # 'line_bits' has columns: file_id, numbits
            # numbits is a binary blob encoding which lines were executed.

            # Check which tables exist to handle schema variations.
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = {row[0] for row in cursor.fetchall()}

            if "file" not in tables:
                logger.warning(
                    f"No 'file' table in {coverage_file}; "
                    "may not be a coverage.py database"
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

            if "line_bits" in tables:
                # coverage.py >= 5.x schema with line_bits blob
                cursor.execute(
                    "SELECT f.path, lb.numbits "
                    "FROM file f "
                    "JOIN line_bits lb ON f.id = lb.file_id"
                )
                for filepath, numbits_blob in cursor.fetchall():
                    line_numbers = _decode_numbits(numbits_blob)
                    file_covered = len(line_numbers)
                    covered_lines_total += file_covered
                    # We don't know total lines from coverage alone;
                    # count covered as a lower bound.
                    total_lines += file_covered
                    files.append(
                        {
                            "filename": filepath,
                            "covered_lines": sorted(line_numbers),
                            "uncovered_lines": [],
                            "line_count": file_covered,
                        }
                    )
            elif "line" in tables:
                # Older coverage.py schema with explicit line table
                cursor.execute("SELECT id, path FROM file")
                file_rows = cursor.fetchall()
                for file_id, filepath in file_rows:
                    cursor.execute(
                        "SELECT lineno FROM line WHERE file_id = ?",
                        (file_id,),
                    )
                    line_numbers = [row[0] for row in cursor.fetchall()]
                    file_covered = len(line_numbers)
                    covered_lines_total += file_covered
                    total_lines += file_covered
                    files.append(
                        {
                            "filename": filepath,
                            "covered_lines": sorted(line_numbers),
                            "uncovered_lines": [],
                            "line_count": file_covered,
                        }
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

        percent = (
            (covered_lines_total / total_lines * 100.0) if total_lines > 0 else 0.0
        )

        logger.info(
            f"Parsed {len(files)} files, {covered_lines_total}/{total_lines} "
            f"lines covered ({percent:.1f}%)"
        )

        self.coverage_data = {
            "type": "coverage",
            "format": "coverage_py",
            "files": files,
            "summary": {
                "total_lines": total_lines,
                "covered_lines": covered_lines_total,
                "percent_covered": percent,
            },
        }

        return self.coverage_data

    def map_coverage_to_spans(self) -> List[Dict[str, Any]]:
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
            branch_lines: Dict[int, Dict[str, Any]] = {}
            for branch in file_data.get("branches", []):
                branch_lines[branch["line"]] = branch

            # Create span records for each covered line
            for line_num in file_data.get("covered_lines", []):
                span: Dict[str, Any] = {
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

    def get_coverage_summary(self) -> Dict[str, Any]:
        """Get coverage summary statistics."""
        summary = self.coverage_data.get("summary", {})
        return dict(summary) if isinstance(summary, dict) else {}

    def get_file_coverage(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Get coverage for specific file."""
        for file_data in self.coverage_data.get("files", []):
            if file_data.get("filename") == filepath:
                return dict(file_data) if isinstance(file_data, dict) else None
        return None
