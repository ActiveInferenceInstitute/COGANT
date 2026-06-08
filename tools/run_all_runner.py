"""Batch corpus runner implementation for run_all.py.

Extracted from the project-root orchestrator so ``run_all.py`` stays a thin
argparse entrypoint.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STAGING_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = STAGING_ROOT / "run_all.json"


@dataclass(frozen=True)
class RunBatchOptions:
    """Programmatic options for :func:`run_batch` (no argparse re-parse)."""

    config: Path | None = None
    dry_run: bool = False
    fail_fast: bool = False
    log: Path | None = None
    targets: str | None = None

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> RunBatchOptions:
        return cls(
            config=getattr(args, "config", None),
            dry_run=bool(getattr(args, "dry_run", False)),
            fail_fast=bool(getattr(args, "fail_fast", False)),
            log=getattr(args, "log", None),
            targets=getattr(args, "targets", None),
        )

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
        "export_multi_formats": "json,jsonlines",
        "visualize_diagrams": True,
        "visualize_format": "mermaid",
        # Post-batch cross-target dashboard
        # (cogant.viz.batch_dashboard via scripts/batch_dashboard.py).
        "batch_dashboard": True,
    },
    "manuscript": {
        "enabled": False,
        "regenerate_metrics": False,
        "strict": False,
    },
}


@dataclass(frozen=True)
class CommandResult:
    """Exit status plus wall-clock timing for manifest recording."""

    returncode: int
    wall_time_s: float = 0.0


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
) -> CommandResult:
    print(f"+ {' '.join(argv)}", file=log_fp, flush=True)
    if dry_run:
        report(f"  [{step}] (dry-run)", log_fp=log_fp)
        return CommandResult(0, 0.0)
    t0 = time.monotonic()
    code = subprocess.call(argv, cwd=str(cwd), env=os.environ.copy())
    dt = time.monotonic() - t0
    status = "ok" if code == 0 else f"FAIL exit={code}"
    report(f"  [{step}] {status} wall_time={dt:.2f}s", log_fp=log_fp)
    return CommandResult(code, dt)


def run_cmd_capture(
    argv: list[str],
    *,
    cwd: Path,
    dry_run: bool,
    out_path: Path,
    log_fp: Any,
    step: str = "capture",
) -> CommandResult:
    print(f"+ {' '.join(argv)} > {out_path}", file=log_fp, flush=True)
    if dry_run:
        report(f"  [{step}] → {out_path.name} (dry-run)", log_fp=log_fp)
        return CommandResult(0, 0.0)
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
    return CommandResult(proc.returncode, dt)


def ensure_git_clone(
    *,
    git_url: str,
    git_ref: str | None,
    dest: Path,
    shallow: bool,
    refresh: bool,
    dry_run: bool,
    log_fp: Any,
) -> CommandResult:
    if dry_run:
        parts = ["git", "clone"]
        if shallow:
            parts.extend(["--depth", "1"])
        if git_ref:
            parts.extend(["--branch", git_ref])
        parts.extend([git_url, str(dest)])
        print(f"+ {' '.join(parts)}", file=log_fp, flush=True)
        report("  [git_clone] (dry-run)", log_fp=log_fp)
        return CommandResult(0, 0.0)

    if refresh and dest.exists():
        shutil.rmtree(dest)
    if dest.exists() and (dest / ".git").is_dir():
        report(f"  [git_clone] skip (existing clone) {dest}", log_fp=log_fp)
        return CommandResult(0, 0.0)

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
    return CommandResult(proc.returncode, dt)


def command_record(
    argv: list[str] | str,
    *,
    step: str,
    result: CommandResult,
) -> dict[str, Any]:
    """Return the stable manifest shape for one executed command."""
    return {
        "cmd": argv,
        "step": step,
        "exit": result.returncode,
        "wall_time_s": round(result.wall_time_s, 3),
    }


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


def _stage_count(stage: dict[str, Any], *, prefer: str, fallback: str) -> int:
    """Return a real integer count from a bundle stage dict.

    Bundles store the full ``nodes``/``edges`` dicts at the stage level but
    do not (today) populate matching ``node_count``/``edge_count`` scalar
    fields. Falling through to ``len(dict)`` keeps the summary honest even
    if the producer side adds explicit counts later.
    """
    explicit = stage.get(prefer)
    if isinstance(explicit, int):
        return explicit
    val = stage.get(fallback)
    if isinstance(val, dict):
        return len(val)
    if isinstance(val, list):
        return len(val)
    return 0


def _failures_for_target(failures: list[str], target_id: str) -> list[str]:
    """Filter the manifest-level failure labels down to one target."""
    suffix = f":{target_id}"
    return [f for f in failures if f.endswith(suffix)]


def _format_score(score: float | int | None) -> str:
    if score is None:
        return "-"
    try:
        return f"{float(score):.1f}%"
    except (TypeError, ValueError):
        return str(score)


def _rel(run_dir: Path, child: Path) -> str:
    try:
        return str(child.relative_to(run_dir))
    except ValueError:
        return str(child)


def _write_cross_target_summary(
    output_root: Path,
    manifest: dict[str, Any],
    *,
    log_fp: Any,
) -> None:
    """Emit ``summary.json`` and ``summary.md`` aggregating per-target results.

    ``summary.json`` is the structured source of truth: one ``rows`` entry per
    target with real integer counts, score, and presence flags for the
    auxiliary directories produced by the sweep.

    ``summary.md`` has two sections:

    1. A compact top-level table covering every target (score, node/edge/
       mapping counts, file-count for the GNN package, presence checks for
       ``site/``, ``roundtrip/reverse/``, ``analysis/``, ``exports/`` and
       ``diagrams/``).
    2. A per-target rich block with a small key/value table (kind, source,
       valid, counts, GNN package files, warnings) and a "key artifacts"
       bullet list of relative paths into ``data/``, ``gnn_package/``,
       ``site/``, ``roundtrip/forward/``, and ``analysis/``.
    """
    summary_meta = manifest.get("summary", {}) or {}
    failures: list[str] = list(summary_meta.get("failed_steps", []) or [])

    rows: list[dict[str, Any]] = []
    for t in manifest.get("targets", []):
        run_dir = Path(t["run_dir"])
        bundle = _read_bundle(run_dir)
        target_failures = _failures_for_target(failures, t.get("id", ""))
        row: dict[str, Any] = {
            "id": t.get("id"),
            "kind": "remote" if t.get("git_url") else "local",
            "source": t.get("git_url") or t.get("path"),
            "run_dir": str(run_dir),
            "warnings_count": len(target_failures),
            "failed_steps": target_failures,
        }
        if bundle is not None:
            sr = bundle.get("stage_results", {}) or {}
            gnn_val = (sr.get("validate", {}) or {}).get("gnn_validation", {}) or {}
            graph_stage = sr.get("graph", {}) or {}
            translate_stage = sr.get("translate", {}) or {}
            row.update(
                {
                    "score": gnn_val.get("score"),
                    "valid": gnn_val.get("valid"),
                    "node_count": _stage_count(graph_stage, prefer="node_count", fallback="nodes"),
                    "edge_count": _stage_count(graph_stage, prefer="edge_count", fallback="edges"),
                    "mapping_count": _stage_count(
                        translate_stage, prefer="mapping_count", fallback="mapping_ids"
                    ),
                    "gnn_package_files": (
                        len(list((run_dir / "gnn_package").glob("*")))
                        if (run_dir / "gnn_package").is_dir()
                        else 0
                    ),
                    "has_site": (run_dir / "site" / "index.html").is_file(),
                    "has_reverse": (
                        any((run_dir / "roundtrip" / "reverse").glob("*"))
                        if (run_dir / "roundtrip" / "reverse").is_dir()
                        else False
                    ),
                    "has_analysis": (run_dir / "analysis").is_dir()
                    and any((run_dir / "analysis").iterdir()),
                    "has_exports": (run_dir / "exports").is_dir()
                    and any((run_dir / "exports").iterdir()),
                    "has_diagrams": (run_dir / "diagrams").is_dir()
                    and any((run_dir / "diagrams").iterdir()),
                }
            )
        else:
            row["score"] = None
            row["valid"] = None
            row["node_count"] = 0
            row["edge_count"] = 0
            row["mapping_count"] = 0
            row["gnn_package_files"] = 0
            row["has_site"] = False
            row["has_reverse"] = False
            row["has_analysis"] = False
            row["has_exports"] = False
            row["has_diagrams"] = False
        rows.append(row)

    summary_json = output_root / "summary.json"
    summary_json.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "target_count": len(rows),
                "total_wall_time_s": summary_meta.get("total_wall_time_s"),
                "failed_steps": failures,
                "rows": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    def chk(flag: bool) -> str:
        return "✓" if flag else "-"

    lines: list[str] = []
    lines.append("# COGANT batch run summary")
    lines.append("")
    lines.append(f"- Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Targets: **{len(rows)}**")
    lines.append(f"- Total wall time: **{summary_meta.get('total_wall_time_s')}s**")
    lines.append(f"- Failed steps: **{len(failures)}**")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(
        "| id | kind | score | nodes | edges | mappings | gnn_pkg | site | reverse "
        "| analysis | exports | diagrams |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|:---:|:---:|:---:|:---:|:---:|")
    for r in rows:
        lines.append(
            "| {id} | {kind} | {score} | {nodes} | {edges} | {map} | {pkg} "
            "| {site} | {rev} | {an} | {ex} | {di} |".format(
                id=r.get("id"),
                kind=r.get("kind"),
                score=_format_score(r.get("score")),
                nodes=r.get("node_count", 0),
                edges=r.get("edge_count", 0),
                map=r.get("mapping_count", 0),
                pkg=r.get("gnn_package_files", 0),
                site=chk(r.get("has_site", False)),
                rev=chk(r.get("has_reverse", False)),
                an=chk(r.get("has_analysis", False)),
                ex=chk(r.get("has_exports", False)),
                di=chk(r.get("has_diagrams", False)),
            )
        )
    lines.append("")
    lines.append("## Per-target detail")
    lines.append("")
    for r in rows:
        run_dir = Path(r["run_dir"])
        lines.append(f"### {r.get('id')}")
        lines.append("")
        lines.append("| field | value |")
        lines.append("|---|---|")
        lines.append(f"| kind | {r.get('kind')} |")
        lines.append(f"| source | `{r.get('source')}` |")
        lines.append(f"| run_dir | `{r.get('run_dir')}` |")
        lines.append(f"| score | {_format_score(r.get('score'))} |")
        lines.append(f"| valid | {chk(bool(r.get('valid')))} |")
        lines.append(f"| nodes | {r.get('node_count', 0)} |")
        lines.append(f"| edges | {r.get('edge_count', 0)} |")
        lines.append(f"| mappings | {r.get('mapping_count', 0)} |")
        lines.append(f"| gnn_package files | {r.get('gnn_package_files', 0)} |")
        lines.append(f"| warnings | {r.get('warnings_count', 0)} |")
        if r.get("failed_steps"):
            lines.append(f"| failed steps | {', '.join(r['failed_steps'])} |")
        lines.append("")
        artifact_paths = [
            ("bundle", run_dir / "data" / "bundle.json"),
            ("gnn package manifest", run_dir / "gnn_package" / "manifest.json"),
            ("static site", run_dir / "site" / "index.html"),
            ("forward gnn", run_dir / "roundtrip" / "forward" / "model.gnn.md"),
            ("graph metrics", run_dir / "analysis" / "graph_metrics.json"),
        ]
        present = [(label, p) for label, p in artifact_paths if p.exists()]
        if present:
            lines.append("Key artifacts:")
            lines.append("")
            for label, p in present:
                lines.append(f"- {label}: `{_rel(run_dir, p)}`")
            lines.append("")

    summary_md = output_root / "summary.md"
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report(f"wrote cross-target summary: {summary_json.name}, {summary_md.name}", log_fp=log_fp)



def run_batch(options: RunBatchOptions | argparse.Namespace) -> int:
    """Run the configured batch corpus. Accepts :class:`RunBatchOptions` or argparse namespace."""
    if isinstance(options, argparse.Namespace):
        options = RunBatchOptions.from_namespace(options)

    cfg = load_config(options.config)
    package_root = (STAGING_ROOT / Path(cfg["package_root"])).resolve()
    if not (package_root / "pyproject.toml").is_file():
        print(f"error: package_root {package_root} has no pyproject.toml", file=sys.stderr)
        return 2

    output_root = (STAGING_ROOT / cfg["output_root"]).resolve()
    steps = cfg["steps"]
    manuscript = cfg.get("manuscript") or {}
    remote_cfg = cfg.get("remote") or {}

    if options.targets:
        wanted = {s.strip() for s in options.targets.split(",") if s.strip()}
        cfg["targets"] = [t for t in cfg["targets"] if t.get("id") in wanted]
        if not cfg["targets"]:
            print(
                f"error: --targets {sorted(wanted)!r} matched nothing in config",
                file=sys.stderr,
            )
            return 2

    if options.log:
        log_path = Path(options.log).expanduser()
        if log_path.parent != Path("."):
            log_path.parent.mkdir(parents=True, exist_ok=True)
        log_fp: Any = open(log_path, "a", encoding="utf-8")
    else:
        log_fp = sys.stdout
    failures: list[str] = []
    try:
        manifest: dict[str, Any] = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "staging_root": str(STAGING_ROOT),
            "package_root": str(package_root),
            "output_root": str(output_root),
            "dry_run": options.dry_run,
            "targets": [],
        }
        batch_start = time.monotonic()
        n_targets = len(cfg["targets"])

        def check(result: CommandResult | int, label: str) -> int:
            code = result.returncode if isinstance(result, CommandResult) else result
            if code != 0:
                report(f"warning: {label} exited {code}", log_fp=log_fp)
                failures.append(label)
                if options.fail_fast:
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
            result = run_cmd(
                margv,
                cwd=template_root,
                dry_run=options.dry_run,
                log_fp=log_fp,
                step="manuscript_variables",
            )
            if rc := check(result, "manuscript_variables"):
                return rc

        if steps.get("doctor"):
            result = run_cmd(
                ["uv", "run", "cogant", "doctor"],
                cwd=package_root,
                dry_run=options.dry_run,
                log_fp=log_fp,
                step="doctor",
            )
            if rc := check(result, "doctor"):
                return rc

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
                if options.fail_fast:
                    return 2
                continue

            manifest["targets"].append(entry)

            kind = "remote" if git_url else "local"
            report(
                f"=== target {ti}/{n_targets} id={tid} kind={kind} run_dir={run_dir}",
                log_fp=log_fp,
            )

            if git_url:
                result = ensure_git_clone(
                    git_url=str(git_url),
                    git_ref=t.get("git_ref"),
                    dest=src,
                    shallow=bool(remote_cfg.get("shallow_clone", True)),
                    refresh=bool(remote_cfg.get("refresh", False)),
                    dry_run=options.dry_run,
                    log_fp=log_fp,
                )
                entry["commands"].append(
                    command_record("git clone", step=f"git_clone:{tid}", result=result)
                )
                if rc := check(result, f"git_clone:{tid}"):
                    return rc

            if not options.dry_run and not target_path.exists():
                print(f"error: missing target path {target_path}", file=sys.stderr)
                if options.fail_fast:
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
                result = run_cmd(
                    tr,
                    cwd=package_root,
                    dry_run=options.dry_run,
                    log_fp=log_fp,
                    step=f"translate:{tid}",
                )
                entry["commands"].append(
                    command_record(tr, step=f"translate:{tid}", result=result)
                )
                if rc := check(result, f"translate:{tid}"):
                    return rc
                # Re-resolve after translate so downstream gates see the real path.
                bundle_json = _bundle_path()
                if not options.dry_run and not bundle_json.is_file():
                    print(
                        f"warning: no bundle at {bundle_json} after translate",
                        file=sys.stderr,
                    )

            if steps.get("scan_json"):
                scan_cmd = ["uv", "run", "cogant", "scan", str(target_path), "-f", "json"]
                result = run_cmd_capture(
                    scan_cmd,
                    cwd=package_root,
                    dry_run=options.dry_run,
                    out_path=run_dir / "scan.json",
                    log_fp=log_fp,
                    step=f"scan:{tid}",
                )
                entry["commands"].append(
                    command_record(scan_cmd, step=f"scan:{tid}", result=result)
                )
                if rc := check(result, f"scan:{tid}"):
                    return rc

            if steps.get("graph_stdout"):
                graph_cmd = ["uv", "run", "cogant", "graph", str(target_path)]
                result = run_cmd_capture(
                    graph_cmd,
                    cwd=package_root,
                    dry_run=options.dry_run,
                    out_path=run_dir / "graph.txt",
                    log_fp=log_fp,
                    step=f"graph:{tid}",
                )
                entry["commands"].append(
                    command_record(graph_cmd, step=f"graph:{tid}", result=result)
                )
                if rc := check(result, f"graph:{tid}"):
                    return rc

            if steps.get("export_gnn") and (options.dry_run or bundle_json.is_file()):
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
                result = run_cmd(
                    ex,
                    cwd=package_root,
                    dry_run=options.dry_run,
                    log_fp=log_fp,
                    step=f"export_gnn:{tid}",
                )
                entry["commands"].append(
                    command_record(ex, step=f"export_gnn:{tid}", result=result)
                )
                if rc := check(result, f"export-gnn:{tid}"):
                    return rc

            if steps.get("render_site") and (options.dry_run or bundle_json.is_file()):
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
                result = run_cmd(
                    rv, cwd=package_root, dry_run=options.dry_run, log_fp=log_fp, step=f"render:{tid}"
                )
                entry["commands"].append(
                    command_record(rv, step=f"render:{tid}", result=result)
                )
                if rc := check(result, f"render:{tid}"):
                    return rc

            if steps.get("viz_png") and (options.dry_run or run_dir.is_dir()):
                vz = ["uv", "run", "cogant", "viz", str(run_dir)]
                result = run_cmd(
                    vz, cwd=package_root, dry_run=options.dry_run, log_fp=log_fp, step=f"viz:{tid}"
                )
                entry["commands"].append(
                    command_record(vz, step=f"viz:{tid}", result=result)
                )
                if rc := check(result, f"viz:{tid}"):
                    return rc

            if steps.get("validate_run_dir") and (options.dry_run or run_dir.is_dir()):
                val = ["uv", "run", "cogant", "validate", str(run_dir)]
                if steps.get("validate_no_upstream_gnn"):
                    val.append("--no-upstream-gnn")
                result = run_cmd_capture(
                    val,
                    cwd=package_root,
                    dry_run=options.dry_run,
                    out_path=run_dir / "validate.txt",
                    log_fp=log_fp,
                    step=f"validate:{tid}",
                )
                entry["commands"].append(
                    command_record(val, step=f"validate:{tid}", result=result)
                )
                if rc := check(result, f"validate:{tid}"):
                    return rc

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
                result = run_cmd_capture(
                    ex,
                    cwd=package_root,
                    dry_run=options.dry_run,
                    out_path=run_dir / "explain.json",
                    log_fp=log_fp,
                    step=f"explain:{tid}",
                )
                entry["commands"].append(
                    command_record(ex, step=f"explain:{tid}", result=result)
                )
                if rc := check(result, f"explain:{tid}"):
                    return rc

            if steps.get("roundtrip") and (options.dry_run or target_path.exists()):
                rt_dir = run_dir / "roundtrip"
                if not options.dry_run:
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
                threshold = t.get("roundtrip_threshold")
                if threshold is not None:
                    rt.extend(["--threshold", str(threshold)])
                result = run_cmd(
                    rt,
                    cwd=package_root,
                    dry_run=options.dry_run,
                    log_fp=log_fp,
                    step=f"roundtrip:{tid}",
                )
                entry["commands"].append(
                    command_record(rt, step=f"roundtrip:{tid}", result=result)
                )
                if rc := check(result, f"roundtrip:{tid}"):
                    return rc

            batch_api = STAGING_ROOT / "tools" / "batch_api.py"

            if steps.get("analyze_graph") and (options.dry_run or target_path.exists()):
                ag = [
                    "uv",
                    "run",
                    "python",
                    str(batch_api),
                    "graph-analysis",
                    "--run-dir",
                    str(run_dir),
                    "--target",
                    str(target_path),
                ]
                result = run_cmd(
                    ag,
                    cwd=package_root,
                    dry_run=options.dry_run,
                    log_fp=log_fp,
                    step=f"analyze_graph:{tid}",
                )
                entry["commands"].append(
                    command_record(ag, step=f"analyze_graph:{tid}", result=result)
                )
                if rc := check(result, f"analyze_graph:{tid}"):
                    return rc

            if steps.get("analyze_static") and (options.dry_run or target_path.exists()):
                asta = [
                    "uv",
                    "run",
                    "python",
                    str(batch_api),
                    "static-analysis",
                    "--run-dir",
                    str(run_dir),
                    "--target",
                    str(target_path),
                ]
                result = run_cmd(
                    asta,
                    cwd=package_root,
                    dry_run=options.dry_run,
                    log_fp=log_fp,
                    step=f"analyze_static:{tid}",
                )
                entry["commands"].append(
                    command_record(asta, step=f"analyze_static:{tid}", result=result)
                )
                if rc := check(result, f"analyze_static:{tid}"):
                    return rc

            if steps.get("export_multi") and (options.dry_run or bundle_json.is_file()):
                exm = [
                    "uv",
                    "run",
                    "python",
                    str(batch_api),
                    "multi-export",
                    "--run-dir",
                    str(run_dir),
                    "--bundle",
                    str(bundle_json),
                ]
                result = run_cmd(
                    exm,
                    cwd=package_root,
                    dry_run=options.dry_run,
                    log_fp=log_fp,
                    step=f"export_multi:{tid}",
                )
                entry["commands"].append(
                    command_record(exm, step=f"export_multi:{tid}", result=result)
                )
                if rc := check(result, f"export_multi:{tid}"):
                    return rc

            if steps.get("visualize_diagrams") and (options.dry_run or target_path.exists()):
                vzd = [
                    "uv",
                    "run",
                    "python",
                    str(batch_api),
                    "visualize",
                    "--run-dir",
                    str(run_dir),
                    "--target",
                    str(target_path),
                ]
                result = run_cmd(
                    vzd,
                    cwd=package_root,
                    dry_run=options.dry_run,
                    log_fp=log_fp,
                    step=f"visualize:{tid}",
                )
                entry["commands"].append(
                    command_record(vzd, step=f"visualize:{tid}", result=result)
                )
                if rc := check(result, f"visualize:{tid}"):
                    return rc

        total_wall = time.monotonic() - batch_start
        manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
        manifest["summary"] = {
            "total_wall_time_s": round(total_wall, 3),
            "target_count": n_targets,
            "failed_steps": failures,
        }

        if not options.dry_run:
            _write_cross_target_summary(output_root, manifest, log_fp=log_fp)
        report(
            f"batch done total_wall_time={total_wall:.2f}s targets={n_targets} "
            f"failed_steps={len(failures)}",
            log_fp=log_fp,
        )
        if failures:
            report(f"failures: {', '.join(failures)}", log_fp=log_fp)
        man_path = output_root / "run_manifest.json"
        if not options.dry_run:
            man_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            print(f"Wrote {man_path}", file=log_fp, flush=True)

        if not options.dry_run and steps.get("batch_dashboard", True):
            dash_script = STAGING_ROOT / "scripts" / "batch_dashboard.py"
            if dash_script.is_file():
                result = run_cmd(
                    [
                        "uv",
                        "run",
                        "python",
                        str(dash_script),
                        "--output-root",
                        str(output_root),
                        "--quiet",
                    ],
                    cwd=package_root,
                    dry_run=False,
                    log_fp=log_fp,
                    step="batch_dashboard",
                )
                post_record = {
                    "exit": result.returncode,
                    "wall_time_s": round(result.wall_time_s, 3),
                    "dir": str((output_root / "dashboard").resolve()),
                }
                manifest.setdefault("post_steps", {})["batch_dashboard"] = post_record
                if result.returncode != 0:
                    report(
                        f"batch_dashboard failed exit={result.returncode} (not fatal)",
                        log_fp=log_fp,
                    )
                # Rewrite manifest so post_steps is persisted, including
                # advisory failures.
                man_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            else:
                report(
                    f"batch_dashboard skipped (script not found at {dash_script})",
                    log_fp=log_fp,
                )

    finally:
        if log_fp is not sys.stdout:
            log_fp.close()

    # Propagate batch failure through the process exit code so CI and
    # run.sh callers can detect a failed sweep without parsing summary.json.
    # (--fail-fast still early-returns the nonzero code mid-loop.)
    return 1 if failures else 0

