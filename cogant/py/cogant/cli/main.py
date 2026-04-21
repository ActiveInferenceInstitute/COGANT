"""Main CLI application with all subcommands.

This module is the single Typer entry point for the ``cogant``
command. Every subcommand here is a thin orchestrator: it parses
options, calls the Session/PipelineRunner APIs, and prints Rich output.

User-facing ergonomics live in sibling modules:

* :mod:`cogant.cli.doctor` — ``cogant doctor`` environment diagnostics.
* :mod:`cogant.cli.diff` — directory-based drift reporting helper.

When adding new commands, prefer: (1) a short docstring that doubles as
``--help`` text, (2) ``typer.Option(..., help=...)`` on every option so
``cogant <cmd> --help`` is self-explanatory, and (3) wrapping any call
into the pipeline with :func:`_handle_pipeline_errors` so users get a
friendly message instead of a Python traceback.
"""

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

from cogant.api.bundle import Bundle
from cogant.api.pipeline import PipelineConfig, PipelineRunner
from cogant.api.session import Session
from cogant.cli.doctor import doctor_command, render_report, run_doctor
from cogant.cli.migrate import migrate_app
from cogant.cli.plugin import plugin_app
from cogant.ingest.repo_sniff import (
    count_source_files as _count_source_files,
)
from cogant.ingest.repo_sniff import (
    estimate_pipeline_seconds as _estimate_pipeline_seconds,
)
from cogant.ingest.repo_sniff import (
    format_duration as _format_duration,
)
from cogant.reverse.cli import reverse_command, roundtrip_command

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Rich console for output
console = Console()

