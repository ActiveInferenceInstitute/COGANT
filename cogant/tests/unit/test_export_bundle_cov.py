"""Behavioral tests for cogant.export.bundle.BundleExporter.

Drives end-to-end bundle export using real ProgramGraph, StateSpaceModel,
and ProcessModel fixtures on disk.
"""

from __future__ import annotations

import json
from pathlib import Path

from cogant.export.bundle import BundleExporter, BundleManifest
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

# --------------------------- fixtures ----------------------------------- #


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
    g.add_edge(Edge(id="e1", source_id="f1", target_id="f2", kind=EdgeKind.CALLS, weight=1.0))
    return g


def _state_space() -> StateSpaceModel:
    return StateSpaceModel(
        id="m_1",
        schema_name="test_schema",
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
        schema_name="test_schema",
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


# --------------------------- default full export ------------------------ #


def test_export_default_formats_writes_all_files(tmp_path):
    """Calling export() with default formats writes at least markdown/json/html
    and a MANIFEST.json pointing at everything that was produced.
    """
    out = tmp_path / "bundle"
    exporter = _make_exporter(out)
    result = exporter.export()

    assert result == out
    assert (out / "MANIFEST.json").exists()
    # Markdown + JSON + HTML should always be present (no optional deps).
    assert (out / "gnn.md").exists()
    assert (out / "gnn.json").exists()
    assert (out / "index.html").exists()

    manifest = json.loads((out / "MANIFEST.json").read_text())
    assert manifest["bundle_id"] == "bundle_m_1"
    assert manifest["schema_name"] == "test_schema"
    assert "metadata" in manifest
    assert manifest["metadata"]["node_count"] == 2
    assert manifest["metadata"]["edge_count"] == 1
    # Checksums for all required files exist
    assert "gnn.md" in manifest["checksums"]
    assert "index.html" in manifest["checksums"]


def test_export_subset_only_writes_requested_formats(tmp_path):
    """Passing a subset of formats only writes those files."""
    out = tmp_path / "only_md"
    _make_exporter(out).export(formats=["markdown"])
    assert (out / "gnn.md").exists()
    assert not (out / "gnn.json").exists()
    # Manifest is always written
    assert (out / "MANIFEST.json").exists()


def test_export_html_content_includes_schema_name(tmp_path):
    """The generated HTML names the schema and reports variable counts."""
    out = tmp_path / "html_only"
    _make_exporter(out).export(formats=["html"])
    html = (out / "index.html").read_text()
    assert "test_schema" in html
    assert "State Variables: 1" in html
    assert "Actions: 1" in html


# --------------------------- manifest helpers --------------------------- #


def test_create_manifest_and_to_dict_round_trip(tmp_path):
    """_create_manifest and _manifest_to_dict produce consistent metadata."""
    exp = _make_exporter(tmp_path)
    manifest = exp._create_manifest({"a.md": "x"}, {"a.md": "abcd1234"})
    assert isinstance(manifest, BundleManifest)
    d = exp._manifest_to_dict(manifest)
    assert d["schema_name"] == "test_schema"
    assert d["files"] == {"a.md": "x"}
    assert d["checksums"] == {"a.md": "abcd1234"}
    # Metadata carries the counts from the fixtures
    assert d["metadata"]["variable_count"] == 1
    assert d["metadata"]["stage_count"] == 1


# --------------------------- checksum ----------------------------------- #


def test_compute_checksum_returns_sha256_hex(tmp_path):
    """_compute_checksum produces a deterministic 64-char SHA256 hex digest."""
    exp = _make_exporter(tmp_path)
    p = tmp_path / "blob.txt"
    p.write_bytes(b"hello world")
    digest = exp._compute_checksum(p)
    # SHA256 hex is 64 characters
    assert len(digest) == 64
    # sha256("hello world") is a well-known value
    assert digest == ("b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9")


# --------------------------- HTML generation --------------------------- #


def test_generate_html_contains_summary(tmp_path):
    """_generate_html returns a standalone HTML document."""
    html = _make_exporter(tmp_path)._generate_html()
    assert "<!DOCTYPE html>" in html
    assert "test_schema" in html
    assert "Observations: 1" in html
