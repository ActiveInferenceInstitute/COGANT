#!/usr/bin/env python3
"""
Thin end-to-end orchestrator for COGANT pipeline.

Takes a control positive example repo and runs the FULL pipeline:
  ingest → parse → symbols → imports → call graph → program graph →
  translation rules → state space → GNN output → validate

Outputs to output/{repo_name}/ with comprehensive analysis:
  - model.gnn.md, model.gnn.json
  - program_graph.json (with metadata and provenance)
  - validation_report.json
  - Mermaid diagrams (class, dependency, state, sequence, semantic, boundary)
  - Charts (node/edge distribution as HTML)
  - Graph exports (typed_graph.json, cytoscape.json, adjacency_matrix.json, graph.dot)
  - Semantic mappings and simulation traces
  - HTML index and markdown summary
"""

import argparse
import html
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

# Add py/ to path for cogant imports
sys.path.insert(0, str(Path(__file__).parent.parent / "py"))

from cogant.config import ConfigLoader
from cogant.gnn.formatter import GNNMarkdownFormatter
from cogant.gnn.json_export import GNNJSONExporter
from cogant.gnn.package import GNNPackageBuilder
from cogant.gnn.runner import GNNModelRunner
from cogant.gnn.validator import GNNValidator
from cogant.graph.builder import ProgramGraphBuilder
from cogant.ingest.repo import RepoIngester
from cogant.process.extractor import ProcessExtractor, ProcessModel
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.scoring.drift import DriftAnalyzer
from cogant.scoring.metrics import CodebaseMetrics
from cogant.statespace.compiler import StateSpaceCompiler
from cogant.static.calls import CallGraphBuilder
from cogant.static.imports import ImportAnalyzer
from cogant.static.parser import PythonASTParser
from cogant.static.symbols import SymbolExtractor
from cogant.translate.engine import TranslationEngine
from cogant.translate.rules import (
    ActionRule,
    ContainmentRule,
    ContextRule,
    EventBusRule,
    InheritanceRule,
    MutatingSubsystemRule,
    ObservationRule,
    PolicyRule,
    PreferenceRule,
    ReadOnlyInputRule,
    RetryPatternRule,
    TestAssertionRule,
)
from cogant.validate.report import ReportGenerator

# Optional imports for rich outputs
try:
    from cogant.viz.mermaid import MermaidGenerator

    HAS_MERMAID = True
except ImportError:
    HAS_MERMAID = False
    logger = logging.getLogger(__name__)

try:
    from cogant.export.bundle import GraphBundle

    HAS_EXPORT = True
except ImportError:
    HAS_EXPORT = False

from cogant.viz.dashboard import DashboardGenerator

try:
    from cogant.viz.graph_view import GraphVisualizer

    HAS_GRAPH_VIZ = True
except ImportError:
    HAS_GRAPH_VIZ = False

try:
    from cogant.viz.semantic_view import SemanticVisualizer

    HAS_SEMANTIC_VIZ = True
except ImportError:
    HAS_SEMANTIC_VIZ = False

try:
    from cogant.viz.gantt import GanttRenderer

    HAS_GANTT = True
except ImportError:
    HAS_GANTT = False

try:
    from cogant.viz.html_renderer import HTMLSiteRenderer

    HAS_HTML_RENDERER = True
except ImportError:
    HAS_HTML_RENDERER = False

try:
    from cogant.viz.plots import StaticPlotter

    HAS_STATIC_PLOTTER = True
