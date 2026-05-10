"""Wave-21 coverage tests for viz/flow.py, viz/matrix_view.py, and observability/logging.py.

Targets the specific uncovered branches reported by coverage:

* ``cogant.viz.flow``       : lines 152, 166-185, 296, 307, 335-341,
                              413-415, 425-439, 459-461, 481-483,
                              489-493, 502-507, 527-529
* ``cogant.viz.matrix_view``: lines 44-46, 67-69, 88-90, 114-116,
                              133-135, 150-152, 169-171, 186-188,
                              203-205, 249-251, 267-269, 299-301
* ``cogant.observability.logging``: structlog branches and ImportError fallback

Strict no-mocks policy: real :mod:`logging` objects, real :class:`ProgramGraph`
instances built via :class:`ProgramGraphBuilder`, real :mod:`matplotlib` and
:mod:`numpy` arrays. ImportError branches are exercised by reloading modules
with ``sys.modules[<dep>] = None`` so that Python's import machinery raises a
genuine :class:`ImportError` (not a mock).
"""

from __future__ import annotations

import importlib
import logging as stdlib_logging
import os
import sys

import pytest

# Headless matplotlib for CI portability
matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")

import numpy as np  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../py"))

from cogant.graph.builder import ProgramGraphBuilder  # noqa: E402
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind  # noqa: E402
from cogant.schemas.graph import ProgramGraph  # noqa: E402
from cogant.viz.flow import (  # noqa: E402
    ControlFlowGraph,
    FlowDiagrammer,
)
from cogant.viz.matrix_view import MatrixVisualizer  # noqa: E402

# ── Builders ─────────────────────────────────────────────────────────────────


def _graph_with_guards_and_calls() -> tuple[ProgramGraph, Node]:
    """Build a graph with both CALLS and GUARDS edges from one function.

    The resulting program graph contains a ``main`` function with:
      * one :data:`EdgeKind.CALLS` edge to ``helper`` (covers call-block path)
      * one :data:`EdgeKind.GUARDS` edge to ``policy`` (covers guard-block path)
      * one CALLS edge to a target that is intentionally absent from
        ``graph.nodes`` to exercise the ``if callee is None: continue`` branch
        in :meth:`FlowDiagrammer.generate_cfg`.
    """
    b = ProgramGraphBuilder(repo_uri="test://wave21-flow-guards")
    main_fn = b.add_node(kind=NodeKind.FUNCTION, name="main", qualified_name="m.main")
    helper = b.add_node(kind=NodeKind.FUNCTION, name="helper", qualified_name="m.helper")
    policy = b.add_node(kind=NodeKind.POLICY, name="auth", qualified_name="m.auth")

    b.add_edge(source_id=main_fn.id, target_id=helper.id, kind=EdgeKind.CALLS)
    b.add_edge(source_id=main_fn.id, target_id=policy.id, kind=EdgeKind.GUARDS)
    graph = b.finalize()

    # Inject a "dangling" CALLS edge to a non-existent node id to hit the
    # ``callee is None`` continue branch (line 152). We bypass the builder
    # because it would refuse a non-existent target.
    dangling = Edge(
        id="dangling-edge-1",
        source_id=main_fn.id,
        target_id="missing-target-id-not-in-graph",
        kind=EdgeKind.CALLS,
    )
    graph.edges[dangling.id] = dangling
    return graph, main_fn


def _graph_with_imports_chain() -> ProgramGraph:
    """Build a graph with two MODULE nodes chained by IMPORTS."""
    b = ProgramGraphBuilder(repo_uri="test://wave21-flow-imports")
    mod_a = b.add_node(kind=NodeKind.MODULE, name="a", qualified_name="pkg.a")
    mod_b = b.add_node(kind=NodeKind.MODULE, name="b", qualified_name="pkg.b")
    file_c = b.add_node(kind=NodeKind.FILE, name="c.py", qualified_name="pkg.c")
    b.add_edge(source_id=mod_a.id, target_id=mod_b.id, kind=EdgeKind.IMPORTS)
    b.add_edge(source_id=mod_b.id, target_id=file_c.id, kind=EdgeKind.IMPORTS)
    return b.finalize()


# ── viz/flow.py — generate_cfg GUARDS branch and dangling-callee guard ───────


