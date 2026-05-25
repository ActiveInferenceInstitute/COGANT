# Tutorial 7: Authoring a language plugin

> **What this page is:** A guided implementation of a new `LanguagePlugin` so COGANT can ingest a language it does not currently support, using tree-sitter as the AST front end.
>
> **Prerequisites:** [Tutorial 4: Writing a custom rule](04_custom_rules.md), familiarity with tree-sitter grammars, and the [Plugin API reference](../api/plugin_api.md).
>
> **Reading time:** ~30 minutes
>
> **Next steps:** [Plugin API reference](../api/plugin_api.md) · [Static analysis API](../api/static.md) · [Translation rules reference](../reference/translation_rules.md)

> **Goal.** Write a new `LanguagePlugin` that teaches COGANT to parse a language it does not currently support, using `tree-sitter` as the AST front end.

> **Theory background:** A language plugin is a registered extension point in COGANT's parser
> layer. The contract you implement is documented in the [plugin API reference](../api/plugin_api.md),
> and the broader rule / extension model that plugins slot into is in the
> [rules overview](../rules/overview.md). Skim both before writing your first plugin so the
> abstract methods below have context.

COGANT's parser layer is plugin-based. v0.1.0 ships plugins for Python (CPython `ast`) and
JavaScript / TypeScript (via `tree-sitter`). Adding a new language means:

1. Implementing a `LanguagePlugin` subclass.
2. Registering it with the plugin registry.
3. Writing parser tests against a tiny golden fixture.

This tutorial walks through adding a **Ruby** plugin as a worked example.

## 1. The plugin base class

```python
# py/cogant/plugins/base.py  (excerpt)

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, List

from cogant.schemas.core import Node, Edge


class LanguagePlugin(ABC):
    """A language-specific parser plugin.

    Plugins are stateless. The registry instantiates each plugin once and
    dispatches files to it by extension + shebang match.
    """

    name: str
    extensions: tuple[str, ...]
    shebang_patterns: tuple[str, ...] = ()

    @abstractmethod
    def parse_file(self, path: Path) -> "ParseResult":
        """Parse a single source file into nodes and edges."""

    @abstractmethod
    def parse_source(self, source: str, filename: str) -> "ParseResult":
        """Parse in-memory source without touching the filesystem."""
```

A `ParseResult` bundles the nodes, edges, and a `diagnostics` list for warnings and errors.

## 2. Pick a tree-sitter grammar

