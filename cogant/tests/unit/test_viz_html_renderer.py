"""Unit tests for viz/html_renderer.py — HTMLSiteRenderer."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../py"))
import pytest
from cogant.viz.html_renderer import HTMLSiteRenderer


def _bundle() -> dict:
    return {
        "target": "my_package",
        "stage_results": {
            "ingest": {"node_count": 10, "edge_count": 15, "status": "ok"},
            "translate": {"rule_firings": 7, "status": "ok"},
        },
        "errors": [],
        "artifacts": {"graph": "/out/graph.json"},
        "score": 0.85,
    }


@pytest.fixture
def renderer():
    return HTMLSiteRenderer(_bundle())


@pytest.mark.unit
def test_init():
    r = HTMLSiteRenderer({})
    assert r is not None


@pytest.mark.unit
def test_render_creates_index(renderer, tmp_path):
    result = renderer.render(str(tmp_path / "site"))
    assert result.exists()
    assert result.name == "index.html"


@pytest.mark.unit
def test_render_creates_subdirs(renderer, tmp_path):
    out = tmp_path / "site2"
    renderer.render(str(out))
    assert (out / "graph").exists()
    assert (out / "models").exists()
    assert (out / "provenance").exists()
    assert (out / "assets").exists()


@pytest.mark.unit
def test_render_index_content(renderer, tmp_path):
    out = tmp_path / "site3"
    idx = renderer.render(str(out))
    content = idx.read_text()
    assert len(content) > 100


@pytest.mark.unit
def test_render_empty_bundle(tmp_path):
    r = HTMLSiteRenderer({})
    result = r.render(str(tmp_path / "empty_site"))
    assert result.exists()


@pytest.mark.unit
def test_render_bundle_with_errors(tmp_path):
    bundle = {
        "target": "bad_pkg",
        "stage_results": {},
        "errors": ["ingest failed: missing file"],
    }
    r = HTMLSiteRenderer(bundle)
    result = r.render(str(tmp_path / "err_site"))
    assert result.exists()


@pytest.mark.unit
def test_render_graph_pages_created(renderer, tmp_path):
    out = tmp_path / "site4"
    renderer.render(str(out))
    html_files = list(out.rglob("*.html"))
    assert len(html_files) >= 1


@pytest.mark.unit
def test_render_models_dir_created(renderer, tmp_path):
    out = tmp_path / "site5"
    renderer.render(str(out))
    assert (out / "models").exists()


@pytest.mark.unit
def test_render_provenance_dir_created(renderer, tmp_path):
    out = tmp_path / "site6"
    renderer.render(str(out))
    assert (out / "provenance").exists()


@pytest.mark.unit
def test_render_data_json_created(renderer, tmp_path):
    out = tmp_path / "site7"
    renderer.render(str(out))
    # data.json or similar should exist in assets
    import os
    files = list(out.rglob("*.json"))
    assert len(files) >= 1
