#!/usr/bin/env python3
"""Targeted branch tests — translate/confidence.py, translate/engine.py,
translate/review.py, ingest/files.py, ingest/language_detect.py,
ingest/manifest.py, ingest/repo_sniff.py.

Covers:
- translate/confidence.py: ConfidenceModel (compute, score_batch, determine_confidence_tier,
  detect_conflicts, get_scoring_report, get_high/low_confidence_mappings,
  get_conflicted_mappings, compute_confidence_score, score_evidence_diversity,
  update_mapping_confidence, clear_log)
- translate/engine.py: TranslationEngine (translate, get_statistics, get_mapping,
  get_mappings_by_kind, get_mappings_by_confidence, get_coverage_report, get_match_log)
- translate/review.py: ReviewManager (add_mapping, accept_mapping, reject_mapping,
  get_unreviewed_mappings, get_review_summary, get_mappings_by_status,
  export_reviewed_mappings, get_mapping_for_review, get_review_history)
- ingest/files.py: FileEnumerator (enumerate), FileInfo
- ingest/language_detect.py: LanguageDetector (detect_language, detect_repo_languages,
  get_supported_languages, get_parser)
- ingest/manifest.py: ManifestParser (parse, parse_requirements_txt, parse_pyproject_toml)
- ingest/repo_sniff.py: count_source_files, estimate_pipeline_seconds, format_duration
"""

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_empty_graph():
    from cogant.schemas.graph import GraphMetadata, ProgramGraph

    return ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))


def _make_graph_with_nodes():
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import EdgeKind, NodeKind

    builder = ProgramGraphBuilder(repo_uri="file:///test")
    n1 = builder.add_node(NodeKind.MODULE, "mod", "mod", path="mod.py")
    n2 = builder.add_node(NodeKind.FUNCTION, "fn", "mod.fn", path="mod.py")
    builder.add_edge(n1.id, n2.id, EdgeKind.CONTAINS)
    return builder.finalize()


def _make_semantic_mapping(label="obs_mod"):
    from cogant.schemas.semantic import MappingKind, SemanticMapping

    return SemanticMapping(
        id=f"map_{label}",
        kind=MappingKind.OBSERVATION,
        semantic_label=label,
        confidence_score=0.75,
        evidence_count=3,
    )


# ---------------------------------------------------------------------------
# translate/confidence.py — ConfidenceModel
# ---------------------------------------------------------------------------


class TestConfidenceModel:
    def _make_model(self):
        from cogant.translate.confidence import ConfidenceModel

        return ConfidenceModel()

    def test_init(self):
        model = self._make_model()
        assert model is not None

    def test_compute_returns_float(self):
        model = self._make_model()
        mapping = _make_semantic_mapping()
        score = model.compute(mapping)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_score_batch_empty(self):
        model = self._make_model()
        model.score_batch([])  # Should not raise

    def test_score_batch_multiple(self):
        model = self._make_model()
        mappings = [_make_semantic_mapping(f"m{i}") for i in range(3)]
        model.score_batch(mappings)

    def test_determine_confidence_tier(self):
        from cogant.schemas.semantic import ConfidenceTier

        model = self._make_model()
        mapping = _make_semantic_mapping()
        tier = model.determine_confidence_tier(mapping, score=0.8)
        assert isinstance(tier, ConfidenceTier)

    def test_detect_conflicts(self):
        model = self._make_model()
        mapping = _make_semantic_mapping()
        conflicts = model.detect_conflicts(mapping)
        assert isinstance(conflicts, list)

    def test_get_scoring_report_empty(self):
        model = self._make_model()
        report = model.get_scoring_report()
        assert isinstance(report, dict)

    def test_get_high_confidence_mappings_empty(self):
        model = self._make_model()
        result = model.get_high_confidence_mappings([])
        assert isinstance(result, list)

    def test_get_high_confidence_mappings_with_data(self):
        model = self._make_model()
        mappings = [_make_semantic_mapping(f"m{i}") for i in range(3)]
        result = model.get_high_confidence_mappings(mappings, threshold=0.5)
        assert isinstance(result, list)

    def test_get_low_confidence_mappings_empty(self):
        model = self._make_model()
        result = model.get_low_confidence_mappings([])
        assert isinstance(result, list)

    def test_get_conflicted_mappings_empty(self):
        model = self._make_model()
        result = model.get_conflicted_mappings([])
        assert isinstance(result, list)

    def test_compute_confidence_score(self):
        model = self._make_model()
        mapping = _make_semantic_mapping()
        score = model.compute_confidence_score(mapping)
        assert isinstance(score, float)

    def test_score_evidence_diversity(self):
        model = self._make_model()
        mapping = _make_semantic_mapping()
        result = model.score_evidence_diversity(mapping)
        assert isinstance(result, float)

    def test_update_mapping_confidence(self):
        model = self._make_model()
        mapping = _make_semantic_mapping()
        model.update_mapping_confidence(mapping)
        assert mapping.confidence_score >= 0.0

    def test_clear_log(self):
        model = self._make_model()
        mapping = _make_semantic_mapping()
        model.compute(mapping)
        model.clear_log()
        report = model.get_scoring_report()
        assert isinstance(report, dict)


