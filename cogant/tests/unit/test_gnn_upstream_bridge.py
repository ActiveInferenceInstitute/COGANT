"""Tests for the optional generalized-notation-notation (``gnn`` >= 4) bridge."""

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


def test_bridge_rejects_pre_v4_upstream(monkeypatch: pytest.MonkeyPatch) -> None:
    """An installed GNN 2.x/3.x distribution is reported as unavailable, not driven."""
    import importlib.metadata

    import cogant.gnn.upstream_bridge as ub

    monkeypatch.setattr(importlib.metadata, "version", lambda name: "2.0.0")
    assert ub.is_upstream_gnn_available() is False
    result = ub.run_upstream_validate_gnn("## GNNSection\nm\n")
    assert result.available is False
    assert result.ok is True
    assert result.skipped_reason is not None
    assert ">= 4.0" in result.skipped_reason


def test_bridge_rejects_foreign_gnn_distribution(monkeypatch: pytest.MonkeyPatch) -> None:
    """A top-level ``gnn`` owned by another distribution is never used."""
    import importlib.metadata

    import cogant.gnn.upstream_bridge as ub

    monkeypatch.setattr(importlib.metadata, "version", lambda name: "4.1.0")
    monkeypatch.setattr(
        importlib.metadata, "packages_distributions", lambda: {"gnn": ["some-other-gnn"]}
    )
    ub._gnn_owned_by_upstream_distribution.cache_clear()
    try:
        assert ub.is_upstream_gnn_available() is False
    finally:
        ub._gnn_owned_by_upstream_distribution.cache_clear()


