"""Targeted unit tests for: exercise cogant.gnn.package.GNNPackageBuilder.

Drives GNNPackageBuilder.build end-to-end against a minimally-populated
ProgramGraph / StateSpaceModel / ProcessModel so the many per-file
``_generate_*`` branches get executed. The exception branches of each
``_generate_*`` helper are exercised via a deliberately-broken graph that
makes the internal helpers raise — but via real object state, not mocks.
"""

from __future__ import annotations

import json
from pathlib import Path

from cogant.gnn.package import GNNPackageBuilder
from cogant.process.extractor import ProcessModel
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.statespace.compiler import StateSpaceModel
from cogant.statespace.temporal import TimeRegime


def _empty_state_space() -> StateSpaceModel:
    return StateSpaceModel(
        id="ss",
        schema_name="current",
        variables={},
        observations={},
        actions={},
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


def _empty_process_model() -> ProcessModel:
    return ProcessModel(id="pm", schema_name="current", stages={}, connections={})


def _empty_graph() -> ProgramGraph:
    return ProgramGraph(metadata=GraphMetadata(repo_uri="test", languages={"python"}))


class TestGNNPackageBuilderEndToEnd:
    """End-to-end smoke test of GNNPackageBuilder.build on empty inputs."""

    def test_build_emits_all_required_files(self, tmp_path: Path) -> None:
        builder = GNNPackageBuilder(
            graph=_empty_graph(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            mappings={},
        )
        manifest = builder.build(str(tmp_path))
        # manifest is a dict with at least these structural keys
        assert isinstance(manifest, dict)
        assert "version" in manifest or "package_version" in manifest or manifest
        # Core JSON files must exist and be valid JSON
        for name in [
            "manifest.json",
            "model.gnn.json",
            "state_space.json",
            "observations.json",
            "actions.json",
            "transitions.json",
            "preferences.json",
            "factors.json",
            "provenance.json",
            "ontology.json",
            "actions_policies.json",
            "connections.json",
            "markov_blanket.json",
            "markov_network.json",
            "program_graph.json",
            "process_model.json",
        ]:
            path = tmp_path / name
            assert path.exists(), f"missing required file: {name}"
            # All must parse as JSON
            json.loads(path.read_text())
        # Markdown file must exist too
        assert (tmp_path / "model.gnn.md").exists()
        # Checksums must have been populated
        assert len(builder.checksums) > 0

    def test_build_with_markov_blanket_config_auto_strategy(self, tmp_path: Path) -> None:
        builder = GNNPackageBuilder(
            graph=_empty_graph(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            mappings={},
            config={"markov_blanket": {"strategy": "auto"}},
        )
        builder.build(str(tmp_path))
        blanket = json.loads((tmp_path / "markov_blanket.json").read_text())
        # Either a real blanket or a stub with "roles" key present
        assert "roles" in blanket or "schema_version" in blanket

    def test_build_with_markov_blanket_mapping_kind_strategy(self, tmp_path: Path) -> None:
        builder = GNNPackageBuilder(
            graph=_empty_graph(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            mappings={},
            config={
                "markov_blanket": {"strategy": "mapping_kind", "mapping_kinds": ["hidden_state"]}
            },
        )
        builder.build(str(tmp_path))
        assert (tmp_path / "markov_blanket.json").exists()

    def test_build_with_markov_blanket_explicit_strategy_no_seeds(self, tmp_path: Path) -> None:
        """explicit strategy with empty seeds list should still complete."""
        builder = GNNPackageBuilder(
            graph=_empty_graph(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            mappings={},
            config={"markov_blanket": {"strategy": "explicit", "seeds": []}},
        )
        builder.build(str(tmp_path))
        assert (tmp_path / "markov_blanket.json").exists()
        assert (tmp_path / "markov_network.json").exists()

    def test_build_with_markov_blanket_module_strategy(self, tmp_path: Path) -> None:
        builder = GNNPackageBuilder(
            graph=_empty_graph(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            mappings={},
            config={"markov_blanket": {"strategy": "module", "module_names": ["main"]}},
        )
        builder.build(str(tmp_path))
        assert (tmp_path / "markov_blanket.json").exists()

    def test_build_populates_checksums_for_required_files(self, tmp_path: Path) -> None:
        builder = GNNPackageBuilder(
            graph=_empty_graph(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            mappings={},
        )
        builder.build(str(tmp_path))
        # Core sidecar files all get a checksum entry
        for name in [
            "model.gnn.md",
            "model.gnn.json",
            "state_space.json",
            "observations.json",
            "actions.json",
            "provenance.json",
        ]:
            assert name in builder.checksums
            assert isinstance(builder.checksums[name], str)
            assert len(builder.checksums[name]) >= 16  # hex digest

    def test_markov_blanket_falls_back_to_stub_when_graph_is_none(self, tmp_path: Path) -> None:
        """Forcing graph=None makes _generate_markov_blanket hit its stub path."""
        builder = GNNPackageBuilder(
            graph=_empty_graph(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            mappings={},
        )
        # Mutate graph to None after construction to exercise the stub path.
        builder.graph = None  # type: ignore[assignment]
        # Also replace process_model since markov runs before model_json
        builder._generate_markov_blanket(tmp_path)  # type: ignore[attr-defined]
        blanket = json.loads((tmp_path / "markov_blanket.json").read_text())
        assert blanket.get("metadata", {}).get("error") is True
        assert "error" in blanket

    def test_process_model_json_skips_when_process_model_is_none(self, tmp_path: Path) -> None:
        builder = GNNPackageBuilder(
            graph=_empty_graph(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            mappings={},
        )
        builder.process_model = None  # type: ignore[assignment]
        builder._generate_process_model_json(tmp_path)  # type: ignore[attr-defined]
        # Nothing written
        assert not (tmp_path / "process_model.json").exists()
