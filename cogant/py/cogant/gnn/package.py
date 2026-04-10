"""
GNN package builder — creates a complete, self-contained GNN model package.

Builds a package with:
- manifest.json: metadata and checksums
- model.gnn.md: canonical GNN markdown
- model.gnn.json: machine-readable model
- state_space.json: detailed state space
- observations.json: observation modalities
- actions.json: actions and policies
- transitions.json: transition structure
- preferences.json: preferences and constraints
- factors.json: factorization structure
- provenance.json: full provenance chain
- ontology.json: ontology mappings
- diagrams/: mermaid diagrams
- visualizations/: HTML visualizations
"""

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cogant.gnn.formatter import GNNMarkdownFormatter
from cogant.gnn.json_export import GNNJSONExporter
from cogant.markov import (
    MarkovBlanketExtractor,
    build_blanket_network,
    serialize_blanket,
)
from cogant.process.extractor import ProcessModel
from cogant.schemas.core import NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import MappingKind
from cogant.statespace.compiler import StateSpaceModel

logger = logging.getLogger(__name__)


def _enum_value(value: Any) -> Any:
    """Return the underlying value of an enum if applicable."""
    return value.value if hasattr(value, "value") else value


class GNNPackageBuilder:
    """Builds a complete, self-contained GNN model package."""

    PACKAGE_VERSION = "1.0.0"
    REQUIRED_FILES = [
        "manifest.json",
        "model.gnn.md",
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
        "preferences_constraints.json",
        "markov_blanket.json",
        "markov_network.json",
    ]

    def __init__(
        self,
        graph: ProgramGraph,
        state_space: StateSpaceModel,
        process_model: ProcessModel,
        mappings: dict[str, Any],
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize the GNN package builder.

        Args:
            graph: Program graph.
            state_space: State space model.
            process_model: Process model.
            mappings: Semantic mappings.
            config: Optional configuration dictionary.
        """
        self.graph = graph
        self.state_space = state_space
        self.process_model = process_model
        self.mappings = mappings
        self.config = config or {}
        self.timestamp = datetime.now(UTC).isoformat()
        self.checksums: dict[str, str] = {}

    def build(self, output_dir: str) -> dict[str, Any]:
        """
        Build the complete GNN package.

        Args:
            output_dir: Directory to create the package in.

        Returns:
            Manifest dictionary with package metadata and checksums.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Building GNN package in {output_path}")

        try:
            # 1. Generate core model files
            self._generate_markdown(output_path)
            self._generate_json_model(output_path)
            self._generate_state_space(output_path)
            self._generate_observations(output_path)
            self._generate_actions(output_path)
            self._generate_transitions(output_path)
            self._generate_preferences(output_path)
            self._generate_factors(output_path)
            self._generate_provenance(output_path)
            self._generate_ontology(output_path)

            # 2. Generate canonical section JSON files
            self._generate_actions_policies(output_path)
            self._generate_connections(output_path)
            self._generate_preferences_constraints(output_path)

            # 2b. Generate Markov blanket artifacts (Active Inference partition)
            self._generate_markov_blanket(output_path)

            # 2c. Dump the typed program graph as JSON so PNG rasterizers can
            # rebuild a NetworkX view without re-running the pipeline.
            self._generate_program_graph_json(output_path)

            # 2d. Dump the ProcessModel as JSON so ``render_all_pngs`` can
            # rasterize a Gantt timeline without re-running ProcessExtractor.
            self._generate_process_model_json(output_path)

            # 3. Generate diagrams
            self._generate_diagrams(output_path)

            # 4. Generate visualizations
            self._generate_visualizations(output_path)

            # 5. Create manifest
            manifest = self._create_manifest(output_path)

            logger.info(f"GNN package built successfully with {len(self.checksums)} files")
            return manifest

        except Exception as e:
            logger.error(f"Failed to build GNN package: {e}", exc_info=True)
            raise

    def _generate_markdown(self, output_path: Path) -> None:
        """Generate canonical GNN markdown."""
        try:
            formatter = GNNMarkdownFormatter(
                self.graph, self.state_space, self.process_model, self.mappings
            )
            markdown = formatter.format()
            markdown_path = output_path / "model.gnn.md"
            markdown_path.write_text(markdown, encoding="utf-8")
            self.checksums["model.gnn.md"] = self._checksum(markdown)
            logger.info(f"Generated {markdown_path.name}")
        except Exception as e:
            logger.error(f"Failed to generate markdown: {e}", exc_info=True)
            raise

    def _generate_json_model(self, output_path: Path) -> None:
        """Generate machine-readable GNN JSON model."""
        try:
            exporter = GNNJSONExporter(
                self.graph, self.state_space, self.process_model, self.mappings
            )
            json_data = exporter.export()
            json_path = output_path / "model.gnn.json"
            json_path.write_text(
                json.dumps(json_data, indent=2, default=str), encoding="utf-8"
            )
            self.checksums["model.gnn.json"] = self._checksum_dict(json_data)
            logger.info(f"Generated {json_path.name}")
        except Exception as e:
            logger.error(f"Failed to generate JSON model: {e}", exc_info=True)
            raise

    def _generate_state_space(self, output_path: Path) -> None:
        """Generate detailed state space JSON."""
        try:
            state_space_data = {
                "variables": self._extract_state_variables(),
                "observations": self._extract_observation_space(),
                "actions": self._extract_action_space(),
                "transitions": self._extract_transition_structure(),
                "metadata": {
                    "num_variables": len(self.state_space.variables)
                    if hasattr(self.state_space, "variables")
                    else 0,
                    "num_observations": len(self.state_space.observations)
                    if hasattr(self.state_space, "observations")
                    else 0,
                    "num_actions": len(self.state_space.actions)
                    if hasattr(self.state_space, "actions")
                    else 0,
                },
            }
            json_path = output_path / "state_space.json"
            json_path.write_text(json.dumps(state_space_data, indent=2), encoding="utf-8")
            self.checksums["state_space.json"] = self._checksum_dict(state_space_data)
            logger.info(f"Generated {json_path.name}")
        except Exception as e:
            logger.error(f"Failed to generate state space: {e}", exc_info=True)
            # Non-fatal: continue with other files

    def _generate_observations(self, output_path: Path) -> None:
        """Generate observation modalities JSON."""
        try:
            observations = {
                "modalities": self._extract_observation_modalities(),
                "count": len(self.state_space.observations)
                if hasattr(self.state_space, "observations")
                else 0,
            }
            json_path = output_path / "observations.json"
            json_path.write_text(json.dumps(observations, indent=2), encoding="utf-8")
            self.checksums["observations.json"] = self._checksum_dict(observations)
            logger.info(f"Generated {json_path.name}")
        except Exception as e:
            logger.error(f"Failed to generate observations: {e}", exc_info=True)

    def _generate_actions(self, output_path: Path) -> None:
        """Generate actions and policies JSON."""
        try:
            actions = {
                "actions": self._extract_actions(),
                "policies": self._extract_policies(),
                "count": len(self.state_space.actions)
                if hasattr(self.state_space, "actions")
                else 0,
            }
            json_path = output_path / "actions.json"
            json_path.write_text(json.dumps(actions, indent=2), encoding="utf-8")
            self.checksums["actions.json"] = self._checksum_dict(actions)
            logger.info(f"Generated {json_path.name}")
        except Exception as e:
            logger.error(f"Failed to generate actions: {e}", exc_info=True)

    def _generate_transitions(self, output_path: Path) -> None:
        """Generate transition structure JSON."""
        try:
            transitions = {
                "structure": self._extract_transition_structure(),
                "deterministic": self._is_deterministic(),
                "markovian": self._is_markovian(),
            }
            json_path = output_path / "transitions.json"
            json_path.write_text(json.dumps(transitions, indent=2), encoding="utf-8")
            self.checksums["transitions.json"] = self._checksum_dict(transitions)
            logger.info(f"Generated {json_path.name}")
        except Exception as e:
            logger.error(f"Failed to generate transitions: {e}", exc_info=True)

    def _generate_preferences(self, output_path: Path) -> None:
        """Generate preferences and constraints JSON."""
        try:
            preferences = {
                "preferences": self._extract_preferences(),
                "constraints": self._extract_constraints(),
                "objectives": self._extract_objectives(),
            }
            json_path = output_path / "preferences.json"
            json_path.write_text(json.dumps(preferences, indent=2), encoding="utf-8")
            self.checksums["preferences.json"] = self._checksum_dict(preferences)
            logger.info(f"Generated {json_path.name}")
        except Exception as e:
            logger.error(f"Failed to generate preferences: {e}", exc_info=True)

    def _generate_factors(self, output_path: Path) -> None:
        """Generate factorization structure JSON."""
        try:
            factors = {
                "factorization": self._extract_factorization(),
                "factors": self._extract_factor_list(),
            }
            json_path = output_path / "factors.json"
            json_path.write_text(json.dumps(factors, indent=2), encoding="utf-8")
            self.checksums["factors.json"] = self._checksum_dict(factors)
            logger.info(f"Generated {json_path.name}")
        except Exception as e:
            logger.error(f"Failed to generate factors: {e}", exc_info=True)

    def _generate_provenance(self, output_path: Path) -> None:
        """Generate full provenance chain JSON."""
        try:
            provenance = {
                "timestamp": self.timestamp,
                "graph_nodes": self._count_graph_nodes(),
                "graph_edges": self._count_graph_edges(),
                "state_space_elements": self._count_state_space_elements(),
                "semantic_mappings": len(self.mappings) if isinstance(self.mappings, dict) else 0,
                "sources": self._extract_source_evidence(),
            }
            json_path = output_path / "provenance.json"
            json_path.write_text(json.dumps(provenance, indent=2, default=str), encoding="utf-8")
            self.checksums["provenance.json"] = self._checksum_dict(provenance)
            logger.info(f"Generated {json_path.name}")
        except Exception as e:
            logger.error(f"Failed to generate provenance: {e}", exc_info=True)

    def _generate_ontology(self, output_path: Path) -> None:
        """Generate ontology mappings JSON."""
        try:
            ontology = {
                "mappings": self._extract_ontology_mappings(),
                "classes": self._extract_classes(),
                "relationships": self._extract_relationships(),
            }
            json_path = output_path / "ontology.json"
            json_path.write_text(json.dumps(ontology, indent=2), encoding="utf-8")
            self.checksums["ontology.json"] = self._checksum_dict(ontology)
            logger.info(f"Generated {json_path.name}")
        except Exception as e:
            logger.error(f"Failed to generate ontology: {e}", exc_info=True)

    def _generate_actions_policies(self, output_path: Path) -> None:
        """Generate canonical actions and policies JSON."""
        try:
            actions_policies = {
                "actions": self._extract_actions(),
                "policies": self._extract_policies(),
                "count": len(self.state_space.actions)
                if hasattr(self.state_space, "actions")
                else 0,
            }
            json_path = output_path / "actions_policies.json"
            json_path.write_text(json.dumps(actions_policies, indent=2), encoding="utf-8")
            self.checksums["actions_policies.json"] = self._checksum_dict(actions_policies)
            logger.info(f"Generated {json_path.name}")
        except Exception as e:
            logger.error(f"Failed to generate actions_policies: {e}", exc_info=True)

    def _generate_connections(self, output_path: Path) -> None:
        """Generate connections (graph edges) JSON."""
        try:
            connections = {
                "edges": self._extract_relationships(),
                "count": len(self.graph.edges) if self.graph and hasattr(self.graph, "edges") else 0,
                "by_kind": self._count_edges_by_kind(),
            }
            json_path = output_path / "connections.json"
            json_path.write_text(json.dumps(connections, indent=2), encoding="utf-8")
            self.checksums["connections.json"] = self._checksum_dict(connections)
            logger.info(f"Generated {json_path.name}")
        except Exception as e:
            logger.error(f"Failed to generate connections: {e}", exc_info=True)

    def _generate_preferences_constraints(self, output_path: Path) -> None:
        """Generate canonical preferences and constraints JSON."""
        try:
            preferences_constraints = {
                "preferences": self._extract_preferences(),
                "constraints": self._extract_constraints(),
                "objectives": self._extract_objectives(),
            }
            json_path = output_path / "preferences_constraints.json"
            json_path.write_text(json.dumps(preferences_constraints, indent=2), encoding="utf-8")
            self.checksums["preferences_constraints.json"] = self._checksum_dict(preferences_constraints)
            logger.info(f"Generated {json_path.name}")
        except Exception as e:
            logger.error(f"Failed to generate preferences_constraints: {e}", exc_info=True)

    def _generate_markov_blanket(self, output_path: Path) -> None:
        """Compute and serialize the Active-Inference Markov blanket.

        Produces two artifacts in the bundle:

        * ``markov_blanket.json`` — full per-node role assignment
          (internal μ / sensory s / active a / external η) with the
          strategy metadata and per-node rationale from
          :func:`cogant.markov.blanket.serialize_blanket`.
        * ``markov_network.json`` — collapsed four-role aggregate
          network with per-EdgeKind breakdowns from
          :func:`cogant.markov.network.build_blanket_network`.

        The seed strategy is driven by ``self.config``:
          - ``config["markov_blanket"]["strategy"]`` — default ``"auto"``.
          - ``config["markov_blanket"]["module_names"]`` — list of module
            names when strategy is ``"module"``.
          - ``config["markov_blanket"]["mapping_kinds"]`` — list of
            mapping kinds when strategy is ``"mapping_kind"``.

        If no semantic mappings are present, the extractor falls back
        to the ``auto`` cohesion-scoring strategy. Failures are logged
        but not fatal: a minimal stub with an ``error`` field is written
        so the bundle still contains the required files.
        """
        mb_cfg = self.config.get("markov_blanket", {}) if isinstance(self.config, dict) else {}
        strategy = mb_cfg.get("strategy", "auto")
        module_names = mb_cfg.get("module_names")
        mapping_kinds = mb_cfg.get("mapping_kinds", ["hidden_state"])

        try:
            if self.graph is None:
                raise ValueError("no program graph available")

            extractor = MarkovBlanketExtractor(self.graph)

            kwargs = {"strategy": strategy}
            if strategy == "module" and module_names:
                kwargs["module_names"] = list(module_names)
            elif strategy == "mapping_kind":
                kwargs["mapping_kinds"] = list(mapping_kinds)
                kwargs["semantic_mappings"] = self.mappings or {}
            elif strategy == "explicit":
                kwargs["seeds"] = mb_cfg.get("seeds") or []

            blanket = extractor.extract(**kwargs)
            network = build_blanket_network(self.graph, blanket)

            blanket_payload = serialize_blanket(
                blanket,
                self.graph,
                include_rationale=mb_cfg.get("include_rationale", True),
                max_nodes_per_role=mb_cfg.get("max_nodes_per_role"),
            )
            network_payload = network.to_dict()

            blanket_path = output_path / "markov_blanket.json"
            network_path = output_path / "markov_network.json"
            blanket_path.write_text(json.dumps(blanket_payload, indent=2), encoding="utf-8")
            network_path.write_text(json.dumps(network_payload, indent=2), encoding="utf-8")
            self.checksums["markov_blanket.json"] = self._checksum_dict(blanket_payload)
            self.checksums["markov_network.json"] = self._checksum_dict(network_payload)

            # Also emit Mermaid diagrams:
            #   - markov_blanket.mmd: the collapsed four-role view.
            #   - markov_blanket_detail.mmd: member-level detail view
            #     with nodes grouped per role and styled by role class.
            diag_dir = output_path / "diagrams"
            diag_dir.mkdir(parents=True, exist_ok=True)
            mmd = network.to_mermaid()
            (diag_dir / "markov_blanket.mmd").write_text(mmd, encoding="utf-8")

            try:
                from cogant.viz.boundary import BoundaryMapper
                bm = BoundaryMapper()
                detail_mmd = bm.markov_blanket_detailed_mermaid(
                    self.graph, blanket=blanket, max_per_role=12
                )
                (diag_dir / "markov_blanket_detail.mmd").write_text(
                    detail_mmd, encoding="utf-8"
                )
            except Exception as e:  # pragma: no cover - detail view is optional
                logger.warning(f"Failed to render detailed Markov blanket diagram: {e}")

            logger.info(
                "Generated markov_blanket.json (strategy=%s, internal=%d, boundary=%d, external=%d)",
                strategy,
                blanket.stats.get("internal_count", 0),
                blanket.stats.get("sensory_count", 0) + blanket.stats.get("active_count", 0),
                blanket.stats.get("external_count", 0),
            )
        except Exception as e:
            logger.error(f"Failed to generate markov blanket: {e}", exc_info=True)
            # Preserve bundle required-files contract by writing stub files.
            stub_blanket = {
                "schema_version": "1.0.0",
                "error": str(e),
                "seeds": [],
                "stats": {},
                "roles": {"internal": [], "sensory": [], "active": [], "external": []},
                "metadata": {"strategy": strategy, "error": True},
            }
            stub_network = {
                "role_counts": {"internal": 0, "sensory": 0, "active": 0, "external": 0},
                "role_members": {"internal": [], "sensory": [], "active": [], "external": []},
                "aggregate_edges": [],
                "edge_kind_breakdown": [],
                "metadata": {"error": str(e)},
            }
            (output_path / "markov_blanket.json").write_text(
                json.dumps(stub_blanket, indent=2), encoding="utf-8"
            )
            (output_path / "markov_network.json").write_text(
                json.dumps(stub_network, indent=2), encoding="utf-8"
            )
            self.checksums["markov_blanket.json"] = self._checksum_dict(stub_blanket)
            self.checksums["markov_network.json"] = self._checksum_dict(stub_network)

    def _generate_program_graph_json(self, output_path: Path) -> None:
        """Dump the typed ``ProgramGraph`` as a JSON sidecar.

        This is the canonical input for :func:`cogant.viz.png_export.render_program_graph_png`
        and guarantees that any consumer of a COGANT GNN package (``cogant validate``,
        ``cogant viz``, downstream tooling) can rebuild a NetworkX view of the
        repo without re-running the pipeline.
        """
        try:
            from cogant.api.orchestration import program_graph_to_dict

            data = program_graph_to_dict(self.graph)
            path = output_path / "program_graph.json"
            path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            self.checksums["program_graph.json"] = self._checksum_dict(data)
            logger.info("Generated program_graph.json")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Could not generate program_graph.json: {e}")

    def _generate_process_model_json(self, output_path: Path) -> None:
        """Dump the ``ProcessModel`` as a JSON sidecar.

        Mirrors ``_generate_program_graph_json``: gives consumers (notably
        ``render_all_pngs`` → ``render_process_gantt_png``) a standalone file
        to load without re-running ``ProcessExtractor``. The shape matches
        what :func:`cogant.viz.png_export._load_process_model_from_json`
        expects: ``process_id``, ``stages``, ``policies``, ``timelines``.
        """
        if self.process_model is None:
            return
        try:
            def _to_dict(obj: Any) -> Any:
                if obj is None:
                    return None
                if hasattr(obj, "model_dump"):
                    return obj.model_dump()
                if hasattr(obj, "__dict__"):
                    return {k: _to_dict(v) for k, v in vars(obj).items()}
                if isinstance(obj, (list, tuple)):
                    return [_to_dict(v) for v in obj]
                if isinstance(obj, dict):
                    return {k: _to_dict(v) for k, v in obj.items()}
                return obj

            data = {
                "process_id": getattr(self.process_model, "process_id", None)
                or getattr(self.process_model, "id", None),
                "stages": [
                    _to_dict(s) for s in getattr(self.process_model, "stages", []) or []
                ],
                "policies": [
                    _to_dict(p) for p in getattr(self.process_model, "policies", []) or []
                ],
                "timelines": [
                    _to_dict(t) for t in getattr(self.process_model, "timelines", []) or []
                ],
                "connections": [
                    _to_dict(c)
                    for c in getattr(self.process_model, "connections", []) or []
                ],
            }
            path = output_path / "process_model.json"
            path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            self.checksums["process_model.json"] = self._checksum_dict(data)
            logger.info("Generated process_model.json")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Could not generate process_model.json: {e}")

    def _generate_diagrams(self, output_path: Path) -> None:
        """Generate mermaid diagrams driven by the real graph and state space.

        Uses ``cogant.viz.mermaid.MermaidGenerator`` so that diagrams reflect
        actual classes, modules, transitions, and processes — not hand-coded
        placeholders.
        """
        from cogant.viz.mermaid import MermaidGenerator

        diagrams_dir = output_path / "diagrams"
        diagrams_dir.mkdir(exist_ok=True)
        gen = MermaidGenerator()

        try:
            diagrams = {
                "class_diagram.mermaid": gen.generate_class_diagram(self.graph),
                "state_diagram.mermaid": gen.generate_state_diagram(self.state_space),
                "sequence_diagram.mermaid": gen.generate_sequence_diagram(
                    process_model=self.process_model, graph=self.graph
                ),
                "dependency_diagram.mermaid": gen.generate_dependency_graph(
                    self.graph
                ),
                "active_inference_diagram.mermaid": gen.generate_active_inference_diagram(
                    self.state_space
                ),
            }

            for filename, content in diagrams.items():
                filepath = diagrams_dir / filename
                filepath.write_text(content, encoding="utf-8")
                self.checksums[f"diagrams/{filename}"] = self._checksum(content)
                logger.info(f"Generated {filename}")
        except Exception as e:
            logger.error(f"Failed to generate diagrams: {e}", exc_info=True)

    def _generate_visualizations(self, output_path: Path) -> None:
        """Generate HTML visualizations using the real plotting modules.

        Uses ``cogant.viz.plots.StaticPlotter`` to render the node-type,
        edge-type, and confidence distributions, and the dashboard
        renderer to produce a populated dashboard.html.
        """
        from cogant.viz.plots import StaticPlotter

        viz_dir = output_path / "visualizations"
        viz_dir.mkdir(exist_ok=True)

        try:
            dashboard = self._generate_dashboard_html()
            dashboard_path = viz_dir / "dashboard.html"
            dashboard_path.write_text(dashboard, encoding="utf-8")
            self.checksums["visualizations/dashboard.html"] = self._checksum(dashboard)
            logger.info("Generated dashboard.html")

            charts_dir = viz_dir / "charts"
            charts_dir.mkdir(exist_ok=True)

            plotter = StaticPlotter()
            charts: dict[str, str] = {}
            try:
                charts["node_dist.html"] = plotter.plot_node_type_distribution(self.graph)
            except Exception as e:
                logger.warning(f"node_dist plot failed, falling back: {e}")
                charts["node_dist.html"] = self._fallback_chart(
                    "Node distribution", self._count_nodes_by_kind()
                )
            try:
                charts["edge_dist.html"] = plotter.plot_edge_type_distribution(self.graph)
            except Exception as e:
                logger.warning(f"edge_dist plot failed, falling back: {e}")
                charts["edge_dist.html"] = self._fallback_chart(
                    "Edge distribution", self._count_edges_by_kind()
                )
            try:
                charts["confidence.html"] = plotter.plot_confidence_distribution(
                    self.mappings if isinstance(self.mappings, dict) else {}
                )
            except Exception as e:
                logger.warning(f"confidence plot failed, falling back: {e}")
                charts["confidence.html"] = self._fallback_chart(
                    "Confidence distribution",
                    self._count_mappings_by_tier(),
                )

            for filename, content in charts.items():
                filepath = charts_dir / filename
                filepath.write_text(content, encoding="utf-8")
                self.checksums[f"visualizations/charts/{filename}"] = self._checksum(content)
                logger.info(f"Generated {filename}")
        except Exception as e:
            logger.error(f"Failed to generate visualizations: {e}", exc_info=True)

    def _count_nodes_by_kind(self) -> dict[str, int]:
        """Count nodes by kind for fallback charts."""
        from collections import defaultdict

        counts: dict[str, int] = defaultdict(int)
        if self.graph and hasattr(self.graph, "nodes"):
            for node in self.graph.nodes.values():
                counts[str(node.kind)] += 1
        return dict(counts)

    def _count_mappings_by_tier(self) -> dict[str, int]:
        """Count semantic mappings by confidence tier."""
        from collections import defaultdict

        counts: dict[str, int] = defaultdict(int)
        if not isinstance(self.mappings, dict):
            return {}
        for m in self.mappings.values():
            tier = getattr(m, "confidence_tier", None)
            label = tier.value if hasattr(tier, "value") else str(tier or "unknown")
            counts[label] += 1
        return dict(counts)

    def _fallback_chart(self, title: str, counts: dict[str, int]) -> str:
        """Render a tiny SVG bar chart from a counts dict.

        Used when the StaticPlotter raises (e.g. matplotlib unavailable
        in the runtime environment). The output is a self-contained HTML
        document with an inline SVG so it never depends on external
        assets.
        """
        max_v = max(counts.values()) if counts else 1
        bar_w = 40
        gap = 12
        chart_h = 200
        x = gap
        bars: list[str] = []
        labels: list[str] = []
        for key, value in sorted(counts.items(), key=lambda kv: -kv[1]):
            bar_h = int((value / max_v) * (chart_h - 30)) if max_v else 0
            y = chart_h - bar_h - 20
            bars.append(
                f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bar_h}" '
                f'fill="#4682B4" stroke="#1e3f6b"/>'
                f'<text x="{x + bar_w / 2}" y="{y - 4}" font-size="10" '
                f'text-anchor="middle">{value}</text>'
            )
            labels.append(
                f'<text x="{x + bar_w / 2}" y="{chart_h - 4}" font-size="9" '
                f'text-anchor="middle" transform="rotate(-15 {x + bar_w / 2} {chart_h - 4})">{key}</text>'
            )
            x += bar_w + gap
        width = max(x + gap, 200)
        return (
            "<!DOCTYPE html><html><head><title>"
            + title
            + '</title></head><body><h1 style="font-family:Arial">'
            + title
            + f'</h1><svg width="{width}" height="{chart_h + 20}" xmlns="http://www.w3.org/2000/svg" '
            + 'style="font-family:Arial">'
            + "".join(bars)
            + "".join(labels)
            + "</svg></body></html>"
        )

    def _create_manifest(self, output_path: Path) -> dict[str, Any]:
        """Create and save the package manifest."""
        manifest = {
            "version": self.PACKAGE_VERSION,
            "timestamp": self.timestamp,
            "package_path": str(output_path),
            "checksums": self.checksums,
            "files": list(self.checksums.keys()),
            "graph_stats": {
                "nodes": self._count_graph_nodes(),
                "edges": self._count_graph_edges(),
            },
            "state_space_stats": self._count_state_space_elements(),
            "semantic_mappings_count": len(self.mappings)
            if isinstance(self.mappings, dict)
            else 0,
        }

        manifest_path = output_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
        logger.info("Generated manifest.json")

        return manifest

    # Data extraction helpers

    def _state_var_object(self, var_id: str) -> Any | None:
        """Resolve a state-space variable id back to its full object.

        ``StateSpaceModel.variables`` is a list of string ids; the full
        ``StateVariable`` objects live on
        ``StateSpaceModel._state_var_objects`` (an internal dict the
        compiler populates). This helper centralises the lookup.
        """
        store = getattr(self.state_space, "_state_var_objects", None)
        if isinstance(store, dict):
            return store.get(var_id)
        return None

    def _action_object(self, action_id: str) -> Any | None:
        """Resolve an action id back to its full ``Action`` object."""
        actions = getattr(self.state_space, "actions", None)
        if isinstance(actions, dict):
            return actions.get(action_id)
        return None

    def _extract_state_variables(self) -> list[dict[str, Any]]:
        """Extract state variables with type/cardinality/source info."""
        out: list[dict[str, Any]] = []
        for var_id in getattr(self.state_space, "variables", []) or []:
            obj = self._state_var_object(var_id)
            if obj is None:
                out.append({"id": str(var_id), "name": str(var_id), "type": "variable"})
                continue
            out.append(
                {
                    "id": getattr(obj, "id", str(var_id)),
                    "name": getattr(obj, "name", str(var_id)),
                    "var_type": getattr(getattr(obj, "var_type", None), "value", None)
                    or str(getattr(obj, "var_type", "")),
                    "cardinality": getattr(obj, "cardinality", None),
                    "domain": getattr(obj, "domain", None),
                    "factor": getattr(obj, "factor", None),
                    "description": getattr(obj, "description", ""),
                    "source_node_ids": getattr(obj, "source_node_ids", []) or [],
                    "confidence": _enum_value(getattr(obj, "confidence", None)),
                }
            )
        return out

    def _extract_observation_space(self) -> list[dict[str, Any]]:
        """Extract observation space with full modality info."""
        out: list[dict[str, Any]] = []
        observations = getattr(self.state_space, "observations", None)
        if observations is None:
            return out
        if isinstance(observations, dict):
            iterable = observations.values()
        else:
            iterable = observations
        for obs in iterable:
            if hasattr(obs, "name"):
                out.append(
                    {
                        "id": getattr(obs, "id", str(obs)),
                        "name": getattr(obs, "name", ""),
                        "modality": getattr(obs, "modality", "symbolic"),
                        "values": getattr(obs, "values", None),
                        "source_channels": getattr(obs, "source_channels", []) or [],
                        "description": getattr(obs, "description", ""),
                        "confidence": _enum_value(getattr(obs, "confidence", None)),
                    }
                )
            else:
                out.append({"id": str(obs), "name": str(obs), "modality": "symbolic"})
        return out

    def _extract_action_space(self) -> list[dict[str, Any]]:
        """Extract action space with controllers and effects."""
        out: list[dict[str, Any]] = []
        actions = getattr(self.state_space, "actions", None)
        if actions is None:
            return out
        iterable = actions.values() if isinstance(actions, dict) else actions
        for action in iterable:
            if hasattr(action, "name"):
                out.append(
                    {
                        "id": getattr(action, "id", str(action)),
                        "name": getattr(action, "name", ""),
                        "controller_id": getattr(action, "controller_id", None),
                        "parameters": getattr(action, "parameters", []) or [],
                        "effects": list(
                            getattr(action, "effects", None)
                            or getattr(action, "affects_state_vars", None)
                            or []
                        ),
                        "preconditions": list(
                            getattr(action, "preconditions", None) or []
                        ),
                        "description": getattr(action, "description", ""),
                        "confidence": _enum_value(getattr(action, "confidence", None)),
                    }
                )
            else:
                out.append({"id": str(action), "name": str(action)})
        return out

    def _extract_transition_structure(self) -> dict[str, Any]:
        """Extract transition structure from the real state space."""
        transitions = getattr(self.state_space, "transitions", None) or []
        return {
            "type": "state_transitions",
            "transition_count": len(transitions) if hasattr(transitions, "__len__") else 0,
            "deterministic": self._is_deterministic(),
            "markovian": self._is_markovian(),
            "time_regime": getattr(self.state_space, "time_regime", None),
        }

    def _extract_observation_modalities(self) -> list[str]:
        """Extract observation modalities present in the state space."""
        modalities: list[str] = []
        observations = getattr(self.state_space, "observations", None)
        if observations is not None:
            iterable = (
                observations.values() if isinstance(observations, dict) else observations
            )
            for obs in iterable:
                modality = getattr(obs, "modality", None)
                if modality and modality not in modalities:
                    modalities.append(str(modality))
        if not modalities:
            modalities = ["symbolic"]
        return modalities

    def _extract_actions(self) -> list[dict[str, Any]]:
        """Extract actions with full details including effects and preconditions."""
        actions = getattr(self.state_space, "actions", None)
        if actions is None:
            return []

        def _effects_for_action(action: Any) -> list[str]:
            effects = getattr(action, "effects", None)
            if effects is None:
                effects = getattr(action, "affects_state_vars", None)
            return list(effects or [])

        actions_list: list[dict[str, Any]] = []
        iterable: Any
        if isinstance(actions, dict):
            iterable = actions.values()
        else:
            iterable = actions
        for action in iterable:
            if not hasattr(action, "name"):
                actions_list.append({"id": str(action), "name": str(action)})
                continue
            actions_list.append(
                {
                    "id": getattr(action, "id", str(action)),
                    "name": getattr(action, "name", ""),
                    "controller_id": getattr(action, "controller_id", None),
                    "parameters": getattr(action, "parameters", []) or [],
                    "effects": _effects_for_action(action),
                    "preconditions": getattr(action, "preconditions", []) or [],
                    "description": getattr(action, "description", ""),
                    "confidence": _enum_value(getattr(action, "confidence", None)),
                }
            )
        return actions_list

    def _extract_policies(self) -> list[dict[str, Any]]:
        """Extract policies derived from POLICY/ORCHESTRATION mappings.

        Falls back to a single deterministic stub if no policy mappings
        exist so the section is never empty in a working pipeline.
        """
        out: list[dict[str, Any]] = []
        if isinstance(self.mappings, dict):
            for mid, m in self.mappings.items():
                kind = getattr(m, "kind", None)
                if kind in (MappingKind.POLICY, MappingKind.ORCHESTRATION):
                    out.append(
                        {
                            "id": mid,
                            "label": getattr(m, "semantic_label", "") or mid,
                            "kind": _enum_value(kind),
                            "description": getattr(m, "description", ""),
                            "controller_node_ids": list(
                                getattr(m, "graph_fragment_node_ids", []) or []
                            ),
                            "confidence": getattr(m, "confidence_score", 0.0),
                            "tier": _enum_value(getattr(m, "confidence_tier", None)),
                        }
                    )
        if not out:
            out.append(
                {
                    "id": "policy:default",
                    "label": "deterministic-default",
                    "kind": "policy",
                    "description": "No POLICY mappings extracted; using deterministic default.",
                    "controller_node_ids": [],
                    "confidence": 0.0,
                    "tier": "static_only",
                }
            )
        return out

    def _extract_preferences(self) -> list[dict[str, Any]]:
        """Extract preferences from state space."""
        if not hasattr(self.state_space, "preferences"):
            return []
        prefs_list = []
        for _pref_id, pref in self.state_space.preferences.items():
            prefs_list.append({
                "id": pref.id,
                "name": pref.name,
                "description": pref.description,
                "scope": pref.scope,
                "expression": pref.expression,
                "weight": pref.weight,
                "source": pref.source,
                "confidence": pref.confidence.value if hasattr(pref.confidence, 'value') else str(pref.confidence),
            })
        return prefs_list

    def _extract_constraints(self) -> list[dict[str, Any]]:
        """Extract constraints from CONSTRAINT mappings and state-space preferences."""
        out: list[dict[str, Any]] = []
        if isinstance(self.mappings, dict):
            for mid, m in self.mappings.items():
                if getattr(m, "kind", None) == MappingKind.CONSTRAINT:
                    out.append(
                        {
                            "id": mid,
                            "label": getattr(m, "semantic_label", "") or mid,
                            "description": getattr(m, "description", ""),
                            "scope": list(
                                getattr(m, "graph_fragment_node_ids", []) or []
                            ),
                            "confidence": getattr(m, "confidence_score", 0.0),
                            "tier": _enum_value(getattr(m, "confidence_tier", None)),
                            "source": "translation_rule",
                        }
                    )
        prefs = getattr(self.state_space, "preferences", None)
        if isinstance(prefs, dict):
            for pid, pref in prefs.items():
                if getattr(pref, "source", "") == "constraint":
                    out.append(
                        {
                            "id": pid,
                            "label": getattr(pref, "name", "") or pid,
                            "description": getattr(pref, "description", ""),
                            "scope": list(getattr(pref, "scope", []) or []),
                            "confidence": _enum_value(getattr(pref, "confidence", None)),
                            "weight": getattr(pref, "weight", 1.0),
                            "expression": getattr(pref, "expression", ""),
                            "source": "state_space.preferences",
                        }
                    )
        return out

    def _extract_objectives(self) -> list[dict[str, Any]]:
        """Extract objectives from PREFERENCE mappings and state-space preferences."""
        out: list[dict[str, Any]] = []
        if isinstance(self.mappings, dict):
            for mid, m in self.mappings.items():
                if getattr(m, "kind", None) == MappingKind.PREFERENCE:
                    out.append(
                        {
                            "id": mid,
                            "label": getattr(m, "semantic_label", "") or mid,
                            "description": getattr(m, "description", ""),
                            "weight": 1.0,
                            "scope": list(
                                getattr(m, "graph_fragment_node_ids", []) or []
                            ),
                            "confidence": getattr(m, "confidence_score", 0.0),
                            "tier": _enum_value(getattr(m, "confidence_tier", None)),
                            "source": "translation_rule",
                        }
                    )
        prefs = getattr(self.state_space, "preferences", None)
        if isinstance(prefs, dict):
            for pid, pref in prefs.items():
                source = getattr(pref, "source", "")
                if source != "constraint":
                    out.append(
                        {
                            "id": pid,
                            "label": getattr(pref, "name", "") or pid,
                            "description": getattr(pref, "description", ""),
                            "weight": getattr(pref, "weight", 1.0),
                            "scope": list(getattr(pref, "scope", []) or []),
                            "expression": getattr(pref, "expression", ""),
                            "confidence": _enum_value(getattr(pref, "confidence", None)),
                            "source": source or "state_space.preferences",
                        }
                    )
        return out

    def _extract_factorization(self) -> dict[str, Any]:
        """Extract factorization structure from the state space.

        Groups state variables by their ``factor`` attribute (assigned by
        the compiler) and returns the factor → variable mapping plus a
        small summary so the GNN package always carries a real
        factorization view.
        """
        from collections import defaultdict

        groups: dict[str, list[str]] = defaultdict(list)
        ungrouped: list[str] = []
        for var_id in getattr(self.state_space, "variables", []) or []:
            obj = self._state_var_object(var_id)
            factor = getattr(obj, "factor", None) if obj else None
            if factor:
                groups[str(factor)].append(var_id)
            else:
                ungrouped.append(var_id)
        if not groups and ungrouped:
            groups["default"] = ungrouped
        elif ungrouped:
            groups["default"].extend(ungrouped)

        return {
            "type": "factor_partition" if groups else "none",
            "factor_count": len(groups),
            "variable_count": sum(len(v) for v in groups.values()),
            "factors": [
                {"id": fid, "variables": sorted(vs)}
                for fid, vs in sorted(groups.items())
            ],
        }

    def _extract_factor_list(self) -> list[dict[str, Any]]:
        """Flat list of factor descriptors used by the factors.json export."""
        factorization = self._extract_factorization()
        return list(factorization.get("factors", []))

    def _extract_ontology_mappings(self) -> list[dict[str, Any]]:
        """Extract ontology mappings — one row per semantic mapping with full role info."""
        out: list[dict[str, Any]] = []
        if not isinstance(self.mappings, dict):
            return out
        for mid, m in self.mappings.items():
            out.append(
                {
                    "id": mid,
                    "kind": _enum_value(getattr(m, "kind", None)),
                    "semantic_label": getattr(m, "semantic_label", "") or mid,
                    "description": getattr(m, "description", ""),
                    "graph_node_ids": list(
                        getattr(m, "graph_fragment_node_ids", []) or []
                    ),
                    "graph_edge_ids": list(
                        getattr(m, "graph_fragment_edge_ids", []) or []
                    ),
                    "confidence": getattr(m, "confidence_score", 0.0),
                    "tier": _enum_value(getattr(m, "confidence_tier", None)),
                    "evidence_count": getattr(m, "evidence_count", 0),
                }
            )
        return out

    def _extract_classes(self) -> list[str]:
        """Extract class definitions."""
        classes = set()
        for _nid, node in self.graph.nodes.items():
            if node.kind == NodeKind.CLASS:
                classes.add(node.name)
        return list(classes)

    def _extract_relationships(self) -> list[dict[str, str]]:
        """Extract relationships."""
        relationships = []
        for _eid, edge in self.graph.edges.items():
            relationships.append({"source": edge.source_id, "target": edge.target_id, "kind": str(edge.kind)})
        return relationships[:100]  # Limit to first 100

    def _extract_source_evidence(self) -> dict[str, Any]:
        """Extract source evidence."""
        return {
            "graph_nodes": self._count_graph_nodes(),
            "graph_edges": self._count_graph_edges(),
            "timestamp": self.timestamp,
        }

    def _count_graph_nodes(self) -> int:
        """Count nodes in graph."""
        return len(self.graph.nodes) if self.graph and hasattr(self.graph, "nodes") else 0

    def _count_graph_edges(self) -> int:
        """Count edges in graph."""
        return len(self.graph.edges) if self.graph and hasattr(self.graph, "edges") else 0

    def _count_edges_by_kind(self) -> dict[str, int]:
        """Count edges by kind."""
        from collections import defaultdict
        counts = defaultdict(int)
        if self.graph and hasattr(self.graph, "edges"):
            for edge in self.graph.edges.values():
                counts[str(edge.kind)] += 1
        return dict(counts)

    def _count_state_space_elements(self) -> dict[str, int]:
        """Count state space elements."""
        return {
            "variables": len(self.state_space.variables)
            if hasattr(self.state_space, "variables")
            else 0,
            "observations": len(self.state_space.observations)
            if hasattr(self.state_space, "observations")
            else 0,
            "actions": len(self.state_space.actions)
            if hasattr(self.state_space, "actions")
            else 0,
        }

    def _is_deterministic(self) -> bool:
        """Heuristic determinism check.

        A model is treated as non-deterministic when any transition has
        more than one ``to_state`` candidate, or when any likelihood
        spans multiple observations conditioned on the same state set.
        """
        transitions = getattr(self.state_space, "transitions", None) or []
        for t in transitions:
            to_states = getattr(t, "to_states", None) or getattr(t, "successors", None) or []
            if hasattr(to_states, "__len__") and len(to_states) > 1:
                return False
        likelihoods = getattr(self.state_space, "likelihoods", None) or []
        for likelihood in likelihoods:
            obs = getattr(likelihood, "observations", None) or []
            if hasattr(obs, "__len__") and len(obs) > 1:
                return False
        return True

    def _is_markovian(self) -> bool:
        """Heuristic Markov property check.

        A transition that conditions on more than one prior state set
        breaks the Markov assumption.
        """
        transitions = getattr(self.state_space, "transitions", None) or []
        for t in transitions:
            from_states = (
                getattr(t, "from_states", None)
                or getattr(t, "predecessors", None)
                or []
            )
            if hasattr(from_states, "__len__") and len(from_states) > 1:
                return False
        return True

    def _generate_dashboard_html(self) -> str:
        """Generate a populated dashboard HTML for the model package.

        This is a small, self-contained dashboard rendered server-side
        from the real graph, mapping, and state-space counts. No
        external assets, no JS execution required.
        """
        nodes_by_kind = self._count_nodes_by_kind()
        edges_by_kind = self._count_edges_by_kind()
        mappings_by_tier = self._count_mappings_by_tier()
        state_space_counts = self._count_state_space_elements()

        def _rows(d: dict[str, Any]) -> str:
            if not d:
                return "<tr><td colspan='2'><em>(none)</em></td></tr>"
            return "".join(
                f"<tr><td>{k}</td><td>{v}</td></tr>"
                for k, v in sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))
            )

        return f"""<!DOCTYPE html>
<html>
<head>
<title>GNN Model Dashboard</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 20px; color: #222 }}
h1 {{ color: #1e3f6b }}
table {{ border-collapse: collapse; margin: 8px 0 16px 0 }}
th, td {{ border: 1px solid #999; padding: 4px 10px; text-align: left }}
.stat {{ margin: 10px 0; padding: 10px 14px; border: 1px solid #ccc; background: #f6f8fb }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px }}
</style>
</head>
<body>
<h1>GNN Model Package Dashboard</h1>
<div class="stat">
    <h3>Package</h3>
    <p>Version: {self.PACKAGE_VERSION}</p>
    <p>Generated: {self.timestamp}</p>
    <p>Nodes: {self._count_graph_nodes()} &nbsp; Edges: {self._count_graph_edges()} &nbsp;
       Mappings: {len(self.mappings) if isinstance(self.mappings, dict) else 0}</p>
</div>
<div class="grid">
<div class="stat"><h3>Nodes by kind</h3><table><tr><th>Kind</th><th>Count</th></tr>{_rows(nodes_by_kind)}</table></div>
<div class="stat"><h3>Edges by kind</h3><table><tr><th>Kind</th><th>Count</th></tr>{_rows(edges_by_kind)}</table></div>
<div class="stat"><h3>Mappings by confidence tier</h3><table><tr><th>Tier</th><th>Count</th></tr>{_rows(mappings_by_tier)}</table></div>
<div class="stat"><h3>State space</h3><table><tr><th>Component</th><th>Count</th></tr>{_rows(state_space_counts)}</table></div>
</div>
</body>
</html>"""

    # Utility functions

    @staticmethod
    def _checksum(text: str) -> str:
        """Compute SHA256 checksum of text."""
        return hashlib.sha256(text.encode()).hexdigest()

    @staticmethod
    def _checksum_dict(data: dict[str, Any]) -> str:
        """Compute SHA256 checksum of dictionary."""
        text = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(text.encode()).hexdigest()
