"""Tests for RunBatchOptions and programmatic run_batch invocation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_all_runner import RunBatchOptions, run_batch  # noqa: E402


def test_run_batch_options_from_namespace() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--log", type=Path, default=None)
    parser.add_argument("--targets", type=str, default=None)
    ns = parser.parse_args(["--dry-run", "--targets", "calculator"])
    opts = RunBatchOptions.from_namespace(ns)
    assert opts.dry_run is True
    assert opts.targets == "calculator"
    assert opts.fail_fast is False


def test_run_batch_options_from_sparse_namespace() -> None:
    opts = RunBatchOptions.from_namespace(argparse.Namespace(dry_run=True))

    assert opts.config is None
    assert opts.dry_run is True
    assert opts.fail_fast is False
    assert opts.log is None
    assert opts.targets is None


def test_run_batch_accepts_options_directly() -> None:
    """Programmatic callers must not depend on sys.argv re-parsing."""
    opts = RunBatchOptions(dry_run=True, targets="calculator")
    rc = run_batch(opts)
    assert rc == 0
