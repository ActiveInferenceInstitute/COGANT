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

from pathlib import Path
from typing import Optional, List
import logging

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.syntax import Syntax

from cogant.api.session import Session
from cogant.api.pipeline import PipelineRunner, PipelineConfig
from cogant.api.bundle import Bundle
from cogant.api.review import ReviewAPI
from cogant.cli.doctor import doctor_command, run_doctor, render_report
from cogant.cli.migrate import migrate_app
from cogant.cli.plugin import plugin_app
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


# Extensions COGANT can currently parse. Kept in sync with
# ``cogant.ingest`` loosely — the set is used by ``init``'s repo-health
# sniff and ``_estimate_pipeline_seconds``.
_SOURCE_EXTENSIONS = {
    ".py",
    ".pyi",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
}


def _friendly_pipeline_error(exc: BaseException, target: Optional[Path] = None) -> None:
    """Render a user-facing error message for a pipeline failure.

    This is the single place where exceptions bubbling out of the
    Session / PipelineRunner APIs are translated into human text. The
    caller is expected to raise ``typer.Exit(code=1)`` afterwards; we
    deliberately do not do it here so unit tests can assert on the
    printed message without also catching the exit.
    """

    if isinstance(exc, FileNotFoundError):
        console.print(f"[red]Error:[/red] Repository not found: {target or exc}")
        console.print(
            "  [dim]→ Check the path exists and contains Python/JS/TS files[/dim]"
        )
        return
    if isinstance(exc, PermissionError):
        console.print(f"[red]Error:[/red] Permission denied: {target or exc}")
        console.print(
            "  [dim]→ Check read permissions on the repository and its files[/dim]"
        )
        return
    if isinstance(exc, NotADirectoryError):
        console.print(
            f"[red]Error:[/red] Expected a repository directory but got a file: "
            f"{target or exc}"
        )
        return

    # Fallback — print exception type + message, suggest doctor.
    console.print(f"[red]Unexpected error:[/red] {type(exc).__name__}: {exc}")
    console.print("  [dim]→ Run [bold]cogant doctor[/bold] to check your environment[/dim]")
    console.print(
        "  [dim]→ File a bug at "
        "https://github.com/cogant-contributors/cogant/issues[/dim]"
    )


def _count_source_files(root: Path) -> int:
    """Best-effort count of parseable source files below ``root``.

    Used for ``init`` time estimation and repo-validity sniffing. It
    walks at most a few thousand files and skips obvious noise
    directories so first-run UX stays snappy.
    """

    if not root.exists() or not root.is_dir():
        return 0

    skip_dirs = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        "dist",
        "build",
        "target",
    }

    count = 0
    # Hard cap so pathological monorepos do not freeze the CLI.
    file_budget = 5000
    for path in root.rglob("*"):
        if file_budget <= 0:
            break
        file_budget -= 1
        # Skip noise directories by looking at path parts.
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in _SOURCE_EXTENSIONS:
            count += 1
    return count


def _estimate_pipeline_seconds(file_count: int) -> float:
    """Rough wall-clock estimate for a full ``translate`` run.

    The 50ms/file heuristic comes from the v0.1.0 benchmark table on
    the control-positive fixtures; it overestimates for tiny repos and
    underestimates for very large ones, but is honest enough to tell
    users whether they are waiting seconds or minutes.
    """

    if file_count <= 0:
        return 0.0
    # 50ms per file + a 2s constant-time overhead for pipeline setup.
    return 2.0 + (file_count * 0.05)


def _format_duration(seconds: float) -> str:
    if seconds < 1.0:
        return "<1s"
    if seconds < 60.0:
        return f"{seconds:.0f}s"
    minutes, rem = divmod(seconds, 60.0)
    return f"{int(minutes)}m {int(rem)}s"


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
        console.print(f"  Config: {config_file}" + (" [dim](created)[/dim]" if config_created else " [dim](existing)[/dim]"))
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
            console.print(
                "[yellow]--run requested but no source files found; skipping.[/yellow]"
            )
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
            raise typer.Exit(code=1)

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
        raise typer.Exit(code=1)

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
        import json

        console.print_json(data=result)


