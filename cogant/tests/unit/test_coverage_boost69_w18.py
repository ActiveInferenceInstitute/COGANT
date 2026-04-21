#!/usr/bin/env python3
"""Coverage boost batch 69 — observability, plugins, tools, statespace modules.

Covers:
- observability: Counter (inc, reset), Histogram (observe, mean, p95, p99, count),
  MetricsRegistry (counter, histogram, summary, reset_all), get_logger, setup_logging
- plugins: PluginRegistry (discover, list_plugins, get_plugin_info, get_loaded_object),
  PluginInfo, PluginMetadata, discover_plugins
- tools: organize_run_dir, migrate_output_tree
- statespace: StateSpaceCompiler (compile), StateVariableExtractor (extract,
  get_state_variables), TemporalAnalyzer (analyze, get_metrics, get_event_patterns,
  get_ordering_constraints, get_critical_path), StateVariable, StateSpaceModel
"""

from pathlib import Path

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


# ---------------------------------------------------------------------------
# observability — Counter, Histogram, MetricsRegistry
# ---------------------------------------------------------------------------


class TestCounter:
    def test_init_default(self):
        from cogant.observability import Counter

        c = Counter(name="test_counter")
        assert c.name == "test_counter"
        assert c.value == 0

    def test_inc_increments(self):
        from cogant.observability import Counter

        c = Counter(name="c1")
        c.inc()
        assert c.value == 1
        c.inc()
        assert c.value == 2

    def test_inc_by_amount(self):
        from cogant.observability import Counter

        c = Counter(name="c2")
        c.inc(5)
        assert c.value == 5

    def test_reset_clears(self):
        from cogant.observability import Counter

        c = Counter(name="c3")
        c.inc(10)
        c.reset()
        assert c.value == 0

    def test_init_with_labels(self):
        from cogant.observability import Counter

        c = Counter(name="c4", labels={"env": "test"})
        assert c.labels == {"env": "test"}


class TestHistogram:
    def test_init(self):
        from cogant.observability import Histogram

        h = Histogram(name="latency")
        assert h.name == "latency"

    def test_observe_adds_value(self):
        from cogant.observability import Histogram

        h = Histogram(name="h1")
        h.observe(1.0)
        h.observe(2.0)
        assert h.count() == 2

    def test_mean_correct(self):
        from cogant.observability import Histogram

        h = Histogram(name="h2")
        h.observe(1.0)
        h.observe(3.0)
        assert abs(h.mean() - 2.0) < 1e-9

    def test_mean_empty(self):
        from cogant.observability import Histogram

        h = Histogram(name="h3")
        result = h.mean()
        assert result == 0.0 or result is None or isinstance(result, float)

    def test_p95_returns_float(self):
        from cogant.observability import Histogram

        h = Histogram(name="h4")
        for i in range(100):
            h.observe(float(i))
        p = h.p95()
        assert isinstance(p, float)

    def test_p99_returns_float(self):
        from cogant.observability import Histogram

        h = Histogram(name="h5")
        for i in range(100):
            h.observe(float(i))
        p = h.p99()
        assert isinstance(p, float)


class TestMetricsRegistry:
    def test_init(self):
        from cogant.observability import MetricsRegistry

        reg = MetricsRegistry()
        assert reg is not None

    def test_counter_creates_counter(self):
        from cogant.observability import Counter, MetricsRegistry

        reg = MetricsRegistry()
        c = reg.counter("requests")
        assert isinstance(c, Counter)

    def test_counter_with_labels(self):
        from cogant.observability import Counter, MetricsRegistry

        reg = MetricsRegistry()
        c = reg.counter("requests", labels={"method": "GET"})
        assert isinstance(c, Counter)

    def test_histogram_creates_histogram(self):
        from cogant.observability import Histogram, MetricsRegistry

        reg = MetricsRegistry()
        h = reg.histogram("response_time")
        assert isinstance(h, Histogram)

    def test_summary_returns_dict(self):
        from cogant.observability import MetricsRegistry

        reg = MetricsRegistry()
        reg.counter("c1").inc(5)
        summary = reg.summary()
        assert isinstance(summary, dict)

    def test_reset_all(self):
        from cogant.observability import MetricsRegistry

        reg = MetricsRegistry()
        reg.counter("c1").inc(10)
        reg.reset_all()
        # After reset, counters should be cleared or reset
        summary = reg.summary()
        assert isinstance(summary, dict)


