"""Configurable driver for the upstream GNN 25-step pipeline.

This module composes the Active Inference Institute
``generalized-notation-notation`` numbered pipeline (steps ``0_template`` →
``24_intelligent_analysis``) on top of a COGANT-built ``gnn_package/``.

The 10-stage COGANT pipeline produces a ``model.gnn.md`` plus the 16 required
JSON sidecars at ``bundle.artifacts['_gnn_package_dir']``. Pointing the
upstream pipeline at that package exercises the Active Inference processing
chain (parsing, type checking, validation, export, ontology, reporting, …)
over the bundle COGANT just emitted.

Upstream contract (GNN 4.x)
---------------------------
GNN 4.x ships the top-level ``gnn`` package and binds selection,
configuration, source identity, output ownership and deadlines to one
pipeline *invocation* (``python -m gnn.main``): every step reads the same
frozen source manifest and writes into a leased output root. Running numbered
scripts one at a time (the GNN 2.x bridge strategy) bypasses that run
context, so this driver issues exactly one ``python -m gnn.main`` invocation
with ``--only-steps`` set to the selected steps and reads per-step outcomes
from ``00_pipeline_summary/pipeline_execution_summary.json``.

Only ``*.gnn.md`` / ``model.gnn.md`` files are staged as upstream inputs:
upstream discovery treats every ``*.json`` file as a model source, and the
COGANT JSON sidecars are package evidence, not standalone GNN models.

Default selection skips:

* ``1_setup`` — provisions a uv environment relative to the upstream source
  checkout; from an installed wheel it creates a stray ``.venv`` inside the
  caller's environment and attempts ``uv sync`` repairs.
* ``2_tests`` — runs upstream's own repository test suite, which is not
  shipped in the wheel (the step cannot pass from an installed package).
* ``11_render`` / ``12_execute`` — generate and run framework-specific
  simulation code (PyMDP, RxInfer, JAX, …): heavy, and not generally
  meaningful for codebase-derived bundles.

All four can be re-enabled by passing ``skip_steps=[]`` (or listing them in
``only_steps``).

Selection semantics: ``skip_steps`` (plus step 13 when ``skip_llm``) is passed
to upstream as ``--skip-steps``, so a skipped step never runs. Upstream
resolves declared prerequisites of the requested steps (e.g. ``16_analysis``
needs ``12_execute``, ``18_security`` needs ``11_render``) and runs any that
are not explicitly skipped; such steps are reported in
:attr:`UpstreamPipelineResult.auto_included`. A requested step whose
prerequisite is skipped still runs, with an upstream prerequisite warning.

The pipeline is **advisory**: a failing upstream step is recorded but does
not raise. Callers can promote any step to fatal by inspecting
``UpstreamPipelineResult.steps`` and acting on ``success=False``.
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Step catalogue
# ---------------------------------------------------------------------------

UPSTREAM_STEP_SCRIPTS: tuple[str, ...] = (
    "0_template.py",
    "1_setup.py",
    "2_tests.py",
    "3_gnn.py",
    "4_model_registry.py",
    "5_type_checker.py",
    "6_validation.py",
    "7_export.py",
    "8_visualization.py",
    "9_advanced_viz.py",
    "10_ontology.py",
    "11_render.py",
    "12_execute.py",
    "13_llm.py",
    "14_ml_integration.py",
    "15_audio.py",
    "16_analysis.py",
    "17_integration.py",
    "18_security.py",
    "19_research.py",
    "20_website.py",
    "21_mcp.py",
    "22_gui.py",
    "23_report.py",
    "24_intelligent_analysis.py",
)
"""Canonical 25 numbered scripts in the upstream pipeline (steps 0 → 24).

Indexed by step number: ``UPSTREAM_STEP_SCRIPTS[3] == "3_gnn.py"``.
"""

DEFAULT_SKIP_STEPS: frozenset[int] = frozenset({1, 2, 11, 12})
"""Steps suppressed by default (see the module docstring for rationale).

* ``1_setup`` — upstream environment provisioning (mutates the caller's
  environment when run from an installed wheel).
