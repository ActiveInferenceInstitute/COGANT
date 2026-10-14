"""The validator surfaces best-effort artifacts the builder could not produce.

When Markov blanket extraction fails, ``GNNPackageBuilder`` keeps the
package consumable but writes placeholder ``markov_blanket.json`` /
``markov_network.json`` payloads, records
``manifest.artifact_status.markov_blanket = "unavailable"`` and adds a
manifest warning. ``GNNValidator`` must not certify such a package as a
clean, full-score pass: the placeholder has to show up as a validation
warning (it is not publication-ready evidence).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from cogant.gnn.package import GNNPackageBuilder
from cogant.gnn.validator import GNNValidator
from cogant.process.extractor import ProcessModel
from cogant.schemas.core import Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.statespace.compiler import StateSpaceModel
from cogant.statespace.temporal import TimeRegime

pytestmark = pytest.mark.unit


def _build(tmp_path: Path, config: dict[str, Any] | None = None) -> Path:
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///t", languages={"python"}))
    graph.add_node(Node(id="m", kind=NodeKind.MODULE, name="m", qualified_name="m"))
    GNNPackageBuilder(
        graph=graph,
        state_space=StateSpaceModel(
            id="ss",
            schema_name="current",
            variables={},
            observations={},
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
        ),
        process_model=ProcessModel(id="pm", schema_name="current", stages={}, connections={}),
        mappings={},
        config=config,
    ).build(str(tmp_path))
    return tmp_path


def _artifact_warnings(result: Any) -> list[str]:
    return [w for w in result.warnings if "markov_blanket" in w]


def test_unavailable_markov_blanket_is_reported(tmp_path: Path) -> None:
    pkg = _build(tmp_path, config={"markov_blanket": {"strategy": "bogus_strategy"}})
    manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["artifact_status"] == {"markov_blanket": "unavailable"}

    result = GNNValidator().validate_package(str(pkg), upstream_gnn=False)

    (warning,) = _artifact_warnings(result)
    assert "unavailable" in warning
    assert "bogus_strategy" in warning
    assert result.details["artifact_status"] == {"markov_blanket": "unavailable"}
    assert result.score < 100.0


def test_stub_payload_is_reported_without_manifest_status(tmp_path: Path) -> None:
    pkg = _build(tmp_path, config={"markov_blanket": {"strategy": "bogus_strategy"}})
    manifest_path = pkg / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # A package written before artifact_status existed: only the stub knows.
    manifest.pop("artifact_status")
    manifest.pop("warnings")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = GNNValidator().validate_package(str(pkg), upstream_gnn=False)

    assert len(_artifact_warnings(result)) == 1
    assert result.details["artifact_status"] == {"markov_blanket": "unavailable"}


def test_healthy_markov_blanket_adds_no_artifact_warning(tmp_path: Path) -> None:
    pkg = _build(tmp_path)

    result = GNNValidator().validate_package(str(pkg), upstream_gnn=False)

    assert _artifact_warnings(result) == []
    assert result.details["artifact_status"] == {"markov_blanket": "success"}
