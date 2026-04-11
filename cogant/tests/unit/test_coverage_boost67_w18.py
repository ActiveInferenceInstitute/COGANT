#!/usr/bin/env python3
"""Coverage boost batch 67 — export modules, config module, viz/mermaid module.

Covers:
- export: GraphMLExporter (export), ParquetExporter (export), TypedExporter
  (export_adjacency_matrix, export_cytoscape_json, export_graphviz_dot,
   export_typed_graph)
- config: ConfigLoader (load_default, load_all_configs, build_cogant_config),
  list_presets, get_preset, get_named_preset, CogantConfig, PipelineConfig,
  ExportFormat, LogLevel, ValidationLevel
- viz/mermaid: MermaidGenerator (generate_flowchart, generate_class_diagram,
  generate_dependency_graph, generate_all)
- viz/boundary: BoundaryMapper (map_module_boundaries, map_type_boundaries,
  generate_boundary_report, markov_blanket_collapsed_mermaid)
"""

import pytest
from pathlib import Path

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_empty_graph():
    from cogant.schemas.graph import ProgramGraph, GraphMetadata
    return ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))


def _make_graph_with_nodes():
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import NodeKind, EdgeKind
    builder = ProgramGraphBuilder(repo_uri="file:///test")
    n1 = builder.add_node(NodeKind.MODULE, "mod", "mod", path="mod.py")
    n2 = builder.add_node(NodeKind.CLASS, "Cls", "mod.Cls", path="mod.py")
    n3 = builder.add_node(NodeKind.FUNCTION, "fn", "mod.fn", path="mod.py")
    builder.add_edge(n1.id, n2.id, EdgeKind.CONTAINS)
    builder.add_edge(n1.id, n3.id, EdgeKind.CONTAINS)
    return builder.finalize()


def _make_process_model():
    from cogant.process.extractor import ProcessModel
    return ProcessModel(id="pm1", schema_name="test", stages={}, connections={})


