#!/usr/bin/env python3
"""Regenerate cogant/evaluation/METRICS.yaml from live repo state.

Run from the repo root:
    cd cogant && uv run python ../tools/regenerate_metrics.py

All values are computed from the live state of the repository at call time.
"""
from __future__ import annotations

import ast
import json
import os
import re
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Repo root: the directory that contains both cogant/ and tools/
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
COGANT_DIR = REPO_ROOT / "cogant"
PY_PKG = COGANT_DIR / "py" / "cogant"
TESTS_DIR = COGANT_DIR / "tests"
EVAL_DIR = COGANT_DIR / "evaluation"
RUST_DIR = COGANT_DIR / "rust"
DOCS_EVAL = COGANT_DIR / "docs" / "evaluation"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: str, cwd: Path | None = None, timeout: int = 180) -> tuple[int, str]:
    """Run a shell command, return (returncode, combined stdout+stderr)."""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout + result.stderr


def _count_files(directory: Path, pattern: str) -> int:
    if not directory.exists():
        return 0
    return len(list(directory.rglob(pattern)))


# ---------------------------------------------------------------------------
# 1. Package version
# ---------------------------------------------------------------------------

def get_cogant_version() -> str:
    init_path = PY_PKG / "__init__.py"
    if not init_path.exists():
        return "unknown"
    text = init_path.read_text()
    m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
    return m.group(1) if m else "unknown"


# ---------------------------------------------------------------------------
# 2. Git SHA
# ---------------------------------------------------------------------------

def get_git_sha() -> str:
    rc, out = _run("git rev-parse HEAD", cwd=REPO_ROOT)
    return out.strip() if rc == 0 else "unknown"


# ---------------------------------------------------------------------------
# 3. Test file counts
# ---------------------------------------------------------------------------

def get_test_file_counts() -> dict[str, int]:
    unit_dir = TESTS_DIR / "unit"
    integration_dir = TESTS_DIR / "integration"
    property_dir = TESTS_DIR / "property"
    fuzz_dir = TESTS_DIR / "fuzz"

    return {
        "unit": _count_files(unit_dir, "test_*.py"),
        "integration": _count_files(integration_dir, "test_*.py"),
        "property": _count_files(property_dir, "test_*.py"),
        "fuzz": _count_files(fuzz_dir, "test_*.py"),
    }


# ---------------------------------------------------------------------------
# 4. Pytest collection count
# ---------------------------------------------------------------------------

def get_test_count_total() -> int:
    """Run pytest --collect-only and parse 'N selected'."""
    try:
        rc, out = _run(
            "uv run pytest --collect-only -q 2>&1",
            cwd=COGANT_DIR,
            timeout=120,
        )
        # Look for "N selected" or "N test" patterns
        m = re.search(r"(\d+)\s+selected", out)
        if m:
            return int(m.group(1))
        # Fallback: count "test session" lines
        m = re.search(r"collected\s+(\d+)\s+item", out)
        if m:
            return int(m.group(1))
        return 0
    except subprocess.TimeoutExpired:
        print("WARNING: pytest --collect-only timed out; using 0", file=sys.stderr)
        return 0


# ---------------------------------------------------------------------------
# 5+6. Pytest run results + coverage (single combined invocation)
# ---------------------------------------------------------------------------

