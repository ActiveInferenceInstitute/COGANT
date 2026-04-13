## Incremental Export

For large projects, export in batches:

```python
# doctest: +SKIP  # example requires runtime context or external resources
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

For repository-level incremental **analysis** (skip unchanged files), see CLI `cogant translate --incremental` and [CLI — commands](../cli/commands.md).

### See also

- [Compression and size](compression_size.md)
- [Overview](overview.md)

