"""Preference derivatives survive parsed-model and standalone-code boundaries."""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from cogant.reverse.callable import MatrixFunctions
from cogant.reverse.matrices import render_matrices_module
from cogant.reverse.parser import parse_gnn

SOURCE = """## ModelName
PreferenceSensitivity
## StateSpaceBlock
s[2,1,type=float]
o[2,1,type=float]
u[2,1,type=int]
## State Space
```gnn-matrices
A[[rows=2][cols=2]]
1.0 0.0
0.0 1.0
B[[rows=2][cols=2][depth=2]]
# action=0
1.0 0.0
0.0 1.0
# action=1
0.0 1.0
1.0 0.0
C[[rows=2][cols=1]]
0.0
1.0986122886681098
D[[rows=2][cols=1]]
1.0
0.0
```
"""


def test_parsed_gnn_exposes_fixed_policy_preference_gradient() -> None:
    # Given: source bytes declaring a complete identity/swap model.
    functions = MatrixFunctions.from_gnn_text(SOURCE)
    # When: requesting sensitivity through the public parsed-model facade.
    gradient = functions.score_preference_gradient([1.0, 0.0], [1, 0])
    # Then: both predicted outcomes favor state one, against 1/4, 3/4 preferences.
    assert gradient == pytest.approx([0.5, -0.5])


def test_generated_gradient_executes_with_site_packages_disabled(tmp_path: Path) -> None:
    # Given: a generated matrix module, independent of the installed package.
    generated = tmp_path / "matrices.py"
    generated.write_text(render_matrices_module(parse_gnn(SOURCE)), encoding="utf-8")
    program = (
        "import json,runpy,sys; m=runpy.run_path(sys.argv[1]); "
        "print(json.dumps(m['score_preference_gradient']([1.0,0.0],[1,0])))"
    )
    # When: executing the public generated helper in isolated stdlib-only Python.
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", program, str(generated)],
        capture_output=True,
        text=True,
        check=True,
    )
    # Then: the generated derivative matches independent arithmetic, with no NaN.
    gradient = json.loads(result.stdout)
    assert gradient == pytest.approx([0.5, -0.5])
    assert all(math.isfinite(value) for value in gradient)
