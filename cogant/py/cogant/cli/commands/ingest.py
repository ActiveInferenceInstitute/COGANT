"""CLI command registrations."""

from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from cogant.api.session import Session
from cogant.cli._app import (
    app,
    console,
)
from cogant.cli._app import (
    friendly_pipeline_error as _friendly_pipeline_error,
)


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