# Typer app
app = typer.Typer(
    name="cogant",
    help=(
        "Codebase-to-GNN Translation Engine.\n\n"
        "Translate a repository into an Active Inference Generalized "
        "Notation for Networks (GNN) state-space model. Run "
        "[bold]cogant doctor[/bold] first to verify your environment, "
        "then [bold]cogant init <repo>[/bold] for a guided first run."
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
)


# ------------------------------------------------------- error helpers ----


def _parse_step_csv(
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


def _apply_upstream_pipeline_flags(
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
    only_list = _parse_step_csv(only, label="--upstream-gnn-only-steps")
    skip_list = _parse_step_csv(skip, label="--upstream-gnn-skip-steps", empty_means=[])
    if only_list is not None:
        config.upstream_gnn_only_steps = only_list
    if skip_list is not None:
        config.upstream_gnn_skip_steps = skip_list
    if frameworks:
        config.upstream_gnn_frameworks = frameworks
    if llm_model:
        config.upstream_gnn_llm_model = llm_model


def _render_upstream_pipeline_table(result: object) -> None:
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


def _friendly_pipeline_error(exc: BaseException, target: Path | None = None) -> None:
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
    console.print(
        "  [dim]→ File a bug at https://github.com/cogant-contributors/cogant/issues[/dim]"
    )


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


def _run_pipeline_with_progress(
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


@app.command()
def scan(
    target: str = typer.Argument(
        ".",
        help="Path or URL of the repository to scan.",
    ),
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: 'table' for human-readable Rich table, 'json' for raw.",
    ),
) -> None:
    """Scan a repository and print a quick summary.

    This is the fastest way to sanity-check that COGANT can see a
    repository before running the full pipeline. It runs only the
    static-analysis extractors (no graph build, no translation).
    """

    console.print(f"[bold blue]Scanning[/bold blue] {target}")

    try:
        session = Session.from_target(target)
        result = session.extract_static()
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        _friendly_pipeline_error(exc, Path(target))
        raise typer.Exit(code=1) from exc

    if format == "table":
        table = Table(title="Repository Summary")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="magenta")

        ingest = result.get("ingest") or {}
        modules = result.get("modules") or []
        n_modules = len(modules) if isinstance(modules, list) else len(modules)
        sym = result.get("symbols") or {}

        table.add_row("Target", target)
        table.add_row("Type", result.get("type", "unknown"))
        table.add_row("Files (ingest)", str(ingest.get("file_count", "—")))
        table.add_row("Python modules parsed", str(n_modules))
        table.add_row("Symbol summary", str(sym.get("python_modules_parsed", n_modules)))

        console.print(table)
    elif format == "json":
        console.print_json(data=result)


@app.command()
def extract_static(
    target: str = typer.Argument(
        ".",
        help="Path of the repository to analyse statically.",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help=(
            "Output directory for exported JSON artifacts. When set, the "
            "full export graph runs; otherwise only an in-memory summary is "
            "printed."
        ),
    ),
    layout_output: bool = typer.Option(
        False,
        "--layout-output",
        help=(
            "After export, move artifacts into data/, diagrams/, site/, "
            "reports/, figures/ subdirectories for easier downstream "
            "consumption."
        ),
    ),
) -> None:
    """Run static analysis only (AST, type inference, symbol tables).

    Produces the same artifacts as the ``static`` stage of
    ``cogant translate`` but without building a graph or running the
    translation rules. Use this to debug parsing problems in
    isolation.
    """
    console.print(f"[bold blue]Extracting static analysis[/bold blue] from {target}")

    session = Session.from_target(target)
    result = session.extract_static()

    if output:
        op = Path(output)
        out_dir = op if op.is_dir() or (op.suffix == "" and not op.exists()) else op.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        session.export_all(str(out_dir), layout=layout_output)
        console.print(f"[green]✓ Exported to {out_dir}[/green]")
    else:
        modules = result.get("modules") or []
        n_mod = len(modules) if isinstance(modules, list) else len(modules)
        console.print(
            Panel(
                f"Static analysis: {n_mod} Python module(s) parsed; "
                f"symbols={result.get('symbols', {})}"
            )
        )


@app.command()
def extract_dynamic(
    target: str = typer.Argument(
        ".",
        help="Path of the repository to analyse dynamically.",
    ),
    traces: str | None = typer.Option(
        None,
        "--traces",
        "-t",
        help="Optional path to a pre-recorded trace file to merge into the session.",
    ),
) -> None:
    """Run dynamic analysis (coverage databases, runtime traces).

    Requires either a ``coverage`` database under the target repo or
    a trace file passed via ``--traces``. Prefer ``cogant translate``
    when you want both static and dynamic signal — this command is
    for debugging the dynamic layer in isolation.
    """
    console.print(f"[bold blue]Extracting dynamic analysis[/bold blue] from {target}")

    session = Session.from_target(target)
    result = session.extract_dynamic()

    console.print(Panel(f"Extracted {len(result['traces'])} traces and coverage data"))


@app.command()
def graph(
    target: str = typer.Argument(
        ".",
        help="Path of the repository to build the program dependency graph for.",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional format hint; currently informational only.",
    ),
) -> None:
    """Build and summarise the program dependency graph.

    Runs the ``static`` and ``graph`` stages and prints a one-line
    node/edge count. Use ``cogant translate --skip export,validate``
    when you want the full graph JSON on disk.
    """
    console.print(f"[bold blue]Building program graph[/bold blue] for {target}")

    session = Session.from_target(target)
    session.extract_static()
    result = session.build_graph()

    nodes = result.get("nodes") or {}
    edges = result.get("edges") or {}
    n_nodes = len(nodes) if isinstance(nodes, dict) else len(nodes)
    n_edges = len(edges) if isinstance(edges, dict) else len(edges)
    console.print(Panel(f"Graph: {n_nodes} nodes, {n_edges} edges"))


@app.command()
def translate(
    target: str = typer.Argument(
        ".",
        help="Path to the repository to translate (must contain Python/JS/TS sources).",
    ),
    config_file: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="YAML or JSON pipeline config file with stage / plugin overrides.",
    ),
    skip_stages: str | None = typer.Option(
        None,
        "--skip",
        help="Comma-separated list of stages to skip (e.g. 'dynamic,validate').",
    ),
    output_dir: str = typer.Option(
        "output",
        "--output",
        "-o",
        help="Directory where bundle.json and derived artifacts are written.",
    ),
    layout_output: bool = typer.Option(
        False,
        "--layout-output",
        help=(
            "After export, move artifacts into data/, diagrams/, site/, "
            "reports/, figures/ subdirectories."
        ),
    ),
    no_dynamic: bool = typer.Option(
        False,
        "--no-dynamic",
        help=(
            "Skip the dynamic-analysis enrichment stage "
            "(coverage + trace). Faster but less accurate."
        ),
    ),
    coverage_path: str | None = typer.Option(
        None,
        "--coverage",
        help="Path to a coverage database (.coverage) or Cobertura coverage.xml.",
    ),
    trace_path: str | None = typer.Option(
        None,
        "--trace",
        help="Path to a Chrome DevTools trace JSON file for dynamic analysis.",
    ),
    incremental: str | None = typer.Option(
        None,
        "--incremental",
        help=(
            "Git ref (e.g. HEAD~1, a commit hash, or a tag) to use as the "
            "incremental baseline. Only files that changed between this "
            "ref and HEAD are re-parsed; unchanged results are served "
            "from ~/.cache/cogant when available."
        ),
    ),
    cache_dir: str | None = typer.Option(
        None,
        "--cache-dir",
        help=(
            "Override the incremental cache directory. Defaults to "
            "~/.cache/cogant. Useful for tests and benchmarks that need "
            "an isolated cache state."
        ),
    ),
    upstream_gnn_pipeline: bool = typer.Option(
        False,
        "--upstream-gnn-pipeline/--no-upstream-gnn-pipeline",
        help=(
            "After validate, drive the upstream GNN 25-step pipeline "
            "over the produced gnn_package/. Render (11) and Execute (12) "
            "are skipped by default."
        ),
    ),
    upstream_gnn_only_steps: str | None = typer.Option(
        None,
        "--upstream-gnn-only-steps",
        help="Restrict the upstream pass to these step indices, e.g. '3,5,7'.",
    ),
    upstream_gnn_skip_steps: str | None = typer.Option(
        None,
        "--upstream-gnn-skip-steps",
        help=("Override the upstream skip list (default '11,12'). Pass '' to run all 25 steps."),
    ),
    upstream_gnn_frameworks: str | None = typer.Option(
        None,
        "--upstream-gnn-frameworks",
        help="Frameworks for upstream render/execute (e.g. 'lite', 'all').",
    ),
    upstream_gnn_llm_model: str | None = typer.Option(
        None,
        "--upstream-gnn-llm-model",
        help="Override OLLAMA_MODEL for upstream step 13 (LLM).",
    ),
) -> None:
    """Translate a repository into an Active Inference GNN state-space model.

    Runs the full COGANT pipeline: ingest → static → normalize → graph
    → translate → statespace → process → export → validate. Each
    stage is logged; on failure, the bundle is still written with
    ``errors`` populated so you can post-mortem the run.
    """
    console.print(
        Panel(
            f"[bold]COGANT Pipeline[/bold]\nTranslating [cyan]{target}[/cyan] to GNN...",
            expand=False,
        )
    )

    # Fast-fail with a friendly error if the target does not exist.
    # PipelineRunner.run() otherwise produces a bundle full of stage
    # errors and exits 0, which hides the real problem from users.
    target_path = Path(target)
    if not target_path.exists():
        _friendly_pipeline_error(FileNotFoundError(target), target_path)
        raise typer.Exit(code=1)
    if target_path.is_file():
        _friendly_pipeline_error(NotADirectoryError(target), target_path)
        raise typer.Exit(code=1)

    config = PipelineConfig(output_dir=output_dir, layout_output=layout_output)
    if config_file:
        try:
            from cogant.config.loaders import ConfigLoader

            cf_path = Path(config_file)
            if cf_path.suffix.lower() in {".yaml", ".yml"}:
                cf_data = ConfigLoader.load_from_yaml(cf_path)
            else:
                cf_data = ConfigLoader.load_json_from_file(cf_path)

            # Support a `pipeline:` section or a flat layout
            pipe_data = cf_data.get("pipeline", cf_data)
            if isinstance(pipe_data, dict):
                if "stages" in pipe_data or "run_stages" in pipe_data:
                    _stages = pipe_data.get("stages") or pipe_data.get("run_stages") or []
                    config.stages = list(_stages)
                if "skip_stages" in pipe_data:
                    config.skip_stages = list(pipe_data["skip_stages"])
                if "plugins" in pipe_data:
                    config.plugins = dict(pipe_data["plugins"])
                if "output_dir" in pipe_data:
                    config.output_dir = str(pipe_data["output_dir"])
                if "verbose" in pipe_data:
                    config.verbose = bool(pipe_data["verbose"])
                if "dry_run" in pipe_data:
                    config.dry_run = bool(pipe_data["dry_run"])
                if "layout_output" in pipe_data:
                    config.layout_output = bool(pipe_data["layout_output"])
            console.print(f"[dim]Loaded config from {config_file}[/dim]")
        except Exception as e:
            console.print(f"[yellow]Warning: failed to load config {config_file}: {e}[/yellow]")
    if skip_stages:
        config.skip_stages = [s.strip() for s in skip_stages.split(",") if s.strip()]

    # CLI overrides for dynamic-analysis wiring. ``--no-dynamic`` takes
    # precedence over any coverage / trace paths the user may have
    # supplied; we still record them on the config so a subsequent call
    # without ``--no-dynamic`` still has them.
    if no_dynamic:
        config.skip_dynamic = True
        console.print("[dim]--no-dynamic: skipping dynamic analysis stage[/dim]")
    if coverage_path:
        config.coverage_path = coverage_path
    if trace_path:
        config.trace_path = trace_path
    if incremental:
        config.incremental_since = incremental
        console.print(
            f"[dim]--incremental {incremental}: only re-parsing files changed since ref[/dim]"
        )
    if cache_dir:
        config.cache_dir = cache_dir
    _apply_upstream_pipeline_flags(
        config,
        enable=upstream_gnn_pipeline,
        only=upstream_gnn_only_steps,
        skip=upstream_gnn_skip_steps,
        frameworks=upstream_gnn_frameworks,
        llm_model=upstream_gnn_llm_model,
    )

    runner = PipelineRunner()
    try:
        bundle = _run_pipeline_with_progress(runner, target, config, description_prefix="translate")
    except FileNotFoundError as exc:
        _friendly_pipeline_error(exc, Path(target))
        raise typer.Exit(code=1) from exc
    except PermissionError as exc:
        _friendly_pipeline_error(exc, Path(target))
        raise typer.Exit(code=1) from exc
    except NotADirectoryError as exc:
        _friendly_pipeline_error(exc, Path(target))
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        _friendly_pipeline_error(exc, Path(target))
        raise typer.Exit(code=1) from exc

    # Show results
    console.print("\n[bold green]Pipeline Results[/bold green]")
    results_table = Table()
    results_table.add_column("Stage", style="cyan")
    results_table.add_column("Status", style="magenta")

    for stage in config.stages:
        if stage in bundle.stage_results:
            results_table.add_row(stage, "[green]✓ Success[/green]")
        elif stage in config.skip_stages:
            results_table.add_row(stage, "[yellow]⊘ Skipped[/yellow]")
        else:
            results_table.add_row(stage, "[red]✗ Failed[/red]")

    console.print(results_table)

    if bundle.errors:
        console.print("\n[red bold]Errors:[/red bold]")
        for error in bundle.errors:
            console.print(f"  • {error}")

    inc_stats = bundle.metadata.get("incremental_stats") if bundle.metadata else None
    if inc_stats and inc_stats.get("enabled"):
        hit = "hit" if inc_stats.get("cache_hit") else "miss"
        console.print(
            f"\n[bold]Incremental:[/bold] cache {hit} "
            f"(since {inc_stats.get('since')}, "
            f"{inc_stats.get('files_reparsed', 0)}/"
            f"{inc_stats.get('files_total', 0)} files re-parsed)"
        )
        if inc_stats.get("reason"):
            console.print(f"[dim]  {inc_stats['reason']}[/dim]")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    bundle_path = out / "bundle.json"
    bundle.save_json(str(bundle_path))

    if layout_output:
        from cogant.tools.organize_example_outputs import organize_run_dir

        organize_run_dir(out, dry_run=False)

    console.print("\n[green]✓ Translation complete[/green]")
    console.print(f"Output: {output_dir}")
    console.print(f"[dim]Saved bundle: {bundle_path}[/dim]")


@app.command()
def analyze(
    target: str = typer.Argument(
        ".",
        help="Path of the repository to analyze (must contain Python/JS/TS sources).",
    ),
    incremental: str | None = typer.Option(
        None,
        "--incremental",
        help=(
            "Git commit SHA, tag, branch, or relative ref (e.g. HEAD~1) to "
            "use as the incremental baseline. Only source files that changed "
            "between this ref and HEAD are re-parsed; unchanged stage "
            "results are served from the incremental cache. Omit to run a "
            "full cold analysis."
        ),
    ),
    output_dir: str = typer.Option(
        "output",
        "--output",
        "-o",
        help="Directory where bundle.json and derived artifacts are written.",
    ),
    cache_dir: str | None = typer.Option(
        None,
        "--cache-dir",
        help=(
            "Override the incremental cache directory. Defaults to "
            "~/.cache/cogant. Useful for tests and benchmarks that need an "
            "isolated cache state."
        ),
    ),
    no_dynamic: bool = typer.Option(
        False,
        "--no-dynamic",
        help=(
            "Skip the dynamic-analysis enrichment stage. Faster, pure "
            "static-analysis mode — recommended for incremental runs."
        ),
    ),
    skip_stages: str | None = typer.Option(
        None,
        "--skip",
        help="Comma-separated list of stages to skip (e.g. 'dynamic,validate').",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress per-stage progress output (still prints summary).",
    ),
    output_format: str = typer.Option(
        "rich",
        "--format",
        help=(
            "Output format for the post-run summary: 'rich' (default, "
            "Rich tables and panels) or 'json' (machine-readable summary "
            "with target, stages_run, node_count, edge_count, mapping_count)."
        ),
    ),
    upstream_gnn_pipeline: bool = typer.Option(
        False,
        "--upstream-gnn-pipeline/--no-upstream-gnn-pipeline",
        help=(
            "After validate, drive the upstream Active Inference Institute "
            "GNN 25-step pipeline over the produced gnn_package/. "
            "Render (step 11) and Execute (step 12) are skipped by default."
        ),
    ),
    upstream_gnn_only_steps: str | None = typer.Option(
        None,
        "--upstream-gnn-only-steps",
        help=(
            "Restrict the upstream pass to these step indices, e.g. '3,5,7'. "
            "Ignored when --upstream-gnn-pipeline is off."
        ),
    ),
    upstream_gnn_skip_steps: str | None = typer.Option(
        None,
        "--upstream-gnn-skip-steps",
        help=(
            "Override the upstream pass skip list (default '11,12'). Pass '' to run all 25 steps."
        ),
    ),
    upstream_gnn_frameworks: str | None = typer.Option(
        None,
        "--upstream-gnn-frameworks",
        help=(
            "Frameworks for upstream render/execute (e.g. 'lite', 'all', "
            "'pymdp,jax'). Only consulted when those steps are enabled."
        ),
    ),
    upstream_gnn_llm_model: str | None = typer.Option(
        None,
        "--upstream-gnn-llm-model",
        help="Override OLLAMA_MODEL for upstream step 13 (LLM).",
    ),
) -> None:
    """Analyze a repository, optionally in incremental mode.

    ``cogant analyze`` is the canonical entry point for running the
    COGANT pipeline on a codebase. In its default form it is equivalent
    to ``cogant translate`` (ingest → static → normalize → graph →
    dynamic → translate → statespace → process → export → validate).

    With ``--incremental <commit>`` it switches to the fast path:

    1. Compute ``git diff --name-only <commit> HEAD`` to resolve the
       changed source file set.
    2. Look up a cached bundle for the target repository in
       ``~/.cache/cogant`` (or ``--cache-dir`` override).
    3. On a full cache hit with zero changed files, return the cached
       bundle without touching the parsers — the typical "second run
       with no edits" fast path.
    4. On a partial hit, re-parse only the changed subset, patch the
       cached stage-results via
       :func:`cogant.ingest.incremental.apply_incremental_patch`, and
       write the updated bundle/GNN output.
    5. On a cache miss or non-git target, fall back to a full cold run
       and populate the cache so the next incremental call can benefit.

    Incremental stats (``cache_hit``, ``files_reparsed``, ``files_total``,
    ``reason``) are reported after the run and are also persisted on
    ``bundle.metadata['incremental_stats']``.
    """
    json_mode = output_format.lower() == "json"
    if json_mode:
        quiet = True
    if not quiet:
        title = "[bold]COGANT Analyze[/bold]"
        if incremental:
            title += f"\n[dim]Incremental baseline: [cyan]{incremental}[/cyan][/dim]"
        console.print(
            Panel(
                f"{title}\nTarget: [cyan]{target}[/cyan]",
                expand=False,
            )
        )

    target_path = Path(target)
    if not target_path.exists():
        _friendly_pipeline_error(FileNotFoundError(target), target_path)
        raise typer.Exit(code=1)
    if target_path.is_file():
        _friendly_pipeline_error(NotADirectoryError(target), target_path)
        raise typer.Exit(code=1)

    config = PipelineConfig(output_dir=output_dir)
    if skip_stages:
        config.skip_stages = [s.strip() for s in skip_stages.split(",") if s.strip()]
    if no_dynamic:
        config.skip_dynamic = True
    if incremental:
        config.incremental_since = incremental
    if cache_dir:
        config.cache_dir = cache_dir
    _apply_upstream_pipeline_flags(
        config,
        enable=upstream_gnn_pipeline,
        only=upstream_gnn_only_steps,
        skip=upstream_gnn_skip_steps,
        frameworks=upstream_gnn_frameworks,
        llm_model=upstream_gnn_llm_model,
    )

    runner = PipelineRunner()
    try:
        if quiet:
            bundle = runner.run(target, config)
        else:
            bundle = _run_pipeline_with_progress(
                runner, target, config, description_prefix="analyze"
            )
    except FileNotFoundError as exc:
        _friendly_pipeline_error(exc, Path(target))
        raise typer.Exit(code=1) from exc
    except PermissionError as exc:
        _friendly_pipeline_error(exc, Path(target))
        raise typer.Exit(code=1) from exc
    except NotADirectoryError as exc:
        _friendly_pipeline_error(exc, Path(target))
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        _friendly_pipeline_error(exc, Path(target))
        raise typer.Exit(code=1) from exc

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    bundle_path = out / "bundle.json"
    bundle.save_json(str(bundle_path))

    inc_stats = bundle.metadata.get("incremental_stats") if bundle.metadata else None
    if json_mode:
        graph = bundle.stage_results.get("graph") or {}
        translate = bundle.stage_results.get("translate") or {}
        node_count = (
            graph.get("node_count") if isinstance(graph, dict) else getattr(graph, "node_count", 0)
        ) or 0
        edge_count = (
            graph.get("edge_count") if isinstance(graph, dict) else getattr(graph, "edge_count", 0)
        ) or 0
        mapping_count = (
            translate.get("mapping_count")
            if isinstance(translate, dict)
            else getattr(translate, "mapping_count", 0)
        ) or 0
        payload = {
            "target": str(target),
            "stages_run": [s for s in config.stages if s in bundle.stage_results],
            "node_count": int(node_count),
            "edge_count": int(edge_count),
            "mapping_count": int(mapping_count),
            "bundle_path": str(bundle_path),
            "errors": list(bundle.errors or []),
            "incremental_stats": inc_stats,
        }
        import json as _json

        print(_json.dumps(payload, indent=2, default=str))
        return
    if not quiet:
        console.print("\n[bold green]Analyze Results[/bold green]")
        results_table = Table()
        results_table.add_column("Stage", style="cyan")
        results_table.add_column("Status", style="magenta")
        for stage in config.stages:
            if stage in bundle.stage_results:
                results_table.add_row(stage, "[green]✓ Success[/green]")
            elif stage in config.skip_stages or (stage == "dynamic" and config.skip_dynamic):
                results_table.add_row(stage, "[yellow]⊘ Skipped[/yellow]")
            else:
                results_table.add_row(stage, "[red]✗ Failed[/red]")
        console.print(results_table)

    if bundle.errors and not quiet:
        console.print("\n[red bold]Errors:[/red bold]")
        for error in bundle.errors:
            console.print(f"  • {error}")

    if inc_stats and inc_stats.get("enabled"):
        hit = "hit" if inc_stats.get("cache_hit") else "miss"
        console.print(
            f"\n[bold]Incremental:[/bold] cache {hit} "
            f"(since {inc_stats.get('since')}, "
            f"{inc_stats.get('files_reparsed', 0)}/"
            f"{inc_stats.get('files_total', 0)} files re-parsed)"
        )
        if inc_stats.get("reason"):
            console.print(f"[dim]  {inc_stats['reason']}[/dim]")

    if not quiet:
        console.print("\n[green]✓ Analysis complete[/green]")
        console.print(f"[dim]Saved bundle: {bundle_path}[/dim]")


@app.command()
def statespace(
    target: str = typer.Argument(
        ".",
        help="Path of the repository to compile into a state-space model.",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional output file for the compiled state space; currently informational.",
    ),
) -> None:
    """Compile an Active Inference state-space model (S, O, A, π).

    Runs static → graph → translate → statespace and prints a count
    of states, observations, actions, and policies. The full state
    space is persisted only when you invoke ``cogant translate``.
    """
    console.print(f"[bold blue]Compiling state space[/bold blue] for {target}")

    session = Session.from_target(target)
    session.extract_static()
    session.build_graph()
    session.translate_to_gnn()
    result = session.compile_state_space()

    console.print(
        Panel(
            f"State Space:\n"
            f"  States: {len(result['states'])}\n"
            f"  Observations: {len(result['observations'])}\n"
            f"  Actions: {len(result['actions'])}\n"
            f"  Policies: {len(result['policies'])}"
        )
    )


@app.command()
def process(
    target: str = typer.Argument(
        ".",
        help="Path to the repository whose execution / process model to extract.",
    ),
    no_dynamic: bool = typer.Option(
        False,
        "--no-dynamic",
        help="Skip the dynamic-analysis enrichment stage (coverage + trace).",
    ),
) -> None:
    """Extract the pipeline / execution process model from a repository.

    Runs the pipeline without the ``export`` and ``validate`` stages
    so you get the process graph quickly. Combine with ``--no-dynamic``
    for a purely-static run on repos without a test suite.
    """

    console.print(f"[bold blue]Extracting process model[/bold blue] from {target}")

    runner = PipelineRunner()
    config = PipelineConfig(
        skip_stages=["export", "validate"],
        skip_dynamic=no_dynamic,
    )
    try:
        bundle = _run_pipeline_with_progress(runner, target, config, description_prefix="process")
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        _friendly_pipeline_error(exc, Path(target))
        raise typer.Exit(code=1) from exc

    process_model = bundle.stage_results.get("process", {})
    console.print(
        Panel(
            f"Process Model:\n"
            f"  Stages: {len(process_model.get('stages', []))}\n"
            f"  Dependencies: {len(process_model.get('dependencies', []))}"
        )
    )


@app.command()
def export_gnn(
    bundle_path: str = typer.Argument(
        ...,
        help="Path to a bundle JSON file produced by `cogant translate`.",
    ),
    output_dir: str = typer.Option(
        "output",
        "--output",
        "-o",
        help="Output directory for the re-exported artifacts.",
    ),
    format: str = typer.Option(
        "all",
        "--format",
        "-f",
        help="Output format: 'all', 'markdown', or 'json'.",
    ),
) -> None:
    """Re-export a previously generated GNN bundle in a different format.

    Useful when you want a markdown report from an existing run
    without re-running the full pipeline.
    """
    console.print(f"[bold blue]Exporting[/bold blue] {bundle_path}")

    import json

    with open(bundle_path) as f:
        data = json.load(f)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if format in ["all", "json"]:
        json_file = output_path / "bundle.json"
        with open(json_file, "w") as f:
            json.dump(data, f, indent=2)
        console.print(f"[green]✓ JSON[/green] → {json_file}")

    if format in ["all", "markdown"]:
        from cogant.export.markdown import render_bundle_markdown

        md_file = output_path / "bundle.md"
        md_file.write_text(render_bundle_markdown(data), encoding="utf-8")
        console.print(f"[green]✓ Markdown[/green] → {md_file}")

    console.print("\n[green]✓ Export complete[/green]")


@app.command()
def render(
    bundle_path: str = typer.Argument(
        ...,
        help="Path to a bundle JSON file produced by `cogant translate`.",
    ),
    output_dir: str = typer.Option(
        "output",
        "--output",
        "-o",
        help="Directory where the rendered HTML site is written.",
    ),
) -> None:
    """Render an interactive HTML site from a bundle.

    Produces a self-contained site with the program graph,
    state-space summary, and per-stage diagnostics.
    """
    console.print(f"[bold blue]Rendering site[/bold blue] for {bundle_path}")

    import json

    with open(bundle_path) as f:
        data = json.load(f)

    # Create a Bundle object from data
    from cogant.api.bundle import Bundle

    bundle = Bundle(
        target=data["target"],
        artifacts=data.get("artifacts", {}),
        stage_results=data.get("stage_results", {}),
        errors=data.get("errors", []),
        metadata=data.get("metadata", {}),
    )

    index_path = bundle.render_site(output_dir)
    console.print("[green]✓ Site rendered[/green]")
    console.print(f"  Open: {index_path}")


@app.command()
def viz(
    run_dir: str = typer.Argument(..., help="Run/output directory to rasterize"),
) -> None:
    """Generate PNGs for every Mermaid/SVG/dot/network artifact in a run directory.

    Walks ``run_dir`` recursively and emits a PNG sibling for every
    ``.mermaid``, ``.mmd``, ``.svg``, and ``.dot`` file plus ``program_graph.png``
    when ``program_graph.json`` is present. Safe to re-run; existing PNGs
    are overwritten.
    """
    from cogant.viz.png_export import render_all_pngs

    target = Path(run_dir).resolve()
    if not target.exists():
        console.print(f"[red]Path does not exist:[/red] {target}")
        raise typer.Exit(code=2)
    if not target.is_dir():
        console.print(f"[red]Not a directory:[/red] {target}")
        raise typer.Exit(code=2)

    console.print(f"[bold blue]Rasterizing visualizations[/bold blue] in {target}")
    result = render_all_pngs(target)
    total = sum(len(v) for v in result.values())
    table = Table(title="PNG output summary")
    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="right", style="green")
    for cat, paths in result.items():
        table.add_row(cat, str(len(paths)))
    console.print(table)
    console.print(f"[green]✓ Wrote {total} PNG files[/green]")


