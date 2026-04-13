# Plugin Author — Learning Path

You want to extend COGANT — add support for a new language, write custom
translation rules, build a new exporter, or wire in a domain-specific
validator. This path walks you from "I want to extend it" to "I have a working
plugin and know how to publish it."

Estimated reading time: ~2 hours. Estimated hands-on time: ~half a day for a
first non-trivial plugin.

## Steps

1. **[Plugin Authoring Tutorial](../tutorials/07_plugin_authoring.md)** —
   Start here, even if you already know how plugins work in general. This is
   the COGANT-flavored end-to-end walkthrough: scaffold a plugin, register it
   via entry points, run it against the test suite, see it picked up by the
   pipeline. After this you'll have a concrete mental model of where your
   code fits.

2. **[Plugin API](../api/plugin_api.md)** — The reference for the protocols
   your plugin implements: parser plugins, translation-rule plugins, exporter
   plugins, validator plugins. Read the protocol that matches what you're
   building, plus the shared base classes.

3. **[Rules Overview](../rules/overview.md)** — Most plugin work touches the
   rule system, even indirectly. This page explains how rules are organized,
   how they're applied, and how rule sets compose. If you're writing a
   *translation rule* plugin, this is required reading; if you're writing a
   parser or exporter, it's useful context.

4. **[Custom Rules](../rules/custom_rules.md)** — The practical guide to
   writing your own rules: the rule schema, conditions and actions, how
   precedence and conflict resolution work, and how to test rules in
   isolation before plugging them into the full pipeline.

## Adjacent reading (pick what applies)

- **By plugin type:**
    - [Language Parser Plugin](../plugins/language_parser_plugin.md)
    - [Translation Rule Plugin](../plugins/translation_rule_plugin.md)
    - [Exporter Plugin](../plugins/exporter_plugin.md)
    - [Validator Plugin](../plugins/validator_plugin.md)
- **Plugin lifecycle:**
    - [Plugin Configuration](../plugins/plugin_configuration.md)
    - [Plugin Discovery](../plugins/plugin_discovery.md)
    - [Plugin Publishing](../plugins/plugin_publishing.md)
- **Quality:**
    - [Best Practices](../plugins/best_practices.md)
    - [Development Tips](../plugins/plugin_development_tips.md)
    - [Plugin Taxonomy & Abstract Bases](../plugins/plugin_taxonomy_abstract_bases.md)
- **Rule deep-dives:**
    - [Heuristic Rules](../rules/heuristic_rules.md)
    - [Rule Application](../rules/rule_application.md)
    - [Conflict Resolution](../rules/conflict_resolution.md)
    - [Testing Rules](../rules/testing_rules.md)

## Where to go next

- Once your plugin is working, **share it** following the
  [Plugin Publishing](../plugins/plugin_publishing.md) guide.
- To understand how the **scoring and review stages** consume your plugin's
  output, see the [Scoring API](../api/scoring_api.md) and
  [Review API](../api/reviewapi.md).
- If your plugin is upstream-worthy, follow the [Contributor](contributor.md)
  path to land it in the main repository.
