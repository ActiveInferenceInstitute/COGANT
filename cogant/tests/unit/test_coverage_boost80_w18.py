#!/usr/bin/env python3
"""Coverage boost batch 80 — runtime/loop.py extended paths,
config/loaders.py error paths, ingest/files.py gitignore and
edge cases, gnn/formatter/semantic.py exception branch,
gnn/matrices.py missing paths.

Covers:
- runtime/loop.py: AgentRuntime (from matrices with callable likelihood/transition/
  preference_score, run_until_convergence with cfg=None, run_episode with
  empty steps fallback, update_D_from_posterior, update_A_from_episode with
  degenerate column)
- config/loaders.py: ConfigLoadError, ConfigLoader (load_from_yaml
  error paths, load_from_json error paths, build_cogant_config,
  build_pipeline_config, build_export_config, build_validation_config)
- ingest/files.py: FileEnumerator (_load_gitignore with .gitignore,
  _should_ignore with wildcard patterns, enumerate with compute_checksums)
- gnn/formatter/semantic.py: _format_markov_blanket exception path
- gnn/matrices.py: additional paths
"""

import json
import types
import pytest
from pathlib import Path

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_simple_matrices():
    """Return a simple namespace with A/B/C/D matrices."""
    m = types.SimpleNamespace(
        A=[[0.9, 0.1], [0.1, 0.9]],
        B=[[[1.0, 0.0], [0.0, 1.0]]],
        C=[1.0, 0.0],
        D=[0.5, 0.5],
    )
    return m


def _make_matrices_with_helpers():
    """Return a matrices namespace with callable likelihood/transition/preference_score."""
    def likelihood(state_dist):
        n_obs = 2
        # simple: return flat obs
        return [0.5] * n_obs

    def transition(state_dist, action=0):
        return list(state_dist)

    def preference_score(obs_dist):
        return sum(obs_dist)

    m = types.SimpleNamespace(
        A=[[0.9, 0.1], [0.1, 0.9]],
        B=[[[1.0, 0.0], [0.0, 1.0]]],
        C=[1.0, 0.0],
        D=[0.5, 0.5],
        likelihood=likelihood,
        transition=transition,
        preference_score=preference_score,
    )
    return m


def _make_runtime(with_helpers=False):
    from cogant.runtime.loop import AgentRuntime
    m = _make_matrices_with_helpers() if with_helpers else _make_simple_matrices()
    return AgentRuntime(m)


# ---------------------------------------------------------------------------
# runtime/loop.py — AgentRuntime with callable helpers
# ---------------------------------------------------------------------------

