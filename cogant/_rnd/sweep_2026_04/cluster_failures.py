#!/usr/bin/env python3
"""Cluster failures by root cause."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "_rnd" / "sweep_2026_04" / "block_results.json"

data = json.loads(RESULTS.read_text())

clusters: dict[str, list[dict]] = defaultdict(list)
for r in data["results"]:
    if r["ok"]:
        continue
    err = r["stderr_tail"]
    # Extract final error line
    lines = [ln for ln in err.strip().split("\n") if ln.strip()]
    final = lines[-1] if lines else "UNKNOWN"
    # Normalize common patterns
    key = final
    if "ModuleNotFoundError" in final:
        m = re.search(r"No module named ['\"]([^'\"]+)['\"]", final)
        key = f"ModuleNotFoundError: {m.group(1) if m else '?'}"
    elif "ImportError" in final:
        m = re.search(r"cannot import name ['\"]([^'\"]+)['\"] from ['\"]([^'\"]+)['\"]", final)
        if m:
            key = f"ImportError: {m.group(1)} from {m.group(2)}"
    elif "AttributeError" in final:
        m = re.search(r"module ['\"]([^'\"]+)['\"] has no attribute ['\"]([^'\"]+)['\"]", final)
        if m:
            key = f"AttributeError: {m.group(1)}.{m.group(2)}"
        else:
            m = re.search(r"'([^']+)' object has no attribute '([^']+)'", final)
            if m:
                key = f"AttributeError: {m.group(1)}.{m.group(2)}"
    elif "TypeError" in final:
        key = f"TypeError: {final.split('TypeError:', 1)[-1].strip()[:80]}"
    elif "NameError" in final:
        m = re.search(r"name ['\"]([^'\"]+)['\"] is not defined", final)
        key = f"NameError: {m.group(1) if m else '?'}"
    elif "FileNotFoundError" in final:
        key = "FileNotFoundError"
    elif "SyntaxError" in final:
        key = "SyntaxError"
    clusters[key].append(r)

for key, items in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
    print(f"\n== {key} ({len(items)}) ==")
    for r in items:
        print(f"  - {r['file']}#{r['index']}")
