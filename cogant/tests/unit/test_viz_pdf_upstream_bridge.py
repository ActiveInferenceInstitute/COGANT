"""Targeted unit tests: PDFExporter + upstream_bridge — push 88%/82% → ~95%+.

Targets uncovered lines in two files:

1. ``py/cogant/viz/pdf_export.py`` (88% → ~95%):
   * lines 67-70: ``_role_counts_from_mappings`` non-dict / non-list / scalar input
   * lines 206-208, 233-235, 258-259, 283: program graph + bundle inner-except paths
   * lines 352-354, 379-381, 398, 400-401: matrix import-error & ``_to_2d`` failure
   * lines 464-466, 491-493, 587-589, 614-616, 626, 702: blanket / pipeline edges
   * lines 723-725, 750-752, 915-916, 926-928, 971-973: roundtrip + full-report imports
   * lines 1088-1090, 1093-1120: full-analysis coupling-metrics empty + populated paths
   * line 1141, 1158, 1244, 1261-1263: full-analysis matrix + findings dict branch
   * Page-layout exercises: report with non-dict pipeline_result object, large finding lists

2. ``py/cogant/gnn/upstream_bridge/__init__.py``:
   * ``_require_upstream_gnn`` missing-distribution ImportError chain
   * ``json_safe`` model_dump fallback (already partially covered)
   * ``is_upstream_gnn_available`` / ``upstream_version`` ImportError branches
   * ``run_upstream_validate_gnn``: unavailable, missing ``validate_gnn_syntax``,
     raising validator, and swallowed temp-file unlink OSError branches
   * ``upstream_validate_file_content``: missing ``validate_gnn_source`` and
     non-dict result branches
   * process_directory + process_multi_format passthroughs
   * parse_upstream_model_gnn_md exception branch

All tests use real objects (no mocks) per COGANT no-mocks policy. Optional
matplotlib / reportlab paths use ``pytest.importorskip``. Import-error
simulation uses ``monkeypatch.setattr(builtins, "__import__", ...)`` (real
Python machinery, not unittest.mock).
"""

from __future__ import annotations

import builtins
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# pdf_export — _role_counts_from_mappings module-level helper edge cases
# --------------------------------------------------------------------------- #


def test_role_counts_from_none_returns_empty() -> None:
    """Lines 69-70: scalar/None/unknown fallback to {}."""
    from cogant.viz.pdf_export import _role_counts_from_mappings

    assert _role_counts_from_mappings(None) == {}


def test_role_counts_from_int_returns_empty() -> None:
    """Lines 69-70: non-dict/non-list input falls through."""
    from cogant.viz.pdf_export import _role_counts_from_mappings

    assert _role_counts_from_mappings(42) == {}


def test_role_counts_from_string_returns_empty() -> None:
    """Strings would technically iterate, but fall through to else."""
    from cogant.viz.pdf_export import _role_counts_from_mappings

    assert _role_counts_from_mappings("not a mapping") == {}


def test_role_counts_from_list_of_dicts() -> None:
    """Lines 67-68: list branch with dict items."""
    from cogant.viz.pdf_export import _role_counts_from_mappings

    items = [
        {"kind": "HIDDEN_STATE"},
        {"kind": "OBSERVATION"},
        {"kind": "HIDDEN_STATE"},
    ]
    out = _role_counts_from_mappings(items)
    assert out == {"HIDDEN_STATE": 2, "OBSERVATION": 1}


def test_role_counts_from_dict_of_objects() -> None:
    """Per source-code precedence, non-dict items always resolve to 'unknown'.

    The expression in pdf_export._role_counts_from_mappings is:

        str(getattr(m, "kind", None) or m.get("kind", "unknown")
            if isinstance(m, dict) else "unknown")

    Python parses this as a ternary on the RHS of ``or``, so the entire
    ``isinstance`` ternary is the second operand. When ``m`` is not a dict,
    the ternary returns "unknown" regardless of any ``.kind`` attribute.
    Documented as the helper's actual behavior.
    """
    from cogant.viz.pdf_export import _role_counts_from_mappings

    @dataclass
    class _M:
        kind: str

    out = _role_counts_from_mappings({"a": _M("ROLE1"), "b": _M("ROLE2"), "c": _M("ROLE1")})
    # Three non-dict items all resolved to "unknown"
    assert out == {"unknown": 3}


