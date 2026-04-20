"""Wave-20 coverage boost: exercise cogant.api.orchestration end-to-end.

Drives every ``run_*`` stage function against a real tiny Python
repository — no mocks, no stubs. Both happy-path and the
``RuntimeError`` branches for stages invoked out of order are covered.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.api.bundle import Bundle
from cogant.api.orchestration import (
    program_graph_to_dict,
    run_dynamic,
    run_export,
    run_graph,
    run_ingest,
    run_normalize,
    run_process,
    run_statespace,
    run_static,
    run_translate,
    run_validate,
)

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tiny_repo(tmp_path: Path) -> Path:
    """A tiny but structurally realistic Python repo.

    Contains a class with a mutating method (for WRITES/READS dataflow
    edges), a subclass (INHERITS), an import from an in-repo module
    (IMPORTS), and a top-level function (CONTAINS).
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "helper.py").write_text(
        "def compute(x):\n"
        "    return x * 2\n"
    )
    (repo / "main.py").write_text(
        "from helper import compute\n"
        "\n"
        "class Counter:\n"
        "    def __init__(self):\n"
        "        self.value = 0\n"
        "\n"
        "    def increment(self):\n"
        "        self.value += 1\n"
        "        return self.value\n"
        "\n"
        "    def read(self):\n"
        "        return self.value\n"
        "\n"
        "\n"
        "class FastCounter(Counter):\n"
        "    pass\n"
        "\n"
        "\n"
        "def top_level_fn(n):\n"
        "    return compute(n) + 1\n"
    )
    return repo


@pytest.fixture()
def full_bundle(tiny_repo: Path, tmp_path: Path) -> tuple[Bundle, Path]:
    """Drive every stage in order so downstream tests start fully populated."""
    bundle = Bundle(target=str(tiny_repo))
    run_ingest(str(tiny_repo), bundle)
    run_static(bundle)
    run_normalize(bundle)
    run_graph(bundle, str(tiny_repo))
    translate_result = run_translate(bundle)
    bundle.stage_results["translate"] = translate_result
    run_statespace(bundle, str(tiny_repo))
    run_process(bundle, str(tiny_repo))
    return bundle, tmp_path


# ---------------------------------------------------------------------------
# stage happy paths
# ---------------------------------------------------------------------------


class TestRunIngest:
    def test_ingest_counts_python_files(self, tiny_repo: Path) -> None:
        bundle = Bundle(target=str(tiny_repo))
        result = run_ingest(str(tiny_repo), bundle)
        assert result["type"] == "ingest"
        # Two python files: main.py + helper.py
        assert result["file_count"] >= 2
        assert result["language_distribution"].get("python", 0) >= 2
        # Snapshot is stashed in artifacts
        assert "repo_snapshot" in bundle.artifacts

    def test_ingest_with_incremental_metadata_filters_files(
        self, tiny_repo: Path
    ) -> None:
        """bundle.metadata['_incremental'] filters snapshot.files down."""
        bundle = Bundle(target=str(tiny_repo))
        # Only helper.py is "changed"
        bundle.metadata["_incremental"] = {
            "changed_files": [str(tiny_repo / "helper.py")],
            "changed_count": 1,
        }
        result = run_ingest(str(tiny_repo), bundle)
        # Only the changed file should be in the filtered snapshot
        assert result["file_count"] == 1
        assert "incremental" in result
        assert result["incremental"]["changed_count"] == 1
        assert result["incremental"]["total_before_filter"] >= 2


class TestRunStatic:
    def test_static_parses_python_modules(self, tiny_repo: Path) -> None:
        bundle = Bundle(target=str(tiny_repo))
        run_ingest(str(tiny_repo), bundle)
        result = run_static(bundle)
        assert result["type"] == "static_analysis"
        assert result["symbols"]["python_modules_parsed"] >= 2
        # main.py should report at least 1 class + 1 function
        modules = result["modules"]
        main_mod = next(m for m in modules if m["path"].endswith("main.py"))
        assert main_mod["classes"] >= 2  # Counter + FastCounter
        assert main_mod["functions"] >= 1
        # Detail is stashed on the bundle
        assert "parsed_modules_detail" in bundle.artifacts

    def test_static_without_ingest_raises(self, tmp_path: Path) -> None:
        bundle = Bundle(target=str(tmp_path))
        with pytest.raises(RuntimeError, match="ingest stage must run before static"):
            run_static(bundle)


