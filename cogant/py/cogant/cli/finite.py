from pathlib import Path

import typer
from pydantic import ValidationError

from cogant.statespace import (
    FiniteModel,
    FiniteModelSpec,
    compile_finite_model,
    verify_finite_model,
)
from cogant.statespace.finite_model import MAX_DENSE_ENTRIES
from cogant.statespace.finite_spec import FiniteModelError

finite_app = typer.Typer(help="Compile and check explicitly declared finite state-space models.")


@finite_app.command("compile")
def compile_model(
    spec: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="New JSON file; defaults to stdout."
    ),
    max_entries: int = typer.Option(
        MAX_DENSE_ENTRIES, min=1, help="Dense A/B/C/D allocation budget."
    ),
) -> None:
    """Compile a finite model specification into an immutable A/B/C/D artifact."""
    try:
        declared = FiniteModelSpec.model_validate_json(spec.read_text(encoding="utf-8"))
        model = compile_finite_model(declared, max_entries=max_entries)
        serialized = model.model_dump_json(indent=2) + "\n"
        if output is None:
            typer.echo(serialized, nl=False)
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x", encoding="utf-8") as stream:
                stream.write(serialized)
    except (OSError, UnicodeError, ValidationError, FiniteModelError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc


@finite_app.command("verify")
def verify_model(
    spec: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
    compiled: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
) -> None:
    """Check every compiled entry and its source identity; emit a JSON verdict."""
    try:
        declared = FiniteModelSpec.model_validate_json(spec.read_text(encoding="utf-8"))
        model = FiniteModel.model_validate_json(compiled.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    report = verify_finite_model(declared, model)
    typer.echo(report.model_dump_json(indent=2))
    if not report.passed:
        raise typer.Exit(code=1)
