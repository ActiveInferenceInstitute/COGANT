## Configuration and precedence

- Optional YAML settings for the pipeline are loaded with [`ConfigLoader.load_from_yaml`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/config/loaders.py); the repo ships an example [`cogant.yaml`](https://github.com/cogant-contributors/cogant/blob/main/cogant/cogant.yaml) at the package root.
- CLI / `PipelineRunner` accept `--config` / `PipelineConfig` fields that point at that file; see [`SPEC` § Configuration](../reference/README.md) for the shape of merged settings.
- **Rule execution order** is defined in code: concrete [`TranslationRule`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/translate/rules.py) classes are registered on [`TranslationEngine`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/translate/engine.py) in a single ordered list. There is no separate YAML-driven “rule priority” layer in v0.1.x—adding or reordering rules requires Python changes or wrapping the engine in your integration.
- **Downstream shape:** After translation, mappings are stored on the pipeline bundle as **`_semantic_mappings`** (dict: id → mapping object) and consumed by the **export** stage and [`GNNPackageBuilder`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/gnn/package.py). See [API guide § Export stage and GNN package](../api/README.md).

