## Configuration and precedence

- Optional YAML settings for the pipeline are loaded with [`ConfigLoader.load_from_yaml`](../py/cogant/config/loaders.py); the repo ships an example [`cogant.yaml`](../cogant.yaml) at the package root.
- CLI / `PipelineRunner` accept `--config` / `PipelineConfig` fields that point at that file; see [`SPEC` § Configuration](../reference/README.md) for the shape of merged settings.
- **Rule execution order** is defined in code: concrete [`TranslationRule`](../py/cogant/translate/rules.py) classes are registered on [`TranslationEngine`](../py/cogant/translate/engine.py) in a single ordered list. There is no separate YAML-driven “rule priority” layer in v0.1.x—adding or reordering rules requires Python changes or wrapping the engine in your integration.
- **Downstream shape:** After translation, mappings are stored on the pipeline bundle as **`_semantic_mappings`** (dict: id → mapping object) and consumed by the **export** stage and [`GNNPackageBuilder`](../py/cogant/gnn/package.py). See [API guide § Export stage and GNN package](../api/README.md).

