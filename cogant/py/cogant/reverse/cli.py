"""Typer subcommands for the reverse synthesis engine.

Two commands are exposed:

* ``cogant reverse <gnn.md> -o <out_dir>`` — parse a GNN markdown file,
  plan the package, and synthesize the Python source tree.
* ``cogant roundtrip <repo_path>`` — run forward on a repository, then
  reverse on the emitted GNN, then forward again, and report the
  role-preservation score and invariant-ledger status.

Both commands are thin wrappers around :mod:`cogant.reverse.parser`,
:mod:`cogant.reverse.planner`, :mod:`cogant.reverse.synthesizer`, and
:mod:`cogant.reverse.idempotency`. All business logic lives in those
modules; this file only handles option parsing and Rich output.
"""

from __future__ import annotations

import json
import logging
import os
import py_compile
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cogant.reverse.idempotency import (
    ROLE_PRESERVATION_THRESHOLD,
    ROUNDTRIP_STATUS_DRIFT,
    ROUNDTRIP_STATUS_FAILED,
    ROUNDTRIP_STATUS_ROLE_PRESERVED,
    ROUNDTRIP_STATUS_STRUCTURALLY_ISOMORPHIC,
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
    status_colors = {
        ROUNDTRIP_STATUS_STRUCTURALLY_ISOMORPHIC: "green",
        ROUNDTRIP_STATUS_ROLE_PRESERVED: "cyan",
        ROUNDTRIP_STATUS_DRIFT: "yellow",
        ROUNDTRIP_STATUS_FAILED: "red",
    }
    status_color = status_colors.get(result.roundtrip_status, "red")
    console.print(
        Panel(
            f"[bold {status_color}]{result.roundtrip_status}[/bold {status_color}]  "
            f"role_preservation_score = {result.role_preservation_score:.2%}  "
            f"(threshold = {threshold:.0%})",
            title="Round-trip verification",
            border_style=status_color,
        )
    )

    table = Table(show_header=True)
    table.add_column("Role", style="cyan")
    table.add_column("Original", style="magenta", justify="right")
    table.add_column("Synthesized", style="green", justify="right")

    all_roles = sorted(set(result.original_roles) | set(result.synthesized_roles))
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

    invariant_rows = [
        f"{key}={'[green]✓[/green]' if ok else '[red]✗[/red]'}"
        for key, ok in sorted(result.invariants.items())
        if isinstance(ok, bool)
    ]
    if invariant_rows:
        console.print("Invariants: " + "  ".join(invariant_rows))

    if result.errors:
        for err in result.errors:
            console.print(f"[yellow]warning:[/yellow] {err}")

    if result.package_path:
        console.print(f"[dim]Synthesized package: {result.package_path}[/dim]")


def _role_confusion(result: RoundtripResult) -> list[dict[str, int | str]]:
    """Return per-role original/synthesized/delta counts."""
    rows: list[dict[str, int | str]] = []
    roles = sorted(set(result.original_roles) | set(result.synthesized_roles))
    for role in roles:
        original = int(result.original_roles.get(role, 0))
        synthesized = int(result.synthesized_roles.get(role, 0))
        rows.append(
            {
                "role": role,
                "original": original,
                "synthesized": synthesized,
                "delta": synthesized - original,
            }
        )
    return rows


def _role_edit_distance(result: RoundtripResult) -> dict[str, float | int]:
    """Return a transparent role-multiset edit-distance proxy."""
    rows = _role_confusion(result)
    missing = sum(max(0, -int(row["delta"])) for row in rows)
    extra = sum(max(0, int(row["delta"])) for row in rows)
    total_original = sum(result.original_roles.values())
    total_synthesized = sum(result.synthesized_roles.values())
    denominator = max(total_original + total_synthesized, 1)
    distance = missing + extra
    return {
        "missing": missing,
        "extra": extra,
        "distance": distance,
        "normalized": distance / denominator,
    }


def _generated_code_status(package_path: Path | None) -> dict[str, Any]:
    """Compile and, when present, pytest-smoke the synthesized package."""
    if package_path is None or not package_path.exists():
        return {
            "status": "not_available",
            "compile_status": "not_available",
            "test_status": "not_available",
            "checked_files": 0,
            "tests_path": None,
            "details": "synthesized package was not preserved on disk",
        }

    py_files = sorted(path for path in package_path.rglob("*.py") if path.is_file())
    compile_errors: list[str] = []
    for py_file in py_files:
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as exc:
            compile_errors.append(f"{py_file.relative_to(package_path)}: {exc.msg}")

    tests_path = package_path / "tests"
    test_status = "not_found"
    test_output = ""
    if tests_path.is_dir() and not compile_errors:
        env = dict(os.environ)
        parent = str(package_path.parent)
        env["PYTHONPATH"] = (
            parent if not env.get("PYTHONPATH") else parent + os.pathsep + env["PYTHONPATH"]
        )
        env["PYTEST_ADDOPTS"] = ""
        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    str(tests_path),
                    "-q",
                    "-o",
                    "addopts=",
                ],
                cwd=str(package_path.parent),
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30,
                check=False,
            )
            test_status = "passed" if completed.returncode == 0 else "failed"
            test_output = completed.stdout.strip()[-2000:]
        except (OSError, subprocess.SubprocessError, TimeoutError) as exc:
            test_status = "failed"
            test_output = f"{type(exc).__name__}: {exc}"

    compile_status = "passed" if not compile_errors else "failed"
    status = (
        "passed"
        if compile_status == "passed" and test_status in {"passed", "not_found"}
        else "failed"
    )
    return {
        "status": status,
        "compile_status": compile_status,
        "test_status": test_status,
        "checked_files": len(py_files),
        "tests_path": str(tests_path) if tests_path.is_dir() else None,
        "errors": compile_errors,
        "output": test_output,
    }


