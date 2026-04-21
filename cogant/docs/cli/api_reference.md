## API Reference

For programmatic usage, see `examples/example_pipeline.py` for the Python API.

Quick reference:

```python
# doctest: +SKIP  # example requires runtime context or external resources
from cogant import Session, PipelineRunner, Bundle
from cogant.api.pipeline import PipelineConfig

# Method 1: Session API
session = Session.from_target("./repo")
session.extract_static()
session.build_graph()
session.translate_to_gnn()
session.export_all("output/")

# Method 2: Pipeline Runner
runner = PipelineRunner()
config = PipelineConfig(output_dir="output/")
bundle = runner.run("./repo", config)

# Access results
print(bundle.repo_summary())
print(bundle.program_graph())
bundle.render_site("html_site/")
```
