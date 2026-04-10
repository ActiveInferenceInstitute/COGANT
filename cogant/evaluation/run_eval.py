"""Real-world COGANT pipeline evaluation.

Runs COGANT forward pipeline on a set of real Python repos, collecting
metrics for the REAL_WORLD_EVAL.md report.

Usage (from repository root):

    PYTHONPATH=py python evaluation/run_eval.py
"""
from __future__ import annotations

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

REPOS = [
    "click",
    "pyyaml",
    "requests",
    "tqdm",
    "dateutil",
    "urllib3",
    "httpx",
    "fastapi",
]

STAGES = ["ingest", "static", "normalize", "graph", "translate", "statespace"]


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
    if matrix is None:
        return False
    try:
        if not matrix:
            return False
        # For lists: non-empty with non-empty inner
        if isinstance(matrix, list):
            return len(matrix) > 0 and (
                not isinstance(matrix[0], list) or len(matrix[0]) > 0
            )
        return True
    except Exception:
        return False


def run_one(repo_name: str) -> dict[str, Any]:
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
    config = PipelineConfig(stages=STAGES, skip_dynamic=True)
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
        except Exception as exc:  # noqa: BLE001
            result["bundle_errors"].append(f"graph inspection error: {exc}")

    if mappings is not None:
        try:
            result["semantic_mapping_count"] = len(mappings)
        except Exception:
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
        except Exception as exc:  # noqa: BLE001
            result["bundle_errors"].append(
                f"GNNMatrices error: {type(exc).__name__}: {exc}"
            )

    result["gnn_section_count"] = _count_gnn_sections(md_block)

    has_graph = result["node_count"] > 0
    if result["bundle_error_count"] == 0 and result["exception"] is None:
        result["status"] = "pass" if has_graph else "empty"
    elif has_graph:
        result["status"] = "partial"
    else:
        result["status"] = "fail"
    return result


def main() -> None:
    results = []
    for repo in REPOS:
        print(f"[eval] running {repo}...", flush=True)
        r = run_one(repo)
        print(
            f"  -> status={r['status']} nodes={r['node_count']} "
            f"edges={r['edge_count']} mappings={r['semantic_mapping_count']} "
            f"errors={r['bundle_error_count']} t={r['elapsed_s']}s",
            flush=True,
        )
        if r.get("exception"):
            print(f"  !! exception: {r['exception']}", flush=True)
        results.append(r)

    out_json = THIS_DIR / "real_world_eval_results.json"
    out_json.write_text(json.dumps(results, indent=2, default=str))
    print(f"[eval] wrote {out_json}", flush=True)


if __name__ == "__main__":
    main()
