# Control-Positive Fixtures

Small, deterministic repositories used as normal fast evidence for COGANT's
pipeline, dashboards, roundtrip metrics, and manuscript figures. These fixtures
are COGANT-owned and should remain runnable without network access.

## Fixtures

- [`calculator/`](calculator/) - arithmetic service with config, action, and constraint roles.
- [`event_pipeline/`](event_pipeline/) - event ingest, transformation, and dispatch flow.
- [`flask_mini/`](flask_mini/) - minimal Flask-style web app.
- [`async_service/`](async_service/) - asyncio queue, dispatch action, and shutdown state.
- [`cli_tool/`](cli_tool/) - argparse command surface and side-effect action.
- [`data_pipeline/`](data_pipeline/) - extract/transform/load style data flow.
- [`plugin_architecture/`](plugin_architecture/) - registry and plugin dispatch pattern.
- [`notebook_module/`](notebook_module/) - notebook-converted analysis module.
- [`multi_package_workspace/`](multi_package_workspace/) - cross-package imports and workspace boundaries.

## Smoke Command

From the inner package root:

```bash
uv run cogant translate examples/control_positive/calculator --layout-output --output output/calculator
```