@app.command()
def validate(
    bundle_path: str = typer.Argument(
        ...,
        help="Bundle JSON path, run directory, or gnn_package directory",
    ),
    no_upstream_gnn: bool = typer.Option(
        False,
        "--no-upstream-gnn",
        help=(
            "Skip Active Inference Institute src.gnn validation on model.gnn.md "
            "(COGANT structural checks still run). Default is to run upstream. "
            "Or set COGANT_DISABLE_UPSTREAM_GNN=1."
        ),
    ),
    upstream_gnn_pipeline: bool = typer.Option(
        False,
        "--upstream-gnn-pipeline/--no-upstream-gnn-pipeline",
        help=(
            "Drive the upstream GNN 25-step pipeline over the package "
            "directory. Render (11) and Execute (12) are skipped by default."
        ),
    ),
    upstream_gnn_only_steps: str | None = typer.Option(
        None,
        "--upstream-gnn-only-steps",
        help="Restrict the upstream pass to these step indices, e.g. '3,5,7'.",
    ),
    upstream_gnn_skip_steps: str | None = typer.Option(
        None,
        "--upstream-gnn-skip-steps",
        help=("Override the upstream skip list (default '11,12'). Pass '' to run all 25 steps."),
    ),
    upstream_gnn_frameworks: str | None = typer.Option(
        None,
        "--upstream-gnn-frameworks",
        help="Frameworks for upstream render/execute (e.g. 'lite', 'all').",
    ),
    upstream_gnn_llm_model: str | None = typer.Option(
        None,
        "--upstream-gnn-llm-model",
        help="Override OLLAMA_MODEL for upstream step 13 (LLM).",
    ),
    upstream_gnn_output_dir: str | None = typer.Option(
        None,
        "--upstream-gnn-output-dir",
        help=(
            "Where the upstream pass writes per-step outputs. Defaults to "
            "<package_dir>/../upstream_pipeline/."
        ),
    ),
) -> None:
    """Run validation checks.

    Supports three inputs:

    * a JSON bundle file → runs the lightweight bundle structure checks
    * a directory containing ``gnn_package/`` → runs the full
      :class:`GNNValidator` and prints score + error/warning table
    * a directory that *is* a ``gnn_package`` → same as above
    """
    console.print(f"[bold blue]Validating[/bold blue] {bundle_path}")

    import json

    p = Path(bundle_path)

    # Route 1: directory — look for a gnn_package subdir or assume it *is* one
    gnn_dir: Path | None = None
    if p.is_dir():
        if (p / "manifest.json").exists() and (p / "model.gnn.md").exists():
            gnn_dir = p
        elif (p / "gnn_package" / "manifest.json").exists():
            gnn_dir = p / "gnn_package"

    if gnn_dir is not None:
        from cogant.gnn.validator import GNNValidator

        result = GNNValidator().validate_package(
            str(gnn_dir), upstream_gnn=False if no_upstream_gnn else None
        )
        status = (
            "[green bold]VALID[/green bold]" if result.valid else "[red bold]INVALID[/red bold]"
        )
        console.print(
            Panel(
                f"{status}  score=[magenta]{result.score:.1f}/100[/magenta]\n"
                f"errors={len(result.errors)}  warnings={len(result.warnings)}\n"
                f"package: {gnn_dir}"
            )
        )
        if result.errors:
            console.print("[red bold]Errors:[/red bold]")
            for err in result.errors[:10]:
                console.print(f"  • {err}")
        if result.warnings:
            console.print("[yellow]Warnings:[/yellow]")
            for warn in result.warnings[:10]:
                console.print(f"  • {warn}")

        if upstream_gnn_pipeline:
            from cogant.gnn.upstream_bridge.pipeline import (
                UpstreamPipelineConfig,
                run_upstream_pipeline,
            )

            only = _parse_step_csv(
                upstream_gnn_only_steps,
                label="--upstream-gnn-only-steps",
            )
            skip = _parse_step_csv(
                upstream_gnn_skip_steps,
                label="--upstream-gnn-skip-steps",
            )
            out_dir = (
                Path(upstream_gnn_output_dir)
                if upstream_gnn_output_dir
                else gnn_dir.parent / "upstream_pipeline"
            )
            cfg = UpstreamPipelineConfig(
                target_dir=gnn_dir,
                output_dir=out_dir,
                only_steps=only,
                skip_steps=skip if skip is not None else [11, 12],
                frameworks=upstream_gnn_frameworks or "lite",
                llm_model=upstream_gnn_llm_model,
            )
            console.print(
                "\n[bold]Upstream GNN 25-step pipeline:[/bold] "
                f"target=[cyan]{cfg.target_dir}[/cyan] "
                f"output=[cyan]{cfg.output_dir}[/cyan]"
            )
            pipeline_result = run_upstream_pipeline(cfg)
            _render_upstream_pipeline_table(pipeline_result)

        raise typer.Exit(code=0 if result.valid else 1)

    # Route 2: lightweight bundle-JSON structure check (file or run dir with bundle.json)
    if not p.exists():
        console.print(f"[red]✗ Not found:[/red] {bundle_path}")
        raise typer.Exit(code=2)

    json_path: Path
    if p.is_file():
        json_path = p
    elif p.is_dir():
        bundle_candidate = p / "bundle.json"
        if bundle_candidate.is_file():
            json_path = bundle_candidate
            console.print(f"[dim]Validating {json_path}[/dim]")
        else:
            console.print(f"[red]✗ Directory has no gnn_package/ and no bundle.json:[/red] {p}")
            raise typer.Exit(code=2)
    else:
        console.print(f"[red]✗ Not a file or directory:[/red] {bundle_path}")
        raise typer.Exit(code=2)

    with open(json_path) as f:
        data = json.load(f)

    checks = {
        "has_target": "target" in data,
        "has_artifacts": len(data.get("artifacts", {})) > 0,
        "has_stage_results": len(data.get("stage_results", {})) > 0,
        "errors_empty": len(data.get("errors", [])) == 0,
    }

    table = Table(title="Bundle Validation")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="magenta")

    for check, passed in checks.items():
        status = "[green]✓[/green]" if passed else "[red]✗[/red]"
        table.add_row(check, status)

    console.print(table)

    all_passed = all(checks.values())
    if all_passed:
        console.print("\n[green bold]✓ All checks passed[/green bold]")
    else:
        console.print("\n[red bold]✗ Some checks failed[/red bold]")
        raise typer.Exit(code=1)