def test_bridge_reports_missing_distribution(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib.metadata

    import cogant.gnn.upstream_bridge as ub

    def _missing(name: str) -> str:
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", _missing)
    assert ub.is_upstream_gnn_available() is False
    assert ub.upstream_version() is None
    with pytest.raises(ImportError, match="cogant\\[upstream\\]"):
        ub._require_upstream_gnn()


class _FakeUpstream:
    """Stand-in for the upstream ``gnn`` module (GNN 4.x public names)."""

    __version__ = "4.1.0"

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def validate_gnn_syntax(
        self, path: object, level: object = "standard"
    ) -> tuple[bool, list[str]]:
        self.calls.append(("validate_gnn_syntax", (path, level), {}))
        candidate = Path(str(path))
        text = candidate.read_text(encoding="utf-8") if candidate.is_file() else str(path)
        valid = "ModelName" in text
        return (valid, [] if valid else ["Required section missing: ModelName"])

    def validate_gnn_source(self, source: object, *, is_content: bool = False) -> dict[str, object]:
        self.calls.append(("validate_gnn_source", (source,), {"is_content": is_content}))
        return {"is_valid": True, "errors": []}

    def check_gnn_file_structure(self, *args: object, **kwargs: object) -> dict[str, object]:
        self.calls.append(("check_gnn_file_structure", args, kwargs))
        return {"valid": True}


def test_validate_routes_to_v4_validate_gnn_syntax(monkeypatch: pytest.MonkeyPatch) -> None:
    """``run_upstream_validate_gnn`` stages a file and forwards the level."""
    import cogant.gnn.upstream_bridge as ub

    fake = _FakeUpstream()
    monkeypatch.setattr(ub, "_require_upstream_gnn", lambda: fake)

    ok = ub.run_upstream_validate_gnn("## ModelName\nm\n", validation_level="strict")
    assert ok.available and ok.ok and ok.errors == [] and ok.version == "4.1.0"
    name, (path, level), _ = fake.calls[0]
    assert name == "validate_gnn_syntax"
    assert level == "strict"
    assert str(path).endswith(".gnn.md")
    assert not Path(str(path)).exists(), "temporary staging file must be removed"

    bad = ub.run_upstream_validate_gnn("## GNNSection\nm\n")
    assert bad.available and not bad.ok
    assert bad.errors == ["Required section missing: ModelName"]


def test_renamed_facades_route_to_v4_names(monkeypatch: pytest.MonkeyPatch) -> None:
    """GNN 2.x facade names forward to the GNN 4.x replacements."""
    import cogant.gnn.upstream_bridge as ub

    fake = _FakeUpstream()
    monkeypatch.setattr(ub, "_require_upstream_gnn", lambda: fake)

    assert ub.upstream_validate_file_content("## ModelName\nm\n") == {
        "is_valid": True,
        "errors": [],
    }
    assert ub.upstream_validate_structure("model.gnn.md") == {"valid": True}
    assert ub.upstream_validate_syntax_formal("## ModelName\nm\n")[0] is True
    assert [c[0] for c in fake.calls] == [
        "validate_gnn_source",
        "check_gnn_file_structure",
        "validate_gnn_syntax",
    ]


def test_validate_reports_upstream_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    import cogant.gnn.upstream_bridge as ub

    class _Raising(_FakeUpstream):
        def validate_gnn_syntax(
            self, path: object, level: object = "standard"
        ) -> tuple[bool, list[str]]:
            raise RuntimeError("boom")

    monkeypatch.setattr(ub, "_require_upstream_gnn", lambda: _Raising())
    r = ub.run_upstream_validate_gnn("## ModelName\nm\n")
    assert r.available is True
    assert r.ok is False
    assert r.errors == ["upstream validate_gnn_syntax raised: boom"]


def test_run_upstream_validate_gnn_returns_dataclass() -> None:
    """Always returns a structured result without raising."""
    r = run_upstream_validate_gnn("## GNNSection\ntest-model\n")
    assert isinstance(r, UpstreamGNNValidation)
    d = r.to_dict()
    assert "available" in d and "ok" in d
    assert d["errors"] == [] or isinstance(d["errors"], list)


def test_is_upstream_gnn_available_is_bool() -> None:
    assert is_upstream_gnn_available() in (True, False)


@pytest.mark.skipif(not is_upstream_gnn_available(), reason="upstream gnn not importable")
def test_upstream_version_string_or_none() -> None:
    v = upstream_version()
    assert v is None or isinstance(v, str)


@pytest.mark.skipif(not is_upstream_gnn_available(), reason="upstream gnn not importable")
def test_upstream_validate_markdown_alias() -> None:
    r = upstream_validate_markdown("## GNNSection\nx\n")
    assert isinstance(r, UpstreamGNNValidation)


@pytest.mark.skipif(not is_upstream_gnn_available(), reason="upstream gnn not importable")
def test_upstream_parse_file_minimal(tmp_path: Path) -> None:
    md = tmp_path / "t.gnn.md"
    md.write_text(
        "## GNNSection\nm\n\n## GNNVersionAndFlags\nGNN v2.0.0\n",
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
        "model.gnn.md": "## GNNSection\nx\n## GNNVersionAndFlags\nGNN v2.0.0\n"
        "## ModelName\nn\n"
        "## StateSpaceBlock\ns_f0[1,1,type=int]\n## Connections\n## InitialParameterization\n"
        "## Equations\nQ(s) = softmax(ln(D) + ln(A^T * o))\n"
        "## Time\nDiscrete\n## ActInfOntologyAnnotation\n"
        "## ModelParameters\nnum_hidden_states=1\n## Footer\nGenerated by COGANT.\n"
        "## Signature\npending\n",
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
        pytest.skip("upstream gnn not importable")
    monkeypatch.delenv("COGANT_DISABLE_UPSTREAM_GNN", raising=False)
    pkg = tmp_gnn_package()
    v = GNNValidator()
    r = v.validate_package(str(pkg), upstream_gnn=True)
    assert "upstream_gnn" in r.details


@pytest.mark.skipif(not is_upstream_gnn_available(), reason="upstream gnn not importable")
def test_get_upstream_gnn_format_enum() -> None:
    """Re-exported enum class from upstream."""
    fmt = get_upstream_gnn_format_enum()
    assert fmt is not None
    assert any(m.name == "MARKDOWN" for m in fmt)


@pytest.mark.skipif(not is_upstream_gnn_available(), reason="upstream gnn not importable")
def test_get_upstream_parsing_system() -> None:
    """Smoke: upstream parser instance constructs."""
    ps = get_upstream_parsing_system()
    assert ps is not None


@pytest.mark.skipif(not is_upstream_gnn_available(), reason="upstream gnn not importable")
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
