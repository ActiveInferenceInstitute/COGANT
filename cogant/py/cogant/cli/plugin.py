"""CLI subcommand: ``cogant plugin list`` / ``cogant plugin info <name>``.

Thin orchestrator -- delegates to :class:`cogant.plugins.registry.PluginRegistry`.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from cogant.plugins.registry import PluginRegistry

console = Console()

plugin_app = typer.Typer(
    name="plugin",
    help="Manage and inspect COGANT plugins.",
    no_args_is_help=True,
)


@plugin_app.command("list")
def plugin_list() -> None:
    """List all discovered COGANT plugins."""
    registry = PluginRegistry()
    plugins = registry.discover()

    if not plugins:
        console.print("[dim]No plugins installed.[/dim]")
        raise typer.Exit()

    table = Table(title="COGANT Plugins")
    table.add_column("Name", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Entry Point", style="yellow")
    table.add_column("Status", style="bold")

    for p in plugins:
        status = "[green]discovered[/green]" if not p.error else f"[red]{p.error}[/red]"
        table.add_row(p.name, p.version, p.entry_point, status)

    console.print(table)


@plugin_app.command("info")
def plugin_info(
    name: str = typer.Argument(..., help="Plugin name to inspect."),
) -> None:
    """Show detailed information about a specific plugin."""
    registry = PluginRegistry()
    registry.discover()

    try:
        info = registry.get_plugin_info(name)
    except KeyError:
        console.print(f"[red]Plugin '{name}' not found.[/red]")
        raise typer.Exit(code=1)

    # Attempt to load it
    loaded_info = registry.load(name)

    console.print(f"[bold]Name:[/bold]        {loaded_info.name}")
    console.print(f"[bold]Version:[/bold]     {loaded_info.version}")
    console.print(f"[bold]Entry Point:[/bold] {loaded_info.entry_point}")
    console.print(f"[bold]Loaded:[/bold]      {loaded_info.loaded}")
    if loaded_info.error:
        console.print(f"[bold red]Error:[/bold red]      {loaded_info.error}")