def _roundtrip_result_payload(
    result: RoundtripResult,
    threshold: float,
    *,
    include_generated_code: bool = False,
) -> dict[str, Any]:
    """Return the stable JSON payload shared by CLI output and artifacts."""
    role_confusion = _role_confusion(result)
    role_edit = _role_edit_distance(result)
    graph_edit = result.graph_delta.get("edit_distance") if result.graph_delta else role_edit
    generated_code = (
        _generated_code_status(result.package_path)
        if include_generated_code
        else {
            "status": "not_requested",
            "compile_status": "not_requested",
            "test_status": "not_requested",
        }
    )
    invariants = dict(result.invariants)
    if include_generated_code:
        invariants["generated_code_compile_ok"] = generated_code.get("compile_status") == "passed"
        invariants["generated_code_tests_ok"] = generated_code.get("test_status") in {
            "passed",
            "not_found",
        }
    generated_code_ok = generated_code.get("status") in {"passed", "not_requested"}
    return {
        "schema_version": "2.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "roundtrip_status": result.roundtrip_status,
        "role_preservation_score": result.role_preservation_score,
        "role_preserved": result.role_preserved,
        "structurally_isomorphic": result.structurally_isomorphic,
        "matrix_preserved": result.matrix_preserved,
        "gnn_sections_preserved": result.gnn_sections_preserved,
        "generated_code_ok": bool(result.generated_code_ok and generated_code_ok),
        "vacuous_roundtrip": result.vacuous_roundtrip,
        "matrix_score": result.matrix_score,
        "structural_score": result.structural_score,
        "role_confusion": role_confusion,
        "role_edit_distance": role_edit,
        "graph_edit_distance": graph_edit,
        "graph_delta": result.graph_delta,
        "gnn_diff": result.gnn_diff,
        "matrix_delta": result.matrix_delta,
        "invariants": invariants,
        "rule_evidence_trace": result.rule_evidence_trace,
        "generated_code": generated_code,
        "original_roles": result.original_roles,
        "synthesized_roles": result.synthesized_roles,
        "original_graph_summary": result.original_graph_summary,
        "synthesized_graph_summary": result.synthesized_graph_summary,
        "shape_match": result.shape_match,
        "package_path": str(result.package_path) if result.package_path else None,
        "warnings": result.warnings,
        "errors": result.errors,
        "threshold": threshold,
    }


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
    * a neutral selector helper, or ``select_policy`` when POLICY is a target role
    * one ``check_<name>`` predicate per source/target constraint
    * runtime ``A``/``B``/``C``/``D`` matrices in ``matrices.py``

    When fed back through ``cogant`` forward, the synthesized package
    is designed to preserve the source GNN's role multiset where the
    forward rules can recognise equivalent generated structures. Use
    ``cogant roundtrip`` to inspect the stronger invariant ledger on
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
    output_dir: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Directory where intermediate GNN + synthesized package are stored.",
    ),
    role_threshold: float = typer.Option(
        ROLE_PRESERVATION_THRESHOLD,
        "--threshold",
        help="Minimum role-preservation score for the weaker success tier.",
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
    """Verify round-trip status for a GNN file or a repository.

    When ``target`` is a file, it is parsed as a GNN, synthesized to
    Python, and forward is re-run on the synthesized package. When
    ``target`` is a directory, forward is run on the repository first
    to emit a GNN, then the same reverse / forward cycle follows.

    The command exits with code 0 if ``role_preservation_score >= threshold``
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

    payload = _roundtrip_result_payload(
        result,
        role_threshold,
        include_generated_code=output_dir is not None,
    )
    if output_dir is not None:
        metrics_path = output_dir.expanduser().resolve() / "metrics.json"
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        trace = result.rule_evidence_trace
        if trace:
            trace_path = output_dir.expanduser().resolve() / "rule_evidence_trace.json"
            trace_path.write_text(json.dumps(trace, indent=2, default=str) + "\n", encoding="utf-8")

    if json_output:
        console.print_json(data=payload)
    else:
        _render_roundtrip_result(result, threshold=role_threshold)

    if not result.role_preserved:
        raise typer.Exit(code=1)


__all__ = ["reverse_command", "roundtrip_command"]
