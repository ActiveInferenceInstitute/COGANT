"""Tests for generalized-notation-notation (src.gnn) bridge — core dependency."""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.gnn import (
    get_upstream_gnn_format_enum,
    get_upstream_parsing_system,
    parse_upstream_model_gnn_md,
)
from cogant.gnn.upstream_bridge import (
    UpstreamGNNValidation,
    is_upstream_gnn_available,
    json_safe,
    run_upstream_validate_gnn,
    upstream_parse_file,
    upstream_validate_markdown,
    upstream_version,
)


def test_run_upstream_validate_gnn_returns_dataclass() -> None:
    """Always returns a structured result without raising."""
    r = run_upstream_validate_gnn("## GNNSection\ntest-model\n")
    assert isinstance(r, UpstreamGNNValidation)
    d = r.to_dict()
    assert "available" in d and "ok" in d
    assert d["errors"] == [] or isinstance(d["errors"], list)


def test_is_upstream_gnn_available_is_bool() -> None:
    assert is_upstream_gnn_available() in (True, False)


@pytest.mark.skipif(not is_upstream_gnn_available(), reason="src.gnn not importable")
def test_upstream_version_string_or_none() -> None:
    v = upstream_version()
    assert v is None or isinstance(v, str)


@pytest.mark.skipif(not is_upstream_gnn_available(), reason="src.gnn not importable")
def test_upstream_validate_markdown_alias() -> None:
    r = upstream_validate_markdown("## GNNSection\nx\n")
    assert isinstance(r, UpstreamGNNValidation)


@pytest.mark.skipif(not is_upstream_gnn_available(), reason="src.gnn not importable")
def test_upstream_parse_file_minimal(tmp_path: Path) -> None:
    md = tmp_path / "t.gnn.md"
    md.write_text(
        "## GNNSection\nm\n\n## GNNVersionAndFlags\nGNN v1\n",
        encoding="utf-8",
    )
    info = upstream_parse_file(md)
    assert info is not None


def test_json_safe_primitives() -> None:
    assert json_safe({"a": 1}) == {"a": 1}
    assert json_safe([1, 2]) == [1, 2]


def test_validator_respects_disable_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """When COGANT_DISABLE_UPSTREAM_GNN is set, validator skips upstream."""
    from cogant.gnn.validator import GNNValidator

    pkg = tmp_gnn_package()
    try:
        monkeypatch.setenv("COGANT_DISABLE_UPSTREAM_GNN", "1")
        v = GNNValidator()
        r = v.validate_package(str(pkg), upstream_gnn=None)
        assert "upstream_gnn" not in r.details or r.details.get("upstream_gnn") is None
    finally:
        monkeypatch.delenv("COGANT_DISABLE_UPSTREAM_GNN", raising=False)


def tmp_gnn_package() -> Path:
    """Minimal on-disk layout for GNNValidator required files."""
    import tempfile

    root = Path(tempfile.mkdtemp(prefix="gnn_pkg_"))
    files = {
        "manifest.json": "{}",
        "model.gnn.md": "## GNNSection\nx\n## GNNVersionAndFlags\nGNN v1\n## ModelName\nn\n"
        "## StateSpaceBlock\ns_f0[1,1,type=int]\n## Connections\n## InitialParameterization\n"
        "## Time\nDiscrete\n## ActInfOntologyAnnotation\n",
        "model.gnn.json": "{}",
        "state_space.json": '{"variables":[],"observations":[],"actions":[],"transitions":{}}',
        "observations.json": '{"modalities":[],"count":0}',
        "actions.json": '{"actions":[],"policies":[],"count":0}',
        "transitions.json": '{"structure":{},"deterministic":true,"markovian":true}',
        "preferences.json": '{"preferences":[],"constraints":[],"objectives":[]}',
        "factors.json": '{"factorization":{},"factors":[]}',
        "provenance.json": '{"timestamp":null,"sources":{}}',
        "ontology.json": '{"mappings":[],"classes":[],"relationships":[]}',
        "actions_policies.json": '{"actions":[],"policies":[],"count":0}',
        "connections.json": '{"edges":[],"count":0,"by_kind":{}}',
        "preferences_constraints.json": '{"preferences":[],"constraints":[],"objectives":[]}',
        "markov_blanket.json": '{"schema_version":"1.0.0","roles":{"internal":[],"sensory":[],"active":[],"external":[]}}',
        "markov_network.json": '{"role_counts":{},"aggregate_edges":[]}',
    }
    for name, body in files.items():
        (root / name).write_text(body, encoding="utf-8")
    return root


def test_validator_runs_upstream_when_core_dep(monkeypatch: pytest.MonkeyPatch) -> None:
    """With disable env unset, details includes upstream_gnn when upstream runs."""
    from cogant.gnn.validator import GNNValidator

    if not is_upstream_gnn_available():
        pytest.skip("src.gnn not importable")
    monkeypatch.delenv("COGANT_DISABLE_UPSTREAM_GNN", raising=False)
    pkg = tmp_gnn_package()
    v = GNNValidator()
    r = v.validate_package(str(pkg), upstream_gnn=True)
    assert "upstream_gnn" in r.details


@pytest.mark.skipif(not is_upstream_gnn_available(), reason="src.gnn not importable")
def test_get_upstream_gnn_format_enum() -> None:
    """Re-exported enum class from upstream."""
    fmt = get_upstream_gnn_format_enum()
    assert fmt is not None
    assert any(m.name == "MARKDOWN" for m in fmt)


@pytest.mark.skipif(not is_upstream_gnn_available(), reason="src.gnn not importable")
def test_get_upstream_parsing_system() -> None:
    """Smoke: upstream parser instance constructs."""
    ps = get_upstream_parsing_system()
    assert ps is not None


@pytest.mark.skipif(not is_upstream_gnn_available(), reason="src.gnn not importable")
def test_parse_upstream_model_gnn_md_minimal_package() -> None:
    """JSON-safe summary for model.gnn.md under a package directory."""
    pkg = tmp_gnn_package()
    try:
        out = parse_upstream_model_gnn_md(pkg)
        assert "path" in out
        assert str(pkg / "model.gnn.md") in out["path"] or out["path"].endswith("model.gnn.md")
        assert ("parse" in out and out["parse"] is not None) or "error" in out
    finally:
        import shutil

        shutil.rmtree(pkg, ignore_errors=True)


@pytest.mark.parametrize(
    "name",
    (
        "upstream_discover_files",
        "upstream_generate_report",
        "upstream_module_info",
        "upstream_parse_formal",
        "upstream_process_directory",
        "upstream_process_directory_lightweight",
        "upstream_process_multi_format",
        "upstream_validate_file_content",
        "upstream_validate_structure",
        "upstream_validate_syntax_formal",
    ),
)
def test_upstream_bridge_advanced_facades_are_importable(name: str) -> None:
    """Facades not re-exported from ``cogant.gnn`` remain on ``upstream_bridge``."""
    import cogant.gnn.upstream_bridge as ub

    assert hasattr(ub, name)
    assert callable(getattr(ub, name))
