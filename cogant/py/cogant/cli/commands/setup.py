"""CLI command registrations."""

from pathlib import Path

import typer

from cogant.api.pipeline import PipelineConfig, PipelineRunner
from cogant.cli._app import (
    app,
    console,
)
from cogant.cli._app import (
    friendly_pipeline_error as _friendly_pipeline_error,
)
from cogant.cli._app import (
    run_pipeline_with_progress as _run_pipeline_with_progress,
)
from cogant.cli.doctor import doctor_command, render_report, run_doctor
from cogant.ingest.repo_sniff import count_source_files as _count_source_files
from cogant.ingest.repo_sniff import estimate_pipeline_seconds as _estimate_pipeline_seconds
from cogant.ingest.repo_sniff import format_duration as _format_duration


@app.command()
def init(
    path: str = typer.Argument(
        ...,
        help="Path to initialize (created if it does not exist).",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimal output (suppresses confirmation summary).",
    ),
    check_env: bool = typer.Option(
        False,
        "--check/--no-check",
        help=(
            "Run [bold]cogant doctor[/bold] before touching the filesystem. "
            "Use this on a fresh machine to surface missing dependencies."
        ),
    ),
    run: bool = typer.Option(
        False,
        "--run",
        help=(
            "After initializing, also run [bold]cogant translate[/bold] on "
            "the newly created project. Off by default so init stays fast."
        ),
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip the confirmation prompt before running translate.",
    ),
) -> None:
    """Initialize a new COGANT project (guided first-time setup).

    This command is safe to re-run: it creates ``.cogant/config.json``
    if missing, refuses to clobber an existing config, and can
    optionally run doctor and translate in a single pass.

    Typical first-time flow::

        cogant init ./my_repo --check --run

    which: (1) diagnoses the environment, (2) scaffolds the project
    config, (3) estimates pipeline duration from the file count, and
    (4) translates the repo to GNN after a confirmation prompt.
    """

    console.print(f"[bold blue]Initializing COGANT project[/bold blue] at {path}")

    project_dir = Path(path)

    # --------- Step 0: optional environment diagnostics -----------------
    if check_env:
        console.print("\n[bold]Step 1/4[/bold] — Environment diagnostics")
        report = run_doctor()
        render_report(console, report)
        if not report.ok:
            console.print(
                "[red]Environment check failed — aborting init. "
                "Fix the errors above and retry.[/red]"
            )
            raise typer.Exit(code=1)

    # --------- Step 1: filesystem scaffold ------------------------------
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create .cogant directory
    cogant_dir = project_dir / ".cogant"
    cogant_dir.mkdir(exist_ok=True)

    # Create config file (never overwritten — init is idempotent).
    config_file = cogant_dir / "config.json"
    config_created = False
    if not config_file.exists():
        config_file.write_text(
            """{
  "version": "0.1.0",
  "name": "untitled",
  "target": ".",
  "output_dir": "output",
  "stages": [
    "ingest",
    "static",
    "normalize",
    "graph",
    "translate",
    "statespace",
    "process",
    "export",
    "validate"
  ]
}
"""
        )
        config_created = True

    # --------- Step 2: repo sniff + estimate ---------------------------
    file_count = _count_source_files(project_dir)
    estimate_s = _estimate_pipeline_seconds(file_count)

    if not quiet:
        console.print("[green]✓ Project initialized successfully[/green]")
        console.print(
            f"  Config: {config_file}"
            + (" [dim](created)[/dim]" if config_created else " [dim](existing)[/dim]")
        )
        console.print(f"  Source files detected: [cyan]{file_count}[/cyan]")
        if file_count == 0:
            console.print(
                "  [yellow]No .py/.js/.ts files found — "
                "cogant translate will have nothing to process.[/yellow]"
            )
        else:
            console.print(
                f"  Estimated [bold]translate[/bold] time: "
                f"[magenta]{_format_duration(estimate_s)}[/magenta] "
                f"[dim](≈50ms/file)[/dim]"
            )

    # --------- Step 3: optional translate run --------------------------
    if run:
        if file_count == 0:
            console.print("[yellow]--run requested but no source files found; skipping.[/yellow]")
            return
        if not yes:
            confirm = typer.confirm(
                f"Run cogant translate on {project_dir} now?",
                default=True,
            )
            if not confirm:
                console.print("[dim]Skipped translate (user declined).[/dim]")
                return

        console.print("\n[bold]Running translate pipeline…[/bold]")
        try:
            runner = PipelineRunner()
            config = PipelineConfig(output_dir=str(project_dir / "output"))
            bundle = _run_pipeline_with_progress(
                runner,
                str(project_dir),
                config,
                description_prefix="init",
            )
        except Exception as exc:  # noqa: BLE001 — user-facing surface
            _friendly_pipeline_error(exc, project_dir)
            raise typer.Exit(code=1) from exc

        console.print(
            f"[green]✓ Translate complete[/green] — "
            f"{len(bundle.stage_results)} stages, {len(bundle.errors)} errors"
        )
        console.print(f"  Bundle: {project_dir / 'output' / 'bundle.json'}")


@app.command()
def doctor() -> None:
    """Diagnose the COGANT runtime environment.

    Prints a Rich panel listing the Python version, every runtime
    dependency (core, viz, multilang), the optional Rust backend, and
    external tooling such as ``git``. Exits with code ``1`` when any
    required check fails so it can gate CI setups.
    """

    code = doctor_command(console)
    if code != 0:
        raise typer.Exit(code=code)