@pytest.mark.unit
def test_generate_cfg_with_guards_edge_creates_guard_and_skip_blocks() -> None:
    """generate_cfg routes :data:`EdgeKind.GUARDS` through guard+skip blocks."""
    graph, main_fn = _graph_with_guards_and_calls()
    fd = FlowDiagrammer()
    cfg = fd.generate_cfg(main_fn, graph=graph)

    # Guard branch creates ``_guard_<callee>`` and ``_skip_<callee>`` blocks
    block_kinds = {info.get("kind") for info in cfg.nodes.values()}
    assert "condition_block" in block_kinds, "GUARDS edge must create a condition_block"
    # Two of the three edges from main are valid (CALLS+GUARDS); dangling skipped
    # Guards yield two outgoing edges (true + false branch) marked conditional
    conditional_edges = [e for e in cfg.edges if e[2] == "conditional"]
    assert len(conditional_edges) >= 2, "Guard must emit two conditional edges"


@pytest.mark.unit
def test_generate_cfg_skips_dangling_callee_edge() -> None:
    """generate_cfg ignores edges whose target node is missing from the graph."""
    graph, main_fn = _graph_with_guards_and_calls()
    fd = FlowDiagrammer()
    cfg = fd.generate_cfg(main_fn, graph=graph)

    # No call_block should reference ``missing-target-id-not-in-graph``
    for info in cfg.nodes.values():
        assert info.get("callee_id") != "missing-target-id-not-in-graph"


# ── viz/flow.py — generate_call_graph and generate_dependency_graph ──────────


@pytest.mark.unit
def test_generate_call_graph_uses_metadata_call_count_and_recursive() -> None:
    """generate_call_graph reads ``call_count`` and ``is_recursive`` metadata."""
    b = ProgramGraphBuilder(repo_uri="test://wave21-callgraph-meta")
    fn_a = b.add_node(kind=NodeKind.FUNCTION, name="a", qualified_name="m.a")
    fn_b = b.add_node(kind=NodeKind.METHOD, name="b", qualified_name="m.C.b")
    b.add_edge(
        source_id=fn_a.id,
        target_id=fn_b.id,
        kind=EdgeKind.CALLS,
        metadata={"call_count": 7, "is_recursive": True},
    )
    graph = b.finalize()

    cg = FlowDiagrammer().generate_call_graph(graph)
    assert len(cg.edges) == 1
    _, _, edge_info = cg.edges[0]
    assert edge_info["call_count"] == 7
    assert edge_info["is_recursive"] is True


@pytest.mark.unit
def test_generate_dependency_graph_collects_imports_edges() -> None:
    """generate_dependency_graph emits one edge per IMPORTS relation (line 296)."""
    graph = _graph_with_imports_chain()
    dg = FlowDiagrammer().generate_dependency_graph(graph)

    assert len(dg.edges) == 2
    # The two MODULEs and one FILE are nodes in the dep graph
    assert len(dg.nodes) == 3
    # ``a`` has no incoming imports → it is a root
    root_names = {dg.nodes[r]["name"] for r in dg.root_modules}
    assert "a" in root_names


@pytest.mark.unit
def test_generate_dependency_graph_root_calculation_via_incoming_count() -> None:
    """Root modules are exactly those with zero incoming IMPORTS edges (line 307)."""
    graph = _graph_with_imports_chain()
    dg = FlowDiagrammer().generate_dependency_graph(graph)

    # Module ``b`` is imported by ``a`` and itself imports ``c.py``
    # so ``b`` should NOT be a root
    b_id = next(nid for nid, info in dg.nodes.items() if info["name"] == "b")
    assert b_id not in dg.root_modules


# ── viz/flow.py — Mermaid flowchart conditional & unconditional rendering ────


@pytest.mark.unit
def test_to_mermaid_flowchart_emits_conditional_and_unconditional_edges() -> None:
    """to_mermaid_flowchart emits ``-->|conditional|`` and plain ``-->`` (335-341)."""
    cfg = ControlFlowGraph(
        function_node=Node(
            id="fn-x", kind=NodeKind.FUNCTION, name="fnx", qualified_name="fnx"
        ),
    )
    cfg.nodes["a-1"] = {"name": "alpha", "kind": "basic_block"}
    cfg.nodes["b.2"] = {"name": "beta", "kind": "basic_block"}
    cfg.nodes["c-3"] = {"name": "gamma", "kind": "basic_block"}
    cfg.edges = [
        ("a-1", "b.2", "conditional"),
        ("b.2", "c-3", "unconditional"),
    ]
    cfg.entry_node_id = "a-1"
    cfg.exit_node_ids = ["c-3"]

    mermaid = FlowDiagrammer().to_mermaid_flowchart(cfg)
    # IDs sanitized (- and . → _)
    assert "a_1" in mermaid and "b_2" in mermaid and "c_3" in mermaid
    assert "-->|conditional|" in mermaid
    # An unconditional edge is rendered without the conditional pipe label
    assert "b_2 --> c_3" in mermaid


