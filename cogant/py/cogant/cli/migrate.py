"""``cogant migrate`` — verify that GNN files use the current 2.0.0 schema.

Usage::

    cogant migrate path/to/file.gnn.md
The command no longer rewrites files. It exits non-zero when a file does
not declare the current GNN contract.
"""

from pathlib import Path

import typer
from rich.console import Console

from cogant.schema import CURRENT_GNN_VERSION, detect_version

console = Console()

migrate_app = typer.Typer(name="migrate", help="Verify GNN files use the current schema version.")


@migrate_app.command()
def migrate(
    path: Path = typer.Argument(..., help="Path to GNN markdown file to migrate."),
    target: str = typer.Option(
        CURRENT_GNN_VERSION,
        "--target",
        help="Target schema version.",
    ),
) -> None:
    """Detect the GNN schema version and require the current target."""
    if not path.exists():
        console.print(f"[red]Error:[/red] File not found: {path}")
        raise typer.Exit(code=1)

    original = path.read_text(encoding="utf-8")
    detected = detect_version(original)
    console.print(f"Detected schema version: [bold]{detected}[/bold]")

    if detected == target:
        console.print("[green]GNN file uses the current schema.[/green]")
        raise typer.Exit(code=0)

    console.print(f"[red]Unsupported GNN schema:[/red] expected {target}, found {detected}.")
    raise typer.Exit(code=1)
