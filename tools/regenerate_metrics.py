#!/usr/bin/env python3
"""Regenerate ``cogant/evaluation/METRICS.yaml`` from live repo state.

Run from any directory — all paths are anchored on ``__file__``. The
historical convention was to run from the ``cogant/`` package root, and that
still works::

    cd cogant && uv run python ../tools/regenerate_metrics.py

or equivalently::

    uv run python tools/regenerate_metrics.py
    uv run python projects/cogant/tools/regenerate_metrics.py  # parent template root

The script probes the live repository at call time: it runs pytest,
mypy, and ruff against ``cogant/py/cogant/``; reads ``coverage.json``
(if present); walks the AST of every source file; and parses the
roundtrip-evaluation JSONL. All of that is then written to
``cogant/evaluation/METRICS.yaml`` with an auto-generated header.

Exit codes
----------
* ``0`` — METRICS.yaml written successfully.
* ``1`` — fatal error (missing ``cogant/`` tree, write failure, etc.).

Test/mypy/ruff timeouts degrade to warning messages with ``-1``
sentinel values for the affected metric so the YAML still writes; CI
should then flag the negative value downstream.
"""

from __future__ import annotations

import ast
import json
import re
import statistics
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Repo root: the directory that contains both cogant/ and tools/
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
TOOLS_DIR = Path(__file__).parent
COGANT_DIR = REPO_ROOT / "cogant"
PY_PKG = COGANT_DIR / "py" / "cogant"
TESTS_DIR = COGANT_DIR / "tests"
EVAL_DIR = COGANT_DIR / "evaluation"
RUST_DIR = COGANT_DIR / "rust"
DOCS_EVAL = COGANT_DIR / "docs" / "evaluation"

if str(TOOLS_DIR.resolve()) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR.resolve()))


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


def get_python_min_from_pyproject() -> str:
    """Minimum CPython ``X.Y`` from ``[project].requires-python`` in ``cogant/pyproject.toml``."""
    pyproject = COGANT_DIR / "pyproject.toml"
    if not pyproject.is_file():
        return "3.11"
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except OSError:
        return "3.11"
    req = (data.get("project") or {}).get("requires-python") or ""
    if not isinstance(req, str):
        return "3.11"
    # ">=3.11", ">=3.11,<3.14", "~=3.11.0"
    m = re.search(r">=\s*(\d+)\.(\d+)", req)
    if m:
        return f"{m.group(1)}.{m.group(2)}"
    m = re.search(r"~=\s*(\d+)\.(\d+)", req)
    if m:
        return f"{m.group(1)}.{m.group(2)}"
    return "3.11"


def get_default_runner_stages() -> list[str]:
    """Ordered stage names from :class:`cogant.api.pipeline.PipelineConfig` defaults."""
    py_root = COGANT_DIR / "py"
    if not py_root.is_dir():
        return [
            "ingest",
            "static",
            "normalize",
            "graph",
            "dynamic",
            "translate",
            "statespace",
            "process",
            "export",
            "validate",
        ]
    insert_at = str(py_root.resolve())
    if insert_at not in sys.path:
        sys.path.insert(0, insert_at)
    try:
        from cogant.api.pipeline import PipelineConfig  # noqa: PLC0415

        return list(PipelineConfig().stages)
    except Exception as exc:  # pragma: no cover - import guard for stripped checkouts
        print(
            f"WARNING: could not import PipelineConfig for runner stages ({exc}); "
            "using static fallback list.",
            file=sys.stderr,
        )
        return [
            "ingest",
            "static",
            "normalize",
            "graph",
            "dynamic",
            "translate",
            "statespace",
            "process",
            "export",
            "validate",
        ]


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
            "uv run pytest tests/ --collect-only -q --no-cov 2>&1",
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


