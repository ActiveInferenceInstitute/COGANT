"""Reverse parsing refuses matrix allocations sized by untrusted integers.

``parse_gnn`` runs on GNN text supplied to the ``/reverse`` endpoint.  A
~100-byte document can declare ``identity(20000,20000,10)``, a fenced
``B[[rows=R][cols=C][depth=D]]`` header, or factor cardinalities whose
Cartesian product drives the projected D/A/B tensors.  Each must be checked
against ``MAX_REVERSE_MATRIX_ELEMENTS`` *before* the nested lists are built,
and rejected with a :class:`ReverseModelError` (a ``ValueError``, mapped to
HTTP 422) instead of exhausting memory.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from cogant.reverse import parser as parser_module
from cogant.reverse.idempotency import ROUNDTRIP_STATUS_FAILED, verify_repo_roundtrip
from cogant.reverse.parser import ReverseModelError, parse_gnn

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
CALCULATOR = EXAMPLES / "control_positive" / "calculator"

SMALL_BUDGET = 10_000


@pytest.fixture
def small_budget(monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setattr(parser_module, "MAX_REVERSE_MATRIX_ELEMENTS", SMALL_BUDGET, raising=False)
    return SMALL_BUDGET


def _identity_document(rows: int, cols: int, depth: int) -> str:
    return (
        "## ModelName\nx\n\n## StateSpaceBlock\n\n"
        f"## InitialParameterization\nB_f0=identity({rows},{cols},{depth})\n"
    )


def _fenced_b_document(rows: int, cols: int, depth: int) -> str:
    return (
        f"## ModelName\nx\n\n```gnn-matrices\nB[[rows={rows}][cols={cols}][depth={depth}]]\n```\n"
    )


def test_identity_shorthand_over_budget_is_rejected(small_budget: int) -> None:
    with pytest.raises(ReverseModelError, match="identity"):
        parse_gnn(_identity_document(200, 200, 1))


def test_fenced_transition_header_over_budget_is_rejected(small_budget: int) -> None:
    with pytest.raises(ReverseModelError, match="B"):
        parse_gnn(_fenced_b_document(200, 200, 1))


def test_cartesian_factor_projection_over_budget_is_rejected(small_budget: int) -> None:
    text = (
        "## ModelName\nx\n\n## StateSpaceBlock\n"
        "s_f0[30,1,type=int]\ns_f1[30,1,type=int]\n"
        "o_m0[2,1,type=int]\nu_c0[2,1,type=int]\n\n"
        "## InitialParameterization\nC_m0={ (0.0, 1.0) }\n"
    )

    with pytest.raises(ReverseModelError, match="exceeds"):
        parse_gnn(text)


def test_single_entry_prior_expansion_over_budget_is_rejected(small_budget: int) -> None:
    text = (
        "## ModelName\nx\n\n## StateSpaceBlock\ns_f0[200,1,type=int]\n\n"
        "```gnn-matrices\n"
        "B[[rows=1][cols=1][depth=1]]\n  # action=0\n  1\n\n"
        "D[[rows=1]]\n  1\n```\n"
    )

    with pytest.raises(ReverseModelError, match="exceeds"):
        parse_gnn(text)


def test_models_within_budget_still_parse(small_budget: int) -> None:
    model = parse_gnn(_identity_document(10, 10, 2))
    assert model.model_name == "x"

    fenced = parse_gnn(
        "## ModelName\nx\n\n## StateSpaceBlock\ns_f0[2,1,type=int]\n\n"
        "```gnn-matrices\nB[[rows=2][cols=2][depth=1]]\n  # action=0\n  1 0\n  0 1\n```\n"
    )
    assert fenced.B == [[[1.0], [0.0]], [[0.0], [1.0]]]


@pytest.mark.parametrize(
    "text",
    [
        _identity_document(20_000, 20_000, 10),
        _fenced_b_document(100_000, 100_000, 10),
    ],
    ids=["identity", "fenced-header"],
)
def test_default_budget_rejects_tiny_hostile_documents_quickly(text: str) -> None:
    assert len(text.encode("utf-8")) < 200
    started = time.perf_counter()

    with pytest.raises(ReverseModelError, match="MAX_REVERSE_MATRIX_ELEMENTS"):
        parse_gnn(text)

    assert time.perf_counter() - started < 5.0


def test_reverse_endpoint_helper_maps_budget_rejection_to_value_error() -> None:
    server_app = pytest.importorskip("cogant.server.app")
    text = (
        "## ModelName\nx\n\n## StateSpaceBlock\n\n"
        "## InitialParameterization\nB_f0=identity(20000,20000,10)\n"
    )

    with pytest.raises(ValueError, match="MAX_REVERSE_MATRIX_ELEMENTS"):
        server_app._synthesize_zip_from_gnn_text(text)


def test_repo_roundtrip_reports_budget_rejection_as_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # With a 5-cell budget the reverse parser refuses the calculator's own
    # forward bundle (its fenced B block alone is 1 x 1 x 6 cells).
    monkeypatch.setattr(parser_module, "MAX_REVERSE_MATRIX_ELEMENTS", 5)

    result = verify_repo_roundtrip(CALCULATOR, output_dir=tmp_path)

    assert result.roundtrip_status == ROUNDTRIP_STATUS_FAILED
    assert any("MAX_REVERSE_MATRIX_ELEMENTS" in error for error in result.errors)
    assert result.original_roles
