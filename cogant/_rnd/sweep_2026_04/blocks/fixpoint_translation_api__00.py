from cogant.translate.engine import TranslationEngine

engine = TranslationEngine(max_iterations=10)
engine.register_rule(my_rule)

# Run fixpoint iteration
mappings = engine.translate(graph)
