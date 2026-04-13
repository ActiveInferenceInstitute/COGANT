# AGENTS.md — Plugins module

Documentation for COGANT's four plugin extension points: language parsers,
translation rules, validators, and exporters. This module is the canonical
source for the plugin taxonomy, the abstract base classes, the
configuration and discovery contract, the development workflow, and the
publishing story.

## Purpose and ownership

When a plugin contract changes in code, the matching page here must change
in the same PR. Plugins are a public, out-of-tree extension surface, so
documentation drift here directly breaks third-party developers. Owned by
whoever is editing the abstract base classes in `py/cogant/plugins/` (or
the plugin discovery / registration code).

## File map

| File | Purpose | Update trigger |
|------|---------|----------------|
| `README.md` | TOC and recommended reading order | When a file is added, removed, or renamed |
| `AGENTS.md` | This file — maintenance rules | When ownership or the update-with-code policy changes |
| `overview.md` | What a COGANT plugin is and when to author one | When the plugin story changes materially |
| `plugin_taxonomy_abstract_bases.md` | The four ABCs and their contracts | Whenever any ABC gains, loses, or changes a method |
| `language_parser_plugin.md` | Adding support for a new source language | When the parser interface or registration contract changes |
| `translation_rule_plugin.md` | Shipping a rule pack as a plugin | When the rule plugin contract changes |
| `validator_plugin.md` | Adding a validator to the validation pipeline | When the validator plugin contract changes |
| `exporter_plugin.md` | Emitting a custom output format | When the exporter plugin contract changes |
| `plugin_configuration.md` | Runtime configuration of plugins | When the configuration schema changes |
| `plugin_discovery.md` | Entry-point discovery and load order | When discovery rules or load order change |
| `plugin_development_tips.md` | Practical advice for robust plugins | When a recurring plugin bug suggests new guidance |
| `plugin_publishing.md` | Packaging, naming, and distribution | When packaging conventions or naming policy change |
| `best_practices.md` | Quality bar checklist for first-party-grade plugins | When a new quality criterion is adopted |
| `see_also.md` | Cross-links to related modules | When link targets move |

## Adding a new doc

1. Decide whether the new content belongs in one of the existing plugin-
   type pages or deserves its own page. Prefer to extend an existing page
   unless the new topic applies to all four plugin types.
2. Use a short, lower-case, underscore-separated slug.
3. Open with the plugin type (parser / rule / validator / exporter) the
   page applies to, or explicitly say "all types".
4. Include a minimal working example — ideally under 50 lines — that a
   third-party developer can copy into a new package.
5. Add a row to the `## Contents` table in `README.md`.

## Known gotchas

- `plugin_taxonomy_abstract_bases.md` is the single source of truth for
  the ABCs. Any duplication of ABC signatures across other pages in this
  module is a bug — link to the taxonomy page instead.
- Plugin contracts are public API. A change in any of the four plugin-type
  pages must be announced in `../roadmap/deprecation_policy.md` and in
  the changelog.
- Configuration keys documented in `plugin_configuration.md` must match
  the schema in code. Grep the repository for the key string before
  editing this page.
