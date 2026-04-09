## Plugin Development Tips

### Testing

```python
import pytest
from my_plugin import MyTranslationRule
from cogant.schemas.core import Node, NodeKind
from cogant.schemas.graph import ProgramGraph, GraphMetadata
from cogant.graph.queries import GraphQuery

def test_my_rule():
    rule = MyTranslationRule()
    
    node = Node(id="fn_special", name="special_function", kind=NodeKind.FUNCTION)
    graph = ProgramGraph(nodes=[node], edges=[], metadata=GraphMetadata())
    query = GraphQuery(graph)
    
    matches = rule.matches(graph, query)
    assert len(matches) == 1
    mapping = rule.apply(matches[0], graph, query)
    assert mapping.target_concept == "special_function"
```

### Logging

```python
import logging
from cogant.translate.engine import TranslationRule

logger = logging.getLogger(__name__)

class MyTranslationRule(TranslationRule):
    def apply(self, match, graph, query):
        logger.debug(f"Applying rule to {match['name']}")
        # ...
        logger.info(f"Assigned concept {mapping.target_concept}")
        return mapping
```

### Error Handling

```python
from cogant.plugins import LanguagePlugin

class MyParserPlugin(LanguagePlugin):
    def parse(self, source_code: str):
        try:
            ast = self._parse_entities(source_code)
            return {"ast": ast, "errors": [], "warnings": []}
        except Exception as e:
            return {"ast": [], "errors": [str(e)], "warnings": []}
```