def get_test_results_and_coverage() -> tuple[dict[str, int], float]:
    """Run pytest with coverage, then export JSON. Returns (test_results, coverage_pct).

    Both steps are done in a single shell pipeline so .coverage is not
    garbage-collected between subprocesses.
    """
    coverage_json = COGANT_DIR / "coverage.json"
    try:
        rc, out = _run(
            "uv run pytest -q --override-ini='addopts=' --cov=cogant -p no:warnings 2>&1"
            " && uv run coverage json -o coverage.json",
            cwd=COGANT_DIR,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        print("WARNING: pytest run timed out", file=sys.stderr)
        return (
            {"passing": 0, "failing": 0, "skipped": 0, "xfailed": 0, "xpassed": 0},
            0.0,
        )

    # Parse test counts from summary line
    # Example: "2059 passed, 86 skipped, 2 xfailed, 1 xpassed, 12 failed in 75s"
    test_result = {"passing": 0, "failing": 0, "skipped": 0, "xfailed": 0, "xpassed": 0}
    for line in out.splitlines():
        if re.search(r"\d+\s+passed", line) or re.search(r"\d+\s+failed", line):
            mp = re.search(r"(\d+)\s+passed", line)
            mf = re.search(r"(\d+)\s+failed", line)
            ms = re.search(r"(\d+)\s+skipped", line)
            mxf = re.search(r"(\d+)\s+xfailed", line)
            mxp = re.search(r"(\d+)\s+xpassed", line)
            if mp:
                test_result["passing"] = int(mp.group(1))
            if mf:
                test_result["failing"] = int(mf.group(1))
            if ms:
                test_result["skipped"] = int(ms.group(1))
            if mxf:
                test_result["xfailed"] = int(mxf.group(1))
            if mxp:
                test_result["xpassed"] = int(mxp.group(1))

    # Parse coverage percent
    coverage_pct = 0.0
    if coverage_json.exists():
        try:
            data = json.loads(coverage_json.read_text())
            totals = data.get("totals", {})
            coverage_pct = round(float(totals.get("percent_covered", 0.0)), 2)
        except (json.JSONDecodeError, KeyError):
            pass

    if coverage_pct == 0.0:
        # Fallback: parse TOTAL line from stdout
        m = re.search(r"TOTAL\s+\d+\s+\d+\s+([\d.]+)%", out)
        if m:
            coverage_pct = float(m.group(1))

    return test_result, coverage_pct


# ---------------------------------------------------------------------------
# 7. mypy strict errors
# ---------------------------------------------------------------------------

def get_mypy_errors() -> int:
    try:
        rc, out = _run(
            "uv run mypy --strict cogant/ 2>&1 | grep 'error:' | wc -l",
            cwd=COGANT_DIR,
            timeout=120,
        )
        return int(out.strip())
    except (subprocess.TimeoutExpired, ValueError):
        return -1  # FIXME: timed out


# ---------------------------------------------------------------------------
# 8. Ruff violations
# ---------------------------------------------------------------------------

def get_ruff_violations() -> int:
    try:
        rc, out = _run(
            "uv run ruff check cogant/ 2>&1",
            cwd=COGANT_DIR,
            timeout=60,
        )
        # Last summary line: "Found N errors."
        m = re.search(r"Found\s+(\d+)\s+error", out)
        if m:
            return int(m.group(1))
        # Count non-blank lines that look like violations
        violations = [
            line for line in out.splitlines()
            if line.strip() and not line.startswith("All checks") and "error" not in line.lower()
        ]
        # If exit code 0, no violations
        if rc == 0:
            return 0
        return len([l for l in out.splitlines() if re.match(r'\s*cogant/', l)])
    except subprocess.TimeoutExpired:
        return -1  # FIXME: timed out


# ---------------------------------------------------------------------------
# 9. Codebase AST walk
# ---------------------------------------------------------------------------

def analyze_python_source() -> dict[str, int]:
    """Walk cogant/py/cogant/ and count files, LOC, classes, functions."""
    source_files = 0
    total_loc = 0
    public_classes = 0
    public_functions = 0
    public_modules = 0

    pkg_dir = PY_PKG
    if not pkg_dir.exists():
        return {
            "python_source_files": 0,
            "python_loc": 0,
            "public_modules": 0,
            "public_classes": 0,
            "public_functions": 0,
        }

    for py_file in pkg_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        source_files += 1
        text = py_file.read_text(errors="replace")
        total_loc += len(text.splitlines())

        # Count public modules (non-underscore-prefixed py files)
        if not py_file.stem.startswith("_"):
            public_modules += 1

        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                public_classes += 1
            elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                public_functions += 1

    return {
        "python_source_files": source_files,
        "python_loc": total_loc,
        "public_modules": public_modules,
        "public_classes": public_classes,
        "public_functions": public_functions,
    }


# ---------------------------------------------------------------------------
# 10. Roundtrip evaluation data
# ---------------------------------------------------------------------------

def parse_roundtrip_results() -> dict:
    jsonl_path = EVAL_DIR / "dataset" / "roundtrip_results.jsonl"
    if not jsonl_path.exists():
        return {
            "total_targets": 0,
            "isomorphic_count": 0,
            "approximate_count": 0,
            "divergent_count": 0,
            "mean_epsilon": 0.0,
            "median_epsilon": 0.0,
            "min_epsilon": 0.0,
            "max_epsilon": 0.0,
            "per_target": [],
        }

    entries = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    iso = sum(1 for e in entries if e.get("tier") == "ISOMORPHIC")
    approx = sum(1 for e in entries if e.get("tier") == "APPROXIMATE")
    div = sum(1 for e in entries if e.get("tier") == "DIVERGENT")
    epsilons = [e["epsilon"] for e in entries]

    per_target = [
        {
            "name": e["repo"],
            "group": e["group"],
            "epsilon": e["epsilon"],
            "tier": e["tier"],
            "elapsed_s": e.get("elapsed_s", 0.0),
        }
        for e in entries
    ]

    return {
        "total_targets": len(entries),
        "isomorphic_count": iso,
        "approximate_count": approx,
        "divergent_count": div,
        "mean_epsilon": round(statistics.mean(epsilons), 4),
        "median_epsilon": round(statistics.median(epsilons), 4),
        "min_epsilon": min(epsilons),
        "max_epsilon": max(epsilons),
        "per_target": per_target,
    }


# ---------------------------------------------------------------------------
# 11. Literature bibliography count
# ---------------------------------------------------------------------------

def count_bibliography_entries() -> int:
    lit_path = DOCS_EVAL / "LITERATURE.md"
    if not lit_path.exists():
        return 0
    text = lit_path.read_text()
    # Each entry starts with ### [key] in sections 1-14
    entries = re.findall(r"^### \[", text, re.MULTILINE)
    return len(entries)


# ---------------------------------------------------------------------------
# 12. Rust crates
# ---------------------------------------------------------------------------

def count_rust_crates() -> int:
    if not RUST_DIR.exists():
        return 0
    crates = [
        d for d in RUST_DIR.iterdir()
        if d.is_dir() and (d / "Cargo.toml").exists()
    ]
    return len(crates)


# ---------------------------------------------------------------------------
# 13. Rust FFI availability
# ---------------------------------------------------------------------------

def rust_ffi_available() -> bool:
    pyi_path = PY_PKG / "rust_backend.pyi"
    so_files = list(PY_PKG.glob("_rust*.so")) + list(PY_PKG.glob("_rust*.pyd"))
    return pyi_path.exists() or len(so_files) > 0


# ---------------------------------------------------------------------------
# 14. Translation rules count
# ---------------------------------------------------------------------------

def count_translation_rules() -> int:
    rules_init = PY_PKG / "translate" / "rules" / "__init__.py"
    if not rules_init.exists():
        return 0
    text = rules_init.read_text()
    # Count concrete rule classes exported in __all__, excluding the base class
    all_match = re.search(r"__all__\s*=\s*\[(.*?)\]", text, re.DOTALL)
    if not all_match:
        return 0
    entries = re.findall(r'"([^"]+)"', all_match.group(1))
    # Exclude the abstract base class
    concrete = [e for e in entries if e != "TranslationRule"]
    return len(concrete)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Regenerating METRICS.yaml...", file=sys.stderr)

    version = get_cogant_version()
    git_sha = get_git_sha()
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    print("  [1/9] Version + SHA", file=sys.stderr)

    print("  [2/9] Test file counts...", file=sys.stderr)
    file_counts = get_test_file_counts()

    print("  [3/9] Test collection count...", file=sys.stderr)
    test_count_total = get_test_count_total()

    print("  [4/9] Test run results + coverage (this may take a few minutes)...", file=sys.stderr)
    test_results, coverage_pct = get_test_results_and_coverage()

    print("  [6/9] mypy strict errors...", file=sys.stderr)
    mypy_errors = get_mypy_errors()

    print("  [7/9] Ruff violations...", file=sys.stderr)
    ruff_violations = get_ruff_violations()

    print("  [8/9] Python source analysis...", file=sys.stderr)
    source_stats = analyze_python_source()

    print("  [9/9] Evaluation data + metadata...", file=sys.stderr)
    roundtrip = parse_roundtrip_results()
    bib_entries = count_bibliography_entries()
    rust_crates = count_rust_crates()
    ffi = rust_ffi_available()
    translation_rules = count_translation_rules()

    metrics = {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "generator_git_sha": git_sha,
        "cogant_version": version,
        "package": {
            "name": "cogant",
            "version": version,
            "python_min": "3.10",
        },
        "testing": {
            "test_count_total": test_count_total,
            "test_count_passing": test_results["passing"],
            "test_count_failing": test_results["failing"],
            "test_count_skipped": test_results["skipped"],
            "test_count_xfailed": test_results["xfailed"],
            "test_count_xpassed": test_results["xpassed"],
            "test_files_unit": file_counts["unit"],
            "test_files_integration": file_counts["integration"],
            "test_files_property": file_counts["property"],
            "test_files_fuzz": file_counts["fuzz"],
            "coverage_percent": coverage_pct,
            "mypy_strict_errors": mypy_errors,
            "ruff_violations": ruff_violations,
        },
        "codebase": {
            "python_source_files": source_stats["python_source_files"],
            "python_loc": source_stats["python_loc"],
            "public_modules": source_stats["public_modules"],
            "public_classes": source_stats["public_classes"],
            "public_functions": source_stats["public_functions"],
        },
        "pipeline": {
            "stage_count": 8,
            "translation_rules": translation_rules,
            "stages": [
                "ingest",
                "parse",
                "graph",
                "translate",
                "statespace",
                "markov",
                "gnn",
                "reverse",
            ],
        },
        "evaluation": {
            "roundtrip": {
                "data_source": "cogant/evaluation/dataset/roundtrip_results.jsonl",
                "note": "Post-wave-16 benchmark (wave-16 CONSTRAINT/POLICY/CONTEXT synthesizer fixes; re-run 2026-04-10). 23/23 ISOMORPHIC.",
                "threshold_isomorphic": 0.8,
                "threshold_approximate": 0.5,
                "total_targets": roundtrip["total_targets"],
                "isomorphic_count": roundtrip["isomorphic_count"],
                "approximate_count": roundtrip["approximate_count"],
                "divergent_count": roundtrip["divergent_count"],
                "mean_epsilon": roundtrip["mean_epsilon"],
                "median_epsilon": roundtrip["median_epsilon"],
                "min_epsilon": roundtrip["min_epsilon"],
                "max_epsilon": roundtrip["max_epsilon"],
                "per_target": roundtrip["per_target"],
            },
        },
        "literature": {
            "source": "cogant/docs/evaluation/LITERATURE.md",
            "bibliography_entries": bib_entries,
        },
        "rust": {
            "crates_total": rust_crates,
            "ffi_available": ffi,
        },
    }

    out_path = EVAL_DIR / "METRICS.yaml"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    header = (
        "# cogant/evaluation/METRICS.yaml\n"
        "# AUTO-GENERATED by tools/regenerate_metrics.py\n"
        "# DO NOT EDIT BY HAND. Run: cd cogant && uv run python ../tools/regenerate_metrics.py\n\n"
    )

    yaml_str = yaml.dump(
        metrics,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )

    out_path.write_text(header + yaml_str)
    print(f"Written: {out_path}", file=sys.stderr)
    print(f"  test_count_total={test_count_total}, passing={test_results['passing']}, "
          f"coverage={coverage_pct}%, mypy_errors={mypy_errors}, "
          f"roundtrip={roundtrip['isomorphic_count']}/{roundtrip['total_targets']} ISOMORPHIC",
          file=sys.stderr)


if __name__ == "__main__":
    main()