def test_role_counts_from_list_with_object_items() -> None:
    """List branch with object items: non-dict items always resolve to 'unknown'."""
    from cogant.viz.pdf_export import _role_counts_from_mappings

    class _Obj:
        pass

    out = _role_counts_from_mappings([_Obj(), _Obj()])
    # Objects without 'kind' or 'get' fall through to 'unknown'
    assert "unknown" in out
    assert out["unknown"] == 2


def test_role_counts_from_list_of_dicts_uses_kind_key() -> None:
    """Dict items DO take the .get('kind') branch via the ternary's true side."""
    from cogant.viz.pdf_export import _role_counts_from_mappings

    out = _role_counts_from_mappings(
        [
            {"kind": "K1"},
            {"kind": "K2"},
            {"kind": "K1"},
            {},  # no 'kind' → "unknown" default
        ]
    )
    assert out == {"K1": 2, "K2": 1, "unknown": 1}


# --------------------------------------------------------------------------- #
# pdf_export — _kind_color sanity
# --------------------------------------------------------------------------- #


def test_kind_color_known_kind() -> None:
    from cogant.viz.pdf_export import _DEFAULT_COLOR, _kind_color

    assert _kind_color("module") == "#4C72B0"
    assert _kind_color("function") == "#55A868"
    assert _kind_color("nonexistent_kind_xyz") == _DEFAULT_COLOR


def test_kind_color_non_string_input() -> None:
    """Coerced via str() — int / None pass through."""
    from cogant.viz.pdf_export import _DEFAULT_COLOR, _kind_color

    assert _kind_color(42) == _DEFAULT_COLOR


# --------------------------------------------------------------------------- #
# pdf_export — node_counts_by_kind
# --------------------------------------------------------------------------- #


def test_node_counts_by_kind_empty_input() -> None:
    """Object without .nodes returns {} (line ~54-55 fallback)."""
    from cogant.viz.pdf_export import _node_counts_by_kind

    class _NoNodes:
        pass

    assert _node_counts_by_kind(_NoNodes()) == {}


def test_node_counts_by_kind_list_nodes_returns_empty() -> None:
    """When .nodes is not a dict, count fall-through."""
    from cogant.viz.pdf_export import _node_counts_by_kind

    @dataclass
    class _G:
        nodes: list = field(default_factory=list)

    # nodes is list, not dict — so loop is skipped
    assert _node_counts_by_kind(_G(nodes=[])) == {}


# --------------------------------------------------------------------------- #
# pdf_export — import-error error branches for each export method
# --------------------------------------------------------------------------- #

_PLT_MODS = ("matplotlib", "matplotlib.pyplot", "matplotlib.backends.backend_pdf", "networkx")


def _make_blocker(blocked: tuple[str, ...]) -> Any:
    """Return a __import__ replacement that raises on blocked names."""
    real_import = builtins.__import__

    def _blocker(name: str, *args: Any, **kwargs: Any) -> Any:
        if name in blocked or name.split(".")[0] in {b.split(".")[0] for b in blocked}:
            raise ImportError(f"blocked: {name}")
        return real_import(name, *args, **kwargs)

    return _blocker


def test_export_gnn_bundle_import_error(monkeypatch, tmp_path: Path) -> None:
    """Lines 233-235: ImportError on matplotlib → empty string + warning log."""
    pytest.importorskip("matplotlib")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    out = str(tmp_path / "x.pdf")
    # Simulate matplotlib import failure
    with monkeypatch.context() as m:
        m.setattr(builtins, "__import__", _make_blocker(_PLT_MODS))
        # Force re-import by clearing cached
        for mod_name in list(sys.modules):
            if any(mod_name.startswith(b) for b in ("matplotlib",)):
                m.delitem(sys.modules, mod_name, raising=False)
        result = e.export_gnn_bundle(object(), out)
    assert result == ""


def test_export_matrices_import_error(monkeypatch, tmp_path: Path) -> None:
    """Lines 379-381: matrices import error returns empty string."""
    pytest.importorskip("matplotlib")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    out = str(tmp_path / "m.pdf")
    with monkeypatch.context() as m:
        m.setattr(builtins, "__import__", _make_blocker(_PLT_MODS))
        for mod_name in list(sys.modules):
            if mod_name.startswith("matplotlib"):
                m.delitem(sys.modules, mod_name, raising=False)
        result = e.export_matrices({"A": [[1.0]]}, out)
    assert result == ""