# ── viz/flow.py — to_png with CallGraph and DependencyGraph ──────────────────


@pytest.mark.unit
def test_to_png_with_call_graph_renders_file(tmp_path) -> None:
    """to_png handles CallGraph branch (lines 425-432)."""
    graph, _ = _graph_with_guards_and_calls()
    fd = FlowDiagrammer()
    cg = fd.generate_call_graph(graph)
    out = tmp_path / "callgraph.png"
    result = fd.to_png(cg, str(out), dpi=80)
    assert result == str(out)
    assert out.exists() and out.stat().st_size > 0


@pytest.mark.unit
def test_to_png_with_dependency_graph_renders_file(tmp_path) -> None:
    """to_png handles DependencyGraph branch (lines 434-439)."""
    graph = _graph_with_imports_chain()
    fd = FlowDiagrammer()
    dg = fd.generate_dependency_graph(graph)
    out = tmp_path / "depgraph.png"
    result = fd.to_png(dg, str(out), dpi=80)
    assert result == str(out)
    assert out.exists()


# ── viz/flow.py — to_pdf with all three graph types ──────────────────────────


@pytest.mark.unit
def test_to_pdf_with_control_flow_graph_renders_file(tmp_path) -> None:
    """to_pdf handles ControlFlowGraph branch (lines 488-493)."""
    graph, main_fn = _graph_with_guards_and_calls()
    fd = FlowDiagrammer()
    cfg = fd.generate_cfg(main_fn, graph=graph)
    out = tmp_path / "cfg.pdf"
    result = fd.to_pdf(cfg, str(out))
    assert result == str(out)
    assert out.exists() and out.stat().st_size > 0


@pytest.mark.unit
def test_to_pdf_with_dependency_graph_renders_file(tmp_path) -> None:
    """to_pdf handles DependencyGraph branch (lines 502-507)."""
    graph = _graph_with_imports_chain()
    fd = FlowDiagrammer()
    dg = fd.generate_dependency_graph(graph)
    out = tmp_path / "depgraph.pdf"
    result = fd.to_pdf(dg, str(out))
    assert result == str(out)
    assert out.exists()


# ── viz/flow.py — render exception branches ──────────────────────────────────


@pytest.mark.unit
def test_to_png_returns_empty_on_render_exception(tmp_path) -> None:
    """to_png catches the exception path (lines 459-461) on bad output dir."""
    graph, main_fn = _graph_with_guards_and_calls()
    fd = FlowDiagrammer()
    cfg = fd.generate_cfg(main_fn, graph=graph)
    bad_path = "/this/dir/does/not/exist/wave21.png"
    result = fd.to_png(cfg, bad_path)
    assert result == ""


@pytest.mark.unit
def test_to_pdf_returns_empty_on_render_exception(tmp_path) -> None:
    """to_pdf catches the exception path (lines 527-529) on bad output dir."""
    graph, main_fn = _graph_with_guards_and_calls()
    fd = FlowDiagrammer()
    cg = fd.generate_call_graph(graph)
    bad_path = "/this/dir/does/not/exist/wave21.pdf"
    result = fd.to_pdf(cg, bad_path)
    assert result == ""


# ── viz/flow.py — ImportError fallback for matplotlib/networkx ───────────────


@pytest.mark.unit
def test_to_png_returns_empty_when_matplotlib_unavailable(tmp_path, monkeypatch) -> None:
    """to_png returns ``""`` when matplotlib import fails (lines 413-415).

    The function performs its imports inline, so we make ``matplotlib.pyplot``
    raise :class:`ImportError` at call-time by setting the entry to ``None``
    in :data:`sys.modules` (Python's import machinery turns this into an
    ImportError on subsequent imports).
    """
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", None)
    node = Node(id="fn-imp", kind=NodeKind.FUNCTION, name="fn", qualified_name="fn")
    cfg = ControlFlowGraph(function_node=node)
    result = FlowDiagrammer().to_png(cfg, str(tmp_path / "x.png"))
    assert result == ""


@pytest.mark.unit
def test_to_pdf_returns_empty_when_matplotlib_unavailable(tmp_path, monkeypatch) -> None:
    """to_pdf returns ``""`` when matplotlib import fails (lines 481-483)."""
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", None)
    node = Node(id="fn-imp2", kind=NodeKind.FUNCTION, name="fn", qualified_name="fn")
    cfg = ControlFlowGraph(function_node=node)
    result = FlowDiagrammer().to_pdf(cfg, str(tmp_path / "x.pdf"))
    assert result == ""


