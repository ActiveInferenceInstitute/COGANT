from cogant import PipelineRunner
from cogant.api.pipeline import PipelineConfig

runner = PipelineRunner()
config = PipelineConfig(output_dir="output/")
bundle = runner.run("./my_project", config)

# Get validation report
report = bundle.validation_report()

# Print summary
print(f"Passed: {report.get('passed')}")
print(f"Checks: {report.get('checks', {})}")
for warning in report.get("warnings", []):
    print(f"  WARNING: {warning}")

# Save bundle (includes validation) as JSON
bundle.save_json("output/bundle.json")
