from cogant.api.pipeline import PipelineRunner, PipelineConfig

runner = PipelineRunner()
config = PipelineConfig(output_dir="output/")
bundle = runner.run("./my_repo", config)
