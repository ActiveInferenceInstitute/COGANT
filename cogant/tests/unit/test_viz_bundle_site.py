"""Coverage for ``cogant.viz.bundle_site`` (static HTML scaffold for Bundle.render_site)."""

from __future__ import annotations

from pathlib import Path

from cogant.viz import bundle_site


def test_render_bundle_site_writes_expected_tree(tmp_path: Path) -> None:
    repo_summary = {
        "target": "/tmp/demo",
        "file_count": 3,
        "total_errors": 0,
        "language_distribution": {"python": 2, "markdown": 1},
    }
    out = bundle_site.render_bundle_site(tmp_path, target="/tmp/demo", repo_summary=repo_summary)
    assert out == tmp_path / "index.html"
    assert (tmp_path / "index.html").is_file()
    assert (tmp_path / "graph" / "program_graph.html").is_file()
    assert (tmp_path / "models" / "state_space.html").is_file()
    assert (tmp_path / "assets" / "style.css").is_file()
    text = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "COGANT Analysis Report" in text
    assert "python" in text and "markdown" in text


def test_render_fragments_non_empty() -> None:
    assert "Program Graph" in bundle_site.render_graph_html()
    assert bundle_site.render_statespace_html()
    assert "body" in bundle_site.render_css()
