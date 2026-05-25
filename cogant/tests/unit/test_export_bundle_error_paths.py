"""Coverage tests for cogant.export.bundle — targeted.

Targets uncovered branches in BundleExporter:
- export_zip (lines 295-327)
- export_with_provenance (lines 349-390)
- _compute_bundle_hash (394-395)
- Per-format exception catches (152-154, 174-176, 191-193, 204-206, 221-223)
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from cogant.export.bundle import BundleExporter
from cogant.process.extractor import ProcessConnection, ProcessModel, Stage
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.statespace.compiler import (
    Action,
    ObservationModality,
    StateSpaceModel,
    Transition,
)
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import StateVariable, StateVariableType

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _graph() -> ProgramGraph:
    meta = GraphMetadata(repo_uri="file:///tmp/repo")
    meta.languages = {"python"}
    g = ProgramGraph(metadata=meta)
    g.add_node(
        Node(
            id="f1",
            kind=NodeKind.FUNCTION,
            name="run",
            qualified_name="pkg.run",
            path="pkg/file.py",
        )
    )
    g.add_node(
        Node(
            id="f2",
            kind=NodeKind.FUNCTION,
            name="helper",
            qualified_name="pkg.helper",
            path="pkg/file.py",
        )
    )
    g.add_edge(
        Edge(id="e1", source_id="f1", target_id="f2", kind=EdgeKind.CALLS, weight=1.0)
    )
    return g


def _state_space() -> StateSpaceModel:
    return StateSpaceModel(
        id="m_zip",
        schema_name="zip_schema",
        variables={
            "v1": StateVariable(
                id="v1",
                name="busy",
                var_type=StateVariableType.BOOLEAN,
                node_id="f1",
            )
        },
        observations={
            "o1": ObservationModality(
                id="o1", name="beat", source_node_id="f1", modality_type="event"
            )
        },
        actions={"a1": Action(id="a1", name="run", controller_id="f1", effects=["v1"])},
        transitions={
            "t1": Transition(
                id="t1",
                source_state={"v1": "pre"},
                target_state={"v1": "post"},
                action_id="a1",
            )
        },
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


def _process() -> ProcessModel:
    return ProcessModel(
        id="pm_1",
        schema_name="zip_schema",
        stages={"s1": Stage(id="s1", name="ingest")},
        connections={
            "c1": ProcessConnection(
                id="c1",
                source_stage_id="s1",
                target_stage_id="s1",
                trigger="loop",
            )
        },
    )


def _make_exporter(out: Path) -> BundleExporter:
    return BundleExporter(
        program_graph=_graph(),
        state_space_model=_state_space(),
        process_model=_process(),
        semantic_mappings={},
        output_dir=out,
    )


# ---------------------------------------------------------------------------
# export_zip
# ---------------------------------------------------------------------------


def test_export_zip_creates_archive_with_all_formats(tmp_path: Path) -> None:
    """export_zip writes a real ZIP archive containing the bundle files."""
    out_dir = tmp_path / "bundle"
    zip_path = tmp_path / "archive.zip"
    exporter = _make_exporter(out_dir)

    written = exporter.export_zip(str(zip_path))

    assert written == str(zip_path)
    assert zip_path.exists()
    assert zip_path.stat().st_size > 0

    # Inspect archive contents
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
    assert "MANIFEST.json" in names
    assert "gnn.md" in names
    assert "gnn.json" in names
    assert "index.html" in names

    # Temp working directory must be cleaned up
    assert not (out_dir / ".temp_zip").exists()


def test_export_zip_creates_parent_directories(tmp_path: Path) -> None:
    """export_zip creates missing parent directories for the archive path."""
    out_dir = tmp_path / "bundle"
    zip_path = tmp_path / "deep" / "nested" / "out.zip"
    exporter = _make_exporter(out_dir)

    exporter.export_zip(str(zip_path))
    assert zip_path.exists()


# ---------------------------------------------------------------------------
# export_with_provenance
# ---------------------------------------------------------------------------


def test_export_with_provenance_writes_json_with_metadata(tmp_path: Path) -> None:
    """export_with_provenance writes a JSON file containing provenance + bundle."""
    out_dir = tmp_path / "bundle"
    out_dir.mkdir()
    exporter = _make_exporter(out_dir)

    bundle = {"matrices": {"A": [[1, 0], [0, 1]]}, "metadata": {"id": "test"}}
    config = {"target": "/tmp/repo", "skip_stages": ["dynamic"]}

    output_path = tmp_path / "prov.json"
    written = exporter.export_with_provenance(bundle, config, str(output_path))

    assert written == str(output_path)
    assert output_path.exists()

    payload = json.loads(output_path.read_text())
    assert "provenance" in payload
    assert "bundle" in payload
    prov = payload["provenance"]
    # Required provenance fields
    assert "timestamp" in prov
    assert "cogant_version" in prov
    assert prov["config"] == config
    assert prov["source_metadata"]["repo_uri"] == "file:///tmp/repo"
    assert prov["source_metadata"]["node_count"] == 2
    assert prov["source_metadata"]["edge_count"] == 1
    assert "python" in prov["source_metadata"]["languages"]
    # Hash is a SHA256 hex digest (64 chars)
    assert len(prov["content_hash"]) == 64


def test_export_with_provenance_creates_output_directory(tmp_path: Path) -> None:
    """export_with_provenance creates parent directories as needed."""
    out_dir = tmp_path / "bundle"
    out_dir.mkdir()
    exporter = _make_exporter(out_dir)

    target = tmp_path / "very" / "deep" / "out.json"
    written = exporter.export_with_provenance({}, {}, str(target))
    assert Path(written).exists()


def test_export_with_provenance_hash_is_deterministic(tmp_path: Path) -> None:
    """The same bundle produces the same content_hash."""
    out_dir = tmp_path / "bundle"
    out_dir.mkdir()
    exporter = _make_exporter(out_dir)

    bundle = {"a": 1, "b": [1, 2, 3]}
    config: dict = {}

    p1 = tmp_path / "a.json"
    p2 = tmp_path / "b.json"
    exporter.export_with_provenance(bundle, config, str(p1))
    exporter.export_with_provenance(bundle, config, str(p2))

    h1 = json.loads(p1.read_text())["provenance"]["content_hash"]
    h2 = json.loads(p2.read_text())["provenance"]["content_hash"]
    assert h1 == h2


def test_export_with_provenance_records_cogant_version(tmp_path: Path) -> None:
    """The cogant_version field is populated from the package __version__."""
    out_dir = tmp_path / "bundle"
    out_dir.mkdir()
    exporter = _make_exporter(out_dir)

    target = tmp_path / "ver.json"
    exporter.export_with_provenance({}, {}, str(target))
    payload = json.loads(target.read_text())
    # cogant has __version__ = "0.5.0" (or higher)
    assert payload["provenance"]["cogant_version"] != "unknown"


# ---------------------------------------------------------------------------
# _compute_bundle_hash
# ---------------------------------------------------------------------------


def test_compute_bundle_hash_returns_sha256_hex(tmp_path: Path) -> None:
    """_compute_bundle_hash produces a 64-char hex SHA256 digest."""
    exporter = _make_exporter(tmp_path)
    digest = exporter._compute_bundle_hash({"x": 1, "y": 2})
    assert len(digest) == 64
    # Deterministic: identical bundle yields the same hash
    assert digest == exporter._compute_bundle_hash({"y": 2, "x": 1})  # sort_keys=True


def test_compute_bundle_hash_changes_with_content(tmp_path: Path) -> None:
    """Different bundles yield different hashes."""
    exporter = _make_exporter(tmp_path)
    h1 = exporter._compute_bundle_hash({"x": 1})
    h2 = exporter._compute_bundle_hash({"x": 2})
    assert h1 != h2


# ---------------------------------------------------------------------------
# Per-format exception catches: provoke a failure and verify graceful return
# ---------------------------------------------------------------------------


class _BoomGraph:
    """Stand-in graph object that raises whenever attributes are introspected."""

    @property
    def nodes(self) -> dict:  # pragma: no cover - access raises
        raise RuntimeError("graph access boom")

    @property
    def edges(self) -> dict:  # pragma: no cover - access raises
        raise RuntimeError("graph access boom")

    @property
    def metadata(self) -> object:  # pragma: no cover - access raises
        raise RuntimeError("graph access boom")


def test_export_markdown_handles_internal_failure(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """_export_markdown catches inner exceptions and returns (None, '')."""
    # Use a regular file as output_dir so opening "gnn.md" inside it fails.
    blocker = tmp_path / "blocker"
    blocker.write_text("not a dir")
    exporter = BundleExporter(
        program_graph=_graph(),
        state_space_model=_state_space(),
        process_model=_process(),
        semantic_mappings={},
        output_dir=blocker,
    )
    with caplog.at_level("ERROR"):
        path, checksum = exporter._export_markdown()
    assert path is None
    assert checksum == ""
    assert any("Failed to export markdown" in rec.message for rec in caplog.records)


def test_export_json_handles_internal_failure(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """_export_json catches inner exceptions and returns (None, '')."""
    blocker = tmp_path / "json_blocker"
    blocker.write_text("not a dir")
    exporter = BundleExporter(
        program_graph=_graph(),
        state_space_model=_state_space(),
        process_model=_process(),
        semantic_mappings={},
        output_dir=blocker,
    )
    with caplog.at_level("ERROR"):
        path, checksum = exporter._export_json()
    assert path is None
    assert checksum == ""
    assert any("Failed to export JSON" in rec.message for rec in caplog.records)


def test_export_graphml_handles_internal_failure(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """_export_graphml catches inner exceptions and returns (None, '')."""
    blocker = tmp_path / "graphml_blocker"
    blocker.write_text("not a dir")
    exporter = BundleExporter(
        program_graph=_graph(),
        state_space_model=_state_space(),
        process_model=_process(),
        semantic_mappings={},
        output_dir=blocker,
    )
    with caplog.at_level("ERROR"):
        path, checksum = exporter._export_graphml()
    assert path is None
    assert checksum == ""
    assert any("Failed to export GraphML" in rec.message for rec in caplog.records)


def test_export_parquet_handles_internal_failure(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """_export_parquet catches inner exceptions and returns ([], {}).

    Pointing output_dir at an existing file makes ParquetExporter.export()
    raise on its own mkdir(parents=True, exist_ok=True), which propagates
    up to _export_parquet's exception catch.
    """
    blocker = tmp_path / "parquet_blocker"
    blocker.write_text("not a dir")
    exporter = BundleExporter(
        program_graph=_graph(),
        state_space_model=_state_space(),
        process_model=_process(),
        semantic_mappings={},
        output_dir=blocker,
    )
    with caplog.at_level("ERROR"):
        files, checksums = exporter._export_parquet()
    assert files == []
    assert checksums == {}
    assert any("Failed to export Parquet" in rec.message for rec in caplog.records)


def test_export_html_handles_internal_failure(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """_export_html catches inner exceptions and returns (None, '')."""
    # Create an exporter then point output_dir to a path that cannot be written:
    # use a regular file (so opening "index.html" inside it fails).
    blocker = tmp_path / "blocker"
    blocker.write_text("file in the way")
    exporter = BundleExporter(
        program_graph=_graph(),
        state_space_model=_state_space(),
        process_model=_process(),
        semantic_mappings={},
        output_dir=blocker,  # not a directory -> open will fail
    )
    with caplog.at_level("ERROR"):
        path, checksum = exporter._export_html()
    assert path is None
    assert checksum == ""
    assert any("Failed to export HTML" in rec.message for rec in caplog.records)