* ``2_tests`` — upstream repository test suite (not shipped in the wheel).
* ``11_render`` — framework-specific simulation code generation.
* ``12_execute`` — runs the rendered simulations (heavy optional deps).
"""

SUCCESS_STATUSES: frozenset[str] = frozenset({"SUCCESS", "SUCCESS_WITH_WARNINGS", "SKIPPED"})
"""Upstream step statuses COGANT counts as a passing step."""

DEFAULT_TIMEOUT_S: float = 3600.0
"""Bridge-level wall-clock ceiling for one upstream invocation (seconds).

Upstream applies its own per-step deadlines inside the invocation; this outer
bound only guarantees the COGANT caller is never blocked indefinitely.
"""

_SUMMARY_RELPATH = Path("00_pipeline_summary") / "pipeline_execution_summary.json"
_STAGED_INPUT_DIRNAME = "_cogant_input"
_LOG_FILENAME = "upstream_pipeline.log"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_gnn_main() -> Any | None:
    """Import upstream :mod:`gnn.main`, returning ``None`` if unavailable.

    GNN 4.x guarantees that importing ``gnn.main`` has no working-directory
    or import-path side effects, so no cwd guard is needed here.
    """
    try:
        return importlib.import_module("gnn.main")
    except ImportError:
        return None


def resolve_steps(
    only: list[int] | None,
    skip: list[int] | None,
) -> list[int]:
    """Return the ordered list of step indices to execute.

    Args:
        only: When set, restrict to these step indices (preserving canonical
            order). When ``None``, start from all 25 steps.
        skip: Step indices to drop after applying ``only``. Ignored entries
            outside ``range(25)`` are silently dropped (callers should
            validate beforehand).

    Returns:
        Sorted list of integers in ``[0, 25)``.

    Examples:
        >>> resolve_steps(None, [11, 12])
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
        >>> resolve_steps([3, 5, 7], None)
        [3, 5, 7]
        >>> resolve_steps([3, 5, 7], [5])
        [3, 7]
    """
    universe = set(range(len(UPSTREAM_STEP_SCRIPTS)))
    chosen = set(only) & universe if only is not None else set(universe)
    if skip:
        chosen -= set(skip)
    return sorted(chosen)


def _is_upstream_main_available() -> bool:
    """Return ``True`` when ``gnn.main`` can be imported."""
    return _import_gnn_main() is not None


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UpstreamStepResult:
    """Outcome of running a single upstream pipeline step.

    Attributes:
        step_index: Step number (0..24).
        script: Script filename (e.g. ``"3_gnn.py"``).
        status: Upstream-reported status string
            (``"SUCCESS"`` / ``"SUCCESS_WITH_WARNINGS"`` / ``"SKIPPED"`` /
            ``"FAILED"`` / ``"TIMEOUT"`` / ``"NOT_RUN"`` / ``"BRIDGE_ERROR"``).
        success: ``True`` iff ``status`` is one of
            ``{"SUCCESS", "SUCCESS_WITH_WARNINGS", "SKIPPED"}``.
        duration_s: Wall-clock duration in seconds.
        exit_code: Subprocess exit code (``-1`` when not available).
        memory_delta_mb: Resident-memory growth observed by upstream.
        output_dir: Absolute path to the per-step output directory, when
            known.
        error: Free-form error message when ``success`` is ``False``.
    """

    step_index: int
    script: str
    status: str
    success: bool
    duration_s: float
    exit_code: int = -1
    memory_delta_mb: float = 0.0
    output_dir: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "script": self.script,
            "status": self.status,
            "success": self.success,
            "duration_s": self.duration_s,
            "exit_code": self.exit_code,
            "memory_delta_mb": self.memory_delta_mb,
            "output_dir": self.output_dir,
            "error": self.error,
        }


@dataclass(frozen=True)
class UpstreamPipelineResult:
    """Aggregated outcome of an upstream pipeline run.

    Attributes:
        available: ``False`` when ``gnn.main`` could not be imported (in
            which case ``steps`` is empty and ``error`` describes why).
        steps: Per-step results in execution order.
        executed: Step indices requested from upstream plus any it
            auto-included (see ``auto_included``).
        skipped: Step indices that did not run.
        total_duration_s: Wall-clock duration of the upstream invocation.
        output_dir: Absolute path to the upstream output root.
        target_dir: Absolute path to the GNN package directory used as
            input.
        error: Bridge-level error (e.g. ``gnn.main`` import failure, a
            timeout, or a missing upstream summary).
        upstream_status: Upstream ``overall_status`` for the invocation, when
            the summary was produced.
        run_id: Upstream invocation ID (``GNN_RUN_ID``), when reported.
        auto_included: Steps upstream ran as declared prerequisites of the
            requested steps although the caller did not request them.
    """

    available: bool
    steps: list[UpstreamStepResult] = field(default_factory=list)
    executed: list[int] = field(default_factory=list)
    skipped: list[int] = field(default_factory=list)
    total_duration_s: float = 0.0
    output_dir: str | None = None
    target_dir: str | None = None
    error: str | None = None
    upstream_status: str | None = None
    run_id: str | None = None
    auto_included: list[int] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return sum(1 for s in self.steps if s.success)

    @property
    def failure_count(self) -> int:
        return sum(1 for s in self.steps if not s.success)

    @property
    def success_rate(self) -> float:
        """Fraction of executed steps that succeeded; ``0.0`` for empty runs."""
        if not self.steps:
            return 0.0
        return self.success_count / len(self.steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "executed": list(self.executed),
            "skipped": list(self.skipped),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "total_duration_s": self.total_duration_s,
            "output_dir": self.output_dir,
            "target_dir": self.target_dir,
            "error": self.error,
            "upstream_status": self.upstream_status,
            "run_id": self.run_id,
            "auto_included": list(self.auto_included),
            "steps": [s.to_dict() for s in self.steps],
        }


@dataclass
class UpstreamPipelineConfig:
    """Inputs for :func:`run_upstream_pipeline`.

    Attributes:
        target_dir: Directory containing the GNN markdown model (the COGANT
            ``gnn_package/`` works because it ships ``model.gnn.md`` at the
            root). Required.
        output_dir: Upstream output root (per-step sub-directories plus
            ``00_pipeline_summary/``). Required.
        only_steps: Restrict execution to these step indices. ``None`` means
            "every step in the catalogue".
        skip_steps: Step indices to drop. Defaults to
            :data:`DEFAULT_SKIP_STEPS`.
        frameworks: Forwarded to upstream ``--frameworks`` (used by
            ``11_render``/``12_execute``; e.g. ``"lite"``, ``"all"``,
            ``"pymdp,jax"``).
        llm_model: ``OLLAMA_MODEL`` for ``13_llm`` in the upstream child
            process (``None`` leaves the inherited value alone). The
            caller's own environment is never modified.
        timesteps: Forwarded to upstream ``--timesteps`` (``12_execute``).
        verbose: Forwarded to upstream ``--verbose``.
        skip_llm: Forwarded to upstream ``--skip-llm``.
        timeout_s: Bridge-level wall-clock ceiling for the invocation.
    """

    target_dir: Path
    output_dir: Path
    only_steps: list[int] | None = None
    skip_steps: list[int] = field(default_factory=lambda: sorted(DEFAULT_SKIP_STEPS))
    frameworks: str = "lite"
    llm_model: str | None = None
    timesteps: int = 15
    verbose: bool = False
    skip_llm: bool = False
    timeout_s: float = DEFAULT_TIMEOUT_S

    def __post_init__(self) -> None:
        self.target_dir = Path(self.target_dir).resolve()
        self.output_dir = Path(self.output_dir).resolve()


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def _stage_target_dir(cfg: UpstreamPipelineConfig) -> Path:
    """Stage only GNN markdown models as the upstream source corpus.

    A COGANT ``gnn_package/`` contains JSON sidecars that are valid package
    evidence but are not standalone GNN models. Upstream discovery treats
    every ``*.json`` file as a model source, so the invocation receives a
    small staging directory containing only ``*.gnn.md`` / ``model.gnn.md``.
    When no markdown model exists the original directory is returned so
    upstream reports the empty corpus itself.
    """
    markdown_files = sorted(cfg.target_dir.glob("*.gnn.md"))
    model_path = cfg.target_dir / "model.gnn.md"
    if model_path.is_file() and model_path not in markdown_files:
        markdown_files.insert(0, model_path)
    if not markdown_files:
        return cfg.target_dir

    staged = cfg.output_dir / _STAGED_INPUT_DIRNAME
    staged.mkdir(parents=True, exist_ok=True)
    for existing in staged.iterdir():
        if existing.is_file():
            existing.unlink()
    for source in markdown_files:
        shutil.copy2(source, staged / source.name)
    return staged


def _effective_skip(cfg: UpstreamPipelineConfig) -> list[int]:
    """Steps that must not run: ``skip_steps`` plus ``13_llm`` under ``skip_llm``."""
    universe = range(len(UPSTREAM_STEP_SCRIPTS))
    skip = {step for step in (cfg.skip_steps or []) if step in universe}
    if cfg.skip_llm:
        skip.add(UPSTREAM_STEP_SCRIPTS.index("13_llm.py"))
    return sorted(skip)


def _build_main_command(
    cfg: UpstreamPipelineConfig, target_dir: Path, chosen: list[int]
) -> list[str]:
    """Return the single ``python -m gnn.main`` invocation for ``chosen``.

    COGANT's active interpreter is used so the child resolves the same
    installed ``gnn`` package (never an upstream checkout's nested ``.venv``).
    The skip set is passed explicitly: upstream applies it after resolving
    prerequisites, so a skipped step cannot be pulled back in as a dependency.
    """
    cmd = [
        sys.executable,
        "-m",
        "gnn.main",
        "--target-dir",
        str(target_dir),
        "--output-dir",
        str(cfg.output_dir),
        "--only-steps",
        ",".join(str(step) for step in chosen),
        "--frameworks",
        cfg.frameworks,
        "--timesteps",
        str(cfg.timesteps),
        "--verbose" if cfg.verbose else "--no-verbose",
    ]
    skip = _effective_skip(cfg)
    if skip:
        cmd.extend(["--skip-steps", ",".join(str(step) for step in skip)])
    if cfg.skip_llm:
        cmd.append("--skip-llm")
    return cmd


def _child_env(cfg: UpstreamPipelineConfig) -> dict[str, str]:
    """Environment for the upstream child; the caller's env is not mutated."""
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    # Let upstream mint a fresh invocation ID: an inherited ID or run-context
    # file would claim an unrelated run's identity.
    env.pop("GNN_RUN_ID", None)
    env.pop("GNN_RUN_CONTEXT_FILE", None)
    if cfg.llm_model is not None:
        env["OLLAMA_MODEL"] = cfg.llm_model
    return env


def _per_step_output_dir(output_dir: Path, step_index: int) -> Path:
    """Return the conventional per-step output directory.

    Upstream writes ``<output_dir>/<step_stem>_output`` for most steps, where
    ``<step_stem>`` is the script name without the trailing ``.py``.
    """
    script = UPSTREAM_STEP_SCRIPTS[step_index]
    return output_dir / f"{script.removesuffix('.py')}_output"


def _last_line(text: str, *, marker: str | None = None) -> str | None:
    """Return the last non-empty line (optionally containing ``marker``)."""
    for line in reversed(text.splitlines()):
        stripped = line.strip()
        if stripped and (marker is None or marker in stripped):
            return stripped[:500]
    return None


def _step_error(raw: dict[str, Any]) -> str | None:
    """Single-line failure reason from an upstream step record."""
    stderr = str(raw.get("stderr") or "")
    stdout = str(raw.get("stdout") or "")
    return (
        _last_line(stderr)
        or _last_line(stdout, marker=" - ERROR - ")
        or _last_line(stdout, marker="FAILED")
    )


def _as_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _as_int(value: Any, default: int = -1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _steps_from_summary(
    summary: dict[str, Any], cfg: UpstreamPipelineConfig, chosen: list[int]
) -> list[UpstreamStepResult]:
    """Map upstream summary step records onto :class:`UpstreamStepResult`.

    Every requested step yields exactly one result: steps upstream never
    reached (aborted invocation, exhausted deadline) are reported as
    ``NOT_RUN`` failures rather than silently disappearing. Steps upstream ran
    without being requested (auto-included prerequisites) are reported too,
    in step order, so the result never hides work that ran.
    """
    by_script: dict[str, dict[str, Any]] = {}
    for raw in summary.get("steps") or []:
        if isinstance(raw, dict):
            by_script[str(raw.get("script_name", ""))] = raw
    reported = set(chosen) | {
        UPSTREAM_STEP_SCRIPTS.index(script)
        for script in by_script
        if script in UPSTREAM_STEP_SCRIPTS
    }

    results: list[UpstreamStepResult] = []
    for step_index in sorted(reported):
        script = UPSTREAM_STEP_SCRIPTS[step_index]
        out_dir = str(_per_step_output_dir(cfg.output_dir, step_index))
        raw = by_script.get(script)
        if raw is None:
            results.append(
                UpstreamStepResult(
                    step_index=step_index,
                    script=script,
                    status="NOT_RUN",
                    success=False,
                    duration_s=0.0,
                    output_dir=out_dir,
                    error="step absent from the upstream pipeline summary",
                )
            )
            continue
        status = str(raw.get("status", "UNKNOWN"))
        success = status in SUCCESS_STATUSES
        results.append(
            UpstreamStepResult(
                step_index=step_index,
                script=script,
                status=status,
                success=success,
                duration_s=_as_float(raw.get("duration_seconds")),
                exit_code=_as_int(raw.get("exit_code")),
                memory_delta_mb=_as_float(raw.get("memory_delta_mb")),
                output_dir=out_dir,
                error=None if success else _step_error(raw),
            )
        )
    return results


def _bridge_failure_steps(
    cfg: UpstreamPipelineConfig, chosen: list[int], status: str, error: str
) -> list[UpstreamStepResult]:
    """One failed result per requested step when no current summary exists."""
    return [
        UpstreamStepResult(
            step_index=step_index,
            script=UPSTREAM_STEP_SCRIPTS[step_index],
            status=status,
            success=False,
            duration_s=0.0,
            output_dir=str(_per_step_output_dir(cfg.output_dir, step_index)),
            error=error,
        )
        for step_index in chosen
    ]


def _read_summary(path: Path, started_at: float) -> dict[str, Any] | None:
    """Load the upstream summary written by *this* invocation, if any.

    A summary older than the invocation start belongs to a previous run in
    the same output root and must not be reported as current evidence.
    """
    try:
        if path.stat().st_mtime < started_at:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _read_log_tail(path: Path, limit: int = 20_000) -> str:
    """Return up to the last ``limit`` characters of the upstream log."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[-limit:]


def _write_bridge_summary(
    cfg: UpstreamPipelineConfig,
    result: UpstreamPipelineResult,
) -> None:
    summary_path = cfg.output_dir / "upstream_pipeline_summary.json"
    payload = result.to_dict()
    try:
        summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:  # pragma: no cover - defensive
        logger.warning(
            "Could not write upstream pipeline summary to %s: %s",
            summary_path,
            exc,
        )


def run_upstream_pipeline(
    cfg: UpstreamPipelineConfig,
) -> UpstreamPipelineResult:
    """Execute the configured subset of upstream pipeline steps.

    Issues one ``python -m gnn.main --only-steps …`` invocation against a
    staged copy of the package's GNN markdown, then reads per-step outcomes
    from the upstream run summary. One failing step does not abort the run
    (upstream continues past non-critical failures); bridge-level problems —
    timeout, a crashed invocation, a missing summary — are reported per
    requested step with ``status`` ``TIMEOUT`` / ``BRIDGE_ERROR`` and on
    :attr:`UpstreamPipelineResult.error`. The upstream console log is written
    to ``<output_dir>/upstream_pipeline.log`` and the bridge summary to
    ``<output_dir>/upstream_pipeline_summary.json``.

    Args:
        cfg: Pipeline configuration.

    Returns:
        :class:`UpstreamPipelineResult` with one :class:`UpstreamStepResult`
        per requested step.
    """
    if _import_gnn_main() is None:
        return UpstreamPipelineResult(
            available=False,
            error=(
                "gnn.main not importable; install the optional cogant[upstream] "
                "extra (generalized-notation-notation)"
            ),
            target_dir=str(cfg.target_dir),
            output_dir=str(cfg.output_dir),
        )

    chosen = resolve_steps(cfg.only_steps, _effective_skip(cfg))
    skipped = [i for i in range(len(UPSTREAM_STEP_SCRIPTS)) if i not in chosen]
    if not chosen:
        # Upstream rejects an empty step selection at admission; an empty
        # request is a no-op, not a failure.
        return UpstreamPipelineResult(
            available=True,
            skipped=skipped,
            target_dir=str(cfg.target_dir),
            output_dir=str(cfg.output_dir),
        )

    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    cmd = _build_main_command(cfg, _stage_target_dir(cfg), chosen)

    logger.info(
        "Upstream GNN pipeline: %d/%d steps selected (skipping %s) target=%s",
        len(chosen),
        len(UPSTREAM_STEP_SCRIPTS),
        skipped,
        cfg.target_dir,
    )

    log_path = cfg.output_dir / _LOG_FILENAME
    started_wall = time.time()
    total_start = time.perf_counter()
    returncode: int | None = None
    bridge_error: str | None = None
    bridge_status = "BRIDGE_ERROR"
    try:
        with log_path.open("w", encoding="utf-8") as log_handle:
            completed = subprocess.run(
                cmd,
                cwd=cfg.output_dir,
                env=_child_env(cfg),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                timeout=cfg.timeout_s,
                check=False,
            )
        returncode = completed.returncode
    except subprocess.TimeoutExpired:
        bridge_status = "TIMEOUT"
        bridge_error = f"upstream gnn.main exceeded the {cfg.timeout_s:g}s bridge timeout"
    except OSError as exc:
        bridge_error = f"could not launch upstream gnn.main: {exc}"
    total = time.perf_counter() - total_start

    summary = _read_summary(cfg.output_dir / _SUMMARY_RELPATH, started_wall)
    upstream_status: str | None = None
    run_id: str | None = None
    auto_included: list[int] = []
    if summary is not None:
        steps = _steps_from_summary(summary, cfg, chosen)
        upstream_status = str(summary.get("overall_status") or "") or None
        run_id = str(summary.get("run_id") or "") or None
        auto_included = sorted(s.step_index for s in steps if s.step_index not in chosen)
    else:
        if bridge_error is None:
            tail = _last_line(_read_log_tail(log_path)) or "no output"
            bridge_error = (
                f"upstream gnn.main exited {returncode} without a pipeline summary: {tail}"
            )
        steps = _bridge_failure_steps(cfg, chosen, bridge_status, bridge_error)

    for step in steps:
        log = logger.info if step.success else logger.warning
        log(
            "Upstream step %s -> %s in %.2fs%s",
            step.script,
            step.status,
            step.duration_s,
            f" ({step.error})" if step.error else "",
        )

    executed = sorted(set(chosen) | set(auto_included))
    result = UpstreamPipelineResult(
        available=True,
        steps=steps,
        executed=executed,
        skipped=[i for i in skipped if i not in auto_included],
        total_duration_s=total,
        output_dir=str(cfg.output_dir),
        target_dir=str(cfg.target_dir),
        error=bridge_error,
        upstream_status=upstream_status,
        run_id=run_id,
        auto_included=auto_included,
    )
    _write_bridge_summary(cfg, result)
    return result


__all__ = [
    "DEFAULT_SKIP_STEPS",
    "DEFAULT_TIMEOUT_S",
    "SUCCESS_STATUSES",
    "UPSTREAM_STEP_SCRIPTS",
    "UpstreamPipelineConfig",
    "UpstreamPipelineResult",
    "UpstreamStepResult",
    "resolve_steps",
    "run_upstream_pipeline",
]
