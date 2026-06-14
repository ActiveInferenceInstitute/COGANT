"""Dependency-light PNG inspection helpers for strict figure QA."""

from __future__ import annotations

import hashlib
import zlib
from collections.abc import Iterable
from pathlib import Path


def _sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _png_dimensions(path: Path) -> dict[str, int] | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return {
        "width": int.from_bytes(data[16:20], "big"),
        "height": int.from_bytes(data[20:24], "big"),
    }


def _png_chunks(data: bytes) -> Iterable[tuple[bytes, bytes]]:
    offset = 8
    while offset + 12 <= len(data):
        length = int.from_bytes(data[offset : offset + 4], "big")
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        yield kind, payload
        offset += 12 + length
        if kind == b"IEND":
            break


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _png_visual_metrics(path: Path) -> dict[str, object] | None:
    """Return lightweight publication QA metrics for an 8-bit PNG.

    This deliberately avoids Pillow so strict manuscript checks work in the
    small template-tooling environment. Unsupported PNG encodings still report
    dimensions and mark colour-diversity fields as unavailable.
    """

    try:
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None

    ihdr = data[16:29]
    width = int.from_bytes(ihdr[0:4], "big")
    height = int.from_bytes(ihdr[4:8], "big")
    bit_depth = ihdr[8]
    color_type = ihdr[9]
    metrics: dict[str, object] = {
        "width": width,
        "height": height,
        "min_dimension_ok": width >= 320 and height >= 180,
        "png_bit_depth": bit_depth,
        "png_color_type": color_type,
    }

    channels_by_type = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    channels = channels_by_type.get(color_type)
    if bit_depth != 8 or channels is None:
        metrics.update(
            {
                "sampled_pixels": 0,
                "estimated_unique_colors": None,
                "nonblank": None,
                "color_diversity_ok": None,
            }
        )
        return metrics

    idat = b"".join(payload for kind, payload in _png_chunks(data) if kind == b"IDAT")
    try:
        raw = zlib.decompress(idat)
    except zlib.error:
        metrics.update(
            {
                "sampled_pixels": 0,
                "estimated_unique_colors": None,
                "nonblank": None,
                "color_diversity_ok": None,
            }
        )
        return metrics

    stride = width * channels
    bpp = channels
    rows: list[bytes] = []
    pos = 0
    prior = bytes(stride)
    for _ in range(height):
        if pos >= len(raw):
            break
        filter_type = raw[pos]
        pos += 1
        row = bytearray(raw[pos : pos + stride])
        pos += stride
        for i, value in enumerate(row):
            left = row[i - bpp] if i >= bpp else 0
            up = prior[i] if i < len(prior) else 0
            up_left = prior[i - bpp] if i >= bpp and i - bpp < len(prior) else 0
            if filter_type == 1:
                row[i] = (value + left) & 0xFF
            elif filter_type == 2:
                row[i] = (value + up) & 0xFF
            elif filter_type == 3:
                row[i] = (value + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                row[i] = (value + _paeth(left, up, up_left)) & 0xFF
        prior = bytes(row)
        rows.append(prior)

    if not rows:
        metrics.update(
            {
                "sampled_pixels": 0,
                "estimated_unique_colors": 0,
                "nonblank": False,
                "color_diversity_ok": False,
            }
        )
        return metrics

    step = max(1, int(((width * height) / 10_000) ** 0.5))
    unique: set[tuple[int, ...]] = set()
    sampled = 0
    for y in range(0, len(rows), step):
        row = rows[y]
        for x in range(0, width, step):
            start = x * channels
            unique.add(tuple(row[start : start + channels]))
            sampled += 1
    unique_count = len(unique)
    metrics.update(
        {
            "sampled_pixels": sampled,
            "estimated_unique_colors": unique_count,
            "nonblank": unique_count > 1,
            "color_diversity_ok": unique_count >= 4,
        }
    )
    return metrics


def _png_text_metadata(path: Path) -> list[str]:
    try:
        data = path.read_bytes()
    except OSError:
        return []
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return []

    texts: list[str] = []
    for kind, payload in _png_chunks(data):
        try:
            if kind == b"tEXt":
                key, _, value = payload.partition(b"\x00")
                texts.append(
                    f"{key.decode('latin-1', 'ignore')}={value.decode('latin-1', 'ignore')}"
                )
            elif kind == b"zTXt":
                key, _, rest = payload.partition(b"\x00")
                if len(rest) >= 2:
                    value = zlib.decompress(rest[1:]).decode("utf-8", "ignore")
                    texts.append(f"{key.decode('latin-1', 'ignore')}={value}")
            elif kind == b"iTXt":
                parts = payload.split(b"\x00", 5)
                if len(parts) == 6:
                    key, compression_flag, _compression_method, _lang, _translated, value = parts
                    raw_text = zlib.decompress(value) if compression_flag == b"\x01" else value
                    texts.append(
                        f"{key.decode('utf-8', 'ignore')}={raw_text.decode('utf-8', 'ignore')}"
                    )
        except (OSError, UnicodeDecodeError, zlib.error):
            continue
    return texts
