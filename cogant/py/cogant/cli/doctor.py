"""Environment diagnostics for the COGANT CLI.

The ``cogant doctor`` subcommand performs a fast, side-effect-free scan
of the runtime to help users figure out whether their machine is set up
correctly before running long pipelines. It checks:

* Python version against the minimum supported interpreter,
* every runtime dependency COGANT can use (core, viz, multilang),
* the optional Rust backend extension module,
* external tools such as ``git`` and ``coverage``,
* and prints a single ``Overall`` verdict.

Design notes:

* **No pipeline imports.** The doctor must never trigger a pipeline
  import chain — it has to work even when the environment is broken
  enough that ``cogant translate`` would fail. Everything uses
  :mod:`importlib` lookups, :func:`shutil.which`, and a ``try/except``
  around the Rust backend.
* **Shared entrypoint.** :func:`run_doctor` is exposed so other CLI
  commands (e.g. ``cogant init``) can invoke diagnostics in-process
  without a subprocess hop and receive a structured result.
* **Deterministic output.** All checks are ordered; the function
  returns a :class:`DoctorReport` dataclass so tests can assert on
  individual check results, not just raw console strings.
"""

from __future__ import annotations

import importlib
import importlib.metadata as importlib_metadata
import importlib.util
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# --------------------------------------------------------------------- data --


@dataclass
class DoctorCheck:
    """A single diagnostic result."""

    name: str
    status: str  # "ok" | "warn" | "fail"
    detail: str = ""

    @property
    def icon(self) -> str:
        """Return a single-character visual glyph matching :attr:`status`."""
        return {"ok": "✅", "warn": "⚠️", "fail": "❌"}.get(self.status, "?")


@dataclass
class DoctorReport:
    """Aggregated diagnostic report."""

    checks: list[DoctorCheck] = field(default_factory=list)

    def add(self, check: DoctorCheck) -> None:
        """Append ``check`` to this report's ordered list of diagnostics."""
        self.checks.append(check)

    @property
    def ok(self) -> bool:
        """``True`` when nothing is failing (warnings are allowed)."""
        return all(c.status != "fail" for c in self.checks)

    @property
    def has_warnings(self) -> bool:
        """``True`` when at least one check carries ``"warn"`` status."""
        return any(c.status == "warn" for c in self.checks)

    @property
    def verdict(self) -> str:
        """Return ``"READY"``, ``"READY (with warnings)"`` or ``"NOT READY"``.

        A failing check (``status == "fail"``) yields ``"NOT READY"``; a
        clean report with one or more warnings yields the parenthesized
        form; otherwise the verdict is the plain ``"READY"`` string.
        """
        if not self.ok:
            return "NOT READY"
        if self.has_warnings:
            return "READY (with warnings)"
        return "READY"


# --------------------------------------------------------------- helpers ----


MIN_PYTHON: tuple[int, int] = (3, 11)

# (module_name, friendly_label, category, required)
# category is one of: "core", "viz", "multilang", "optional"
_DEPENDENCIES: list[tuple[str, str, str, bool]] = [
    ("cogant", "cogant", "core", True),
    ("networkx", "networkx", "core", True),
    ("pyarrow", "pyarrow", "core", True),
    ("duckdb", "duckdb", "core", True),
    ("matplotlib", "matplotlib (viz extras)", "viz", False),
    ("tree_sitter", "tree-sitter (multilang extras)", "multilang", False),
    ("coverage", "coverage.py (dynamic analysis)", "optional", False),
]


def _package_version(module_name: str) -> str | None:
    """Return the installed version of ``module_name`` if available.

    Uses :mod:`importlib.metadata` with a fallback to the module's
    ``__version__`` attribute (some packages expose one, not the
    other). Returns ``None`` if the module cannot be imported.
    """

    # Prefer metadata — does not require importing the package at all.
    distribution_name = module_name.replace("_", "-")
    try:
        return importlib_metadata.version(distribution_name)
    except importlib_metadata.PackageNotFoundError:
        pass
    try:
        return importlib_metadata.version(module_name)
    except importlib_metadata.PackageNotFoundError:
        pass

    # Fall back to importing and reading ``__version__``.
    try:
        mod = importlib.import_module(module_name)
    except Exception:  # noqa: BLE001 — any import failure means "not installed"
        return None
    return getattr(mod, "__version__", "unknown")


def _check_python() -> DoctorCheck:
    v = sys.version_info
    version_str = f"{v.major}.{v.minor}.{v.micro}"
    requirement = f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}"
    if (v.major, v.minor) >= MIN_PYTHON:
        return DoctorCheck(
            name="Python",
            status="ok",
            detail=f"{version_str} (>={requirement} required)",
        )
    return DoctorCheck(
        name="Python",
        status="fail",
        detail=f"{version_str} (>={requirement} required)",
    )


def _check_dependency(module_name: str, label: str, required: bool) -> DoctorCheck:
    version = _package_version(module_name)
    if version is None:
        return DoctorCheck(
            name=label,
            status="fail" if required else "warn",
            detail="not installed",
        )
    return DoctorCheck(name=label, status="ok", detail=version)


def _check_rust_backend() -> DoctorCheck:
    try:
        importlib.import_module("cogant._rust")
    except Exception as exc:  # noqa: BLE001 — any import failure is a warning
        return DoctorCheck(
            name="Rust backend",
            status="warn",
            detail=f"cogant._rust not available (optional): {type(exc).__name__}",
        )
    return DoctorCheck(name="Rust backend", status="ok", detail="loaded")


