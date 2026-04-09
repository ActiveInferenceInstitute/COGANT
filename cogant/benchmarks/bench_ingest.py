"""Benchmark: File discovery and ingestion."""

import pytest
from pathlib import Path
from cogant.ingest import Repository


@pytest.fixture
def fixture_repo(tmp_path):
    """Create a test repository with many files."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Create 1000 Python files
    for i in range(1000):
        file_path = src_dir / f"module_{i}.py"
        file_path.write_text(f"# Module {i}\ndef func_{i}(): pass\n")

    return tmp_path


def test_ingest_discovery(benchmark, fixture_repo):
    """Benchmark file discovery and manifest creation."""
    repo = Repository(path=fixture_repo)

    def ingest():
        return repo.create_manifest()

    manifest = benchmark(ingest)
    assert len(manifest.files) == 1000


def test_ingest_filtering(benchmark, fixture_repo):
    """Benchmark file filtering with excludes."""
    # Add some files to exclude
    (fixture_repo / "node_modules").mkdir()
    for i in range(100):
        (fixture_repo / "node_modules" / f"pkg_{i}.py").write_text("# ignored")

    repo = Repository(path=fixture_repo)

    def ingest_with_filter():
        config = {"exclude_patterns": ["node_modules"]}
        return repo.create_manifest()

    manifest = benchmark(ingest_with_filter)
    # Should only include src/ files, not node_modules
    assert all("node_modules" not in str(f.path) for f in manifest.files)
