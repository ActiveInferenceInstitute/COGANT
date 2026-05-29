"""CLI command registrations."""

from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from cogant.api.pipeline import PipelineConfig, PipelineRunner
from cogant.cli._app import (
    app,
    console,
)
from cogant.cli._app import (
    apply_upstream_pipeline_flags as _apply_upstream_pipeline_flags,
)
from cogant.cli._app import (
    friendly_pipeline_error as _friendly_pipeline_error,
)
from cogant.cli._app import (
    run_pipeline_with_progress as _run_pipeline_with_progress,
)


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
    min_confidence: float | None = typer.Option(
        None,
        "--min-confidence",
        help="Minimum mapping confidence in [0.0, 1.0]; mappings scoring "
        "below this are excluded from state-space/process/export "
        "(default: pipeline default, 0.40).",
    ),
) -> None:
    """Translate a repository into an Active Inference GNN state-space model.

    Runs the full COGANT pipeline: ingest → static → normalize → graph
    → dynamic → translate → statespace → process → export → validate.
    The ``dynamic`` enrichment stage runs by default and is skipped only
    with ``--no-dynamic``. Each stage is logged; on failure, the bundle is
    still written with ``errors`` populated so you can post-mortem the run.
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
    if min_confidence is not None:
        if not 0.0 <= min_confidence <= 1.0:
            console.print("[red]--min-confidence must be between 0.0 and 1.0[/red]")
            raise typer.Exit(code=1)
        config.min_confidence = min_confidence
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


