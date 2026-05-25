#!/usr/bin/env python3
"""Targeted branch tests — api/orchestration.py deeper stage runners.

Covers:
- run_graph: empty dir, with Python file, raises without snapshot
- run_translate: raises without graph, with empty graph
- run_statespace: raises without graph, with empty graph
- run_process: raises without graph, with empty graph
- _default_translation_engine: importable and returns TranslationEngine
"""

import pytest

pytestmark = pytest.mark.unit


def _make_bundle(tmp_path):
    from cogant.api.bundle import Bundle

    return Bundle(target=str(tmp_path))


def _run_ingest_static_graph(tmp_path, bundle=None):
    """Run ingest + static + graph chain, return bundle."""
    from cogant.api.orchestration import run_graph, run_ingest, run_static

    if bundle is None:
        bundle = _make_bundle(tmp_path)
    run_ingest(str(tmp_path), bundle)
    run_static(bundle)
    run_graph(bundle, str(tmp_path))
    return bundle


# ---------------------------------------------------------------------------
# api/orchestration.py — run_graph
# ---------------------------------------------------------------------------


class TestRunGraph:
    def test_run_graph_requires_snapshot(self, tmp_path):
        from cogant.api.orchestration import run_graph

        bundle = _make_bundle(tmp_path)
        with pytest.raises(RuntimeError, match="ingest"):
            run_graph(bundle, str(tmp_path))

    def test_run_graph_empty_dir(self, tmp_path):
        from cogant.api.orchestration import run_graph, run_ingest

        bundle = _make_bundle(tmp_path)
        run_ingest(str(tmp_path), bundle)
        result = run_graph(bundle, str(tmp_path))
        assert isinstance(result, dict)

    def test_run_graph_stores_program_graph(self, tmp_path):
        from cogant.api.orchestration import run_graph, run_ingest

        bundle = _make_bundle(tmp_path)
        run_ingest(str(tmp_path), bundle)
        run_graph(bundle, str(tmp_path))
        pg = bundle.artifacts.get("_program_graph")
        assert pg is not None

    def test_run_graph_with_python_module(self, tmp_path):
        from cogant.api.orchestration import run_graph, run_ingest

        (tmp_path / "mymod.py").write_text("class Foo:\n    def bar(self):\n        return 1\n")
        bundle = _make_bundle(tmp_path)
        run_ingest(str(tmp_path), bundle)
        result = run_graph(bundle, str(tmp_path))
        assert isinstance(result, dict)
        pg = bundle.artifacts.get("_program_graph")
        assert pg is not None

    def test_run_graph_with_classes_and_imports(self, tmp_path):
        from cogant.api.orchestration import run_graph, run_ingest

        (tmp_path / "a.py").write_text("class A:\n    x: int = 0\n")
        (tmp_path / "b.py").write_text("import a\nclass B(object):\n    pass\n")
        bundle = _make_bundle(tmp_path)
        run_ingest(str(tmp_path), bundle)
        result = run_graph(bundle, str(tmp_path))
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# api/orchestration.py — run_translate
# ---------------------------------------------------------------------------


class TestRunTranslate:
    def test_run_translate_requires_graph(self, tmp_path):
        from cogant.api.orchestration import run_translate

        bundle = _make_bundle(tmp_path)
        with pytest.raises(RuntimeError, match="graph"):
            run_translate(bundle)

    def test_run_translate_empty_graph(self, tmp_path):
        from cogant.api.orchestration import run_graph, run_ingest, run_translate

        bundle = _make_bundle(tmp_path)
        run_ingest(str(tmp_path), bundle)
        run_graph(bundle, str(tmp_path))
        result = run_translate(bundle)
        assert isinstance(result, dict)
        assert result["type"] == "gnn_model"
        assert "mapping_count" in result

    def test_run_translate_stores_mappings(self, tmp_path):
        from cogant.api.orchestration import run_graph, run_ingest, run_translate

        (tmp_path / "mod.py").write_text("def process(x: int) -> int:\n    return x\n")
        bundle = _make_bundle(tmp_path)
        run_ingest(str(tmp_path), bundle)
        run_graph(bundle, str(tmp_path))
        run_translate(bundle)
        mappings = bundle.artifacts.get("_semantic_mappings")
        assert isinstance(mappings, dict)

    def test_run_translate_stores_engine(self, tmp_path):
        from cogant.api.orchestration import run_graph, run_ingest, run_translate

        bundle = _make_bundle(tmp_path)
        run_ingest(str(tmp_path), bundle)
        run_graph(bundle, str(tmp_path))
        run_translate(bundle)
        engine = bundle.artifacts.get("_translation_engine")
        assert engine is not None


