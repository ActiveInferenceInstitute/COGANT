from cogant import PipelineRunner
from cogant.api.pipeline import PipelineConfig
from rules.my_rules import MyCustomRule

runner = PipelineRunner()
config = PipelineConfig(output_dir="output/")
# Custom rules are loaded via config; see cogant.yaml plugins section
bundle = runner.run("./my_project", config)
