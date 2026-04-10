#!/usr/bin/env python3
"""Inject manuscript variables from METRICS.yaml into markdown files.

Usage:
    python tools/inject_manuscript_vars.py <input.md> [--dry-run] [--output out.md]
    python tools/inject_manuscript_vars.py manuscript/ --all [--dry-run]
"""
import argparse
import sys
from pathlib import Path

import yaml

# Allow running from repo root or from tools/ directory
_TOOLS_DIR = Path(__file__).parent
_REPO_ROOT = _TOOLS_DIR.parent
sys.path.insert(0, str(_TOOLS_DIR))

from manuscript_vars import MANUSCRIPT_VARS

METRICS_PATH = _REPO_ROOT / "cogant" / "evaluation" / "METRICS.yaml"


def load_metrics() -> dict:
    with open(METRICS_PATH) as f:
        return yaml.safe_load(f)


def resolve_path(data: dict, dotpath: str):
    parts = dotpath.split(".")
    for p in parts:
        if isinstance(data, dict):
            data = data.get(p)
        else:
            return None
    return data


def inject(text: str, metrics: dict, dry_run: bool = False) -> tuple[str, list[str]]:
    """Substitute {{VAR}} patterns. Returns (new_text, list_of_substitutions)."""
    substitutions = []
    for var, path in MANUSCRIPT_VARS.items():
        value = resolve_path(metrics, path)
        if value is None:
            continue
        if isinstance(value, float):
            formatted = f"{value:.4f}" if "epsilon" in path else f"{value:.1f}"
        else:
            formatted = str(value)
        if var in text:
            substitutions.append(f"  {var} → {formatted} (from {path})")
            if not dry_run:
                text = text.replace(var, formatted)
    return text, substitutions


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
        val_str = str(value) if value is not None else "<not found>"
        print(f"{var:<{col_var}}  {path:<{col_path}}  {val_str}")


def main():
    parser = argparse.ArgumentParser(
        description="Inject METRICS.yaml values into manuscript {{VAR}} placeholders."
    )
    parser.add_argument("input", nargs="?", help="Input markdown file or directory (omit when using --report)")
    parser.add_argument("--dry-run", action="store_true", help="Show substitutions without modifying files")
    parser.add_argument("--output", help="Output file (default: in-place)")
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
    else:
        files = [input_path]

    total_subs = 0
    for f in files:
        text = f.read_text(encoding="utf-8")
        new_text, subs = inject(text, metrics, dry_run=args.dry_run)
        if subs:
            print(f"\n{f}:")
            for s in subs:
                print(s)
            total_subs += len(subs)
        if not args.dry_run:
            out = Path(args.output) if args.output else f
            out.write_text(new_text, encoding="utf-8")

    if total_subs == 0:
        print("No {{VAR}} placeholders found in the specified files.")
    elif args.dry_run:
        print(f"\n[DRY RUN — {total_subs} substitution(s) would be made; no files modified]")
    else:
        print(f"\n{total_subs} substitution(s) applied.")


if __name__ == "__main__":
    main()