# ---------------------------------------------------------------------------
# api/orchestration.py — run_statespace
# ---------------------------------------------------------------------------


class TestRunStatespace:
    def test_run_statespace_requires_graph(self, tmp_path):
        from cogant.api.orchestration import run_statespace

        bundle = _make_bundle(tmp_path)
        with pytest.raises(RuntimeError, match="graph"):
            run_statespace(bundle, str(tmp_path))

    def test_run_statespace_empty_graph(self, tmp_path):
        from cogant.api.orchestration import run_graph, run_ingest, run_statespace

        bundle = _make_bundle(tmp_path)
        run_ingest(str(tmp_path), bundle)
        run_graph(bundle, str(tmp_path))
        result = run_statespace(bundle, str(tmp_path))
        assert isinstance(result, dict)
        assert result["type"] == "state_space_model"
        assert "states" in result
        assert "observations" in result
        assert "actions" in result

    def test_run_statespace_stores_model(self, tmp_path):
        from cogant.api.orchestration import run_graph, run_ingest, run_statespace

        bundle = _make_bundle(tmp_path)
        run_ingest(str(tmp_path), bundle)
        run_graph(bundle, str(tmp_path))
        run_statespace(bundle, str(tmp_path))
        model = bundle.artifacts.get("_state_space_model")
        assert model is not None

    def test_run_statespace_with_module(self, tmp_path):
        from cogant.api.orchestration import run_graph, run_ingest, run_statespace, run_translate

        (tmp_path / "m.py").write_text(
            "class Agent:\n    state: int = 0\n    def act(self) -> str:\n        return 'action'\n"
        )
        bundle = _make_bundle(tmp_path)
        run_ingest(str(tmp_path), bundle)
        run_graph(bundle, str(tmp_path))
        run_translate(bundle)
        result = run_statespace(bundle, str(tmp_path))
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# api/orchestration.py — run_process
# ---------------------------------------------------------------------------


class TestRunProcess:
    def test_run_process_requires_graph(self, tmp_path):
        from cogant.api.orchestration import run_process

        bundle = _make_bundle(tmp_path)
        with pytest.raises(RuntimeError, match="graph"):
            run_process(bundle, str(tmp_path))

    def test_run_process_empty_graph(self, tmp_path):
        from cogant.api.orchestration import run_graph, run_ingest, run_process

        bundle = _make_bundle(tmp_path)
        run_ingest(str(tmp_path), bundle)
        run_graph(bundle, str(tmp_path))
        result = run_process(bundle, str(tmp_path))
        assert isinstance(result, dict)
        assert "type" in result

    def test_run_process_stores_model(self, tmp_path):
        from cogant.api.orchestration import run_graph, run_ingest, run_process

        bundle = _make_bundle(tmp_path)
        run_ingest(str(tmp_path), bundle)
        run_graph(bundle, str(tmp_path))
        run_process(bundle, str(tmp_path))
        model = bundle.artifacts.get("_process_model")
        assert model is not None


# ---------------------------------------------------------------------------
# api/orchestration.py — _default_translation_engine
# ---------------------------------------------------------------------------


class TestDefaultTranslationEngine:
    def test_import_and_call(self):
        from cogant.api.orchestration import _default_translation_engine

        engine = _default_translation_engine()
        assert engine is not None

    def test_engine_has_translate(self):
        from cogant.api.orchestration import _default_translation_engine

        engine = _default_translation_engine()
        assert hasattr(engine, "translate")

    def test_engine_registers_full_shipped_rule_set(self):
        from cogant.api.orchestration import _default_translation_engine

        engine = _default_translation_engine()
        rule_names = {rule.name for rule in engine.rules}
        assert len(rule_names) == 22
        assert {"parameter", "state_machine", "rate_limiter"} <= rule_names
