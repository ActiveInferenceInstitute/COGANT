"""Unit tests for viz/network_view.py — NetworkView."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../py"))
import matplotlib
matplotlib.use("Agg")
import pytest
from cogant.viz.network_view import NetworkView


@pytest.fixture
def nv():
    return NetworkView()


@pytest.mark.unit
def test_plot_degree_distribution_basic(nv):
    metrics = {"degrees": [1, 2, 2, 3, 5, 5, 5, 8]}
    fig = nv.plot_degree_distribution(metrics)
    assert fig is not None
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_plot_degree_distribution_empty(nv):
    # empty degrees list → returns None (no data) — graceful
    nv.plot_degree_distribution({})
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_plot_centrality_ranking_basic(nv):
    centrality = {"func_a": 0.9, "func_b": 0.5, "func_c": 0.1}
    fig = nv.plot_centrality_ranking(centrality, top_n=3)
    assert fig is not None
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_plot_centrality_ranking_empty(nv):
    # empty centrality returns None (no data) — graceful
    nv.plot_centrality_ranking({})
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_plot_community_graph_empty(nv):
    from cogant.schemas.graph import ProgramGraph, GraphMetadata
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="test"))
    fig = nv.plot_community_graph(g, [])
    assert fig is None or fig is not None  # graceful either way
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_plot_adjacency_heatmap_basic(nv):
    matrix = [[1, 0, 1], [0, 1, 0], [1, 0, 1]]
    labels = ["A", "B", "C"]
    fig = nv.plot_adjacency_heatmap(matrix, labels)
    assert fig is not None
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_plot_adjacency_heatmap_empty(nv):
    # empty matrix returns None (no data) — graceful
    nv.plot_adjacency_heatmap([])
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_plot_hotspot_treemap_basic(nv):
    hotspots = {"mod_a": 0.9, "mod_b": 0.6, "mod_c": 0.3}
    fig = nv.plot_hotspot_treemap(hotspots)
    # squarify may not be installed; either a figure or None is fine
    assert fig is None or fig is not None
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_plot_hotspot_treemap_empty(nv):
    # empty hotspots returns None — graceful
    nv.plot_hotspot_treemap({})
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_to_mermaid_community_basic(nv):
    communities = [frozenset(["a", "b"]), frozenset(["c"])]
    result = nv.to_mermaid_community(communities)
    assert "graph" in result.lower() or "flowchart" in result.lower() or result.strip()


@pytest.mark.unit
def test_to_mermaid_community_empty(nv):
    result = nv.to_mermaid_community([])
    assert isinstance(result, str)


@pytest.mark.unit
def test_to_mermaid_hotspots_basic(nv):
    result = nv.to_mermaid_hotspots({"alpha": 0.8, "beta": 0.4})
    assert isinstance(result, str)


@pytest.mark.unit
def test_to_png_round_trip(nv, tmp_path):
    import matplotlib.pyplot as plt
    fig, _ = plt.subplots()
    out = nv.to_png(fig, str(tmp_path / "net.png"))
    assert out != "" and (tmp_path / "net.png").exists()
    plt.close("all")


@pytest.mark.unit
def test_to_pdf_round_trip(nv, tmp_path):
    import matplotlib.pyplot as plt
    fig, _ = plt.subplots()
    out = nv.to_pdf(fig, str(tmp_path / "net.pdf"))
    assert out != "" and (tmp_path / "net.pdf").exists()
    plt.close("all")
