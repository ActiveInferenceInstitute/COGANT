#!/usr/bin/env python3
"""Inject manuscript variables from METRICS.yaml into markdown files.

This CLI walks a Markdown file or directory, replaces every registered
``{{VAR}}`` placeholder with the corresponding value from
``cogant/evaluation/METRICS.yaml``, and writes the result either in place,
into a staging directory, or to a single named output file.

Exit codes
----------
* ``0`` — success (all placeholders resolved or ``--report`` completed).
* ``1`` — METRICS.yaml missing, parse error, usage error, or (with
  ``--strict``) at least one unresolved ``{{VAR}}`` token remained in the
  output.

Invocation is directory-independent: paths are resolved relative to
``__file__``, so the tool works identically from the repo root, from
``tools/``, or via ``uv run``.

Usage:
    python tools/inject_manuscript_vars.py <input.md> [--dry-run] [--output out.md]
    python tools/inject_manuscript_vars.py manuscript/ --all [--dry-run]
    python tools/inject_manuscript_vars.py manuscript/ --all --output-dir staging/
    python tools/inject_manuscript_vars.py manuscript/ --all --strict   # CI gate
    python tools/inject_manuscript_vars.py --report                     # show resolved table
"""

import argparse
import difflib
import sys
from pathlib import Path

import yaml

# Allow running from repo root or from tools/ directory. All paths below are
# anchored on ``__file__``; we never rely on the caller's cwd.
_TOOLS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TOOLS_DIR.parent
sys.path.insert(0, str(_TOOLS_DIR))

from manuscript_vars import (  # noqa: E402
    MANUSCRIPT_VARS,
    find_unresolved_placeholders,
    format_value_for_path,
    resolve_path,
    substitute_text,
)

METRICS_PATH = _REPO_ROOT / "cogant" / "evaluation" / "METRICS.yaml"


def load_metrics() -> dict:
    """Load METRICS.yaml as a plain ``dict``; raise with context on failure."""
    try:
        with open(METRICS_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except OSError as exc:
        raise SystemExit(f"ERROR: could not read {METRICS_PATH}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise SystemExit(f"ERROR: could not parse {METRICS_PATH}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(
            f"ERROR: {METRICS_PATH} did not parse to a mapping (got {type(data).__name__})"
        )
    return data


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
    parser.add_argument(
        "input", nargs="?", help="Input markdown file or directory (omit when using --report)"
    )
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
    parser.add_argument(
        "--all", dest="all_files", action="store_true", help="Process all .md files in directory"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print a compact table of all registered vars and their current METRICS.yaml values, then exit.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Exit non-zero if any {{PLACEHOLDER}} remains unresolved after "
            "substitution (unknown token, or METRICS.yaml missing that entry). "
            "Use this in CI to guard against silent drift."
        ),
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
    unresolved_by_file: dict[str, list[str]] = {}
    for f in files:
        text = f.read_text(encoding="utf-8")
        new_text, subs = inject(text, metrics, dry_run=False)
        if subs:
            total_subs += len(subs)
            files_changed += 1

        remaining = find_unresolved_placeholders(new_text)
        if remaining:
            try:
                label = str(f.relative_to(_REPO_ROOT))
            except ValueError:
                label = str(f)
            unresolved_by_file[label] = remaining

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

    if unresolved_by_file:
        header = "\nUnresolved {{PLACEHOLDER}} tokens remaining after substitution:"
        print(header, file=sys.stderr)
        for label, tokens in sorted(unresolved_by_file.items()):
            print(f"  {label}:", file=sys.stderr)
            for tok in tokens:
                print(f"    - {tok}", file=sys.stderr)
        if args.strict:
            print(
                "ERROR (--strict): unresolved placeholders present; "
                "register them in tools/manuscript_vars.py::MANUSCRIPT_VARS "
                "or add the missing entry to METRICS.yaml.",
                file=sys.stderr,
            )
            sys.exit(1)


if __name__ == "__main__":
    main()
