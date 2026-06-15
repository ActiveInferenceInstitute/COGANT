"""Copy registered manuscript figures and write manifest/sidecar metadata."""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Iterable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from manuscript_figure_registry import MANUSCRIPT_FIGURES, ManuscriptFigure

from figures.constants import (
    COGANT_STAGING_ROOT,
    FIGURE_MANIFEST_SCHEMA_VERSION,
    FIGURE_SIDECAR_SCHEMA_VERSION,
)
from figures.metadata import (
    _artifact_summary,
    _displayed_counts,
    _layout_method,
    _layout_seed,
    _metadata_missing,
    _package_version,
    _panel_metadata,
    _panels,
    _reference_failures,
    _source_artifact_recency_issues,
    _source_metadata,
)
from figures.png import _png_dimensions, _png_text_metadata, _png_visual_metrics, _sha256_file
from figures.renderers import _prepare_source_figures

_IMAGE_LABEL_RE = re.compile(
    r"!\[[^\]]*\]\((?P<path>[^)]+)\)\{#(?P<label>fig:[-A-Za-z0-9_.:]+)(?:\s[^}]*)?\}"
)


def copy_manuscript_figures(
    staging_root: Path | None = None,
    *,
    figures: Iterable[ManuscriptFigure] = MANUSCRIPT_FIGURES,
    strict: bool = False,
) -> Path:
    """Copy curated package output figures and write a manifest.

    Missing figures are recorded in the manifest so fresh checkouts can still
    regenerate the injected manuscript before running the optional visual
    pipeline. Pass ``strict=True`` when rendering a publication artifact.
    """

    root = (staging_root or COGANT_STAGING_ROOT).resolve()
    figures = tuple(figures)
    _prepare_source_figures(root, figures)
    output_dir = root / "output" / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)

    copied: list[dict[str, object]] = []
    missing: list[dict[str, object]] = []
    strict_failures: list[str] = []
    generated_at = datetime.now(UTC).isoformat()
    renderer_version = _package_version(root)

    for figure in figures:
        src = root / figure.source
        dest = output_dir / figure.destination
        record = asdict(figure)
        record["source"] = str(src.relative_to(root))
        record["destination"] = str(dest.relative_to(root))
        if src.is_file():
            shutil.copy2(src, dest)
            record["copied"] = True
            record["bytes"] = dest.stat().st_size
            record["sha256"] = _sha256_file(dest)
            record["dimensions_px"] = _png_dimensions(dest)
            source_artifact = root / figure.source_artifact if figure.source_artifact else None
            record["source_artifact_exists"] = bool(source_artifact and source_artifact.is_file())
            source_artifact_sha256 = (
                _sha256_file(source_artifact)
                if source_artifact and source_artifact.is_file()
                else None
            )
            record["source_artifact_sha256"] = source_artifact_sha256
            record["source_artifact_digest"] = source_artifact_sha256
            record["data_digest_sha256"] = source_artifact_sha256
            record["source_artifact_summary"] = _artifact_summary(source_artifact, root)
            record["source_artifact_recency_issues"] = _source_artifact_recency_issues(source_artifact, root)
            record["visual_qa"] = _png_visual_metrics(dest)
            record["png_text_metadata"] = _png_text_metadata(dest)
            source_sidecar = src.with_suffix(".figure.json")
            if source_sidecar.is_file():
                record["source_figure_sidecar"] = str(source_sidecar.relative_to(root))
                try:
                    record["source_figure_metadata"] = json.loads(
                        source_sidecar.read_text(encoding="utf-8")
                    )
                except ValueError:
                    record["source_figure_metadata"] = None
            source_metadata = _source_metadata(record)
            if source_metadata:
                for key in (
                    "matrix_source_artifact",
                    "matrix_values_from_artifact",
                    "matrix_validation_errors",
                    "fallback_panels",
                    "degraded_panels",
                    "panel_sources",
                    "source_matrix_shapes",
                    "display_matrix_shapes",
                    "displayed_matrix_shapes",
                    "matrix_reducers",
                    "source_matrix_diagnostics",
                    "panel_diagnostics",
                    "matrix_dimensions",
                    "state_space_counts",
                    "dimension_alignment",
                    "axis_labels",
                    "state_label_groups",
                    "state_group_boundary_indices",
                    "matrix_interpretation_notes",
                    "strict_real_matrices",
                    "render_backend",
                    "degraded_renderer",
                    "degraded_rasterization",
                    "selected_target_id",
                    "selected_target_command_count",
                    "batch_target_count",
                    "batch_command_count",
                    "publication_dimension_policy",
                ):
                    if key in source_metadata:
                        record[key] = source_metadata[key]
                if "source_artifact_digest" in source_metadata:
                    record["matrix_source_artifact_digest"] = source_metadata[
                        "source_artifact_digest"
                    ]
            if figure.key == "forward_abcd_matrices":
                record["matrix_source_path"] = figure.source_artifact
                record["matrix_source_digest"] = source_artifact_sha256
                record["matrix_source_artifact_digest"] = (
                    record.get("matrix_source_artifact_digest") or source_artifact_sha256
                )
                reducers = record.get("matrix_reducers")
                if isinstance(reducers, dict) and isinstance(reducers.get("B"), dict):
                    record["b_reducer"] = reducers["B"]
                record.setdefault("fallback_panels", [])
                record.setdefault("degraded_panels", [])
            record["renderer_version"] = renderer_version
            record["known_limitations"] = figure.limitations
            record["displayed_counts"] = _displayed_counts(record)
            record["layout_method"] = _layout_method(record)
            record["layout_seed"] = _layout_seed(record)
            record["panel_metadata"] = _panel_metadata(figure, record)
            record["panels"] = _panels(record)
            metadata_missing = _metadata_missing(record)
            if record["source_artifact_recency_issues"]:
                metadata_missing.extend(
                    f"source_artifact_recency_issue:{item['newer_sibling']}"
                    for item in record["source_artifact_recency_issues"]
                )
            record["metadata_complete"] = not metadata_missing
            record["metadata_missing"] = metadata_missing
            destination_sidecar = dest.with_suffix(".figure.json")
            record["destination_figure_sidecar"] = str(destination_sidecar.relative_to(root))
            figure_metadata = {
                "schema_version": FIGURE_SIDECAR_SCHEMA_VERSION,
                "generated_at": generated_at,
                "key": figure.key,
                "role": figure.role,
                "caption": figure.caption,
                "source": record["source"],
                "destination": record["destination"],
                "source_artifact": figure.source_artifact,
                "source_artifact_sha256": source_artifact_sha256,
                "source_artifact_digest": source_artifact_sha256,
                "data_digest_sha256": source_artifact_sha256,
                "renderer_version": renderer_version,
                "renderer": figure.renderer,
                "layout_method": record["layout_method"],
                "layout_seed": record["layout_seed"],
                "method_note": figure.method_note,
                "reading_guide": figure.reading_guide,
                "limitations": figure.limitations,
                "known_limitations": figure.limitations,
                "alt_text": figure.alt_text,
                "displayed_counts": record["displayed_counts"],
                "panel_metadata": record["panel_metadata"],
                "panels": record["panels"],
                "matrix_source_artifact": record.get("matrix_source_artifact"),
                "matrix_source_artifact_digest": record.get("matrix_source_artifact_digest"),
                "matrix_source_path": record.get("matrix_source_path"),
                "matrix_source_digest": record.get("matrix_source_digest"),
                "matrix_values_from_artifact": record.get("matrix_values_from_artifact"),
                "matrix_validation_errors": record.get("matrix_validation_errors"),
                "fallback_panels": record.get("fallback_panels"),
                "degraded_panels": record.get("degraded_panels"),
                "panel_sources": record.get("panel_sources"),
                "source_matrix_shapes": record.get("source_matrix_shapes"),
                "display_matrix_shapes": record.get("display_matrix_shapes"),
                "displayed_matrix_shapes": record.get("displayed_matrix_shapes")
                or record.get("display_matrix_shapes"),
                "matrix_reducers": record.get("matrix_reducers"),
                "b_reducer": record.get("b_reducer"),
                "source_matrix_diagnostics": record.get("source_matrix_diagnostics"),
                "panel_diagnostics": record.get("panel_diagnostics"),
                "matrix_dimensions": record.get("matrix_dimensions"),
                "state_space_counts": record.get("state_space_counts"),
                "dimension_alignment": record.get("dimension_alignment"),
                "axis_labels": record.get("axis_labels"),
                "state_label_groups": record.get("state_label_groups"),
                "state_group_boundary_indices": record.get("state_group_boundary_indices"),
                "matrix_interpretation_notes": record.get("matrix_interpretation_notes"),
                "strict_real_matrices": record.get("strict_real_matrices"),
                "render_backend": record.get("render_backend"),
                "degraded_renderer": record.get("degraded_renderer"),
                "degraded_rasterization": record.get("degraded_rasterization"),
                "selected_target_id": record.get("selected_target_id"),
                "selected_target_command_count": record.get("selected_target_command_count"),
                "batch_target_count": record.get("batch_target_count"),
                "batch_command_count": record.get("batch_command_count"),
                "publication_dimension_policy": record.get("publication_dimension_policy"),
                "dimensions_px": record["dimensions_px"],
                "image_width_px": (
                    record["dimensions_px"].get("width")
                    if isinstance(record.get("dimensions_px"), dict)
                    else None
                ),
                "image_height_px": (
                    record["dimensions_px"].get("height")
                    if isinstance(record.get("dimensions_px"), dict)
                    else None
                ),
                "bytes": record["bytes"],
                "sha256": record["sha256"],
                "visual_qa": record["visual_qa"],
                "png_text_metadata": record["png_text_metadata"],
                "source_artifact_summary": record["source_artifact_summary"],
                "source_artifact_recency_issues": record["source_artifact_recency_issues"],
                "source_figure_metadata": record.get("source_figure_metadata"),
            }
            destination_sidecar.write_text(
                json.dumps(figure_metadata, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            record["destination_figure_sidecar_exists"] = destination_sidecar.is_file()
            record["figure_metadata"] = figure_metadata
            if metadata_missing:
                strict_failures.append(
                    f"{figure.key}: missing/failed {', '.join(str(item) for item in metadata_missing)}"
                )
            copied.append(record)
        else:
            record["copied"] = False
            missing.append(record)

    strict_failures.extend(_reference_failures(root, figures))
    missing_sidecars = [
        str(item.get("destination_figure_sidecar") or item.get("destination"))
        for item in copied
        if not Path(root / str(item.get("destination_figure_sidecar") or "")).is_file()
    ]
    if missing_sidecars:
        strict_failures.append("missing generated figure sidecars: " + ", ".join(missing_sidecars))

    manifest = {
        "schema_version": FIGURE_MANIFEST_SCHEMA_VERSION,
        "generated_at": generated_at,
        "source_root": "registered COGANT run and evaluation artifacts",
        "output_dir": str(output_dir.relative_to(root)),
        "copied_count": len(copied),
        "missing_count": len(missing),
        "strict_metadata_failure_count": len(strict_failures),
        "strict_metadata_failures": strict_failures,
        "figures": copied,
        "missing": missing,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    _write_template_figure_registry(root, output_dir, copied, generated_at)

    if strict and missing:
        missing_sources = ", ".join(str(item["source"]) for item in missing)
        raise FileNotFoundError(f"Missing manuscript figures: {missing_sources}")
    if strict and strict_failures:
        raise ValueError("Incomplete manuscript figure metadata: " + "; ".join(strict_failures))

    return manifest_path


def _write_template_figure_registry(
    root: Path,
    output_dir: Path,
    copied: list[dict[str, object]],
    generated_at: str,
) -> Path:
    """Write the parent-template figure registry shape beside COGANT's manifest."""

    labels_by_filename = _manuscript_figure_labels_by_filename(root)
    entries: list[dict[str, object]] = []
    for record in copied:
        destination = str(record.get("destination") or "")
        filename = Path(destination).name
        for label in sorted(labels_by_filename.get(filename, ())):
            entries.append(
                {
                    "label": label,
                    "filename": filename,
                    "caption": record.get("caption", ""),
                    "key": record.get("key", ""),
                    "role": record.get("role", ""),
                    "generated_by": record.get("renderer", ""),
                    "source_artifact": record.get("source_artifact", ""),
                    "sha256": record.get("sha256", ""),
                }
            )
    registry = {
        "schema_version": "template-figure-registry-v1",
        "generated_at": generated_at,
        "figures": entries,
    }
    path = output_dir / "figure_registry.json"
    path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _manuscript_figure_labels_by_filename(root: Path) -> dict[str, set[str]]:
    labels: dict[str, set[str]] = {}
    manuscript_dir = root / "manuscript"
    if not manuscript_dir.exists():
        return labels
    for path in sorted(manuscript_dir.glob("*.md")):
        if path.name in {"AGENTS.md", "README.md", "SYNTAX.md"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for match in _IMAGE_LABEL_RE.finditer(text):
            filename = Path(match.group("path")).name
            labels.setdefault(filename, set()).add(match.group("label").rstrip(".,;:"))
    return labels
