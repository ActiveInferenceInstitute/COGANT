"""CLI command registrations."""

import functools
import sys
from pathlib import Path
from typing import Any

import typer
from rich.panel import Panel
from rich.table import Table

from cogant.api.analysis_commands import (
    run_graph_analysis,
    run_multi_export,
    run_static_analysis,
    run_visualize,
)
from cogant.api.pipeline import PipelineConfig, PipelineRunner
from cogant.cli._app import (
    app,
    console,
)
from cogant.cli._app import (
    parse_step_csv as _parse_step_csv,
)
from cogant.cli._app import (
    render_upstream_pipeline_table as _render_upstream_pipeline_table,
)
from cogant.reverse.cli import reverse_command, roundtrip_command


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
    output_format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json|table",
    ),
    hotspot_threshold: int = typer.Option(
        10, "--threshold", "-t", help="Complexity hotspot threshold"
    ),
) -> None:
    """Run static analysis (complexity, coupling, dead code, metrics) on source code.

    Performs lexical analysis without execution: extracts symbols, measures cyclomatic
    complexity, detects module coupling, identifies unreachable code, and computes
    Halstead metrics. Results are written to JSON if ``--output`` is specified.
    """
    if output_format not in {"json", "table"}:
        console.print("[red]Unknown --format; use json or table.[/red]")
        raise typer.Exit(code=2)
    report = run_static_analysis(path, output=output, hotspot_threshold=hotspot_threshold)
    if output_format == "json":
        console.print_json(data=report)
        return
    table = Table(title="Static analysis")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Target", str(report["target"]))
    table.add_row("Files", str(report["file_count"]))
    table.add_row("Skipped files", str(report["skipped_file_count"]))
    table.add_row("Lines of code", str(report["total_lines_of_code"]))
    table.add_row("Hotspot threshold", str(report["hotspot_threshold"]))
    console.print(table)
    if output:
        console.print(f"[dim]Wrote {output.expanduser().resolve()}[/dim]")


@app.command("analyze-graph")
def analyze_graph(
    gnn_path: Path = typer.Argument(
        ..., help="Path to source directory, run directory, bundle, or ProgramGraph JSON"
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output JSON path"),
    output_format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json|table",
    ),
) -> None:
    """Run network analysis (centrality, communities, cycles) on a ProgramGraph.

    Computes graph-theoretic properties: node centrality (degree, betweenness, closeness),
    cycle detection, path analysis, and hotspot identification. Works on any serialized
    ProgramGraph or GNN bundle.
    """
    if output_format not in {"json", "table"}:
        console.print("[red]Unknown --format; use json or table.[/red]")
        raise typer.Exit(code=2)
    report = run_graph_analysis(gnn_path, output=output)
    if output_format == "json":
        console.print_json(data=report)
        return
    metrics = report.get("metrics", {})
    table = Table(title="Graph analysis")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    for key in (
        "node_count",
        "edge_count",
        "density",
        "avg_degree",
        "connected_components",
        "is_dag",
    ):
        table.add_row(key, str(metrics.get(key, "n/a")))
    console.print(table)
    if output:
        console.print(f"[dim]Wrote {output.expanduser().resolve()}[/dim]")


@app.command("visualize")
def visualize(
    path: Path = typer.Argument(..., help="Path to GNN bundle, ProgramGraph, or source"),
    output_format: str = typer.Option(
        "mermaid", "--format", "-f", help="Output format: mermaid|png|svg|pdf|html"
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output path"),
) -> None:
    """Generate a visualization (Mermaid/PNG/PDF/SVG) from a COGANT artifact.

    Converts program graphs, state-space models, and semantic structures into
    viewable diagrams. Supports multiple output formats with customizable layout
    and styling options.
    """
    fmt = output_format.lower()
    if fmt not in {"mermaid", "png", "svg", "pdf", "html"}:
        console.print("[red]Unknown --format; use mermaid, png, svg, pdf, or html.[/red]")
        raise typer.Exit(code=2)
    suffix = ".mmd" if fmt == "mermaid" else f".{fmt}"
    out = output or Path(f"cogant_visualization{suffix}")
    result = run_visualize(path, output=out, fmt=fmt)
    console.print(f"[green]Wrote[/green] {result}")


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
    requested = [fmt.strip() for fmt in formats.split(",") if fmt.strip()]
    manifest = run_multi_export(path, formats=requested, output_dir=output_dir)
    console.print_json(data=manifest)


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
