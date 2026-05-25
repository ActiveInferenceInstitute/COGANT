#!/usr/bin/env python3
"""Build a cross-target dashboard for a COGANT ``run_all`` output tree.

Wraps :class:`cogant.viz.batch_dashboard.BatchDashboardGenerator` so the
staging-root orchestrator (``run_all.py``) — and humans — can produce
``output/dashboard/`` artifacts without writing Python.

Typical usage (from the COGANT project root):

.. code-block:: bash

    # After a normal run_all sweep:
    uv run --directory cogant python ../scripts/batch_dashboard.py \\
        --output-root cogant/output

    # Custom destination:
    uv run --directory cogant python ../scripts/batch_dashboard.py \\
        --output-root cogant/output \\
        --dashboard-dir cogant/output/dashboard

The script prints absolute paths of every written file, one per line, on
stdout (for the manifest collector in ``run_all.py``) and a one-line
human banner on stderr. Exit code is ``0`` on success; ``2`` when
``--output-root`` is missing. Relative paths are accepted from either the
current process directory or the staging root, which keeps the documented
``uv run --directory cogant`` invocation ergonomic.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running directly without an editable install: prepend the inner
# package's ``py/`` so ``import cogant`` resolves.
_STAGING_ROOT = Path(__file__).resolve().parent.parent
_PY_ROOT = _STAGING_ROOT / "cogant" / "py"
if _PY_ROOT.is_dir() and str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))


def _resolve_relative_to_staging(path: Path) -> Path:
    """Resolve a CLI path, accepting either current-cwd or staging-root paths."""
    if path.is_absolute() or path.exists():
        return path
    staging_path = _STAGING_ROOT / path
    if staging_path.exists():
        return staging_path
    return path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build COGANT batch dashboard artifacts from a run_all output tree.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("cogant/output"),
        help="Directory written by run_all (default: cogant/output).",
    )
    parser.add_argument(
        "--dashboard-dir",
        type=Path,
        default=None,
        help="Where to write dashboard artifacts (default: <output-root>/dashboard).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help=(
            "Explicit run_manifest.json path; default: <output-root>/run_manifest.json. "
            "Used mostly by tests and ad-hoc reports."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the stderr banner (stdout paths still printed).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    output_root = _resolve_relative_to_staging(args.output_root)
    if not output_root.is_dir():
        print(
            f"batch_dashboard: --output-root {output_root} is not a directory",
            file=sys.stderr,
        )
        return 2

    from cogant.viz.batch_dashboard import BatchDashboardGenerator  # late import

    explicit_manifest = None
    if args.manifest is not None:
        manifest_path = _resolve_relative_to_staging(args.manifest)
        if not manifest_path.is_file():
            print(
                f"batch_dashboard: --manifest {manifest_path} does not exist",
                file=sys.stderr,
            )
            return 2
        try:
            explicit_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"batch_dashboard: cannot read manifest: {exc}", file=sys.stderr)
            return 2

    gen = BatchDashboardGenerator(output_root, manifest=explicit_manifest)
    dashboard_dir = (
        _resolve_relative_to_staging(args.dashboard_dir)
        if args.dashboard_dir is not None
        else None
    )
    written = gen.write_all(dashboard_dir)

    for path in written.values():
        print(str(path.resolve()))

    if not args.quiet:
        dest = (
            dashboard_dir.resolve()
            if dashboard_dir
            else (output_root / "dashboard").resolve()
        )
        print(
            f"batch_dashboard: wrote {len(written)} artifacts under {dest}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
