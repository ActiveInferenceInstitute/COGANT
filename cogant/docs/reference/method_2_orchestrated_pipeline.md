## Method 2: Orchestrated Pipeline
runner = PipelineRunner()
config = PipelineConfig(output_dir="output/")
bundle = runner.run("./my_repo", config)

