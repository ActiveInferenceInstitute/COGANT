"""Real-world COGANT pipeline evaluation.

Runs COGANT forward pipeline on a set of real Python repos, collecting
metrics for the REAL_WORLD_EVAL.md report.

Usage (from repository root):

    PYTHONPATH=py python evaluation/run_eval.py
    PYTHONPATH=py python evaluation/run_eval.py --repo click --repo httpx
    PYTHONPATH=py python evaluation/run_eval.py --output /tmp/results.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import traceback
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
EVAL_REPOS = THIS_DIR / "eval_repos"
COGANT_PY = THIS_DIR.parent / "py"
sys.path.insert(0, str(COGANT_PY))

# Silence noisy INFO logs so the table output is clean.
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

from cogant.api.bundle import ArtifactKey  # noqa: E402
from cogant.api.pipeline import PipelineConfig, PipelineRunner  # noqa: E402

# Default eval corpus: external Python projects checked out under
# ``evaluation/eval_repos/<name>``. Override via ``--repo NAME`` (repeatable).
REPOS: list[str] = [
    "click",
    "pyyaml",
    "requests",
    "tqdm",
    "dateutil",
    "urllib3",
    "httpx",
    "fastapi",
]

# Pipeline stages exercised by the evaluation. ``dynamic`` is intentionally
# omitted so the evaluation runs offline and deterministically without
# requiring a live Python interpreter to import each target repo.
STAGES: list[str] = ["ingest", "static", "normalize", "graph", "translate", "statespace"]


def _count_gnn_sections(md_block: str) -> int:
    """Count bracket-header sections (A, B, C, D) in a GNN markdown block."""
    if not md_block:
        return 0
    count = 0
    for line in md_block.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("A[[", "B[[", "C[[", "D[[")):
            count += 1
    return count


def _matrix_nonempty(matrix: Any) -> bool:
    """Return True if ``matrix`` is a non-empty list/list-of-lists or other truthy container.

    Treats ``None`` and any container whose first row is empty as empty.
    Catches ``TypeError`` from objects with no defined truthiness so the
    function never crashes when handed an unexpected matrix backend.
    """
    if matrix is None:
        return False
    try:
        if not matrix:
            return False
        # For lists: non-empty with non-empty inner
        if isinstance(matrix, list):
            return len(matrix) > 0 and (not isinstance(matrix[0], list) or len(matrix[0]) > 0)
        return True
    except (TypeError, ValueError):
        return False


def run_one(repo_name: str, *, skip_dynamic: bool = True) -> dict[str, Any]:
    """Run the COGANT pipeline against a single eval-corpus repository.

    Args:
        repo_name: Subdirectory name under ``evaluation/eval_repos/``.
        skip_dynamic: When True (default), the dynamic-import stage is
            skipped so the evaluation runs offline without importing each
            target repo.

    Returns:
        Result dict with status, timing, graph/mapping counts, GNN matrix
        non-emptiness flags, error count, and any exception captured during
        the run. Status is one of ``"pass"``, ``"partial"``, ``"empty"``,
        or ``"fail"``.
    """
    repo_path = EVAL_REPOS / repo_name
    result: dict[str, Any] = {
        "repo": repo_name,
        "status": "fail",
        "elapsed_s": 0.0,
        "node_count": 0,
        "edge_count": 0,
        "semantic_mapping_count": 0,
        "matrix_A_nonempty": False,
        "matrix_B_nonempty": False,
        "matrix_C_nonempty": False,
        "matrix_D_nonempty": False,
        "gnn_section_count": 0,
        "bundle_error_count": 0,
        "bundle_errors": [],
        "exception": None,
    }
    if not repo_path.exists():
        result["exception"] = f"repo not cloned: {repo_path}"
        return result

    runner = PipelineRunner()
    config = PipelineConfig(stages=STAGES, skip_dynamic=skip_dynamic)
    start = time.time()
    bundle = None
    try:
        bundle = runner.run(str(repo_path), config)
    except Exception as exc:  # noqa: BLE001
        result["elapsed_s"] = round(time.time() - start, 2)
        result["exception"] = f"{type(exc).__name__}: {exc}"
        result["traceback"] = traceback.format_exc().splitlines()[-5:]
        return result
    result["elapsed_s"] = round(time.time() - start, 2)

    errors = list(getattr(bundle, "errors", []) or [])
    result["bundle_error_count"] = len(errors)
    result["bundle_errors"] = errors[:5]  # first 5 for brevity

    graph = bundle.get_artifact(ArtifactKey.PROGRAM_GRAPH)
    mappings = bundle.get_artifact(ArtifactKey.SEMANTIC_MAPPINGS)
    state_space = bundle.get_artifact(ArtifactKey.STATE_SPACE_MODEL)

    if graph is not None:
        try:
            result["node_count"] = len(graph.nodes)
            result["edge_count"] = len(graph.edges)
        except (AttributeError, TypeError) as exc:
            result["bundle_errors"].append(f"graph inspection error: {exc}")

    if mappings is not None:
        try:
            result["semantic_mapping_count"] = len(mappings)
        except TypeError:
            # Mappings artifact is not a sized container; leave count at 0.
            pass

    # Matrices from GNNMatrices (needs graph + state_space + mappings).
    md_block = ""
    if graph is not None and state_space is not None:
        try:
            from cogant.gnn.matrices import GNNMatrices

            gnn = GNNMatrices(graph, mappings or {}, state_space)
            A = gnn.compute_A()
            B = gnn.compute_B()
            C = gnn.compute_C()
            D = gnn.compute_D()
            result["matrix_A_nonempty"] = _matrix_nonempty(A)
            result["matrix_B_nonempty"] = _matrix_nonempty(B)
            result["matrix_C_nonempty"] = _matrix_nonempty(C)
            result["matrix_D_nonempty"] = _matrix_nonempty(D)
            md_block = gnn.to_gnn_markdown_block()
        except (ValueError, TypeError, AttributeError, KeyError) as exc:
            result["bundle_errors"].append(f"GNNMatrices error: {type(exc).__name__}: {exc}")

    result["gnn_section_count"] = _count_gnn_sections(md_block)

    has_graph = result["node_count"] > 0
    if result["bundle_error_count"] == 0 and result["exception"] is None:
        result["status"] = "pass" if has_graph else "empty"
    elif has_graph:
        result["status"] = "partial"
    else:
        result["status"] = "fail"
    return result


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for ``run_eval.py``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        action="append",
        default=None,
        help="Restrict the evaluation to a specific repo name (repeatable). "
        "Default: run all repos in REPOS.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=THIS_DIR / "real_world_eval_results.json",
        help="Path to write JSON results (default: %(default)s).",
    )
    parser.add_argument(
        "--include-dynamic",
        action="store_true",
        help="Include the ``dynamic`` stage (requires repo to be importable).",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Entry point for ``run_eval.py``.

    Iterates over the configured repos, runs the pipeline on each, prints a
    one-line summary per repo, and writes the full result list as JSON.
    """
    args = _build_arg_parser().parse_args(argv)
    repos = args.repo if args.repo else REPOS
    skip_dynamic = not args.include_dynamic

    results: list[dict[str, Any]] = []
    for repo in repos:
        print(f"[eval] running {repo}...", flush=True)
        r = run_one(repo, skip_dynamic=skip_dynamic)
        print(
            f"  -> status={r['status']} nodes={r['node_count']} "
            f"edges={r['edge_count']} mappings={r['semantic_mapping_count']} "
            f"errors={r['bundle_error_count']} t={r['elapsed_s']}s",
            flush=True,
        )
        if r.get("exception"):
            print(f"  !! exception: {r['exception']}", flush=True)
        results.append(r)

    out_json = Path(args.output)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(results, indent=2, default=str))
    print(f"[eval] wrote {out_json}", flush=True)


if __name__ == "__main__":
    main()