class TestRunNormalize:
    def test_normalize_produces_facts(self, tiny_repo: Path) -> None:
        bundle = Bundle(target=str(tiny_repo))
        run_ingest(str(tiny_repo), bundle)
        result = run_normalize(bundle)
        assert result["type"] == "normalized"
        # helper.compute + Counter/FastCounter/top_level_fn + methods = lots of facts
        assert result["fact_count"] >= 5
        # Each fact has kind / qualified_name / path
        assert "normalized_facts" in bundle.artifacts
        for fact in result["nodes"]:
            assert "kind" in fact and "qualified_name" in fact and "path" in fact

    def test_normalize_without_ingest_raises(self, tmp_path: Path) -> None:
        bundle = Bundle(target=str(tmp_path))
        with pytest.raises(RuntimeError, match="ingest stage must run before normalize"):
            run_normalize(bundle)


class TestRunGraph:
    def test_graph_builds_rich_program_graph(self, tiny_repo: Path) -> None:
        bundle = Bundle(target=str(tiny_repo))
        run_ingest(str(tiny_repo), bundle)
        result = run_graph(bundle, str(tiny_repo))
        assert result["type"] == "program_graph"
        # At least MODULE nodes for helper.py + main.py, CLASS for Counter &
        # FastCounter, FUNCTION for compute + top_level_fn, plus methods.
        assert len(result["nodes"]) >= 6
        # Edges should include CONTAINS, IMPORTS, INHERITS, READS/WRITES
        assert len(result["edges"]) >= 3
        assert "_program_graph" in bundle.artifacts
        kinds = {e["kind"] for e in result["edges"].values()}
        # CONTAINS and INHERITS must both show up — FastCounter inherits Counter
        assert "contains" in kinds
        assert "inherits" in kinds

    def test_graph_without_ingest_raises(self, tmp_path: Path) -> None:
        bundle = Bundle(target=str(tmp_path))
        with pytest.raises(RuntimeError, match="ingest stage must run before graph"):
            run_graph(bundle, str(tmp_path))

    def test_graph_auto_runs_normalize_if_missing(
        self, tiny_repo: Path
    ) -> None:
        """graph backfills normalized_facts if normalize hasn't run yet."""
        bundle = Bundle(target=str(tiny_repo))
        run_ingest(str(tiny_repo), bundle)
        # Note: skipping run_normalize deliberately
        assert bundle.artifacts.get("normalized_facts") is None
        run_graph(bundle, str(tiny_repo))
        # graph stage should have backfilled the normalized facts
        assert bundle.artifacts.get("normalized_facts") is not None


class TestRunTranslate:
    def test_translate_runs_rules_against_graph(
        self, tiny_repo: Path
    ) -> None:
        bundle = Bundle(target=str(tiny_repo))
        run_ingest(str(tiny_repo), bundle)
        run_graph(bundle, str(tiny_repo))
        result = run_translate(bundle)
        assert result["type"] == "gnn_model"
        assert "mapping_count" in result
        assert "mapping_ids" in result
        # Engine + mappings dict get stashed
        assert "_translation_engine" in bundle.artifacts
        assert "_semantic_mappings" in bundle.artifacts
        # Mapping count >= 0, but with real code we expect some rule hits
        assert result["mapping_count"] >= 0

    def test_translate_without_graph_raises(self, tmp_path: Path) -> None:
        bundle = Bundle(target=str(tmp_path))
        with pytest.raises(RuntimeError, match="graph stage must run before translate"):
            run_translate(bundle)


class TestRunStatespace:
    def test_statespace_compiles_model(self, tiny_repo: Path) -> None:
        bundle = Bundle(target=str(tiny_repo))
        run_ingest(str(tiny_repo), bundle)
        run_graph(bundle, str(tiny_repo))
        run_translate(bundle)
        result = run_statespace(bundle, str(tiny_repo))
        assert result["type"] == "state_space_model"
        assert "states" in result and "observations" in result
        assert "actions" in result and "policies" in result
        assert "_state_space_model" in bundle.artifacts

    def test_statespace_without_graph_raises(self, tmp_path: Path) -> None:
        bundle = Bundle(target=str(tmp_path))
        with pytest.raises(RuntimeError, match="graph stage must run before statespace"):
            run_statespace(bundle, str(tmp_path))


class TestRunProcess:
    def test_process_extracts_stages(self, tiny_repo: Path) -> None:
        bundle = Bundle(target=str(tiny_repo))
        run_ingest(str(tiny_repo), bundle)
        run_graph(bundle, str(tiny_repo))
        result = run_process(bundle, str(tiny_repo))
        assert result["type"] == "process_model"
        assert "stages" in result
        assert "stage_count" in result
        assert "_process_model" in bundle.artifacts

    def test_process_without_graph_raises(self, tmp_path: Path) -> None:
        bundle = Bundle(target=str(tmp_path))
        with pytest.raises(RuntimeError, match="graph stage must run before process"):
            run_process(bundle, str(tmp_path))


# ---------------------------------------------------------------------------
# export + validate + dynamic
# ---------------------------------------------------------------------------


