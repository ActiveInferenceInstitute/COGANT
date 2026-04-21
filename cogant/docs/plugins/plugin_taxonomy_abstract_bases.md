## Plugin taxonomy (abstract bases)

| Base class | Role |
|------------|------|
| [`LanguagePlugin`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/plugins/base.py) | Parse source, extract symbols/types, resolve imports |
| [`TracePlugin`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/plugins/base.py) | Ingest traces and coverage; derive call graphs |
| [`NormalizerPlugin`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/plugins/base.py) | Canonicalize intermediate dicts; schema checks |
| [`TranslationRulePlugin`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/plugins/base.py) | Map graph nodes/edges to GNN-oriented features (parallel to lower-level [`TranslationRule`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/translate/engine.py) hooks) |
| [`StateSpacePlugin`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/plugins/base.py) | Optional hooks around state / observation / action extraction |
| [`ProcessModelPlugin`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/plugins/base.py) | Stage ordering and dependency extraction from bundles |
| [`ExportPlugin`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/plugins/base.py) | Additional disk formats beyond built-in exporters |
| [`ValidationPlugin`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/plugins/base.py) | Custom bundle or package checks and quality metrics |
| [`VisualizationPlugin`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/plugins/base.py) | Alternate renderers for bundles or graphs |

**Registration:** There is no dynamic plugin registry in `cogant.plugins` yet—subclasses are imported and wired by application code or tests. Treat these bases as contracts for downstream packages; contributing a first-party registry is tracked on the [roadmap](../roadmap/README.md).

**Pipeline translation rules:** The running pipeline applies concrete [`TranslationRule`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/translate/rules.py) instances from the translate package; see [Translation rules](../rules/README.md) and the examples below.