@app.command()
def extract_static(
    target: str = typer.Argument(
        ".",
        help="Path of the repository to analyse statically.",
    ),
    output: Optional[str] = typer.Option(
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
    traces: Optional[str] = typer.Option(
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

    console.print(
        Panel(f"Extracted {len(result['traces'])} traces and coverage data")
    )


@app.command()
def graph(
    target: str = typer.Argument(
        ".",
        help="Path of the repository to build the program dependency graph for.",
    ),
    output: Optional[str] = typer.Option(
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
    config_file: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="YAML or JSON pipeline config file with stage / plugin overrides.",
    ),
    skip_stages: Optional[str] = typer.Option(
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
    coverage_path: Optional[str] = typer.Option(
        None,
        "--coverage",
        help="Path to a coverage database (.coverage) or Cobertura coverage.xml.",
    ),
    trace_path: Optional[str] = typer.Option(
        None,
        "--trace",
        help="Path to a Chrome DevTools trace JSON file for dynamic analysis.",
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
                    config.stages = list(pipe_data.get("stages") or pipe_data.get("run_stages"))
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

    runner = PipelineRunner()
    try:
        bundle = _run_pipeline_with_progress(
            runner, target, config, description_prefix="translate"
        )
    except FileNotFoundError as exc:
        _friendly_pipeline_error(exc, Path(target))
        raise typer.Exit(code=1)
    except PermissionError as exc:
        _friendly_pipeline_error(exc, Path(target))
        raise typer.Exit(code=1)
    except NotADirectoryError as exc:
        _friendly_pipeline_error(exc, Path(target))
        raise typer.Exit(code=1)
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        _friendly_pipeline_error(exc, Path(target))
        raise typer.Exit(code=1)

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

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    bundle_path = out / "bundle.json"
    bundle.save_json(str(bundle_path))

    if layout_output:
        from cogant.tools.organize_example_outputs import organize_run_dir

        organize_run_dir(out, dry_run=False)

    console.print(f"\n[green]✓ Translation complete[/green]")
    console.print(f"Output: {output_dir}")
    console.print(f"[dim]Saved bundle: {bundle_path}[/dim]")


@app.command()
def statespace(
    target: str = typer.Argument(
        ".",
        help="Path of the repository to compile into a state-space model.",
    ),
    output: Optional[str] = typer.Option(
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
        bundle = _run_pipeline_with_progress(
            runner, target, config, description_prefix="process"
        )
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        _friendly_pipeline_error(exc, Path(target))
        raise typer.Exit(code=1)

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

    with open(bundle_path, "r") as f:
        data = json.load(f)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if format in ["all", "json"]:
        json_file = output_path / "bundle.json"
        with open(json_file, "w") as f:
            json.dump(data, f, indent=2)
        console.print(f"[green]✓ JSON[/green] → {json_file}")

    if format in ["all", "markdown"]:
        md_file = output_path / "bundle.md"
        with open(md_file, "w") as f:
            f.write(f"# COGANT Export\n\nTarget: {data['target']}\n")
        console.print(f"[green]✓ Markdown[/green] → {md_file}")

    console.print(f"\n[green]✓ Export complete[/green]")


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

    with open(bundle_path, "r") as f:
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
    console.print(f"[green]✓ Site rendered[/green]")
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
    gnn_dir: Optional[Path] = None
    if p.is_dir():
        if (p / "manifest.json").exists() and (p / "model.gnn.md").exists():
            gnn_dir = p
        elif (p / "gnn_package" / "manifest.json").exists():
            gnn_dir = p / "gnn_package"

    if gnn_dir is not None:
        from cogant.gnn.validator import GNNValidator

        result = GNNValidator().validate_package(str(gnn_dir))
        status = "[green bold]VALID[/green bold]" if result.valid else "[red bold]INVALID[/red bold]"
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
            console.print(
                f"[red]✗ Directory has no gnn_package/ and no bundle.json:[/red] {p}"
            )
            raise typer.Exit(code=2)
    else:
        console.print(f"[red]✗ Not a file or directory:[/red] {bundle_path}")
        raise typer.Exit(code=2)

    with open(json_path, "r") as f:
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
    output: Optional[str] = typer.Option(
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

        console.print(
            f"[bold blue]Comparing output bundles[/bold blue] {p_a.name} ↔ {p_b.name}"
        )
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

    with open(p_a, "r") as f:
        data1 = json.load(f)
    with open(p_b, "r") as f:
        data2 = json.load(f)

    console.print(f"\nBundle 1: {data1.get('target', p_a)}")
    console.print(f"Bundle 2: {data2.get('target', p_b)}")

    errors1 = len(data1.get("errors", []))
    errors2 = len(data2.get("errors", []))

    if errors1 != errors2:
        console.print(
            f"  Errors: {errors1} → {errors2} ([yellow]{errors2-errors1:+d}[/yellow])"
        )

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
    output: Optional[Path] = typer.Option(
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
            f"[yellow]Not a git repository: {path}. "
            f"Incremental mode is unavailable.[/yellow]"
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
    node_name: str = typer.Argument(
        ..., help="Node name (or substring) to explain"
    ),
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
        raise typer.Exit(code=2)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    except RuntimeError as exc:
        console.print(f"[red]Pipeline error:[/red] {exc}")
        raise typer.Exit(code=1)

    fmt = (output_format or "text").lower()
    if fmt == "json":
        print(format_json(result))
    elif fmt == "text":
        format_text(result, console=console)
    else:
        console.print(
            f"[red]Unknown --format {output_format!r}; "
            f"use 'text' or 'json'.[/red]"
        )
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
        console.print(f"\nRun {i+1}/{iterations}...", end=" ")

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
# Reverse synthesis subcommands
#
# These are registered via ``app.command`` after the reverse_command /
# roundtrip_command callables are imported from ``cogant.reverse.cli``.
# Keeping the implementation in ``cogant.reverse.cli`` means the reverse
# module can be tested and imported independently of the global Typer
# app — the registration here is purely glue.
# ---------------------------------------------------------------------------

app.command(name="reverse", help="Synthesize a Python package from a GNN markdown file.")(
    reverse_command
)
app.command(name="roundtrip", help="Verify forward-reverse-forward round-trip isomorphism.")(
    roundtrip_command
)

# Plugin management subcommands (cogant plugin list / cogant plugin info)
app.add_typer(plugin_app, name="plugin")
app.add_typer(migrate_app, name="migrate")


if __name__ == "__main__":
    app()