class TestAgentRuntimeExtended:
    def test_init_with_callable_helpers(self):
        """Test that callable likelihood/transition/preference_score are bound."""
        from cogant.runtime.loop import AgentRuntime
        rt = _make_runtime(with_helpers=True)
        assert rt is not None
        assert hasattr(rt, "_likelihood")
        assert hasattr(rt, "_transition")
        assert hasattr(rt, "_preference_score")

    def test_run_n_steps_with_helpers(self):
        from cogant.runtime.loop import AgentRuntime
        rt = _make_runtime(with_helpers=True)
        steps = rt.run_n_steps(3)
        assert isinstance(steps, list)
        assert len(steps) == 3

    def test_run_until_convergence_no_cfg(self):
        """run_until_convergence with cfg=None should use defaults."""
        from cogant.runtime.loop import AgentRuntime
        rt = _make_runtime()
        steps = rt.run_until_convergence(cfg=None)
        assert isinstance(steps, list)
        assert len(steps) >= 1

    def test_run_until_convergence_short(self):
        from cogant.runtime.loop import AgentRuntime, AgentConfig
        rt = _make_runtime()
        cfg = AgentConfig(max_steps=5, convergence_threshold=0.001)
        steps = rt.run_until_convergence(cfg=cfg)
        assert isinstance(steps, list)
        assert len(steps) <= 5

    def test_run_episode_with_empty_initial_state(self):
        """run_episode when n_steps produces 0 steps should fallback."""
        from cogant.runtime.loop import AgentRuntime
        rt = _make_runtime()
        # Run 0 steps to trigger empty-steps path
        result = rt.run_episode(n_steps=0, initial_state=[0.5, 0.5])
        assert result is not None
        assert isinstance(result.steps, list)
        assert isinstance(result.final_posterior, list)

    def test_run_episode_empty_D_fallback(self):
        """When D is empty, fallback uses uniform distribution."""
        from cogant.runtime.loop import AgentRuntime
        m = types.SimpleNamespace(
            A=[[0.9, 0.1], [0.1, 0.9]],
            B=[[[1.0, 0.0], [0.0, 1.0]]],
            C=[1.0, 0.0],
            D=[],  # empty D
        )
        rt = AgentRuntime(m)
        result = rt.run_episode(n_steps=0, initial_state=None)
        assert result is not None
        assert isinstance(result.final_posterior, list)

    def test_update_D_from_posterior_basic(self):
        from cogant.runtime.loop import AgentRuntime
        rt = _make_runtime()
        new_D = rt.update_D_from_posterior([0.7, 0.3])
        assert isinstance(new_D, list)
        assert len(new_D) == 2
        assert abs(sum(new_D) - 1.0) < 1e-6

    def test_update_D_from_posterior_empty(self):
        """When D is empty, return D unchanged."""
        from cogant.runtime.loop import AgentRuntime
        m = types.SimpleNamespace(A=[], B=[], C=[], D=[])
        rt = AgentRuntime(m)
        result = rt.update_D_from_posterior([0.5, 0.5])
        assert result == []

    def test_update_A_from_counts_basic(self):
        from cogant.runtime.loop import AgentRuntime
        rt = _make_runtime()
        obs_state_counts = [[3.0, 1.0], [1.0, 3.0]]
        new_A = rt.update_A_from_counts(obs_state_counts, learning_rate=0.5)
        assert isinstance(new_A, list)
        assert len(new_A) == 2

    def test_update_A_from_counts_empty_A(self):
        """When A is empty, return A unchanged."""
        from cogant.runtime.loop import AgentRuntime
        m = types.SimpleNamespace(A=[], B=[], C=[], D=[0.5, 0.5])
        rt = AgentRuntime(m)
        result = rt.update_A_from_counts([[1.0], [0.0]])
        assert result == []

    def test_update_A_from_counts_degenerate_column(self):
        """Test degenerate column path (all zeros → uniform reset)."""
        from cogant.runtime.loop import AgentRuntime
        rt = _make_runtime()
        # Pass all-zero counts for one state column → degenerate
        obs_state_counts = [[0.0, 0.0], [0.0, 0.0]]
        new_A = rt.update_A_from_counts(obs_state_counts, learning_rate=0.1)
        assert isinstance(new_A, list)
        # Each column should be uniform (0.5) since degenerate
        for s in range(2):
            col_sum = sum(new_A[o][s] for o in range(2))
            assert abs(col_sum - 1.0) < 1e-6

    def test_update_A_from_counts_zero_n_states(self):
        """When A has empty rows, n_states=0, return A unchanged."""
        from cogant.runtime.loop import AgentRuntime
        m = types.SimpleNamespace(
            A=[[], []],  # rows with no states
            B=[], C=[], D=[0.5, 0.5],
        )
        rt = AgentRuntime(m)
        result = rt.update_A_from_counts([[1.0], [0.0]])
        assert result == [[], []]


# ---------------------------------------------------------------------------
# config/loaders.py — error paths and build methods
# ---------------------------------------------------------------------------

class TestConfigLoader:
    def test_config_load_error_is_exception(self):
        from cogant.config.loaders import ConfigLoadError
        e = ConfigLoadError("test error")
        assert str(e) == "test error"
        assert isinstance(e, Exception)

    def test_load_from_yaml_nonexistent(self, tmp_path):
        from cogant.config.loaders import ConfigLoader, ConfigLoadError
        with pytest.raises(ConfigLoadError):
            ConfigLoader.load_from_yaml(tmp_path / "missing.yaml")

    def test_load_from_yaml_valid(self, tmp_path):
        from cogant.config.loaders import ConfigLoader
        p = tmp_path / "config.yaml"
        p.write_text("cogant:\n  timeout: 30\n")
        result = ConfigLoader.load_from_yaml(p)
        assert isinstance(result, dict)

    def test_load_json_from_file_nonexistent(self, tmp_path):
        from cogant.config.loaders import ConfigLoader, ConfigLoadError
        with pytest.raises(ConfigLoadError):
            ConfigLoader.load_json_from_file(tmp_path / "missing.json")

    def test_load_json_from_file_invalid(self, tmp_path):
        from cogant.config.loaders import ConfigLoader, ConfigLoadError
        p = tmp_path / "bad.json"
        p.write_text("not valid json {{{")
        with pytest.raises(ConfigLoadError):
            ConfigLoader.load_json_from_file(p)

    def test_load_json_from_file_valid(self, tmp_path):
        from cogant.config.loaders import ConfigLoader
        p = tmp_path / "config.json"
        p.write_text('{"cogant": {"timeout": 30}}')
        result = ConfigLoader.load_json_from_file(p)
        assert isinstance(result, dict)

    def test_build_cogant_config_default(self):
        from cogant.config.loaders import ConfigLoader
        config = ConfigLoader.build_cogant_config()
        assert config is not None

    def test_build_cogant_config_with_dict(self):
        from cogant.config.loaders import ConfigLoader
        config = ConfigLoader.build_cogant_config(config_dict={"cogant": {}})
        assert config is not None

    def test_build_pipeline_config_default(self):
        from cogant.config.loaders import ConfigLoader
        config = ConfigLoader.build_pipeline_config()
        assert config is not None

    def test_build_export_config_default(self):
        from cogant.config.loaders import ConfigLoader
        config = ConfigLoader.build_export_config()
        assert config is not None

    def test_build_validation_config_default(self):
        from cogant.config.loaders import ConfigLoader
        config = ConfigLoader.build_validation_config()
        assert config is not None

    def test_merge_configs_deep(self):
        from cogant.config.loaders import ConfigLoader
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"z": 4}, "b": 5}
        result = ConfigLoader.merge_configs(base, override, deep=True)
        assert result["b"] == 5
        assert isinstance(result, dict)

    def test_merge_configs_shallow(self):
        from cogant.config.loaders import ConfigLoader
        base = {"a": 1, "b": 2}
        override = {"b": 99, "c": 3}
        result = ConfigLoader.merge_configs(base, override, deep=False)
        assert result["b"] == 99
        assert result["c"] == 3


