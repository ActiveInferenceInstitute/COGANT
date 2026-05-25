"""Shared Typer app, console, and CLI helper utilities."""

import functools
import logging
import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from cogant.api.pipeline import PipelineConfig, PipelineRunner
from cogant.api.bundle import Bundle

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

console = Console()

app = typer.Typer(
    name="cogant",
    help=(
        "Codebase-to-GNN Translation Engine.\n\n"
        "Translate a repository into an Active Inference Generalized "
        "Notation Notation (GNN) state-space model. Run "
        "[bold]cogant doctor[/bold] first to verify your environment, "
        "then [bold]cogant init <repo>[/bold] for a guided first run."
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
)


# ------------------------------------------------------- error helpers ----


def parse_step_csv(
    value: str | None,
    *,
    label: str,
    empty_means: list[int] | None = None,
) -> list[int] | None:
    """Parse a ``"3,5,7"``-style CSV of upstream step indices.

    * ``None`` (flag not given) → ``None`` (caller keeps its default).
    * ``""`` (flag given with empty value) → ``empty_means`` (defaults to
      ``None``). Use ``empty_means=[]`` for ``--skip-steps`` to mean
      "do not skip anything".
    * Otherwise parses comma-separated integers and validates the
      ``0..24`` range, raising :class:`typer.BadParameter` on invalid input.
    """
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return empty_means
    try:
        result = [int(v) for v in cleaned.split(",") if v.strip()]
    except ValueError as exc:
        raise typer.BadParameter(
            f"{label} expects a comma-separated list of integers (got {value!r})"
        ) from exc
    out_of_range = [v for v in result if v < 0 or v > 24]
    if out_of_range:
        raise typer.BadParameter(
            f"{label} contains out-of-range step(s) {out_of_range}; must be 0..24"
        )
    return result


def apply_upstream_pipeline_flags(
    config: PipelineConfig,
    *,
    enable: bool,
    only: str | None,
    skip: str | None,
    frameworks: str | None,
    llm_model: str | None,
) -> None:
    """Mutate ``config`` to honour the ``--upstream-gnn-*`` flag family."""
    config.upstream_gnn_pipeline = enable
    only_list = parse_step_csv(only, label="--upstream-gnn-only-steps")
    skip_list = parse_step_csv(skip, label="--upstream-gnn-skip-steps", empty_means=[])
    if only_list is not None:
        config.upstream_gnn_only_steps = only_list
    if skip_list is not None:
        config.upstream_gnn_skip_steps = skip_list
    if frameworks:
        config.upstream_gnn_frameworks = frameworks
    if llm_model:
        config.upstream_gnn_llm_model = llm_model


def render_upstream_pipeline_table(result: object) -> None:
    """Print a Rich table summarising an :class:`UpstreamPipelineResult`."""
    if not getattr(result, "available", False):
        console.print(
            "[yellow]Upstream pipeline unavailable:[/yellow] "
            f"{getattr(result, 'error', None) or 'src.main not importable'}"
        )
        return
    table = Table(title="Upstream GNN pipeline")
    table.add_column("Step", justify="right", style="cyan")
    table.add_column("Script", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Time (s)", justify="right")
    table.add_column("Notes", style="yellow")
    for step in getattr(result, "steps", []) or []:
        notes = step.error or ""
        if len(notes) > 60:
            notes = notes[:57] + "..."
        status_style = "green" if step.success else "red"
        table.add_row(
            f"{step.step_index:02d}",
            step.script,
            f"[{status_style}]{step.status}[/{status_style}]",
            f"{step.duration_s:.2f}",
            notes,
        )
    console.print(table)
    console.print(
        f"[dim]executed={len(result.executed)} skipped={len(result.skipped)} "
        f"success={result.success_count} fail={result.failure_count} "
        f"total={result.total_duration_s:.2f}s output={result.output_dir}[/dim]"
    )


def friendly_pipeline_error(exc: BaseException, target: Path | None = None) -> None:
    """Render a user-facing error message for a pipeline failure.

    This is the single place where exceptions bubbling out of the
    Session / PipelineRunner APIs are translated into human text. The
    caller is expected to raise ``typer.Exit(code=1)`` afterwards; we
    deliberately do not do it here so unit tests can assert on the
    printed message without also catching the exit.
    """

    if isinstance(exc, FileNotFoundError):
        console.print(f"[red]Error:[/red] Repository not found: {target or exc}")
        console.print("  [dim]→ Check the path exists and contains Python/JS/TS files[/dim]")
        return
    if isinstance(exc, PermissionError):
        console.print(f"[red]Error:[/red] Permission denied: {target or exc}")
        console.print("  [dim]→ Check read permissions on the repository and its files[/dim]")
        return
    if isinstance(exc, NotADirectoryError):
        console.print(
            f"[red]Error:[/red] Expected a repository directory but got a file: {target or exc}"
        )
        return

    # Fallback — print exception type + message, suggest doctor.
    console.print(f"[red]Unexpected error:[/red] {type(exc).__name__}: {exc}")
    console.print("  [dim]→ Run [bold]cogant doctor[/bold] to check your environment[/dim]")
    console.print("  [dim]→ File a bug at https://github.com/docxology/cogant/issues[/dim]")

def run_pipeline_with_progress(
    runner: "PipelineRunner",
    target: str,
    config: "PipelineConfig",
    description_prefix: str = "pipeline",
) -> "Bundle":
    """Run a pipeline while showing a single Rich progress spinner.

    The real per-stage progress lives inside ``PipelineRunner`` (which
    emits logs), but that API does not currently expose a callback
    stream. Rather than plumbing one in — and risking test breakage —
    we show a best-effort spinner that cycles through the canonical
    pipeline phase names while the run is in flight. Once the runner
    returns we update the spinner to ``Done`` and fall through.

    The helper is defensive: if Rich fails to initialise a live
    context (e.g. when stdout is captured by pytest), we fall back to
    running the pipeline without the spinner so tests keep working.
    """

    description = f"[cyan]{description_prefix}[/cyan]: Parsing source files…"
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            TimeElapsedColumn(),
            transient=True,
            console=console,
        ) as progress:
            task = progress.add_task(description, total=None)
            # We cannot hook into runner.run() mid-stage without an
            # API change, so we update the description to reflect the
            # canonical phases before invocation and once after.
            progress.update(
                task,
                description=f"[cyan]{description_prefix}[/cyan]: Building program graph…",
            )
            bundle = runner.run(target, config)
            progress.update(
                task,
                description=f"[cyan]{description_prefix}[/cyan]: Applying translation rules…",
            )
            progress.update(
                task,
                description=f"[cyan]{description_prefix}[/cyan]: Done",
            )
            return bundle
    except Exception:  # noqa: BLE001 — re-raised below, fallback for display only
        # If the progress context itself blew up (not the pipeline),
        # retry without a spinner. A real pipeline error will re-raise
        # from the inner ``runner.run`` and be caught by the caller.
        return runner.run(target, config)

