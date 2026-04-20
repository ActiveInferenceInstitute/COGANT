#!/usr/bin/env python3
"""Run COGANT against configured example repos and emit all practical CLI outputs.

Each target writes under ``output_root/<id>/`` (bundle, ``gnn_package/``, scans, site,
PNGs, validation). Local targets use ``path``; remote targets use ``git_url`` (clone to
``<id>/_git_source/``). See staging README.md (Batch outputs)."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STAGING_ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = STAGING_ROOT / "run_all.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "package_root": "cogant",
    "output_root": "cogant/output",
    "remote": {
        "shallow_clone": True,
        "refresh": False,
    },
    "targets": [
        {
            "id": "calculator",
            "path": "examples/control_positive/calculator",
            "explain": None,
        },
        {
            "id": "event_pipeline",
            "path": "examples/control_positive/event_pipeline",
            "explain": None,
        },
        {
            "id": "flask_mini",
            "path": "examples/control_positive/flask_mini",
            "explain": None,
        },
        {
            "id": "remote_itsdangerous",
            "path": None,
            "git_url": "https://github.com/pallets/itsdangerous.git",
            "git_ref": None,
            "explain": None,
        },
        {
            "id": "remote_markupsafe",
            "path": None,
            "git_url": "https://github.com/pallets/markupsafe.git",
            "git_ref": None,
            "explain": None,
        },
    ],
    "steps": {
        "doctor": False,
        "translate": True,
        "layout_output": True,
        "no_dynamic": True,
        "scan_json": True,
        "graph_stdout": True,
        "export_gnn": True,
        "export_gnn_format": "all",
        "render_site": True,
        "viz_png": True,
        "validate_run_dir": True,
        "validate_no_upstream_gnn": False,
        "roundtrip": True,
        # The four steps below bypass the v0.5.0 CLI stubs and call the real
        # Python APIs via tools/batch_api.py. Flip to False to skip.
        "analyze_graph": True,
        "analyze_static": True,
        "export_multi": True,
        "export_multi_formats": "json,graphml",
        "visualize_diagrams": True,
        "visualize_format": "mermaid",
    },
    "manuscript": {
        "enabled": False,
        "regenerate_metrics": False,
        "strict": False,
    },
}


def load_config(path: Path | None) -> dict[str, Any]:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    p = path or (DEFAULT_CONFIG_PATH if DEFAULT_CONFIG_PATH.is_file() else None)
    if p is not None and p.is_file():
        data = json.loads(p.read_text(encoding="utf-8"))
        for k, v in data.items():
            if k == "steps" and isinstance(v, dict):
                cfg["steps"].update(v)
            elif k == "manuscript" and isinstance(v, dict):
                cfg["manuscript"].update(v)
            elif k == "remote" and isinstance(v, dict):
                cfg["remote"].update(v)
            else:
                cfg[k] = v
    return cfg


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def report(msg: str, *, log_fp: Any | None = None) -> None:
    """Human-oriented line on stderr (and log file when duplicated)."""
    line = f"[run_all {_ts()}] {msg}"
    print(line, file=sys.stderr, flush=True)
    if log_fp is not None and log_fp is not sys.stdout and log_fp is not sys.stderr:
        print(line, file=log_fp, flush=True)


def run_cmd(
    argv: list[str],
    *,
    cwd: Path,
    dry_run: bool,
    log_fp: Any,
    step: str = "cmd",
) -> int:
    print(f"+ {' '.join(argv)}", file=log_fp, flush=True)
    if dry_run:
        report(f"  [{step}] (dry-run)", log_fp=log_fp)
        return 0
    t0 = time.monotonic()
    code = subprocess.call(argv, cwd=str(cwd), env=os.environ.copy())
    dt = time.monotonic() - t0
    status = "ok" if code == 0 else f"FAIL exit={code}"
    report(f"  [{step}] {status} wall_time={dt:.2f}s", log_fp=log_fp)
    return code


def run_cmd_capture(
    argv: list[str],
    *,
    cwd: Path,
    dry_run: bool,
    out_path: Path,
    log_fp: Any,
    step: str = "capture",
) -> int:
    print(f"+ {' '.join(argv)} > {out_path}", file=log_fp, flush=True)
    if dry_run:
        report(f"  [{step}] → {out_path.name} (dry-run)", log_fp=log_fp)
        return 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    proc = subprocess.run(
        argv,
        cwd=str(cwd),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )
    dt = time.monotonic() - t0
    combined = (proc.stdout or "") + (proc.stderr or "")
    out_path.write_text(combined, encoding="utf-8")
    status = "ok" if proc.returncode == 0 else f"FAIL exit={proc.returncode}"
    report(
        f"  [{step}] {status} wall_time={dt:.2f}s wrote {out_path.name} ({len(combined)} bytes)",
        log_fp=log_fp,
    )
    if proc.returncode != 0 and combined.strip():
        tail = combined.strip()[-800:]
        report(f"  [{step}] output tail:\n{tail}", log_fp=log_fp)
    return proc.returncode


def ensure_git_clone(
    *,
    git_url: str,
    git_ref: str | None,
    dest: Path,
    shallow: bool,
    refresh: bool,
    dry_run: bool,
    log_fp: Any,
) -> int:
    if dry_run:
        parts = ["git", "clone"]
        if shallow:
            parts.extend(["--depth", "1"])
        if git_ref:
            parts.extend(["--branch", git_ref])
        parts.extend([git_url, str(dest)])
        print(f"+ {' '.join(parts)}", file=log_fp, flush=True)
        report("  [git_clone] (dry-run)", log_fp=log_fp)
        return 0

    if refresh and dest.exists():
        shutil.rmtree(dest)
    if dest.exists() and (dest / ".git").is_dir():
        report(f"  [git_clone] skip (existing clone) {dest}", log_fp=log_fp)
        return 0

    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone"]
    if shallow:
        cmd.extend(["--depth", "1"])
    if git_ref:
        cmd.extend(["--branch", git_ref])
    cmd.extend([git_url, str(dest)])
    print(f"+ {' '.join(cmd)}", file=log_fp, flush=True)
    t0 = time.monotonic()
    proc = subprocess.run(cmd, env=os.environ.copy(), capture_output=True, text=True)
    dt = time.monotonic() - t0
    if proc.returncode != 0:
        report(
            f"  [git_clone] FAIL exit={proc.returncode} wall_time={dt:.2f}s",
            log_fp=log_fp,
        )
        print(proc.stderr or proc.stdout, file=sys.stderr)
    else:
        report(f"  [git_clone] ok wall_time={dt:.2f}s → {dest}", log_fp=log_fp)
    return proc.returncode


def _read_bundle(run_dir: Path) -> dict[str, Any] | None:
    """Return parsed bundle.json for a run dir, preferring the --layout-output
    path. Silent on parse errors — the caller just skips the row."""
    for candidate in (run_dir / "data" / "bundle.json", run_dir / "bundle.json"):
        if candidate.is_file():
            try:
                return json.loads(candidate.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return None
    return None


def _write_cross_target_summary(
    output_root: Path,
    manifest: dict[str, Any],
    *,
    log_fp: Any,
) -> None:
    """Emit ``summary.json`` + ``summary.md`` aggregating per-target results."""
    rows: list[dict[str, Any]] = []
    for t in manifest.get("targets", []):
        run_dir = Path(t["run_dir"])
        bundle = _read_bundle(run_dir)
        row: dict[str, Any] = {
            "id": t.get("id"),
            "kind": "remote" if t.get("git_url") else "local",
            "source": t.get("git_url") or t.get("path"),
            "run_dir": str(run_dir),
        }
        if bundle is not None:
            sr = bundle.get("stage_results", {}) or {}
            gnn_val = (sr.get("validate", {}) or {}).get("gnn_validation", {}) or {}
            graph_stage = sr.get("graph", {}) or {}
            translate_stage = sr.get("translate", {}) or {}
            row.update({
                "score": gnn_val.get("score"),
                "valid": gnn_val.get("valid"),
                "node_count": graph_stage.get("node_count") or graph_stage.get("nodes"),
                "edge_count": graph_stage.get("edge_count") or graph_stage.get("edges"),
                "mapping_count": translate_stage.get("mapping_count"),
                "gnn_package_files": len(list((run_dir / "gnn_package").glob("*"))) if (run_dir / "gnn_package").is_dir() else 0,
                "has_site": (run_dir / "site" / "index.html").is_file(),
                "has_reverse": any((run_dir / "roundtrip" / "reverse").glob("*")) if (run_dir / "roundtrip" / "reverse").is_dir() else False,
                "has_analysis": (run_dir / "analysis").is_dir() and any((run_dir / "analysis").iterdir()),
                "has_exports": (run_dir / "exports").is_dir() and any((run_dir / "exports").iterdir()),
                "has_diagrams": (run_dir / "diagrams").is_dir() and any((run_dir / "diagrams").iterdir()),
            })
        else:
            row["score"] = None
            row["valid"] = None
        rows.append(row)

    summary_json = output_root / "summary.json"
    summary_json.write_text(
        json.dumps({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "target_count": len(rows),
            "total_wall_time_s": manifest.get("summary", {}).get("total_wall_time_s"),
            "failed_steps": manifest.get("summary", {}).get("failed_steps", []),
            "rows": rows,
        }, indent=2),
        encoding="utf-8",
    )

    lines: list[str] = []
    lines.append("# COGANT batch run summary")
    lines.append("")
    lines.append(f"- Targets: **{len(rows)}**")
    lines.append(f"- Total wall time: **{manifest.get('summary', {}).get('total_wall_time_s')}s**")
    lines.append(f"- Failed steps: **{len(manifest.get('summary', {}).get('failed_steps', []))}**")
    lines.append("")
    lines.append("| id | kind | score | nodes | edges | mappings | gnn_pkg | site | reverse | analysis | exports | diagrams |")
    lines.append("|---|---|---:|---:|---:|---:|---:|:---:|:---:|:---:|:---:|:---:|")
    for r in rows:
        chk = lambda b: "✓" if b else "-"  # noqa: E731
        lines.append(
            "| {id} | {kind} | {score} | {nodes} | {edges} | {map} | {pkg} | {site} | {rev} | {an} | {ex} | {di} |".format(
                id=r.get("id"),
                kind=r.get("kind"),
                score=r.get("score") if r.get("score") is not None else "-",
                nodes=r.get("node_count") or "-",
                edges=r.get("edge_count") or "-",
                map=r.get("mapping_count") or "-",
                pkg=r.get("gnn_package_files") or 0,
                site=chk(r.get("has_site")),
                rev=chk(r.get("has_reverse")),
                an=chk(r.get("has_analysis")),
                ex=chk(r.get("has_exports")),
                di=chk(r.get("has_diagrams")),
            )
        )
    summary_md = output_root / "summary.md"
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report(f"wrote cross-target summary: {summary_json.name}, {summary_md.name}", log_fp=log_fp)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run COGANT pipeline + GNN outputs.")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--log", type=Path, default=None)
    parser.add_argument("--print-default-config", action="store_true")
    parser.add_argument(
        "--targets",
        type=str,
        default=None,
        help="Comma-separated target ids to run (subset of the config). Default: all.",
    )
    args = parser.parse_args()

    if args.print_default_config:
        print(json.dumps(DEFAULT_CONFIG, indent=2))
        return 0

    cfg = load_config(args.config)
    package_root = (STAGING_ROOT / Path(cfg["package_root"])).resolve()
    if not (package_root / "pyproject.toml").is_file():
        print(f"error: package_root {package_root} has no pyproject.toml", file=sys.stderr)
        return 2

    output_root = (STAGING_ROOT / cfg["output_root"]).resolve()
    steps = cfg["steps"]
    manuscript = cfg.get("manuscript") or {}
    remote_cfg = cfg.get("remote") or {}

    if args.targets:
        wanted = {s.strip() for s in args.targets.split(",") if s.strip()}
        cfg["targets"] = [t for t in cfg["targets"] if t.get("id") in wanted]
        if not cfg["targets"]:
            print(
                f"error: --targets {sorted(wanted)!r} matched nothing in config",
                file=sys.stderr,
            )
            return 2

    log_fp: Any = open(args.log, "a", encoding="utf-8") if args.log else sys.stdout
    try:
        manifest: dict[str, Any] = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "staging_root": str(STAGING_ROOT),
            "package_root": str(package_root),
            "output_root": str(output_root),
            "dry_run": args.dry_run,
            "targets": [],
        }
        failures: list[str] = []
        batch_start = time.monotonic()
        n_targets = len(cfg["targets"])

        def check(code: int, label: str) -> int:
            if code != 0:
                report(f"warning: {label} exited {code}", log_fp=log_fp)
                failures.append(label)
                if args.fail_fast:
                    return code
            return 0

        if manuscript.get("enabled"):
            script = STAGING_ROOT / "scripts" / "z_generate_manuscript_variables.py"
            if not script.is_file():
                print(f"error: missing {script}", file=sys.stderr)
                return 2
            margv = [sys.executable, str(script)]
            if manuscript.get("regenerate_metrics"):
                margv.append("--regenerate-metrics")
            if manuscript.get("strict"):
                margv.append("--strict")
            template_root = STAGING_ROOT.parent.parent
            code = run_cmd(margv, cwd=template_root, dry_run=args.dry_run, log_fp=log_fp, step="manuscript_variables")
            if check(code, "manuscript_variables"):
                return code

        if steps.get("doctor"):
            code = run_cmd(
                ["uv", "run", "cogant", "doctor"],
                cwd=package_root,
                dry_run=args.dry_run,
                log_fp=log_fp,
                step="doctor",
            )
            if check(code, "doctor"):
                return code

        output_root.mkdir(parents=True, exist_ok=True)

        for ti, t in enumerate(cfg["targets"], start=1):
            tid = t["id"]
            run_dir = (output_root / tid).resolve()
            git_url = t.get("git_url")
            rel = t.get("path")

            entry: dict[str, Any] = {
                "id": tid,
                "run_dir": str(run_dir),
                "commands": [],
            }

            if git_url:
                entry["git_url"] = git_url
                entry["git_ref"] = t.get("git_ref")
                src = run_dir / "_git_source"
                entry["source_dir"] = str(src)
                target_path = src
            elif rel:
                entry["path"] = str(rel)
                target_path = (package_root / rel).resolve()
                entry["absolute_target"] = str(target_path)
            else:
                print(
                    f"error: target {tid!r} needs either path or git_url",
                    file=sys.stderr,
                )
                if args.fail_fast:
                    return 2
                continue

            manifest["targets"].append(entry)

            kind = "remote" if git_url else "local"
            report(
                f"=== target {ti}/{n_targets} id={tid} kind={kind} run_dir={run_dir}",
                log_fp=log_fp,
            )

            if git_url:
                code = ensure_git_clone(
                    git_url=str(git_url),
                    git_ref=t.get("git_ref"),
                    dest=src,
                    shallow=bool(remote_cfg.get("shallow_clone", True)),
                    refresh=bool(remote_cfg.get("refresh", False)),
                    dry_run=args.dry_run,
                    log_fp=log_fp,
                )
                if check(code, f"git_clone:{tid}"):
                    return code

            if not args.dry_run and not target_path.exists():
                print(f"error: missing target path {target_path}", file=sys.stderr)
                if args.fail_fast:
                    return 2
                continue

            # With --layout-output the bundle is relocated to <run_dir>/data/bundle.json.
            # The closure resolves whichever path exists at call time so downstream
            # steps fire reliably regardless of layout choice.
            _run_dir = run_dir

            def _bundle_path() -> Path:
                top = _run_dir / "bundle.json"
                laid = _run_dir / "data" / "bundle.json"
                if top.is_file():
                    return top
                if laid.is_file():
                    return laid
                return laid if steps.get("layout_output") else top

            bundle_json = _bundle_path()

            if steps.get("translate", True):
                tr = [
                    "uv",
                    "run",
                    "cogant",
                    "translate",
                    str(target_path),
                    "--output",
                    str(run_dir),
                ]
                if steps.get("layout_output"):
                    tr.append("--layout-output")
                if steps.get("no_dynamic"):
                    tr.append("--no-dynamic")
                code = run_cmd(tr, cwd=package_root, dry_run=args.dry_run, log_fp=log_fp, step=f"translate:{tid}")
                entry["commands"].append({"cmd": tr, "exit": code})
                if check(code, f"translate:{tid}"):
                    return code
                # Re-resolve after translate so downstream gates see the real path.
                bundle_json = _bundle_path()
                if not args.dry_run and not bundle_json.is_file():
                    print(
                        f"warning: no bundle at {bundle_json} after translate",
                        file=sys.stderr,
                    )

            if steps.get("scan_json"):
                code = run_cmd_capture(
                    ["uv", "run", "cogant", "scan", str(target_path), "-f", "json"],
                    cwd=package_root,
                    dry_run=args.dry_run,
                    out_path=run_dir / "scan.json",
                    log_fp=log_fp,
                    step=f"scan:{tid}",
                )
                entry["commands"].append({"cmd": "scan -f json", "exit": code})
                if check(code, f"scan:{tid}"):
                    return code

            if steps.get("graph_stdout"):
                code = run_cmd_capture(
                    ["uv", "run", "cogant", "graph", str(target_path)],
                    cwd=package_root,
                    dry_run=args.dry_run,
                    out_path=run_dir / "graph.txt",
                    log_fp=log_fp,
                    step=f"graph:{tid}",
                )
                entry["commands"].append({"cmd": "graph", "exit": code})
                if check(code, f"graph:{tid}"):
                    return code

            if steps.get("export_gnn") and (args.dry_run or bundle_json.is_file()):
                eg_dir = run_dir / "export_gnn"
                fmt = str(steps.get("export_gnn_format") or "all")
                ex = [
                    "uv",
                    "run",
                    "cogant",
                    "export-gnn",
                    str(bundle_json),
                    "--output",
                    str(eg_dir),
                    "--format",
                    fmt,
                ]
                code = run_cmd(ex, cwd=package_root, dry_run=args.dry_run, log_fp=log_fp, step=f"export_gnn:{tid}")
                entry["commands"].append({"cmd": ex, "exit": code})
                if check(code, f"export-gnn:{tid}"):
                    return code

            if steps.get("render_site") and (args.dry_run or bundle_json.is_file()):
                site_dir = run_dir / "site"
                rv = [
                    "uv",
                    "run",
                    "cogant",
                    "render",
                    str(bundle_json),
                    "--output",
                    str(site_dir),
                ]
                code = run_cmd(rv, cwd=package_root, dry_run=args.dry_run, log_fp=log_fp, step=f"render:{tid}")
                entry["commands"].append({"cmd": rv, "exit": code})
                if check(code, f"render:{tid}"):
                    return code

            if steps.get("viz_png") and (args.dry_run or run_dir.is_dir()):
                vz = ["uv", "run", "cogant", "viz", str(run_dir)]
                code = run_cmd(vz, cwd=package_root, dry_run=args.dry_run, log_fp=log_fp, step=f"viz:{tid}")
                entry["commands"].append({"cmd": vz, "exit": code})
                if check(code, f"viz:{tid}"):
                    return code

            if steps.get("validate_run_dir") and (args.dry_run or run_dir.is_dir()):
                val = ["uv", "run", "cogant", "validate", str(run_dir)]
                if steps.get("validate_no_upstream_gnn"):
                    val.append("--no-upstream-gnn")
                code = run_cmd_capture(
                    val,
                    cwd=package_root,
                    dry_run=args.dry_run,
                    out_path=run_dir / "validate.txt",
                    log_fp=log_fp,
                    step=f"validate:{tid}",
                )
                entry["commands"].append({"cmd": val, "exit": code})
                if check(code, f"validate:{tid}"):
                    return code

            explain_node = t.get("explain")
            if explain_node and isinstance(explain_node, str) and explain_node.strip():
                ex = [
                    "uv",
                    "run",
                    "cogant",
                    "explain",
                    str(target_path),
                    explain_node.strip(),
                    "-f",
                    "json",
                ]
                code = run_cmd_capture(
                    ex,
                    cwd=package_root,
                    dry_run=args.dry_run,
                    out_path=run_dir / "explain.json",
                    log_fp=log_fp,
                    step=f"explain:{tid}",
                )
                entry["commands"].append({"cmd": ex, "exit": code})
                if check(code, f"explain:{tid}"):
                    return code

            if steps.get("roundtrip") and (args.dry_run or target_path.exists()):
                rt_dir = run_dir / "roundtrip"
                if not args.dry_run:
                    rt_dir.mkdir(parents=True, exist_ok=True)
                rt = [
                    "uv",
                    "run",
                    "cogant",
                    "roundtrip",
                    str(target_path),
                    "--output",
                    str(rt_dir),
                    "--keep-tmp",
                ]
                code = run_cmd(
                    rt,
                    cwd=package_root,
                    dry_run=args.dry_run,
                    log_fp=log_fp,
                    step=f"roundtrip:{tid}",
                )
                entry["commands"].append({"cmd": rt, "exit": code})
                if check(code, f"roundtrip:{tid}"):
                    return code

            batch_api = STAGING_ROOT / "tools" / "batch_api.py"

            if steps.get("analyze_graph") and (args.dry_run or target_path.exists()):
                ag = [
                    "uv", "run", "python", str(batch_api), "graph-analysis",
                    "--run-dir", str(run_dir),
                    "--target", str(target_path),
                ]
                code = run_cmd(ag, cwd=package_root, dry_run=args.dry_run, log_fp=log_fp, step=f"analyze_graph:{tid}")
                entry["commands"].append({"cmd": ag, "exit": code})
                if check(code, f"analyze_graph:{tid}"):
                    return code

            if steps.get("analyze_static") and (args.dry_run or target_path.exists()):
                asta = [
                    "uv", "run", "python", str(batch_api), "static-analysis",
                    "--run-dir", str(run_dir),
                    "--target", str(target_path),
                ]
                code = run_cmd(asta, cwd=package_root, dry_run=args.dry_run, log_fp=log_fp, step=f"analyze_static:{tid}")
                entry["commands"].append({"cmd": asta, "exit": code})
                if check(code, f"analyze_static:{tid}"):
                    return code

            if steps.get("export_multi") and (args.dry_run or bundle_json.is_file()):
                exm = [
                    "uv", "run", "python", str(batch_api), "multi-export",
                    "--run-dir", str(run_dir),
                    "--bundle", str(bundle_json),
                ]
                code = run_cmd(exm, cwd=package_root, dry_run=args.dry_run, log_fp=log_fp, step=f"export_multi:{tid}")
                entry["commands"].append({"cmd": exm, "exit": code})
                if check(code, f"export_multi:{tid}"):
                    return code

            if steps.get("visualize_diagrams") and (args.dry_run or target_path.exists()):
                vzd = [
                    "uv", "run", "python", str(batch_api), "visualize",
                    "--run-dir", str(run_dir),
                    "--target", str(target_path),
                ]
                code = run_cmd(vzd, cwd=package_root, dry_run=args.dry_run, log_fp=log_fp, step=f"visualize:{tid}")
                entry["commands"].append({"cmd": vzd, "exit": code})
                if check(code, f"visualize:{tid}"):
                    return code

        total_wall = time.monotonic() - batch_start
        manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
        manifest["summary"] = {
            "total_wall_time_s": round(total_wall, 3),
            "target_count": n_targets,
            "failed_steps": failures,
        }

        if not args.dry_run:
            _write_cross_target_summary(output_root, manifest, log_fp=log_fp)
        report(
            f"batch done total_wall_time={total_wall:.2f}s targets={n_targets} "
            f"failed_steps={len(failures)}",
            log_fp=log_fp,
        )
        if failures:
            report(f"failures: {', '.join(failures)}", log_fp=log_fp)
        man_path = output_root / "run_manifest.json"
        if not args.dry_run:
            man_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            print(f"Wrote {man_path}", file=log_fp, flush=True)

    finally:
        if log_fp is not sys.stdout:
            log_fp.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())