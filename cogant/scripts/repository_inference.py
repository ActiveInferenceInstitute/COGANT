"""Persist a repository export, typed model rollout, and separate roundtrip verdict."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Annotated, Final

import typer
from pydantic import TypeAdapter

from cogant.reverse.idempotency import RoundtripResult, verify_repo_roundtrip
from cogant.runtime.inference import load_inference_trace, write_inference_trace_artifact

app = typer.Typer()
DEFAULT_TARGET: Final = Path(__file__).resolve().parents[1] / "examples/control_positive/calculator"


def roundtrip_structure_verdict(result: RoundtripResult) -> str:
    """Confirm structure only for an explicit, error-free strict verdict."""
    established = (
        result.roundtrip_status == "STRUCTURALLY_ISOMORPHIC"
        and result.structurally_isomorphic is True
        and not result.errors
    )
    verdict = "Structure preserved" if established else "Structure preservation not established"
    return f"{verdict}: roundtrip_status={result.roundtrip_status}"


@app.command()
def main(
    output: Annotated[Path, typer.Option("--output", "-o")],
    target: Annotated[Path, typer.Argument(exists=True, file_okay=False)] = DEFAULT_TARGET,
    steps: Annotated[int, typer.Option(min=1, max=10_000)] = 8,
) -> None:
    """Translate a repository into a new output directory and execute its GNN."""
    try:
        output.mkdir(parents=True, exist_ok=False)
        forward = output / "forward"
        with (output / "translate.log").open("w", encoding="utf-8") as log:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "cogant.cli",
                    "translate",
                    str(target.resolve()),
                    "--no-dynamic",
                    "--output",
                    str(forward.resolve()),
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )
        trace_path = write_inference_trace_artifact(forward, steps=steps)
        trace = load_inference_trace(forward)
        result = verify_repo_roundtrip(target, output_dir=output / "roundtrip")
        (output / "roundtrip.json").write_bytes(
            TypeAdapter(RoundtripResult).dump_json(result, indent=2) + b"\n"
        )
        verdict = roundtrip_structure_verdict(result)
        report = (
            "# Repository model execution\n\n"
            f"- Source GNN SHA256: {trace.source_sha256}\n"
            f"- Matrix SHA256: {trace.matrices_sha256}\n"
            f"- Trace: {trace_path.relative_to(output)}\n"
            f"- Mode: {trace.mode}; steps: {len(trace.trace)}\n"
            f"- Policy: {trace.policy_objective}; horizon: {trace.policy_horizon}\n"
            f"- Roundtrip: {verdict}\n\n"
            "Observations are modal predictions of the exported model. Actions select "
            "transition slices; they do not invoke source-program functions. "
            "Numerical execution and roundtrip structure do not establish empirical "
            "adequacy, behavioral equivalence, or globally optimal control.\n"
        )
        (output / "report.md").write_text(report, encoding="utf-8")
        typer.echo(report)
        if result.errors or result.roundtrip_status == "FAILED":
            raise ValueError(f"roundtrip failed: {result.errors}")
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error


if __name__ == "__main__":
    app()
