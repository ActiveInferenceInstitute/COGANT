# Agents — py/cogant/cli

## Owner

Frontend Lead

## Responsibilities

Implement command-line interface design and command routing. Provide user-facing messaging, help text, and error reporting. Integrate with environment and shell utilities. Implement progress reporting and interactive features through Rich console output.

## Extending

Add new commands to main.py as @app.command() functions. Each command should parse arguments, delegate to cogant.api (Session, PipelineRunner, ReviewAPI), and display results through Rich console. Follow naming convention cogant <verb> <target>. Use typer.Argument and typer.Option for parameters. Keep commands stateless and lightweight.

## Coordination

Delegates all analysis work to cogant.api; CLI is purely a shell. Commands should map 1:1 to stable API surface (Session methods, PipelineRunner stages, ReviewAPI workflow). All error messages and help text are user-facing and reviewed by Architecture Lead. Environment-specific behavior (working directory, file paths) should be handled in CLI layer, not API.

## Files

main.py: Typer app instance with 14 subcommands. Each command function imports from cogant.api, creates Session/PipelineRunner/ReviewAPI objects, delegates work, and renders results using Rich (Table, Panel, Syntax for code blocks). console = Console() instance used throughout for styled output. All commands support --help.

diff.py: Helper module with load_bundle (reads output directory and loads graph, mappings, state_space) and diff_command (compares two bundles using DriftAnalyzer and CodebaseMetrics, generates markdown diff report).

__init__.py: Exports app for entry point.
