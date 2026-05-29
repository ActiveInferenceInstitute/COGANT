"""CLI command registrations."""

from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

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

    When both arguments are bundle JSON files (with ``graph``,
    ``state_space``, or related top-level keys), the semantic
    :class:`cogant.scoring.drift.DriftAnalyzer` report is produced.
    Otherwise a lightweight stage-list diff is shown.
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

    # JSON bundle diff via DriftAnalyzer when payloads look like bundles.
    import json

    with open(p_a) as f:
        data1 = json.load(f)
    with open(p_b) as f:
        data2 = json.load(f)

    bundle_keys = {"graph", "state_space", "program_graph", "mappings"}
    if (
        isinstance(data1, dict)
        and isinstance(data2, dict)
        and (bundle_keys & data1.keys() or bundle_keys & data2.keys())
    ):
        from cogant.scoring.drift import DriftAnalyzer

        console.print(f"[bold blue]Comparing bundle JSON[/bold blue] {p_a.name} ↔ {p_b.name}")
        report = DriftAnalyzer(data1, data2).generate_diff_report()
        if output:
            out_path = Path(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(report, encoding="utf-8")
            console.print(f"[green]Wrote diff report to {out_path}[/green]")
        else:
            console.print(report)
        console.print("\n[green]✓ Diff complete[/green]")
        return

    # Lightweight stage-list diff for non-bundle JSON payloads.
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
