"""Benchmark: File discovery and ingestion via :class:`cogant.ingest.RepoIngester`.

Drives the public ingest API (``RepoIngester.ingest_local``) against
synthetic repositories created in pytest ``tmp_path`` so the benchmark
runs without network access. Two scenarios are exercised:

* ``test_ingest_discovery`` — flat repo with 1000 Python modules; baseline
  for file enumeration + manifest extraction throughput.
* ``test_ingest_filtering`` — same repo plus a ``node_modules/`` tree with
  100 entries; verifies the gitignore-aware enumerator excludes them.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from cogant.ingest import RepoIngester, RepoSnapshot

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    """Create a synthetic Python repository with 1000 modules under ``src/``."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Create 1000 Python files
    for i in range(1000):
        file_path = src_dir / f"module_{i}.py"
        file_path.write_text(f"# Module {i}\ndef func_{i}(): pass\n")

    return tmp_path


def test_ingest_discovery(benchmark: BenchmarkFixture, fixture_repo: Path) -> None:
    """Benchmark file discovery and manifest creation on a 1000-file repo."""
    ingester = RepoIngester()

    def ingest() -> RepoSnapshot:
        return ingester.ingest_local(fixture_repo, include_test_files=True)

    snapshot = benchmark(ingest)
    # The synthetic repo only contains 1000 .py files, so the snapshot
    # should report exactly that many Python files. Other languages may
    # appear if pytest writes anything else, so we count only python.
    py_files = [f for f in snapshot.files if f.language == "python"]
    assert len(py_files) == 1000


def test_ingest_filtering(benchmark: BenchmarkFixture, fixture_repo: Path) -> None:
    """Benchmark file enumeration when ``node_modules/`` is excluded.

    Adds a ``node_modules`` tree with 100 ``.py`` files (which the
    gitignore-aware enumerator excludes by default) and confirms none of
    those paths surface in the resulting :class:`RepoSnapshot`.
    """
    # Add a ``node_modules`` subtree that the enumerator should exclude.
    node_modules = fixture_repo / "node_modules"
    node_modules.mkdir()
    # Provide a .gitignore so the enumerator (which respects gitignore)
    # treats node_modules as excluded.
    (fixture_repo / ".gitignore").write_text("node_modules/\n")
    for i in range(100):
        (node_modules / f"pkg_{i}.py").write_text("# ignored\n")

    ingester = RepoIngester()

    def ingest_with_filter() -> RepoSnapshot:
        return ingester.ingest_local(fixture_repo, include_test_files=True)

    snapshot = benchmark(ingest_with_filter)
    # Should only include src/ files, not node_modules
    assert all("node_modules" not in str(f.path) for f in snapshot.files)
