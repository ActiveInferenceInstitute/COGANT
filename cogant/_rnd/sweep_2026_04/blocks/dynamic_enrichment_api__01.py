from cogant.api.pipeline import PipelineRunner, PipelineConfig

config = PipelineConfig(
    plugins={
        "dynamic": {
            "coverage_path": "coverage.xml",
            "trace_path": "trace.json",
        }
    },
    output_dir="output/",
)
runner = PipelineRunner()
bundle = runner.run("./my-repo", config)
