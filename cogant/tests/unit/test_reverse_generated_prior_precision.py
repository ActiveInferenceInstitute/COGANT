"""Generated ``matrices.py`` must accept its own prior.

The renderer used to round every matrix entry to 6 decimals while the
generated ``likelihood``/``transition`` helpers require a state distribution
to sum to 1.0 within 1e-6.  A uniform prior over 3 states renders as
``[0.333333, 0.333333, 0.333333]`` (sum 0.999999), so the synthesized
package's own ``main()`` and smoke tests raised "state distribution must sum
to 1.0" for every such model (e.g. the async_service, cli_tool and
notebook_module control-positive fixtures).
"""

from __future__ import annotations

import importlib
import math
import sys
from pathlib import Path

import pytest

from cogant.reverse.matrices import render_matrices_module
from cogant.reverse.parser import ReverseGNNModel
from cogant.reverse.planner import plan_package
from cogant.reverse.synthesizer import synthesize_package


def _thirds_model(name: str = "thirds_prior") -> ReverseGNNModel:
    third = 1.0 / 3.0
    return ReverseGNNModel(
        model_name=name,
        hidden_states=["s_f0"],
        observations=["o_m0"],
        actions=["u_c0"],
        cardinalities={"s_f0": 3, "o_m0": 2, "u_c0": 1},
        A=[[2 / 3, 1 / 3, 1 / 7], [1 / 3, 2 / 3, 6 / 7]],
        B=[[[1.0 if row == col else 0.0] for col in range(3)] for row in range(3)],
        C=[0.0, 1.0],
        D=[third, third, third],
    )


def test_rendered_prior_is_accepted_by_generated_helpers() -> None:
    namespace: dict[str, object] = {}
    exec(compile(render_matrices_module(_thirds_model()), "matrices.py", "exec"), namespace)

    prior = namespace["INITIAL_STATE_PRIOR"]
    assert isinstance(prior, list)
    assert math.isclose(sum(prior), 1.0, abs_tol=1e-9)
    likelihood = namespace["likelihood"]
    transition = namespace["transition"]
    assert callable(likelihood) and callable(transition)
    assert len(likelihood(prior)) == 2
    assert len(transition(prior, 0)) == 3
    for column in range(3):
        a_matrix = namespace["A"]
        assert isinstance(a_matrix, list)
        assert math.isclose(sum(row[column] for row in a_matrix), 1.0, abs_tol=1e-9)


def test_synthesized_package_main_runs_with_thirds_prior(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = _thirds_model("thirds_prior_pkg")
    package = synthesize_package(plan_package(model), model, tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    try:
        main_module = importlib.import_module(f"{package.name}.main")
        final_state = main_module.main(num_steps=3)
    finally:
        for name in [mod for mod in sys.modules if mod.split(".")[0] == package.name]:
            del sys.modules[name]

    assert final_state is not None