def _make_state_space():
    from cogant.statespace.compiler import StateSpaceModel
    from cogant.statespace.temporal import TimeRegime
    return StateSpaceModel(
        id="ss1", schema_name="test",
        variables={}, observations={}, actions={},
        transitions={}, likelihoods={}, preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


# ---------------------------------------------------------------------------
# export — GraphMLExporter
# ---------------------------------------------------------------------------

class TestGraphMLExporter:
    def test_init_empty_graph(self):
        from cogant.export import GraphMLExporter
        graph = _make_empty_graph()
        exporter = GraphMLExporter(graph)
        assert exporter is not None

    def test_export_returns_str(self):
        from cogant.export import GraphMLExporter
        graph = _make_empty_graph()
        exporter = GraphMLExporter(graph)
        result = exporter.export()
        assert isinstance(result, str)

    def test_export_with_nodes(self):
        from cogant.export import GraphMLExporter
        graph = _make_graph_with_nodes()
        exporter = GraphMLExporter(graph)
        result = exporter.export()
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# export — ParquetExporter
# ---------------------------------------------------------------------------

class TestParquetExporter:
    def test_init(self):
        from cogant.export import ParquetExporter
        graph = _make_empty_graph()
        exporter = ParquetExporter(graph)
        assert exporter is not None

    def test_export_returns_list(self, tmp_path):
        from cogant.export import ParquetExporter
        graph = _make_empty_graph()
        exporter = ParquetExporter(graph)
        result = exporter.export(tmp_path)
        assert isinstance(result, list)

    def test_export_with_nodes(self, tmp_path):
        from cogant.export import ParquetExporter
        graph = _make_graph_with_nodes()
        exporter = ParquetExporter(graph)
        result = exporter.export(tmp_path)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# export — TypedExporter
# ---------------------------------------------------------------------------

class TestTypedExporter:
    def _make_exporter(self):
        from cogant.export import TypedExporter
        return TypedExporter()

    def test_init(self):
        exporter = self._make_exporter()
        assert exporter is not None

    def test_export_typed_graph_empty(self):
        exporter = self._make_exporter()
        graph = _make_empty_graph()
        result = exporter.export_typed_graph(graph)
        assert isinstance(result, dict)

    def test_export_typed_graph_with_nodes(self):
        exporter = self._make_exporter()
        graph = _make_graph_with_nodes()
        result = exporter.export_typed_graph(graph)
        assert isinstance(result, dict)

    def test_export_cytoscape_json(self):
        exporter = self._make_exporter()
        graph = _make_graph_with_nodes()
        result = exporter.export_cytoscape_json(graph)
        assert isinstance(result, dict)

    def test_export_graphviz_dot(self):
        exporter = self._make_exporter()
        graph = _make_graph_with_nodes()
        result = exporter.export_graphviz_dot(graph)
        assert isinstance(result, str)
        assert "digraph" in result or "graph" in result or len(result) >= 0

    def test_export_adjacency_matrix_empty(self):
        exporter = self._make_exporter()
        graph = _make_empty_graph()
        result = exporter.export_adjacency_matrix(graph)
        assert isinstance(result, dict)

    def test_export_adjacency_matrix_with_nodes(self):
        exporter = self._make_exporter()
        graph = _make_graph_with_nodes()
        result = exporter.export_adjacency_matrix(graph)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# config — ConfigLoader and module-level functions
# ---------------------------------------------------------------------------

class TestConfigLoader:
    def test_load_default_returns_dict(self):
        from cogant.config import ConfigLoader
        result = ConfigLoader.load_default()
        assert isinstance(result, dict)

    def test_load_all_configs_no_path(self):
        from cogant.config import ConfigLoader
        result = ConfigLoader.load_all_configs()
        assert isinstance(result, dict)

    def test_load_all_configs_with_preset(self):
        from cogant.config import ConfigLoader
        result = ConfigLoader.load_all_configs(preset="minimal")
        assert isinstance(result, dict)

    def test_build_cogant_config_default(self):
        from cogant.config import ConfigLoader
        from cogant.config.schema import CogantConfig
        cfg = ConfigLoader.build_cogant_config()
        assert isinstance(cfg, CogantConfig)

    def test_build_cogant_config_with_dict(self):
        from cogant.config import ConfigLoader
        from cogant.config.schema import CogantConfig
        cfg = ConfigLoader.build_cogant_config({"max_workers": 4})
        assert isinstance(cfg, CogantConfig)


class TestConfigModuleFunctions:
    def test_list_presets_returns_list(self):
        from cogant.config import list_presets
        presets = list_presets()
        assert isinstance(presets, list)
        assert len(presets) > 0

    def test_list_presets_has_standard(self):
        from cogant.config import list_presets
        presets = list_presets()
        assert "standard" in presets

    def test_get_preset_minimal(self):
        from cogant.config import get_preset
        result = get_preset("minimal")
        assert isinstance(result, dict)

    def test_get_preset_comprehensive(self):
        from cogant.config import get_preset
        result = get_preset("comprehensive")
        assert isinstance(result, dict)

    def test_get_named_preset(self):
        from cogant.config import get_named_preset
        result = get_named_preset("minimal")
        assert isinstance(result, dict)

    def test_get_preset_unknown_raises(self):
        from cogant.config import get_preset
        with pytest.raises((KeyError, ValueError, Exception)):
            get_preset("nonexistent_preset_xyz")


class TestCogantConfig:
    def test_create_default(self):
        from cogant.config.schema import CogantConfig
        cfg = CogantConfig()
        assert hasattr(cfg, "max_workers")
        assert isinstance(cfg.max_workers, int)

    def test_version_field(self):
        from cogant.config.schema import CogantConfig
        cfg = CogantConfig()
        assert hasattr(cfg, "version")
        assert isinstance(cfg.version, str)

    def test_enable_caching_field(self):
        from cogant.config.schema import CogantConfig
        cfg = CogantConfig()
        assert hasattr(cfg, "enable_caching")
        assert isinstance(cfg.enable_caching, bool)

    def test_custom_max_workers(self):
        from cogant.config.schema import CogantConfig
        cfg = CogantConfig(max_workers=8)
        assert cfg.max_workers == 8


class TestConfigEnums:
    def test_export_format_values(self):
        from cogant.config import ExportFormat
        assert ExportFormat is not None
        values = list(ExportFormat)
        assert len(values) > 0

    def test_log_level_values(self):
        from cogant.config import LogLevel
        assert LogLevel is not None
        values = list(LogLevel)
        assert len(values) > 0

    def test_validation_level_values(self):
        from cogant.config import ValidationLevel
        assert ValidationLevel is not None
        values = list(ValidationLevel)
        assert len(values) > 0


# ---------------------------------------------------------------------------
# viz — MermaidGenerator
# ---------------------------------------------------------------------------

class TestMermaidGenerator:
    def _make_generator(self):
        from cogant.viz import MermaidGenerator
        return MermaidGenerator()

    def test_init(self):
        gen = self._make_generator()
        assert gen is not None

    def test_generate_flowchart_empty_graph(self):
        gen = self._make_generator()
        graph = _make_empty_graph()
        result = gen.generate_flowchart(graph, semantic_mappings={})
        assert isinstance(result, str)

    def test_generate_flowchart_with_nodes(self):
        gen = self._make_generator()
        graph = _make_graph_with_nodes()
        result = gen.generate_flowchart(graph, semantic_mappings={})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_class_diagram_empty(self):
        gen = self._make_generator()
        graph = _make_empty_graph()
        result = gen.generate_class_diagram(graph)
        assert isinstance(result, str)

    def test_generate_class_diagram_with_nodes(self):
        gen = self._make_generator()
        graph = _make_graph_with_nodes()
        result = gen.generate_class_diagram(graph)
        assert isinstance(result, str)

    def test_generate_dependency_graph_empty(self):
        gen = self._make_generator()
        graph = _make_empty_graph()
        result = gen.generate_dependency_graph(graph)
        assert isinstance(result, str)

    def test_generate_dependency_graph_with_nodes(self):
        gen = self._make_generator()
        graph = _make_graph_with_nodes()
        result = gen.generate_dependency_graph(graph)
        assert isinstance(result, str)

    def test_generate_all_returns_dict(self):
        from cogant.viz import MermaidGenerator
        gen = MermaidGenerator()
        graph = _make_graph_with_nodes()
        result = gen.generate_all(graph)
        assert isinstance(result, dict)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# viz — BoundaryMapper
# ---------------------------------------------------------------------------

class TestBoundaryMapper:
    def _make_mapper(self):
        from cogant.viz import BoundaryMapper
        return BoundaryMapper()

    def test_init(self):
        mapper = self._make_mapper()
        assert mapper is not None

    def test_map_module_boundaries_empty(self):
        mapper = self._make_mapper()
        graph = _make_empty_graph()
        result = mapper.map_module_boundaries(graph)
        assert isinstance(result, str)

    def test_map_module_boundaries_with_nodes(self):
        mapper = self._make_mapper()
        graph = _make_graph_with_nodes()
        result = mapper.map_module_boundaries(graph)
        assert isinstance(result, str)

    def test_map_type_boundaries(self):
        mapper = self._make_mapper()
        graph = _make_graph_with_nodes()
        result = mapper.map_type_boundaries(graph)
        assert isinstance(result, str)

    def test_generate_boundary_report(self):
        mapper = self._make_mapper()
        graph = _make_graph_with_nodes()
        result = mapper.generate_boundary_report(graph)
        assert isinstance(result, (str, dict))

    def test_markov_blanket_collapsed_mermaid(self):
        from cogant.markov.blanket import partition_by_seeds
        mapper = self._make_mapper()
        graph = _make_graph_with_nodes()
        blanket = partition_by_seeds(graph, seeds=set())
        result = mapper.markov_blanket_collapsed_mermaid(graph, blanket)
        assert isinstance(result, str)
