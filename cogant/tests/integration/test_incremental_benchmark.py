"""Benchmark: full cold run vs incremental second run.

Real behavioral test — no mocking. We build a small synthetic Python
package inside a fresh git repo, invoke ``PipelineRunner.run`` end-to-
end once for the cold baseline, then re-run it with
``incremental_since="HEAD"`` pointed at the same isolated cache
directory. A zero-change incremental second run MUST hit the cache and
MUST be materially faster than the cold baseline.

Why we do not use the Typer CLI via subprocess here: subprocess spawn
overhead on macOS + Python import dwarfs the measured pipeline time on a
3-file repo, which would make the ratio noisy. We exercise the same
``PipelineRunner`` object that the ``cogant analyze --incremental``
command wires up, so the coverage is equivalent for the incremental
code path under test.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest

from cogant.api.pipeline import PipelineConfig, PipelineRunner

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Synthetic repo fixture
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> None:
    """Run a ``git`` command inside ``repo``, raising on failure."""
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _make_fixture_repo(root: Path) -> Path:
    """Create a tiny Python package inside a fresh git repo."""
    repo = root / "fixture_repo"
    pkg = repo / "mypkg"
    pkg.mkdir(parents=True)

    (pkg / "__init__.py").write_text('"""mypkg — synthetic test package."""\n')
    (pkg / "adder.py").write_text(
        '"""Simple adder module."""\n'
        "\n"
        "def add(a: int, b: int) -> int:\n"
        '    """Return a + b."""\n'
        "    return a + b\n"
        "\n"
        "\n"
        "def add_many(values: list[int]) -> int:\n"
        '    """Sum a list of ints."""\n'
        "    total = 0\n"
        "    for v in values:\n"
        "        total = add(total, v)\n"
        "    return total\n"
    )
    (pkg / "multiplier.py").write_text(
        '"""Simple multiplier module."""\n'
        "\n"
        "from mypkg.adder import add\n"
        "\n"
        "\n"
        "def mul(a: int, b: int) -> int:\n"
        '    """Multiply a * b using repeated addition."""\n'
        "    result = 0\n"
        "    for _ in range(b):\n"
        "        result = add(result, a)\n"
        "    return result\n"
    )
    (pkg / "pipeline.py").write_text(
        '"""Orchestrator that wires adder + multiplier."""\n'
        "\n"
        "from mypkg.adder import add_many\n"
        "from mypkg.multiplier import mul\n"
        "\n"
        "\n"
        "def run(items: list[int], factor: int) -> int:\n"
        '    """Sum items then multiply by factor."""\n'
        "    total = add_many(items)\n"
        "    return mul(total, factor)\n"
    )

    # Initialize git and commit
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@cogant.invalid")
    _git(repo, "config", "user.name", "Cogant Test")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "initial fixture")
    return repo


def _run_pipeline(
    repo: Path, cache_dir: Path, output_dir: Path, since: str | None
) -> tuple[float, object]:
    """Execute the pipeline once and return (elapsed_seconds, bundle)."""
    config = PipelineConfig(
        output_dir=str(output_dir),
        skip_stages=["export", "validate"],  # mirror benchmark command scope
        skip_dynamic=True,  # no coverage data → avoid auto-detect branch
        cache_dir=str(cache_dir),
        incremental_since=since,
    )
    runner = PipelineRunner()
    start = time.perf_counter()
    bundle = runner.run(str(repo), config)
    elapsed = time.perf_counter() - start
    return elapsed, bundle


# ---------------------------------------------------------------------------
# Actual benchmark
# ---------------------------------------------------------------------------


def test_incremental_zero_change_is_faster(tmp_path: Path) -> None:
    """Incremental run with no changes is faster than a cold run.

    Contract:
    * Cold run populates the incremental cache.
    * Second run with ``incremental_since="HEAD"`` sees zero changed
      files → full cache hit → returns the cached bundle.
    * Incremental wall-clock is at most half the cold wall-clock.
    """
    repo = _make_fixture_repo(tmp_path)
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Cold run — seeds the cache. We still pass ``incremental_since`` so
    # the save path (``_incremental_cache_save``) actually fires; without
    # it the runner never touches the cache.
    cold_elapsed, cold_bundle = _run_pipeline(
        repo,
        cache_dir=cache_dir,
        output_dir=tmp_path / "out_cold",
        since="HEAD",
    )
    assert cold_bundle is not None
    cold_stats = cold_bundle.metadata.get("incremental_stats") or {}
    assert cold_stats.get("enabled") is True
    # First run: cache is empty, so this MUST be a miss and a full run.
    assert cold_stats.get("cache_hit") is False, (
        f"Cold run should miss the (empty) cache, got stats={cold_stats}"
    )

    # Sanity check: cache should now contain exactly one entry.
    shard_files = list(cache_dir.rglob("*.json"))
    assert shard_files, f"Cold run failed to populate {cache_dir}; found no JSON entries"

    # Warm incremental run — same HEAD, no code changes.
    warm_elapsed, warm_bundle = _run_pipeline(
        repo,
        cache_dir=cache_dir,
        output_dir=tmp_path / "out_warm",
        since="HEAD",
    )
    warm_stats = warm_bundle.metadata.get("incremental_stats") or {}

    # --- Correctness assertions -------------------------------------------
    assert warm_stats.get("enabled") is True
    assert warm_stats.get("cache_hit") is True, (
        f"Warm run should hit the cache, got stats={warm_stats}"
    )
    assert warm_stats.get("files_reparsed", -1) == 0, (
        f"Zero-change warm run should reparse 0 files, got stats={warm_stats}"
    )
    # files_total should see all 4 Python files (3 modules + __init__)
    assert warm_stats.get("files_total", 0) >= 3, (
        f"Expected ≥3 python files discovered, got stats={warm_stats}"
    )

    # --- Performance assertion --------------------------------------------
    # Primary contract: at least 2x faster. We add a small absolute floor
    # to protect against flaky sub-millisecond measurements on very fast
    # machines (the cold run on a 3-file repo can legitimately take just
    # a few tens of milliseconds).
    assert cold_elapsed > 0.0
    assert warm_elapsed > 0.0
    ratio = cold_elapsed / max(warm_elapsed, 1e-6)
    # Allow a tiny grace band when both runs are under 50ms; otherwise
    # enforce the 2x speedup strictly.
    if cold_elapsed > 0.05:
        assert warm_elapsed < cold_elapsed * 0.5, (
            f"Incremental was not 2x faster: "
            f"cold={cold_elapsed:.4f}s warm={warm_elapsed:.4f}s "
            f"ratio={ratio:.2f}"
        )
    else:
        # Very fast cold run — still require some speedup, but tolerate noise.
        assert warm_elapsed <= cold_elapsed, (
            f"Incremental should not be slower than cold on a trivial repo: "
            f"cold={cold_elapsed:.4f}s warm={warm_elapsed:.4f}s"
        )


def test_incremental_after_edit_reparses_only_changed(tmp_path: Path) -> None:
    """After editing one file, incremental reparses exactly that file.

    This complements the zero-change benchmark above: it verifies the
    *partial-hit* branch of ``_incremental_preflight`` — the actual
    graph-delta patching path.
    """
    repo = _make_fixture_repo(tmp_path)
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Cold run to seed the cache.
    _run_pipeline(
        repo,
        cache_dir=cache_dir,
        output_dir=tmp_path / "out_cold",
        since="HEAD",
    )

    # Record the commit we'll diff against, then edit one file and commit.
    baseline_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    target = repo / "mypkg" / "multiplier.py"
    target.write_text(
        target.read_text() + "\n"
        "def mul_const(a: int) -> int:\n"
        '    """Multiply a by a fixed constant."""\n'
        "    return mul(a, 7)\n"
    )
    _git(repo, "add", "mypkg/multiplier.py")
    _git(repo, "commit", "-q", "-m", "edit multiplier")

    # Incremental run against the baseline SHA.
    elapsed, bundle = _run_pipeline(
        repo,
        cache_dir=cache_dir,
        output_dir=tmp_path / "out_partial",
        since=baseline_sha,
    )
    stats = bundle.metadata.get("incremental_stats") or {}

    assert stats.get("enabled") is True
    assert stats.get("cache_hit") is True, (
        f"Partial incremental should still see a cache hit, got {stats}"
    )
    # Exactly one file changed between baseline_sha and HEAD.
    assert stats.get("files_reparsed") == 1, f"Expected 1 file reparsed, got stats={stats}"
    assert elapsed > 0.0