@app.command()
def diff(
    path_a: str = typer.Argument(..., help="Baseline bundle JSON or output directory"),
    path_b: str = typer.Argument(..., help="Current bundle JSON or output directory"),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Write the full drift report to this markdown file",
    ),
) -> None:
    """Compare two bundles or output directories and report drift.

    When both arguments are directories containing COGANT output (with
    ``program_graph.json``, ``semantic_mappings.json``, and/or
    ``model.gnn.json``), the rich
    :func:`cogant.cli.diff.diff_command` is invoked: it runs
    :class:`cogant.scoring.drift.DriftAnalyzer` and
    :class:`cogant.scoring.metrics.CodebaseMetrics` and prints/writes a
    full markdown drift report including architectural drift score,
    semantic churn, and side-by-side metrics.

    When both arguments are bundle JSON files, a lightweight shallow
    diff is shown (legacy behavior).
    """
    p_a = Path(path_a)
    p_b = Path(path_b)

    if not p_a.exists() or not p_b.exists():
        console.print(f"[red]Error: path not found: {p_a if not p_a.exists() else p_b}[/red]")
        raise typer.Exit(code=2)

    # Directory-based rich diff via cogant.cli.diff.diff_command
    if p_a.is_dir() and p_b.is_dir():
        from cogant.cli.diff import diff_command

        console.print(f"[bold blue]Comparing output bundles[/bold blue] {p_a.name} ↔ {p_b.name}")
        report = diff_command(str(p_a), str(p_b))
        if output:
            out_path = Path(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(report, encoding="utf-8")
            console.print(f"[green]Wrote diff report to {out_path}[/green]")
        else:
            console.print(report)
        console.print("\n[green]✓ Diff complete[/green]")
        return

    # File-based shallow diff (legacy behavior)
    import json

    with open(p_a) as f:
        data1 = json.load(f)
    with open(p_b) as f:
        data2 = json.load(f)

    console.print(f"\nBundle 1: {data1.get('target', p_a)}")
    console.print(f"Bundle 2: {data2.get('target', p_b)}")

    errors1 = len(data1.get("errors", []))
    errors2 = len(data2.get("errors", []))

    if errors1 != errors2:
        console.print(f"  Errors: {errors1} → {errors2} ([yellow]{errors2 - errors1:+d}[/yellow])")

    stages1 = set(data1.get("stage_results", {}).keys())
    stages2 = set(data2.get("stage_results", {}).keys())

    added = stages2 - stages1
    removed = stages1 - stages2

    if added:
        console.print(f"  Added stages: {', '.join(added)}")
    if removed:
        console.print(f"  Removed stages: {', '.join(removed)}")

    console.print("\n[green]✓ Diff complete[/green]")


@app.command("changed")
def changed(
    path: Path = typer.Argument(
        Path("."),
        help="Repository path (must be a git working tree)",
    ),
    since: str = typer.Option(
        "HEAD~1",
        "--since",
        "-s",
        help="Git ref to compare against (default: HEAD~1)",
    ),
    python_only: bool = typer.Option(
        False,
        "--python-only",
        help="Only list changed Python files",
    ),
    source_only: bool = typer.Option(
        False,
        "--source-only",
        help="Only list changed source files in known languages",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Write the list of changed files to this path (one per line)",
    ),
) -> None:
    """List files changed since a git ref (incremental analysis helper).

    This powers COGANT's incremental mode: point the pipeline at the
    output to re-analyze only the files that actually need it. For
    non-git directories the command exits with a warning and an empty
    result.
    """
    from cogant.ingest.incremental import IncrementalIngester

    ingester = IncrementalIngester(path)
    if not ingester.is_git_repo():
        console.print(
            f"[yellow]Not a git repository: {path}. Incremental mode is unavailable.[/yellow]"
        )
        raise typer.Exit(code=1)

    if python_only:
        paths = ingester.python_files_changed_since(since)
        header = f"{len(paths)} Python files changed since {since}"
        rendered_lines = [str(p) for p in paths]
    elif source_only:
        paths = ingester.source_files_changed_since(since)
        header = f"{len(paths)} source files changed since {since}"
        rendered_lines = [str(p) for p in paths]
    else:
        changes = ingester.changed_since(since)
        header = f"{len(changes)} files changed since {since}"
        rendered_lines = [f"{c.change_type}\t{c.path}" for c in changes]

    console.print(f"[bold]{header}[/bold]")
    for line in rendered_lines:
        console.print(f"  {line}")

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("\n".join(rendered_lines) + "\n", encoding="utf-8")
        console.print(f"[green]Wrote {len(rendered_lines)} entries to {output}[/green]")


@app.command()
def explain(
    repo_path: str = typer.Argument(..., help="Path to the repository to analyze"),
    node_name: str = typer.Argument(..., help="Node name (or substring) to explain"),
    output_format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format: 'text' (rich console) or 'json'",
    ),
) -> None:
    """Explain why a node was assigned its Active Inference role.

    Runs the static pipeline (ingest → static → normalize → graph →
    translate) against ``repo_path``, resolves ``node_name`` to a
    concrete node in the program graph, then asks every registered
    translation rule whether it fired on that node and why. The output
    lists rules in priority order with their fired/considered status,
    the semantic kind they would produce, the edges that triggered them,
    and the Markov blanket role (μ/s/a/η) of the node.

    Exit codes:
      * ``0`` on success
      * ``1`` on pipeline / IO errors
      * ``2`` when the node name cannot be resolved
    """
    from cogant.cli.explain import (
        NodeNotFoundError,
        explain_node,
        format_json,
        format_text,
    )

    try:
        result = explain_node(repo_path, node_name)
    except NodeNotFoundError as exc:
        console.print(f"[red]Node not found:[/red] {exc}")
        raise typer.Exit(code=2) from exc
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    except RuntimeError as exc:
        console.print(f"[red]Pipeline error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    fmt = (output_format or "text").lower()
    if fmt == "json":
        print(format_json(result))
    elif fmt == "text":
        format_text(result, console=console)
    else:
        console.print(f"[red]Unknown --format {output_format!r}; use 'text' or 'json'.[/red]")
        raise typer.Exit(code=1)


@app.command()
def benchmark(
    target: str = typer.Argument(
        ".",
        help="Path of the repository to benchmark.",
    ),
    iterations: int = typer.Option(
        3,
        "--iterations",
        "-n",
        help="Number of independent pipeline runs to time.",
    ),
    no_dynamic: bool = typer.Option(
        False,
        "--no-dynamic",
        help=(
            "Skip the dynamic-analysis enrichment stage (coverage + "
            "trace). Use this to measure pure static-analysis throughput."
        ),
    ),
) -> None:
    """Benchmark pipeline wall-clock performance over several runs.

    Prints average / min / max across ``iterations``. The ``export``
    and ``validate`` stages are skipped so the measurement focuses on
    the translation core rather than IO.
    """
    import time

    console.print(f"[bold blue]Benchmarking[/bold blue] {target} ({iterations} runs)")

    times = []
    for i in range(iterations):
        console.print(f"\nRun {i + 1}/{iterations}...", end=" ")

        start = time.time()
        runner = PipelineRunner()
        config = PipelineConfig(
            skip_stages=["export", "validate"],
            skip_dynamic=no_dynamic,
        )
        runner.run(target, config)
        elapsed = time.time() - start

        times.append(elapsed)
        console.print(f"[green]{elapsed:.2f}s[/green]")

    # Show statistics
    avg = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    console.print("\n[bold]Statistics[/bold]")
    stats_table = Table()
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Time", style="magenta")

    stats_table.add_row("Average", f"{avg:.2f}s")
    stats_table.add_row("Min", f"{min_time:.2f}s")
    stats_table.add_row("Max", f"{max_time:.2f}s")

    console.print(stats_table)


# ---------------------------------------------------------------------------
# New analysis and visualization commands
# ---------------------------------------------------------------------------


@app.command("analyze-static")
def analyze_static(
    path: Path = typer.Argument(..., help="Path to Python source file or directory"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output JSON path"),
    hotspot_threshold: int = typer.Option(
        10, "--threshold", "-t", help="Complexity hotspot threshold"
    ),
) -> None:
    """Run static analysis (complexity, coupling, dead code, metrics) on source code.

    Performs lexical analysis without execution: extracts symbols, measures cyclomatic
    complexity, detects module coupling, identifies unreachable code, and computes
    Halstead metrics. Results are written to JSON if ``--output`` is specified.
    """
    console.print("[bold blue]Running static analysis[/bold blue]")
    console.print("[dim]→ Not yet fully implemented — use the Python API directly[/dim]")
    console.print("  from cogant.static import ComplexityAnalyzer, CouplingAnalyzer")
    console.print("  from cogant.static import DeadCodeAnalyzer, MetricsAnalyzer")


@app.command("analyze-graph")
def analyze_graph(
    gnn_path: Path = typer.Argument(..., help="Path to GNN bundle or ProgramGraph"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output JSON path"),
) -> None:
    """Run network analysis (centrality, communities, cycles) on a ProgramGraph.

    Computes graph-theoretic properties: node centrality (degree, betweenness, closeness),
    cycle detection, path analysis, and hotspot identification. Works on any serialized
    ProgramGraph or GNN bundle.
    """
    console.print("[bold blue]Running graph analysis[/bold blue]")
    console.print("[dim]→ Not yet fully implemented — use the Python API directly[/dim]")
    console.print("  from cogant.graph import GraphAnalyzer")
    console.print("  analyzer = GraphAnalyzer(graph)")
    console.print("  metrics = analyzer.compute_metrics()")


@app.command("visualize")
def visualize(
    path: Path = typer.Argument(..., help="Path to GNN bundle, ProgramGraph, or source"),
    format: str = typer.Option(
        "mermaid", "--format", "-f", help="Output format: mermaid|png|pdf|svg"
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output path"),
) -> None:
    """Generate a visualization (Mermaid/PNG/PDF/SVG) from a COGANT artifact.

    Converts program graphs, state-space models, and semantic structures into
    viewable diagrams. Supports multiple output formats with customizable layout
    and styling options.
    """
    console.print("[bold blue]Generating visualization[/bold blue]")
    console.print("[dim]→ Not yet fully implemented — use the Python API directly[/dim]")
    console.print("  from cogant.viz import GraphVisualizer, MermaidGenerator")
    console.print("  from cogant.viz.png_export import render_program_graph_png")


@app.command("export")
def export_cmd(
    path: Path = typer.Argument(..., help="Path to GNN bundle or ProgramGraph"),
    formats: str = typer.Option(
        "json,graphml", "--formats", "-f", help="Comma-separated export formats"
    ),
    output_dir: Path = typer.Option(Path("."), "--output-dir", "-o", help="Output directory"),
) -> None:
    """Export a COGANT artifact to multiple formats (JSON, GraphML, Parquet, SVG, etc.).

    Serializes a program graph or GNN model to multiple interchange formats for use in
    downstream tools, databases, and visualization systems. Supports JSON, GraphML,
    Parquet, SVG, and custom schema exports.
    """
    console.print("[bold blue]Exporting artifact[/bold blue]")
    console.print("[dim]→ Not yet fully implemented — use the Python API directly[/dim]")
    console.print("  from cogant.export import MultiFormatExporter, ExportFormat")
    console.print("  exporter = MultiFormatExporter(output_dir)")


# ---------------------------------------------------------------------------
# Reverse synthesis subcommands
#
# Decorator-form wrappers so AST-based audits (and future doc generators)
# enumerate every Typer command without special-casing the
# ``app.command(...)(callable)`` glue form. Implementation lives in
# ``cogant.reverse.cli`` so the reverse module remains independently
# importable and testable.
# ---------------------------------------------------------------------------


@app.command(name="reverse", help="Synthesize a Python package from a GNN markdown file.")
@functools.wraps(reverse_command)
def _reverse(*args: Any, **kwargs: Any) -> None:
    return reverse_command(*args, **kwargs)


@app.command(name="roundtrip", help="Verify forward-reverse-forward round-trip isomorphism.")
@functools.wraps(roundtrip_command)
def _roundtrip(*args: Any, **kwargs: Any) -> None:
    return roundtrip_command(*args, **kwargs)


@app.command(name="version")
def version_command() -> None:
    """Print the COGANT version (semver) and key runtime info as JSON."""

    import json as _json

    from cogant import __rust_version__, __version__

    payload = {
        "cogant": __version__,
        "python": sys.version.split()[0],
        "rust_extension": __rust_version__,
    }
    print(_json.dumps(payload, indent=2))


@app.command("upstream-gnn")
def upstream_gnn_command(
    package_dir: Path = typer.Argument(
        ...,
        help=(
            "Path to a GNN package directory (containing model.gnn.md and "
            "the 16 JSON sidecars) or to a parent directory containing one."
        ),
    ),
    output_dir: Path = typer.Option(
        Path("output/upstream_pipeline"),
        "--output-dir",
        "-o",
        help="Where the upstream pipeline writes per-step output sub-directories.",
    ),
    only_steps: str | None = typer.Option(
        None,
        "--only-steps",
        help="Restrict to these step indices, e.g. '3,5,7'.",
    ),
    skip_steps: str | None = typer.Option(
        None,
        "--skip-steps",
        help=(
            "Override the skip list (default '11,12'). "
            "Pass an empty string to skip nothing and run all 25 steps."
        ),
    ),
    frameworks: str = typer.Option(
        "lite",
        "--frameworks",
        help="Forwarded to upstream render/execute (e.g. 'lite', 'all').",
    ),
    llm_model: str | None = typer.Option(
        None,
        "--llm-model",
        help="Override OLLAMA_MODEL for upstream step 13 (LLM).",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose upstream logging.",
    ),
) -> None:
    """Drive the upstream GNN 25-step pipeline against an existing package.

    The COGANT ``analyze`` / ``translate`` / ``validate`` commands accept
    ``--upstream-gnn-pipeline`` to run this pass as part of a normal
    pipeline run. Use ``cogant upstream-gnn`` when you already have a
    ``gnn_package/`` directory on disk and want to re-execute one or more
    upstream steps without re-analysing the source repository.
    """
    from cogant.gnn.upstream_bridge.pipeline import (
        UpstreamPipelineConfig,
        run_upstream_pipeline,
    )

    pkg = package_dir.resolve()
    if not pkg.exists():
        console.print(f"[red]Package directory not found:[/red] {pkg}")
        raise typer.Exit(code=2)
    if pkg.is_dir() and not (pkg / "model.gnn.md").exists():
        candidate = pkg / "gnn_package"
        if (candidate / "model.gnn.md").exists():
            pkg = candidate
        else:
            console.print(f"[red]No model.gnn.md found at {pkg} or {pkg}/gnn_package[/red]")
            raise typer.Exit(code=2)

    only = _parse_step_csv(only_steps, label="--only-steps")
    skip = _parse_step_csv(skip_steps, label="--skip-steps", empty_means=[])

    cfg = UpstreamPipelineConfig(
        target_dir=pkg,
        output_dir=output_dir.resolve(),
        only_steps=only,
        skip_steps=skip if skip is not None else sorted({11, 12}),
        frameworks=frameworks,
        llm_model=llm_model,
        verbose=verbose,
    )
    console.print(
        Panel(
            f"[bold]Upstream GNN 25-step pass[/bold]\n"
            f"target: [cyan]{cfg.target_dir}[/cyan]\n"
            f"output: [cyan]{cfg.output_dir}[/cyan]",
            expand=False,
        )
    )
    result = run_upstream_pipeline(cfg)
    _render_upstream_pipeline_table(result)
    if not result.available or result.failure_count:
        raise typer.Exit(code=1)


# Plugin management subcommands (cogant plugin list / cogant plugin info)
app.add_typer(plugin_app, name="plugin")
app.add_typer(migrate_app, name="migrate")


if __name__ == "__main__":
    app()
