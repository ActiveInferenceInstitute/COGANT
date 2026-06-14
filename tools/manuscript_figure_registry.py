"""Registry of manuscript figures copied from COGANT run outputs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ManuscriptFigure:
    """A package-generated figure copied into the manuscript asset tree."""

    key: str
    source: str
    destination: str
    caption: str
    role: str
    source_artifact: str = ""
    renderer: str = ""
    method_note: str = ""
    reading_guide: str = ""
    limitations: str = ""
    alt_text: str = ""
    min_width_px: int = 1000
    min_height_px: int = 500
    require_manuscript_reference: bool = True
    evidence_requirements: tuple[str, ...] = ()


MANUSCRIPT_FIGURES: tuple[ManuscriptFigure, ...] = (
    ManuscriptFigure(
        key="graphical_abstract",
        source="cogant/output/calculator/figures/graphical_abstract.png",
        destination="cogant_graphical_abstract.png",
        role="code-gnn-code-graphical-abstract",
        caption=(
            "COGANT graphical abstract generated from the calculator run, "
            "showing source code, program graph, semantic roles, state-space "
            "compilation, GNN matrices, Markov blanket partition, and "
            "roundtrip artifact status."
        ),
        source_artifact="cogant/output/calculator/program_graph.json",
        renderer="cogant.viz.inspection_dashboard.render_graphical_abstract_png",
        method_note="End-to-end visual synopsis composed from run artifacts.",
        reading_guide="Read left-to-right as code graph, semantic mapping, matrices, boundary, and roundtrip evidence.",
        limitations="Overview only; detailed panels provide the inspectable counts and deltas.",
        alt_text="Graphical abstract summarizing COGANT's code to graph to GNN to code evidence chain.",
        min_width_px=1400,
        min_height_px=600,
    ),
    ManuscriptFigure(
        key="interpretability_overview",
        source="cogant/output/calculator/figures/interpretability_overview.png",
        destination="cogant_interpretability_overview.png",
        role="overview-code-to-gnn-interpretability",
        caption=(
            "Compact COGANT interpretability overview for the calculator run, "
            "summarizing the code graph, semantic role mappings, GNN state "
            "space, and Markov blanket partition on one page."
        ),
        source_artifact="cogant/output/calculator/program_graph.json",
        renderer="cogant.viz.png.render_interpretability_overview_png",
        method_note=(
            "Multi-panel overview generated from program graph, rule trace, state space, "
            "and blanket artifacts."
        ),
        reading_guide="Use it as the map of the inspection workbench before reading individual diagnostic figures.",
        limitations="Small panels intentionally trade detail for continuity across conversion boundaries.",
        alt_text="Interpretability overview tying graph, mappings, state space, and Markov blanket panels together.",
        min_width_px=1800,
        min_height_px=900,
    ),
    ManuscriptFigure(
        key="forward_program_graph",
        source="cogant/output/calculator/data/program_graph.png",
        destination="cogant_forward_program_graph.png",
        role="forward-code-to-graph",
        caption=(
            "Calculator fixture after the forward codebase-to-program-graph "
            "conversion; nodes are the package-emitted program entities used "
            "by downstream semantic mapping."
        ),
        source_artifact="cogant/output/calculator/program_graph.json",
        renderer="cogant.viz.png.render_program_graph_png",
        method_note="Deterministic containment-first graph drawing from the same JSON consumed by semantic mapping.",
        reading_guide=(
            "Node fill encodes program kind; edge color/style encodes relation kind; "
            "outlines mark semantic roles when rule evidence exists."
        ),
        limitations="Static extraction view; it does not prove complete runtime behavior coverage.",
        alt_text="Program graph for calculator with node kinds, edge kinds, counts, and semantic-role outlines.",
        min_width_px=1800,
        min_height_px=1200,
    ),
    ManuscriptFigure(
        key="forward_state_space_factor",
        source="cogant/output/calculator/state_space_factor.png",
        destination="cogant_forward_state_space_factor.png",
        role="forward-graph-to-state-space",
        caption=(
            "State-space factor graph emitted from the same calculator run, "
            "showing the one-way conversion from semantic mappings into "
            "hidden state, observation, and action factors."
        ),
        source_artifact="cogant/output/calculator/state_space.json",
        renderer="cogant.viz.png.render_state_space_factor_png",
        method_note="Factor graph view of hidden states, observations, actions, and transitions.",
        reading_guide=(
            "Read blue as hidden state, teal as observation, orange as action, and "
            "connecting edges as matrix-generating relations."
        ),
        limitations="Displays compiled factors, not an empirical validation of behavioral adequacy.",
        alt_text="State-space factor graph showing hidden states, observations, actions, and transition links.",
        min_width_px=1800,
        min_height_px=1200,
    ),
    ManuscriptFigure(
        key="forward_abcd_matrices",
        source="cogant/output/flask_app/connections_matrix.png",
        destination="cogant_forward_abcd_matrices.png",
        role="forward-state-space-to-matrices",
        caption=(
            "A/B/C/D connection-matrix panel rendered from the Flask application "
            "fixture's exported model.gnn.json matrix arrays, with hidden-state "
            "group annotations for program/service states and inheritance-role states."
        ),
        source_artifact="cogant/output/flask_app/gnn_package/model.gnn.json",
        renderer="cogant.viz.png.render_connections_matrix_png",
        method_note=(
            "Heatmap rendering of exported likelihood, transition, preference, and "
            "prior arrays. A, C, and D are direct matrix/vector panels; B is a "
            "recorded action-axis summary of the exported transition tensor. Axis "
            "labels and state groups are derived from model.gnn.json."
        ),
        reading_guide=(
            "Inspect shapes, sparsity, identity/default bands, hidden-state index "
            "groups, and the B reducer metadata before interpreting downstream "
            "inference traces."
        ),
        limitations=(
            "Panels are inspection views of exported structural values, not learned "
            "probability estimates or semantic-adequacy evidence."
        ),
        alt_text=(
            "A/B/C/D matrix heatmap panel generated from the Flask application "
            "state-space model."
        ),
        min_width_px=1800,
        min_height_px=1300,
    ),
    ManuscriptFigure(
        key="markov_blanket",
        source="cogant/output/calculator/figures/markov_blanket.png",
        destination="cogant_markov_blanket.png",
        role="structural-markov-blanket-partition",
        caption=(
            "Structural Markov-blanket partition generated from the calculator "
            "gnn_package/markov_blanket.json sidecar."
        ),
        source_artifact="cogant/output/calculator/gnn_package/markov_blanket.json",
        renderer="cogant.viz.png.render_markov_blanket_png",
        method_note=(
            "Deterministic role-partition renderer for internal, sensory, active, "
            "and external program-node groups."
        ),
        reading_guide=(
            "Use the role lanes and counts to inspect the emitted structural boundary "
            "before reading runtime traces."
        ),
        limitations=(
            "This is a total structural partition over emitted program nodes; it is "
            "not a probabilistic conditional-independence proof."
        ),
        alt_text=(
            "Markov blanket partition with internal, sensory, active, and external "
            "role groups for the calculator fixture."
        ),
        min_width_px=1600,
        min_height_px=1000,
    ),
    ManuscriptFigure(
        key="gnn_markdown_render",
        source="cogant/output/calculator/figures/model_gnn_mosaic.png",
        destination="cogant_gnn_markdown_render.png",
        role="forward-gnn-markdown-render",
        caption=(
            "Rendered all-page mosaic of the emitted model.gnn.md bundle, the "
            "human-readable Generalized Notation Notation artifact."
        ),
        source_artifact="cogant/output/calculator/gnn_package/model.gnn.md",
        renderer="cogant.viz.png.gnn_markdown.render_gnn_markdown_mosaic_png",
        method_note="Native matplotlib mosaic composed from every rendered GNN markdown page.",
        reading_guide=(
            "Use it to inspect the reader-facing bundle format alongside the JSON "
            "and validation sidecars."
        ),
        limitations=(
            "The mosaic is readability and interchange evidence, not a validation result."
        ),
        alt_text="Eight-panel mosaic of the calculator model.gnn.md bundle.",
        min_width_px=1600,
        min_height_px=1200,
    ),
    ManuscriptFigure(
        key="upstream_generative_model",
        source=(
            "cogant/output/upstream_pipeline/8_visualization_output/model.gnn/"
            "model.gnn_generative_model.png"
        ),
        destination="cogant_upstream_generative_model.png",
        role="gnn-to-upstream-generative-model",
        caption=(
            "Upstream Generalized Notation Notation visualization of the "
            "POMDP generative-model structure."
        ),
        source_artifact="cogant/output/upstream_pipeline/8_visualization_output/model.gnn/model.gnn_generative_model.png",
        renderer="upstream GNN visualization pipeline",
        method_note="Interoperability figure copied from the upstream Generalized Notation Notation pipeline output.",
        reading_guide=(
            "Read this as a boundary check that COGANT's emitted GNN artifact can be "
            "accepted by upstream tooling."
        ),
        limitations="It confirms representation compatibility, not model correctness.",
        alt_text="Upstream GNN visualization of the generated POMDP model structure.",
        min_width_px=1800,
        min_height_px=2400,
    ),
    ManuscriptFigure(
        key="roundtrip_batch_gantt",
        source="cogant/output/dashboard/run_gantt.png",
        destination="cogant_roundtrip_batch_gantt.png",
        role="forward-reverse-forward-roundtrip",
        caption=(
            "Calculator-target publication timeline rendered from run_all's manifest, "
            "showing the selected command sequence and the explicit "
            "roundtrip:calculator stage; gate markers identify validation and "
            "roundtrip checks."
        ),
        source_artifact="cogant/output/run_manifest.json",
        renderer="tools.manuscript_figures._render_publication_batch_timeline",
        method_note=(
            "Wide matplotlib timeline generated from the calculator command records "
            "in the batch manifest; batch-wide context remains in the sidecar."
        ),
        reading_guide=(
            "Read the ordered bars as the recorded calculator stage sequence; elapsed "
            "durations are audit metadata, not benchmark claims. Gate markers "
            "distinguish verification gates from ordinary execution stages."
        ),
        limitations="Timing varies by machine and should not be interpreted as a benchmark without repeated runs.",
        alt_text="Batch dashboard Gantt chart with forward, visualization, validation, and roundtrip stages.",
        min_width_px=1400,
        min_height_px=700,
        evidence_requirements=("targets_count", "stages"),
    ),
    ManuscriptFigure(
        key="batch_evidence_summary",
        source="cogant/output/dashboard/batch_evidence_summary.png",
        destination="cogant_batch_evidence_summary.png",
        role="aggregate-batch-dashboard-evidence",
        caption=(
            "Aggregate batch evidence summary rendered from "
            "cogant/output/dashboard/metrics_per_target.json, with semantic-role "
            "totals, validation-score buckets, roundtrip status, and visual "
            "workbench completeness."
        ),
        source_artifact="cogant/output/dashboard/metrics_per_target.json",
        renderer="tools.manuscript_figures._render_publication_batch_evidence_summary",
        method_note=(
            "Matplotlib small-multiple chart generated from the batch dashboard JSON; "
            "the raw Mermaid audit sidecars remain in cogant/output/dashboard/."
        ),
        reading_guide=(
            "Read the semantic-role bar chart first, then verify that validation, "
            "roundtrip, and visual-workbench panels cover the same target batch."
        ),
        limitations=(
            "Aggregate counts describe emitted artifacts for this run; they do not "
            "prove semantic correctness, role-ground-truth coverage, or benchmark performance."
        ),
        alt_text=(
            "Four-panel batch summary with semantic role totals, validation score "
            "buckets, roundtrip statuses, and visual workbench completeness."
        ),
        min_width_px=1200,
        min_height_px=800,
        evidence_requirements=(
            "target_count",
            "total_nodes",
            "total_edges",
            "total_mappings",
            "validation_score_count",
            "role_total_count",
            "roundtrip_status_kind_count",
            "visual_artifact_total_count",
            "complete_evidence_target_count",
        ),
    ),
    ManuscriptFigure(
        key="roundtrip_visual_diff",
        source="cogant/output/calculator/figures/roundtrip_diff.png",
        destination="cogant_roundtrip_visual_diff.png",
        role="roundtrip-graph-gnn-matrix-diff",
        caption=(
            "Roundtrip visual diff for the calculator run, comparing original "
            "and regenerated graph counts, GNN sections, matrix shapes, and "
            "roundtrip invariants."
        ),
        source_artifact="cogant/output/calculator/roundtrip/metrics.json",
        renderer="cogant.viz.inspection_dashboard roundtrip renderer",
        method_note="Invariant-ledger visual diff from original and regenerated graph/GNN/matrix artifacts.",
        reading_guide=(
            "Read status, deltas, and compile/smoke panels separately; role preservation "
            "is weaker than strict structural isomorphism."
        ),
        limitations="Reverse synthesis is intentionally skeletal and can preserve roles while drifting structurally.",
        alt_text="Roundtrip visual diff showing graph, GNN, matrix, invariant, and generated-code status.",
        min_width_px=1400,
        min_height_px=650,
    ),
    ManuscriptFigure(
        key="rule_evidence_trace",
        source="cogant/output/calculator/figures/rule_trace.png",
        destination="cogant_rule_evidence_trace.png",
        role="rule-evidence-human-review-trace",
        caption=(
            "Rule evidence trace figure generated from rule_evidence_trace.json, "
            "showing which translation rules contributed semantic mappings."
        ),
        source_artifact="cogant/output/calculator/rule_evidence_trace.json",
        renderer="cogant.viz.inspection_dashboard native rule trace renderer",
        method_note=(
            "Aggregate per-rule contribution bars with mapping, conflict, and "
            "accepted/rejected totals; the per-mapping rule id, matched nodes, and "
            "confidence components live in the source JSON, not this rendered panel."
        ),
        reading_guide=(
            "Rows are proposed semantic mappings; inspect rule id and confidence "
            "components before trusting a role assignment."
        ),
        limitations="Reviewed precision proxies do not quantify missed mappings without a labelled false-negative corpus.",
        alt_text="Rule evidence trace table linking semantic mappings to rules, evidence snippets, and review status.",
        min_width_px=1400,
        min_height_px=650,
    ),
    ManuscriptFigure(
        key="confidence_calibration",
        source="cogant/output/calculator/figures/confidence_calibration.png",
        destination="cogant_confidence_calibration.png",
        role="evidence-coverage-review-readiness",
        caption=(
            "Evidence-coverage and review-readiness panel generated from "
            "rule_evidence_trace.json."
        ),
        source_artifact="cogant/output/calculator/rule_evidence_trace.json",
        renderer="cogant.viz.inspection_dashboard native evidence coverage renderer",
        method_note=(
            "Mapping confidence tiers, rule contribution counts, conflict events, "
            "and reviewer-annotation coverage derived from rule evidence."
        ),
        reading_guide=(
            "Use the bars and reviewed-row card to prioritize human review before "
            "treating confidence tiers as calibrated."
        ),
        limitations=(
            "When reviewed rows are zero, this is review-priority evidence only; it "
            "does not estimate calibration, false-negative coverage, or semantic truth."
        ),
        alt_text=(
            "Evidence coverage panel with proposed mappings, rule contributions, "
            "confidence tiers, conflicts, and reviewed-row counts."
        ),
        min_width_px=1400,
        min_height_px=700,
        evidence_requirements=("mappings", "reviewed_mapping_rows", "reviewed_rule_rows"),
    ),
    ManuscriptFigure(
        key="inference_trace",
        source="cogant/output/calculator/figures/inference_trace.png",
        destination="cogant_inference_trace.png",
        role="runtime-belief-policy-free-energy-trace",
        caption=(
            "Deterministic runtime inference trace emitted from the package's "
            "built-in demonstration A/B/C/D matrices (not the fixture's exported "
            "values), with belief, action, preference, and free-energy panels."
        ),
        source_artifact="cogant/output/calculator/data/inference_trace.json",
        renderer="cogant.runtime.inference_demo and native visualization renderer",
        method_note=(
            "Deterministic trace generated from the package's built-in demonstration "
            "A/B/C/D matrices (`default_demo_matrices`), which share an exported model's "
            "shape but are not the fixture's exported values."
        ),
        reading_guide=(
            "Read belief, action, preference, and free-energy-like panels as a smoke "
            "demonstration of executable matrices."
        ),
        limitations="Demonstration trace only; it is not a behavioural-performance benchmark.",
        alt_text=(
            "Inference trace with belief trajectory, selected actions, preference "
            "satisfaction, and free-energy-like curve."
        ),
        min_width_px=1400,
        min_height_px=650,
    ),
    ManuscriptFigure(
        key="rule_family_ablation",
        source="cogant/output/calculator/figures/ablation_rule_family.png",
        destination="cogant_rule_family_ablation.png",
        role="measured-rule-family-and-fixpoint-ablation",
        caption=(
            "Measured ablation generated by `tools/regenerate_ablation.py` and "
            "resolved from the `ablation` block of `evaluation/METRICS.yaml`. Left: "
            "net mapping delta per rule family per fixture when that family's rules "
            "are withheld and the engine is re-run. Right: total mappings versus "
            "fixpoint iteration cap K. Net deltas, not per-MappingKind decomposition."
        ),
        source_artifact="cogant/evaluation/METRICS.yaml",
        renderer="cogant.viz.ablation_view.render_ablation_png",
        method_note=(
            "Deterministic matplotlib (Agg) render; fixtures and families in fixed "
            "sorted order with a fixed colour-blind-safe palette; values are the "
            "measured net per-family mapping deltas, not reconstructed estimates."
        ),
        reading_guide=(
            "Read the left panel to see which rule families contribute the most "
            "mappings (semantic dominates; structural is the unique HIDDEN_STATE "
            "source); read the right panel to confirm fixpoint convergence by K."
        ),
        limitations=(
            "Shows measured net per-family totals only; per-MappingKind "
            "decomposition and the zoo/01 appendix table are not measured here."
        ),
        alt_text=(
            "Two-panel ablation figure: grouped bars of net mapping delta per rule "
            "family per fixture, and fixpoint convergence lines versus iteration cap."
        ),
        min_width_px=1800,
        min_height_px=800,
    ),
    ManuscriptFigure(
        key="eval_graph_sizes",
        source="cogant/evaluation/figures/fig1_graph_sizes.png",
        destination="cogant_eval_graph_sizes.png",
        role="fixture-graph-size-comparison",
        caption=(
            "Fixture-level program-graph size comparison generated from "
            "cogant/evaluation/figures/metrics.json."
        ),
        source_artifact="cogant/evaluation/figures/metrics.json",
        renderer="generate_figures.figure_graph_sizes",
        method_note=(
            "Horizontal grouped bar chart of node and edge counts from the public "
            "API fixture run."
        ),
        reading_guide=(
            "Compare nodes and edges within each fixture before reading the graph "
            "composition table."
        ),
        limitations=(
            "Counts reflect the public API orchestration graph, not optional "
            "dashboard-only call-graph enrichments."
        ),
        alt_text=(
            "Horizontal grouped bars comparing node and edge counts across the six "
            "packaged fixtures."
        ),
        min_width_px=1400,
        min_height_px=750,
        evidence_requirements=("fixture_count", "total_nodes", "total_edges"),
    ),
    ManuscriptFigure(
        key="eval_node_kinds",
        source="cogant/evaluation/figures/fig2_node_kinds.png",
        destination="cogant_eval_node_kinds.png",
        role="fixture-node-kind-composition",
        caption=(
            "Fixture-level node-kind composition generated from "
            "cogant/evaluation/figures/metrics.json."
        ),
        source_artifact="cogant/evaluation/figures/metrics.json",
        renderer="generate_figures.figure_node_kinds",
        method_note=(
            "Horizontal stacked bar chart of MODULE, CLASS, METHOD, and FUNCTION "
            "counts by fixture."
        ),
        reading_guide=(
            "Use the stacked segments to see whether a fixture is class-heavy, "
            "method-heavy, or function-heavy."
        ),
        limitations=(
            "Only node kinds emitted by the public API graph path are shown; absent "
            "optional kinds are not inferred."
        ),
        alt_text=(
            "Stacked horizontal bars showing module, class, method, and function "
            "nodes for each packaged fixture."
        ),
        min_width_px=1400,
        min_height_px=750,
        evidence_requirements=("fixture_count", "node_kind_count", "total_nodes"),
    ),
    ManuscriptFigure(
        key="eval_state_space",
        source="cogant/evaluation/figures/fig3_state_space.png",
        destination="cogant_eval_state_space.png",
        role="fixture-state-space-output-comparison",
        caption=(
            "Fixture-level state-space output comparison generated from "
            "cogant/evaluation/figures/metrics.json."
        ),
        source_artifact="cogant/evaluation/figures/metrics.json",
        renderer="generate_figures.figure_state_space",
        method_note=(
            "Grouped horizontal bar chart of compiled hidden-state variables, "
            "observations, actions, and transitions."
        ),
        reading_guide=(
            "Compare observation/action balance across fixtures before interpreting "
            "matrix default-value diagnostics."
        ),
        limitations=(
            "The figure reports compiled counts only; it does not evaluate whether "
            "the extracted state space is behaviorally complete."
        ),
        alt_text=(
            "Grouped horizontal bars comparing state variables, observations, "
            "actions, and transitions across fixtures."
        ),
        min_width_px=1400,
        min_height_px=800,
        evidence_requirements=(
            "fixture_count",
            "total_state_variables",
            "total_observations",
            "total_actions",
        ),
    ),
    ManuscriptFigure(
        key="eval_pipeline_latency",
        source="cogant/evaluation/figures/fig4_pipeline_latency.png",
        destination="cogant_eval_pipeline_latency.png",
        role="fixture-api-pipeline-latency",
        caption=(
            "Fixture-level public API pipeline latency generated from "
            "cogant/evaluation/figures/metrics.json."
        ),
        source_artifact="cogant/evaluation/figures/metrics.json",
        renderer="generate_figures.figure_pipeline_latency",
        method_note=(
            "Directly labelled horizontal bar chart of end-to-end API run time, "
            "color-coded by fixture group."
        ),
        reading_guide=(
            "Use the labels as single-run audit timing, then compare them with the "
            "separate repeated benchmark table."
        ),
        limitations=(
            "Wall-clock timings vary by machine and load; this is provenance timing, "
            "not a statistically repeated benchmark."
        ),
        alt_text=(
            "Horizontal bars showing public API pipeline wall-clock seconds for "
            "each packaged fixture."
        ),
        min_width_px=1400,
        min_height_px=750,
        evidence_requirements=("fixture_count", "total_elapsed_s"),
    ),
)