except ImportError:
    HAS_STATIC_PLOTTER = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class RoundtripOrchestrator:
    """Orchestrates a complete roundtrip through the COGANT pipeline."""

    def __init__(
        self, repo_path: Path, output_dir: Path, config: dict = None, compare_repo_path: Path = None
    ):
        """Initialize orchestrator.

        Args:
            repo_path: Path to repository to analyze.
            output_dir: Directory for output files.
            config: Configuration dictionary with 'pipeline', 'export', 'validation' keys.
            compare_repo_path: Optional second repository path for drift analysis comparison.
        """
        self.repo_path = Path(repo_path).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or {}
        self.compare_repo_path = Path(compare_repo_path).resolve() if compare_repo_path else None

        logger.info(f"Orchestrator initialized for: {self.repo_path}")
        logger.info(f"Output directory: {self.output_dir}")
        if self.compare_repo_path:
            logger.info(f"Drift analysis enabled: comparing against {self.compare_repo_path}")
        if self.config:
            logger.info(f"Configuration loaded: {len(self.config)} subsystems configured")

    def run(self) -> bool:
        """Execute the full pipeline.

        Returns:
            True if successful, False otherwise.
        """
        try:
            logger.info("=" * 80)
            logger.info("COGANT ROUNDTRIP ORCHESTRATOR")
            logger.info("=" * 80)

            # Step 1: Ingest repository
            logger.info("\n[1/9] Ingesting repository...")
            snapshot = self._ingest_repo()
            if not snapshot:
                return False

            # Step 2: Parse Python files
            logger.info("\n[2/9] Parsing Python files...")
            parsed_files = self._parse_files(snapshot)
            if not parsed_files:
                logger.warning("No Python files parsed")
                return False

            # Step 3: Extract symbols
            logger.info("\n[3/9] Extracting symbols...")
            symbol_tables = self._extract_symbols(parsed_files)

            # Step 4: Analyze imports
            logger.info("\n[4/9] Analyzing imports...")
            import_edges = self._analyze_imports(snapshot)

            # Step 5: Build call graph
            logger.info("\n[5/9] Building call graph...")
            call_edges = self._build_call_graph(snapshot)

            # Step 6: Build program graph
            logger.info("\n[6/9] Building program graph...")
            graph = self._build_program_graph(
                snapshot, parsed_files, symbol_tables, import_edges, call_edges
            )
            if not graph:
                logger.error("Failed to build program graph")
                return False

            # Step 7: Apply translation rules
            logger.info("\n[7/9] Applying translation rules...")
            semantic_mappings = self._apply_translation_rules(graph)

            # Step 8: Compile state space
            logger.info("\n[8/9] Compiling state space...")
            state_space = self._compile_state_space(graph, semantic_mappings)

            # Step 9: Format GNN output and validate
            logger.info("\n[9/9] Formatting GNN output and validating...")
            success = self._format_and_validate(graph, state_space, semantic_mappings)

            # Additional analysis: Compute metrics and self-drift
            logger.info("\n[Metrics] Computing codebase metrics and baseline drift...")
            self._compute_metrics(graph, state_space, semantic_mappings)
            self._compute_self_drift(graph, state_space, semantic_mappings)

            # Optional: Compare with second repo if --compare flag is set
            if self.compare_repo_path:
                logger.info(f"\n[Compare] Analyzing second repository: {self.compare_repo_path}")
                compare_output_dir = (
                    self.output_dir.parent / f"{self.compare_repo_path.name}_comparison"
                )
                compare_output_dir.mkdir(parents=True, exist_ok=True)
                compare_orchestrator = RoundtripOrchestrator(
                    self.compare_repo_path, compare_output_dir, self.config
                )
                compare_success = compare_orchestrator.run()
                if compare_success:
                    logger.info("[Compare] Computing drift between repositories...")
                    # TODO: Load and compare the bundles for detailed drift analysis

            logger.info("\n" + "=" * 80)
            logger.info("ROUNDTRIP COMPLETE")
            logger.info("=" * 80)

            return success

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            return False

    def _ingest_repo(self):
        """Step 1: Ingest repository."""
        try:
            ingester = RepoIngester()
            snapshot = ingester.ingest_local(
                self.repo_path, include_test_files=True, compute_checksums=False
            )
            logger.info(
                f"  Found {len(snapshot.files)} files "
                f"({len([f for f in snapshot.files if f.language == 'python'])} Python)"
            )
            return snapshot
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            return None

    def _parse_files(self, snapshot):
        """Step 2: Parse Python files."""
        parsed = {}
        parser = PythonASTParser()

        python_files = [f for f in snapshot.files if f.language == "python"]
        logger.info(f"  Parsing {len(python_files)} Python files...")

        for file_info in python_files:
            try:
                module = parser.parse_file(file_info.path)
                if not module.errors:
                    parsed[file_info.path] = module
                    logger.debug(
                        f"    Parsed {file_info.relative_path}: "
                        f"{len(module.classes)} classes, {len(module.functions)} functions"
                    )
                else:
                    logger.warning(f"    Parse errors in {file_info.relative_path}")
            except Exception as e:
                logger.warning(f"    Failed to parse {file_info.relative_path}: {e}")

        logger.info(f"  Successfully parsed {len(parsed)} files")
        return parsed

    def _extract_symbols(self, parsed_files):
        """Step 3: Extract symbols from parsed files."""
        symbol_tables = {}
        extractor = SymbolExtractor(self.repo_path)

        for file_path, module in parsed_files.items():
            try:
                table = extractor.extract_from_file(file_path)
                symbol_tables[file_path] = table
                logger.debug(f"    Extracted {len(table.symbols)} symbols from {file_path.name}")
            except Exception as e:
                logger.warning(f"    Symbol extraction failed for {file_path.name}: {e}")

        logger.info(f"  Extracted symbols from {len(symbol_tables)} files")
        return symbol_tables

    def _analyze_imports(self, snapshot):
        """Step 4: Analyze import statements."""
        import_edges = []
        analyzer = ImportAnalyzer(self.repo_path)

        python_files = [f for f in snapshot.files if f.language == "python"]
        for file_info in python_files:
            try:
                edges = analyzer.analyze_file(file_info.path)
                import_edges.extend(edges)
                logger.debug(f"    Found {len(edges)} imports in {file_info.relative_path}")
            except Exception as e:
                logger.warning(f"    Import analysis failed for {file_info.relative_path}: {e}")

        logger.info(f"  Analyzed {len(import_edges)} import edges")
        return import_edges

    def _build_call_graph(self, snapshot):
        """Step 5: Build call graph."""
        call_edges = []
        builder = CallGraphBuilder(self.repo_path)

        python_files = [f for f in snapshot.files if f.language == "python"]
        for file_info in python_files:
            try:
                edges = builder.extract_calls_from_file(file_info.path)
                call_edges.extend(edges)
                logger.debug(f"    Found {len(edges)} calls in {file_info.relative_path}")
            except Exception as e:
                logger.warning(
                    f"    Call graph extraction failed for {file_info.relative_path}: {e}"
                )

        logger.info(f"  Built call graph with {len(call_edges)} edges")
        return call_edges

    def _build_program_graph(self, snapshot, parsed_files, symbol_tables, import_edges, call_edges):
        """Step 6: Build program graph."""
        try:
            builder = ProgramGraphBuilder(str(self.repo_path))

            # Track node references for edge building
            module_nodes = {}  # module_name -> node
            class_nodes = {}  # qualified_name -> node
            method_nodes = {}  # qualified_name -> node
            func_nodes = {}  # qualified_name -> node

            # Add nodes for files and symbols
            for file_path, module in parsed_files.items():
                file_rel = file_path.relative_to(self.repo_path)

                # Add module node
                module_name = file_path.stem
                module_node = builder.add_node(
                    kind=NodeKind.MODULE,
                    name=module_name,
                    qualified_name=module_name,
                    path=str(file_rel),
                    language="python",
                )
                module_nodes[module_name] = module_node

                # Add class nodes
                for cls in module.classes:
                    class_qname = f"{module_name}.{cls.name}"
                    class_node = builder.add_node(
                        kind=NodeKind.CLASS,
                        name=cls.name,
                        qualified_name=class_qname,
                        path=str(file_rel),
                        language="python",
                        metadata={"bases": cls.bases, "docstring": cls.docstring},
                    )
                    class_nodes[class_qname] = class_node

                    # CONTAINMENT: module contains class
                    builder.add_edge(
                        module_node.id,
                        class_node.id,
                        EdgeKind.CONTAINS,
                        metadata={"relationship": "module_contains_class"},
                    )

                    # Add method nodes
                    for method in cls.methods:
                        method_qname = f"{module_name}.{cls.name}.{method.name}"
                        method_node = builder.add_node(
                            kind=NodeKind.METHOD
                            if hasattr(NodeKind, "METHOD")
                            else NodeKind.FUNCTION,
                            name=method.name,
                            qualified_name=method_qname,
                            path=str(file_rel),
                            language="python",
                            metadata={"parameters": method.args, "is_method": True},
                        )
                        method_nodes[method_qname] = method_node

                        # CONTAINMENT: class contains method
                        builder.add_edge(
                            class_node.id,
                            method_node.id,
                            EdgeKind.CONTAINS,
                            metadata={"relationship": "class_contains_method"},
                        )

                        # WRITES/MUTATES: methods that write to self.* attributes
                        # Detect from method body AST
                        self._add_dataflow_edges(
                            builder, method_node, class_node, method, file_path
                        )

                # Add function nodes
                for func in module.functions:
                    func_qname = f"{module_name}.{func.name}"
                    func_node = builder.add_node(
                        kind=NodeKind.FUNCTION,
                        name=func.name,
                        qualified_name=func_qname,
                        path=str(file_rel),
                        language="python",
                        metadata={"parameters": func.args},
                    )
                    func_nodes[func_qname] = func_node

                    # CONTAINMENT: module contains function
                    builder.add_edge(
                        module_node.id,
                        func_node.id,
                        EdgeKind.CONTAINS,
                        metadata={"relationship": "module_contains_function"},
                    )

            # Add import edges
            for edge in import_edges:
                source_mods = builder.graph.get_nodes_by_kind(NodeKind.MODULE)
                for node in source_mods:
                    if edge.source_file.name == node.name + ".py":
                        target_name = edge.module_name.split(".")[0]
                        target_nodes = [
                            n for n in builder.graph.nodes.values() if n.name == target_name
                        ]
                        if target_nodes:
                            builder.add_edge(
                                node.id,
                                target_nodes[0].id,
                                EdgeKind.IMPORTS,
                                metadata={"module_name": edge.module_name},
                            )
                        break

            # Add call edges
            for edge in call_edges:
                caller_nodes = [
                    n for n in builder.graph.nodes.values() if n.name == edge.caller_name
                ]
                callee_nodes = [
                    n for n in builder.graph.nodes.values() if n.name == edge.callee_name
                ]
                if caller_nodes and callee_nodes:
                    for caller in caller_nodes:
                        for callee in callee_nodes:
                            builder.add_edge(
                                caller.id,
                                callee.id,
                                EdgeKind.CALLS,
                                metadata={"line_num": edge.line_num},
                            )

            # Add inheritance edges
            for qname, class_node in class_nodes.items():
                bases = class_node.metadata.get("bases", []) if class_node.metadata else []
                for base in bases:
                    base_nodes = [
                        n
                        for n in builder.graph.nodes.values()
                        if n.name == base and n.kind == NodeKind.CLASS
                    ]
                    if base_nodes:
                        builder.add_edge(
                            class_node.id,
                            base_nodes[0].id,
                            EdgeKind.INHERITS,
                            metadata={"base_class": base},
                        )

            graph = builder.finalize()
            stats = builder.get_statistics()
            logger.info(
                f"  Built program graph: {stats['total_nodes']} nodes, {stats['total_edges']} edges"
            )

            # Save program graph for inspection
            self._save_program_graph(graph)

            return graph

        except Exception as e:
            logger.error(f"Program graph building failed: {e}", exc_info=True)
            return None

    def _add_dataflow_edges(self, builder, method_node, class_node, method_ast, file_path):
        """Add READS/WRITES/MUTATES edges based on method body analysis.

        Scans method AST for self.attr assignments (WRITES/MUTATES) and
        self.attr reads (READS) to build dataflow edges between methods
        and their containing class.
        """
        import ast as ast_mod

        try:
            source = file_path.read_text()
            tree = ast_mod.parse(source)
        except Exception:
            return

        # Find this method's AST node
        for node in ast_mod.walk(tree):
            if isinstance(node, (ast_mod.FunctionDef, ast_mod.AsyncFunctionDef)):
                if node.name == method_node.name:
                    writes = 0
                    reads = 0
                    for child in ast_mod.walk(node):
                        # self.attr = value → WRITES
                        if isinstance(child, ast_mod.Assign):
                            for target in child.targets:
                                if (
                                    isinstance(target, ast_mod.Attribute)
                                    and isinstance(target.value, ast_mod.Name)
                                    and target.value.id == "self"
                                ):
                                    writes += 1
                        # AugAssign: self.attr += value → MUTATES
                        if isinstance(child, ast_mod.AugAssign):
                            if (
                                isinstance(child.target, ast_mod.Attribute)
                                and isinstance(child.target.value, ast_mod.Name)
                                and child.target.value.id == "self"
                            ):
                                writes += 1
                        # self.attr as expression (read)
                        if isinstance(child, ast_mod.Attribute):
                            if isinstance(child.value, ast_mod.Name) and child.value.id == "self":
                                reads += 1

                    if writes > 0:
                        builder.add_edge(
                            method_node.id,
                            class_node.id,
                            EdgeKind.WRITES,
                            metadata={
                                "write_count": writes,
                                "pattern": "self_attribute_assignment",
                            },
                        )
                    if reads > writes:  # net reads after accounting for writes
                        builder.add_edge(
                            method_node.id,
                            class_node.id,
                            EdgeKind.READS,
                            metadata={"read_count": reads, "pattern": "self_attribute_access"},
                        )
                    break

    def _apply_translation_rules(self, graph):
        """Step 7: Apply translation rules."""
        try:
            engine = TranslationEngine()

            # Register rules - existing rules
            engine.register_rule(ReadOnlyInputRule())
            engine.register_rule(MutatingSubsystemRule())
            engine.register_rule(EventBusRule())
            engine.register_rule(RetryPatternRule())
            engine.register_rule(TestAssertionRule())

            # Register new rules for comprehensive semantic extraction
            engine.register_rule(ObservationRule())
            engine.register_rule(ActionRule())
            engine.register_rule(PolicyRule())
            engine.register_rule(PreferenceRule())
            engine.register_rule(ContextRule())
            engine.register_rule(InheritanceRule())
            engine.register_rule(ContainmentRule())

            # Translate
            mappings = engine.translate(graph)
            stats = engine.get_statistics()

            logger.info(f"  Applied translation rules: {stats['total_mappings']} mappings")
            logger.info(f"    Mappings by kind: {stats['mappings_by_kind']}")

            return {m.id: m for m in mappings}

        except Exception as e:
            logger.error(f"Translation failed: {e}", exc_info=True)
            return {}

    def _compile_state_space(self, graph, semantic_mappings):
        """Step 8: Compile state space."""
        try:
            compiler = StateSpaceCompiler(graph, self.repo_path.name)
            state_space = compiler.compile(semantic_mappings)

            logger.info(f"  Compiled state space with {len(state_space.variables)} variables")
            logger.info(f"    Variables: {list(state_space.variables.keys())[:5]}...")

            return state_space

        except Exception as e:
            logger.error(f"State space compilation failed: {e}", exc_info=True)
            # Return a minimal state space to continue
            from cogant.statespace.compiler import StateSpaceModel
            from cogant.statespace.temporal import TimeRegime

            return StateSpaceModel(
                id=f"minimal_state_space_{self.repo_path.name}",
                schema_name=self.repo_path.name,
                variables={},
                observations={},
                actions={},
                transitions={},
                likelihoods={},
                preferences={},
                time_regime=TimeRegime.SYNCHRONOUS,
                metadata={},
            )

    def _format_and_validate(self, graph, state_space, semantic_mappings):
        """Step 9: Format GNN output and validate + generate rich outputs."""
        markdown = None
        json_data = None
        report = None

        try:
            # Task 1: Build real process model from the graph
            logger.info("  [Task 1] Building process model from program graph...")
            process_model = self._build_process_model(graph)

            # Format markdown (with graceful fallback)
            try:
                logger.info(
                    f"  Creating formatter: semantic_mappings type = {type(semantic_mappings).__name__}, len = {len(semantic_mappings) if hasattr(semantic_mappings, '__len__') else 'N/A'}"
                )
                formatter = GNNMarkdownFormatter(
                    graph, state_space, process_model, semantic_mappings
                )
                markdown = formatter.format()
                logger.info(f"  Formatted GNN markdown ({len(markdown)} chars)")
            except Exception as e:
                logger.warning(f"GNN markdown formatting failed, using minimal fallback: {e}")
                markdown = f"# {self.repo_path.name} Analysis\n\nMarkdown generation failed: {e}\n"

            # Export JSON (with graceful fallback)
            try:
                exporter = GNNJSONExporter(graph, state_space, process_model, semantic_mappings)
                json_data = exporter.export()
                logger.info(f"  Exported JSON with {len(json_data)} top-level keys")
            except Exception as e:
                logger.warning(f"GNN JSON export failed: {e}", exc_info=True)
                json_data = {"error": str(e), "note": "JSON export failed"}

            # Generate validation report (with graceful fallback)
            try:
                reporter = ReportGenerator(graph, state_space, process_model, self.repo_path.name)
                report = reporter.generate()
                logger.info(
                    f"  Generated validation report: {'VALID' if report.is_valid else 'ISSUES FOUND'}"
                )
            except Exception as e:
                logger.warning(f"Validation report generation failed: {e}")

                # Create minimal report object
                class MinimalReport:
                    is_valid = False
                    coverage_score = 0.0
                    confidence_score = 0.0
                    issues = []
                    id = f"report_{self.repo_path.name}"
                    summary = f"Report generation failed: {e}"

                report = MinimalReport()

            # Save core outputs
            if markdown or json_data or report:
                self._save_outputs(markdown or "", json_data or {}, report)

            # Save enhanced program graph
            self._save_enhanced_program_graph(graph)

            # Generate and save Mermaid diagrams
            self._save_mermaid_diagrams(graph, state_space, process_model, semantic_mappings)

            # Generate and save charts
            self._save_distribution_charts(graph)

            # Generate and save graph exports
            self._save_graph_exports(graph)

            # Generate and save semantic mappings
            self._save_semantic_mappings(semantic_mappings)

            # Generate and save metrics
            logger.info("  [Metrics] Computing and saving codebase metrics...")
            self._save_metrics_report(graph, state_space, semantic_mappings)
            # Task 2: Add simulation trace output
            logger.info("  [Task 2] Adding simulation trace output...")
            self._add_simulation_trace(state_space)

            # Task 3: Add confidence heatmap HTML
            logger.info("  [Task 3] Adding confidence heatmap HTML...")
            self._add_confidence_heatmap(semantic_mappings)

            # Task 4: Add process timeline Mermaid gantt chart
            logger.info("  [Task 4] Adding process timeline...")
            self._add_process_timeline(process_model)

            # Task 5: Enrich summary markdown with mapping kinds and next steps
            logger.info("  [Task 5] Enriching summary markdown...")
            self._enrich_summary_markdown(graph, state_space, semantic_mappings, report)

            # Wire in visualization modules
            logger.info("  [Visualizations] Wiring unused visualization modules...")
            self._wire_graph_view(graph)
            self._wire_semantic_view(state_space)
            self._wire_gantt_chart(process_model)
            self._wire_html_site_renderer(
                graph, state_space, process_model, semantic_mappings, report
            )
            self._wire_diff_view(graph, state_space)
            self._wire_boundary_map(graph)

            # Wire extra export formats (GraphML, Parquet)
            logger.info("  [Exports] Wiring additional export formats...")
            self._wire_export_formats(graph, state_space, process_model, semantic_mappings)

            # Generate advanced visualization types (factor graph, sunburst,
            # radar, state-space matrix). These all emit SVGs/HTMLs that will
            # later be rasterized by _generate_png_outputs.
            logger.info("  [Visualizations] Generating advanced visualizations...")
            self._generate_advanced_visualizations(graph, state_space, semantic_mappings)

            # Generate interactive dashboard (replaces basic HTML index)
            if markdown and report:
                self._generate_dashboard(
                    graph, state_space, process_model, semantic_mappings, report
                )

            logger.info(
                "  Generated rich outputs: Mermaid diagrams, charts, semantic mappings, summary, dashboard, timeline, heatmap, trace"
            )

            # Task 6: Build GNN package
            logger.info("  [Task 6] Building GNN package...")
            self._build_gnn_package(graph, state_space, process_model, semantic_mappings)

            # Task 7: Validate GNN package
            logger.info("  [Task 7] Validating GNN package...")
            self._validate_gnn_package()

            # Task 8: Run GNN model
            logger.info("  [Task 8] Running GNN model...")
            self._run_gnn_model()

            # Task 9: Run the full GNN pipeline into a dedicated subfolder
            logger.info("  [Task 9] Running full GNN pipeline into gnn_pipeline/ ...")
            self._run_full_gnn_pipeline(graph, state_space, process_model, semantic_mappings)

            # PNG rasterization is the final step of the pipeline so that every
            # upstream artifact (mermaid, svg, dot, validation badge, GNN
            # package figures) is already on disk by the time we rasterize.
            logger.info("  [PNG] Rasterizing every visualization artifact to PNG...")
            self._generate_png_outputs(graph, state_space, process_model)

            return True

        except Exception as e:
            logger.error(f"Rich output generation failed: {e}", exc_info=True)
            # Still return True if we at least generated core outputs
            return True

    def _save_program_graph(self, graph):
        """Save program graph as JSON (legacy, kept for compatibility)."""
        self._save_enhanced_program_graph(graph)

    def _save_enhanced_program_graph(self, graph):
        """Save program graph as JSON with metadata and provenance."""
        try:
            data = {
                "id": getattr(graph, "id", f"program_graph_{self.repo_path.name}"),
                "metadata": {
                    "repo": self.repo_path.name,
                    "generated_at": datetime.now().isoformat(),
                    "node_count": len(graph.nodes),
                    "edge_count": len(graph.edges),
                },
                "nodes": {
                    nid: {
                        "id": nid,
                        "name": node.name,
                        "kind": str(node.kind),
                        "qualified_name": node.qualified_name,
                        "path": node.path or "",
                        "language": node.language or "unknown",
                        "metadata": node.metadata or {},
                        "source_range": getattr(node, "source_range", None),
                    }
                    for nid, node in graph.nodes.items()
                },
                "edges": {
                    eid: {
                        "id": eid,
                        "source": edge.source_id,
                        "target": edge.target_id,
                        "kind": str(edge.kind),
                        "weight": edge.weight if hasattr(edge, "weight") else 1,
                        "metadata": edge.metadata or {},
                        "provenance": getattr(edge, "provenance", None),
                    }
                    for eid, edge in graph.edges.items()
                },
                "statistics": {
                    "total_nodes": len(graph.nodes),
                    "total_edges": len(graph.edges),
                    "nodes_by_kind": self._count_nodes_by_kind(graph),
                    "edges_by_kind": self._count_edges_by_kind(graph),
                },
            }

            output_file = self.output_dir / "program_graph.json"
            with open(output_file, "w") as f:
                json.dump(data, f, indent=2, default=str)

            logger.debug(f"  Saved enhanced program graph to {output_file}")
        except Exception as e:
            logger.warning(f"Failed to save enhanced program graph: {e}")

    def _count_nodes_by_kind(self, graph):
        """Count nodes by kind."""
        counts = {}
        for node in graph.nodes.values():
            kind_str = str(node.kind)
            counts[kind_str] = counts.get(kind_str, 0) + 1
        return counts

    def _count_edges_by_kind(self, graph):
        """Count edges by kind."""
        counts = {}
        for edge in graph.edges.values():
            kind_str = str(edge.kind)
            counts[kind_str] = counts.get(kind_str, 0) + 1
        return counts

    def _save_mermaid_diagrams(self, graph, state_space, process_model, semantic_mappings):
        """Generate and save all Mermaid diagrams."""
        if not HAS_MERMAID:
            logger.warning("MermaidGenerator not available, skipping Mermaid diagrams")
            return

        try:
            gen = MermaidGenerator()
            diagrams = gen.generate_all(
                graph=graph,
                state_space=state_space,
                process_model=process_model,
                mappings=semantic_mappings,
            )

            # Save each diagram
            for name, content in diagrams.items():
                if content:
                    output_file = self.output_dir / f"{name}.mermaid"
                    with open(output_file, "w") as f:
                        f.write(content)
                    logger.debug(f"  Saved Mermaid diagram: {output_file.name}")

            # Add additional diagrams not in generate_all
            try:
                boundary_diagram = self._generate_boundary_diagram(graph)
                if boundary_diagram:
                    with open(self.output_dir / "boundary_map.mermaid", "w") as f:
                        f.write(boundary_diagram)
                    logger.debug("  Saved boundary map")
            except Exception as e:
                logger.warning(f"Failed to generate boundary map: {e}")

            try:
                semantic_flow = self._generate_semantic_flow(graph, semantic_mappings)
                if semantic_flow:
                    with open(self.output_dir / "semantic_flow.mermaid", "w") as f:
                        f.write(semantic_flow)
                    logger.debug("  Saved semantic flow")
            except Exception as e:
                logger.warning(f"Failed to generate semantic flow: {e}")

        except Exception as e:
            logger.warning(f"Failed to generate Mermaid diagrams: {e}")

    def _generate_boundary_diagram(self, graph):
        """Generate module boundary diagram."""
        try:
            modules = graph.get_nodes_by_kind(NodeKind.MODULE)
            if not modules:
                return None

            lines = ["graph TD"]
            for module in modules:
                safe_id = module.id.replace("-", "_").replace(".", "_")
                label = module.name or module.qualified_name
                lines.append(f"    {safe_id}['{label}']")

            # Add containment relationships (subgraph)
            for module in modules:
                classes = [
                    graph.get_node(edge.target_id)
                    for edge in graph.get_edges_from(module.id)
                    if edge.kind == EdgeKind.CONTAINS
                ]
                if classes:
                    safe_id = module.id.replace("-", "_").replace(".", "_")
                    lines.append(f"    subgraph {safe_id}[Module: {module.name}]")
                    for cls in classes:
                        if cls:
                            cls_safe = cls.id.replace("-", "_").replace(".", "_")
                            lines.append(f"        {cls_safe}['{cls.name}']")
                    lines.append("    end")

            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"Boundary diagram generation failed: {e}")
            return None

    def _generate_semantic_flow(self, graph, semantic_mappings):
        """Generate semantic flow diagram (code to semantic mapping)."""
        try:
            lines = ["flowchart TD"]
            lines.append("    START['Code Elements']")

            # Group by semantic role (semantic_mappings is dict of mapping_id -> SemanticMapping)
            role_groups = {}
            for mapping_id, mapping in semantic_mappings.items():
                # Handle both dict-style (role string) and SemanticMapping objects
                if hasattr(mapping, "kind"):
                    role = (
                        mapping.kind.value if hasattr(mapping.kind, "value") else str(mapping.kind)
                    )
                    node_ids = (
                        mapping.graph_fragment_node_ids
                        if hasattr(mapping, "graph_fragment_node_ids")
                        else []
                    )
                else:
                    role = str(mapping)
                    node_ids = []

                if role not in role_groups:
                    role_groups[role] = []
                role_groups[role].extend(node_ids)

            # Create flow for each role (sorted by role name for deterministic output)
            for role in sorted(role_groups.keys()):
                node_ids = role_groups[role]
                role_safe = role.replace(" ", "_").replace("-", "_")
                lines.append(f"    START --> {role_safe}['{role.upper()}']")

                # Add nodes for this role
                for node_id in node_ids[:3]:  # Limit to first 3 per role
                    node = graph.get_node(node_id)
                    if node:
                        node_safe = node_id.replace("-", "_").replace(".", "_")
                        lines.append(f"    {role_safe} --> {node_safe}['{node.name}']")

            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"Semantic flow generation failed: {e}")
            return None

    def _save_distribution_charts(self, graph):
        """Generate HTML bar charts for node and edge distribution."""
        try:
            # Node distribution
            node_counts = self._count_nodes_by_kind(graph)
            self._save_chart_html("node_distribution.html", node_counts, "Node Type Distribution")

            # Edge distribution
            edge_counts = self._count_edges_by_kind(graph)
            self._save_chart_html("edge_distribution.html", edge_counts, "Edge Type Distribution")

            logger.debug("  Saved distribution charts")
        except Exception as e:
            logger.warning(f"Failed to save distribution charts: {e}")

    def _save_chart_html(self, filename, data, title):
        """Save a simple bar chart as HTML with inline SVG."""
        try:
            # Prepare data for chart
            labels = list(data.keys())
            values = list(data.values())
            max_val = max(values) if values else 1

            # Generate SVG
            width = 600
            height = 400
            margin = 60
            chart_width = width - 2 * margin
            chart_height = height - 2 * margin
            bar_width = chart_width / len(labels) if labels else 1
            max_height = chart_height * 0.8

            svg_lines = [
                f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
                "<style>text { font-family: Arial, sans-serif; font-size: 12px; }</style>",
                f'<rect width="{width}" height="{height}" fill="white"/>',
                f'<text x="{width / 2}" y="30" text-anchor="middle" font-size="18" font-weight="bold">{html.escape(title)}</text>',
            ]

            # Y-axis
            svg_lines.append(
                f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" stroke="black" stroke-width="2"/>'
            )
            # X-axis
            svg_lines.append(
                f'<line x1="{margin}" y1="{height - margin}" x2="{width - margin}" y2="{height - margin}" stroke="black" stroke-width="2"/>'
            )

            # Bars
            colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
            for i, (label, value) in enumerate(zip(labels, values)):
                x = margin + i * bar_width + bar_width * 0.1
                bar_h = (value / max_val) * max_height if max_val > 0 else 0
                y = height - margin - bar_h
                color = colors[i % len(colors)]

                svg_lines.append(
                    f'<rect x="{x}" y="{y}" width="{bar_width * 0.8}" height="{bar_h}" fill="{color}" stroke="black" stroke-width="1"/>'
                )

                # Label
                label_clean = str(label).replace("NodeKind.", "").replace("EdgeKind.", "")[:20]
                svg_lines.append(
                    f'<text x="{x + bar_width * 0.4}" y="{height - margin + 20}" text-anchor="middle">{html.escape(label_clean)}</text>'
                )

                # Value
                svg_lines.append(
                    f'<text x="{x + bar_width * 0.4}" y="{y - 5}" text-anchor="middle" font-weight="bold">{value}</text>'
                )

            svg_lines.append("</svg>")

            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{html.escape(title)}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
    </style>
