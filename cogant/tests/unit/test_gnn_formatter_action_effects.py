"""Unit tests for GNNMarkdownFormatter action effect field compatibility."""

from types import SimpleNamespace

from cogant.gnn.formatter import GNNMarkdownFormatter


class TestGNNMarkdownFormatterActionEffects:
    """Schema-variant reads: ``effects`` vs ``affects_state_vars``."""

    def test_effects_present_returns_copy(self) -> None:
        original = ["a", "b"]
        action = SimpleNamespace(effects=original)
        out = GNNMarkdownFormatter._action_effects(action)
        assert out == ["a", "b"]
        out.append("c")
        assert original == ["a", "b"]

    def test_effects_missing_uses_affects_state_vars(self) -> None:
        action = SimpleNamespace(affects_state_vars=["x", "y"])
        assert GNNMarkdownFormatter._action_effects(action) == ["x", "y"]

    def test_effects_preferred_over_affects_state_vars(self) -> None:
        action = SimpleNamespace(effects=["primary"], affects_state_vars=["ignored"])
        assert GNNMarkdownFormatter._action_effects(action) == ["primary"]

    def test_both_missing_returns_empty(self) -> None:
        action = SimpleNamespace()
        assert GNNMarkdownFormatter._action_effects(action) == []

    def test_effects_none_falls_back_to_affects(self) -> None:
        action = SimpleNamespace(effects=None, affects_state_vars=["z"])
        assert GNNMarkdownFormatter._action_effects(action) == ["z"]

    def test_empty_effects_returns_empty(self) -> None:
        action = SimpleNamespace(effects=[])
        assert GNNMarkdownFormatter._action_effects(action) == []
