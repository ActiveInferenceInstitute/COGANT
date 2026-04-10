"""Typer subcommands for the reverse synthesis engine.

Two commands are exposed:

* ``cogant reverse <gnn.md> -o <out_dir>`` — parse a GNN markdown file,
  plan the package, and synthesize the Python source tree.
* ``cogant roundtrip <repo_path>`` — run forward on a repository, then
  reverse on the emitted GNN, then forward again, and report the
  role-match score.

Both commands are thin wrappers around :mod:`cogant.reverse.parser`,
:mod:`cogant.reverse.planner`, :mod:`cogant.reverse.synthesizer`, and
:mod:`cogant.reverse.idempotency`. All business logic lives in those
modules; this file only handles option parsing and Rich output.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cogant.reverse.idempotency import (
    ROLE_MATCH_THRESHOLD,
    RoundtripResult,
    verify_repo_roundtrip,
    verify_roundtrip,
)
from cogant.reverse.parser import parse_gnn
from cogant.reverse.planner import plan_package
from cogant.reverse.synthesizer import synthesize_package

logger = logging.getLogger(__name__)
console = Console()


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _render_plan_summary(
    gnn_path: Path,
    package_path: Path,
    state_count: int,
    obs_count: int,
    action_count: int,
    policy_count: int,
    constraint_count: int,
) -> None:
    """Print a Rich table summarising what was written."""
    table = Table(title="Reverse synthesis summary", show_header=True)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Source GNN", str(gnn_path))
    table.add_row("Output package", str(package_path))
    table.add_row("Hidden states", str(state_count))
    table.add_row("Observations", str(obs_count))
    table.add_row("Actions", str(action_count))
    table.add_row("Policies", str(policy_count))
    table.add_row("Constraints", str(constraint_count))
    console.print(table)


def _render_roundtrip_result(result: RoundtripResult, threshold: float) -> None:
    """Print a Rich panel + table describing a round-trip outcome."""
    status_color = "green" if result.is_isomorphic else "yellow"
    status_text = "ISOMORPHIC" if result.is_isomorphic else "DRIFT"
    console.print(
        Panel(
            f"[bold {status_color}]{status_text}[/bold {status_color}]  "
            f"role_match_score = {result.role_match_score:.2%}  "
            f"(threshold = {threshold:.0%})",
            title="Round-trip verification",
            border_style=status_color,
        )
    )

    table = Table(show_header=True)
    table.add_column("Role", style="cyan")
    table.add_column("Original", style="magenta", justify="right")
    table.add_column("Synthesized", style="green", justify="right")

    all_roles = sorted(
        set(result.original_roles) | set(result.synthesized_roles)
    )
    for role in all_roles:
        table.add_row(
            role,
            str(result.original_roles.get(role, 0)),
            str(result.synthesized_roles.get(role, 0)),
        )
    console.print(table)

    if result.shape_match:
        shape_rows = [
            f"{key}={'[green]✓[/green]' if ok else '[red]✗[/red]'}"
            for key, ok in sorted(result.shape_match.items())
        ]
        console.print("Shape match: " + "  ".join(shape_rows))

    if result.errors:
        for err in result.errors:
            console.print(f"[yellow]warning:[/yellow] {err}")

    if result.package_path:
        console.print(f"[dim]Synthesized package: {result.package_path}[/dim]")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def reverse_command(
    gnn_file: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to a GNN markdown file produced by COGANT (or any conforming emitter).",
    ),
    output_dir: Path = typer.Option(
        Path("./reverse_output"),
        "--output",
        "-o",
        help="Directory where the synthesized Python package will be written.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print a machine-readable JSON summary instead of the Rich table.",
    ),
) -> None:
    """Synthesize a runnable Python package from a GNN markdown file.

    The emitted package mirrors the GNN topology:

    * one ``Factor<N>`` class per hidden-state slot
    * one ``observe_<name>`` function per observation modality
    * one ``act_<name>`` function per action
    * a ``select_policy`` helper
    * one ``check_<name>`` predicate per constraint
    * runtime ``A``/``B``/``C``/``D`` matrices in ``matrices.py``

    When fed back through ``cogant`` forward, the synthesized package
    is designed to produce a GNN that is role-multiset isomorphic to
    the input GNN. Use ``cogant roundtrip`` to verify this property on
    an existing repository.
    """
    gnn_path = gnn_file.expanduser().resolve()
    output_path = output_dir.expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        model = parse_gnn(gnn_path)
        plan = plan_package(model)
        package_path = synthesize_package(plan, model, output_path)
    except (OSError, ValueError) as exc:
        console.print(f"[red]Error during synthesis:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if json_output:
        payload = {
            "source_gnn": str(gnn_path),
            "package_path": str(package_path),
            "package_name": plan.package_name,
            "hidden_states": len(plan.state_vars),
            "observations": len(plan.obs_functions),
            "actions": len(plan.action_methods),
            "policies": len(plan.policy_functions),
            "constraints": len(plan.constraint_checks),
            "has_A_matrix": plan.has_A_matrix,
            "has_B_tensor": plan.has_B_tensor,
            "has_C_vector": plan.has_C_vector,
            "has_D_vector": plan.has_D_vector,
        }
        console.print_json(data=payload)
    else:
        _render_plan_summary(
            gnn_path=gnn_path,
            package_path=package_path,
            state_count=len(plan.state_vars),
            obs_count=len(plan.obs_functions),
            action_count=len(plan.action_methods),
            policy_count=len(plan.policy_functions),
            constraint_count=len(plan.constraint_checks),
        )


def roundtrip_command(
    target: Path = typer.Argument(
        ...,
        exists=True,
        help="Either a GNN markdown file or a repository directory to round-trip.",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Directory where intermediate GNN + synthesized package are stored.",
    ),
    role_threshold: float = typer.Option(
        ROLE_MATCH_THRESHOLD,
        "--threshold",
        help="Minimum role-match score for the round-trip to be flagged isomorphic.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print a JSON summary of the round-trip instead of the Rich table.",
    ),
    keep_tmp: bool = typer.Option(
        False,
        "--keep-tmp",
        help="Preserve the synthesized package on disk for inspection.",
    ),
) -> None:
    """Verify round-trip isomorphism for a GNN file or a repository.

    When ``target`` is a file, it is parsed as a GNN, synthesized to
    Python, and forward is re-run on the synthesized package. When
    ``target`` is a directory, forward is run on the repository first
    to emit a GNN, then the same reverse / forward cycle follows.

    The command exits with code 0 if ``role_match_score >= threshold``
    and code 1 otherwise, so it can be used in CI.
    """
    target_path = target.expanduser().resolve()

    try:
        if target_path.is_file():
            result = verify_roundtrip(
                target_path,
                tmp_dir=output_dir,
                role_threshold=role_threshold,
                keep_tmp=keep_tmp,
            )
        else:
            result = verify_repo_roundtrip(
                target_path,
                output_dir=output_dir,
                role_threshold=role_threshold,
            )
    except (OSError, ValueError) as exc:
        console.print(f"[red]Error during round-trip:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if json_output:
        payload = {
            "is_isomorphic": result.is_isomorphic,
            "role_match_score": result.role_match_score,
            "original_roles": result.original_roles,
            "synthesized_roles": result.synthesized_roles,
            "shape_match": result.shape_match,
            "package_path": str(result.package_path) if result.package_path else None,
            "errors": result.errors,
            "threshold": role_threshold,
        }
        console.print_json(data=payload)
    else:
        _render_roundtrip_result(result, threshold=role_threshold)

    if not result.is_isomorphic:
        raise typer.Exit(code=1)


__all__ = ["reverse_command", "roundtrip_command"]