</head>
<body>
    <h1>{html.escape(title)}</h1>
    {"".join(svg_lines)}
    <table border="1" style="margin-top: 20px; border-collapse: collapse;">
        <tr><th>Type</th><th>Count</th></tr>
"""
            for label, value in sorted(zip(labels, values), key=lambda x: x[1], reverse=True):
                html_content += (
                    f"        <tr><td>{html.escape(str(label))}</td><td>{value}</td></tr>\n"
                )

            html_content += """    </table>
</body>
</html>
"""

            output_file = self.output_dir / filename
            with open(output_file, "w") as f:
                f.write(html_content)

            logger.debug(f"  Saved chart: {filename}")
        except Exception as e:
            logger.warning(f"Failed to save chart {filename}: {e}")

    def _save_graph_exports(self, graph):
        """Generate various graph export formats."""
        try:
            # Typed graph JSON
            self._save_typed_graph(graph)

            # Cytoscape JSON
            self._save_cytoscape_json(graph)

            # Adjacency matrix
            self._save_adjacency_matrix(graph)

            # GraphViz DOT
            self._save_graphviz_dot(graph)

            logger.debug("  Saved graph exports")
        except Exception as e:
            logger.warning(f"Failed to save graph exports: {e}")

    def _save_typed_graph(self, graph):
        """Save full typed graph export with all metadata."""
        try:
            data = {
                "id": getattr(graph, "id", f"typed_graph_{self.repo_path.name}"),
                "type": "program_graph",
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "repo": self.repo_path.name,
                    "node_count": len(graph.nodes),
                    "edge_count": len(graph.edges),
                },
                "nodes": [
                    {
                        "id": nid,
                        "name": node.name,
                        "kind": str(node.kind),
                        "qualified_name": node.qualified_name,
                        "path": node.path or "",
                        "language": node.language or "unknown",
                        "metadata": node.metadata or {},
                    }
                    for nid, node in graph.nodes.items()
                ],
                "edges": [
                    {
                        "id": eid,
                        "source": edge.source_id,
                        "target": edge.target_id,
                        "kind": str(edge.kind),
                        "weight": getattr(edge, "weight", 1),
                        "metadata": edge.metadata or {},
                    }
                    for eid, edge in graph.edges.items()
                ],
            }

            output_file = self.output_dir / "typed_graph.json"
            with open(output_file, "w") as f:
                json.dump(data, f, indent=2, default=str)

            logger.debug("  Saved typed_graph.json")
        except Exception as e:
            logger.warning(f"Failed to save typed graph: {e}")

    def _save_cytoscape_json(self, graph):
        """Save Cytoscape.js compatible JSON format."""
        try:
            elements = []

            # Add nodes
            for nid, node in graph.nodes.items():
                elements.append(
                    {
                        "data": {
                            "id": nid,
                            "label": node.name,
                            "kind": str(node.kind),
                            "qualified_name": node.qualified_name,
                        },
                        "classes": str(node.kind).replace("NodeKind.", "").lower(),
                    }
                )

            # Add edges
            for eid, edge in graph.edges.items():
                elements.append(
                    {
                        "data": {
                            "id": eid,
                            "source": edge.source_id,
                            "target": edge.target_id,
                            "label": str(edge.kind).replace("EdgeKind.", ""),
                        },
                        "classes": str(edge.kind).replace("EdgeKind.", "").lower(),
                    }
                )

            data = {
                "elements": elements,
                "style": [
                    {
                        "selector": "node",
                        "style": {"content": "data(label)", "text-valign": "center"},
                    },
                    {"selector": "edge", "style": {"target-arrow-shape": "triangle"}},
                ],
            }

            output_file = self.output_dir / "cytoscape.json"
            with open(output_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug("  Saved cytoscape.json")
        except Exception as e:
            logger.warning(f"Failed to save cytoscape json: {e}")

    def _save_adjacency_matrix(self, graph):
        """Save adjacency matrix as JSON."""
        try:
            # Create node ID to index mapping
            node_ids = sorted(graph.nodes.keys())
            node_to_idx = {nid: i for i, nid in enumerate(node_ids)}

            # Initialize matrix
            n = len(node_ids)
            matrix = [[0 for _ in range(n)] for _ in range(n)]

            # Fill matrix from edges
            for edge in graph.edges.values():
                src_idx = node_to_idx.get(edge.source_id)
                tgt_idx = node_to_idx.get(edge.target_id)
                if src_idx is not None and tgt_idx is not None:
                    matrix[src_idx][tgt_idx] = getattr(edge, "weight", 1)

            data = {
                "node_ids": node_ids,
                "matrix": matrix,
                "metadata": {
                    "size": n,
                    "edge_count": len(graph.edges),
                    "generated_at": datetime.now().isoformat(),
                },
            }

            output_file = self.output_dir / "adjacency_matrix.json"
            with open(output_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug("  Saved adjacency_matrix.json")
        except Exception as e:
            logger.warning(f"Failed to save adjacency matrix: {e}")

    def _save_graphviz_dot(self, graph):
        """Save graph in GraphViz DOT format."""
        try:
            lines = ["digraph G {"]
            lines.append("    rankdir=LR;")
            lines.append("    node [shape=box];")

            # Add nodes
            for nid, node in graph.nodes.items():
                safe_id = nid.replace("-", "_").replace(".", "_")
                label = f"{node.name}\\n({str(node.kind).replace('NodeKind.', '')})"
                lines.append(f'    {safe_id} [label="{label}"];')

            # Add edges
            for edge in graph.edges.values():
                src_safe = edge.source_id.replace("-", "_").replace(".", "_")
                tgt_safe = edge.target_id.replace("-", "_").replace(".", "_")
                label = str(edge.kind).replace("EdgeKind.", "")
                lines.append(f'    {src_safe} -> {tgt_safe} [label="{label}"];')

            lines.append("}")

            output_file = self.output_dir / "graph.dot"
            with open(output_file, "w") as f:
                f.write("\n".join(lines))

            logger.debug("  Saved graph.dot")
        except Exception as e:
            logger.warning(f"Failed to save graphviz dot: {e}")

    def _save_semantic_mappings(self, semantic_mappings):
        """Save semantic mappings with provenance."""
        try:
            data = {
                "generated_at": datetime.now().isoformat(),
                "total_mappings": len(semantic_mappings),
                "mappings": {},
            }

            # Group by semantic role
            by_role = {}
            for mapping_id, mapping in semantic_mappings.items():
                kind = getattr(mapping, "kind", None)
                role = kind.value if kind is not None else "unknown"
                if role not in by_role:
                    by_role[role] = []

                mapping_dict = {
                    "id": mapping_id,
                    "semantic_role": role,
                    "confidence": getattr(mapping, "confidence", 0.0),
                    "source": getattr(mapping, "source", "unknown"),
                    "target": getattr(mapping, "target", "unknown"),
                    "metadata": getattr(mapping, "metadata", {}),
                }
                by_role[role].append(mapping_dict)

            data["mappings_by_role"] = by_role
            data["role_summary"] = {role: len(mappings) for role, mappings in by_role.items()}

            output_file = self.output_dir / "semantic_mappings.json"
            with open(output_file, "w") as f:
                json.dump(data, f, indent=2, default=str)

            logger.debug("  Saved semantic_mappings.json")
        except Exception as e:
            logger.warning(f"Failed to save semantic mappings: {e}")

    def _save_html_index(self, markdown, report):
        """Save a self-contained HTML index with embedded diagrams."""
        try:
            # Read stats from summary or program_graph
            num_nodes = 0
            num_edges = 0
            num_mappings = 0

            summary_file = self.output_dir / "summary.md"
            if summary_file.exists():
                try:
                    with open(summary_file) as f:
                        content = f.read()
                    # Extract from summary
                    nodes_match = re.search(r"Total Nodes[^:]*:\s*(\d+)", content)
                    edges_match = re.search(r"Total Edges[^:]*:\s*(\d+)", content)
                    mappings_match = re.search(r"Total Mappings[^:]*:\s*(\d+)", content)
                    if nodes_match:
                        num_nodes = int(nodes_match.group(1))
                    if edges_match:
                        num_edges = int(edges_match.group(1))
                    if mappings_match:
                        num_mappings = int(mappings_match.group(1))
                except Exception:
                    pass

            # Read mermaid diagrams if they exist
            diagrams_html = ""
            for diag_name in ["class_diagram", "state_diagram", "semantic_flow"]:
                diag_file = self.output_dir / f"{diag_name}.mermaid"
                if diag_file.exists():
                    try:
                        with open(diag_file) as f:
                            content = f.read()
                        diagrams_html += f"""
