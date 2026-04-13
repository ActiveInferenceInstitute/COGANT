#!/usr/bin/env python3
"""Execute every runnable Python block from docs and record pass/fail."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "_rnd" / "sweep_2026_04" / "block_catalog.json"
RESULTS = ROOT / "_rnd" / "sweep_2026_04" / "block_results.json"

TIMEOUT = 60


def main() -> None:
    data = json.loads(CATALOG.read_text())
    results = []
    runnable = [b for b in data["blocks"] if b["runnable"]]
    print(f"running {len(runnable)} runnable blocks", flush=True)
    for n, entry in enumerate(runnable, 1):
        block_path = ROOT / entry["block_file"]
        cmd = ["uv", "run", "--quiet", "python", str(block_path)]
        try:
            proc = subprocess.run(
                cmd,
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
            )
            ok = proc.returncode == 0
            stderr = proc.stderr
            stdout = proc.stdout
        except subprocess.TimeoutExpired:
            ok = False
            stderr = "TIMEOUT"
            stdout = ""
        result = {
            "file": entry["file"],
            "index": entry["index"],
            "block_file": entry["block_file"],
            "ok": ok,
            "stdout_tail": (stdout or "")[-400:],
            "stderr_tail": (stderr or "")[-800:],
        }
        results.append(result)
        status = "PASS" if ok else "FAIL"
        print(f"[{n}/{len(runnable)}] {status} {entry['file']}#{entry['index']}", flush=True)
    summary = {
        "total": len(results),
        "passed": sum(1 for r in results if r["ok"]),
        "failed": sum(1 for r in results if not r["ok"]),
        "results": results,
    }
    RESULTS.write_text(json.dumps(summary, indent=2))
    print(f"passed={summary['passed']} failed={summary['failed']}")


if __name__ == "__main__":
    main()