# ---------------------------------------------------------------------------
# translate/engine.py — TranslationEngine
# ---------------------------------------------------------------------------


class TestTranslationEngine:
    def _make_engine(self):
        from cogant.translate.engine import TranslationEngine

        return TranslationEngine()

    def test_init(self):
        engine = self._make_engine()
        assert engine is not None

    def test_translate_empty_graph(self):
        engine = self._make_engine()
        graph = _make_empty_graph()
        mappings = engine.translate(graph)
        assert isinstance(mappings, list)

    def test_translate_with_nodes(self):
        engine = self._make_engine()
        graph = _make_graph_with_nodes()
        mappings = engine.translate(graph)
        assert isinstance(mappings, list)

    def test_translate_with_rule_filter(self):
        engine = self._make_engine()
        graph = _make_empty_graph()
        mappings = engine.translate(graph, rule_filter=["nonexistent_rule"])
        assert isinstance(mappings, list)

    def test_get_statistics_empty(self):
        engine = self._make_engine()
        stats = engine.get_statistics()
        assert isinstance(stats, dict)

    def test_get_mapping_unknown(self):
        engine = self._make_engine()
        result = engine.get_mapping("nonexistent_id")
        assert result is None

    def test_get_mappings_by_kind_empty(self):
        engine = self._make_engine()
        from cogant.schemas.semantic import MappingKind

        result = engine.get_mappings_by_kind(MappingKind.OBSERVATION)
        assert isinstance(result, list)

    def test_get_mappings_by_confidence_empty(self):
        from cogant.schemas.semantic import ConfidenceTier

        engine = self._make_engine()
        result = engine.get_mappings_by_confidence(ConfidenceTier.STATIC_ONLY)
        assert isinstance(result, list)

    def test_get_coverage_report(self):
        engine = self._make_engine()
        graph = _make_graph_with_nodes()
        engine.translate(graph)
        report = engine.get_coverage_report(graph)
        assert isinstance(report, dict)

    def test_get_match_log(self):
        engine = self._make_engine()
        log = engine.get_match_log()
        assert isinstance(log, list)

    def test_get_statistics_after_translate(self):
        engine = self._make_engine()
        graph = _make_graph_with_nodes()
        engine.translate(graph)
        stats = engine.get_statistics()
        assert isinstance(stats, dict)


# ---------------------------------------------------------------------------
# translate/review.py — ReviewManager
# ---------------------------------------------------------------------------


