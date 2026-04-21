"""Configurable driver for the upstream GNN 25-step pipeline.

This module composes the Active Inference Institute
``generalized-notation-notation`` numbered pipeline (steps ``0_template`` →
``24_intelligent_analysis``) on top of a COGANT-built ``gnn_package/``.

The 10-stage COGANT pipeline produces a ``model.gnn.md`` plus the 16 required
JSON sidecars at ``bundle.artifacts['_gnn_package_dir']``. Pointing the
upstream pipeline at that directory exercises the full Active Inference
processing chain (parsing, validation, ontology, ML integration, reporting,
…) over the bundle COGANT just emitted.

Default behaviour skips ``11_render`` and ``12_execute``: those steps generate
framework-specific simulation code (PyMDP, RxInfer, JAX, …) and run it, which
is heavy and not generally meaningful for codebase-derived bundles. Both can
be turned back on by passing ``skip_steps=[]`` (or by listing them in
``only_steps``).

The pipeline is **advisory**: a failing upstream step is recorded but does
not raise. Callers can promote any step to fatal by inspecting
``UpstreamPipelineResult.steps`` and acting on ``success=False``.

Side-effects of importing :mod:`src.main` (it ``chdir`` s to its own project
root on import) are contained by :func:`_preserve_cwd`, so the rest of
COGANT keeps the caller's working directory.
"""

from __future__ import annotations

import contextlib
import importlib
import json
import logging
import os
import time
from collections.abc import Iterator
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

DEFAULT_SKIP_STEPS: frozenset[int] = frozenset({11, 12})
"""Steps suppressed by default.

* ``11_render`` — generates framework-specific simulation code (PyMDP, RxInfer,
  JAX, …) which only makes sense for small synthetic Active Inference models.
* ``12_execute`` — runs the rendered simulation; depends on heavy optional
  deps (JAX, PyMDP, …) and assumes a runnable model.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _preserve_cwd() -> Iterator[None]:
    """Restore ``os.getcwd()`` after the ``with`` block.

    Importing :mod:`src.main` ``chdir`` s to the upstream project root; this
    context manager guarantees the caller never observes that side-effect.
    """
    saved = os.getcwd()
    try:
        yield
    finally:
        try:
            os.chdir(saved)
        except OSError:
            pass


def _import_src_main() -> Any | None:
    """Import :mod:`src.main`, returning ``None`` if unavailable."""
    try:
        with _preserve_cwd():
            return importlib.import_module("src.main")
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
    """Return ``True`` when ``src.main`` can be imported."""
    return _import_src_main() is not None


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
            ``"FAILED"`` / ``"UNKNOWN"`` / ``"BRIDGE_ERROR"``).
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
        available: ``False`` when ``src.main`` could not be imported (in
            which case ``steps`` is empty and ``error`` describes why).
        steps: Per-step results in execution order.
        executed: Step indices actually invoked.
        skipped: Step indices intentionally skipped.
        total_duration_s: Wall-clock duration across all executed steps.
        output_dir: Absolute path to the upstream output root.
        target_dir: Absolute path to the GNN package directory used as
            input.
        error: Bridge-level error (e.g. ``src.main`` import failure).
    """

    available: bool
    steps: list[UpstreamStepResult] = field(default_factory=list)
    executed: list[int] = field(default_factory=list)
    skipped: list[int] = field(default_factory=list)
    total_duration_s: float = 0.0
    output_dir: str | None = None
    target_dir: str | None = None
    error: str | None = None

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
            "steps": [s.to_dict() for s in self.steps],
        }


