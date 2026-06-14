"""Composability integration tests for cogant.

Verifies that every major cogant module is independently importable and
instantiable, and that the reverse + runtime pipeline works end-to-end
without the full ingest/graph/translate/statespace/markov chain.
"""

from __future__ import annotations

import math
import types
from pathlib import Path


def test_every_module_importable_and_instantiable() -> None:
    """Every major cogant module can be imported and its key class accessed."""
    from cogant.cache.hasher import hash_file
    from cogant.cache.store import CacheStore, get_cache_dir
    from cogant.observability.logging import get_logger
    from cogant.observability.metrics import MetricsRegistry
    from cogant.pipeline.dag import PipelineDAG, Stage
    from cogant.plugins.registry import PluginRegistry
    from cogant.reverse.callable import MatrixFunctions
    from cogant.reverse.parser import ReverseGNNModel, parse_gnn
    from cogant.reverse.planner import plan_package
    from cogant.reverse.synthesizer import synthesize_package
    from cogant.runtime.config import AgentConfig
    from cogant.runtime.loop import AgentRuntime
    from cogant.schema.detector import detect_version
    from cogant.schema.versions import CURRENT_GNN_VERSION
    from cogant.translate.dsl import compile_ruleset, load_rules_from_dict

    # Each class/function is a real object, not None
    assert CacheStore is not None
    assert get_cache_dir is not None
    assert hash_file is not None
    assert PipelineDAG is not None
    assert Stage is not None
    assert CURRENT_GNN_VERSION == "2.0.0"
    assert detect_version is not None
    assert PluginRegistry is not None
    assert load_rules_from_dict is not None
    assert compile_ruleset is not None
    assert MetricsRegistry is not None
    assert get_logger is not None
    assert parse_gnn is not None
    assert ReverseGNNModel is not None
    assert plan_package is not None
    assert synthesize_package is not None
    assert MatrixFunctions is not None
    assert AgentRuntime is not None
    assert AgentConfig is not None

    # Instantiate where possible (no side-effects)
    cfg = AgentConfig()
    assert cfg.max_steps == 100

    registry = PluginRegistry()
    assert registry is not None

    metrics = MetricsRegistry()
    assert metrics is not None

    logger = get_logger("test_composability")
    assert logger is not None


def test_standalone_gnn_to_agent() -> None:
    """Construct ReverseGNNModel -> plan -> MatrixFunctions -> AgentRuntime -> run_n_steps.

    Uses: reverse.parser, reverse.planner, reverse.callable,
          runtime.loop, runtime.config
    Does NOT use: ingest, graph, translate, statespace, markov
    """
    from cogant.reverse.callable import MatrixFunctions
    from cogant.reverse.parser import ReverseGNNModel
    from cogant.reverse.planner import plan_package
    from cogant.runtime.config import AgentConfig
    from cogant.runtime.loop import AgentRuntime

    # 1. Construct a 3-state POMDP model directly
    model = ReverseGNNModel(
        model_name="test_pomdp",
        raw_model_name="TestPOMDP",
        hidden_states=["s_f0", "s_f1", "s_f2"],
        observations=["o_m0", "o_m1", "o_m2"],
        actions=["u_c0", "u_c1"],
        A=[
            [0.8, 0.1, 0.1],
            [0.1, 0.8, 0.1],
            [0.1, 0.1, 0.8],
        ],
        B=[
            [[1.0, 0.0], [0.0, 0.5], [0.0, 0.5]],
            [[0.0, 0.5], [1.0, 0.0], [0.0, 0.5]],
            [[0.0, 0.5], [0.0, 0.5], [1.0, 0.0]],
        ],
        C=[1.0, 0.0, -1.0],
        D=[0.4, 0.3, 0.3],
    )
    assert model.model_name == "test_pomdp"
    assert model.n_states == 3
    assert model.n_obs == 3

    # 2. Plan (verify planning works without synthesis)
    plan = plan_package(model)
    assert plan.package_name, "Plan must have a package name"
    assert len(plan.nodes) > 0, "Plan must have at least one node"

    # 3. Build callable matrix functions (skip file synthesis)
    mf = MatrixFunctions(model)
    assert callable(mf.likelihood)
    assert callable(mf.transition)
    assert callable(mf.preference_score)

    # 4. Create runtime -- MatrixFunctions stores matrices as private attrs
    #    so we wrap with a namespace exposing public A, B, C, D + callables
    ns = types.SimpleNamespace(
        A=mf._A,
        B=mf._B,
        C=mf._C,
        D=mf._D,
        likelihood=mf.likelihood,
        transition=mf.transition,
        preference_score=mf.preference_score,
    )
    rt = AgentRuntime(ns)

    # 5. Run 5 steps
    steps = rt.run_n_steps(5)
    assert len(steps) == 5

    for i, step in enumerate(steps):
        assert step.t == i
        assert math.isfinite(step.free_energy)
        assert abs(sum(step.state_dist) - 1.0) < 1e-6
        assert 0 <= step.obs
        assert 0 <= step.action

    # 6. Run until convergence with tight threshold
    cfg = AgentConfig(max_steps=20, convergence_threshold=1e-4)
    conv_steps = rt.run_until_convergence(cfg=cfg)
    assert len(conv_steps) >= 1
    assert len(conv_steps) <= 20

    # 7. Verify free energy is finite throughout
    for step in conv_steps:
        assert math.isfinite(step.free_energy)


