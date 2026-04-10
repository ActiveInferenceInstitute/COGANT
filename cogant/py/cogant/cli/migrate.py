"""``cogant migrate`` — detect and migrate GNN files to the current schema.

Usage::

    cogant migrate path/to/file.gnn.md
    cogant migrate path/to/file.gnn.md --dry-run

With ``--dry-run``, prints a unified diff of what would change without
writing the file.
"""

import difflib
from pathlib import Path

import typer
from rich.console import Console

from cogant.schema import SchemaVersion, detect_version, migrate_gnn

console = Console()

migrate_app = typer.Typer(name="migrate", help="Migrate GNN files to the current schema version.")


@migrate_app.command()
def migrate(
    path: Path = typer.Argument(..., help="Path to GNN markdown file to migrate."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print diff without modifying the file."),
    target: str = typer.Option(
        SchemaVersion.CURRENT,
        "--target",
        help="Target schema version.",
    ),
) -> None:
    """Detect the GNN schema version and migrate to the target version."""
    if not path.exists():
        console.print(f"[red]Error:[/red] File not found: {path}")
        raise typer.Exit(code=1)

    original = path.read_text(encoding="utf-8")
    detected = detect_version(original)
    console.print(f"Detected schema version: [bold]{detected}[/bold]")

    if detected == target:
        console.print("[green]Already at target version. No migration needed.[/green]")
        raise typer.Exit(code=0)

    migrated, changes = migrate_gnn(original, target=target)

    if not changes:
        console.print("[green]No changes required.[/green]")
        raise typer.Exit(code=0)

    for change in changes:
        console.print(f"  [cyan]->[/cyan] {change}")

    if dry_run:
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            migrated.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
        )
        console.print()
        for line in diff:
            console.print(line, end="", highlight=False)
        console.print()
    else:
        path.write_text(migrated, encoding="utf-8")
        console.print(f"[green]Migrated {path} to v{target}.[/green]")
