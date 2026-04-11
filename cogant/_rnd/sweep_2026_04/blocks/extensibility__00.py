from cogant.translate.engine import TranslationRule
from cogant.schemas.semantic import SemanticMapping

class MyCustomRule(TranslationRule):
    def matches(self, graph, query):
        # Return list of match dicts
        return [...]
    
    def apply(self, match, graph, query):
        return SemanticMapping(...)