# ── viz/matrix_view.py — inner exception branches ────────────────────────────


@pytest.mark.unit
def test_plot_A_matrix_returns_none_on_invalid_input() -> None:
    """plot_A_matrix returns None when the array cast fails (lines 67-69)."""
    viz = MatrixVisualizer()
    # Object array with non-numeric, non-broadcastable contents triggers the
    # inner exception (np.asarray with dtype=float on heterogeneous nested seq)
    bad = [[object(), object()], [object()]]
    fig = viz.plot_A_matrix(bad)
    assert fig is None


@pytest.mark.unit
def test_plot_B_matrix_returns_none_on_invalid_input() -> None:
    """plot_B_matrix returns None on bad input (lines 114-116)."""
    viz = MatrixVisualizer()
    bad = [[object()], [object(), object()]]
    fig = viz.plot_B_matrix(bad)
    assert fig is None


@pytest.mark.unit
def test_plot_C_vector_returns_none_on_invalid_input() -> None:
    """plot_C_vector returns None on bad input (lines 150-152)."""
    viz = MatrixVisualizer()
    bad = [object(), object()]
    fig = viz.plot_C_vector(bad)
    assert fig is None


@pytest.mark.unit
def test_plot_D_vector_returns_none_on_invalid_input() -> None:
    """plot_D_vector returns None on bad input (lines 186-188)."""
    viz = MatrixVisualizer()
    bad = [object(), object()]
    fig = viz.plot_D_vector(bad)
    assert fig is None


@pytest.mark.unit
def test_plot_all_matrices_returns_none_on_invalid_input() -> None:
    """plot_all_matrices returns None on bad input (lines 249-251)."""
    viz = MatrixVisualizer()
    matrices = {"A": [[object()]], "B": [[object()]], "C": [object()], "D": [object()]}
    fig = viz.plot_all_matrices(matrices)
    assert fig is None


# ── viz/matrix_view.py — ImportError fallbacks for matplotlib/numpy ──────────


@pytest.mark.unit
def test_matrix_methods_return_none_when_matplotlib_unavailable(monkeypatch) -> None:
    """Every plot_* method returns None when matplotlib import fails.

    Covers lines 44-46, 88-90, 133-135, 169-171, 203-205. The plot methods
    perform their imports inline, so we make ``matplotlib.pyplot`` raise
    :class:`ImportError` at call-time by setting the entry to ``None`` in
    :data:`sys.modules`.
    """
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", None)
    viz = MatrixVisualizer()
    assert viz.plot_A_matrix(np.eye(2)) is None
    assert viz.plot_B_matrix(np.eye(2)) is None
    assert viz.plot_C_vector(np.array([0.5, 0.5])) is None
    assert viz.plot_D_vector(np.array([0.5, 0.5])) is None
    assert viz.plot_all_matrices({"A": np.eye(2)}) is None


@pytest.mark.unit
def test_matrix_to_png_returns_empty_when_matplotlib_unavailable(
    tmp_path, monkeypatch
) -> None:
    """to_png returns '' when matplotlib import fails (lines 267-269)."""
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", None)
    viz = MatrixVisualizer()
    # ``fig`` argument is ignored when matplotlib isn't available
    result = viz.to_png(object(), str(tmp_path / "x.png"))
    assert result == ""


@pytest.mark.unit
def test_matrix_to_pdf_returns_empty_when_matplotlib_unavailable(
    tmp_path, monkeypatch
) -> None:
    """to_pdf returns '' when matplotlib import fails (lines 299-301)."""
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", None)
    viz = MatrixVisualizer()
    result = viz.to_pdf(object(), str(tmp_path / "x.pdf"))
    assert result == ""


# ── observability/logging.py — structlog branches and stdlib fallback ────────


@pytest.mark.unit
def test_setup_logging_console_format_when_structlog_available() -> None:
    """setup_logging(format='console') configures structlog ConsoleRenderer."""
    structlog = pytest.importorskip("structlog")
    import cogant.observability.logging as log_mod

    if not log_mod._STRUCTLOG_AVAILABLE:
        importlib.reload(log_mod)
    assert log_mod._STRUCTLOG_AVAILABLE is True
    log_mod.setup_logging(level="DEBUG", format="console")

    # get_logger should return a structlog BoundLogger (or BoundLoggerLazyProxy)
    logger = log_mod.get_logger("wave21.console")
    # Real structlog logger exposes .info / .bind
    assert callable(getattr(logger, "info", None))
    assert callable(getattr(logger, "bind", None))
    # structlog symbol still resolvable
    assert hasattr(structlog, "get_logger")


