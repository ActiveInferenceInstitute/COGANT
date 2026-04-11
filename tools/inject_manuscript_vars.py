#!/usr/bin/env python3
"""Inject manuscript variables from METRICS.yaml into markdown files.

Usage:
    python tools/inject_manuscript_vars.py <input.md> [--dry-run] [--output out.md]
    python tools/inject_manuscript_vars.py manuscript/ --all [--dry-run]
    python tools/inject_manuscript_vars.py manuscript/ --all --output-dir staging/
"""
import argparse
import difflib
import sys
from pathlib import Path

import yaml

# Allow running from repo root or from tools/ directory
_TOOLS_DIR = Path(__file__).parent
_REPO_ROOT = _TOOLS_DIR.parent
sys.path.insert(0, str(_TOOLS_DIR))

from manuscript_vars import (
    MANUSCRIPT_VARS,
    format_value_for_path,
    resolve_path,
    substitute_text,
)

METRICS_PATH = _REPO_ROOT / "cogant" / "evaluation" / "METRICS.yaml"


def load_metrics() -> dict:
    with open(METRICS_PATH) as f:
        return yaml.safe_load(f)


def inject(text: str, metrics: dict, dry_run: bool = False) -> tuple[str, list[str]]:
    """Substitute {{VAR}} patterns. Returns (new_text, list_of_substitutions)."""
    new_text, substitutions = substitute_text(text, metrics)
    if dry_run:
        return text, substitutions
    return new_text, substitutions


def make_unified_diff(original: str, updated: str, label: str) -> str:
    """Produce a unified diff between *original* and *updated* text.

    Returns an empty string if the two texts are identical, so callers can
    cheaply detect "no change" without parsing the diff output.
    """
    if original == updated:
        return ""
    diff_lines = difflib.unified_diff(
        original.splitlines(keepends=True),
        updated.splitlines(keepends=True),
        fromfile=f"a/{label}",
        tofile=f"b/{label}",
        n=3,
    )
    return "".join(diff_lines)


def report(metrics: dict) -> None:
    """Print a compact table of all registered vars and their current METRICS.yaml values."""
    col_var = max(len(v) for v in MANUSCRIPT_VARS) + 2
    col_path = max(len(p) for p in MANUSCRIPT_VARS.values()) + 2
    header_var = "VAR"
    header_path = "METRICS_PATH"
    header_val = "CURRENT_VALUE"
    print(f"{header_var:<{col_var}}  {header_path:<{col_path}}  {header_val}")
    print(f"{'-' * col_var}  {'-' * col_path}  {'-' * 20}")
    for var, path in sorted(MANUSCRIPT_VARS.items()):
        value = resolve_path(metrics, path)
        if value is None:
            val_str = "<not found>"
        else:
            val_str = format_value_for_path(path, value)
        print(f"{var:<{col_var}}  {path:<{col_path}}  {val_str}")


def main():
    parser = argparse.ArgumentParser(
        description="Inject METRICS.yaml values into manuscript {{VAR}} placeholders."
    )
    parser.add_argument("input", nargs="?", help="Input markdown file or directory (omit when using --report)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show a unified diff of what would change, without writing any file.",
    )
    parser.add_argument(
        "--output",
        help="Output file for single-file mode (default: in-place). Ignored in --all / directory mode.",
    )
    parser.add_argument(
        "--output-dir",
        help=(
            "Staging directory: write substituted files here instead of editing "
            "in-place. Preserves originals. Directory structure is mirrored "
            "relative to the input path."
        ),
    )
    parser.add_argument("--all", dest="all_files", action="store_true", help="Process all .md files in directory")
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print a compact table of all registered vars and their current METRICS.yaml values, then exit.",
    )
    args = parser.parse_args()

    if not METRICS_PATH.exists():
        print(f"ERROR: METRICS.yaml not found at {METRICS_PATH}", file=sys.stderr)
        print("Run the metrics-agent first, or create METRICS.yaml manually.", file=sys.stderr)
        sys.exit(1)

    metrics = load_metrics()

    if args.report:
        report(metrics)
        return

    if not args.input:
        parser.error("the following arguments are required: input (unless --report is used)")

    input_path = Path(args.input)

    if args.all_files or input_path.is_dir():
        files = sorted(input_path.glob("**/*.md"))
        # In directory mode, compute a root for output-dir mirroring
        mirror_root = input_path if input_path.is_dir() else input_path.parent
    else:
        files = [input_path]
        mirror_root = input_path.parent

    if args.output and args.output_dir:
        parser.error("--output and --output-dir are mutually exclusive")
    if args.output and (args.all_files or input_path.is_dir()):
        parser.error("--output only applies to single-file mode; use --output-dir for directories")

    output_dir: Path | None = Path(args.output_dir) if args.output_dir else None
    if output_dir is not None and not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    total_subs = 0
    files_changed = 0
    for f in files:
        text = f.read_text(encoding="utf-8")
        new_text, subs = inject(text, metrics, dry_run=False)
        if subs:
            total_subs += len(subs)
            files_changed += 1

        if args.dry_run:
            # Show a unified diff instead of listing substitutions.
            try:
                label = str(f.relative_to(_REPO_ROOT))
            except ValueError:
                label = str(f)
            diff = make_unified_diff(text, new_text, label)
            if diff:
                print(diff, end="")
            continue

        # Determine output target
        if output_dir is not None:
            try:
                rel = f.relative_to(mirror_root)
            except ValueError:
                rel = Path(f.name)
            out = output_dir / rel
            out.parent.mkdir(parents=True, exist_ok=True)
        elif args.output:
            out = Path(args.output)
        else:
            out = f

        # Only write when content actually changed (or explicit --output / --output-dir)
        if new_text != text or args.output or output_dir is not None:
            out.write_text(new_text, encoding="utf-8")

        if subs:
            print(f"\n{f}:")
            for s in subs:
                print(s)

    if total_subs == 0:
        print("No {{VAR}} placeholders found in the specified files.")
    elif args.dry_run:
        print(
            f"\n[DRY RUN — {total_subs} substitution(s) across {files_changed} file(s); "
            "no files modified]"
        )
    else:
        target = f"staging dir {output_dir}" if output_dir is not None else "in-place"
        print(f"\n{total_subs} substitution(s) applied ({target}).")


if __name__ == "__main__":
    main()
