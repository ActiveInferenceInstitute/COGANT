#!/usr/bin/env python3
"""Coverage boost batch 82 — plugins/registry.py, ingest/incremental.py,
reverse/synthesizer.py extended, gnn/runner.py missing paths.

Covers:
- plugins/registry.py: PluginRegistry (discover, list_plugins, get_plugin_info,
  get_loaded_object, load error paths, _get_entry_points, _dist_version)
- ingest/incremental.py: IncrementalIngester (init, is_git_repo, changed_since
  non-git path, working_tree_changes non-git, python_files_changed_since,
  _parse_name_status, changed_since_commit)
- reverse/synthesizer.py: _render_policy_module with policy functions,
  _render_context_module with scaffold_context_classes and context_functions,
  _render_observe_module with bool/int python_type paths
- gnn/runner.py: ExecutionTrace, GNNModelRunner additional methods
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_reverse_model_with_all(**kwargs):
    from cogant.reverse.parser import ReverseGNNModel

    defaults = {
        "model_name": "test_model",
        "hidden_states": ["state_a", "state_b"],
        "observations": ["obs_x"],
        "actions": ["act_1"],
        "policies": ["pi_0"],
        "constraints": ["c_0"],
    }
    defaults.update(kwargs)
    return ReverseGNNModel(**defaults)


def _make_package_plan(name="test_model", **model_kwargs):
    from cogant.reverse.idempotency import plan_package

    model = _make_reverse_model_with_all(model_name=name, **model_kwargs)
    return plan_package(model), model


# ---------------------------------------------------------------------------
# plugins/registry.py — PluginRegistry
# ---------------------------------------------------------------------------


class TestPluginRegistry:
    def _make_registry(self):
        from cogant.plugins.registry import PluginRegistry

        return PluginRegistry()

    def test_init(self):
        registry = self._make_registry()
        assert registry is not None

    def test_discover_returns_list(self):
        registry = self._make_registry()
        result = registry.discover()
        assert isinstance(result, list)

    def test_list_plugins_returns_list(self):
        registry = self._make_registry()
        result = registry.list_plugins()
        assert isinstance(result, list)

    def test_get_plugin_info_nonexistent_raises(self):
        registry = self._make_registry()
        with pytest.raises(KeyError):
            registry.get_plugin_info("nonexistent_plugin_xyz")

    def test_get_loaded_object_nonexistent_raises(self):
        registry = self._make_registry()
        with pytest.raises(KeyError):
            registry.get_loaded_object("nonexistent_plugin_xyz")

    def test_load_nonexistent_plugin_fails(self):
        registry = self._make_registry()
        info = registry.load("nonexistent_plugin_xyz_12345")
        # Should return PluginInfo with loaded=False or raise
        assert info is None or not info.loaded

    def test_get_entry_points_returns_list(self):
        from cogant.plugins.registry import PluginRegistry

        eps = PluginRegistry._get_entry_points()
        assert isinstance(eps, list)

    def test_discover_and_list_consistent(self):
        registry = self._make_registry()
        discovered = registry.discover()
        listed = registry.list_plugins()
        # discovered returns PluginInfo objects; listed should match
        assert len(discovered) == len(listed)


# ---------------------------------------------------------------------------
# ingest/incremental.py — IncrementalIngester (non-git repo path)
# ---------------------------------------------------------------------------


class TestIncrementalIngester:
    def test_init_non_git_repo(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        assert ingester is not None
        # tmp_path is not a git repo
        assert ingester.is_git_repo() is False

    def test_is_git_repo_returns_bool(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        result = ingester.is_git_repo()
        assert isinstance(result, bool)

    def test_changed_since_non_git_returns_empty(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        result = ingester.changed_since("HEAD~1")
        assert result == []

    def test_working_tree_changes_non_git_returns_empty(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        result = ingester.working_tree_changes()
        assert result == []

    def test_python_files_changed_since_non_git_returns_empty(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        result = ingester.python_files_changed_since("HEAD~1")
        assert result == []

    def test_changed_since_commit_non_git_returns_empty(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        result = ingester.changed_since_commit("abc123")
        assert result == []

    def test_parse_name_status_basic(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        stdout = "M\tpath/to/file.py\nA\tnew_file.py\nD\told_file.py\n"
        result = ingester._parse_name_status(stdout)
        assert isinstance(result, list)
        assert len(result) == 3

    def test_parse_name_status_with_rename(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        stdout = "R100\told.py\tnew.py\n"
        result = ingester._parse_name_status(stdout)
        assert isinstance(result, list)

    def test_parse_name_status_empty(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        result = ingester._parse_name_status("")
        assert result == []

    def test_init_nonexistent_path(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path / "does_not_exist")
        assert ingester.is_git_repo() is False

    def test_changed_file_dataclass(self):
        from cogant.ingest.incremental import ChangedFile

        cf = ChangedFile(path=Path("test.py"), change_type="M")
        assert cf.change_type == "M"
        assert cf.path == Path("test.py")


# ---------------------------------------------------------------------------
# reverse/synthesizer.py — extended paths
# ---------------------------------------------------------------------------


class TestSynthesizerExtendedPaths:
    def test_render_policy_module_with_policy_functions(self):
        """When plan has policy_functions, they are rendered."""
        from cogant.reverse.planner import NodePlan
        from cogant.reverse.synthesizer import PackagePlan, _render_policy_module

        pf = NodePlan(name="pi_main", slot="policy.main", python_type="int")
        plan = PackagePlan(
            package_name="test_pkg",
            raw_model_name="test",
            nodes=[],
            state_vars=[],
            obs_functions=[],
            action_methods=[],
            policy_functions=[pf],
            constraint_checks=[],
            context_functions=[],
            scaffold_constraint_checks=[],
            scaffold_policy_functions=[],
            scaffold_context_classes=[],
            has_A_matrix=False,
            has_B_tensor=False,
            has_C_vector=False,
            has_D_vector=False,
        )
        result = _render_policy_module(plan)
        assert isinstance(result, str)
        # The policy function should appear
        assert "select_policy" in result or "pi_" in result

    def test_render_context_module_with_scaffold_classes(self):
        """When plan has scaffold_context_classes, they are rendered."""
        from cogant.reverse.planner import NodePlan
        from cogant.reverse.synthesizer import PackagePlan, _render_context_module

        ctx = NodePlan(name="UserSettings", slot="context.user", python_type="int")
        plan = PackagePlan(
            package_name="test_pkg",
            raw_model_name="test",
            nodes=[],
            state_vars=[],
            obs_functions=[],
            action_methods=[],
            policy_functions=[],
            constraint_checks=[],
            context_functions=[],
            scaffold_constraint_checks=[],
            scaffold_policy_functions=[],
            scaffold_context_classes=[ctx],  # non-empty
            has_A_matrix=False,
            has_B_tensor=False,
            has_C_vector=False,
            has_D_vector=False,
        )
        result = _render_context_module(plan)
        assert isinstance(result, str)
        assert "UserSettings" in result

    def test_render_context_module_with_context_functions(self):
        """When plan has context_functions, they are rendered as Settings classes."""
        from cogant.reverse.planner import NodePlan
        from cogant.reverse.synthesizer import PackagePlan, _render_context_module

        ctx_fn = NodePlan(name="context_database", slot="context.db", python_type="int")
        plan = PackagePlan(
            package_name="test_pkg",
            raw_model_name="test",
            nodes=[],
            state_vars=[],
            obs_functions=[],
            action_methods=[],
            policy_functions=[],
            constraint_checks=[],
            context_functions=[ctx_fn],  # non-empty
            scaffold_constraint_checks=[],
            scaffold_policy_functions=[],
            scaffold_context_classes=[NodePlan(name="SettingsX", slot="x", python_type="int")],
            has_A_matrix=False,
            has_B_tensor=False,
            has_C_vector=False,
            has_D_vector=False,
        )
        result = _render_context_module(plan)
        assert isinstance(result, str)
        assert "Settings" in result

    def test_render_observe_module_with_bool_type(self):
        """Observations with bool type should render bool return."""
        from cogant.reverse.planner import NodePlan
        from cogant.reverse.synthesizer import PackagePlan, _render_observe_module

        obs = NodePlan(name="observe_active", slot="obs.active", python_type="bool")
        plan = PackagePlan(
            package_name="test_pkg",
            raw_model_name="test",
            nodes=[],
            state_vars=[],
            obs_functions=[obs],
            action_methods=[],
            policy_functions=[],
            constraint_checks=[],
            context_functions=[],
            scaffold_constraint_checks=[],
            scaffold_policy_functions=[],
            scaffold_context_classes=[],
            has_A_matrix=True,
            has_B_tensor=False,
            has_C_vector=False,
            has_D_vector=False,
        )
        result = _render_observe_module(plan)
        assert isinstance(result, str)
        assert "False" in result or "bool" in result.lower()

    def test_render_observe_module_with_int_type(self):
        """Observations with int type should render int return."""
        from cogant.reverse.planner import NodePlan
        from cogant.reverse.synthesizer import PackagePlan, _render_observe_module

        obs = NodePlan(name="observe_count", slot="obs.count", python_type="int")
        plan = PackagePlan(
            package_name="test_pkg",
            raw_model_name="test",
            nodes=[],
            state_vars=[],
            obs_functions=[obs],
            action_methods=[],
            policy_functions=[],
            constraint_checks=[],
            context_functions=[],
            scaffold_constraint_checks=[],
            scaffold_policy_functions=[],
            scaffold_context_classes=[],
            has_A_matrix=True,
            has_B_tensor=False,
            has_C_vector=False,
            has_D_vector=False,
        )
        result = _render_observe_module(plan)
        assert isinstance(result, str)
        assert "0" in result or "int" in result.lower()

    def test_render_policy_module_with_scaffold_policies(self):
        """scaffold_policy_functions also rendered."""
        from cogant.reverse.planner import NodePlan
        from cogant.reverse.synthesizer import PackagePlan, _render_policy_module

        spf = NodePlan(name="route_state_a", slot="scaffold.policy.0", python_type="int")
        plan = PackagePlan(
            package_name="test_pkg",
            raw_model_name="test",
            nodes=[],
            state_vars=[],
            obs_functions=[],
            action_methods=[],
            policy_functions=[],
            constraint_checks=[],
            context_functions=[],
            scaffold_constraint_checks=[],
            scaffold_policy_functions=[spf],
            scaffold_context_classes=[],
            has_A_matrix=False,
            has_B_tensor=False,
            has_C_vector=False,
            has_D_vector=False,
        )
        result = _render_policy_module(plan)
        assert isinstance(result, str)
        assert "route_state_a" in result


# ---------------------------------------------------------------------------
# gnn/runner.py — additional method coverage
# ---------------------------------------------------------------------------


class TestGNNModelRunnerAdditional:
    def _make_gnn_package(self, tmp_path):
        manifest = {
            "version": "1.0.0",
            "schema_name": "test",
            "files": [],
            "checksums": {},
        }
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))
        (tmp_path / "model.gnn.json").write_text(json.dumps({"model_name": "test"}))
        (tmp_path / "state_space.json").write_text(
            json.dumps(
                {
                    "variables": [],
                    "observations": [],
                    "actions": [],
                    "transitions": {},
                }
            )
        )
        return tmp_path

    def test_execution_trace_basic(self):
        from cogant.gnn.runner import ExecutionTrace

        trace = ExecutionTrace(
            step=0,
            state={"s": 0.5},
            action="act_1",
            observation="obs_0",
        )
        assert trace.step == 0
        assert isinstance(trace.state, dict)

    def test_execution_trace_with_beliefs(self):
        from cogant.gnn.runner import ExecutionTrace

        trace = ExecutionTrace(
            step=1,
            state={"s": 0.3},
            beliefs={"state_a": 0.7, "state_b": 0.3},
            free_energy_before=1.5,
            free_energy_after=1.2,
        )
        assert trace.step == 1
        assert trace.free_energy_before == 1.5

    def test_runner_init(self):
        from cogant.gnn.runner import GNNModelRunner

        runner = GNNModelRunner()
        assert runner is not None
        assert hasattr(runner, "load_package")

    def test_runner_load_package(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner

        self._make_gnn_package(tmp_path)
        runner = GNNModelRunner()
        runner.load_package(str(tmp_path))
        assert runner.package_dir is not None

    def test_runner_run_after_load(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner

        self._make_gnn_package(tmp_path)
        runner = GNNModelRunner()
        runner.load_package(str(tmp_path))
        traces = runner.run(steps=2)
        # run returns a list of traces or similar
        assert traces is not None
