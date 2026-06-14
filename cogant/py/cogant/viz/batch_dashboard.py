"""Batch-run dashboard generator for COGANT ``run_all`` sweeps.

A single COGANT run produces a single :class:`~cogant.viz.dashboard.DashboardGenerator`
HTML page. Operators who exercise the staging-root :mod:`run_all` orchestrator,
however, drive the pipeline against several targets in one batch and end up
with one ``output/<target_id>/`` tree per target plus a top-level
``output/run_manifest.json`` describing what was attempted.

:class:`BatchDashboardGenerator` walks that manifest, parses each target's
``bundle.json`` (and surrounding files), and emits a small set of analyzer- and
manuscript-friendly artifacts:

============================= ===========================================
File                          Purpose
============================= ===========================================
``summary.csv``               Per-target metrics row (id, kind, score, …)
``metrics_per_target.json``   Same data, JSON-structured
``dashboard.md``              Top-level Markdown report with cross-links
``node_count_bar.mmd``        Mermaid bar of nodes per target
``edge_count_bar.mmd``        Mermaid bar of edges per target
``score_distribution.mmd``    Mermaid bar chart of validation-score buckets
``visual_completeness.mmd``   Mermaid bar chart of dashboard / abstract completeness
``parser_status_distribution.mmd`` Mermaid bar chart of parser certainty / fallback status
``role_distribution.mmd``     Mermaid bar chart of semantic roles across targets
``confidence_distribution.mmd`` Mermaid bar chart of mapping confidence tiers
``roundtrip_status.mmd``      Mermaid bar chart of roundtrip status buckets
``failure_reasons.mmd``       Mermaid bar chart of failed-step labels
``run_gantt.mmd``             Mermaid Gantt of recorded command timings
============================= ===========================================

The module deliberately uses only the Python standard library so that it
can run under the minimal install profile (no ``matplotlib``, no ``jinja2``,
no ``plotly``). All output is plain text — Mermaid blocks are syntactically
valid and can be embedded in MkDocs or rendered to PNG via
:func:`cogant.viz.render_mermaid_text_to_png` when the visualization extras
are present.

The generator is conservative on input parsing: a missing or malformed
file is reported as an empty / ``None`` field, never an exception, so the
dashboard remains useful even when an individual target fails partway
through the pipeline.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "BatchDashboardGenerator",
    "TargetMetrics",
    "write_batch_dashboard",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TargetMetrics:
    """One row of the batch dashboard, derived from a single target's outputs.

    All numeric fields default to ``0``; absent / unparseable values are
    surfaced as zeros so downstream sums and averages stay total. Use the
    :attr:`presence` mapping to distinguish "no artifact" from "artifact
    with zero counts" — the former has the corresponding key false.
    """

    target_id: str
    kind: str  # "local" | "remote" | "unknown"
    source: str  # path or git_url (best-effort)
    score: float | None  # 0..100 validation score, or None
    node_count: int = 0
    edge_count: int = 0
    mapping_count: int = 0
    gnn_package_files: int = 0
    wall_time_s: float = 0.0
    role_distribution: dict[str, int] = field(default_factory=dict)
    confidence_distribution: dict[str, int] = field(default_factory=dict)
    parser_status: str = "unknown"
    roundtrip_status: str = "not_present"
    generated_code_status: str = "not_present"
    graph_edit_normalized: float | None = None
    visual_artifact_count: int = 0
    failure_reasons: tuple[str, ...] = field(default_factory=tuple)
    failed_steps: tuple[str, ...] = field(default_factory=tuple)
    presence: dict[str, bool] = field(default_factory=dict)

    def as_jsonable(self) -> dict[str, Any]:
        d = asdict(self)
        # tuple → list for JSON-cleanliness
        d["failed_steps"] = list(d["failed_steps"])
        d["failure_reasons"] = list(d["failure_reasons"])
        return d


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("batch_dashboard: failed to read %s (%s)", path, exc)
        return None


def _read_bundle(run_dir: Path) -> dict[str, Any] | None:
    for candidate in (run_dir / "data" / "bundle.json", run_dir / "bundle.json"):
        data = _load_json(candidate)
        if isinstance(data, dict):
            return data
    return None


def _read_run_json(run_dir: Path, *rel_paths: str) -> dict[str, Any]:
    for rel in rel_paths:
        data = _load_json(run_dir / rel)
        if isinstance(data, dict):
            return data
    return {}


def _int_distribution(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, int] = {}
    for key, raw in value.items():
        if isinstance(raw, bool):
            continue
        if isinstance(raw, int | float):
            out[str(key)] = int(raw)
        elif isinstance(raw, dict | list | tuple | set):
            out[str(key)] = len(raw)
    return dict(sorted(out.items()))


def _model_distributions(run_dir: Path) -> tuple[dict[str, int], dict[str, int]]:
    model = _read_run_json(
        run_dir,
        "gnn_package/model.gnn.json",
        "data/model.gnn.json",
        "model.gnn.json",
    )
    mappings = model.get("mappings") if isinstance(model, dict) else {}
    summary = mappings.get("summary") if isinstance(mappings, dict) else {}
    if not isinstance(summary, dict):
        summary = {}
    roles = _int_distribution(summary.get("mapping_kinds"))
    confidence = _int_distribution(summary.get("confidence_tiers"))
    if roles and confidence:
        return roles, confidence
    records = mappings.get("mappings") if isinstance(mappings, dict) else {}
    iterable = (
        records.values()
        if isinstance(records, dict)
        else records
        if isinstance(records, list)
        else []
    )
    for record in iterable:
        if not isinstance(record, dict):
            continue
        kind = str(record.get("kind") or "unknown")
        tier = str(record.get("confidence_tier") or "uncalibrated")
        roles[kind] = roles.get(kind, 0) + 1
        confidence[tier] = confidence.get(tier, 0) + 1
    return dict(sorted(roles.items())), dict(sorted(confidence.items()))


def _roundtrip_statuses(run_dir: Path) -> tuple[str, str, float | None]:
    metrics = _read_run_json(run_dir, "roundtrip/metrics.json", "roundtrip_metrics.json")
    if not metrics:
        return ("not_present", "not_present", None)
    status = str(metrics.get("roundtrip_status") or "").lower()
    if not status:
        is_iso = metrics.get("structurally_isomorphic")
        status = (
            "structurally_isomorphic"
            if is_iso is True
            else "drift"
            if is_iso is False
            else "metrics_present"
        )
    generated_raw = metrics.get("generated_code")
    generated: dict[str, Any] = generated_raw if isinstance(generated_raw, dict) else {}
    generated_status = str(generated.get("status") or "unknown")
    graph_edit = metrics.get("graph_edit_distance")
    normalized = None
    if isinstance(graph_edit, dict) and isinstance(graph_edit.get("normalized"), int | float):
        normalized = float(graph_edit["normalized"])
    return (status, generated_status, normalized)


def _visual_artifact_count(run_dir: Path) -> int:
    count = 0
    for subdir in ("figures", "site", "gnn_package/visualizations"):
        path = run_dir / subdir
        if path.is_dir():
            try:
                count += sum(1 for child in path.rglob("*") if child.is_file())
            except OSError:
                pass
    return count


def _stage_count(
    stage: dict[str, Any] | None,
    *,
    prefer: str,
    fallback: str | tuple[str, ...],
) -> int:
    if not isinstance(stage, dict):
        return 0
    explicit = stage.get(prefer)
    if isinstance(explicit, int):
        return explicit
    fallback_keys = (fallback,) if isinstance(fallback, str) else fallback
    for key in fallback_keys:
        val = stage.get(key)
        if isinstance(val, dict):
            return len(val)
        if isinstance(val, list):
            return len(val)
    return 0


def _bundle_stages(bundle: dict[str, Any] | None) -> dict[str, Any]:
    """Return the stage mapping from either recorded bundle layout.

    Current COGANT bundles write ``stage_results``; older tests and a few
    fixtures use ``stages``. Supporting both keeps the dashboard useful across
    generated archives without forcing a migration pass over old output trees.
    """
    if not isinstance(bundle, dict):
        return {}
    for key in ("stage_results", "stages"):
        val = bundle.get(key)
        if isinstance(val, dict):
            return val
    return {}


def _coerce_score(bundle: dict[str, Any] | None) -> float | None:
    if not isinstance(bundle, dict):
        return None
    val = bundle.get("validation_score")
    stages = _bundle_stages(bundle)
    if val is None:
        validate = stages.get("validate")
        if isinstance(validate, dict):
            val = validate.get("score")
            if val is None:
                gnn_validation = validate.get("gnn_validation")
                if isinstance(gnn_validation, dict):
                    val = gnn_validation.get("score")
    if isinstance(val, (int, float)):
        return float(val)
    return None


def _bundle_kind_source(entry: dict[str, Any] | None) -> tuple[str, str]:
    """Best-effort `(kind, source)` extraction from a manifest entry."""
    if not isinstance(entry, dict):
        return ("unknown", "")
    if entry.get("git_url"):
        return ("remote", str(entry["git_url"]))
    path_val = entry.get("path") or entry.get("absolute_target")
    if path_val:
        return ("local", str(path_val))
    return ("unknown", "")


def _entry_failed_steps(entry: dict[str, Any] | None) -> tuple[str, ...]:
    if not isinstance(entry, dict):
        return ()
    raw = entry.get("failed_steps") or []
    if isinstance(raw, list):
        return tuple(str(x) for x in raw)
    return ()


def _entry_wall_time(entry: dict[str, Any] | None) -> float:
    if not isinstance(entry, dict):
        return 0.0
    cmds = entry.get("commands") or []
    if not isinstance(cmds, list):
        return 0.0
    total = 0.0
    for cmd in cmds:
        if isinstance(cmd, dict):
            dt = cmd.get("wall_time_s")
            if isinstance(dt, (int, float)):
                total += float(dt)
    return round(total, 3)


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return 0
    if isinstance(value, dict | list | tuple | set):
        return len(value)
    return 0


def _parser_status(
    run_dir: Path, *, node_count: int, edge_count: int, failed_steps: tuple[str, ...]
) -> str:
    """Return a compact parser status bucket for dashboards.

    The pipeline can emit parser information through several artifacts
    depending on whether the run came from the CLI, the batch API, or an older
    stored output tree. This helper reads the common fields but never fails the
    dashboard when those reports are absent.
    """

    report = _read_run_json(
        run_dir,
        "data/parser_report.json",
        "analysis/parser_report.json",
        "parser_report.json",
        "data/static_analysis.json",
        "analysis/static_analysis.json",
    )
    raw_status = report.get("parser_status") or report.get("status")
    if isinstance(raw_status, str) and raw_status.strip():
        normalized = raw_status.strip().lower().replace(" ", "_")
        if normalized in {"parsed", "fallback", "partial", "failed", "unknown"}:
            return normalized

    fallback_count = max(
        _coerce_int(report.get("parser_fallback_count")),
        _coerce_int(report.get("fallback_count")),
        _coerce_int(report.get("fallbacks")),
    )
    skipped_count = max(
        _coerce_int(report.get("skipped_file_count")),
        _coerce_int(report.get("skipped_files")),
    )
    unsupported_count = max(
        _coerce_int(report.get("unsupported_construct_count")),
        _coerce_int(report.get("unsupported_constructs")),
        _coerce_int(report.get("unsupported")),
    )
    if any("parse" in step.lower() or "static" in step.lower() for step in failed_steps):
        return "failed"
    if fallback_count:
        return "fallback"
    if skipped_count or unsupported_count:
        return "partial"
    if node_count or edge_count:
        return "parsed"
    return "unknown"


def _count_gnn_package_files(run_dir: Path) -> int:
    pkg = run_dir / "gnn_package"
    if not pkg.is_dir():
        return 0
    try:
        return sum(1 for _ in pkg.rglob("*") if _.is_file())
    except OSError:
        return 0


def _presence_flags(run_dir: Path) -> dict[str, bool]:
    return {
        "data": (run_dir / "data").is_dir(),
        "site": (run_dir / "site").is_dir(),
        "inspection_dashboard": (run_dir / "site" / "inspection_dashboard.html").is_file(),
        "gnn_package": (run_dir / "gnn_package").is_dir(),
        "roundtrip": (run_dir / "roundtrip").is_dir(),
        "roundtrip_metrics": (run_dir / "roundtrip" / "metrics.json").is_file(),
        "analysis": (run_dir / "analysis").is_dir(),
        "exports": (run_dir / "exports").is_dir(),
        "diagrams": (run_dir / "diagrams").is_dir(),
        "figures": (run_dir / "figures").is_dir(),
        "graphical_abstract": (
            (run_dir / "figures" / "graphical_abstract.png").is_file()
            or (run_dir / "figures" / "graphical_abstract.svg").is_file()
        ),
        "validate_report": (run_dir / "validate.txt").is_file(),
        "scan_json": (run_dir / "scan.json").is_file(),
        "graph_txt": (run_dir / "graph.txt").is_file(),
    }


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


class BatchDashboardGenerator:
    """Build cross-target dashboard artifacts from a ``run_all`` output tree.

    Parameters
    ----------
    output_root
        Directory written by ``run_all`` — typically ``cogant/output``.
        Must contain at least one per-target subdirectory; ``run_manifest.json``
        is consulted when present but not required.
    manifest
        Pre-loaded manifest dict. When ``None`` (the default), the
        generator reads ``output_root / "run_manifest.json"``. Pass an
        explicit dict for tests or for synthesised batch reports.
    """

    def __init__(
        self,
        output_root: Path | str,
        *,
        manifest: dict[str, Any] | None = None,
    ) -> None:
        self.output_root = Path(output_root)
        self._explicit_manifest = manifest

    # ------------------------------------------------------------------
    # Inputs
    # ------------------------------------------------------------------

    def load_manifest(self) -> dict[str, Any]:
        """Return the run manifest, falling back to an empty skeleton."""
        if self._explicit_manifest is not None:
            return self._explicit_manifest
        loaded = _load_json(self.output_root / "run_manifest.json")
        if isinstance(loaded, dict):
            return loaded
        return {"targets": [], "summary": {}}

    def discover_targets(self, manifest: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Return manifest target entries; fall back to subdir scan when absent.

        When the manifest is missing or has no ``targets`` array, every
        immediate subdirectory of ``output_root`` that contains a
        ``data/`` *or* ``bundle.json`` is treated as a target with id =
        directory name. This keeps the dashboard usable for ad-hoc
        manual sweeps without a manifest.
        """
        man = manifest if manifest is not None else self.load_manifest()
        targets = man.get("targets") if isinstance(man, dict) else None
        if isinstance(targets, list) and targets:
            return [t for t in targets if isinstance(t, dict)]
        scanned: list[dict[str, Any]] = []
        if not self.output_root.is_dir():
            return scanned
        for child in sorted(self.output_root.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith("."):
                continue
            if (child / "bundle.json").is_file() or (child / "data" / "bundle.json").is_file():
                scanned.append({"id": child.name, "run_dir": str(child), "commands": []})
        return scanned

    # ------------------------------------------------------------------
    # Per-target metrics
    # ------------------------------------------------------------------

    def collect_target_metrics(
        self,
        manifest: dict[str, Any] | None = None,
    ) -> list[TargetMetrics]:
        """Return one :class:`TargetMetrics` per discovered target."""
        man = manifest if manifest is not None else self.load_manifest()
        entries = self.discover_targets(man)
        rows: list[TargetMetrics] = []
        for entry in entries:
            tid = str(entry.get("id") or "unknown")
            run_dir_str = entry.get("run_dir") or str(self.output_root / tid)
            run_dir = Path(run_dir_str)
            bundle = _read_bundle(run_dir)
            stages = _bundle_stages(bundle)
            graph_stage = stages.get("graph")
            translate_stage = stages.get("translate")
            node_count = _stage_count(graph_stage, prefer="node_count", fallback="nodes")
            edge_count = _stage_count(graph_stage, prefer="edge_count", fallback="edges")
            mapping_count = _stage_count(
                translate_stage,
                prefer="mapping_count",
                fallback=("mappings", "mapping_ids", "semantic_mappings"),
            )
            kind, source = _bundle_kind_source(entry)
            roles, confidence = _model_distributions(run_dir)
            roundtrip_status, generated_code_status, graph_edit_normalized = _roundtrip_statuses(
                run_dir
            )
            failed_steps = _entry_failed_steps(entry)
            parser_status = _parser_status(
                run_dir,
                node_count=node_count,
                edge_count=edge_count,
                failed_steps=failed_steps,
            )
            rows.append(
                TargetMetrics(
                    target_id=tid,
                    kind=kind,
                    source=source,
                    score=_coerce_score(bundle),
                    node_count=node_count,
                    edge_count=edge_count,
                    mapping_count=mapping_count,
                    gnn_package_files=_count_gnn_package_files(run_dir),
                    wall_time_s=_entry_wall_time(entry),
                    role_distribution=roles,
                    confidence_distribution=confidence,
                    parser_status=parser_status,
                    roundtrip_status=roundtrip_status,
                    generated_code_status=generated_code_status,
                    graph_edit_normalized=graph_edit_normalized,
                    visual_artifact_count=_visual_artifact_count(run_dir),
                    failure_reasons=failed_steps,
                    failed_steps=failed_steps,
                    presence=_presence_flags(run_dir),
                )
            )
        return rows

    # ------------------------------------------------------------------
    # Renderers
    # ------------------------------------------------------------------

    def render_summary_csv(self, metrics: list[TargetMetrics]) -> str:
        """Return a CSV with one row per target plus a header row."""
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerow(
            [
                "target_id",
                "kind",
                "source",
                "score",
                "node_count",
                "edge_count",
                "mapping_count",
                "gnn_package_files",
                "wall_time_s",
                "parser_status",
                "roundtrip_status",
                "generated_code_status",
                "graph_edit_normalized",
                "visual_artifact_count",
                "failed_step_count",
                "has_site",
                "has_inspection_dashboard",
                "has_graphical_abstract",
                "has_roundtrip",
                "has_roundtrip_metrics",
                "has_gnn_package",
            ]
        )
        for m in metrics:
            writer.writerow(
                [
                    m.target_id,
                    m.kind,
                    m.source,
                    "" if m.score is None else f"{m.score:.2f}",
                    m.node_count,
                    m.edge_count,
                    m.mapping_count,
                    m.gnn_package_files,
                    f"{m.wall_time_s:.3f}",
                    m.parser_status,
                    m.roundtrip_status,
                    m.generated_code_status,
                    "" if m.graph_edit_normalized is None else f"{m.graph_edit_normalized:.4f}",
                    m.visual_artifact_count,
                    len(m.failed_steps),
                    int(bool(m.presence.get("site"))),
                    int(bool(m.presence.get("inspection_dashboard"))),
                    int(bool(m.presence.get("graphical_abstract"))),
                    int(bool(m.presence.get("roundtrip"))),
                    int(bool(m.presence.get("roundtrip_metrics"))),
                    int(bool(m.presence.get("gnn_package"))),
                ]
            )
        return buf.getvalue()

    def render_metrics_json(
        self,
        metrics: list[TargetMetrics],
        manifest: dict[str, Any] | None = None,
    ) -> str:
        man = manifest if manifest is not None else self.load_manifest()
        payload = {
            "schema_version": "1.0",
            "output_root": str(self.output_root),
            "started_at": man.get("started_at") if isinstance(man, dict) else None,
            "finished_at": man.get("finished_at") if isinstance(man, dict) else None,
            "summary": man.get("summary") if isinstance(man, dict) else {},
            "targets": [m.as_jsonable() for m in metrics],
        }
        return json.dumps(payload, indent=2)

    @staticmethod
    def _mermaid_bar(title: str, axis_label: str, metrics: list[TargetMetrics], attr: str) -> str:
        """Return a Mermaid xychart-beta bar diagram for one numeric attribute.

        Falls back to a single ``"(no targets)"`` bar when ``metrics`` is empty
        so the file is still valid Mermaid syntax.
        """
        if not metrics:
            ids = ['"(no targets)"']
            vals = [0]
        else:
            ids = [f'"{m.target_id}"' for m in metrics]
            vals = [int(getattr(m, attr)) for m in metrics]
        return (
            "%%{init: {'theme': 'default'}}%%\n"
            "xychart-beta\n"
            f'    title "{title}"\n'
            f"    x-axis [{', '.join(ids)}]\n"
            f'    y-axis "{axis_label}"\n'
            f"    bar [{', '.join(str(v) for v in vals)}]\n"
        )

    @staticmethod
    def _mermaid_label(value: str) -> str:
        safe = value.replace("\\", "/").replace('"', "'")
        return f'"{safe}"'

    @classmethod
    def _mermaid_count_bar(cls, title: str, axis_label: str, counts: dict[str, int]) -> str:
        """Return a Mermaid xychart-beta bar diagram for categorical counts.

        The method name avoids claiming a horizontal orientation because Mermaid's
        lightweight chart grammar does not expose one. Counts are sorted by value
        and directly labelled in the source, which keeps these charts more
        inspectable than the old pie slices while preserving the same artifact
        filenames for downstream links.
        """
        nonzero = [(str(label), int(count)) for label, count in counts.items() if int(count)]
        if not nonzero:
            nonzero = [("none", 0)]
        nonzero.sort(key=lambda item: (-item[1], item[0]))
        labels = [cls._mermaid_label(label) for label, _ in nonzero]
        values = [str(count) for _, count in nonzero]
        return (
            "%%{init: {'theme': 'default'}}%%\n"
            "xychart-beta\n"
            f'    title "{title}"\n'
            f"    x-axis [{', '.join(labels)}]\n"
            f'    y-axis "{axis_label}"\n'
            f"    bar [{', '.join(values)}]\n"
        )

    def render_mermaid_node_bar(self, metrics: list[TargetMetrics]) -> str:
        return self._mermaid_bar(
            title="Program graph nodes per target",
            axis_label="nodes",
            metrics=metrics,
            attr="node_count",
        )

    def render_mermaid_edge_bar(self, metrics: list[TargetMetrics]) -> str:
        return self._mermaid_bar(
            title="Program graph edges per target",
            axis_label="edges",
            metrics=metrics,
            attr="edge_count",
        )

    def render_mermaid_score_pie(self, metrics: list[TargetMetrics]) -> str:
        """Return validation-score buckets as bars.

        The recorded method name is retained for callers and tests that
        predate the visualization rewrite away from pie charts.
        """
        buckets = {"100": 0, "90-99": 0, "70-89": 0, "<70": 0, "no-score": 0}
        for m in metrics:
            s = m.score
            if s is None:
                buckets["no-score"] += 1
            elif s >= 100:
                buckets["100"] += 1
            elif s >= 90:
                buckets["90-99"] += 1
            elif s >= 70:
                buckets["70-89"] += 1
            else:
                buckets["<70"] += 1
        return self._mermaid_count_bar("Validation score distribution", "targets", buckets)

    def render_mermaid_visual_completeness_pie(self, metrics: list[TargetMetrics]) -> str:
        """Return visual-workbench completeness buckets as bars.

        The recorded method name is retained for compatibility.
        """
        buckets = {"dashboard+abstract+roundtrip": 0, "partial": 0, "missing": 0}
        for m in metrics:
            has_dashboard = bool(m.presence.get("inspection_dashboard"))
            has_abstract = bool(m.presence.get("graphical_abstract"))
            has_roundtrip_metrics = bool(m.presence.get("roundtrip_metrics"))
            if has_dashboard and has_abstract and has_roundtrip_metrics:
                buckets["dashboard+abstract+roundtrip"] += 1
            elif has_dashboard or has_abstract or has_roundtrip_metrics:
                buckets["partial"] += 1
            else:
                buckets["missing"] += 1
        return self._mermaid_count_bar("Visual workbench completeness", "targets", buckets)

    @staticmethod
    def _aggregate_dicts(metrics: list[TargetMetrics], attr: str) -> dict[str, int]:
        totals: dict[str, int] = {}
        for metric in metrics:
            value = getattr(metric, attr)
            if not isinstance(value, dict):
                continue
            for key, count in value.items():
                totals[str(key)] = totals.get(str(key), 0) + int(count)
        return dict(sorted(totals.items(), key=lambda item: (-item[1], item[0])))

    def _bar_from_counts(self, title: str, axis_label: str, counts: dict[str, int]) -> str:
        return self._mermaid_count_bar(title, axis_label, counts)

    def render_mermaid_role_distribution(self, metrics: list[TargetMetrics]) -> str:
        return self._bar_from_counts(
            "Semantic role distribution",
            "mappings",
            self._aggregate_dicts(metrics, "role_distribution"),
        )

    def render_mermaid_confidence_distribution(self, metrics: list[TargetMetrics]) -> str:
        return self._bar_from_counts(
            "Confidence tier distribution",
            "mappings",
            self._aggregate_dicts(metrics, "confidence_distribution"),
        )

    def render_mermaid_parser_status_pie(self, metrics: list[TargetMetrics]) -> str:
        counts: dict[str, int] = {}
        for metric in metrics:
            counts[metric.parser_status] = counts.get(metric.parser_status, 0) + 1
        return self._bar_from_counts("Parser status distribution", "targets", counts)

    def render_mermaid_roundtrip_status_pie(self, metrics: list[TargetMetrics]) -> str:
        counts: dict[str, int] = {}
        for metric in metrics:
            counts[metric.roundtrip_status] = counts.get(metric.roundtrip_status, 0) + 1
        return self._bar_from_counts("Roundtrip status", "targets", counts)

    def render_mermaid_failure_reasons_pie(self, metrics: list[TargetMetrics]) -> str:
        counts: dict[str, int] = {}
        for metric in metrics:
            for reason in metric.failure_reasons:
                counts[reason] = counts.get(reason, 0) + 1
        return self._bar_from_counts("Failure reasons", "failed steps", counts)

    def render_mermaid_gantt(
        self,
        manifest: dict[str, Any] | None = None,
        *,
        max_rows: int = 60,
    ) -> str:
        """Return a Mermaid Gantt of recorded command timings.

        The chart sums consecutive command durations per target so each
        target produces one row per step name (truncated at ``max_rows``).
        Manifests without ``wall_time_s`` per command fall back to a
        single placeholder bar so the file remains valid Mermaid.
        """
        man = manifest if manifest is not None else self.load_manifest()
        targets = man.get("targets") if isinstance(man, dict) else None
        rows: list[tuple[str, str, float]] = []
        if isinstance(targets, list):
            for entry in targets:
                if not isinstance(entry, dict):
                    continue
                tid = str(entry.get("id") or "unknown")
                cmds = entry.get("commands") or []
                if not isinstance(cmds, list):
                    continue
                for cmd in cmds:
                    if not isinstance(cmd, dict):
                        continue
                    dt = cmd.get("wall_time_s")
                    name = cmd.get("step") or cmd.get("cmd") or "step"
                    if isinstance(dt, (int, float)) and dt > 0:
                        rows.append((tid, str(name), float(dt)))
        rows = rows[:max_rows]
        if not rows:
            return (
                "gantt\n"
                "    title COGANT batch timing (no wall_time_s recorded)\n"
                "    dateFormat  X\n"
                "    axisFormat  %S\n"
                "    section batch\n"
                "    no-data : 0, 1\n"
            )
        lines = [
            "gantt",
            "    title COGANT batch timings",
            "    dateFormat  X",
            "    axisFormat  %S",
        ]
        current_target: str | None = None
        cursor = 0.0
        for tid, step, dt in rows:
            if tid != current_target:
                lines.append(f"    section {tid}")
                current_target = tid
            start = int(cursor)
            end = int(cursor + dt)
            if end <= start:
                end = start + 1
            safe_step = step.replace(":", "_")
            lines.append(f"    {safe_step} : {start}, {end}")
            cursor = float(end)
        return "\n".join(lines) + "\n"

    def render_markdown_dashboard(
        self,
        metrics: list[TargetMetrics],
        manifest: dict[str, Any] | None = None,
    ) -> str:
        """Return a top-level Markdown report linking every artifact."""
        man = manifest if manifest is not None else self.load_manifest()
        summary = man.get("summary") if isinstance(man, dict) else {}
        if not isinstance(summary, dict):
            summary = {}
        n = len(metrics)
        n_scored = sum(1 for m in metrics if m.score is not None)
        mean_score = (
            sum(m.score for m in metrics if m.score is not None) / n_scored if n_scored else None
        )
        total_nodes = sum(m.node_count for m in metrics)
        total_edges = sum(m.edge_count for m in metrics)
        total_mappings = sum(m.mapping_count for m in metrics)
        total_visuals = sum(m.visual_artifact_count for m in metrics)
        total_wall = summary.get("total_wall_time_s") or sum(m.wall_time_s for m in metrics)
        visual_complete = sum(
            1
            for m in metrics
            if m.presence.get("inspection_dashboard")
            and m.presence.get("graphical_abstract")
            and m.presence.get("roundtrip_metrics")
        )
        failures = summary.get("failed_steps") or []
        if not isinstance(failures, list):
            failures = []

        lines: list[str] = []
        lines.append("# COGANT batch dashboard")
        lines.append("")
        lines.append(
            "Auto-generated by `cogant.viz.batch_dashboard.BatchDashboardGenerator`. "
            "Run `uv run --directory cogant python ../scripts/batch_dashboard.py "
            "--output-root cogant/output` from the staging root to rebuild after a sweep."
        )
        lines.append("")
        lines.append("## Headline")
        lines.append("")
        lines.append(f"- Targets: **{n}**")
        if mean_score is not None:
            lines.append(f"- Mean validation score: **{mean_score:.1f} / 100**")
        else:
            lines.append("- Mean validation score: (none scored)")
        lines.append(f"- Total program-graph nodes: **{total_nodes}**")
        lines.append(f"- Total program-graph edges: **{total_edges}**")
        lines.append(f"- Total semantic mappings: **{total_mappings}**")
        lines.append(f"- Visual artifacts discovered: **{total_visuals}**")
        try:
            lines.append(f"- Total wall time: **{float(total_wall):.2f}s**")
        except (TypeError, ValueError):
            pass
        lines.append(f"- Failed step labels: **{len(failures)}**")
        lines.append(f"- Visual workbench complete: **{visual_complete} / {n}**")
        lines.append("")

        # Per-target table
        lines.append("## Per-target metrics")
        lines.append("")
        lines.append(
            "| Target | Kind | Score | Nodes | Edges | Mappings | "
            "GNN files | Parser | Roundtrip | Code | Graph edit | Visuals | Wall (s) | Failures |"
        )
        lines.append(
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | ---: | ---: | ---: | ---: |"
        )
        for m in metrics:
            score_str = "-" if m.score is None else f"{m.score:.1f}"
            lines.append(
                f"| `{m.target_id}` | {m.kind} | {score_str} | "
                f"{m.node_count} | {m.edge_count} | {m.mapping_count} | "
                f"{m.gnn_package_files} | {m.parser_status} | "
                f"{m.roundtrip_status} | {m.generated_code_status} | "
                f"{'-' if m.graph_edit_normalized is None else f'{m.graph_edit_normalized:.3f}'} | "
                f"{m.visual_artifact_count} | {m.wall_time_s:.2f} | "
                f"{len(m.failed_steps)} |"
            )
        lines.append("")

        # Mermaid embeds
        lines.append("## Visualisations")
        lines.append("")
        lines.append("### Nodes per target")
        lines.append("")
        lines.append("```mermaid")
        lines.append(self.render_mermaid_node_bar(metrics).rstrip())
        lines.append("```")
        lines.append("")
        lines.append("### Edges per target")
        lines.append("")
        lines.append("```mermaid")
        lines.append(self.render_mermaid_edge_bar(metrics).rstrip())
        lines.append("```")
        lines.append("")
        lines.append("### Validation-score distribution")
        lines.append("")
        lines.append("```mermaid")
        lines.append(self.render_mermaid_score_pie(metrics).rstrip())
        lines.append("```")
        lines.append("")
        lines.append("### Visual-workbench completeness")
        lines.append("")
        lines.append("```mermaid")
        lines.append(self.render_mermaid_visual_completeness_pie(metrics).rstrip())
        lines.append("```")
        lines.append("")
        lines.append("### Parser status distribution")
        lines.append("")
        lines.append("```mermaid")
        lines.append(self.render_mermaid_parser_status_pie(metrics).rstrip())
        lines.append("```")
        lines.append("")
        lines.append("### Semantic role distribution")
        lines.append("")
        lines.append("```mermaid")
        lines.append(self.render_mermaid_role_distribution(metrics).rstrip())
        lines.append("```")
        lines.append("")
        lines.append("### Confidence-tier distribution")
        lines.append("")
        lines.append("```mermaid")
        lines.append(self.render_mermaid_confidence_distribution(metrics).rstrip())
        lines.append("```")
        lines.append("")
        lines.append("### Roundtrip status")
        lines.append("")
        lines.append("```mermaid")
        lines.append(self.render_mermaid_roundtrip_status_pie(metrics).rstrip())
        lines.append("```")
        lines.append("")
        lines.append("### Failure reasons")
        lines.append("")
        lines.append("```mermaid")
        lines.append(self.render_mermaid_failure_reasons_pie(metrics).rstrip())
        lines.append("```")
        lines.append("")

        # Artifact bullet list
        lines.append("## Artifacts")
        lines.append("")
        for m in metrics:
            sub = []
            if m.presence.get("gnn_package"):
                sub.append("`gnn_package/`")
            if m.presence.get("site"):
                sub.append("`site/`")
            if m.presence.get("inspection_dashboard"):
                sub.append("`site/inspection_dashboard.html`")
            if m.presence.get("graphical_abstract"):
                sub.append("`figures/graphical_abstract.*`")
            if m.presence.get("roundtrip"):
                sub.append("`roundtrip/`")
            if m.presence.get("roundtrip_metrics"):
                sub.append("`roundtrip/metrics.json`")
            if m.presence.get("validate_report"):
                sub.append("`validate.txt`")
            if m.presence.get("scan_json"):
                sub.append("`scan.json`")
            if m.presence.get("analysis"):
                sub.append("`analysis/`")
            if m.presence.get("exports"):
                sub.append("`exports/`")
            present = ", ".join(sub) if sub else "(no auxiliary directories)"
            lines.append(f"- **{m.target_id}** — {present}")
        if not metrics:
            lines.append("- (no targets discovered)")
        lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Top-level "write all artifacts" convenience
    # ------------------------------------------------------------------

    def write_all(self, dashboard_dir: Path | str | None = None) -> dict[str, Path]:
        """Materialise every artifact under ``dashboard_dir`` (default: ``output_root / "dashboard"``).

        Returns a ``{artifact_name: written_path}`` mapping for the caller
        to log or include in a manifest.
        """
        dest = Path(dashboard_dir) if dashboard_dir else self.output_root / "dashboard"
        dest.mkdir(parents=True, exist_ok=True)
        manifest = self.load_manifest()
        metrics = self.collect_target_metrics(manifest)

        written: dict[str, Path] = {}

        csv_path = dest / "summary.csv"
        csv_path.write_text(self.render_summary_csv(metrics), encoding="utf-8")
        written["summary_csv"] = csv_path

        json_path = dest / "metrics_per_target.json"
        json_path.write_text(self.render_metrics_json(metrics, manifest), encoding="utf-8")
        written["metrics_json"] = json_path

        node_bar_path = dest / "node_count_bar.mmd"
        node_bar_path.write_text(self.render_mermaid_node_bar(metrics), encoding="utf-8")
        written["node_count_bar"] = node_bar_path

        edge_bar_path = dest / "edge_count_bar.mmd"
        edge_bar_path.write_text(self.render_mermaid_edge_bar(metrics), encoding="utf-8")
        written["edge_count_bar"] = edge_bar_path

        score_path = dest / "score_distribution.mmd"
        score_path.write_text(self.render_mermaid_score_pie(metrics), encoding="utf-8")
        written["score_distribution"] = score_path

        visual_path = dest / "visual_completeness.mmd"
        visual_path.write_text(
            self.render_mermaid_visual_completeness_pie(metrics), encoding="utf-8"
        )
        written["visual_completeness"] = visual_path

        parser_path = dest / "parser_status_distribution.mmd"
        parser_path.write_text(self.render_mermaid_parser_status_pie(metrics), encoding="utf-8")
        written["parser_status_distribution"] = parser_path

        role_path = dest / "role_distribution.mmd"
        role_path.write_text(self.render_mermaid_role_distribution(metrics), encoding="utf-8")
        written["role_distribution"] = role_path

        confidence_path = dest / "confidence_distribution.mmd"
        confidence_path.write_text(
            self.render_mermaid_confidence_distribution(metrics), encoding="utf-8"
        )
        written["confidence_distribution"] = confidence_path

        rt_status_path = dest / "roundtrip_status.mmd"
        rt_status_path.write_text(
            self.render_mermaid_roundtrip_status_pie(metrics), encoding="utf-8"
        )
        written["roundtrip_status"] = rt_status_path

        failure_path = dest / "failure_reasons.mmd"
        failure_path.write_text(self.render_mermaid_failure_reasons_pie(metrics), encoding="utf-8")
        written["failure_reasons"] = failure_path

        gantt_path = dest / "run_gantt.mmd"
        gantt_path.write_text(self.render_mermaid_gantt(manifest), encoding="utf-8")
        written["run_gantt"] = gantt_path

        md_path = dest / "dashboard.md"
        md_path.write_text(self.render_markdown_dashboard(metrics, manifest), encoding="utf-8")
        written["dashboard_md"] = md_path

        return written


def write_batch_dashboard(
    output_root: Path | str,
    *,
    dashboard_dir: Path | str | None = None,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Path]:
    """Functional shortcut around :class:`BatchDashboardGenerator`."""
    gen = BatchDashboardGenerator(output_root, manifest=manifest)
    return gen.write_all(dashboard_dir)