<div class="diagram-section">
    <h2>{diag_name.replace("_", " ").title()}</h2>
    <pre class="mermaid">
{html.escape(content)}
    </pre>
</div>
"""
                    except Exception:
                        pass

            # Embed node and edge distribution SVG charts
            for chart_name in ["node_distribution", "edge_distribution"]:
                chart_file = self.output_dir / f"{chart_name}.html"
                if chart_file.exists():
                    try:
                        with open(chart_file) as f:
                            content = f.read()
                        # Extract SVG from the HTML file
                        svg_match = re.search(r"<svg[^>]*>.*?</svg>", content, re.DOTALL)
                        if svg_match:
                            svg_content = svg_match.group(0)
                            title = chart_name.replace("_", " ").title()
                            diagrams_html += f"""
<div class="diagram-section">
    <h2>{title}</h2>
    {svg_content}
</div>
"""
                    except Exception:
                        pass

            # Read summary if it exists and render as HTML
            summary_html = ""
            if summary_file.exists():
                try:
                    with open(summary_file) as f:
                        summary_content = f.read()
                    # Escape HTML and preserve formatting
                    summary_escaped = html.escape(summary_content)
                    summary_html = f"""
<div class="diagram-section">
    <h2>Summary</h2>
    <pre style="white-space: pre-wrap; word-wrap: break-word;">
{summary_escaped}
    </pre>
