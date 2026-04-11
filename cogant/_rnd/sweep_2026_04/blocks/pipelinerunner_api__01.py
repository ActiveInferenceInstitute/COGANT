from cogant.api.pipeline import PipelineConfig

config = PipelineConfig(
    # Stages to execute in order
    stages=[
        "ingest",
        "static",
        "normalize",
        "graph",
        "translate",
        "statespace",
        "process",
        "export",
        "validate",
    ],
    # Skip specific stages
    skip_stages=["dynamic", "process"],
    # Plugin configurations
    plugins={
        "python": {"version": "3.9"},
        "java": {"jdk_home": "/usr/lib/jvm/java-11"},
    },
    # Output directory
    output_dir="output/",
    # Enable verbose logging
    verbose=True,
    # Dry run (no side effects)
    dry_run=False,
)

bundle = runner.run("./my_repo", config)
