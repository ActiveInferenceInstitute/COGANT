"""Shared anti-tautology assertions for visualization tests.

These helpers reject "figure exists" and "file is non-empty" checks that can
pass for visually degenerate outputs.
"""

from __future__ import annotations

import os
import struct
from pathlib import Path
from typing import Any

import numpy as np

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _array_has_values(data: Any) -> bool:
    """Return True when an extracted artist array is non-empty and not all-NaN."""
    array = np.asarray(data)
    if array.size == 0:
        return False
    try:
        return not np.isnan(array).all()
    except TypeError:
        return True


def _line_has_content(line: Any) -> bool:
    """Return True when a line carries y-data that is not empty/all-NaN."""
    return _array_has_values(line.get_ydata())


def _image_has_content(image: Any) -> bool:
    """Return True when an image artist exposes a non-empty, not-all-NaN array."""
    return _array_has_values(image.get_array())


def _collection_has_content(collection: Any) -> bool:
    """Return True when a collection has real drawable payload."""
    get_array = getattr(collection, "get_array", None)
    if callable(get_array):
        data = get_array()
        if data is not None:
            return _array_has_values(data)

    get_offsets = getattr(collection, "get_offsets", None)
    if callable(get_offsets):
        offsets = get_offsets()
        if offsets is None:
            return False
        return _array_has_values(offsets)

    return True


def assert_figure_nondegenerate(fig: object, *, allow_text_only: bool = False) -> None:
    """Assert that a matplotlib figure contains real drawn content.

    Text-only figures are rejected by default because they commonly indicate
    placeholder/empty rendering paths that still produce a Figure object.
    """
    assert fig is not None, "Expected a matplotlib Figure, got None"

    get_axes = getattr(fig, "get_axes", None)
    assert callable(get_axes), f"Expected figure-like object with get_axes(), got {type(fig)!r}"

    axes = list(get_axes())
    assert axes, "Figure is degenerate: fig.get_axes() returned no Axes"

    saw_text = False
    reasons: list[str] = []
    for index, ax in enumerate(axes):
        if any(_line_has_content(line) for line in ax.lines):
            return
        if ax.patches:
            return
        if any(_image_has_content(image) for image in ax.images):
            return
        if any(_collection_has_content(collection) for collection in ax.collections):
            return
        if ax.texts:
            saw_text = True
        reasons.append(
            f"axes[{index}]: lines={len(ax.lines)}, patches={len(ax.patches)}, images={len(ax.images)}, "
            f"collections={len(ax.collections)}, texts={len(ax.texts)}"
        )

    if allow_text_only and saw_text:
        return

    text_note = " Text-only axes were present but do not count by default." if saw_text else ""
    raise AssertionError(
        "Figure is degenerate: no Axes contained lines, patches, images, or collections."
        f"{text_note} Details: {'; '.join(reasons)}"
    )


def assert_png_nondegenerate(path: str | os.PathLike[str]) -> None:
    """Assert that a PNG file exists, is structurally valid, and is larger than 1x1."""
    png_path = Path(path)
    assert png_path.exists(), f"{png_path}: expected PNG file to exist"
    assert png_path.is_file(), f"{png_path}: expected a regular file"

    with png_path.open("rb") as handle:
        header = handle.read(24)

    assert len(header) >= 24, f"{png_path}: file too short for PNG header/IHDR ({len(header)} bytes)"
    assert header[:8] == PNG_MAGIC, f"{png_path}: invalid PNG magic {header[:8]!r}"

    chunk_length, chunk_type = struct.unpack(">I4s", header[8:16])
    assert chunk_type == b"IHDR", f"{png_path}: expected IHDR chunk, found {chunk_type!r}"
    assert chunk_length >= 8, f"{png_path}: IHDR chunk too short for width/height ({chunk_length})"

    width, height = struct.unpack(">II", header[16:24])
    assert width > 1, f"{png_path}: PNG width is degenerate ({width})"
    assert height > 1, f"{png_path}: PNG height is degenerate ({height})"