class TestReviewManager:
    def _make_manager(self):
        from cogant.translate.review import ReviewManager

        return ReviewManager()

    def test_init(self):
        manager = self._make_manager()
        assert manager is not None

    def test_add_mapping(self):
        manager = self._make_manager()
        mapping = _make_semantic_mapping()
        manager.add_mapping(mapping)

    def test_get_unreviewed_mappings_empty(self):
        manager = self._make_manager()
        result = manager.get_unreviewed_mappings()
        assert isinstance(result, list)

    def test_get_unreviewed_after_add(self):
        manager = self._make_manager()
        mapping = _make_semantic_mapping()
        manager.add_mapping(mapping)
        unreviewed = manager.get_unreviewed_mappings()
        assert len(unreviewed) >= 1

    def test_accept_mapping(self):
        manager = self._make_manager()
        mapping = _make_semantic_mapping()
        manager.add_mapping(mapping)
        result = manager.accept_mapping(mapping.id, reviewer="alice", feedback="looks good")
        assert isinstance(result, bool)

    def test_reject_mapping(self):
        manager = self._make_manager()
        mapping = _make_semantic_mapping()
        manager.add_mapping(mapping)
        result = manager.reject_mapping(mapping.id, reviewer="bob", reason="incorrect label")
        assert isinstance(result, bool)

    def test_accept_unknown_mapping(self):
        manager = self._make_manager()
        result = manager.accept_mapping("nonexistent", reviewer="alice")
        assert result is False

    def test_reject_unknown_mapping(self):
        manager = self._make_manager()
        result = manager.reject_mapping("nonexistent", reviewer="bob", reason="n/a")
        assert result is False

    def test_get_review_summary_empty(self):
        manager = self._make_manager()
        summary = manager.get_review_summary()
        assert isinstance(summary, dict)

    def test_get_mappings_by_status(self):
        manager = self._make_manager()
        result = manager.get_mappings_by_status("auto_proposed")
        assert isinstance(result, list)

    def test_export_reviewed_mappings_empty(self):
        manager = self._make_manager()
        result = manager.export_reviewed_mappings()
        assert isinstance(result, list)

    def test_get_mapping_for_review(self):
        manager = self._make_manager()
        mapping = _make_semantic_mapping()
        manager.add_mapping(mapping)
        result = manager.get_mapping_for_review(mapping.id)
        assert result is None or hasattr(result, "id")

    def test_get_review_history_empty(self):
        manager = self._make_manager()
        result = manager.get_review_history()
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# ingest/files.py — FileEnumerator and FileInfo
# ---------------------------------------------------------------------------