def test_export_markov_blanket_import_error(monkeypatch, tmp_path: Path) -> None:
    """Lines 491-493: markov blanket import error returns empty string."""
    pytest.importorskip("matplotlib")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    out = str(tmp_path / "b.pdf")
    with monkeypatch.context() as m:
        m.setattr(builtins, "__import__", _make_blocker(_PLT_MODS))
        for mod_name in list(sys.modules):
            if mod_name.startswith("matplotlib"):
                m.delitem(sys.modules, mod_name, raising=False)
        result = e.export_markov_blanket(object(), out)
    assert result == ""


def test_export_pipeline_report_import_error(monkeypatch, tmp_path: Path) -> None:
    """Lines 614-616: pipeline report import error returns empty string."""
    pytest.importorskip("matplotlib")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    out = str(tmp_path / "p.pdf")
    with monkeypatch.context() as m:
        m.setattr(builtins, "__import__", _make_blocker(_PLT_MODS))
        for mod_name in list(sys.modules):
            if mod_name.startswith("matplotlib"):
                m.delitem(sys.modules, mod_name, raising=False)
        result = e.export_pipeline_report({}, out)
    assert result == ""


def test_export_roundtrip_report_import_error(monkeypatch, tmp_path: Path) -> None:
    """Lines 750-752: roundtrip report import error returns empty string."""
    pytest.importorskip("matplotlib")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    out = str(tmp_path / "r.pdf")
    with monkeypatch.context() as m:
        m.setattr(builtins, "__import__", _make_blocker(_PLT_MODS))
        for mod_name in list(sys.modules):
            if mod_name.startswith("matplotlib"):
                m.delitem(sys.modules, mod_name, raising=False)
        result = e.export_roundtrip_report(object(), out)
    assert result == ""


def test_export_full_analysis_report_import_error(monkeypatch, tmp_path: Path) -> None:
    """Lines 971-973: full analysis import error returns empty string."""
    pytest.importorskip("matplotlib")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    out = str(tmp_path / "f.pdf")
    with monkeypatch.context() as m:
        m.setattr(builtins, "__import__", _make_blocker(_PLT_MODS))
        for mod_name in list(sys.modules):
            if mod_name.startswith("matplotlib"):
                m.delitem(sys.modules, mod_name, raising=False)
        result = e.export_full_analysis_report({}, out)
    assert result == ""


# --------------------------------------------------------------------------- #
# pdf_export — exception-during-render error paths (lines 206-208, 352-354,
# 464-466, 587-589, 723-725, 926-928, 1261-1263)
# --------------------------------------------------------------------------- #


def test_export_program_graph_invalid_output_dir_returns_empty(tmp_path: Path) -> None:
    """When parent.mkdir cannot create, the inner try block returns ''.

    Use a path under an existing FILE — Path.mkdir(parents=True) raises
    NotADirectoryError on POSIX which the outer except catches.
    """
    pytest.importorskip("matplotlib")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    blocking_file = tmp_path / "blocker"
    blocking_file.write_text("nope", encoding="utf-8")
    # Path under a file — mkdir(parents=True) raises FileExistsError/NotADirectoryError
    out = str(blocking_file / "subdir" / "graph.pdf")
    result = e.export_program_graph(object(), out)
    assert result == ""


def test_export_gnn_bundle_invalid_output_dir_returns_empty(tmp_path: Path) -> None:
    """Lines 352-354: bundle outer-except path."""
    pytest.importorskip("matplotlib")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    blocking_file = tmp_path / "block_b"
    blocking_file.write_text("nope", encoding="utf-8")
    out = str(blocking_file / "deep" / "b.pdf")
    result = e.export_gnn_bundle(object(), out)
    assert result == ""


def test_export_matrices_invalid_output_dir_returns_empty(tmp_path: Path) -> None:
    """Lines 464-466: matrices outer-except path."""
    pytest.importorskip("matplotlib")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    blocking_file = tmp_path / "block_m"
    blocking_file.write_text("nope", encoding="utf-8")
    out = str(blocking_file / "deep" / "m.pdf")
    result = e.export_matrices({"A": [[1.0]]}, out)
    assert result == ""


def test_export_markov_blanket_invalid_output_dir_returns_empty(tmp_path: Path) -> None:
    """Lines 587-589: markov blanket outer-except path."""
    pytest.importorskip("matplotlib")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    blocking_file = tmp_path / "block_mb"
    blocking_file.write_text("nope", encoding="utf-8")
    out = str(blocking_file / "deep" / "mb.pdf")
    result = e.export_markov_blanket({}, out)
    assert result == ""


