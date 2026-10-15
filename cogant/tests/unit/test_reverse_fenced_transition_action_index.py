"""Fenced ``gnn-matrices`` B blocks with an out-of-range ``# action=k`` header.

The fenced B reader indexed ``B[row][col][k]`` with the action number taken
from the text, so ``# action=5`` under ``[depth=2]`` raised ``IndexError``.
That escaped the reverse CLI's ``(OSError, ValueError)`` handler as a
traceback and turned ``/reverse`` into a 500 instead of a 422.
"""

from __future__ import annotations

import pytest

from cogant.reverse.parser import ReverseModelError, parse_gnn

OUT_OF_RANGE_ACTION = """\
## ModelName
x

## StateSpaceBlock
s_f0[2,1,type=int]

```gnn-matrices
B[[rows=2][cols=2][depth=2]]
  # action=0
  1 0
  0 1
  # action=5
  0 1
  1 0
```
"""


def test_out_of_range_action_header_is_a_model_error() -> None:
    with pytest.raises(ReverseModelError, match="action=5"):
        parse_gnn(OUT_OF_RANGE_ACTION)


def test_reverse_endpoint_helper_rejects_out_of_range_action_as_value_error() -> None:
    server_app = pytest.importorskip("cogant.server.app")
    text = OUT_OF_RANGE_ACTION.replace(
        "```gnn-matrices", "## InitialParameterization\n\n```gnn-matrices"
    )

    with pytest.raises(ValueError, match="action=5"):
        server_app._synthesize_zip_from_gnn_text(text)


def test_in_range_action_headers_still_fill_their_slices() -> None:
    text = OUT_OF_RANGE_ACTION.replace("# action=5", "# action=1")
    text = text.replace(
        "\n```\n",
        "\nA[[rows=2][cols=2]]\n1 0\n0 1\nC[[rows=2]]\n0\n0\nD[[rows=2]]\n0.5\n0.5\n```\n",
    )
    model = parse_gnn(text)

    assert model.B == [[[1.0, 0.0], [0.0, 1.0]], [[0.0, 1.0], [1.0, 0.0]]]