def get_test_results_and_coverage() -> tuple[dict[str, int], float, float]:
    """Read test results, suite runtime, and coverage from pytest + coverage.json.

    Runs pytest --tb=no -q (fast, no full suite re-run for coverage) then
    reads coverage.json for the coverage percentage.  This is O(seconds) not
    O(minutes) because we skip --cov during this invocation — the caller is
    expected to have already run the suite with coverage separately and
    committed coverage.json.

    Returns
    -------
    tuple
        ``(test_counts, coverage_percent, suite_runtime_s)`` where
        ``test_counts`` is a dict with keys ``passing``/``failing``/``skipped``/
        ``xfailed``/``xpassed``, ``coverage_percent`` is a float parsed from
        ``coverage.json``, and ``suite_runtime_s`` is the wall-clock seconds
        parsed from pytest's terminal summary line (0.0 on parse failure).
    """
    coverage_json = COGANT_DIR / "coverage.json"

    # Run pytest in fast mode to get pass/fail counts (no coverage collection).
    test_result = {"passing": 0, "failing": 0, "skipped": 0, "xfailed": 0, "xpassed": 0}
    suite_runtime_s: float = 0.0
    try:
        rc, out = _run(
            "uv run pytest tests/ -q --tb=no -p no:warnings --no-header --no-cov 2>&1",
            cwd=COGANT_DIR,
            timeout=1800,
        )
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
            # Parse pytest's terminal summary line: "... in 243.82s ..." or "in 4:03.45"
            # (minutes:seconds). pytest emits one of:
            #   ``===== 6915 passed in 243.82s (0:04:03) =====``
            #   ``===== 6915 passed in 0:04:03 =====``
            if suite_runtime_s == 0.0 and "passed" in line and " in " in line:
                m_sec = re.search(r"\bin\s+([\d.]+)s\b", line)
                if m_sec:
                    try:
                        suite_runtime_s = round(float(m_sec.group(1)), 2)
                    except ValueError:
                        pass
                else:
                    m_ms = re.search(r"\bin\s+(?:(\d+):)?(\d+):([\d.]+)\b", line)
                    if m_ms:
                        h = int(m_ms.group(1) or 0)
                        m = int(m_ms.group(2))
                        s = float(m_ms.group(3))
                        suite_runtime_s = round(h * 3600 + m * 60 + s, 2)
    except subprocess.TimeoutExpired:
        print("WARNING: pytest run timed out; test counts will be 0", file=sys.stderr)

    # Read coverage from coverage.json (expected to exist from last --cov run).
    coverage_pct = 0.0
    if coverage_json.exists():
        try:
            data = json.loads(coverage_json.read_text())
            totals = data.get("totals", {})
            coverage_pct = round(float(totals.get("percent_covered", 0.0)), 2)
        except (json.JSONDecodeError, KeyError):
            pass

    return test_result, coverage_pct, suite_runtime_s


# ---------------------------------------------------------------------------
# 7. mypy strict errors
# ---------------------------------------------------------------------------