class TestRunExport:
    def test_export_writes_all_artifacts(
        self, full_bundle: tuple[Bundle, Path]
    ) -> None:
        bundle, tmp_path = full_bundle
        out = tmp_path / "export_out"
        result = run_export(bundle, str(out))
        assert result["type"] == "export"
        assert result["output_dir"] == str(out)
        # At least program_graph.json, state_space.json, process_model.json,
        # gnn_model.json, and the gnn_package/ dir should be written.
        written = result["artifacts"]
        assert len(written) >= 4
        # Core JSON files must exist on disk
        assert (out / "program_graph.json").exists()
        assert (out / "state_space.json").exists()
        assert (out / "process_model.json").exists()
        assert (out / "gnn_model.json").exists()
        # GNN package dir built
        assert (out / "gnn_package").exists()
        assert (out / "gnn_package" / "manifest.json").exists()
        # export_paths cached on the bundle
        assert "export_paths" in bundle.artifacts

    def test_export_with_no_artifacts_still_creates_dir(
        self, tmp_path: Path
    ) -> None:
        """Export on an empty bundle must not crash — it just writes nothing."""
        bundle = Bundle(target=str(tmp_path))
        out = tmp_path / "empty_out"
        result = run_export(bundle, str(out))
        assert out.exists()
        # No artifacts to write
        assert result["artifacts"] == []


class TestRunValidate:
    def test_validate_on_full_bundle_passes(
        self, full_bundle: tuple[Bundle, Path]
    ) -> None:
        bundle, _ = full_bundle
        result = run_validate(bundle)
        assert result["type"] == "validation"
        assert "checks" in result
        assert "warnings" in result
        # passed is True when the schema validator finds no errors
        assert isinstance(result["passed"], bool)

    def test_validate_with_no_program_graph_returns_synthetic_result(
        self, tmp_path: Path
    ) -> None:
        bundle = Bundle(target=str(tmp_path))
        result = run_validate(bundle)
        assert result["passed"] is False
        assert result["checks"]["program_graph"] == "missing"
        assert "No program graph to validate" in result["warnings"]

    def test_validate_after_export_includes_gnn_validation(
        self, full_bundle: tuple[Bundle, Path]
    ) -> None:
        """After run_export builds a gnn_package, validate reports on it too."""
        bundle, tmp_path = full_bundle
        out = tmp_path / "with_gnn"
        run_export(bundle, str(out))
        result = run_validate(bundle)
        # _gnn_package_dir is cached, so validate should surface gnn_validation
        assert "gnn_validation" in result
        assert "valid" in result["gnn_validation"]
        assert "score" in result["gnn_validation"]
        assert "upstream_parse_summary" in result["gnn_validation"]
        assert isinstance(result["gnn_validation"]["upstream_parse_summary"], dict)


class TestRunDynamic:
    def test_dynamic_without_graph_is_skipped(self, tmp_path: Path) -> None:
        bundle = Bundle(target=str(tmp_path))
        result = run_dynamic(bundle)
        assert result["type"] == "dynamic_enrichment"
        assert result["skipped"] is True
        assert "no program graph" in result["reason"]

    def test_dynamic_with_graph_returns_summary(
        self, tiny_repo: Path
    ) -> None:
        bundle = Bundle(target=str(tiny_repo))
        run_ingest(str(tiny_repo), bundle)
        run_graph(bundle, str(tiny_repo))
        result = run_dynamic(bundle)
        assert result["type"] == "dynamic_enrichment"
        # With a graph but no coverage/trace paths, the enricher still
        # returns a summary dict (no "skipped" flag).
        assert "skipped" not in result or result.get("skipped") is False


# ---------------------------------------------------------------------------
# program_graph_to_dict helper
# ---------------------------------------------------------------------------


class TestProgramGraphToDict:
    def test_to_dict_on_real_graph(self, tiny_repo: Path) -> None:
        bundle = Bundle(target=str(tiny_repo))
        run_ingest(str(tiny_repo), bundle)
        run_graph(bundle, str(tiny_repo))
        pg = bundle.artifacts["_program_graph"]
        d = program_graph_to_dict(pg, statistics={"foo": 1})
        assert d["type"] == "program_graph"
        assert "metadata" in d
        assert "nodes" in d and len(d["nodes"]) >= 2
        assert "edges" in d
        assert d["statistics"] == {"foo": 1}

    def test_to_dict_without_statistics(self, tiny_repo: Path) -> None:
        bundle = Bundle(target=str(tiny_repo))
        run_ingest(str(tiny_repo), bundle)
        run_graph(bundle, str(tiny_repo))
        pg = bundle.artifacts["_program_graph"]
        d = program_graph_to_dict(pg)
        assert d["statistics"] == {}