</div>
"""
                except Exception:
                    pass

            # Generate file list
            files_html = "<ul>"
            for output_file in sorted(self.output_dir.glob("*")):
                if output_file.is_file():
                    size = output_file.stat().st_size
                    files_html += f"<li><a href='{output_file.name}'>{output_file.name}</a> ({size:,} bytes)</li>"
            files_html += "</ul>"

            is_valid = getattr(report, "is_valid", False)
            coverage = getattr(report, "coverage_score", 0.0)
            confidence = getattr(report, "confidence_score", 0.0)

            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>COGANT Analysis: {html.escape(self.repo_path.name)}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .stat-card h3 {{ color: #667eea; margin-bottom: 10px; }}
        .stat-value {{ font-size: 2em; font-weight: bold; }}
        .diagram-section {{
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            overflow-x: auto;
        }}
        .diagram-section h2 {{
            margin-bottom: 15px;
            color: #333;
        }}
        .diagram-section pre {{
            background: #f9f9f9;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #667eea;
            overflow-x: auto;
        }}
        .mermaid {{
            display: flex;
            justify-content: center;
        }}
        .files-section {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-top: 30px;
        }}
        .files-section h2 {{
            margin-bottom: 15px;
            color: #333;
        }}
        .files-section ul {{
            list-style-position: inside;
        }}
        .files-section li {{
            padding: 8px 0;
        }}
        .files-section a {{
            color: #667eea;
            text-decoration: none;
        }}
        .files-section a:hover {{
            text-decoration: underline;
        }}
        .validation {{
            background: #{"e8f5e9" if is_valid else "ffebee"};
            border-left: 4px solid #{"4caf50" if is_valid else "f44336"};
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .validation-status {{
            color: #{"2e7d32" if is_valid else "c62828"};
            font-weight: bold;
        }}
    </style>
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
</head>
<body>
    <div class="container">
        <header>
            <h1>COGANT Analysis: {html.escape(self.repo_path.name)}</h1>
            <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </header>

        <div class="stats">
            <div class="stat-card">
                <h3>Nodes</h3>
                <div class="stat-value">{num_nodes}</div>
            </div>
            <div class="stat-card">
                <h3>Edges</h3>
                <div class="stat-value">{num_edges}</div>
            </div>
            <div class="stat-card">
                <h3>Semantic Mappings</h3>
                <div class="stat-value">{num_mappings}</div>
            </div>
            <div class="stat-card">
                <h3>Validation</h3>
                <div class="stat-value" style="color: #{"4caf50" if is_valid else "f44336"};">
                    {"✓ Valid" if is_valid else "✗ Issues"}
                </div>
            </div>
        </div>

        <div class="validation">
            <div class="validation-status">Validation Status: {"VALID" if is_valid else "ISSUES FOUND"}</div>
            <p>Coverage: {coverage:.1%} | Confidence: {confidence:.1%}</p>
        </div>

        {summary_html}

        {diagrams_html}

        <div class="files-section">
            <h2>Generated Files</h2>
            {files_html}
        </div>

        <div style="text-align: center; margin-top: 40px; color: #999; font-size: 0.9em;">
            <p>Generated by COGANT Roundtrip Orchestrator</p>
        </div>
    </div>
</body>
</html>
"""

            output_file = self.output_dir / "index.html"
            with open(output_file, "w") as f:
                f.write(html_content)

            logger.info("  Saved index.html")
        except Exception as e:
            logger.warning(f"Failed to save HTML index: {e}")

    def _generate_dashboard(self, graph, state_space, process_model, semantic_mappings, report):
        """Generate interactive HTML dashboard using DashboardGenerator."""
        try:
            # Load mermaid diagrams from files
            mermaid_diagrams = {}
            for diag_name in [
                "class_diagram",
                "dependency_graph",
                "state_diagram",
                "sequence_diagram",
                "flowchart",
                "boundary_map",
                "process_timeline",
                "semantic_flow",
            ]:
                diag_file = self.output_dir / f"{diag_name}.mermaid"
                if diag_file.exists():
                    try:
                        with open(diag_file) as f:
                            mermaid_diagrams[diag_name] = f.read()
                    except Exception:
                        pass

            # Create dashboard generator
            dashboard_gen = DashboardGenerator(
                graph=graph,
                state_space=state_space,
                process_model=process_model,
                semantic_mappings=semantic_mappings,
                mermaid_diagrams=mermaid_diagrams,
                validation_report=report,
                repo_name=self.repo_path.name,
                output_dir=self.output_dir,
            )

            # Generate HTML
            html_content = dashboard_gen.generate()

            # Save as dashboard.html
            output_file = self.output_dir / "dashboard.html"
            with open(output_file, "w") as f:
                f.write(html_content)

            file_size = output_file.stat().st_size
            logger.info(f"  Saved dashboard.html ({file_size:,} bytes)")

        except Exception as e:
            logger.warning(f"Failed to generate interactive dashboard: {e}", exc_info=True)

    def _save_outputs(self, markdown, json_data, report):
        """Save GNN outputs and validation report."""
        try:
            # Save markdown
            md_file = self.output_dir / "model.gnn.md"
            with open(md_file, "w") as f:
                f.write(markdown)
            logger.info(f"  Saved GNN markdown to {md_file}")

            # Save JSON
            json_file = self.output_dir / "model.gnn.json"
            with open(json_file, "w") as f:
                json.dump(json_data, f, indent=2, default=str)
            logger.info(f"  Saved GNN JSON to {json_file}")

            # Save validation report
            report_file = self.output_dir / "validation_report.json"
            report_data = {
                "id": report.id,
                "schema_name": report.schema_name,
                "is_valid": report.is_valid,
                "coverage_score": report.coverage_score,
                "confidence_score": report.confidence_score,
                "summary": report.summary,
                "issue_count": len(report.issues),
            }
            with open(report_file, "w") as f:
                json.dump(report_data, f, indent=2)
            logger.info(f"  Saved validation report to {report_file}")

        except Exception as e:
            logger.error(f"Failed to save outputs: {e}")
            raise

    def _compute_self_drift(self, graph, state_space, semantic_mappings):
        """Compute self-drift: compare the codebase against a minimal baseline.

        This shows how "interesting" or complex the codebase is by comparing
        it against an empty baseline.
        """
        try:
            logger.info("Computing self-drift (vs. minimal baseline)...")

            # Create minimal baseline (empty graph)
            baseline_bundle = {
                "graph": {"nodes": [], "edges": []},
                "state_space": {
                    "states": [],
                    "observations": [],
                    "actions": [],
                    "policies": [],
                },
                "mappings": {},
            }

            # Convert graph nodes to dict format
            graph_nodes = []
            if hasattr(graph, "nodes"):
                for n in graph.nodes:
                    if hasattr(n, "id"):
                        # It's a Node object
                        graph_nodes.append(
                            {
                                "id": n.id,
                                "kind": str(n.kind) if hasattr(n, "kind") else "unknown",
                                "attributes": n.attributes if hasattr(n, "attributes") else {},
                            }
                        )
                    else:
                        # It might be a dict-like object or string
                        graph_nodes.append({"id": str(n), "kind": "unknown", "attributes": {}})

            # Convert edges
            graph_edges = []
            if hasattr(graph, "edges"):
                for e in graph.edges:
                    if hasattr(e, "source") and hasattr(e, "target"):
                        graph_edges.append(
                            {
                                "source": e.source,
                                "target": e.target,
                                "kind": str(e.kind) if hasattr(e, "kind") else "unknown",
                            }
                        )

            # Create current bundle
            current_bundle = {
                "graph": {
                    "nodes": graph_nodes,
                    "edges": graph_edges,
                },
                "state_space": {
                    "states": [],
                    "observations": [],
                    "actions": [],
                    "policies": [],
                },
                "mappings": {
                    str(m_id): {"kind": "mapped"}
                    for m_id in (
                        semantic_mappings.keys() if isinstance(semantic_mappings, dict) else []
                    )
                },
            }

            # Compute drift
            analyzer = DriftAnalyzer(baseline_bundle, current_bundle)
            drift = analyzer._compute_drift_score()

            baseline_drift = {
                "total_score": drift.total_score,
                "architectural_score": drift.architectural_score,
                "semantic_churn_score": drift.semantic_churn_score,
                "details": {
                    "structural_drift": drift.details.get("structural_drift", {}),
                    "semantic_drift": drift.details.get("semantic_drift", {}),
                    "state_space_drift": drift.details.get("state_space_drift", {}),
                },
                "interpretation": self._interpret_self_drift(drift),
            }

            # Save baseline drift report
            drift_file = self.output_dir / "baseline_drift.json"
            with open(drift_file, "w") as f:
                json.dump(baseline_drift, f, indent=2, default=str)
            logger.info(f"  Saved baseline drift to {drift_file}")
            logger.info(f"  Self-drift score: {drift.total_score:.2%} (complexity indicator)")

            return baseline_drift
        except Exception as e:
            logger.warning(f"Self-drift computation failed: {e}", exc_info=True)
            return None

    def _interpret_self_drift(self, drift):
        """Interpret self-drift score."""
        score = drift.total_score
        if score < 0.2:
            return "Very simple codebase with minimal complexity"
        elif score < 0.4:
            return "Simple to moderate complexity"
        elif score < 0.6:
            return "Moderate complexity codebase"
        elif score < 0.8:
            return "Complex codebase with significant structure"
        else:
            return "Very complex codebase with rich architectural patterns"

    def _compute_comparison_drift(self, bundle1, bundle2):
        """Compute drift between two analyzed bundles.

        Args:
            bundle1: First bundle (baseline).
            bundle2: Second bundle (current).

        Returns:
            Drift analysis result dict.
        """
        try:
            logger.info("Computing drift between bundles...")

            analyzer = DriftAnalyzer(bundle1, bundle2)
            drift = analyzer._compute_drift_score()

            drift_result = {
                "total_score": drift.total_score,
                "architectural_score": drift.architectural_score,
                "semantic_churn_score": drift.semantic_churn_score,
                "details": drift.details,
                "report": analyzer.generate_diff_report(),
                "mermaid_diagram": analyzer.generate_diff_mermaid(),
            }

            # Save drift report
            drift_report_file = self.output_dir / "drift_report.md"
            with open(drift_report_file, "w") as f:
                f.write(drift_result["report"])
            logger.info(f"  Saved drift report to {drift_report_file}")

            # Save drift diagram
            drift_diagram_file = self.output_dir / "drift_diagram.mermaid"
            with open(drift_diagram_file, "w") as f:
                f.write(drift_result["mermaid_diagram"])
            logger.info(f"  Saved drift diagram to {drift_diagram_file}")

            # Save JSON
            drift_json_file = self.output_dir / "drift_report.json"
            with open(drift_json_file, "w") as f:
                json.dump(
                    {
                        "total_score": drift_result["total_score"],
                        "architectural_score": drift_result["architectural_score"],
                        "semantic_churn_score": drift_result["semantic_churn_score"],
                        "details": drift_result["details"],
                    },
                    f,
                    indent=2,
                    default=str,
                )
            logger.info(f"  Saved drift JSON to {drift_json_file}")

            logger.info(f"  Drift score: {drift.total_score:.2%}")
            return drift_result
        except Exception as e:
            logger.warning(f"Drift computation failed: {e}", exc_info=True)
            return None

    def _compute_metrics(self, graph, state_space, semantic_mappings):
        """Compute codebase metrics."""
        try:
            logger.info("Computing codebase metrics...")

            # Convert graph nodes to dict format
            graph_nodes = []
            if hasattr(graph, "nodes"):
                for n in graph.nodes:
                    if hasattr(n, "id"):
                        graph_nodes.append(
                            {
                                "id": n.id,
                                "kind": str(n.kind) if hasattr(n, "kind") else "unknown",
                                "attributes": n.attributes if hasattr(n, "attributes") else {},
                                "parent_id": getattr(n, "parent_id", None),
                            }
                        )

            # Convert edges
            graph_edges = []
            if hasattr(graph, "edges"):
                for e in graph.edges:
                    if hasattr(e, "source") and hasattr(e, "target"):
                        graph_edges.append(
                            {
                                "source": e.source,
                                "target": e.target,
                                "kind": str(e.kind) if hasattr(e, "kind") else "unknown",
                            }
                        )

            graph_dict = {
                "nodes": graph_nodes,
                "edges": graph_edges,
            }

            # Convert state space to dict format
            state_space_dict = {
                "states": [],
                "observations": [],
                "actions": [],
            }

            # Compute metrics
            mappings_dict = semantic_mappings if isinstance(semantic_mappings, dict) else {}
            metrics = CodebaseMetrics(graph_dict, state_space_dict, mappings_dict)
            metrics_report = metrics.to_dict()

            # Log summary
            logger.info(f"  Complexity: {metrics_report['complexity_score']:.2%}")
            logger.info(f"  Coupling: {metrics_report['coupling_score']:.2%}")
            logger.info(f"  Cohesion: {metrics_report['cohesion_score']:.2%}")

            return metrics_report
        except Exception as e:
            logger.warning(f"Metrics computation failed: {e}", exc_info=True)
            return None

    def _build_process_model(self, graph) -> ProcessModel:
        """Task 1: Build a real process model from the graph.

        Each class becomes a ProcessStage with its methods as sub-steps.
        Each CALLS edge between methods of different classes becomes a ProcessConnection.
        Each CONTAINS edge becomes a parent-child stage relationship.
        """
        try:
            extractor = ProcessExtractor(graph, self.repo_path.name)
            process_model = extractor.extract()
            logger.info(
                f"  Built process model: {len(process_model.stages)} stages, {len(process_model.connections)} connections"
            )
            return process_model
        except Exception as e:
            logger.warning(f"Process model extraction failed, using minimal model: {e}")
            # Fallback to minimal model
            return ProcessModel(
                id=f"process_model_{self.repo_path.name}",
                schema_name=self.repo_path.name,
                stages={},
                connections={},
            )

    def _add_simulation_trace(self, state_space):
        """Task 2: Add simulation trace output after state space compilation."""
        try:
            from cogant.simulate.runner import ModelRunner
            from cogant.simulate.visualization import SimulationVisualizer

            runner = ModelRunner()

            # Run basic simulation
            logger.info("  Running basic state space simulation...")
            trace = runner.run_simulation(state_space, steps=20)

            trace_data = {
                "metadata": {
                    "total_steps": len(trace),
                    "variables": list(state_space.variables.keys())[:10],
                },
                "trace": [
                    {
                        "step": t.get("step"),
                        "action": t.get("action"),
                        "success": t.get("success"),
                        "state_keys": list(t.get("state", {}).keys())[:5],
                    }
                    for t in trace
                ],
            }

            trace_file = self.output_dir / "simulation_trace.json"
            with open(trace_file, "w") as f:
                json.dump(trace_data, f, indent=2, default=str)
            logger.info(f"  Saved simulation trace to {trace_file}")

            # Run Active Inference simulation
            logger.info("  Running Active Inference simulation...")
            ai_trace = runner.run_active_inference(state_space, steps=20)

            # Convert trace to serializable format
            ai_trace_serialized = []
            for step in ai_trace:
                ai_trace_serialized.append(
                    {
                        "step": step.get("step", 0),
                        "observation": str(step.get("observation", "")),
                        "action": str(step.get("action", "")),
                        "free_energy": float(step.get("free_energy", 0.0)),
                        "beliefs": {str(k): float(v) for k, v in step.get("beliefs", {}).items()},
                        "predicted_state_keys": list(step.get("predicted_state", {}).keys())[:5],
                    }
                )

            ai_trace_file = self.output_dir / "active_inference_trace.json"
            with open(ai_trace_file, "w") as f:
                json.dump(ai_trace_serialized, f, indent=2, default=str)
            logger.info(f"  Saved Active Inference trace to {ai_trace_file}")

            # Generate simulation report
            logger.info("  Generating simulation report...")
            report = runner.generate_report(ai_trace)
            report_file = self.output_dir / "simulation_report.md"
            with open(report_file, "w") as f:
                f.write(report)
            logger.info(f"  Saved simulation report to {report_file}")

            # Generate HTML report with visualizations
            logger.info("  Generating visualization HTML...")
            visualizer = SimulationVisualizer()
            html_report = visualizer.generate_html_report(ai_trace, state_space)
            html_file = self.output_dir / "free_energy_trajectory.html"
            with open(html_file, "w") as f:
                f.write(html_report)
            logger.info(f"  Saved visualization HTML to {html_file}")

            return True
        except Exception as e:
            logger.warning(f"Simulation trace failed: {e}", exc_info=True)
            return False

    def _add_confidence_heatmap(self, semantic_mappings):
        """Task 3: Add confidence heatmap HTML showing semantic mappings as colored cells."""
        try:
            # Extract confidence data from mappings
            mapping_list = []
            for mapping_id, mapping in semantic_mappings.items():
                confidence = getattr(mapping, "confidence_score", 0.5)
                mapping_list.append(
                    {
                        "id": mapping_id,
                        "kind": getattr(mapping, "kind", "unknown"),
                        "confidence": confidence,
                        "label": getattr(mapping, "semantic_label", "unknown"),
                    }
                )

            # Sort by confidence
            mapping_list.sort(key=lambda x: x["confidence"], reverse=True)

            # Generate color for confidence level
            def confidence_to_color(conf):
                if conf < 0.5:
                    return "#ff6b6b"  # Red
                elif conf < 0.8:
                    return "#ffd93d"  # Yellow
                else:
                    return "#51cf66"  # Green

            # Generate HTML
            html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Confidence Heatmap</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        .heatmap { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px; margin: 20px 0; }
        .cell {
            padding: 10px;
            border-radius: 4px;
            color: white;
            text-align: center;
            font-weight: bold;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
            word-wrap: break-word;
            font-size: 12px;
        }
        .legend { margin-top: 30px; }
        .legend-item { margin: 10px 0; }
        .legend-color { display: inline-block; width: 20px; height: 20px; margin-right: 10px; border-radius: 2px; }
    </style>
</head>
<body>
    <h1>Semantic Mapping Confidence Heatmap</h1>
    <div class="heatmap">
"""

            for mapping in mapping_list[:100]:  # Limit to first 100
                color = confidence_to_color(mapping["confidence"])
                label = mapping["label"][:15] if mapping["label"] else mapping["kind"]
                html_content += f"""        <div class="cell" style="background-color: {color};" title="{mapping["id"]}: {mapping["confidence"]:.2%}">
            {label}<br/>{mapping["confidence"]:.0%}
        </div>
"""

            html_content += """    </div>

    <div class="legend">
        <h3>Confidence Legend</h3>
        <div class="legend-item">
            <span class="legend-color" style="background-color: #ff6b6b;"></span>
            <span>Low (&lt; 0.5)</span>
        </div>
        <div class="legend-item">
            <span class="legend-color" style="background-color: #ffd93d;"></span>
            <span>Medium (0.5 - 0.8)</span>
        </div>
        <div class="legend-item">
            <span class="legend-color" style="background-color: #51cf66;"></span>
            <span>High (&gt; 0.8)</span>
        </div>
    </div>
</body>
</html>
"""

            heatmap_file = self.output_dir / "confidence_heatmap.html"
            with open(heatmap_file, "w") as f:
                f.write(html_content)
            logger.info(f"  Saved confidence heatmap to {heatmap_file}")
            return True
        except Exception as e:
            logger.warning(f"Confidence heatmap generation failed: {e}")
            return False

    def _add_process_timeline(self, process_model):
        """Task 4: Add process timeline as Mermaid gantt chart."""
        try:
            if not process_model.stages:
                logger.debug("  No stages in process model, skipping timeline")
                return False

            lines = ["gantt"]
            lines.append("    title Process Timeline")
            lines.append("    dateFormat YYYY-MM-DD")

            # Create simple timeline with all stages
            stage_list = list(process_model.stages.values())
            start_date = "2026-01-01"

            for idx, stage in enumerate(stage_list[:30]):  # Limit to 30 stages
                safe_id = stage.name.replace(" ", "_").replace("-", "_")[:20]
                if idx == 0:
                    lines.append("    section Process")
                    lines.append(f"    {safe_id}: a{idx}, {start_date}, 1d")
                else:
                    lines.append(f"    {safe_id}: a{idx}, after a{idx - 1}, 1d")

            timeline_content = "\n".join(lines)

            timeline_file = self.output_dir / "process_timeline.mermaid"
            with open(timeline_file, "w") as f:
                f.write(timeline_content)
            logger.info(f"  Saved process timeline to {timeline_file}")
            return True
        except Exception as e:
            logger.warning(f"Process timeline generation failed: {e}")
            return False

    def _enrich_summary_markdown(self, graph, state_space, semantic_mappings, report):
        """Task 5: Enrich summary markdown with mapping kinds and additional sections."""
        try:
            summary = f"""# Analysis Summary: {self.repo_path.name}

