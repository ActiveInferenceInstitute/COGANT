from cogant import PipelineRunner
from cogant.api.pipeline import PipelineConfig

runner = PipelineRunner()
config = PipelineConfig(output_dir="output/flask_app")
bundle = runner.run("./examples/real_world/flask_app", config)

assert not bundle.errors
print(bundle.repo_summary())
bundle.save_json("output/flask_app/bundle.json")