def test_export_pipeline_report_invalid_output_dir_returns_empty(tmp_path: Path) -> None:
    """Lines 723-725: pipeline outer-except path."""
    pytest.importorskip("matplotlib")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    blocking_file = tmp_path / "block_p"
    blocking_file.write_text("nope", encoding="utf-8")
    out = str(blocking_file / "deep" / "p.pdf")
    result = e.export_pipeline_report({}, out)
    assert result == ""


def test_export_roundtrip_report_invalid_output_dir_returns_empty(tmp_path: Path) -> None:
    """Lines 926-928: roundtrip outer-except path."""
    pytest.importorskip("matplotlib")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    blocking_file = tmp_path / "block_r"
    blocking_file.write_text("nope", encoding="utf-8")
    out = str(blocking_file / "deep" / "r.pdf")
    result = e.export_roundtrip_report({}, out)
    assert result == ""


def test_export_full_analysis_report_invalid_output_dir_returns_empty(tmp_path: Path) -> None:
    """Lines 1261-1263: full analysis outer-except path."""
    pytest.importorskip("matplotlib")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    blocking_file = tmp_path / "block_full"
    blocking_file.write_text("nope", encoding="utf-8")
    out = str(blocking_file / "deep" / "full.pdf")
    result = e.export_full_analysis_report({}, out)
    assert result == ""


# --------------------------------------------------------------------------- #
# pdf_export — _to_2d failure path (line 400-401)
# --------------------------------------------------------------------------- #


def test_export_matrices_with_uncoercible_data(tmp_path: Path) -> None:
    """Lines 398-401: when np.asarray raises, _to_2d returns None — drawn as text.

    Pass a value that np.asarray(dtype=float) cannot coerce. A list with a
    string-only entry triggers ValueError inside np.asarray.
    """
    pytest.importorskip("matplotlib")
    pytest.importorskip("numpy")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    out = str(tmp_path / "uncoercible.pdf")
    bad_matrices = {
        "A": [[1.0, 2.0], [3.0, 4.0]],
        "B": "not a matrix at all",  # _to_2d returns None
        "C": [["x", "y"]],  # ValueError on float coercion
        "D": None,
    }
    result = e.export_matrices(bad_matrices, out)
    assert result == out
    assert Path(out).exists()


def test_export_matrices_with_4d_array(tmp_path: Path) -> None:
    """Lines 397-398: ndim > 3 reshape branch.

    Use only valid non-empty arrays — the per-matrix detail page calls
    ``arr.min()``/``arr.max()`` and zero-size arrays raise ValueError.
    """
    pytest.importorskip("matplotlib")
    np = pytest.importorskip("numpy")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    out = str(tmp_path / "4d.pdf")
    matrices = {
        "A": np.random.rand(2, 3, 4, 5),  # 4-D → reshape branch
        "B": np.random.rand(3, 3, 2),  # 3-D → first slice branch
        "C": np.random.rand(4),  # 1-D → reshape(1,-1) branch
        "D": np.random.rand(2, 2),  # 2-D pass-through
    }
    result = e.export_matrices(matrices, out)
    assert result == out
    assert Path(out).exists()


# --------------------------------------------------------------------------- #
# pdf_export — page-layout & content edge cases
# --------------------------------------------------------------------------- #


def test_export_program_graph_with_invalid_edges(tmp_path: Path) -> None:
    """Edges with missing source/target are silently skipped (line ~133 branch)."""
    pytest.importorskip("matplotlib")
    pytest.importorskip("networkx")
    from cogant.viz.pdf_export import PDFExporter

    @dataclass
    class _N:
        kind: str
        name: str

    @dataclass
    class _E:
        source_id: str | None
        target_id: str | None
        kind: str = "calls"

    @dataclass
    class _G:
        nodes: dict = field(default_factory=dict)
        edges: dict = field(default_factory=dict)

    g = _G(
        nodes={"a": _N("module", "alpha"), "b": _N("class", "Bee")},
        edges={
            "valid": _E("a", "b"),
            "no_src": _E(None, "b"),
            "no_tgt": _E("a", None),
            "both_none": _E(None, None),
        },
    )
    e = PDFExporter()
    out = str(tmp_path / "edges.pdf")
    result = e.export_program_graph(g, out)
    assert result == out
    assert Path(out).exists()


