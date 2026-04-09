## Quick Start

```python
from cogant import Session, PipelineRunner, Bundle
from cogant.api.pipeline import PipelineConfig

# Method 1: Simple Session
session = Session.from_target("./my_repo")
session.extract_static()
session.build_graph()
session.translate_to_gnn()
session.export_all("output/")

# Method 2: Orchestrated Pipeline
runner = PipelineRunner()
config = PipelineConfig(output_dir="output/")
bundle = runner.run("./my_repo", config)

# Access results
print(bundle.repo_summary())
bundle.save_json("output/bundle.json")  # same artifact as `cogant translate --output output/`
bundle.render_site("html_site/")
```