def _check_git() -> DoctorCheck:
    git_bin = shutil.which("git")
    if git_bin is None:
        return DoctorCheck(
            name="git",
            status="warn",
            detail="not on PATH (incremental mode disabled)",
        )
    try:
        out = subprocess.run(  # noqa: S603 — trusted PATH lookup
            [git_bin, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        version = out.stdout.strip().replace("git version ", "") or "unknown"
    except (OSError, subprocess.TimeoutExpired) as exc:
        return DoctorCheck(name="git", status="warn", detail=f"found but unreadable: {exc}")
    return DoctorCheck(name="git", status="ok", detail=version)


def _check_external_tool(
    binary: str,
    label: str,
    *,
    version_args: tuple[str, ...] = ("--version",),
    required: bool = False,
    strip_prefix: str = "",
) -> DoctorCheck:
    """Check an external CLI tool via ``shutil.which`` + ``--version``.

    Returns a ``warn`` status (not ``fail``) for missing optional tools
    so an incomplete dev environment still passes the doctor gate.
    Required tools report ``fail`` when missing.
    """

    binary_path = shutil.which(binary)
    if binary_path is None:
        return DoctorCheck(
            name=label,
            status="fail" if required else "warn",
            detail=f"not on PATH (install {binary})",
        )
    try:
        out = subprocess.run(  # noqa: S603 — trusted PATH lookup
            [binary_path, *version_args],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return DoctorCheck(
            name=label,
            status="warn",
            detail=f"found but unreadable: {type(exc).__name__}",
        )
    raw = (out.stdout or out.stderr or "").strip().splitlines()
    version = raw[0] if raw else "unknown"
    if strip_prefix and version.startswith(strip_prefix):
        version = version[len(strip_prefix) :].strip()
    return DoctorCheck(name=label, status="ok", detail=version or "unknown")


def _check_mypy() -> DoctorCheck:
    """mypy is optional but strongly recommended for CI runs."""
    return _check_external_tool("mypy", "mypy", required=False, strip_prefix="mypy ")


def _check_ruff() -> DoctorCheck:
    """ruff is optional; used for lint/format in the dev loop."""
    return _check_external_tool("ruff", "ruff", required=False, strip_prefix="ruff ")


def _check_mermaid_cli() -> DoctorCheck:
    """mermaid CLI (``mmdc``) renders the diagram exports."""
    return _check_external_tool("mmdc", "mermaid CLI (mmdc)", required=False)


def _find_tree_sitter_node_types() -> Path | None:
    """Locate a tree-sitter ``node-types.json`` bundled with grammars.

    The COGANT multilang extras ship language grammars as wheel
    resources. We walk the installed ``tree_sitter_languages`` /
    ``tree_sitter_python`` packages for a ``node-types.json``, which
    is the canonical marker that the grammar assets landed on disk.
    """

    candidates = (
        "tree_sitter_languages",
        "tree_sitter_python",
        "tree_sitter_javascript",
        "tree_sitter_typescript",
    )
    for pkg in candidates:
        try:
            spec = importlib.util.find_spec(pkg)
        except (ImportError, ValueError):
            continue
        if spec is None or spec.origin is None:
            continue
        pkg_root = Path(spec.origin).parent
        for path in pkg_root.rglob("node-types.json"):
            return path
    return None


def _check_tree_sitter_node_types() -> DoctorCheck:
    """Locate a ``node-types.json`` resource from a tree-sitter grammar."""
    path = _find_tree_sitter_node_types()
    if path is None:
        return DoctorCheck(
            name="tree-sitter node-types.json",
            status="warn",
            detail="not found (multilang extras missing)",
        )
    return DoctorCheck(
        name="tree-sitter node-types.json",
        status="ok",
        detail=str(path),
    )


# ------------------------------------------------------------- public API --


def run_doctor() -> DoctorReport:
    """Run all environment checks and return a :class:`DoctorReport`.

    Exposed so other CLI entry points (e.g. ``cogant init``) can reuse
    the diagnostics without spawning a subprocess.
    """

    report = DoctorReport()
    report.add(_check_python())
    for module_name, label, _category, required in _DEPENDENCIES:
        report.add(_check_dependency(module_name, label, required))
    report.add(_check_rust_backend())
    report.add(_check_git())
    report.add(_check_mypy())
    report.add(_check_ruff())
    report.add(_check_mermaid_cli())
    report.add(_check_tree_sitter_node_types())
    return report


def render_report(console: Console, report: DoctorReport) -> None:
    """Render a :class:`DoctorReport` onto a Rich :class:`Console`."""

    table = Table(
        box=box.SIMPLE,
        show_header=False,
        padding=(0, 1),
        expand=False,
    )
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Detail", style="dim")

    for check in report.checks:
        table.add_row(check.name, check.icon, check.detail)

    verdict_style = "green" if report.ok else "red"
    verdict = f"Overall: [{verdict_style} bold]{report.verdict}[/{verdict_style} bold]"

    console.print(
        Panel(
            table,
            title="[bold]COGANT Environment Diagnostics[/bold]",
            subtitle=verdict,
            border_style="blue",
            expand=False,
        )
    )


def doctor_command(console: Console | None = None) -> int:
    """Entrypoint used by ``main.py``'s ``@app.command()`` wrapper.

    Returns a shell exit code (``0`` success, ``1`` failure) so the
    Typer command can pass it straight to :class:`typer.Exit`.
    """

    console = console or Console()
    report = run_doctor()
    render_report(console, report)
    return 0 if report.ok else 1


# Allow running the module directly for quick manual checks:
#   python -m cogant.cli.doctor
if __name__ == "__main__":  # pragma: no cover — manual smoke entrypoint
    raise typer.Exit(code=doctor_command())
