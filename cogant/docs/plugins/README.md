# Plugins

> COGANT is extensible at four points: language parsers, translation rules, validators, and exporters. This section explains the plugin taxonomy, the abstract base classes, configuration and discovery, and the publishing workflow. Read this if you intend to ship a plugin out-of-tree or vendor one inside your own project.

## Contents

| Page | Description | Level |
|------|-------------|-------|
| [Overview](overview.md) | What a COGANT plugin is and why you would author one | Beginner |
| [Plugin Taxonomy (Abstract Bases)](plugin_taxonomy_abstract_bases.md) | The four abstract base classes and their contracts | Intermediate |
| [Language Parser Plugin](language_parser_plugin.md) | Add support for a new source language | Advanced |
| [Translation Rule Plugin](translation_rule_plugin.md) | Ship a rule pack as a plugin | Intermediate |
| [Validator Plugin](validator_plugin.md) | Add a new validator to the validation pipeline | Intermediate |
| [Exporter Plugin](exporter_plugin.md) | Emit a custom output format | Intermediate |
| [Plugin Configuration](plugin_configuration.md) | How plugins are configured at runtime | Intermediate |
| [Plugin Discovery](plugin_discovery.md) | Entry-point discovery and load order | Intermediate |
| [Plugin Development Tips](plugin_development_tips.md) | Practical advice for building robust plugins | Intermediate |
| [Plugin Publishing](plugin_publishing.md) | Packaging, naming, and distribution | Intermediate |
| [Best Practices](best_practices.md) | Quality bar checklist for first-party-grade plugins | Intermediate |
| [See Also](see_also.md) | Cross-links to related documentation | Beginner |

## Recommended Reading Order

1. [Overview](overview.md) — decide whether you actually need a plugin.
2. [Plugin Taxonomy (Abstract Bases)](plugin_taxonomy_abstract_bases.md) — pick the right base class for your goal.
3. The specific plugin-type page for your target: [Language Parser](language_parser_plugin.md), [Translation Rule](translation_rule_plugin.md), [Validator](validator_plugin.md), or [Exporter](exporter_plugin.md).
4. [Plugin Configuration](plugin_configuration.md) and [Plugin Discovery](plugin_discovery.md) — wire the plugin into a real session.
5. [Plugin Development Tips](plugin_development_tips.md) and [Best Practices](best_practices.md) — harden the implementation.
6. [Plugin Publishing](plugin_publishing.md) — ship it.

Agent notes: [AGENTS.md](AGENTS.md) - Hub: [../index.md](../index.md)
