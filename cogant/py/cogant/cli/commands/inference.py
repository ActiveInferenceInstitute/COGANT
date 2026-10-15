from pathlib import Path

import typer
from pydantic import StrictInt, TypeAdapter

from cogant.cli._app import app
from cogant.runtime.inference import run_gnn_inference
from cogant.runtime.inference_records import InferenceOptions


@app.command("infer")
def infer(
    source: Path = typer.Argument(..., exists=True, dir_okay=False),
    output: Path | None = typer.Option(None, "--output", "-o"),
    steps: int | None = typer.Option(None, min=1, max=10_000),
    observations: Path | None = typer.Option(None, exists=True, dir_okay=False),
    overwrite: bool = typer.Option(False, help="Replace an existing generated trace explicitly."),
    max_work_units: int = typer.Option(100_000_000, min=1),
) -> None:
    """Run exported GNN matrices; optionally condition on a JSON array of observation indices."""
    try:
        observed = (
            TypeAdapter(tuple[StrictInt, ...]).validate_json(observations.read_bytes())
            if observations is not None
            else None
        )
        count = steps if steps is not None else (len(observed) if observed is not None else 8)
        options = InferenceOptions(
            steps=count, observations=observed, max_work_units=max_work_units
        )
        result = run_gnn_inference(source.read_bytes().decode("utf-8"), options)
        result = result.model_copy(update={"source_artifact": str(source)})
        payload = result.model_dump_json(indent=2) + "\n"
        if output is None:
            typer.echo(payload, nl=False)
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("w" if overwrite else "x", encoding="utf-8") as stream:
                stream.write(payload)
    except (OSError, UnicodeError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
