from pathlib import Path
from cogant import PipelineRunner, Session
from cogant.api.pipeline import PipelineConfig

# Option A: ergonomic path-based session
session = Session(
    workspace="/tmp/cogant-workspace",
    repo_path=Path("path/to/repo"),
)
session.build_graph()
session.export_all("output/session", layout=True)

# Option B: full pipeline runner (same orchestration as the CLI)
runner = PipelineRunner()
config = PipelineConfig(output_dir="output/pipeline", layout_output=True)
bundle = runner.run(str(Path("path/to/repo").resolve()), config)

print(bundle.repo_summary())
print(bundle.program_graph().get("statistics", {}))
bundle.save_json("output/bundle.json")
