import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from cogant.reverse.callable import MatrixFunctions
from cogant.reverse.matrices import render_matrices_module
from cogant.reverse.parser import parse_gnn
from cogant.reverse.planner import plan_package
from cogant.reverse.synthesizer import synthesize_package
from cogant.runtime.categorical import CategoricalModel, posterior, variational_free_energy
from cogant.runtime.loop import AgentRuntime

FENCED = """## ModelName
AggregateAxis
## StateSpaceBlock
s_f0[10,1,type=int]
o_m0[2,1,type=int]
u_c0[2,1,type=int]
## InitialParameterization
D_f0={ (1.0) }
B_f0=identity(10,10,2)
## State Space
```gnn-matrices
A[[rows=2][cols=1]]
0.25
0.75
B[[rows=1][cols=1][depth=2]]
# action=0
1.0
# action=1
1.0
C[[rows=2][cols=1]]
0.0
2.0
D[[rows=1][cols=1]]
1.0
```
"""


def test_authoritative_aggregate_fence_preserves_all_matrix_axes() -> None:
    model = parse_gnn(FENCED)
    assert model.matrix_source == "fenced"
    assert not model.degraded
    assert model.diagnostics == []
    assert (model.n_states, model.n_obs, model.n_actions) == (1, 2, 2)
    functions = MatrixFunctions(model)
    assert functions.A == [[0.25], [0.75]]
    assert functions.B == [[[1.0, 1.0]]]
    assert functions.C == [0.0, 2.0]
    assert functions.D == [1.0]
    assert model.cardinalities["s_f0"] == 10


def test_generated_kernel_runs_without_cogant_and_matches_independent_score(tmp_path: Path) -> None:
    model = parse_gnn(FENCED)
    generated = tmp_path / "matrices.py"
    generated.write_text(render_matrices_module(model))
    program = (
        "import json,runpy,sys; m=runpy.run_path(sys.argv[1]); "
        "print(json.dumps({'scores':[m['expected_free_energy']([1.0],a) for a in range(2)],"
        "'action':m['best_action']([1.0])}))"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", program, str(generated)],
        capture_output=True,
        text=True,
        check=True,
    )
    actual = json.loads(result.stdout)
    log_z = math.log1p(math.exp(2))
    expected = log_z - 0.75 * 2
    assert actual["scores"] == pytest.approx([expected, expected])
    assert actual["action"] == 0


def test_filtering_vfe_and_learning_use_current_posterior() -> None:
    matrices = {
        "A": [[0.8, 0.2], [0.2, 0.8]],
        "B": [[[0.0], [1.0]], [[1.0], [0.0]]],
        "C": [0.0, 0.0],
        "D": [0.75, 0.25],
    }
    runtime = AgentRuntime.from_matrices_dict(matrices)
    result, _ = runtime.run_episode_with_logging([0])
    q = [12 / 13, 1 / 13]
    step = result.steps[0]
    assert step.posterior == pytest.approx(q)
    assert step.state_dist == pytest.approx(list(reversed(q)))
    assert step.free_energy == pytest.approx(-math.log(0.65))
    assert result.final_posterior == pytest.approx(q)
    assert result.obs_state_counts[0] == pytest.approx(q)
    second = runtime.step(step.state_dist, 0, t=1)
    assert second.posterior == pytest.approx([0.25, 0.75])
    assert second.free_energy == pytest.approx(-math.log(3.2 / 13))
    runtime.update_A_from_counts([[9.0, 1.0], [1.0, 3.0]], learning_rate=1)
    assert runtime.A == [[0.9, 0.25], [0.1, 0.75]]


def test_policy_sequence_uses_each_action_and_finite_horizon() -> None:
    matrix = CategoricalModel(
        [[1.0, 0.0], [0.0, 1.0]],
        [[[1.0, 0.0], [0.0, 1.0]], [[0.0, 1.0], [1.0, 0.0]]],
        [0.0, 2.0],
        [1.0, 0.0],
    )
    log_z = math.log1p(math.exp(2))
    assert matrix.score([1.0, 0.0], [0, 1]) == pytest.approx(2 * log_z - 2)
    assert matrix.score([1.0, 0.0], [1, 0]) == pytest.approx(2 * log_z - 4)
    with pytest.raises(ValueError, match="policy"):
        matrix.score([1.0, 0.0], [])


def test_impossible_support_is_not_epsilon_smoothed() -> None:
    a = [[1.0, 0.0], [0.0, 1.0]]
    assert math.isinf(variational_free_energy([0.5, 0.5], [0.5, 0.5], a, [1.0, 0.0]))
    with pytest.raises(ValueError, match="evidence"):
        posterior([0.0, 1.0], a, 0)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("0.25\n0.75", "0.25", "exactly 2 rows"),
        ("# action=1\n1.0", "# action=0\n1.0", "duplicate B action"),
        ("# action=1\n1.0", "", "missing declared action"),
        ("# action=1\n1.0", "# action=1\n1.0\n1.0", "exactly 1 rows"),
        ("D[[rows=1][cols=1]]\n1.0", "", "missing D"),
        (
            "D[[rows=1][cols=1]]\n1.0",
            "D[[rows=1][cols=1]]\n1.0\nD[[rows=1]]\n1.0",
            "duplicate matrix",
        ),
        ("0.25\n0.75", "nan\n0.75", "finite numeric"),
        ("A[[rows=2][cols=1]]", "A[[rows=2][cols=2]]", "2 finite numeric"),
        ("# action=0", "# action=-1", "invalid B action"),
    ],
)
def test_corrupt_authoritative_fences_fail_before_execution(
    old: str, new: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        parse_gnn(FENCED.replace(old, new))


def test_duplicate_authoritative_fences_are_rejected() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        parse_gnn(FENCED + FENCED)


def test_unterminated_authoritative_fence_is_rejected() -> None:
    with pytest.raises(ValueError, match="unterminated"):
        parse_gnn(FENCED.removesuffix("```\n"))


def test_generated_driver_filters_then_executes_selected_action(tmp_path: Path) -> None:
    model = parse_gnn(FENCED)
    model.A = [[1.0, 0.0], [0.0, 1.0]]
    model.B = [[[1.0, 0.0], [0.0, 1.0]], [[0.0, 1.0], [1.0, 0.0]]]
    model.C = [0.0, 10.0]
    model.D = [0.8, 0.2]
    model.cardinalities = {"s_f0": 2, "o_m0": 2, "u_c0": 2}
    plan = plan_package(model)
    package = synthesize_package(plan, model, tmp_path)
    program = (
        "import importlib,json,sys; sys.path.insert(0,sys.argv[1]); "
        "main=importlib.import_module(sys.argv[2]+'.main'); "
        "result=main.advance_once(main.State(),observation=0); "
        "print(json.dumps(result.as_distribution()))"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", program, str(package.parent), package.name],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout) == [0.0, 1.0]
