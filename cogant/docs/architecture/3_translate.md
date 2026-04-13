## 3. Translate
engine = TranslationEngine()
engine.register_rule(ReadOnlyInputRule())
engine.register_rule(MutatingSubsystemRule())
