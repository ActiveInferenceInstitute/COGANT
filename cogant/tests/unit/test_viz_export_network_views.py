"""Targeted unit tests for cogant.viz.export_view and cogant.viz.network_view.

Targets every branch in ExportView and NetworkView so coverage clears the
90% gate. Uses real objects only — no mocks, no MagicMock.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import logging
from pathlib import Path

import pytest

from cogant.viz.export_view import ExportView
from cogant.viz.network_view import NetworkView

from ._viz_assert import assert_figure_nondegenerate

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ev() -> ExportView:
    """Provide a fresh ExportView instance."""
    return ExportView()


@pytest.fixture
def nv() -> NetworkView:
    """Provide a fresh NetworkView instance."""
    return NetworkView()


@pytest.fixture(autouse=True)
def _close_plots():
    """Close all matplotlib figures after each test to keep memory bounded."""
    yield
    pytest.importorskip("matplotlib")
    import matplotlib.pyplot as plt

    plt.close("all")


# ===========================================================================
# ExportView — initialization
# ===========================================================================


@pytest.mark.unit
def test_export_view_init_returns_instance() -> None:
    """ExportView() constructs without arguments and yields a usable instance."""
    view = ExportView()
    assert isinstance(view, ExportView)


# ===========================================================================
# ExportView.plot_export_formats
# ===========================================================================


@pytest.mark.unit
def test_plot_export_formats_with_size_key(ev: ExportView) -> None:
    """Result entries with 'size' key feed directly into the bar chart."""
    pytest.importorskip("matplotlib")
    results = {
        "json": {"size": 2048},
        "markdown": {"size": 4096},
        "yaml": {"size": 1024},
    }
    fig = ev.plot_export_formats(results)
    assert_figure_nondegenerate(fig)
    ax = fig.axes[0]
    assert ax.get_ylabel() == "Size (MB)"
    assert "Export Formats" in ax.get_title()


@pytest.mark.unit
def test_plot_export_formats_with_file_path_real_file(ev: ExportView, tmp_path: Path) -> None:
    """A real file referenced via 'file_path' has its size read via Path.stat."""
    pytest.importorskip("matplotlib")
    real = tmp_path / "fixture.bin"
    real.write_bytes(b"x" * 2048)
    results = {"png": {"file_path": str(real)}}
    fig = ev.plot_export_formats(results)
    assert_figure_nondegenerate(fig)


@pytest.mark.unit
def test_plot_export_formats_with_file_path_missing(ev: ExportView, tmp_path: Path) -> None:
    """Missing 'file_path' triggers the inner Exception → size 0 path."""
    pytest.importorskip("matplotlib")
    results = {"pdf": {"file_path": str(tmp_path / "does_not_exist.pdf")}}
    fig = ev.plot_export_formats(results)
    # Missing-file branch: bar is rendered with size=0, which is still a real
    # patch (a zero-height bar), so the figure is non-degenerate as long as
    # the axes contain *any* patch. Use the standard helper.
    assert_figure_nondegenerate(fig)


@pytest.mark.unit
def test_plot_export_formats_dict_without_size_or_path(ev: ExportView) -> None:
    """Dict result lacking both 'size' and 'file_path' falls through to size=0."""
    pytest.importorskip("matplotlib")
    results = {"html": {"misc": "no-size-here"}}
    fig = ev.plot_export_formats(results)
    assert_figure_nondegenerate(fig)


@pytest.mark.unit
def test_plot_export_formats_non_dict_value(ev: ExportView) -> None:
    """A non-dict value uses the size=0 default branch."""
    pytest.importorskip("matplotlib")
    results = {"raw": "not-a-dict", "other": 42}
    fig = ev.plot_export_formats(results)
    assert_figure_nondegenerate(fig)


@pytest.mark.unit
def test_plot_export_formats_empty_returns_none(ev: ExportView) -> None:
    """Empty export_results dict is logged and returns None."""
    assert ev.plot_export_formats({}) is None


@pytest.mark.unit
def test_plot_export_formats_logs_error_on_invalid_input(
    ev: ExportView, caplog: pytest.LogCaptureFixture
) -> None:
    """Pathological input is caught and logged via the outer except."""
    pytest.importorskip("matplotlib")

    # A non-dict, non-empty truthy object triggers the outer exception path
    # because .items() is missing. ExportView must log an error and return None.
    class Truthy:
        def __bool__(self) -> bool:  # truthy → bypass the "if not" guard
            return True

        def items(self):  # raise to hit the outer except
            raise RuntimeError("boom")

    with caplog.at_level(logging.ERROR, logger="cogant.viz.export_view"):
        result = ev.plot_export_formats(Truthy())  # type: ignore[arg-type]
    assert result is None
    assert any("Error plotting export formats" in rec.message for rec in caplog.records)


# ===========================================================================
# ExportView.to_mermaid_export_pipeline
# ===========================================================================


@pytest.mark.unit
def test_to_mermaid_export_pipeline_contains_expected_nodes(ev: ExportView) -> None:
    """Mermaid pipeline diagram contains all stage names and starts with 'graph LR'."""
    output = ev.to_mermaid_export_pipeline()
    assert output.startswith("graph LR")
    for fragment in (
        "Program",
        "GNN",
        "State",
        "Semantic",
        "JSON",
        "Markdown",
        "PNG",
        "PDF",
        "HTML",
        "Export",
    ):
        assert fragment in output


# ===========================================================================
# ExportView.plot_bundle_composition
# ===========================================================================


@pytest.mark.unit
def test_plot_bundle_composition_full_bundle(ev: ExportView) -> None:
    """A full bundle exercises matrices, metadata, roles, mappings, and other branches."""
    pytest.importorskip("matplotlib")
    bundle = {
        "A": [[1, 0], [0, 1]],
        "B": [[1]],
        "C": [[1, 0]],
        "D": [[0.5, 0.5]],
        "metadata": {"name": "test", "version": "1.0"},
        "roles": ["state", "obs"],
        "mappings": {"sv1": "obs1"},
        "extra_field": "extra-value",
    }
    fig = ev.plot_bundle_composition(bundle)
    assert fig is not None
    assert "GNN Bundle Composition" in fig.axes[0].get_title()


@pytest.mark.unit
def test_plot_bundle_composition_string_matrix(ev: ExportView) -> None:
    """String-encoded matrices are sized by string length."""
    pytest.importorskip("matplotlib")
    bundle = {"A": "0,1,1,0", "B": "1"}
    fig = ev.plot_bundle_composition(bundle)
    assert fig is not None


@pytest.mark.unit
def test_plot_bundle_composition_only_other(ev: ExportView) -> None:
    """A bundle that only has 'other' fields still produces a pie chart."""
    pytest.importorskip("matplotlib")
    fig = ev.plot_bundle_composition({"foo": "bar", "baz": [1, 2, 3]})
    assert fig is not None


@pytest.mark.unit
def test_plot_bundle_composition_empty_returns_none(ev: ExportView) -> None:
    """Empty bundle dict is logged and returns None."""
    assert ev.plot_bundle_composition({}) is None


@pytest.mark.unit
def test_plot_bundle_composition_no_measurable_components(ev: ExportView) -> None:
    """A bundle whose measurable components all stringify to empty returns None."""
    pytest.importorskip("matplotlib")
    # Empty string fields produce zero-length sizes for every category
    bundle = {"A": "", "B": "", "extra": ""}
    result = ev.plot_bundle_composition(bundle)
    # 'A' yields matrix_size=0, 'extra' yields other_size=0 (len('')==0). All zero → None.
    assert result is None


@pytest.mark.unit
def test_plot_bundle_composition_unserializable_matrix(ev: ExportView) -> None:
    """Non-JSON-serializable matrix entries hit the inner except → 1000 byte estimate."""
    pytest.importorskip("matplotlib")

    class NotJsonable:
        """An object that json.dumps cannot serialize."""

    bundle = {"A": NotJsonable(), "metadata": {"v": 1}}
    fig = ev.plot_bundle_composition(bundle)
    assert fig is not None  # estimate kicks in, plot still renders


@pytest.mark.unit
def test_plot_bundle_composition_unserializable_metadata(ev: ExportView) -> None:
    """Non-JSON-serializable metadata triggers the metadata except → 500 byte default."""
    pytest.importorskip("matplotlib")

    class NotJsonable:
        pass

    bundle = {"metadata": NotJsonable()}
    fig = ev.plot_bundle_composition(bundle)
    assert fig is not None


@pytest.mark.unit
def test_plot_bundle_composition_unserializable_roles(ev: ExportView) -> None:
    """Non-JSON-serializable roles trigger the roles except → 500 byte default."""
    pytest.importorskip("matplotlib")

    class NotJsonable:
        pass

    bundle = {"roles": NotJsonable()}
    fig = ev.plot_bundle_composition(bundle)
    assert fig is not None


@pytest.mark.unit
def test_plot_bundle_composition_unserializable_mappings(ev: ExportView) -> None:
    """Non-JSON-serializable mappings trigger the mappings except → 500 byte default."""
    pytest.importorskip("matplotlib")

    class NotJsonable:
        pass

    bundle = {"mappings": NotJsonable()}
    fig = ev.plot_bundle_composition(bundle)
    assert fig is not None


@pytest.mark.unit
def test_plot_bundle_composition_logs_error_on_bad_input(
    ev: ExportView, caplog: pytest.LogCaptureFixture
) -> None:
    """A truthy non-dict object lacking .items() exercises the outer except."""
    pytest.importorskip("matplotlib")

    class Truthy:
        def __bool__(self) -> bool:
            return True

        def __contains__(self, key) -> bool:
            raise RuntimeError("boom")

    with caplog.at_level(logging.ERROR, logger="cogant.viz.export_view"):
        result = ev.plot_bundle_composition(Truthy())  # type: ignore[arg-type]
    assert result is None
    assert any("Error plotting bundle composition" in rec.message for rec in caplog.records)


# ===========================================================================
# ExportView.to_png / to_pdf
# ===========================================================================


@pytest.mark.unit
def test_export_to_png_writes_file(ev: ExportView, tmp_path: Path) -> None:
    """to_png saves a real PNG file and returns the destination path."""
    pytest.importorskip("matplotlib")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    out = tmp_path / "out.png"
    result = ev.to_png(fig, str(out), dpi=80)
    assert result == str(out)
    assert out.exists() and out.stat().st_size > 0


@pytest.mark.unit
def test_export_to_png_returns_empty_when_fig_none(ev: ExportView, tmp_path: Path) -> None:
    """A None figure triggers the guard and returns an empty string."""
    pytest.importorskip("matplotlib")
    assert ev.to_png(None, str(tmp_path / "nope.png")) == ""


@pytest.mark.unit
def test_export_to_png_returns_empty_on_save_error(ev: ExportView, tmp_path: Path) -> None:
    """A bad output path triggers the outer except and returns an empty string."""
    pytest.importorskip("matplotlib")
    import matplotlib.pyplot as plt

    fig, _ = plt.subplots()
    bogus = tmp_path / "missing_dir" / "deeper" / "out.png"
    # Parent does not exist → matplotlib raises during savefig
    result = ev.to_png(fig, str(bogus))
    assert result == ""


@pytest.mark.unit
def test_export_to_pdf_writes_file(ev: ExportView, tmp_path: Path) -> None:
    """to_pdf saves a real PDF file and returns the destination path."""
    pytest.importorskip("matplotlib")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.plot([0, 1, 2], [3, 2, 1])
    out = tmp_path / "out.pdf"
    result = ev.to_pdf(fig, str(out))
    assert result == str(out)
    assert out.exists() and out.stat().st_size > 0


@pytest.mark.unit
def test_export_to_pdf_returns_empty_when_fig_none(ev: ExportView, tmp_path: Path) -> None:
    """A None figure triggers the PDF guard and returns an empty string."""
    pytest.importorskip("matplotlib")
    assert ev.to_pdf(None, str(tmp_path / "nope.pdf")) == ""


@pytest.mark.unit
def test_export_to_pdf_returns_empty_on_save_error(ev: ExportView, tmp_path: Path) -> None:
    """A bad output path triggers the outer except and returns an empty string."""
    pytest.importorskip("matplotlib")
    import matplotlib.pyplot as plt

    fig, _ = plt.subplots()
    bogus = tmp_path / "missing_dir" / "out.pdf"
    result = ev.to_pdf(fig, str(bogus))
    assert result == ""


# ===========================================================================
# NetworkView — initialization
# ===========================================================================


@pytest.mark.unit
def test_network_view_init_returns_instance() -> None:
    """NetworkView() constructs without arguments and yields a usable instance."""
    view = NetworkView()
    assert isinstance(view, NetworkView)


# ===========================================================================
# NetworkView.plot_degree_distribution
# ===========================================================================


@pytest.mark.unit
def test_plot_degree_distribution_with_data(nv: NetworkView) -> None:
    """A populated degree list produces a log-log distribution figure."""
    pytest.importorskip("matplotlib")
    fig = nv.plot_degree_distribution({"degrees": [1, 1, 2, 2, 3, 4, 5, 8, 13]})
    assert fig is not None
    ax = fig.axes[0]
    assert "Degree Distribution" in ax.get_title()
    assert ax.get_xscale() == "log"
    assert ax.get_yscale() == "log"


@pytest.mark.unit
def test_plot_degree_distribution_missing_key(nv: NetworkView) -> None:
    """A metrics dict without 'degrees' returns None gracefully."""
    assert nv.plot_degree_distribution({}) is None


@pytest.mark.unit
def test_plot_degree_distribution_logs_error(
    nv: NetworkView, caplog: pytest.LogCaptureFixture
) -> None:
    """Pathological metrics input is caught by the outer except and logged."""
    pytest.importorskip("matplotlib")

    class BadMetrics:
        def get(self, key, default=None):
            raise RuntimeError("boom")

    with caplog.at_level(logging.ERROR, logger="cogant.viz.network_view"):
        result = nv.plot_degree_distribution(BadMetrics())  # type: ignore[arg-type]
    assert result is None
    assert any("Error plotting degree distribution" in r.message for r in caplog.records)


# ===========================================================================
# NetworkView.plot_centrality_ranking
# ===========================================================================


@pytest.mark.unit
def test_plot_centrality_ranking_with_data(nv: NetworkView) -> None:
    """Centrality rank plot returns a horizontal bar chart for top_n nodes."""
    pytest.importorskip("matplotlib")
    centrality = {f"node_{i}": float(i) / 10 for i in range(20)}
    fig = nv.plot_centrality_ranking(centrality, top_n=5)
    assert fig is not None
    ax = fig.axes[0]
    assert "Top 5" in ax.get_title()


@pytest.mark.unit
def test_plot_centrality_ranking_default_top_n(nv: NetworkView) -> None:
    """Default top_n=15 truncates correctly for larger inputs."""
    pytest.importorskip("matplotlib")
    centrality = {f"n{i}": 1.0 / (i + 1) for i in range(30)}
    fig = nv.plot_centrality_ranking(centrality)
    assert fig is not None


@pytest.mark.unit
def test_plot_centrality_ranking_empty_returns_none(nv: NetworkView) -> None:
    """Empty centrality dict logs and returns None."""
    assert nv.plot_centrality_ranking({}) is None


@pytest.mark.unit
def test_plot_centrality_ranking_logs_error(
    nv: NetworkView, caplog: pytest.LogCaptureFixture
) -> None:
    """Bad centrality input is caught by the outer except and logged."""
    pytest.importorskip("matplotlib")

    class BadDict:
        def __bool__(self) -> bool:
            return True

        def items(self):
            raise RuntimeError("boom")

    with caplog.at_level(logging.ERROR, logger="cogant.viz.network_view"):
        result = nv.plot_centrality_ranking(BadDict())  # type: ignore[arg-type]
    assert result is None
    assert any("Error plotting centrality ranking" in r.message for r in caplog.records)


# ===========================================================================
# NetworkView.plot_community_graph
# ===========================================================================


@pytest.mark.unit
def test_plot_community_graph_with_real_networkx(nv: NetworkView) -> None:
    """A real NetworkX graph + communities renders a node-link diagram with legend."""
    pytest.importorskip("matplotlib")
    nx = pytest.importorskip("networkx")
    g = nx.Graph()
    g.add_edges_from([("a", "b"), ("b", "c"), ("d", "e"), ("e", "f"), ("g", "h")])
    communities = [frozenset({"a", "b", "c"}), frozenset({"d", "e", "f"}), frozenset({"g", "h"})]
    fig = nv.plot_community_graph(g, communities)
    assert fig is not None
    ax = fig.axes[0]
    assert "Community Detection" in ax.get_title()


@pytest.mark.unit
def test_plot_community_graph_with_unassigned_nodes(nv: NetworkView) -> None:
    """Nodes not appearing in any community get the default lightgray color."""
    pytest.importorskip("matplotlib")
    nx = pytest.importorskip("networkx")
    g = nx.Graph()
    g.add_edges_from([("a", "b"), ("c", "d"), ("orphan", "lonely")])
    # Only assign two of the four nodes to communities
    communities = [frozenset({"a", "b"}), frozenset({"c", "d"})]
    fig = nv.plot_community_graph(g, communities)
    assert fig is not None


@pytest.mark.unit
def test_plot_community_graph_none_graph(nv: NetworkView) -> None:
    """Passing None as the graph triggers the empty-graph guard."""
    pytest.importorskip("matplotlib")
    pytest.importorskip("networkx")
    assert nv.plot_community_graph(None, []) is None


@pytest.mark.unit
def test_plot_community_graph_empty_graph(nv: NetworkView) -> None:
    """An empty NetworkX graph triggers the empty-graph guard."""
    pytest.importorskip("matplotlib")
    nx = pytest.importorskip("networkx")
    assert nv.plot_community_graph(nx.Graph(), []) is None


@pytest.mark.unit
def test_plot_community_graph_logs_error(
    nv: NetworkView, caplog: pytest.LogCaptureFixture
) -> None:
    """Inconsistent communities (non-iterable) trigger the outer except."""
    pytest.importorskip("matplotlib")
    nx = pytest.importorskip("networkx")
    g = nx.Graph()
    g.add_edge("a", "b")
    with caplog.at_level(logging.ERROR, logger="cogant.viz.network_view"):
        # A non-iterable community value forces the inner loop to raise
        result = nv.plot_community_graph(g, [123])  # type: ignore[list-item]
    assert result is None
    assert any("Error plotting community graph" in r.message for r in caplog.records)


# ===========================================================================
# NetworkView.plot_adjacency_heatmap
# ===========================================================================


@pytest.mark.unit
def test_plot_adjacency_heatmap_with_labels(nv: NetworkView) -> None:
    """Heatmap of a small adjacency matrix with labels renders successfully."""
    pytest.importorskip("matplotlib")
    matrix = [[1, 0, 1], [0, 1, 0], [1, 0, 1]]
    labels = ["A", "B", "C"]
    fig = nv.plot_adjacency_heatmap(matrix, labels)
    assert fig is not None
    assert "Adjacency Matrix Heatmap" in fig.axes[0].get_title()


@pytest.mark.unit
def test_plot_adjacency_heatmap_no_labels(nv: NetworkView) -> None:
    """Heatmap with labels=None skips the tick-label setup branch."""
    pytest.importorskip("matplotlib")
    matrix = [[1, 0], [0, 1]]
    fig = nv.plot_adjacency_heatmap(matrix, None)
    assert fig is not None


@pytest.mark.unit
def test_plot_adjacency_heatmap_large_matrix_label_subset(nv: NetworkView) -> None:
    """Large label list triggers the step-based subset branch (>20 labels)."""
    pytest.importorskip("matplotlib")
    n = 30
    matrix = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    labels = [f"node_{i}" for i in range(n)]
    fig = nv.plot_adjacency_heatmap(matrix, labels)
    assert fig is not None


@pytest.mark.unit
def test_plot_adjacency_heatmap_empty_returns_none(nv: NetworkView) -> None:
    """An empty matrix logs and returns None."""
    assert nv.plot_adjacency_heatmap([]) is None


@pytest.mark.unit
def test_plot_adjacency_heatmap_logs_error(
    nv: NetworkView, caplog: pytest.LogCaptureFixture
) -> None:
    """A non-rectangular matrix triggers numpy ValueError → outer except logs."""
    pytest.importorskip("matplotlib")
    pytest.importorskip("numpy")
    # Ragged rows make np.asarray(..., dtype=int) raise ValueError
    bad = [[1, 2, 3], [4, 5]]
    with caplog.at_level(logging.ERROR, logger="cogant.viz.network_view"):
        result = nv.plot_adjacency_heatmap(bad)
    assert result is None
    assert any("Error plotting adjacency heatmap" in r.message for r in caplog.records)


# ===========================================================================
# NetworkView.plot_hotspot_treemap
# ===========================================================================


@pytest.mark.unit
def test_plot_hotspot_treemap_handles_missing_squarify(nv: NetworkView) -> None:
    """Treemap returns None gracefully when the optional squarify dep is absent."""
    pytest.importorskip("matplotlib")
    # squarify is not part of the project deps. If it is installed locally the
    # call returns a Figure; if not, it returns None. Both are acceptable.
    result = nv.plot_hotspot_treemap({"a": 0.9, "b": 0.5, "c": 0.1})
    assert result is None or hasattr(result, "axes")


@pytest.mark.unit
def test_plot_hotspot_treemap_empty(nv: NetworkView) -> None:
    """An empty hotspots dict logs and returns None."""
    assert nv.plot_hotspot_treemap({}) is None


# ===========================================================================
# NetworkView.to_mermaid_community
# ===========================================================================


@pytest.mark.unit
def test_to_mermaid_community_with_small_communities(nv: NetworkView) -> None:
    """Small communities map to subgraphs containing every member node."""
    communities = [frozenset({"alpha", "beta"}), frozenset({"gamma"})]
    out = nv.to_mermaid_community(communities)
    assert out.startswith("graph TD")
    assert "Community 1" in out
    assert "Community 2" in out


@pytest.mark.unit
def test_to_mermaid_community_truncates_large_community(nv: NetworkView) -> None:
    """Communities larger than 10 emit a 'more nodes' overflow line."""
    big = frozenset(f"node-{i}" for i in range(15))
    out = nv.to_mermaid_community([big])
    assert "more_nodes" in out
    assert "+5 more" in out


@pytest.mark.unit
def test_to_mermaid_community_empty_returns_empty_str(nv: NetworkView) -> None:
    """Empty communities list logs and returns the empty string."""
    assert nv.to_mermaid_community([]) == ""


@pytest.mark.unit
def test_to_mermaid_community_sanitizes_node_ids(nv: NetworkView) -> None:
    """Node IDs containing '-' or '.' are sanitized to underscore-safe identifiers."""
    out = nv.to_mermaid_community([frozenset({"foo-bar.baz"})])
    assert "foo_bar_baz" in out


# ===========================================================================
# NetworkView.to_mermaid_hotspots
# ===========================================================================


@pytest.mark.unit
def test_to_mermaid_hotspots_color_thresholds(nv: NetworkView) -> None:
    """Top-percentile nodes get red, mid get yellow, low get green styling."""
    hotspots = {
        "critical": 1.0,  # 100% → red
        "important": 0.6,  # 60%  → yellow
        "moderate": 0.2,  # 20%  → green
    }
    out = nv.to_mermaid_hotspots(hotspots)
    assert out.startswith("graph TD")
    assert "#FF6B6B" in out  # red
    assert "#FFD700" in out  # yellow
    assert "#90EE90" in out  # green


@pytest.mark.unit
def test_to_mermaid_hotspots_truncates_to_top_10(nv: NetworkView) -> None:
    """Mermaid hotspot output limits to the top 10 nodes by score."""
    hotspots = {f"n_{i}": float(i) for i in range(20)}
    out = nv.to_mermaid_hotspots(hotspots)
    # Each node line includes 'Score:', so we count those rather than node entries
    assert out.count("Score:") == 10


@pytest.mark.unit
def test_to_mermaid_hotspots_empty(nv: NetworkView) -> None:
    """Empty hotspots dict logs and returns the empty string."""
    assert nv.to_mermaid_hotspots({}) == ""


@pytest.mark.unit
def test_to_mermaid_hotspots_sanitizes_node_names(nv: NetworkView) -> None:
    """Node names with '-' and '.' are sanitized to safe Mermaid identifiers."""
    out = nv.to_mermaid_hotspots({"a.b-c": 0.5})
    assert "a_b_c" in out


# ===========================================================================
# NetworkView.to_png / to_pdf
# ===========================================================================


@pytest.mark.unit
def test_network_to_png_writes_file(nv: NetworkView, tmp_path: Path) -> None:
    """to_png saves a real PNG and returns the destination path."""
    pytest.importorskip("matplotlib")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.scatter([0, 1, 2], [1, 4, 9])
    out = tmp_path / "net.png"
    result = nv.to_png(fig, str(out), dpi=80)
    assert result == str(out)
    assert out.exists() and out.stat().st_size > 0


@pytest.mark.unit
def test_network_to_png_returns_empty_when_fig_none(nv: NetworkView, tmp_path: Path) -> None:
    """A None figure triggers the guard and returns an empty string."""
    pytest.importorskip("matplotlib")
    assert nv.to_png(None, str(tmp_path / "nope.png")) == ""


@pytest.mark.unit
def test_network_to_png_returns_empty_on_save_error(nv: NetworkView, tmp_path: Path) -> None:
    """A bad output path triggers the outer except and returns an empty string."""
    pytest.importorskip("matplotlib")
    import matplotlib.pyplot as plt

    fig, _ = plt.subplots()
    bogus = tmp_path / "no_dir" / "deeper" / "out.png"
    assert nv.to_png(fig, str(bogus)) == ""


@pytest.mark.unit
def test_network_to_pdf_writes_file(nv: NetworkView, tmp_path: Path) -> None:
    """to_pdf saves a real PDF file and returns the destination path."""
    pytest.importorskip("matplotlib")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.bar(["x", "y"], [1, 2])
    out = tmp_path / "net.pdf"
    result = nv.to_pdf(fig, str(out))
    assert result == str(out)
    assert out.exists() and out.stat().st_size > 0


@pytest.mark.unit
def test_network_to_pdf_returns_empty_when_fig_none(nv: NetworkView, tmp_path: Path) -> None:
    """A None figure triggers the PDF guard and returns an empty string."""
    pytest.importorskip("matplotlib")
    assert nv.to_pdf(None, str(tmp_path / "nope.pdf")) == ""


@pytest.mark.unit
def test_network_to_pdf_returns_empty_on_save_error(nv: NetworkView, tmp_path: Path) -> None:
    """A bad output path triggers the PDF outer except and returns an empty string."""
    pytest.importorskip("matplotlib")
    import matplotlib.pyplot as plt

    fig, _ = plt.subplots()
    bogus = tmp_path / "missing" / "out.pdf"
    assert nv.to_pdf(fig, str(bogus)) == ""
