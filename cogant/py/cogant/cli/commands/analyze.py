"""CLI command registrations."""

from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from cogant.api.bundle import Bundle
from cogant.api.pipeline import PipelineConfig, PipelineRunner
from cogant.api.session import Session
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
    min_confidence: float | None = typer.Option(
        None,
        "--min-confidence",
        help="Minimum mapping confidence in [0.0, 1.0]; mappings scoring "
        "below this are excluded from state-space/process/export "
        "(default: pipeline default, 0.40).",
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
    if json_mode:
        config.render_visualizations = False
    if min_confidence is not None:
        if not 0.0 <= min_confidence <= 1.0:
            console.print("[red]--min-confidence must be between 0.0 and 1.0[/red]")
            raise typer.Exit(code=1)
        config.min_confidence = min_confidence
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
    """Generate review visualizations for a run directory.

    Walks ``run_dir`` recursively and emits a PNG sibling for every
    ``.mermaid``, ``.mmd``, ``.svg``, and ``.dot`` file plus ``program_graph.png``
    when ``program_graph.json`` is present. Also writes the artifact-first
    inspection dashboard and graphical abstract. Safe to re-run; existing
    generated visual artifacts are overwritten.
    """
    from cogant.viz.png import render_all_pngs

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
    table = Table(title="Visualization output summary")
    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="right", style="green")
    for cat, paths in result.items():
        table.add_row(cat, str(len(paths)))
    console.print(table)
    console.print(f"[green]✓ Wrote {total} visualization files[/green]")