@pytest.mark.unit
def test_setup_logging_json_format_when_structlog_available() -> None:
    """setup_logging(format='json') configures structlog JSONRenderer."""
    pytest.importorskip("structlog")
    import cogant.observability.logging as log_mod

    if not log_mod._STRUCTLOG_AVAILABLE:
        importlib.reload(log_mod)
    log_mod.setup_logging(level="INFO", format="json")
    # Default (json) is used when format is not 'console'
    log_mod.setup_logging(level="INFO", format="not-console")
    # No exception → success
    assert stdlib_logging.getLogger().level == stdlib_logging.INFO


@pytest.mark.unit
def test_get_logger_returns_structlog_when_available() -> None:
    """get_logger uses structlog.get_logger when available (line 66)."""
    pytest.importorskip("structlog")
    import cogant.observability.logging as log_mod

    if not log_mod._STRUCTLOG_AVAILABLE:
        importlib.reload(log_mod)
    logger = log_mod.get_logger("wave21.named")
    # structlog loggers are not stdlib Logger instances
    assert not isinstance(logger, stdlib_logging.Logger)
    # but they do expose .info
    assert callable(getattr(logger, "info", None))


@pytest.mark.unit
def test_setup_logging_falls_back_to_stdlib_when_structlog_missing(monkeypatch) -> None:
    """ImportError fallback: stdlib logging is used when structlog is hidden."""
    real_structlog = sys.modules.pop("structlog", None)
    monkeypatch.setitem(sys.modules, "structlog", None)
    try:
        if "cogant.observability.logging" in sys.modules:
            del sys.modules["cogant.observability.logging"]
        fallback_mod = importlib.import_module("cogant.observability.logging")
        assert fallback_mod._STRUCTLOG_AVAILABLE is False
        fallback_mod.setup_logging(level="WARNING", format="json")
        logger = fallback_mod.get_logger("wave21.fallback")
        assert isinstance(logger, stdlib_logging.Logger)
        assert logger.name == "wave21.fallback"
    finally:
        if "cogant.observability.logging" in sys.modules:
            del sys.modules["cogant.observability.logging"]
        if real_structlog is not None:
            sys.modules["structlog"] = real_structlog
        importlib.import_module("cogant.observability.logging")


@pytest.mark.unit
def test_setup_logging_default_level_for_unknown_string() -> None:
    """Unknown level strings collapse to ``logging.INFO`` via getattr default."""
    import cogant.observability.logging as log_mod

    log_mod.setup_logging(level="NOT_A_LEVEL_XYZ", format="json")
    assert stdlib_logging.getLogger().level == stdlib_logging.INFO


@pytest.mark.unit
@pytest.mark.parametrize(
    "level",
    ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
)
def test_setup_logging_each_standard_level_sets_root(level: str) -> None:
    """Each canonical level name maps to the stdlib numeric level."""
    import cogant.observability.logging as log_mod

    log_mod.setup_logging(level=level, format="json")
    assert stdlib_logging.getLogger().level == getattr(stdlib_logging, level)


@pytest.mark.unit
def test_logger_emits_records_through_real_logging_handler() -> None:
    """Real log records flow through a real handler — round-trip smoke check.

    Avoids :mod:`pytest`'s ``caplog`` because :func:`setup_logging` calls
    :func:`logging.basicConfig` with ``force=True``, which removes the
    capture handler. Instead, we attach our own real :class:`logging.Handler`
    AFTER setup_logging and assert it receives the record.
    """
    import cogant.observability.logging as log_mod

    log_mod.setup_logging(level="DEBUG", format="json")

    received: list[stdlib_logging.LogRecord] = []

    class _CaptureHandler(stdlib_logging.Handler):
        def emit(self, record: stdlib_logging.LogRecord) -> None:
            received.append(record)

    handler = _CaptureHandler(level=stdlib_logging.DEBUG)
    stdlib_logger = stdlib_logging.getLogger("wave21.emit")
    stdlib_logger.setLevel(stdlib_logging.DEBUG)
    stdlib_logger.addHandler(handler)
    # Reset any global disable level set by other tests in the suite.
    prev_disable = stdlib_logging.root.manager.disable
    stdlib_logging.disable(stdlib_logging.NOTSET)
    try:
        stdlib_logger.warning("wave21 hello")
    finally:
        stdlib_logging.disable(prev_disable)
        stdlib_logger.removeHandler(handler)

    assert any("wave21 hello" in rec.getMessage() for rec in received)