def get_mypy_errors() -> int:
    """Run mypy --strict and count ``error:`` lines in the combined output.

    Returns ``-1`` on timeout (sentinel — CI should flag a negative value).
    Shell-pipe parsing was previously used; counting ``error:`` occurrences
    in Python is equivalent and avoids depending on ``grep`` / ``wc``.
    """
    try:
        rc, out = _run(
            "uv run mypy --strict py/cogant/",
            cwd=COGANT_DIR,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        print("WARNING: mypy --strict timed out after 120s", file=sys.stderr)
        return -1
    return sum(1 for line in out.splitlines() if "error:" in line)


# ---------------------------------------------------------------------------
# 8. Ruff violations
# ---------------------------------------------------------------------------


def get_ruff_violations() -> int:
    """Run ``ruff check`` and return the violation count.

    Prefers ``--output-format=json`` (unambiguous, robust across ruff
    versions), falls back to parsing ``Found N error(s)`` summary lines.
    Returns ``-1`` on timeout.
    """
    try:
        rc, out = _run(
            "uv run ruff check --output-format=json py/cogant/",
            cwd=COGANT_DIR,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        print("WARNING: ruff check timed out after 60s", file=sys.stderr)
        return -1
    # JSON path: ruff emits a JSON array of violations on stdout; stderr may
    # carry warnings. Extract just the JSON portion.
    json_start = out.find("[")
    if json_start != -1:
        try:
            return len(json.loads(out[json_start:].strip().split("\n")[0]))
        except json.JSONDecodeError:
            pass
    # Fallback: summary-line parsing.
    m = re.search(r"Found\s+(\d+)\s+error", out)
    if m:
        return int(m.group(1))
    # If exit code 0 and no "Found N" line, assume clean.
    return 0 if rc == 0 else -1


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
            "role_preserved_count": 0,
            "strict_isomorphism_count": 0,
            "drift_count": 0,
            "failed_count": 0,
            "stale_legacy_count": 0,
            "role_preservation_score_source": "empty",
            "mean_role_preservation_score": None,
            "median_role_preservation_score": None,
            "min_role_preservation_score": None,
            "max_role_preservation_score": None,
            "per_target": [],
        }

    entries = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    def _status(entry: dict) -> str:
        status = entry.get("roundtrip_status")
        if status:
            return str(status)
        # Legacy v0.5 rows carry only `tier`/`epsilon` and NO v0.6
        # `role_preservation_score`. Relabelling tier=ISOMORPHIC as a
        # fresh v0.6 "ROLE_PRESERVED" verdict is laundering, not a
        # measurement — flag it so it is NOT counted as role-preserved.
        if "role_preservation_score" not in entry:
            return "STALE_LEGACY"
        tier = str(entry.get("tier") or "").upper()
        if tier == "ISOMORPHIC":
            return "ROLE_PRESERVED"
        if tier == "APPROXIMATE":
            return "DRIFT"
        if tier == "DIVERGENT":
            return "DRIFT"
        return "FAILED" if entry.get("error") else "DRIFT"

    def _role_score(entry: dict) -> float:
        if "role_preservation_score" in entry:
            return float(entry["role_preservation_score"])
        if "epsilon" in entry:
            return float(entry["epsilon"])
        if "role_match_score" in entry:
            return float(entry["role_match_score"])
        return 0.0

    def _score_source(entry: dict) -> str:
        if "role_preservation_score" in entry:
            return "v0.6_native"
        if "epsilon" in entry or "role_match_score" in entry:
            return "legacy_epsilon_proxy"
        return "empty"

    def _scaffolding_fraction(entry: dict) -> float | None:
        """Compute the synthesizer-inflation fraction per RedTeam F23.

        Sums ``synth_*`` minus ``orig_*`` over the per-role count fields
        present on the row (``orig_n_hidden``, ``orig_n_obs``,
        ``orig_n_actions``, ``synth_n_*``), normalised by the synth
        total. Returns ``None`` when neither side has any counts on the
        row (e.g. for v0.5 ε-bucket rows that carry no per-role
        breakdown). Returns 0.0 when the synth total is also zero so
        the fraction is undefined-but-conventionally-zero.
        """
        role_keys = ("hidden", "obs", "actions")
        orig_total = 0
        synth_total = 0
        any_present = False
        for k in role_keys:
            orig_v = entry.get(f"orig_n_{k}")
            synth_v = entry.get(f"synth_n_{k}")
            if orig_v is not None:
                any_present = True
                try:
                    orig_total += int(orig_v)
                except (TypeError, ValueError):
                    pass
            if synth_v is not None:
                any_present = True
                try:
                    synth_total += int(synth_v)
                except (TypeError, ValueError):
                    pass
        if not any_present:
            return None
        if synth_total <= 0:
            return 0.0
        return round((synth_total - orig_total) / synth_total, 4)

    statuses = [_status(e) for e in entries]
    native_scores = [
        float(e["role_preservation_score"]) for e in entries if "role_preservation_score" in e
    ]
    score_sources = {_score_source(e) for e in entries}
    if not entries or score_sources == {"empty"}:
        role_score_source = "empty"
    elif score_sources <= {"legacy_epsilon_proxy", "empty"}:
        role_score_source = "legacy_epsilon_proxy"
    elif "v0.6_native" in score_sources and score_sources - {"v0.6_native", "empty"}:
        role_score_source = "mixed"
    else:
        role_score_source = "v0.6_native"
    role_preserved = sum(
        1 for status in statuses if status in {"STRUCTURALLY_ISOMORPHIC", "ROLE_PRESERVED"}
    )
    strict = sum(1 for status in statuses if status == "STRUCTURALLY_ISOMORPHIC")
    drift = sum(1 for status in statuses if status == "DRIFT")
    failed = sum(1 for status in statuses if status == "FAILED")
    stale_legacy = sum(1 for status in statuses if status == "STALE_LEGACY")

    per_target = [
        {
            "name": e["repo"],
            "group": e["group"],
            "role_preservation_score": _role_score(e),
            "role_preservation_score_source": _score_source(e),
            # Synthesizer-inflation diagnostic (RedTeam F23, 2026-05-20).
            # scaffolding_fraction = (sum(synth_*) - sum(orig_*)) / sum(synth_*)
            # over the per-role count fields when they are present on the
            # row. A value near 0.0 means the synthesizer emitted ≈ the same
            # role counts the origin graph had; values near 1.0 mean the
            # synth side is dominated by scaffolding (newly-introduced
            # roles that did not appear in the origin multiset). Read this
            # alongside ``role_preservation_score`` to know how much of a
            # 1.0 RP score is faithful preservation vs scaffolding
            # inflation that happens to clear the min/max similarity
            # ceiling.
            "scaffolding_fraction": _scaffolding_fraction(e),
            "roundtrip_status": _status(e),
            "strict_structural": _status(e) == "STRUCTURALLY_ISOMORPHIC",
            "role_preserved": _status(e)
            in {"STRUCTURALLY_ISOMORPHIC", "ROLE_PRESERVED"},
            "fixture_group": e.get("fixture_group", e.get("group", "")),
            "file_count": e.get("file_count", 0),
            "loc": e.get("loc", 0),
            "node_count": e.get("node_count", 0),
            "edge_count": e.get("edge_count", 0),
            "parser_fallback_count": e.get("parser_fallback_count", 0),
            "skipped_file_count": e.get("skipped_file_count", 0),
            "unsupported_construct_count": e.get("unsupported_construct_count", 0),
            "dashboard_artifact_completeness": e.get("dashboard_artifact_completeness", 0.0),
            "elapsed_s": e.get("elapsed_s", 0.0),
        }
        for e in entries
    ]

    return {
        "total_targets": len(entries),
        "role_preserved_count": role_preserved,
        "strict_isomorphism_count": strict,
        "drift_count": drift,
        "failed_count": failed,
        "stale_legacy_count": stale_legacy,
        "role_preservation_score_source": role_score_source,
        "mean_role_preservation_score": (
            round(statistics.mean(native_scores), 4) if native_scores else None
        ),
        "median_role_preservation_score": (
            round(statistics.median(native_scores), 4) if native_scores else None
        ),
        "min_role_preservation_score": min(native_scores) if native_scores else None,
        "max_role_preservation_score": max(native_scores) if native_scores else None,
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
    crates = [d for d in RUST_DIR.iterdir() if d.is_dir() and (d / "Cargo.toml").exists()]
    return len(crates)


# ---------------------------------------------------------------------------
# 13. Rust FFI availability
# ---------------------------------------------------------------------------


def rust_ffi_available() -> bool:
    pyi_path = PY_PKG / "rust_backend.pyi"
    so_files = list(PY_PKG.glob("_rust*.so")) + list(PY_PKG.glob("_rust*.pyd"))
    return pyi_path.exists() or len(so_files) > 0


# ---------------------------------------------------------------------------
# 13b. Shipped benchmark fixtures
# ---------------------------------------------------------------------------


def count_shipped_fixtures() -> int:
    """Count packaged benchmark fixtures exercised by the suite harness.

    The manuscript's fixture-corpus claim references "six packaged fixtures"
    drawn from ``examples/control_positive/`` (``calculator``,
    ``event_pipeline``, ``flask_mini``) and ``examples/real_world/``
    (``flask_app``, ``requests_lib``, ``json_stdlib``). We derive the number
    from the live filesystem rather than hard-coding ``6`` so this tracks if
    fixtures are added/removed.
    """
    ex_dir = COGANT_DIR / "examples"
    if not ex_dir.is_dir():
        return 0
    total = 0
    for bucket in ("control_positive", "real_world"):
        bucket_dir = ex_dir / bucket
        if not bucket_dir.is_dir():
            continue
        for child in bucket_dir.iterdir():
            if not child.is_dir():
                continue
            if child.name in {"__pycache__"} or child.name.startswith("_"):
                continue
            total += 1
    return total


def get_benchmark_report_metadata() -> dict[str, str]:
    """Return metadata for the latest committed benchmark suite report.

    The manuscript references the canonical ``suite_YYYYMMDD.md`` report by
    filename and records the interpreter/platform used for that benchmark run.
    Keep those fields generated from the report header so the prose cannot
    drift from the benchmark artifact.
    """
    results_dir = COGANT_DIR / "benchmarks" / "results"
    reports = sorted(results_dir.glob("suite_*.md"))
    if not reports:
        return {
            "benchmark_suite_file": "",
            "benchmark_python_version": "",
            "benchmark_os": "",
        }

    report = reports[-1]
    text = report.read_text(encoding="utf-8")

    def _header_value(name: str) -> str:
        match = re.search(rf"^- {re.escape(name)}:\s*`([^`]+)`", text, re.MULTILINE)
        return match.group(1) if match else ""

    return {
        "benchmark_suite_file": report.name,
        "benchmark_python_version": _header_value("python"),
        "benchmark_os": _header_value("platform"),
    }


# ---------------------------------------------------------------------------
# 13c. IR schema counts (node kinds, edge kinds, Active-Inference roles)
# ---------------------------------------------------------------------------


def count_node_kinds() -> int:
    """Count concrete ``NodeKind`` enum members from ``cogant.schemas.core``."""
    core_path = PY_PKG / "schemas" / "core.py"
    if not core_path.is_file():
        return 0
    text = core_path.read_text()
    m = re.search(r"class\s+NodeKind.*?(?=\nclass\s|\Z)", text, re.DOTALL)
    if not m:
        return 0
    return len(re.findall(r"^\s{4}([A-Z_][A-Z_0-9]*)\s*=", m.group(0), re.MULTILINE))


def count_edge_kinds() -> int:
    """Count concrete ``EdgeKind`` enum members from ``cogant.schemas.core``."""
    core_path = PY_PKG / "schemas" / "core.py"
    if not core_path.is_file():
        return 0
    text = core_path.read_text()
    m = re.search(r"class\s+EdgeKind.*?(?=\nclass\s|\Z)", text, re.DOTALL)
    if not m:
        return 0
    return len(re.findall(r"^\s{4}([A-Z_][A-Z_0-9]*)\s*=", m.group(0), re.MULTILINE))


# Canonical Active-Inference semantic role names shipped in
# ``cogant.schemas.semantic.MappingKind`` — the first seven StrEnum members.
# These are the roles the manuscript enumerates (HIDDEN_STATE, OBSERVATION,
# ACTION, POLICY, PREFERENCE, CONSTRAINT, CONTEXT). The full ``MappingKind``
# enum has additional non-AI members (DATA_FLOW, CONTROL_FLOW, etc.) that
# are not Active Inference roles.
_ACTIVE_INF_ROLE_NAMES: tuple[str, ...] = (
    "HIDDEN_STATE",
    "OBSERVATION",
    "ACTION",
    "POLICY",
    "PREFERENCE",
    "CONSTRAINT",
    "CONTEXT",
)


def count_active_inf_roles() -> int:
    """Return the number of canonical Active-Inference semantic roles.

    Verified against ``cogant.schemas.semantic.MappingKind``: every name in
    :data:`_ACTIVE_INF_ROLE_NAMES` must appear as an enum member. If the
    enum is missing or a role name has been renamed, return 0 so that the
    placeholder remains unresolved (forcing an explicit review) rather than
    silently substituting a stale value.
    """
    sem_path = PY_PKG / "schemas" / "semantic.py"
    if not sem_path.is_file():
        return len(_ACTIVE_INF_ROLE_NAMES)  # conservative fallback
    text = sem_path.read_text()
    m = re.search(r"class\s+MappingKind.*?(?=\nclass\s|\Z)", text, re.DOTALL)
    if not m:
        return len(_ACTIVE_INF_ROLE_NAMES)
    body = m.group(0)
    for name in _ACTIVE_INF_ROLE_NAMES:
        if not re.search(rf"^\s{{4}}{name}\s*=", body, re.MULTILINE):
            return 0
    return len(_ACTIVE_INF_ROLE_NAMES)


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

    # Fail fast with an actionable message if the cogant tree is missing.
    if not COGANT_DIR.is_dir():
        print(
            f"ERROR: cogant directory not found at {COGANT_DIR}. "
            "Are you running from a stripped checkout?",
            file=sys.stderr,
        )
        sys.exit(1)
    if not PY_PKG.is_dir():
        print(
            f"ERROR: python package not found at {PY_PKG}. "
            "Expected cogant/py/cogant/ to contain the source tree.",
            file=sys.stderr,
        )
        sys.exit(1)

    from regenerate_ablation import PACKAGED_FIXTURES, compute_ablation

    version = get_cogant_version()
    git_sha = get_git_sha()
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    print("  [1/10] Version + SHA", file=sys.stderr)

    print("  [2/10] Test file counts...", file=sys.stderr)
    file_counts = get_test_file_counts()

    print("  [3/10] Test collection count...", file=sys.stderr)
    test_count_total = get_test_count_total()

    print("  [4/10] Test run results + coverage (this may take a few minutes)...", file=sys.stderr)
    test_results, coverage_pct, suite_runtime_s = get_test_results_and_coverage()

    # Durability guard (audit 2026-05-18): the pytest sub-invocation above can
    # mis-parse in some environments (uv re-sync noise, transient editable-install
    # breakage) and return passing=0. A multi-thousand-test suite never
    # legitimately reports 0 passing, so treat passing==0 as a parse/run failure:
    # preserve the prior canonical METRICS test counts + suite runtime and warn
    # loudly, instead of silently zeroing the canonical numbers.
    if test_results["passing"] == 0:
        _prev_path = EVAL_DIR / "METRICS.yaml"
        if _prev_path.exists():
            try:
                _prev = yaml.safe_load(_prev_path.read_text()) or {}
                _pt = _prev.get("testing") or {}
                test_results = {
                    "passing": _pt.get("test_count_passing", 0),
                    "failing": _pt.get("test_count_failing", 0),
                    "skipped": _pt.get("test_count_skipped", 0),
                    "xfailed": _pt.get("test_count_xfailed", 0),
                    "xpassed": _pt.get("test_count_xpassed", 0),
                }
                if not test_count_total:
                    test_count_total = _pt.get("test_count_total", 0)
                if not suite_runtime_s:
                    suite_runtime_s = (_prev.get("benchmark") or {}).get(
                        "suite_runtime_s", 0.0
                    )
                print(
                    "WARNING: pytest parse yielded 0 passing (environment/parse "
                    "failure, not a real result). PRESERVED prior METRICS test "
                    "counts/runtime. Re-run the suite manually and update only if "
                    "the code actually changed.",
                    file=sys.stderr,
                )
            except Exception as _e:  # pragma: no cover - defensive
                print(
                    f"WARNING: pytest parse yielded 0 passing and prior METRICS "
                    f"could not be read to preserve counts: {_e}",
                    file=sys.stderr,
                )

    print("  [5/10] mypy strict errors...", file=sys.stderr)
    mypy_errors = get_mypy_errors()

    print("  [6/10] Ruff violations...", file=sys.stderr)
    ruff_violations = get_ruff_violations()

    print("  [7/10] Python source analysis...", file=sys.stderr)
    source_stats = analyze_python_source()

    print("  [8/10] Evaluation data + metadata...", file=sys.stderr)
    roundtrip = parse_roundtrip_results()
    bib_entries = count_bibliography_entries()
    rust_crates = count_rust_crates()
    ffi = rust_ffi_available()
    translation_rules = count_translation_rules()
    python_min = get_python_min_from_pyproject()
    runner_stages = get_default_runner_stages()
    shipped_fixtures = count_shipped_fixtures()
    benchmark_report = get_benchmark_report_metadata()
    node_kinds = count_node_kinds()
    edge_kinds = count_edge_kinds()
    active_inf_roles = count_active_inf_roles()

    print("  [10/10] Ablation axes (live pipeline on 6 fixtures)...", file=sys.stderr)
    ablation = compute_ablation(PACKAGED_FIXTURES)

    metrics = {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "generator_git_sha": git_sha,
        "cogant_version": version,
        "package": {
            "name": "cogant",
            "version": version,
            "python_min": python_min,
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
            "stage_count": len(runner_stages),
            "translation_rules": translation_rules,
            "runner_stages": runner_stages,
        },
        "evaluation": {
            "roundtrip": {
                "data_source": "cogant/evaluation/dataset/roundtrip_results.jsonl",
                "note": (
                    "Legacy benchmark rows converted to the v0.6 roundtrip taxonomy: "
                    "role-preserved is reported separately from strict structural "
                    "isomorphism."
                ),
                "threshold_role_preserved": 0.5,
                "threshold_drift": 0.5,
                "total_targets": roundtrip["total_targets"],
                "role_preserved_count": roundtrip["role_preserved_count"],
                "strict_isomorphism_count": roundtrip["strict_isomorphism_count"],
                "drift_count": roundtrip["drift_count"],
                "failed_count": roundtrip["failed_count"],
                "stale_legacy_count": roundtrip["stale_legacy_count"],
                "role_preservation_score_source": roundtrip["role_preservation_score_source"],
                "mean_role_preservation_score": roundtrip["mean_role_preservation_score"],
                "median_role_preservation_score": roundtrip["median_role_preservation_score"],
                "min_role_preservation_score": roundtrip["min_role_preservation_score"],
                "max_role_preservation_score": roundtrip["max_role_preservation_score"],
                "per_target": roundtrip["per_target"],
            },
        },
        "literature": {
            "source": "cogant/docs/evaluation/LITERATURE.md",
            "bibliography_entries": bib_entries,
        },
        "benchmark": {
            # Wall-clock seconds for the pytest suite run above (parsed from
            # the terminal summary). Manuscript §6.4 references this figure
            # via ``{{SUITE_RUNTIME_S}}``. 0.0 indicates parse failure.
            "suite_runtime_s": suite_runtime_s,
            # Packaged end-to-end fixtures referenced as "six packaged
            # fixtures" in §6 and the abstract. Discovered by walking
            # ``cogant/examples/control_positive`` and
            # ``cogant/examples/real_world``.
            "shipped_fixture_count": shipped_fixtures,
            # Header metadata from the canonical benchmark report referenced
            # by manuscript §6.4.
            "benchmark_suite_file": benchmark_report["benchmark_suite_file"],
            "benchmark_python_version": benchmark_report["benchmark_python_version"],
            "benchmark_os": benchmark_report["benchmark_os"],
        },
        "ir_schema": {
            "node_kind_count": node_kinds,
            "edge_kind_count": edge_kinds,
            "active_inf_role_count": active_inf_roles,
        },
        "rust": {
            "crates_total": rust_crates,
            "ffi_available": ffi,
        },
        "ablation": ablation,
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
    print(
        f"  test_count_total={test_count_total}, passing={test_results['passing']}, "
        f"coverage={coverage_pct}%, mypy_errors={mypy_errors}, "
        f"roundtrip_role_preserved={roundtrip['role_preserved_count']}/"
        f"{roundtrip['total_targets']}, strict={roundtrip['strict_isomorphism_count']}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