def test_cache_and_runtime_roundtrip(tmp_path: Path) -> None:
    """CacheStore can persist and retrieve matrices data used by AgentRuntime.

    Uses: cache.store, cache.hasher, runtime.loop (no reverse, no pipeline).
    """
    import json

    from cogant.cache.hasher import hash_file
    from cogant.cache.store import CacheKey, CacheStore
    from cogant.runtime.loop import AgentRuntime

    # Build a minimal matrices dict
    matrices_dict = {
        "A": [[0.8, 0.2], [0.2, 0.8]],
        "B": [[[1.0, 0.0], [0.0, 1.0]], [[0.0, 1.0], [1.0, 0.0]]],
        "C": [1.0, -1.0],
        "D": [0.5, 0.5],
    }

    # Write to a file in tmp_path, get its content hash
    data_file = tmp_path / "matrices.json"
    data_file.write_text(json.dumps(matrices_dict))
    content_hash = hash_file(data_file)

    # Store via CacheStore with proper CacheKey
    store = CacheStore(cache_dir=tmp_path / ".cache")
    key = CacheKey(
        repo_path=str(tmp_path),
        content_hash=content_hash,
        cogant_version="test",
    )
    store.put(key, {"matrices": matrices_dict})

    # Retrieve and reconstruct
    entry = store.get(key)
    assert entry is not None
    recovered = entry.stage_results["matrices"]

    rt = AgentRuntime.from_matrices_dict(recovered)
    steps = rt.run_n_steps(3)
    assert len(steps) == 3
    for step in steps:
        assert math.isfinite(step.free_energy)


def test_schema_detect_and_parse_compose() -> None:
    """Schema detection + parse_gnn compose without error on zoo model.

    Uses: schema.detector, reverse.parser (no translate, no pipeline).
    """
    from cogant.reverse.parser import parse_gnn
    from cogant.schema.detector import detect_version

    gnn_path = (
        Path(__file__).resolve().parents[2] / "examples" / "zoo" / "12_full_pomdp" / "model.gnn.md"
    )
    gnn_text = gnn_path.read_text()

    # Detect version
    version = detect_version(gnn_text)
    assert version, "Version detection must return a non-empty string"

    # Parse independently -- note: this GNN format populates cardinalities
    # and annotations but not hidden_states list directly
    model = parse_gnn(gnn_path)
    assert model.model_name == "full_pomdp"
    assert "s_hidden" in model.cardinalities
    assert model.cardinalities["s_hidden"] == 5
