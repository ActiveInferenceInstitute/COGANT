from cogant import PipelineRunner
from cogant.api.pipeline import PipelineConfig

runner = PipelineRunner()
config = PipelineConfig(output_dir="output/")
bundle = runner.run("./my_project", config)

# Inspect translation stage results
translate_result = bundle.stage_results.get("translate", {})
print(f"Mappings: {len(translate_result.get('mappings', []))}")
