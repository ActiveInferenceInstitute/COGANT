"""Unit tests for viz/export_view.py — ExportView."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../py"))
import matplotlib
matplotlib.use("Agg")
import pytest
from cogant.viz.export_view import ExportView


def _export_results() -> dict:
    return {
        "json": {"path": "/out/bundle.json", "size_bytes": 1024, "ok": True},
        "markdown": {"path": "/out/bundle.md", "size_bytes": 2048, "ok": True},
        "yaml": {"path": "/out/bundle.yaml", "size_bytes": 512, "ok": False},
    }


def _bundle() -> dict:
    return {
        "metadata": {"name": "test_bundle", "version": "0.1"},
        "state_variables": [{"id": "sv1"}, {"id": "sv2"}],
        "observations": [{"id": "ob1"}],
        "actions": [{"id": "ac1"}],
        "matrices": {"A": [[1, 0], [0, 1]], "B": [[1]], "C": [[1, 0]], "D": [[0.5, 0.5]]},
    }


@pytest.fixture
def ev():
    return ExportView()


@pytest.mark.unit
def test_init():
    assert ExportView() is not None


@pytest.mark.unit
def test_plot_export_formats_basic(ev):
    fig = ev.plot_export_formats(_export_results())
    assert fig is not None
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_plot_export_formats_empty(ev):
    # empty dict returns None (no data to plot) — graceful
    ev.plot_export_formats({})
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_to_mermaid_export_pipeline_returns_str(ev):
    result = ev.to_mermaid_export_pipeline()
    assert isinstance(result, str) and len(result) > 0


@pytest.mark.unit
def test_plot_bundle_composition_basic(ev):
    fig = ev.plot_bundle_composition(_bundle())
    assert fig is not None
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_plot_bundle_composition_empty(ev):
    ev.plot_bundle_composition({})
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_to_png_round_trip(ev, tmp_path):
    import matplotlib.pyplot as plt
    fig, _ = plt.subplots()
    out = ev.to_png(fig, str(tmp_path / "ev.png"))
    assert isinstance(out, str)
    plt.close("all")


@pytest.mark.unit
def test_to_pdf_round_trip(ev, tmp_path):
    import matplotlib.pyplot as plt
    fig, _ = plt.subplots()
    out = ev.to_pdf(fig, str(tmp_path / "ev.pdf"))
    assert isinstance(out, str)
    plt.close("all")
