"""Render a human-readable Markdown summary of a COGANT bundle.

The export bundle (a ``Bundle`` instance, or its ``json``-serialized form
written by ``cogant translate``/``cogant export-gnn``) is a nested dict
that captures every pipeline artifact. ``render_bundle_markdown`` walks
that dict and emits a compact report that is suitable for embedding in
``output/<target>/export_gnn/bundle.md`` or ``reports/run_summary.md``.

The renderer is intentionally tolerant: any unexpected payload shape
(e.g. an old bundle format, or a partially-populated stage) degrades to
``-`` rather than raising, so it can safely run over historical outputs.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def render_bundle_markdown(data: Mapping[str, Any]) -> str:
    """Render a COGANT export bundle dict to a Markdown report.

    Parameters
    ----------
    data:
        The bundle as a mapping (``Bundle.to_dict()`` or the deserialized
        ``bundle.json``). Only ``target``, ``artifacts``, ``stage_results``,
        ``errors`` and ``metadata`` are consumed; extra keys are ignored.

    Returns
    -------
    str
        A self-contained Markdown document. Always non-empty: even an
        otherwise empty bundle produces a header with the target.
    """
    target = str(data.get("target", "<unknown>"))
    artifacts = _as_dict(data.get("artifacts"))
    stage_results = _as_dict(data.get("stage_results"))
    errors = _as_list(data.get("errors"))
    metadata = _as_dict(data.get("metadata"))

    lines: list[str] = []
    lines.append("# COGANT Export")
    lines.append("")
    lines.append(f"- target: `{target}`")
    timing = _as_dict(metadata.get("timing"))
    if "wall_time_ms" in timing:
        lines.append(f"- wall_time_ms: {timing.get('wall_time_ms')}")
    lines.append(f"- stages: {len(stage_results)}")
    lines.append(f"- errors: {len(errors)}")
    lines.append("")

    ingest = _as_dict(stage_results.get("ingest"))
    if ingest:
        lines.append("## Repository")
        lines.append("")
        lines.append(f"- files: {_count(ingest.get('file_count'))}")
        langs = _as_dict(ingest.get("language_distribution"))
        for lang, n in sorted(langs.items()):
            lines.append(f"  - {lang}: {n}")
        lines.append("")

    parsed = _as_list(artifacts.get("parsed_modules_detail"))
    if parsed:
        funcs = sum(_count(_as_dict(m).get("functions")) for m in parsed)
        classes = sum(_count(_as_dict(m).get("classes")) for m in parsed)
        imports = sum(_count(_as_dict(m).get("imports")) for m in parsed)
        lines.append("## Static analysis")
        lines.append("")
        lines.append(f"- modules parsed: {len(parsed)}")
        lines.append(f"- functions: {funcs}")
        lines.append(f"- classes: {classes}")
        lines.append(f"- imports: {imports}")
        lines.append("")

    if stage_results:
        lines.append("## Stages")
        lines.append("")
        lines.append("| stage | summary |")
        lines.append("|---|---|")
        for name in sorted(stage_results):
            lines.append(f"| {name} | {_stage_summary(name, stage_results[name])} |")
        lines.append("")

    if errors:
        lines.append("## Errors")
        lines.append("")
        for err in errors:
            lines.append(f"- {err}")
        lines.append("")

    repo_meta = _as_dict(_as_dict(artifacts.get("repo_snapshot")).get("metadata"))
    if repo_meta:
        rendered: list[str] = []
        for key in ("name", "language", "commit_hash", "author", "timestamp"):
            value = repo_meta.get(key)
            if value:
                rendered.append(f"- {key}: `{value}`")
        if rendered:
            lines.append("## Source")
            lines.append("")
            lines.extend(rendered)
            lines.append("")

    return "\n".join(lines)


def _stage_summary(name: str, payload: Any) -> str:
    """Return a one-line summary describing a single ``stage_results`` entry."""
    if not isinstance(payload, dict):
        return "-"
    if name == "ingest":
        return f"files={_count(payload.get('file_count'))}"
    if name == "static":
        return (
            f"modules={_count(payload.get('modules'))}, "
            f"nodes={_count(payload.get('nodes'))}, "
            f"edges={_count(payload.get('edges'))}"
        )
    if name == "normalize":
        return (
            f"facts={_count(payload.get('fact_count'))}, "
            f"nodes={_count(payload.get('nodes'))}, "
            f"edges={_count(payload.get('edges'))}"
        )
    if name == "graph":
        return f"nodes={_count(payload.get('nodes'))}, edges={_count(payload.get('edges'))}"
    if name == "translate":
        mappings = payload.get("mapping_count")
        if mappings is None:
            mappings = _count(payload.get("mapping_ids"))
        return f"mappings={_count(mappings)}"
    if name == "statespace":
        return (
            f"states={_count(payload.get('states'))}, "
            f"obs={_count(payload.get('observations'))}, "
            f"actions={_count(payload.get('actions'))}"
        )
    if name == "process":
        return (
            f"stages={_count(payload.get('stage_count') or payload.get('stages'))}, "
            f"deps={_count(payload.get('dependencies'))}"
        )
    if name == "validate":
        return (
            f"passed={payload.get('passed')}, "
            f"warnings={_count(payload.get('warnings'))}, "
            f"issues={_count(payload.get('issues'))}"
        )
    if name == "export":
        return f"artifacts={_count(payload.get('artifacts'))}"
    if name == "dynamic":
        if payload.get("skipped"):
            reason = payload.get("reason") or "skipped"
            return f"skipped: {reason}"
        return f"events={_count(payload.get('events'))}"
    return "-"


def _as_dict(obj: Any) -> dict[str, Any]:
    """Return ``obj`` as a ``dict`` if it is a Mapping, else an empty dict."""
    return dict(obj) if isinstance(obj, Mapping) else {}


def _as_list(obj: Any) -> list[Any]:
    """Return ``obj`` as a ``list`` if it is already a list, else an empty list."""
    return list(obj) if isinstance(obj, list) else []


def _count(value: Any) -> int:
    """Best-effort length: ints pass through, sized containers return ``len``."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, (dict, list, tuple, set)):
        return len(value)
    return 0


__all__ = ["render_bundle_markdown"]
