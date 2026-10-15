# Agents — py/cogant/cli

## Owner

Frontend Lead

## Responsibilities

Implement command-line interface design and command routing. Provide user-facing messaging, help text, and error reporting. Integrate with environment and shell utilities. Implement progress reporting and interactive features through Rich console output.

## Extending

Register direct command callbacks under `commands/`; wire command groups in
`main.py` beside `plugin`, `migrate`, and `finite`. Callbacks parse arguments and
delegate to the reusable domain interface. Use Typer arguments and options, and
keep JSON output machine-readable on stdout with validation feedback on stderr.

## Coordination

Delegates all analysis work to cogant.api; CLI is purely a shell. Commands should map 1:1 to stable API surface (Session methods, PipelineRunner stages, ReviewAPI workflow). All error messages and help text are user-facing and reviewed by Architecture Lead. Environment-specific behavior (working directory, file paths) should be handled in CLI layer, not API.

## Files

main.py: Typer wiring for direct command modules and the `plugin`, `migrate`,
and `finite` groups. Run `cogant --help` for the live list and each subcommand's
help for its current options.

finite.py: `compile` and `verify` callbacks for declared finite models; reusable
admission, compilation, and checking live in `cogant.statespace`.

diff.py: Helper module with load_bundle (reads output directory and loads graph, mappings, state_space) and diff_command (compares two bundles using DriftAnalyzer and CodebaseMetrics, generates markdown diff report).

__init__.py: Exports app for entry point.