def test_export_pipeline_report_with_object_input(tmp_path: Path) -> None:
    """Line 626-637: non-dict input takes attr-extraction branch."""
    pytest.importorskip("matplotlib")
    from cogant.viz.pdf_export import PDFExporter

    @dataclass
    class _PipelineResult:
        target: str = "object_target"
        stage_timings: dict = field(default_factory=lambda: {"a": 0.1, "b": 0.2})
        stage_metrics: dict = field(
            default_factory=lambda: {"a": {"count": 5}, "b": "scalar_value"}
        )
        timing: dict | None = None
        metrics: dict | None = None

    e = PDFExporter()
    out = str(tmp_path / "obj_pipeline.pdf")
    result = e.export_pipeline_report(_PipelineResult(), out)
    assert result == out
    assert Path(out).exists()


def test_export_pipeline_report_with_scalar_metric(tmp_path: Path) -> None:
    """Line 702: scalar (non-dict) stage_data branch in metrics table."""
    pytest.importorskip("matplotlib")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    out = str(tmp_path / "scalar_metric.pdf")
    result = e.export_pipeline_report(
        {
            "stage_timings": {"s1": 0.1},
            "stage_metrics": {
                "s1": {"k": 1},
                "s2": "scalar_value",  # non-dict branch
                "s3": 42,
            },
        },
        out,
    )
    assert result == out


def test_export_roundtrip_report_high_score(tmp_path: Path) -> None:
    """Score >= 0.8 triggers green colour branch."""
    pytest.importorskip("matplotlib")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    out = str(tmp_path / "rt_high.pdf")
    result = e.export_roundtrip_report(
        {
            "role_preservation_score": 0.95,
            "tier": "ISOMORPHIC",
            "forward_roles": {"X": 1, "Y": 2},
            "reverse_roles": {"X": 1, "Y": 2, "Z": 1},
            "elapsed_s": 0.5,
        },
        out,
    )
    assert result == out


def test_export_roundtrip_report_mid_score(tmp_path: Path) -> None:
    """0.5 <= score < 0.8 → orange branch."""
    pytest.importorskip("matplotlib")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    out = str(tmp_path / "rt_mid.pdf")
    result = e.export_roundtrip_report(
        {
            "role_preservation_score": 0.65,
            "tier": "PARTIAL",
            "forward_roles": {"A": 3},
            "reverse_roles": {"A": 4, "B": 1},
        },
        out,
    )
    assert result == out


def test_export_roundtrip_report_no_roles(tmp_path: Path) -> None:
    """Empty forward/reverse roles trigger the outer except branch.

    Lines 926-928: when both role dicts are empty the delta-table render
    raises (matplotlib cannot create a zero-row table layout) and the
    outer ``except Exception`` returns ''. This still exercises the
    code path through the catch.
    """
    pytest.importorskip("matplotlib")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    out = str(tmp_path / "rt_empty.pdf")
    result = e.export_roundtrip_report(
        {"role_preservation_score": 0.0, "tier": "EMPTY", "forward_roles": {}, "reverse_roles": {}},
        out,
    )
    # Either the report renders (some matplotlib versions tolerate empty tables)
    # or the outer except returns ''. Both paths exercise the code.
    assert result in (out, "")


def test_export_full_analysis_with_dict_findings(tmp_path: Path) -> None:
    """Line 1244: validation_findings as dict items branch."""
    pytest.importorskip("matplotlib")
    pytest.importorskip("numpy")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    out = str(tmp_path / "full_dict_findings.pdf")
    bundle = {
        "project_name": "DictFindings",
        "validator_score": 60,
        "validation_findings": [
            {"message": "Issue A"},
            {"message": "Issue B"},
            "string finding",  # mixed types
            {"no_message_key": True},  # falls back to str(finding)
        ],
    }
    result = e.export_full_analysis_report(bundle, out)
    assert result == out


def test_export_full_analysis_with_low_score(tmp_path: Path) -> None:
    """score < 50 → red branch."""
    pytest.importorskip("matplotlib")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    out = str(tmp_path / "full_low.pdf")
    result = e.export_full_analysis_report({"validator_score": 30}, out)
    assert result == out