@dataclass
class UpstreamPipelineConfig:
    """Inputs for :func:`run_upstream_pipeline`.

    Attributes:
        target_dir: Directory containing GNN ``*.md`` files (the COGANT
            ``gnn_package/`` works because it ships ``model.gnn.md`` at the
            root). Required.
        output_dir: Where upstream writes per-step output sub-directories.
            Required.
        only_steps: Restrict execution to these step indices. ``None`` means
            "every step in the catalogue".
        skip_steps: Step indices to drop. Defaults to
            :data:`DEFAULT_SKIP_STEPS`.
        frameworks: Forwarded to upstream ``11_render``/``12_execute`` when
            those steps are enabled (e.g. ``"lite"``, ``"all"``,
            ``"pymdp,jax"``).
        llm_model: Override ``OLLAMA_MODEL`` for ``13_llm`` (set to ``None``
            to leave the env var alone).
        timesteps: Forwarded to upstream ``12_execute``.
        verbose: Forwarded to upstream's logger / argument parser.
        skip_llm: Forwarded to upstream's ``--skip-llm`` flag.
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

    def __post_init__(self) -> None:
        self.target_dir = Path(self.target_dir).resolve()
        self.output_dir = Path(self.output_dir).resolve()


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def _build_pipeline_arguments(src_main: Any, cfg: UpstreamPipelineConfig) -> Any:
    """Materialise an upstream :class:`PipelineArguments` from ``cfg``.

    Expects an already-imported ``src.main`` module so we don't pay the
    import (and its ``chdir`` side-effect) twice.
    """
    import sys

    with _preserve_cwd():
        # ``utils.argument_utils`` lives next to ``src/main.py``; expose it.
        if str(src_main.SCRIPT_DIR) not in sys.path:
            sys.path.insert(0, str(src_main.SCRIPT_DIR))
        from utils.argument_utils import PipelineArguments  # type: ignore[import-not-found]

    return PipelineArguments(
        target_dir=cfg.target_dir,
        output_dir=cfg.output_dir,
        verbose=cfg.verbose,
        skip_llm=cfg.skip_llm,
        timesteps=cfg.timesteps,
        frameworks=cfg.frameworks,
    )


def _per_step_output_dir(output_dir: Path, step_index: int) -> Path:
    """Return the conventional per-step output directory.

    Upstream writes ``<output_dir>/<step_stem>_output`` for most steps, where
    ``<step_stem>`` is the script name without the trailing ``.py``.
    """
    script = UPSTREAM_STEP_SCRIPTS[step_index]
    return output_dir / f"{script.removesuffix('.py')}_output"


def run_upstream_pipeline(
    cfg: UpstreamPipelineConfig,
) -> UpstreamPipelineResult:
    """Execute the configured subset of upstream pipeline steps.

    Each enabled step is invoked via :func:`src.main.execute_pipeline_step`,
    which spawns the numbered script as a subprocess against ``cfg.target_dir``
    and ``cfg.output_dir``. One failing step does not abort the run; bridge
    errors are captured per-step into :attr:`UpstreamStepResult.error`.

    Args:
        cfg: Pipeline configuration.

    Returns:
        :class:`UpstreamPipelineResult` with one :class:`UpstreamStepResult`
        per executed step.
    """
    src_main = _import_src_main()
    if src_main is None:
        return UpstreamPipelineResult(
            available=False,
            error=("src.main not importable; install generalized-notation-notation"),
            target_dir=str(cfg.target_dir),
            output_dir=str(cfg.output_dir),
        )

    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    if cfg.llm_model is not None:
        os.environ["OLLAMA_MODEL"] = cfg.llm_model

    chosen = resolve_steps(cfg.only_steps, cfg.skip_steps)
    skipped = [i for i in range(len(UPSTREAM_STEP_SCRIPTS)) if i not in chosen]

    logger.info(
        "Upstream GNN pipeline: %d/%d steps selected (skipping %s) target=%s",
        len(chosen),
        len(UPSTREAM_STEP_SCRIPTS),
        skipped,
        cfg.target_dir,
    )

    step_results: list[UpstreamStepResult] = []
    total_start = time.perf_counter()

    with _preserve_cwd():
        step_logger = src_main.setup_step_logging(
            "cogant.upstream_pipeline",
            verbose=cfg.verbose,
        )
        args = _build_pipeline_arguments(src_main, cfg)

        for position, step_index in enumerate(chosen, start=1):
            script = UPSTREAM_STEP_SCRIPTS[step_index]
            logger.info(
                "Upstream step %d/%d: %s",
                position,
                len(chosen),
                script,
            )
            step_start = time.perf_counter()
            try:
                with _preserve_cwd():
                    raw = src_main.execute_pipeline_step(script, args, step_logger)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Upstream step %s raised: %s", script, exc, exc_info=True)
                step_results.append(
                    UpstreamStepResult(
                        step_index=step_index,
                        script=script,
                        status="BRIDGE_ERROR",
                        success=False,
                        duration_s=time.perf_counter() - step_start,
                        error=f"{type(exc).__name__}: {exc}",
                        output_dir=str(_per_step_output_dir(cfg.output_dir, step_index)),
                    )
                )
                continue

            status = str(raw.get("status", "UNKNOWN"))
            success = status in {"SUCCESS", "SUCCESS_WITH_WARNINGS", "SKIPPED"}
            stderr = str(raw.get("stderr", "") or "")
            error: str | None = None
            if not success and stderr:
                # Trim noisy stderr to a single line for the summary; full
                # output remains in upstream's per-step log file.
                error = stderr.strip().splitlines()[-1][:500]
            duration = time.perf_counter() - step_start
            log = logger.info if success else logger.warning
            log(
                "Upstream step %s -> %s in %.2fs%s",
                script,
                status,
                duration,
                f" ({error})" if error else "",
            )
            step_results.append(
                UpstreamStepResult(
                    step_index=step_index,
                    script=script,
                    status=status,
                    success=success,
                    duration_s=duration,
                    exit_code=int(raw.get("exit_code", -1)),
                    memory_delta_mb=float(raw.get("memory_delta_mb", 0.0)),
                    output_dir=str(_per_step_output_dir(cfg.output_dir, step_index)),
                    error=error,
                )
            )

    total = time.perf_counter() - total_start

    summary_path = cfg.output_dir / "upstream_pipeline_summary.json"
    try:
        summary_path.write_text(
            json.dumps(
                {
                    "target_dir": str(cfg.target_dir),
                    "output_dir": str(cfg.output_dir),
                    "executed": chosen,
                    "skipped": skipped,
                    "steps": [s.to_dict() for s in step_results],
                    "total_duration_s": total,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError as exc:  # pragma: no cover - defensive
        logger.warning(
            "Could not write upstream pipeline summary to %s: %s",
            summary_path,
            exc,
        )

    return UpstreamPipelineResult(
        available=True,
        steps=step_results,
        executed=chosen,
        skipped=skipped,
        total_duration_s=total,
        output_dir=str(cfg.output_dir),
        target_dir=str(cfg.target_dir),
    )


__all__ = [
    "DEFAULT_SKIP_STEPS",
    "UPSTREAM_STEP_SCRIPTS",
    "UpstreamPipelineConfig",
    "UpstreamPipelineResult",
    "UpstreamStepResult",
    "resolve_steps",
    "run_upstream_pipeline",
]
