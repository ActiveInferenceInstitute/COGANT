# tests/unit/plugins/test_ruby_plugin.py

from pathlib import Path

from cogant.plugins.ruby import RubyPlugin
from cogant.schemas.core import NodeKind


FIXTURE = Path(__file__).parent.parent.parent / "fixtures" / "languages" / "ruby" / "calculator.rb"


def test_parses_class_and_methods() -> None:
    plugin = RubyPlugin()
    result = plugin.parse_file(FIXTURE)

    names = {n.name for n in result.nodes}
    assert "Calculator" in names
    assert "get_display" in names
    assert "add" in names
    assert "initialize" in names

    kinds = {n.kind for n in result.nodes}
    assert NodeKind.CLASS in kinds
    assert NodeKind.METHOD in kinds
    assert NodeKind.MODULE in kinds

    # Exactly one CONTAINS edge per child.
    contains = [e for e in result.edges if e.kind.name == "CONTAINS"]
    assert len(contains) == 5  # module -> class, class -> 4 methods (initialize + 3)