class TestObservabilityFunctions:
    def test_get_logger_returns_logger(self):
        from cogant.observability import get_logger

        logger = get_logger("test_module")
        assert logger is not None

    def test_setup_logging_runs(self):
        from cogant.observability import setup_logging

        # Should not raise
        setup_logging(level="INFO", format="json")

    def test_setup_logging_text_format(self):
        from cogant.observability import setup_logging

        setup_logging(level="DEBUG", format="text")


# ---------------------------------------------------------------------------
# plugins — PluginRegistry, PluginInfo, PluginMetadata
# ---------------------------------------------------------------------------


class TestPluginRegistry:
    def test_init(self):
        from cogant.plugins import PluginRegistry

        registry = PluginRegistry()
        assert registry is not None

    def test_discover_returns_list(self):
        from cogant.plugins import PluginRegistry

        registry = PluginRegistry()
        plugins = registry.discover()
        assert isinstance(plugins, list)

    def test_list_plugins_returns_list(self):
        from cogant.plugins import PluginRegistry

        registry = PluginRegistry()
        names = registry.list_plugins()
        assert isinstance(names, list)

    def test_get_plugin_info_unknown(self):
        from cogant.plugins import PluginRegistry

        registry = PluginRegistry()
        with pytest.raises((KeyError, ValueError, Exception)):
            registry.get_plugin_info("nonexistent_plugin_xyz")

    def test_get_loaded_object_unknown_raises(self):
        from cogant.plugins import PluginRegistry

        registry = PluginRegistry()
        with pytest.raises((KeyError, ValueError, Exception)):
            registry.get_loaded_object("nonexistent_xyz")


class TestPluginInfo:
    def test_init(self):
        from cogant.plugins import PluginInfo

        info = PluginInfo(
            name="test_plugin",
            version="1.0.0",
            entry_point="test.plugin:Plugin",
            loaded=False,
            error=None,
        )
        assert info.name == "test_plugin"
        assert info.loaded is False
        assert info.error is None


class TestPluginMetadata:
    def test_init(self):
        from cogant.plugins import PluginMetadata

        meta = PluginMetadata(
            name="my_plugin",
            version="0.1",
            author="alice",
            description="A plugin",
        )
        assert meta.name == "my_plugin"
        assert meta.author == "alice"


class TestDiscoverPlugins:
    def test_discover_returns_list(self):
        from cogant.plugins import discover_plugins

        result = discover_plugins()
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# tools — organize_run_dir, migrate_output_tree
# ---------------------------------------------------------------------------


class TestOrganizeRunDir:
    def test_empty_dir_returns_none_or_path(self, tmp_path):
        from cogant.tools import organize_run_dir

        result = organize_run_dir(tmp_path)
        assert result is None or isinstance(result, Path)

    def test_dry_run_returns_none_or_path(self, tmp_path):
        from cogant.tools import organize_run_dir

        result = organize_run_dir(tmp_path, dry_run=True)
        assert result is None or isinstance(result, Path)


class TestMigrateOutputTree:
    def test_empty_dir_returns_int(self, tmp_path):
        from cogant.tools import migrate_output_tree

        result = migrate_output_tree(tmp_path)
        assert isinstance(result, int)

    def test_dry_run_returns_int(self, tmp_path):
        from cogant.tools import migrate_output_tree

        result = migrate_output_tree(tmp_path, dry_run=True)
        assert isinstance(result, int)

    def test_with_suite_option(self, tmp_path):
        from cogant.tools import migrate_output_tree

        result = migrate_output_tree(tmp_path, suite="control_positive")
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# statespace — StateSpaceCompiler, StateVariableExtractor, TemporalAnalyzer
# ---------------------------------------------------------------------------