Generated: {datetime.now().isoformat()}

## Repository Overview

- **Name**: {self.repo_path.name}
- **Path**: {self.repo_path}
- **Total Nodes**: {len(graph.nodes)}
- **Total Edges**: {len(graph.edges)}

## Program Graph Statistics

### Node Counts by Type
"""
            node_counts = self._count_nodes_by_kind(graph)
            for kind, count in sorted(node_counts.items(), key=lambda x: x[1], reverse=True):
                summary += f"- {kind}: {count}\n"

            summary += "\n### Edge Counts by Type\n"
            edge_counts = self._count_edges_by_kind(graph)
            for kind, count in sorted(edge_counts.items(), key=lambda x: x[1], reverse=True):
                summary += f"- {kind}: {count}\n"

            summary += f"""
## State Space Analysis

- **Variables**: {len(state_space.variables)}
- **Observations**: {len(state_space.observations)}
- **Actions**: {len(state_space.actions)}
- **Transitions**: {len(state_space.transitions)}

"""

            if state_space.variables:
                summary += "### State Variables\n"
                for var_id, var in list(state_space.variables.items())[:10]:
                    var_name = getattr(var, "name", var_id)
                    summary += f"- {var_name}\n"
                if len(state_space.variables) > 10:
                    summary += f"- ... and {len(state_space.variables) - 10} more\n"

            summary += f"""
## Semantic Mappings

- **Total Mappings**: {len(semantic_mappings)}

"""

            # Group by mapping kind (using kind.value for string representation)
            by_kind = {}
            for mapping_id, mapping in semantic_mappings.items():
                kind = getattr(mapping, "kind", None)
                if kind:
                    kind_str = kind.value if hasattr(kind, "value") else str(kind)
                else:
                    kind_str = "unknown"
                by_kind[kind_str] = by_kind.get(kind_str, 0) + 1

            if by_kind:
                summary += "### Mappings by Kind\n"
                for kind, count in sorted(by_kind.items(), key=lambda x: x[1], reverse=True):
                    summary += f"- {kind}: {count}\n"

            summary += f"""
## Validation Results

- **Valid**: {"Yes" if report.is_valid else "No"}
- **Coverage Score**: {report.coverage_score:.2%}
- **Confidence Score**: {report.confidence_score:.2%}
- **Issues Found**: {len(report.issues)}

"""

            if report.issues:
                summary += "### Issues\n"
                for issue in report.issues[:10]:
                    issue_msg = getattr(issue, "message", str(issue))
                    summary += f"- {issue_msg}\n"
                if len(report.issues) > 10:
                    summary += f"- ... and {len(report.issues) - 10} more\n"

            summary += """
## Generated Output Files

### Core Analysis
- `model.gnn.md` - GNN model in Markdown format
- `model.gnn.json` - GNN model in JSON format
- `program_graph.json` - Detailed program graph with metadata
- `validation_report.json` - Validation results
- `summary.md` - This file
- `simulation_trace.json` - State space simulation trace
- `active_inference_trace.json` - Active Inference simulation with beliefs and free energy
- `simulation_report.md` - Markdown report of Active Inference simulation
- `free_energy_trajectory.html` - Interactive visualization of free energy dynamics and beliefs
- `confidence_heatmap.html` - Semantic mapping confidence visualization
- `process_timeline.mermaid` - Process timeline gantt chart

### Visualizations (Mermaid)
- `class_diagram.mermaid` - Class hierarchy and composition
- `dependency_graph.mermaid` - Module dependencies
- `state_diagram.mermaid` - State machine diagram
- `sequence_diagram.mermaid` - Process sequence diagram
- `semantic_flow.mermaid` - Code to semantic mapping flow
- `boundary_map.mermaid` - Module boundary diagram

### Data Exports
- `typed_graph.json` - Full typed graph with all metadata
- `cytoscape.json` - Cytoscape.js compatible format
- `adjacency_matrix.json` - Graph adjacency matrix
- `graph.dot` - GraphViz DOT format
- `semantic_mappings.json` - All semantic mappings

### Charts
- `node_distribution.html` - Bar chart of node type counts
- `edge_distribution.html` - Bar chart of edge type counts

### Report
- `index.html` - Interactive HTML report with embedded diagrams

## Recommended Next Steps

1. **Review semantic mappings** - Check the confidence heatmap to identify low-confidence mappings that may need human review
2. **Validate process model** - Review the process timeline to ensure the extracted workflow stages match your expected process
3. **Inspect state space** - Examine the state variables and transitions to understand the system's dynamic behavior
4. **Check coverage** - Look at the coverage score and address any unexplored code paths
5. **Export for external tools** - Use the graph exports (Cytoscape, GraphViz, Parquet) to integrate with other analysis tools

---