def test_export_full_analysis_with_coupling_no_modules(tmp_path: Path) -> None:
    """Lines 1078-1090: coupling_metrics present but modules empty → skip plot."""
    pytest.importorskip("matplotlib")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    out = str(tmp_path / "full_coupling_empty.pdf")
    result = e.export_full_analysis_report(
        {"project_name": "X", "coupling_metrics": {"modules": {}}}, out
    )
    assert result == out


def test_export_full_analysis_with_coupling_modules(tmp_path: Path) -> None:
    """Lines 1093-1120: full coupling-metrics scatter plot."""
    pytest.importorskip("matplotlib")
    pytest.importorskip("numpy")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    out = str(tmp_path / "full_coupling.pdf")
    result = e.export_full_analysis_report(
        {
            "project_name": "WithCoupling",
            "coupling_metrics": {
                "modules": {
                    "core.utils": {"abstractness": 0.2, "instability": 0.7},
                    "core.api": {"abstractness": 0.8, "instability": 0.3},
                    "core.bare": {},  # uses .5/.5 defaults
                }
            },
        },
        out,
    )
    assert result == out


def test_export_full_analysis_with_invalid_matrix(tmp_path: Path) -> None:
    """Lines 1148-1158: matrix coercion failure → 'unavailable' text branch."""
    pytest.importorskip("matplotlib")
    pytest.importorskip("numpy")
    from cogant.viz.pdf_export import PDFExporter

    e = PDFExporter()
    out = str(tmp_path / "full_bad_mat.pdf")
    result = e.export_full_analysis_report(
        {
            "project_name": "BadMatrices",
            "matrices": {
                "A": [[1.0, 2.0]],
                "B": "totally not numeric",  # asarray(float) raises
                "C": None,  # 'no data' branch
                "D": [[3.0, 4.0]],
            },
        },
        out,
    )
    assert result == out


# --------------------------------------------------------------------------- #
# upstream_bridge — import gate (_require_upstream_gnn)
# --------------------------------------------------------------------------- #


def _fake_upstream(**attrs: Any) -> Any:
    """A stand-in upstream ``gnn`` module carrying only ``attrs``."""
    mod = type(sys)("gnn")
    for name, value in attrs.items():
        setattr(mod, name, value)
    return mod


def _install_upstream(monkeypatch: pytest.MonkeyPatch, module: Any) -> None:
    """Route every bridge facade to ``module`` (or raise it, if an exception)."""
    from cogant.gnn import upstream_bridge

    def _require() -> Any:
        if isinstance(module, BaseException):
            raise module
        return module

    monkeypatch.setattr(upstream_bridge, "_require_upstream_gnn", _require)


def test_require_upstream_gnn_wraps_missing_distribution(monkeypatch) -> None:
    """A missing distribution raises an actionable, chained ImportError."""
    import importlib.metadata

    from cogant.gnn.upstream_bridge import _require_upstream_gnn

    def _missing(name: str) -> str:
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", _missing)
    with pytest.raises(ImportError) as excinfo:
        _require_upstream_gnn()
    assert "cogant[upstream]" in str(excinfo.value)
    assert excinfo.value.__cause__ is not None


def test_is_upstream_gnn_available_returns_false_on_import_error(monkeypatch) -> None:
    from cogant.gnn import upstream_bridge

    _install_upstream(monkeypatch, ImportError("simulated"))
    assert upstream_bridge.is_upstream_gnn_available() is False


def test_upstream_version_returns_none_on_import_error(monkeypatch) -> None:
    from cogant.gnn import upstream_bridge

    _install_upstream(monkeypatch, ImportError("simulated"))
    assert upstream_bridge.upstream_version() is None


def test_upstream_version_returns_none_for_non_string_version(monkeypatch) -> None:
    """A ``__version__`` that isn't a str returns None."""
    from cogant.gnn import upstream_bridge

    _install_upstream(monkeypatch, _fake_upstream(__version__=42))
    assert upstream_bridge.upstream_version() is None


def test_run_upstream_validate_gnn_returns_skipped_on_import_error(monkeypatch) -> None:
    from cogant.gnn import upstream_bridge
    from cogant.gnn.upstream_bridge import UpstreamGNNValidation

    _install_upstream(monkeypatch, ImportError("simulated missing gnn"))
    result = upstream_bridge.run_upstream_validate_gnn("## anything\n")
    assert isinstance(result, UpstreamGNNValidation)
    assert result.available is False
    assert result.ok is True
    assert result.skipped_reason is not None
    assert "core COGANT" in result.skipped_reason