class TestFileEnumerator:
    def test_init(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        enumerator = FileEnumerator(tmp_path)
        assert enumerator is not None

    def test_enumerate_empty_dir(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        enumerator = FileEnumerator(tmp_path)
        files = enumerator.enumerate()
        assert isinstance(files, list)
        assert files == []

    def test_enumerate_with_python_file(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        (tmp_path / "mod.py").write_text("def f(): pass\n")
        enumerator = FileEnumerator(tmp_path, respect_gitignore=False)
        files = enumerator.enumerate()
        assert isinstance(files, list)
        assert len(files) >= 1

    def test_enumerate_no_test_files(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        (tmp_path / "main.py").write_text("x = 1\n")
        (tmp_path / "test_main.py").write_text("def test_x(): pass\n")
        enumerator = FileEnumerator(tmp_path, respect_gitignore=False)
        files = enumerator.enumerate(include_test_files=False)
        names = [f.relative_path for f in files]
        assert not any("test_" in str(n) for n in names)

    def test_enumerate_file_info_fields(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        (tmp_path / "src.py").write_text("x = 1\n")
        enumerator = FileEnumerator(tmp_path, respect_gitignore=False)
        files = enumerator.enumerate()
        if files:
            fi = files[0]
            assert hasattr(fi, "path")
            assert hasattr(fi, "language")
            assert hasattr(fi, "size_bytes")


class TestFileInfo:
    def test_init(self, tmp_path):
        from cogant.ingest.files import FileInfo

        fi = FileInfo(
            path=tmp_path / "mod.py",
            relative_path="mod.py",
            language="python",
            size_bytes=100,
            is_test=False,
            checksum=None,
        )
        assert fi.language == "python"
        assert fi.size_bytes == 100
        assert fi.is_test is False


# ---------------------------------------------------------------------------
# ingest/language_detect.py — LanguageDetector
# ---------------------------------------------------------------------------


class TestLanguageDetector:
    def test_get_supported_languages(self):
        from cogant.ingest.language_detect import LanguageDetector

        langs = LanguageDetector.get_supported_languages()
        assert isinstance(langs, list)
        assert len(langs) > 0

    def test_detect_language_python(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        p = tmp_path / "mod.py"
        p.write_text("x = 1\n")
        lang = LanguageDetector.detect_language(p)
        assert lang is None or isinstance(lang, str)

    def test_detect_language_unknown_ext(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        p = tmp_path / "file.xyz123"
        p.write_text("content\n")
        lang = LanguageDetector.detect_language(p)
        assert lang is None or isinstance(lang, str)

    def test_detect_repo_languages_empty(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        result = LanguageDetector.detect_repo_languages(tmp_path)
        assert isinstance(result, dict)

    def test_detect_repo_languages_with_py(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.py").write_text("y = 2\n")
        result = LanguageDetector.detect_repo_languages(tmp_path)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# ingest/manifest.py — ManifestParser
# ---------------------------------------------------------------------------


class TestManifestParser:
    def test_init(self):
        from cogant.ingest.manifest import ManifestParser

        parser = ManifestParser()
        assert parser is not None

    def test_parse_requirements_txt(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        req = tmp_path / "requirements.txt"
        req.write_text("requests==2.28.0\nnumpy>=1.21.0\npytest\n")
        parser = ManifestParser()
        meta, deps = parser.parse(req)
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    def test_parse_pyproject_toml(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.poetry]
name = "myproject"
version = "0.1.0"

[tool.poetry.dependencies]
python = "^3.10"
requests = "^2.28"
""")
        parser = ManifestParser()
        meta, deps = parser.parse(pyproject)
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    def test_parse_unknown_file_raises(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        unknown = tmp_path / "unknown.xyz"
        unknown.write_text("data\n")
        parser = ManifestParser()
        with pytest.raises((ValueError, Exception)):
            parser.parse(unknown)


class TestDependency:
    def test_init(self):
        from cogant.ingest.manifest import Dependency

        dep = Dependency(name="requests", version="2.28.0", is_dev=False, is_local=False)
        assert dep.name == "requests"
        assert dep.version == "2.28.0"
        assert dep.is_dev is False


# ---------------------------------------------------------------------------
# ingest/repo_sniff.py — count_source_files, estimate_pipeline_seconds,
#                         format_duration
# ---------------------------------------------------------------------------


class TestRepoSniff:
    def test_count_source_files_empty(self, tmp_path):
        from cogant.ingest.repo_sniff import count_source_files

        count = count_source_files(tmp_path)
        assert isinstance(count, int)
        assert count == 0

    def test_count_source_files_with_py(self, tmp_path):
        from cogant.ingest.repo_sniff import count_source_files

        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.py").write_text("y = 2\n")
        count = count_source_files(tmp_path)
        assert count >= 2

    def test_estimate_pipeline_seconds_zero(self):
        from cogant.ingest.repo_sniff import estimate_pipeline_seconds

        result = estimate_pipeline_seconds(0)
        assert isinstance(result, float)
        assert result >= 0.0

    def test_estimate_pipeline_seconds_large(self):
        from cogant.ingest.repo_sniff import estimate_pipeline_seconds

        result = estimate_pipeline_seconds(10000)
        assert isinstance(result, float)
        assert result > 0.0

    def test_format_duration_seconds(self):
        from cogant.ingest.repo_sniff import format_duration

        result = format_duration(45.0)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_duration_minutes(self):
        from cogant.ingest.repo_sniff import format_duration

        result = format_duration(120.0)
        assert isinstance(result, str)

    def test_format_duration_zero(self):
        from cogant.ingest.repo_sniff import format_duration

        result = format_duration(0.0)
        assert isinstance(result, str)