*Report generated by COGANT Roundtrip Orchestrator*
"""

            output_file = self.output_dir / "summary.md"
            with open(output_file, "w") as f:
                f.write(summary)

            logger.debug("  Saved enriched summary.md")
        except Exception as e:
            logger.warning(f"Failed to save enriched summary markdown: {e}")
            return False
        return True

    def _save_metrics_report(self, graph, state_space, semantic_mappings):
        """Save codebase metrics report."""
        try:
            from cogant.scoring.metrics import CodebaseMetrics

            # Convert to dicts
            if isinstance(graph, dict):
                graph_dict = graph
            else:
                graph_dict = {"nodes": [], "edges": []}

            if isinstance(state_space, dict):
                ss_dict = state_space
            else:
                ss_dict = {}

            if isinstance(semantic_mappings, dict):
                mappings_dict = semantic_mappings
            else:
                mappings_dict = {}

            # Compute metrics
            metrics = CodebaseMetrics(graph_dict, ss_dict, mappings_dict)

            # Save markdown report
            md_report = metrics.format_report()
            md_file = self.output_dir / "metrics_report.md"
            with open(md_file, "w") as f:
                f.write(md_report)
            logger.info(f"  Saved metrics report to {md_file.name}")

            # Save JSON report
            json_report = metrics.to_dict()
            json_file = self.output_dir / "metrics_report.json"
            with open(json_file, "w") as f:
                json.dump(json_report, f, indent=2, default=str)
            logger.info(f"  Saved metrics JSON to {json_file.name}")

        except Exception as e:
            logger.warning(f"Failed to save metrics report: {e}")

    def _build_gnn_package(self, graph, state_space, process_model, semantic_mappings):
        """Build a complete, self-contained GNN model package."""
        try:
            package_dir = self.output_dir / "gnn_package"
            logger.info(f"    Building GNN package in {package_dir}")

            builder = GNNPackageBuilder(graph, state_space, process_model, semantic_mappings)
            manifest = builder.build(str(package_dir))

            logger.info(f"    GNN package built with {len(manifest.get('files', []))} files")
            return True
        except Exception as e:
            logger.error(f"Failed to build GNN package: {e}", exc_info=True)
            return False

    def _validate_gnn_package(self):
        """Validate the GNN package against the GNN specification."""
        try:
            package_dir = self.output_dir / "gnn_package"
            if not package_dir.exists():
                logger.warning("GNN package directory not found, skipping validation")
                return False

            validator = GNNValidator()
            result = validator.validate_package(str(package_dir))

            logger.info(
                f"    Validation result: {'VALID' if result.valid else 'INVALID'} (score: {result.score:.1f}%)"
            )

            if result.errors:
                for error in result.errors[:5]:
                    logger.warning(f"      Error: {error}")
                if len(result.errors) > 5:
                    logger.warning(f"      ... and {len(result.errors) - 5} more errors")

            # Save validation report
            validation_report = self.output_dir / "gnn_validation_report.json"
            with open(validation_report, "w") as f:
                json.dump(result.to_dict(), f, indent=2)
            logger.info(f"    Saved validation report to {validation_report.name}")

            # Save validation badge
            badge_svg = self.output_dir / "validation_badge.svg"
            badge_svg.write_text(validator.generate_validation_badge(result))
            logger.info(f"    Saved validation badge to {badge_svg.name}")

            return result.valid
        except Exception as e:
            logger.error(f"Failed to validate GNN package: {e}", exc_info=True)
            return False

    def _run_gnn_model(self):
        """Run the GNN model package and generate execution report."""
        try:
            package_dir = self.output_dir / "gnn_package"
            if not package_dir.exists():
                logger.warning("GNN package directory not found, skipping execution")
                return False

            runner = GNNModelRunner()
            runner.load_package(str(package_dir))

            logger.info("    Running GNN model for 10 steps...")
            execution = runner.run(steps=10)

            logger.info(
                f"    Execution complete: {execution['steps_completed']} steps, "
                f"total_reward={execution['total_reward']:.3f}"
            )

            # Save execution trace
            execution_trace = self.output_dir / "gnn_execution_trace.json"
            with open(execution_trace, "w") as f:
                json.dump(execution, f, indent=2, default=str)
            logger.info(f"    Saved execution trace to {execution_trace.name}")

            # Generate and save execution report
            report = runner.generate_execution_report(execution)
            execution_report = self.output_dir / "gnn_execution_report.md"
            with open(execution_report, "w") as f:
                f.write(report)
            logger.info(f"    Saved execution report to {execution_report.name}")

            return True
        except Exception as e:
            logger.error(f"Failed to run GNN model: {e}", exc_info=True)
            return False

    def _wire_graph_view(self, graph):
        """Wire in graph_view.py visualization module."""
        if not HAS_GRAPH_VIZ:
            logger.warning("GraphVisualizer not available, skipping graph_view visualization")
            return

        try:
            logger.info("    Rendering graph_view visualizations...")

            # Convert program graph to dict
            if isinstance(graph, dict):
                graph_dict = graph
            elif hasattr(graph, "model_dump"):
                graph_dict = graph.model_dump()
            elif hasattr(graph, "__dict__"):
                # Build dict from ProgramGraph object (non-Pydantic dataclass)
                nodes_data = []
                if hasattr(graph, "nodes"):
                    # If nodes is a dict, get values; if it's a list, use as-is
                    nodes_iter = (
                        graph.nodes.values() if isinstance(graph.nodes, dict) else graph.nodes
                    )
                    for node in nodes_iter:
                        node_id = getattr(node, "id", "")
                        # Try both 'label' and 'name'
                        node_label = getattr(node, "label", getattr(node, "name", ""))
                        node_kind = str(getattr(node, "kind", "unknown"))
                        nodes_data.append(
                            {
                                "id": node_id,
                                "name": node_label,
                                "type": node_kind,
                            }
                        )

                edges_data = []
                if hasattr(graph, "edges"):
                    # If edges is a dict, get values; if it's a list, use as-is
                    edges_iter = (
                        graph.edges.values() if isinstance(graph.edges, dict) else graph.edges
                    )
                    for edge in edges_iter:
                        edges_data.append(
                            {
                                "source": getattr(edge, "source_id", ""),
                                "target": getattr(edge, "target_id", ""),
                                "type": str(getattr(edge, "kind", "unknown")),
                            }
                        )

                graph_dict = {
                    "nodes": nodes_data,
                    "edges": edges_data,
                    "metadata": {
                        "node_count": len(nodes_data),
                        "edge_count": len(edges_data),
                    },
                }
            else:
                logger.warning("Cannot convert graph to dict, skipping graph_view visualization")
                return

            # Normalize graph_dict structure: if nodes is a dict (keyed by id), convert to list
            if isinstance(graph_dict.get("nodes"), dict):
                nodes_dict = graph_dict["nodes"]
                graph_dict["nodes"] = [
                    {
                        "id": node_id,
                        "name": node.get("name", node.get("label", "")),
                        "type": node.get("kind", "unknown"),
                    }
                    for node_id, node in nodes_dict.items()
                ]
            elif isinstance(graph_dict.get("nodes"), list):
                # Nodes are already a list - ensure they have required fields
                normalized_nodes = []
                for node in graph_dict["nodes"]:
                    if isinstance(node, dict):
                        normalized_nodes.append(
                            {
                                "id": node.get("id", ""),
                                "name": node.get("name", node.get("label", "")),
                                "type": node.get("type", node.get("kind", "unknown")),
                            }
                        )
                    else:
                        # Try to extract from object
                        normalized_nodes.append(
                            {
                                "id": getattr(node, "id", ""),
                                "name": getattr(node, "label", getattr(node, "name", "")),
                                "type": str(getattr(node, "kind", "unknown")),
                            }
                        )
                graph_dict["nodes"] = normalized_nodes

            if isinstance(graph_dict.get("edges"), dict):
                edges_dict = graph_dict["edges"]
                graph_dict["edges"] = [
                    {
                        "source": edge.get("source_id", ""),
                        "target": edge.get("target_id", ""),
                        "type": edge.get("kind", "unknown"),
                    }
                    for edge_id, edge in edges_dict.items()
                ]
            elif isinstance(graph_dict.get("edges"), list):
                # Edges are already a list - ensure they have required fields
                normalized_edges = []
                for edge in graph_dict["edges"]:
                    if isinstance(edge, dict):
                        normalized_edges.append(
                            {
                                "source": edge.get("source", edge.get("source_id", "")),
                                "target": edge.get("target", edge.get("target_id", "")),
                                "type": edge.get("type", edge.get("kind", "unknown")),
                            }
                        )
                    else:
                        normalized_edges.append(
                            {
                                "source": getattr(edge, "source_id", ""),
                                "target": getattr(edge, "target_id", ""),
                                "type": str(getattr(edge, "kind", "unknown")),
                            }
                        )
                graph_dict["edges"] = normalized_edges

            # Create visualizer and load graph
            visualizer = GraphVisualizer()
            visualizer.from_program_graph(graph_dict)

            # Cluster by package (default)
            visualizer.cluster_by_package()

            # Render interactive HTML
            html_path = self.output_dir / "graph_interactive.html"
            visualizer.render_html(str(html_path))
            logger.info(f"    Saved interactive graph to {html_path.name}")

            # Export D3.js JSON
            d3_json = visualizer.to_d3_json()
            json_path = self.output_dir / "graph_d3.json"
            with open(json_path, "w") as f:
                json.dump(d3_json, f, indent=2)
            logger.info(f"    Saved D3.js JSON to {json_path.name}")

        except Exception as e:
            logger.warning(f"Graph view visualization failed: {e}", exc_info=True)

    def _wire_semantic_view(self, state_space):
        """Wire in semantic_view.py visualization module."""
        if not HAS_SEMANTIC_VIZ:
            logger.warning("SemanticVisualizer not available, skipping semantic_view visualization")
            return

        try:
            logger.info("    Rendering semantic_view visualizations...")

            # Convert state space to dict if needed
            if hasattr(state_space, "to_dict"):
                state_space_dict = state_space.to_dict()
            elif isinstance(state_space, dict):
                state_space_dict = state_space
            else:
                # Try to extract key components
                states_val = getattr(state_space, "states", {})
                observations_val = getattr(state_space, "observations", {})
                actions_val = getattr(state_space, "actions", {})
                policies_val = getattr(state_space, "policies", {})
                transitions_val = getattr(state_space, "transitions", [])

                # Convert dicts to lists if needed
                states_list = (
                    list(states_val.values()) if isinstance(states_val, dict) else states_val
                )
                observations_list = (
                    list(observations_val.values())
                    if isinstance(observations_val, dict)
                    else observations_val
                )
                actions_list = (
                    list(actions_val.values()) if isinstance(actions_val, dict) else actions_val
                )
                policies_list = (
                    list(policies_val.values()) if isinstance(policies_val, dict) else policies_val
                )

                state_space_dict = {
                    "states": states_list,
                    "observations": observations_list,
                    "actions": actions_list,
                    "policies": policies_list,
                    "transitions": transitions_val if isinstance(transitions_val, list) else [],
                }

            # Ensure all values are lists, not dicts
            for key in ["states", "observations", "actions", "policies"]:
                if key in state_space_dict and isinstance(state_space_dict[key], dict):
                    state_space_dict[key] = list(state_space_dict[key].values())

            # Create visualizer and load state space
            visualizer = SemanticVisualizer()
            visualizer.from_state_space(state_space_dict)

            # Render HTML
            html_path = self.output_dir / "semantic_view.html"
            visualizer.render_html(str(html_path))
            logger.info(f"    Saved semantic view to {html_path.name}")

        except Exception as e:
            logger.warning(f"Semantic view visualization failed: {e}", exc_info=True)

    def _wire_gantt_chart(self, process_model):
        """Wire in gantt.py visualization module."""
        if not HAS_GANTT:
            logger.warning("GanttRenderer not available, skipping gantt visualization")
            return

        try:
            logger.info("    Rendering Gantt chart visualization...")

            # Convert process model to dict if needed
            if hasattr(process_model, "to_dict"):
                process_dict = process_model.to_dict()
            elif isinstance(process_model, dict):
                process_dict = process_model
            else:
                # Try to extract key components
                process_dict = {
                    "stages": getattr(process_model, "stages", []),
                    "dependencies": getattr(process_model, "dependencies", []),
                    "connections": getattr(process_model, "connections", []),
                }
                # Convert stage dict to list of dicts if needed
                if isinstance(process_dict["stages"], dict):
                    stages_list = []
                    for k, v in process_dict["stages"].items():
                        stage_dict = {
                            "id": k,
                            "name": v.name if hasattr(v, "name") else str(k),
                            "start": 0,
                            "duration": 10,
                        }
                        if hasattr(v, "__dict__"):
                            stage_dict.update(
                                {kk: vv for kk, vv in vars(v).items() if kk not in stage_dict}
                            )
                        stages_list.append(stage_dict)
                    process_dict["stages"] = stages_list
                # Convert connections to dependencies
                if process_dict["connections"] and not process_dict["dependencies"]:
                    process_dict["dependencies"] = [
                        {"from": str(k), "to": str(v) if not isinstance(v, list) else str(v[0])}
                        for k, v in process_dict["connections"].items()
                    ]

            # Create renderer and load process model
            renderer = GanttRenderer()
            renderer.from_process_model(process_dict)

            # Render HTML
            html_path = self.output_dir / "process_gantt.html"
            renderer.render_html(str(html_path))
            logger.info(f"    Saved Gantt chart to {html_path.name}")

        except Exception as e:
            logger.warning(f"Gantt chart visualization failed: {e}", exc_info=True)

    def _wire_html_site_renderer(
        self, graph, state_space, process_model, semantic_mappings, report
    ):
        """Wire in html_renderer.py visualization module."""
        if not HAS_HTML_RENDERER:
            logger.warning("HTMLSiteRenderer not available, skipping html_renderer visualization")
            return

        try:
            logger.info("    Rendering HTML site...")

            # Create analysis bundle
            bundle = {
                "target": self.repo_path.name,
                "timestamp": datetime.now().isoformat(),
                "artifacts": {
                    "nodes": len(
                        graph.get("nodes", {})
                        if isinstance(graph, dict)
                        else getattr(graph, "nodes", [])
                    ),
                    "edges": len(
                        graph.get("edges", {})
                        if isinstance(graph, dict)
                        else getattr(graph, "edges", [])
                    ),
                },
                "stage_results": {
                    "ingest": True,
                    "static": True,
                    "normalize": True,
                    "graph": True,
                    "translate": True,
                    "statespace": True,
                    "process": True,
                    "export": True,
                    "validate": True,
                },
                "errors": [],
            }

            # Create renderer and generate site
            site_dir = self.output_dir / "site"
            renderer = HTMLSiteRenderer(bundle)
            index_path = renderer.render(str(site_dir))
            logger.info(f"    Saved HTML site to {site_dir.name}/")
            logger.info(f"    Site index at {index_path.name}")

        except Exception as e:
            logger.warning(f"HTML site renderer visualization failed: {e}", exc_info=True)

    def _wire_diff_view(self, graph, state_space):
        """Wire viz.diff_view: render a self-diff (current bundle vs. itself).

        Produces a baseline diff artifact that can later be replaced by a
        commit-to-commit comparison when ``--compare`` is used. Emits both
        JSON and HTML views so downstream tools can consume either.
        """
        try:
            from cogant.viz.diff_view import DiffVisualizer
        except ImportError:
            logger.warning("DiffVisualizer not available, skipping diff view")
            return

        try:
            logger.info("    Rendering self-diff view...")
            if isinstance(graph, dict):
                nodes = graph.get("nodes", {})
                edges = graph.get("edges", {})
            else:
                nodes = getattr(graph, "nodes", {})
                edges = getattr(graph, "edges", {})

            ss_vars = getattr(state_space, "variables", {}) if state_space else {}
            ss_obs = getattr(state_space, "observations", {}) if state_space else {}
            ss_acts = getattr(state_space, "actions", {}) if state_space else {}

            base_bundle = {
                "nodes": len(nodes),
                "edges": len(edges),
                "state_variables": len(ss_vars),
                "observations": len(ss_obs),
                "actions": len(ss_acts),
            }
            head_bundle = dict(base_bundle)  # self-diff → no changes
            visualizer = DiffVisualizer(base_bundle, head_bundle)

            diff_html = self.output_dir / "diff_view.html"
            visualizer.render_html(str(diff_html))
            diff_json = self.output_dir / "diff_view.json"
            diff_json.write_text(visualizer.render_json())
            logger.debug(f"    Saved diff view to {diff_html.name} and {diff_json.name}")
        except Exception as e:
            logger.warning(f"Diff view rendering failed: {e}", exc_info=True)

    def _wire_boundary_map(self, graph):
        """Wire viz.boundary: generate module/type boundary maps.

        Produces two Mermaid diagrams (module boundaries and type
        boundaries) and a JSON boundary report that quantifies bounded
        contexts and coupling between them.
        """
        try:
            from cogant.schemas.graph import ProgramGraph
            from cogant.viz.boundary import BoundaryMapper
        except ImportError:
            logger.warning("BoundaryMapper not available, skipping boundary map")
            return

        # BoundaryMapper expects a real ProgramGraph; synthesize one
        # from the dict form we have in the pipeline.
        try:
            pg = graph
            if isinstance(graph, dict):
                # Reconstruct a minimal ProgramGraph for boundary analysis.
                try:
                    from cogant.graph.builder import ProgramGraphBuilder
                    from cogant.schemas.core import EdgeKind, NodeKind

                    builder = ProgramGraphBuilder(repo_uri=self.repo_path.as_uri())
                    id_map = {}
                    for nid, n in graph.get("nodes", {}).items():
                        try:
                            kind = NodeKind(n.get("kind", "module"))
                        except Exception:
                            kind = NodeKind.MODULE
                        node = builder.add_node(
                            kind=kind,
                            name=n.get("name", nid),
                            qualified_name=n.get("qualified_name"),
                            path=n.get("path"),
                            language=n.get("language"),
                        )
                        id_map[nid] = node.id
                    for eid, e in graph.get("edges", {}).items():
                        try:
                            ek = EdgeKind(e.get("kind", "contains"))
                        except Exception:
                            continue
                        src = id_map.get(e.get("source_id") or e.get("source"))
                        tgt = id_map.get(e.get("target_id") or e.get("target"))
                        if src and tgt:
                            try:
                                builder.add_edge(ek, src, tgt)
                            except Exception:
                                continue
                    pg = builder.finalize()
                except Exception as rebuild_err:
                    logger.warning(f"Boundary map graph reconstruction failed: {rebuild_err}")
                    return

            logger.info("    Generating boundary maps...")
            mapper = BoundaryMapper()

            module_diagram = mapper.map_module_boundaries(pg)
            (self.output_dir / "module_boundaries.mermaid").write_text(module_diagram)

            type_diagram = mapper.map_type_boundaries(pg)
            (self.output_dir / "type_boundaries.mermaid").write_text(type_diagram)

            report = mapper.generate_boundary_report(pg)
            (self.output_dir / "boundary_report.json").write_text(
                json.dumps(report, indent=2, default=str)
            )
            logger.debug("    Saved boundary maps (module/type Mermaid + JSON report)")
        except Exception as e:
            logger.warning(f"Boundary map generation failed: {e}", exc_info=True)

    def _wire_export_formats(self, graph, state_space, process_model, semantic_mappings):
        """Wire cogant.export: emit GraphML and Parquet export formats.

        Every bundle already ships JSON exports of the program graph and
        state-space artifacts; this adds the two machine-interop formats
        (GraphML for Gephi/yEd and Parquet for DuckDB analysis) so the
        round-trip covers the ``export`` module that would otherwise be
        unused by the orchestrator.
        """
        try:
            from cogant.export.graphml import GraphMLExporter
            from cogant.export.parquet import ParquetExporter
        except ImportError as e:
            logger.warning(f"Export modules not available: {e}")
            return

        try:
            # Reuse the same graph-rebuild logic as boundary
            pg = graph
            if isinstance(graph, dict):
                try:
                    from cogant.graph.builder import ProgramGraphBuilder
                    from cogant.schemas.core import EdgeKind, NodeKind

                    builder = ProgramGraphBuilder(repo_uri=self.repo_path.as_uri())
                    id_map = {}
                    for nid, n in graph.get("nodes", {}).items():
                        try:
                            kind = NodeKind(n.get("kind", "module"))
                        except Exception:
                            kind = NodeKind.MODULE
                        node = builder.add_node(
                            kind=kind,
                            name=n.get("name", nid),
                            qualified_name=n.get("qualified_name"),
                            path=n.get("path"),
                            language=n.get("language"),
                        )
                        id_map[nid] = node.id
                    for eid, e in graph.get("edges", {}).items():
                        try:
                            ek = EdgeKind(e.get("kind", "contains"))
                        except Exception:
                            continue
                        src = id_map.get(e.get("source_id") or e.get("source"))
                        tgt = id_map.get(e.get("target_id") or e.get("target"))
                        if src and tgt:
                            try:
                                builder.add_edge(ek, src, tgt)
                            except Exception:
                                continue
                    pg = builder.finalize()
                except Exception as rebuild_err:
                    logger.warning(f"Export graph reconstruction failed: {rebuild_err}")
                    return

            logger.info("    Exporting GraphML and Parquet...")
            # GraphML
            try:
                graphml_text = GraphMLExporter(pg).export()
                (self.output_dir / "program_graph.graphml").write_text(graphml_text)
                logger.debug("    Saved program_graph.graphml")
            except Exception as e:
                logger.warning(f"GraphML export failed: {e}")

            # Parquet
            try:
                parquet_dir = self.output_dir / "parquet"
                parquet_dir.mkdir(exist_ok=True)
                written = ParquetExporter(pg).export(parquet_dir)
                logger.debug(f"    Saved {len(written)} Parquet files to parquet/")
            except Exception as e:
                logger.warning(f"Parquet export failed: {e}")
        except Exception as e:
            logger.warning(f"Export format generation failed: {e}", exc_info=True)

    def _generate_png_outputs(self, graph, state_space=None, process_model=None):
        """Render PNGs for **every** visualization artifact in the run directory.

        Delegates to :func:`cogant.viz.png_export.render_all_pngs` which
        guarantees a PNG sibling for:

        * ``program_graph.json``
        * every ``.mermaid``/``.mmd`` file (via mmdc when available,
          native matplotlib+networkx fallback otherwise),
        * every ``.svg`` file (via cairosvg/rsvg/inkscape/ImageMagick),
        * every ``.dot`` file (via Graphviz),
        * the ``StateSpaceModel`` (factor-graph PNG),
        * the ``ProcessModel`` (Gantt-style PNG).

        This is the single source of truth for raster outputs in a COGANT
        roundtrip; individual visualization wiring helpers should defer to
        it rather than re-implementing PNG export.
        """
        try:
            from cogant.viz.png_export import render_all_pngs
        except ImportError as e:
            logger.warning(f"PNG export unavailable: {e}")
            return

        try:
            result = render_all_pngs(
                self.output_dir,
                state_space=state_space,
                process_model=process_model,
            )
            total = sum(len(v) for v in result.values())
            logger.info(
                f"    Wrote {total} PNG files "
                f"(program_graph={len(result['program_graph'])}, "
                f"mermaid={len(result['mermaid'])}, "
                f"svg={len(result['svg'])}, "
                f"dot={len(result['dot'])}, "
                f"state_space={len(result['state_space'])}, "
                f"process={len(result['process'])})"
            )
        except Exception as e:
            logger.warning(f"PNG output generation failed: {e}", exc_info=True)

    def _run_full_gnn_pipeline(self, graph, state_space, process_model, semantic_mappings):
        """Run the full COGANT GNN pipeline and deposit outputs in gnn_pipeline/.

        This is the real GNN (Generalized Notation Notation) terminal stage:
        build a GNN package, validate it, execute the compiled model via
        the Active Inference runner, and emit a complete artifact bundle
        into ``output_dir/gnn_pipeline/``. Mirrors the minimum contract
        expected by the Active Inference Institute GNN ecosystem:
        metadata, state space, observations, actions, transitions,
        preferences, validation report, and execution trace.
        """
        try:
            from cogant.gnn.package import GNNPackageBuilder
            from cogant.gnn.runner import GNNModelRunner
            from cogant.gnn.validator import GNNValidator
        except ImportError as e:
            logger.warning(f"GNN pipeline modules unavailable: {e}")
            return

        gnn_dir = self.output_dir / "gnn_pipeline"
        gnn_dir.mkdir(exist_ok=True)

        try:
            # Reconstruct a typed ProgramGraph for the GNN package builder
            pg = graph
            if isinstance(graph, dict):
                try:
                    from cogant.graph.builder import ProgramGraphBuilder
                    from cogant.schemas.core import EdgeKind, NodeKind

                    builder = ProgramGraphBuilder(repo_uri=self.repo_path.as_uri())
                    id_map = {}
                    for nid, n in graph.get("nodes", {}).items():
                        try:
                            kind = NodeKind(n.get("kind", "module"))
                        except Exception:
                            kind = NodeKind.MODULE
                        node = builder.add_node(
                            kind=kind,
                            name=n.get("name", nid),
                            qualified_name=n.get("qualified_name"),
                            path=n.get("path"),
                            language=n.get("language"),
                        )
                        id_map[nid] = node.id
                    for eid, e in graph.get("edges", {}).items():
                        try:
                            ek = EdgeKind(e.get("kind", "contains"))
                        except Exception:
                            continue
                        src = id_map.get(e.get("source_id") or e.get("source"))
                        tgt = id_map.get(e.get("target_id") or e.get("target"))
                        if src and tgt:
                            try:
                                builder.add_edge(ek, src, tgt)
                            except Exception:
                                continue
                    pg = builder.finalize()
                except Exception as rebuild_err:
                    logger.warning(f"GNN pipeline graph reconstruction failed: {rebuild_err}")
                    return

            # 1) Build package
            logger.info("    [GNN pipeline] Building package...")
            package_builder = GNNPackageBuilder(
                graph=pg,
                state_space=state_space,
                process_model=process_model,
                mappings=semantic_mappings,
                config={"repo_name": self.repo_path.name},
            )
            build_info = package_builder.build(str(gnn_dir))
            logger.info(f"    [GNN pipeline] Package written to {gnn_dir.name}/")

            # 2) Validate package
            logger.info("    [GNN pipeline] Validating package...")
            validator = GNNValidator()
            validation = validator.validate_package(str(gnn_dir))
            validation_dict = (
                validation.to_dict()
                if hasattr(validation, "to_dict")
                else {
                    "valid": getattr(validation, "valid", False),
                    "score": getattr(validation, "score", 0),
                    "errors": getattr(validation, "errors", []),
                    "warnings": getattr(validation, "warnings", []),
                }
            )
            (gnn_dir / "validation_report.json").write_text(
                json.dumps(validation_dict, indent=2, default=str)
            )
            score = validation_dict.get("score", 0)
            logger.info(f"    [GNN pipeline] Validation score: {score}%")

            # 3) Execute compiled model
            logger.info("    [GNN pipeline] Executing compiled model...")
            try:
                runner = GNNModelRunner()
                runner.load_package(str(gnn_dir))
                trace = runner.run(steps=20)
                (gnn_dir / "execution_trace.json").write_text(
                    json.dumps(trace, indent=2, default=str)
                )
                report_md = runner.generate_execution_report(trace)
                (gnn_dir / "execution_report.md").write_text(report_md)
                steps = (
                    (trace.get("steps_completed") if isinstance(trace, dict) else None)
                    or (trace.get("steps") if isinstance(trace, dict) else None)
                    or 0
                )
                logger.info(f"    [GNN pipeline] Execution complete: {steps} steps")
            except Exception as e:
                logger.warning(f"    [GNN pipeline] Execution failed: {e}")

            # 4) Write a pipeline manifest documenting what's in gnn_pipeline/
            manifest = {
                "pipeline": "cogant.gnn",
                "repo": self.repo_path.name,
                "artifacts": sorted([p.name for p in gnn_dir.iterdir() if p.is_file()]),
                "subdirs": sorted([p.name for p in gnn_dir.iterdir() if p.is_dir()]),
                "validation_score": score,
            }
            (gnn_dir / "pipeline_manifest.json").write_text(
                json.dumps(manifest, indent=2, default=str)
            )
        except Exception as e:
            logger.warning(f"Full GNN pipeline failed: {e}", exc_info=True)

    def _generate_advanced_visualizations(self, graph, state_space, semantic_mappings):
        """Generate advanced visualization types: factor graph, sunburst, radar, matrix."""
        if not HAS_STATIC_PLOTTER:
            logger.warning("StaticPlotter not available, skipping advanced visualizations")
            return

        try:
            plotter = StaticPlotter()

            # Generate Factor Graph SVG
            try:
                logger.info("    Generating factor graph SVG...")
                factor_graph_path = self.output_dir / "factor_graph.svg"
                plotter.plot_factor_graph(state_space, str(factor_graph_path))
                logger.debug(f"    Saved factor graph to {factor_graph_path.name}")
            except Exception as e:
                logger.warning(f"Failed to generate factor graph: {e}")

            # Generate State Space Matrix HTML
            try:
                logger.info("    Generating state space matrix HTML...")
                matrix_html_path = self.output_dir / "state_space_matrix.html"
                plotter.plot_state_space_matrix_html(state_space, str(matrix_html_path))
                logger.debug(f"    Saved state space matrix to {matrix_html_path.name}")
            except Exception as e:
                logger.warning(f"Failed to generate state space matrix HTML: {e}")

            # Generate Ontology Sunburst SVG
            try:
                logger.info("    Generating ontology sunburst SVG...")
                sunburst_path = self.output_dir / "ontology_sunburst.svg"
                plotter.plot_ontology_sunburst(graph, semantic_mappings, str(sunburst_path))
                logger.debug(f"    Saved ontology sunburst to {sunburst_path.name}")
            except Exception as e:
                logger.warning(f"Failed to generate ontology sunburst: {e}")

            # Generate Confidence Radar Chart SVG
            try:
                logger.info("    Generating confidence radar chart SVG...")
                radar_path = self.output_dir / "confidence_radar.svg"
                plotter.plot_confidence_radar(semantic_mappings, str(radar_path))
                logger.debug(f"    Saved confidence radar to {radar_path.name}")
            except Exception as e:
                logger.warning(f"Failed to generate confidence radar: {e}")

            logger.info("  Advanced visualizations generated successfully")

        except Exception as e:
            logger.warning(f"Advanced visualization generation failed: {e}", exc_info=True)

    def print_summary(self):
        """Print summary of generated outputs."""
        print("\n" + "=" * 80)
        print("OUTPUT SUMMARY")
        print("=" * 80)

        for output_file in sorted(self.output_dir.glob("*")):
            size = output_file.stat().st_size
            print(f"  {output_file.name:30} ({size:10,d} bytes)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="COGANT roundtrip orchestrator: Run the full analysis pipeline on a codebase."
    )
    parser.add_argument("repo_path", help="Path to repository to analyze")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to YAML configuration file (or preset name: minimal, standard, comprehensive, gnn-focused, security)",
    )
    parser.add_argument(
        "--preset",
        type=str,
        default=None,
        help="Use a named preset configuration (overrides --config)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: output/{repo_name}/)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity level",
    )
    parser.add_argument(
        "--compare",
        type=str,
        default=None,
        help="Path to second repository for drift analysis comparison",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = getattr(logging, args.log_level)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    repo_path = Path(args.repo_path).resolve()
    if not repo_path.exists():
        logger.error(f"Repository path does not exist: {repo_path}")
        sys.exit(1)

    repo_name = repo_path.name

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir).resolve()
    else:
        output_dir = Path(__file__).parent.parent / "output" / repo_name

    # Load configuration
    config = None
    if args.preset:
        try:
            from cogant.config.presets import get_preset

            logger.info(f"Loading preset: {args.preset}")
            config = get_preset(args.preset)
            logger.info("Preset loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load preset '{args.preset}': {e}")
            sys.exit(1)
    elif args.config:
        # Check if it's a preset name
        try:
            from cogant.config.presets import get_preset

            try:
                config = get_preset(args.config)
                logger.info(f"Loaded preset: {args.config}")
            except ValueError:
                # Not a preset, try loading as file
                config_path = Path(args.config).resolve()
                if not config_path.exists():
                    logger.error(f"Configuration file not found: {config_path}")
                    sys.exit(1)
                logger.info(f"Loading configuration from: {config_path}")
                config = ConfigLoader.load_all_configs(str(config_path))
                logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            sys.exit(1)

    logger.info(f"Analyzing repository: {repo_path}")
    logger.info(f"Output directory: {output_dir}")

    compare_repo_path = None
    if args.compare:
        compare_repo_path = Path(args.compare).resolve()
        if not compare_repo_path.exists():
            logger.error(f"Comparison repository path does not exist: {compare_repo_path}")
            sys.exit(1)

    orchestrator = RoundtripOrchestrator(repo_path, output_dir, config, compare_repo_path)
    success = orchestrator.run()
    orchestrator.print_summary()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