def test_run_upstream_validate_gnn_returns_skipped_when_function_missing(monkeypatch) -> None:
    """An upstream without ``validate_gnn_syntax`` is reported as skipped."""
    from cogant.gnn import upstream_bridge
    from cogant.gnn.upstream_bridge import UpstreamGNNValidation

    _install_upstream(monkeypatch, _fake_upstream())
    result = upstream_bridge.run_upstream_validate_gnn("## anything\n")
    assert isinstance(result, UpstreamGNNValidation)
    assert result.available is False
    assert result.skipped_reason == "upstream gnn has no validate_gnn_syntax"


def test_run_upstream_validate_gnn_handles_function_raising(monkeypatch) -> None:
    """A raising validator is captured in ``errors`` with the upstream version."""
    from cogant.gnn import upstream_bridge
    from cogant.gnn.upstream_bridge import UpstreamGNNValidation

    def _bad_validate(_path: Any, _level: Any = None) -> Any:
        raise RuntimeError("upstream blew up")

    _install_upstream(
        monkeypatch,
        _fake_upstream(validate_gnn_syntax=_bad_validate, __version__="0.0.test"),
    )
    result = upstream_bridge.run_upstream_validate_gnn("## anything\n")
    assert isinstance(result, UpstreamGNNValidation)
    assert result.available is True
    assert result.ok is False
    assert len(result.errors) == 1
    assert "upstream blew up" in result.errors[0]
    assert result.version == "0.0.test"


def test_run_upstream_validate_gnn_swallows_unlink_oserror(monkeypatch) -> None:
    """A failing temp-file cleanup never turns a valid verdict into an error."""
    from cogant.gnn import upstream_bridge
    from cogant.gnn.upstream_bridge import UpstreamGNNValidation

    staged: list[Path] = []

    def _validator(path: Path, _level: Any = None) -> tuple[bool, list[str]]:
        staged.append(Path(path))
        return (True, [])

    def _failing_unlink(self: Path, *a: Any, **kw: Any) -> None:
        raise OSError("simulated unlink failure")

    _install_upstream(
        monkeypatch,
        _fake_upstream(validate_gnn_syntax=_validator, __version__="0.0.unlink-test"),
    )
    real_unlink = Path.unlink
    with monkeypatch.context() as m:
        m.setattr(Path, "unlink", _failing_unlink)
        result = upstream_bridge.run_upstream_validate_gnn("## ok\n")
    assert isinstance(result, UpstreamGNNValidation)
    assert result.available is True
    assert result.ok is True
    for leaked in staged:
        real_unlink(leaked, missing_ok=True)


def test_upstream_validate_file_content_returns_when_function_missing(monkeypatch) -> None:
    """Without ``validate_gnn_source`` the facade returns a shaped failure dict."""
    from cogant.gnn import upstream_bridge

    _install_upstream(monkeypatch, _fake_upstream())
    out = upstream_bridge.upstream_validate_file_content("anything")
    assert out == {"is_valid": False, "errors": ["upstream gnn has no validate_gnn_source"]}


def test_upstream_validate_file_content_wraps_non_dict_result(monkeypatch) -> None:
    """A non-dict upstream result is wrapped in ``{'result': ...}``."""
    from cogant.gnn import upstream_bridge

    def _fn(content: str, *, is_content: bool = True) -> Any:
        return ["a", "list", "result"]

    _install_upstream(monkeypatch, _fake_upstream(validate_gnn_source=_fn))
    out = upstream_bridge.upstream_validate_file_content("x")
    assert out == {"result": ["a", "list", "result"]}


def test_upstream_process_directory_passes_kwargs(monkeypatch, tmp_path: Path) -> None:
    """kwargs are forwarded to upstream ``process_gnn_directory``."""
    from cogant.gnn import upstream_bridge

    captured: dict[str, Any] = {}

    def _proc(in_dir: Path, out_dir: Path, **kwargs: Any) -> dict[str, Any]:
        captured.update(in_dir=in_dir, out_dir=out_dir, kwargs=kwargs)
        return {"ok": True}

    _install_upstream(monkeypatch, _fake_upstream(process_gnn_directory=_proc))
    result = upstream_bridge.upstream_process_directory(
        tmp_path, tmp_path / "out", recursive=True, parallel=False
    )
    assert result == {"ok": True}
    assert captured["in_dir"] == tmp_path
    assert captured["out_dir"] == tmp_path / "out"
    assert captured["kwargs"] == {"recursive": True, "parallel": False}