Ruby has a well-maintained grammar at
[`tree-sitter/tree-sitter-ruby`](https://github.com/tree-sitter/tree-sitter-ruby). Install it:

```bash
uv add tree-sitter-ruby  # or pin to the version used by CI
```

COGANT's parser uses `tree_sitter.Language.build_library()` at import time — see
`py/cogant/parsers/tree_sitter_base.py` for the helper.

## 3. Write the plugin

```python
# doctest: +SKIP  # example requires runtime context or external resources
# py/cogant/plugins/ruby.py

from pathlib import Path
from typing import List

import tree_sitter_ruby  # type: ignore
from tree_sitter import Language, Parser, Node as TSNode

from cogant.plugins.base import LanguagePlugin, ParseResult
from cogant.schemas.core import Node, Edge, NodeKind, EdgeKind


_LANGUAGE = Language(tree_sitter_ruby.language(), "ruby")


class RubyPlugin(LanguagePlugin):
    """Parse Ruby source into COGANT program-graph nodes and edges."""

    name = "ruby"
    extensions = (".rb",)
    shebang_patterns = ("ruby",)

    def __init__(self) -> None:
        self._parser = Parser()
        self._parser.set_language(_LANGUAGE)

    def parse_file(self, path: Path) -> ParseResult:
        source = path.read_text(encoding="utf-8")
        return self.parse_source(source, str(path))

    def parse_source(self, source: str, filename: str) -> ParseResult:
        tree = self._parser.parse(source.encode("utf-8"))
        nodes: List[Node] = []
        edges: List[Edge] = []

        module_node = Node(
            id=f"{filename}:module",
            kind=NodeKind.MODULE,
            name=Path(filename).stem,
            file=filename,
        )
        nodes.append(module_node)

        self._walk(tree.root_node, filename, module_node, nodes, edges)
        return ParseResult(nodes=nodes, edges=edges, diagnostics=[])

    def _walk(
        self,
        ts_node: TSNode,
        filename: str,
        parent: Node,
        nodes: List[Node],
        edges: List[Edge],
    ) -> None:
        if ts_node.type == "class":
            name_node = ts_node.child_by_field_name("name")
            class_name = (
                name_node.text.decode("utf-8") if name_node else "<anon>"
            )
            class_node = Node(
                id=f"{filename}:{class_name}",
                kind=NodeKind.CLASS,
                name=class_name,
                file=filename,
                line_start=ts_node.start_point[0] + 1,
                line_end=ts_node.end_point[0] + 1,
            )
            nodes.append(class_node)
            edges.append(
                Edge(source_id=parent.id, target_id=class_node.id,
                     kind=EdgeKind.CONTAINS)
            )
            parent = class_node
        elif ts_node.type == "method":
            name_node = ts_node.child_by_field_name("name")
            method_name = (
                name_node.text.decode("utf-8") if name_node else "<anon>"
            )
            method_node = Node(
                id=f"{filename}:{parent.name}.{method_name}",
                kind=NodeKind.METHOD,
                name=method_name,
                file=filename,
                line_start=ts_node.start_point[0] + 1,
                line_end=ts_node.end_point[0] + 1,
            )
            nodes.append(method_node)
            edges.append(
                Edge(source_id=parent.id, target_id=method_node.id,
                     kind=EdgeKind.CONTAINS)
            )

        for child in ts_node.children:
            self._walk(child, filename, parent, nodes, edges)
```

## 4. Register the plugin

```python
# doctest: +SKIP  # example requires runtime context or external resources
# py/cogant/plugins/__init__.py

from cogant.plugins.python import PythonPlugin
from cogant.plugins.javascript import JavaScriptPlugin
from cogant.plugins.typescript import TypeScriptPlugin
from cogant.plugins.ruby import RubyPlugin

PLUGIN_REGISTRY = [
    PythonPlugin(),
    JavaScriptPlugin(),
    TypeScriptPlugin(),
    RubyPlugin(),  # <-- new
]
```

## 5. Test against a golden fixture

Create a minimal Ruby fixture:

```ruby
# tests/fixtures/languages/ruby/calculator.rb
class Calculator
  def initialize
    @display = 0
    @history = []
  end

  def get_display
    @display
  end

  def add(x)
    @display += x
    @history << x
    @display
  end
end
```

Write the test (no mocks — real tree-sitter, real source):

```python
# doctest: +SKIP  # example requires runtime context or external resources
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
```

Run it:

```bash
uv run pytest tests/unit/plugins/test_ruby_plugin.py -v
```

## 6. End-to-end smoke test

Once the unit tests are green, run the full pipeline on the Ruby fixture:

```bash
uv run cogant translate tests/fixtures/languages/ruby/ \
    --output output/ruby_smoke \
    --layout-output
uv run cogant validate output/ruby_smoke/gnn_package
```

The existing translation rules are **language-agnostic** — they operate on `NodeKind` and
`EdgeKind`, not on Python-specific idioms. So `ObservationRule`, `ActionRule`, and
`MutatingSubsystemRule` should fire on the Ruby calculator exactly as they do on the Python
one. Any rules that match against English keywords (`get_*`, `set_*`) will also work unchanged.

## Gotchas

- **Edge kinds are a closed enum.** If your language needs a relationship COGANT does not
  currently model (e.g. Ruby-specific `include` vs `extend`), either map it to the closest
  existing `EdgeKind` or propose an extension in an R&D note before adding a new enum value.
- **Call-graph resolution.** The plugin only needs to emit CONTAINS and definition-level
  edges; the graph builder adds CALLS edges in a later pass. Wiring CALLS during parsing is
  possible but not required.
- **Source positions are 1-indexed in COGANT.** Tree-sitter returns 0-indexed rows; convert
  at the plugin boundary.
- **No mocks.** Plugin tests must use real source and the real tree-sitter grammar. See
  `tests/unit/plugins/test_python_plugin.py` for the canonical pattern.

## Next

- [`py/cogant/plugins/base.py`](https://github.com/docxology/cogant/blob/main/cogant/py/cogant/plugins/base.py) — the full base-class API.
- [`py/cogant/parsers/tree_sitter_base.py`](https://github.com/docxology/cogant/blob/main/cogant/py/cogant/parsers/tree_sitter_base.py) —
  shared tree-sitter helpers.
- [Tutorial 4: writing a custom rule](04_custom_rules.md) — once your plugin is parsing, you
  can write language-specific rules to refine the role assignments.
