"""Performance regression harness for COGANT pipeline.

Tracks pipeline wall-clock time on fixed fixtures and fails any fixture that
is more than 20% slower than its recorded baseline.

Usage:

    # Regenerate baseline (run when intentional perf changes are made):
    uv run python benchmarks/bench_perf_regression.py --generate-baseline

    # Run as a test (marked ``slow`` -- opt-in via ``-m slow``):
    uv run pytest benchmarks/bench_perf_regression.py -v -m slow

The harness runs the full in-process :class:`cogant.api.pipeline.PipelineRunner`
(with dynamic + validate stages skipped so timings are stable and self-contained)
against three control fixtures: ``calculator``, ``event_pipeline``, and
``flask_app``. Baseline data lives alongside the harness in ``perf_baseline.json``
so CI can diff it in PRs.
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
import tempfile
import time
from datetime import date
from pathlib import Path
from typing import Any

import pytest

# Ensure the pure-Python package under ``py/`` is importable without an
# editable install. Mirrors the path tweak used by ``tests/conftest.py``.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_PY_ROOT = _REPO_ROOT / "py"
if _PY_ROOT.is_dir() and str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))

from cogant.api.pipeline import PipelineConfig, PipelineRunner  # noqa: E402

# --- Configuration ----------------------------------------------------------

# Fixtures are resolved relative to the repo root. Keys are the stable fixture
# names recorded in the baseline; values are the filesystem paths.
FIXTURES: dict[str, Path] = {
    "calculator": _REPO_ROOT / "examples" / "control_positive" / "calculator",
    "event_pipeline": _REPO_ROOT / "examples" / "control_positive" / "event_pipeline",
    "flask_app": _REPO_ROOT / "examples" / "real_world" / "flask_app",
}

BASELINE_FILE = Path(__file__).parent / "perf_baseline.json"

# A fixture is considered a regression if its current median is more than
# ``THRESHOLD`` times the baseline median.
THRESHOLD = 1.20  # 20% regression threshold

# Iterations used when measuring during a test run. Kept small so the slow
# test still completes in a reasonable time on developer machines.
TEST_ITERATIONS = 3

# Iterations used when generating a baseline. Larger so medians/p95 are stable.
BASELINE_ITERATIONS = 5

logger = logging.getLogger(__name__)


# --- Measurement primitives -------------------------------------------------


def _run_pipeline_once(fixture_path: Path) -> None:
    """Run a single end-to-end pipeline invocation against ``fixture_path``.

    Uses a fresh temp directory for exports each call to avoid cross-run
    interference. ``dynamic`` and ``validate`` stages are skipped so the
    measurement focuses on the deterministic core pipeline.
    """
    runner = PipelineRunner()
    with tempfile.TemporaryDirectory(prefix="cogant-perf-") as tmp:
        config = PipelineConfig(
            output_dir=tmp,
            skip_dynamic=True,
            skip_stages=["validate"],
        )
        runner.run(str(fixture_path), config)


def measure(fixture_path: Path, iterations: int) -> dict[str, float]:
    """Measure median / p95 wall-clock milliseconds for ``iterations`` runs.

    The first run is used as a warm-up (results discarded) when enough
    iterations are available so Python import caches and filesystem state
    do not bias the first data point.
    """
    if iterations < 1:
        raise ValueError(f"iterations must be >= 1, got {iterations}")

    samples_ms: list[float] = []
    total = iterations + (1 if iterations >= 2 else 0)
    for idx in range(total):
        start = time.perf_counter()
        _run_pipeline_once(fixture_path)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        # Discard the warm-up sample when we recorded an extra run.
        if total > iterations and idx == 0:
            logger.debug("warm-up run for %s: %.1fms (discarded)", fixture_path.name, elapsed_ms)
            continue
        samples_ms.append(elapsed_ms)

    samples_sorted = sorted(samples_ms)
    # p95 index using the nearest-rank method; clamp to last element.
    p95_idx = min(len(samples_sorted) - 1, max(0, int(round(0.95 * len(samples_sorted))) - 1))
    return {
        "median_ms": statistics.median(samples_sorted),
        "p95_ms": samples_sorted[p95_idx],
        "samples": samples_sorted,
    }


# --- Baseline generation ----------------------------------------------------


def generate_baseline(output_path: Path = BASELINE_FILE) -> dict[str, Any]:
    """Run every fixture ``BASELINE_ITERATIONS`` times and write the baseline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger.info("Generating perf baseline (%d iterations per fixture)", BASELINE_ITERATIONS)

    fixtures_data: dict[str, dict[str, float]] = {}
    for name, path in FIXTURES.items():
        if not path.exists():
            logger.warning("Skipping missing fixture %s: %s", name, path)
            continue
        logger.info("Measuring %s (%s)", name, path)
        result = measure(path, iterations=BASELINE_ITERATIONS)
        fixtures_data[name] = {
            "median_ms": round(result["median_ms"], 2),
            "p95_ms": round(result["p95_ms"], 2),
        }
        logger.info(
            "  %s: median=%.1fms p95=%.1fms",
            name,
            fixtures_data[name]["median_ms"],
            fixtures_data[name]["p95_ms"],
        )

    baseline = {
        "generated": date.today().isoformat(),
        "iterations": BASELINE_ITERATIONS,
        "threshold": THRESHOLD,
        "fixtures": fixtures_data,
    }
    output_path.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
    logger.info("Wrote baseline to %s", output_path)
    return baseline


# --- pytest integration -----------------------------------------------------


@pytest.mark.slow
def test_no_perf_regression() -> None:
    """Fail if any fixture is > THRESHOLD slower than its baseline median.

    Skipped gracefully when no baseline is present so the default test run
    doesn't flake on fresh clones. Regenerate with::

        uv run python benchmarks/bench_perf_regression.py --generate-baseline
    """
    if not BASELINE_FILE.exists():
        pytest.skip(
            "No perf baseline found; run "
            "`python benchmarks/bench_perf_regression.py --generate-baseline`"
        )

    baseline = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    fixtures = baseline.get("fixtures", {})
    if not fixtures:
        pytest.skip("Baseline has no fixture data")

    regressions: list[str] = []
    for name, path in FIXTURES.items():
        if name not in fixtures:
            logger.info("No baseline entry for %s; skipping", name)
            continue
        if not path.exists():
            logger.warning("Fixture %s missing on disk: %s", name, path)
            continue

        current = measure(path, iterations=TEST_ITERATIONS)
        baseline_median = float(fixtures[name]["median_ms"])
        limit = baseline_median * THRESHOLD
        logger.info(
            "[perf] %s: current=%.1fms baseline=%.1fms limit=%.1fms",
            name,
            current["median_ms"],
            baseline_median,
            limit,
        )
        if current["median_ms"] >= limit:
            regressions.append(
                f"{name}: {current['median_ms']:.0f}ms >= {limit:.0f}ms "
                f"(baseline {baseline_median:.0f}ms, threshold {int((THRESHOLD - 1) * 100)}%)"
            )

    if regressions:
        pytest.fail("Performance regression detected:\n  " + "\n  ".join(regressions))


# --- CLI entrypoint ---------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--generate-baseline",
        action="store_true",
        help="Run each fixture %d times and overwrite perf_baseline.json" % BASELINE_ITERATIONS,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=BASELINE_FILE,
        help="Path to baseline file (default: %(default)s)",
    )
    args = parser.parse_args()

    if args.generate_baseline:
        generate_baseline(args.output)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
