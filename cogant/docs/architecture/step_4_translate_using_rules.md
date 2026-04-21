## Step 4: Translate using rules
engine = TranslationEngine()
engine.register_rule(ReadOnlyInputRule())
engine.register_rule(MutatingSubsystemRule())
engine.register_rule(OrchestratorRule())
engine.register_rule(TestAssertionRule())
engine.register_rule(RetryPatternRule())
engine.register_rule(EventBusRule())
engine.register_rule(ConfigRule())
engine.register_rule(FeatureFlagRule())

auto_mappings = engine.translate(merged_graph)
