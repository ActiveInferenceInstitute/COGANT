from cogant import PipelineRunner
from cogant.api.pipeline import PipelineConfig

runner = PipelineRunner()
config = PipelineConfig(output_dir="output/")

# Plugins are automatically discovered and registered via cogant.yaml
bundle = runner.run("./my_project", config)