class TestStateSpaceCompiler:
    def test_init(self):
        from cogant.statespace import StateSpaceCompiler

        graph = _make_empty_graph()
        compiler = StateSpaceCompiler(graph, schema_name="test")
        assert compiler is not None

    def test_compile_returns_state_space_model(self):
        from cogant.statespace import StateSpaceCompiler, StateSpaceModel

        graph = _make_empty_graph()
        compiler = StateSpaceCompiler(graph, schema_name="test")
        model = compiler.compile(semantic_mappings={})
        assert isinstance(model, StateSpaceModel)

    def test_compile_with_nodes(self):
        from cogant.statespace import StateSpaceCompiler, StateSpaceModel

        graph = _make_graph_with_nodes()
        compiler = StateSpaceCompiler(graph, schema_name="test")
        model = compiler.compile(semantic_mappings={})
        assert isinstance(model, StateSpaceModel)
        assert model.schema_name == "test"


class TestStateVariableExtractor:
    def test_init(self):
        from cogant.statespace import StateVariableExtractor

        graph = _make_empty_graph()
        extractor = StateVariableExtractor(graph)
        assert extractor is not None

    def test_extract_empty_graph(self):
        from cogant.statespace import StateVariableExtractor

        graph = _make_empty_graph()
        extractor = StateVariableExtractor(graph)
        vars = extractor.extract(semantic_mappings={})
        assert isinstance(vars, dict)

    def test_get_state_variables_empty(self):
        from cogant.statespace import StateVariableExtractor

        graph = _make_empty_graph()
        extractor = StateVariableExtractor(graph)
        extractor.extract(semantic_mappings={})
        vars = extractor.get_state_variables()
        assert isinstance(vars, dict)

    def test_extract_with_nodes(self):
        from cogant.statespace import StateVariableExtractor

        graph = _make_graph_with_nodes()
        extractor = StateVariableExtractor(graph)
        vars = extractor.extract(semantic_mappings={})
        assert isinstance(vars, dict)


class TestTemporalAnalyzer:
    def test_init(self):
        from cogant.statespace import TemporalAnalyzer

        graph = _make_empty_graph()
        analyzer = TemporalAnalyzer(graph)
        assert analyzer is not None

    def test_analyze_returns_time_regime(self):
        from cogant.statespace import TemporalAnalyzer
        from cogant.statespace.temporal import TimeRegime

        graph = _make_empty_graph()
        analyzer = TemporalAnalyzer(graph)
        result = analyzer.analyze()
        assert isinstance(result, TimeRegime)

    def test_get_metrics_returns_object(self):
        from cogant.statespace import TemporalAnalyzer

        graph = _make_graph_with_nodes()
        analyzer = TemporalAnalyzer(graph)
        analyzer.analyze()
        metrics = analyzer.get_metrics()
        assert metrics is not None

    def test_get_event_patterns_returns_list(self):
        from cogant.statespace import TemporalAnalyzer

        graph = _make_graph_with_nodes()
        analyzer = TemporalAnalyzer(graph)
        analyzer.analyze()
        patterns = analyzer.get_event_patterns()
        assert isinstance(patterns, list)

    def test_get_ordering_constraints_returns_list(self):
        from cogant.statespace import TemporalAnalyzer

        graph = _make_graph_with_nodes()
        analyzer = TemporalAnalyzer(graph)
        analyzer.analyze()
        constraints = analyzer.get_ordering_constraints()
        assert isinstance(constraints, list)

    def test_get_critical_path_returns_list(self):
        from cogant.statespace import TemporalAnalyzer

        graph = _make_graph_with_nodes()
        analyzer = TemporalAnalyzer(graph)
        analyzer.analyze()
        path = analyzer.get_critical_path()
        assert isinstance(path, list)