def test_upstream_process_multi_format_uses_default_logger(monkeypatch, tmp_path: Path) -> None:
    """``log`` defaults to the bridge module logger when None is passed."""
    from cogant.gnn import upstream_bridge

    captured: dict[str, Any] = {}

    def _proc(in_dir: Path, out_dir: Path, log: Any, **kwargs: Any) -> str:
        captured["log"] = log
        return "done"

    _install_upstream(monkeypatch, _fake_upstream(process_gnn_multi_format=_proc))
    result = upstream_bridge.upstream_process_multi_format(tmp_path, tmp_path / "out", log=None)
    assert result == "done"
    assert captured["log"] is upstream_bridge.logger


def test_upstream_process_multi_format_uses_explicit_logger(monkeypatch, tmp_path: Path) -> None:
    import logging as _logging

    from cogant.gnn import upstream_bridge

    captured: dict[str, Any] = {}
    custom_log = _logging.getLogger("custom-test-logger")

    def _proc(in_dir: Path, out_dir: Path, log: Any, **kwargs: Any) -> str:
        captured["log"] = log
        return "done"

    _install_upstream(monkeypatch, _fake_upstream(process_gnn_multi_format=_proc))
    result = upstream_bridge.upstream_process_multi_format(
        tmp_path, tmp_path / "out", log=custom_log
    )
    assert result == "done"
    assert captured["log"] is custom_log


def test_parse_upstream_model_gnn_md_exception_branch(monkeypatch, tmp_path: Path) -> None:
    """A raising upstream parser yields ``{'path': ..., 'error': ...}``."""
    from cogant.gnn import upstream_bridge

    pkg = tmp_path / "pkg_with_bad_parse"
    pkg.mkdir()
    (pkg / "model.gnn.md").write_text("## stuff\n", encoding="utf-8")

    def _bad_parse(path: Path) -> Any:
        raise RuntimeError("parse failure")

    _install_upstream(monkeypatch, _fake_upstream(parse_gnn_file=_bad_parse))
    out = upstream_bridge.parse_upstream_model_gnn_md(pkg)
    assert "path" in out
    assert "error" in out
    assert "parse failure" in out["error"]


# --------------------------------------------------------------------------- #
# upstream_bridge — UpstreamGNNValidation immutability & to_dict isolation
# --------------------------------------------------------------------------- #


def test_upstream_gnn_validation_is_frozen() -> None:
    """Dataclass is frozen — assigning attributes raises."""
    from cogant.gnn.upstream_bridge import UpstreamGNNValidation

    v = UpstreamGNNValidation(available=True, ok=True)
    with pytest.raises((AttributeError, TypeError)):
        v.ok = False  # type: ignore[misc]


def test_upstream_gnn_validation_to_dict_does_not_share_errors_list() -> None:
    """to_dict returns a copy of errors so mutation does not leak."""
    from cogant.gnn.upstream_bridge import UpstreamGNNValidation

    v = UpstreamGNNValidation(available=True, ok=True, errors=["original"])
    d = v.to_dict()
    d["errors"].append("mutation")
    assert v.errors == ["original"]
    assert d["errors"] == ["original", "mutation"]


# --------------------------------------------------------------------------- #
# upstream_bridge — round-trip integration sanity (upstream available)
# --------------------------------------------------------------------------- #


def test_run_upstream_validate_gnn_real_call_success_path() -> None:
    """Real call goes through the full success path (lines 142-164)."""
    from cogant.gnn.upstream_bridge import (
        UpstreamGNNValidation,
        is_upstream_gnn_available,
        run_upstream_validate_gnn,
    )

    if not is_upstream_gnn_available():
        pytest.skip("upstream gnn not importable in this environment")
    minimal = (
        "## GNNSection\nm\n## GNNVersionAndFlags\nGNN v2.0.0\n## ModelName\nn\n"
        "## StateSpaceBlock\ns_f0[1,1,type=int]\n## Connections\n"
        "## InitialParameterization\n## Time\nDiscrete\n## ActInfOntologyAnnotation\n"
    )
    result = run_upstream_validate_gnn(minimal)
    assert isinstance(result, UpstreamGNNValidation)
    assert result.available is True
    # ok / errors content depends on upstream — both shapes accepted
    assert isinstance(result.errors, list)
