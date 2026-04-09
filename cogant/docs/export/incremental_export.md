## Incremental Export

For large projects, export in batches:

```python
from cogant import PipelineRunner
from cogant.api.pipeline import PipelineConfig

runner = PipelineRunner()
config = PipelineConfig(output_dir="output/")
bundle = runner.run("./my_project", config)

# Export modules separately (planned; illustrative)
# When per-module export is available:
# for module_name, module_graph in bundle.by_module():
#     pyg_data = bundle.export_pytorch_geometric(subgraph=module_graph)
#     torch.save(pyg_data, f"graphs/{module_name}.pt")
```

