#!/usr/bin/env bash
# Run COGANT batch pipeline (see README.md "Batch outputs").
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# Staging root: directory containing run_all.py
if [[ -f "$HERE/run_all.py" ]]; then
  ROOT="$HERE"
elif [[ -f "$HERE/../run_all.py" ]]; then
  ROOT="$(cd "$HERE/.." && pwd)"
else
  echo "error: cannot find run_all.py (run from staging root or inner cogant/)" >&2
  exit 2
fi
PKG="$ROOT/cogant"
if [[ ! -f "$PKG/pyproject.toml" ]]; then
  echo "error: expected package at $PKG" >&2
  exit 2
fi
cd "$PKG"
exec uv run python "$ROOT/run_all.py" "$@"