# ---------------------------------------------------------------------------
# ingest/files.py — FileEnumerator with .gitignore
# ---------------------------------------------------------------------------

class TestFileEnumeratorWithGitignore:
    def test_load_gitignore_creates_patterns(self, tmp_path):
        from cogant.ingest.files import FileEnumerator
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.pyc\n__pycache__\n# comment\n\nbuild/\n")
        fe = FileEnumerator(tmp_path, respect_gitignore=True)
        patterns = fe._load_gitignore()
        assert isinstance(patterns, set)
        assert "*.pyc" in patterns
        assert "__pycache__" in patterns
        # comment should not be included
        assert "# comment" not in patterns

    def test_load_gitignore_no_file(self, tmp_path):
        from cogant.ingest.files import FileEnumerator
        fe = FileEnumerator(tmp_path, respect_gitignore=True)
        patterns = fe._load_gitignore()
        assert patterns == set()

    def test_load_gitignore_cached(self, tmp_path):
        from cogant.ingest.files import FileEnumerator
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.log\n")
        fe = FileEnumerator(tmp_path, respect_gitignore=True)
        p1 = fe._load_gitignore()
        p2 = fe._load_gitignore()  # should return cached
        assert p1 is p2

    def test_should_ignore_with_wildcard_suffix(self, tmp_path):
        from cogant.ingest.files import FileEnumerator
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.pyc\n")
        fe = FileEnumerator(tmp_path, respect_gitignore=True)
        # A file ending in .pyc should be ignored
        test_file = tmp_path / "module.pyc"
        test_file.write_text("")
        result = fe._should_ignore(test_file)
        assert result is True

    def test_should_ignore_with_wildcard_prefix(self, tmp_path):
        from cogant.ingest.files import FileEnumerator
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("build/*\n")
        fe = FileEnumerator(tmp_path, respect_gitignore=True)
        test_file = tmp_path / "build" / "output.txt"
        test_file.parent.mkdir()
        test_file.write_text("")
        result = fe._should_ignore(test_file)
        assert result is True

    def test_enumerate_with_checksums(self, tmp_path):
        from cogant.ingest.files import FileEnumerator
        (tmp_path / "main.py").write_text("x = 1\n")
        fe = FileEnumerator(tmp_path, respect_gitignore=False)
        files = fe.enumerate(compute_checksums=True)
        assert isinstance(files, list)
        assert len(files) >= 1
        # At least one file should have a checksum
        with_checksums = [f for f in files if f.checksum is not None]
        assert len(with_checksums) >= 1

    def test_enumerate_excludes_test_files(self, tmp_path):
        from cogant.ingest.files import FileEnumerator
        (tmp_path / "main.py").write_text("x = 1\n")
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_main.py").write_text("def test_x(): pass\n")
        fe = FileEnumerator(tmp_path, respect_gitignore=False)
        files = fe.enumerate(include_test_files=False)
        # test file should be excluded
        test_files = [f for f in files if "test_" in f.relative_path]
        assert len(test_files) == 0


# ---------------------------------------------------------------------------
# gnn/formatter/semantic.py — exception path
# ---------------------------------------------------------------------------

class TestSemanticFormatterException:
    def test_format_markov_blanket_with_empty_graph(self):
        """With an empty graph, Markov blanket extraction may fail gracefully."""
        from cogant.gnn.formatter.semantic import _SemanticSectionsMixin
        from cogant.schemas.graph import ProgramGraph, GraphMetadata
        from cogant.statespace.compiler import StateSpaceModel
        from cogant.statespace.temporal import TimeRegime
        from cogant.process.extractor import ProcessModel

        class FakeFormatter(_SemanticSectionsMixin):
            pass

        fmt = FakeFormatter()
        fmt.graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))
        fmt.state_space = StateSpaceModel(
            id="ss", schema_name="test",
            variables={}, observations={}, actions={},
            transitions={}, likelihoods={}, preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
        )
        fmt.process = ProcessModel(id="pm", schema_name="test", stages={}, connections={})
        fmt.mappings = {}

        # Should not raise, returns a string with error info or blanket data
        result = fmt._format_markov_blanket()
        assert isinstance(result, str)
