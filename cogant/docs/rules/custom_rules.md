## Custom Rules

### Define Custom Rule

```python
from cogant.translate.engine import TranslationRule
from cogant.schemas.semantic import SemanticMapping, MappingKind, ConfidenceTier
from cogant.schemas.core import NodeKind
from cogant.graph.queries import GraphQuery
from cogant.schemas.graph import ProgramGraph

class MyCustomRule(TranslationRule):
    def matches(self, graph: ProgramGraph, query: GraphQuery):
        """Return list of match dicts for nodes matching this rule."""
        matches = []
        for node in graph.get_nodes_by_kind(NodeKind.FUNCTION):
            if "magic_" in node.name:
                matches.append({"node_id": node.id, "name": node.name})
        return matches

    def apply(self, match, graph: ProgramGraph, query: GraphQuery):
        """Apply rule and return SemanticMapping."""
        return SemanticMapping(
            source_id=match["node_id"],
            target_concept="special_function",
            kind=MappingKind.STRUCTURAL,
            confidence=ConfidenceTier.HIGH,
            provenance=None,
        )
```

### Register Custom Rule

```yaml
# cogant.yaml
translation:
  rule_set: default
  custom_rules:
    - path: "rules/my_rules.py"
      enabled: true
      class_name: "MyCustomRule"
```

Or programmatically:

```python
# doctest: +SKIP  # example requires runtime context or external resources
from cogant import PipelineRunner
from cogant.api.pipeline import PipelineConfig
from rules.my_rules import MyCustomRule

runner = PipelineRunner()
config = PipelineConfig(output_dir="output/")
# Custom rules are loaded via config; see cogant.yaml plugins section
bundle = runner.run("./my_project", config)
```

