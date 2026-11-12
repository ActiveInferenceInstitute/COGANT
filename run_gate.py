#!/usr/bin/env python3
"""Single entry point for COGANT's local and CI gates.

Every GitHub Actions job and every local check runs an arm of this script, so a
command exists in exactly one place.  Arms are independently runnable:

    python run_gate.py --list
    python run_gate.py lint types
    python run_gate.py test-fast
    python run_gate.py --prepare lint types docs content
    python run_gate.py all

``--prepare`` installs the union of the selected arms' extras with one
``uv sync`` (run it once; the arms themselves never install anything).
``--dry-run`` prints the exact commands without executing them.

Paths are anchored on this file, so the script works from any directory.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INNER = ROOT / "cogant"
GITHUB_FORMAT = os.environ.get("GITHUB_ACTIONS") == "true"
GNN_CACHE_DIR = os.environ.get("COGANT_GNN_UV_CACHE", "/tmp/cogant-upstream-uv-cache")


@dataclass(frozen=True)
class Step:
    label: str
    argv: tuple[str, ...]
    cwd: Path = INNER
    env: dict[str, str] = field(default_factory=dict)
    timeout: int = 900


@dataclass(frozen=True)
class Arm:
    name: str
    summary: str
    extras: tuple[str, ...]
    steps: tuple[Step, ...]


def _ruff_check() -> Step:
    argv = ["uv", "run", "ruff", "check", "--no-fix"]
    if GITHUB_FORMAT:
        argv.append("--output-format=github")
    return Step("ruff check", (*argv, "py/cogant/", "tests/"), timeout=300)


def _audit(script: str, *args: str, timeout: int = 300) -> Step:
    return Step(script, ("uv", "run", "python", f"../tools/{script}", *args), timeout=timeout)


GNN_TEST_FILES = (
    "tests/unit/test_gnn_upstream_bridge.py",
    "tests/unit/test_gnn_upstream_bridge_contract.py",
    "tests/unit/test_upstream_pipeline_resolution.py",
    "tests/integration/test_upstream_gnn_pipeline.py",
)

ARMS: dict[str, Arm] = {
    "lint": Arm(
        "lint",
        "ruff check + ruff format --check on the package and test trees",
        ("dev",),
        (
            _ruff_check(),
            Step("ruff format --check", ("uv", "run", "ruff", "format", "--check", "py/cogant/", "tests/"), timeout=300),
        ),
    ),
    "types": Arm(
        "types",
        "strict mypy over the installed package (viz interfaces included)",
        ("dev", "viz"),
        (
            Step(
                "mypy --strict",
                ("uv", "run", "mypy", "--package", "cogant", "--strict", "--no-warn-unused-configs"),
                env={"MYPYPATH": "py"},
                timeout=900,
            ),
        ),
    ),
    "content": Arm(
        "content",
        "repository fact gates: docs constants, stage list, coverage, claims",
        ("dev",),
        (
            _audit("audit_docs_constants.py"),
            _audit("audit_folder_docs.py"),
            _audit("audit_stage_list.py"),
            _audit("audit_test_names.py"),
            # check_metrics_fresh.py is deliberately absent: the dedicated
            # ``metrics-fresh.yml`` workflow owns that check, and running it
            # here duplicated the same script on every CI run.
            _audit("audit_manuscript_module_refs.py"),
            _audit("audit_manuscript_math_adjacency.py"),
            _audit("audit_manuscript_markdown_links.py"),
            _audit("audit_robustness_table.py"),
            _audit("check_coverage_table.py", "--strict"),
            _audit("audit_synthetic_surfaces.py"),
            _audit("audit_figure_renderers.py"),
        ),
    ),
    "docs": Arm(
        "docs",
        "MkDocs strict build and relative-link verification",
        ("dev",),
        (
            Step("mkdocs build --strict", ("uv", "run", "mkdocs", "build", "--strict"), timeout=900),
            Step("verify_doc_links", ("uv", "run", "python", "docs/verify_doc_links.py"), timeout=300),
        ),
    ),
    "test-fast": Arm(
        "test-fast",
        "default test arm: no coverage, no property tree, slow tests deselected",
        ("all",),
        (
            Step(
                "pytest fast",
                (
                    "uv",
                    "run",
                    "pytest",
                    "tests/",
                    "--no-cov",
                    "-q",
                    "--ignore=tests/property/",
                    "-m",
                    "not slow",
                ),
                timeout=3600,
            ),
        ),
    ),
    "test-property": Arm(
        "test-property",
        "Hypothesis law tests (also collected by the full arm)",
        ("all",),
        (
            Step(
                "pytest property",
                (
                    "uv",
                    "run",
                    "pytest",
                    "tests/property/",
                    "-q",
                    "--override-ini=addopts=",
                    "-p",
                    "no:warnings",
                ),
                timeout=1800,
            ),
        ),
    ),
    "test-full": Arm(
        "test-full",
        "full suite with the coverage gate",
        ("all",),
        (
            Step(
                "pytest full",
                (
                    "uv",
                    "run",
                    "pytest",
                    "tests/",
                    "-q",
                    "-m",
                    "not slow",
                    "--cov=cogant",
                    "--cov-fail-under=89",
                ),
                timeout=5400,
            ),
        ),
    ),
    "gnn": Arm(
        "gnn",
        "pinned upstream GNN conformance: probe, bridge tests, provenance",
        ("upstream", "dev"),
        (
            Step(
                "GNN-FEP importer contract",
                (
                    "uv", "run", "python", "-m", "gnn.importers", "check",
                    "--repo", str(ROOT), "--require-pointer",
                    "--workflow", ".github/workflows/ci.yml", "--job", "gnn-conformance",
                ),
                timeout=300,
            ),
            Step("conformance probe", ("uv", "run", "python", "scripts/gnn_conformance_probe.py"), timeout=900),
            Step(
                "bridge tests",
                ("uv", "run", "pytest", "-q", "--no-cov", "-o", "addopts=", "-rs", *GNN_TEST_FILES),
                timeout=1800,
            ),
            _audit("audit_release_integrity.py", "--no-openapi"),
        ),
    ),
    "wheel": Arm(
        "wheel",
        "clean wheel build, isolated install smoke, and release integrity",
        ("dev",),
        (
            Step("wheel smoke", ("uv", "run", "python", "../tools/wheel_smoke.py"), timeout=1800),
            _audit(
                "audit_release_integrity.py",
                "--require-wheel",
                "--check-wheel-reproducibility",
                timeout=900,
            ),
        ),
    ),
    "rust": Arm(
        "rust",
        "Rust backend fmt/check/test/clippy",
        (),
        (
            Step("cargo fmt", ("cargo", "fmt", "--manifest-path", "rust/Cargo.toml", "--all", "--check")),
            Step("cargo check", ("cargo", "check", "--manifest-path", "rust/Cargo.toml", "--workspace")),
            Step("cargo test", ("cargo", "test", "--manifest-path", "rust/Cargo.toml", "--workspace")),
            Step(
                "cargo clippy",
                ("cargo", "clippy", "--manifest-path", "rust/Cargo.toml", "--workspace", "--", "-D", "warnings"),
            ),
        ),
    ),
    "manuscript": Arm(
        "manuscript",
        "inject manuscript variables, validate figures, render the PDF",
        ("dev",),
        (
            Step("render manuscript", ("uv", "run", "python", "../scripts/render_manuscript.py"), timeout=3600),
            Step(
                "verify manuscript links",
                ("uv", "run", "python", "docs/verify_manuscript_links.py"),
                timeout=300,
            ),
        ),
    ),
}

ARM_ORDER = tuple(ARMS)


def _selected(names: list[str]) -> list[Arm]:
    if not names:
        # A bare invocation runs the fast default arm; ``all`` is explicit.
        names = ["test-fast"]
    if names == ["all"]:
        return [ARMS[name] for name in ARM_ORDER]
    unknown = [name for name in names if name not in ARMS]
    if unknown:
        raise SystemExit(f"unknown arm(s): {', '.join(unknown)}\nknown: {', '.join(ARM_ORDER)}")
    seen: list[str] = []
    for name in names:
        if name not in seen:
            seen.append(name)
    return [ARMS[name] for name in seen]


def _prepare(arms: list[Arm], dry_run: bool) -> int:
    extras: list[str] = []
    for arm in arms:
        for extra in arm.extras:
            if extra not in extras:
                extras.append(extra)
    if not extras:
        print("[prepare] selected arms need no Python extras")
        return 0
    argv = ["uv", "sync"]
    for extra in extras:
        argv.extend(["--extra", extra])
    env = dict(os.environ)
    if any("upstream" in arm.extras for arm in arms):
        env["UV_CACHE_DIR"] = GNN_CACHE_DIR
    print(f"[prepare] {' '.join(argv)} (cwd={INNER})")
    if dry_run:
        return 0
    completed = subprocess.run(argv, cwd=INNER, env=env, check=False)
    return completed.returncode


def _run_step(step: Step) -> tuple[bool, float]:
    env = os.environ.copy()
    env.update(step.env)
    print(f"  - {step.label}: {' '.join(step.argv)}")
    started = time.perf_counter()
    try:
        completed = subprocess.run(step.argv, cwd=step.cwd, env=env, timeout=step.timeout, check=False)
    except subprocess.TimeoutExpired:
        print(f"    {step.label}: TIMEOUT after {step.timeout}s", file=sys.stderr)
        return False, time.perf_counter() - started
    except OSError as exc:
        print(f"    {step.label}: unavailable: {exc}", file=sys.stderr)
        return False, time.perf_counter() - started
    elapsed = time.perf_counter() - started
    status = "pass" if completed.returncode == 0 else f"FAIL (exit {completed.returncode})"
    print(f"    {step.label}: {status} ({elapsed:.1f}s)")
    return completed.returncode == 0, elapsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("arms", nargs="*", metavar="ARM", help="arm name(s); default: test-fast")
    parser.add_argument("--list", action="store_true", help="list arms and exit")
    parser.add_argument("--dry-run", action="store_true", help="print commands without running them")
    parser.add_argument(
        "--prepare",
        action="store_true",
        help="run one uv sync for the union of the selected arms' extras first",
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="continue to later arms after a failure (default: stop at the first failure)",
    )
    args = parser.parse_args(argv)

    if args.list:
        width = max(len(name) for name in ARM_ORDER)
        for name in ARM_ORDER:
            arm = ARMS[name]
            extras = f" [extras: {', '.join(arm.extras)}]" if arm.extras else ""
            print(f"{name.ljust(width)}  {arm.summary}{extras}")
        return 0

    arms = _selected(args.arms)
    if args.prepare and _prepare(arms, args.dry_run) != 0:
        return 1

    results: list[tuple[str, str, float]] = []
    failed = False
    for arm in arms:
        print(f"[{arm.name}] {arm.summary}")
        started = time.perf_counter()
        status = "dry" if args.dry_run else "pass"
        for step in arm.steps:
            if args.dry_run:
                print(f"  - {step.label}: {' '.join(step.argv)}")
                continue
            ok, _ = _run_step(step)
            if not ok:
                status = "FAIL"
                failed = True
                break
        results.append((arm.name, status, time.perf_counter() - started))
        if failed and not args.keep_going:
            break

    width = max(len(name) for name, _, _ in results)
    print("\ngate summary")
    for name, status, elapsed in results:
        print(f"  {name.ljust(width)}  {status:<5}  {elapsed:7.2f}s")
    total = sum(elapsed for _, _, elapsed in results)
    print(f"  {'total'.ljust(width)}  {'':<5}  {total:7.2f}s")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
