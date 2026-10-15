"""Strict numeric decoding for authoritative GNN matrix fences."""

from __future__ import annotations

import math
import re

MatrixValue = list[float] | list[list[float]] | list[list[list[float]]]
_HEADER = re.compile(r"([ABCD])\[\[rows=(\d+)\](?:\[cols=(\d+)\])?(?:\[depth=(\d+)\])?\]")
_ACTION = re.compile(r"#\s*action\s*=\s*(\d+)")


def _row(line: str, width: int) -> list[float]:
    values = [float(token) for token in line.split()]
    if len(values) != width or any(not math.isfinite(value) for value in values):
        raise ValueError(f"matrix row requires {width} finite numeric entries")
    return values


def _transition(lines: list[str], dimensions: tuple[int, int, int]) -> list[list[list[float]]]:
    rows, cols, depth = dimensions
    slices: dict[int, list[list[float]]] = {}
    current: int | None = None
    for line in lines:
        action = _ACTION.fullmatch(line)
        if action:
            current = int(action[1])
            if current >= depth:
                raise ValueError(f"B action={current} is outside declared depth={depth}")
            if current in slices:
                raise ValueError(f"duplicate B action slice {current}")
            slices[current] = []
        elif line.startswith("#"):
            if "action" in line:
                raise ValueError("invalid B action slice header")
        else:
            if current is None:
                raise ValueError("B numeric rows require an action slice header")
            slices[current].append(_row(line, cols))
    if set(slices) != set(range(depth)):
        raise ValueError("B is missing declared action slices")
    if any(len(values) != rows for values in slices.values()):
        raise ValueError(f"each B action slice requires exactly {rows} rows")
    return [
        [[slices[action][r][c] for action in range(depth)] for c in range(cols)]
        for r in range(rows)
    ]


def read_matrices(text: str, max_elements: int) -> dict[str, MatrixValue]:
    """Read one complete fence without truncation, projection or duplicate replacement."""
    starts = list(re.finditer(r"^\s*```gnn-matrices[^\n]*\n", text, re.MULTILINE))
    if not starts:
        return {}
    if len(starts) != 1:
        raise ValueError("expected exactly one authoritative gnn-matrices fence")
    closing = re.search(r"^\s*```\s*$", text[starts[0].end() :], re.MULTILINE)
    if closing is None:
        raise ValueError("unterminated gnn-matrices fence")
    block = text[starts[0].end() : starts[0].end() + closing.start()]
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    matrices: dict[str, MatrixValue] = {}
    index = 0
    while index < len(lines):
        if lines[index].startswith("#"):
            index += 1
            continue
        header = _HEADER.fullmatch(lines[index])
        if header is None:
            raise ValueError(f"invalid matrix header: {lines[index]}")
        name = header[1]
        if name in matrices:
            raise ValueError(f"duplicate matrix header {name}")
        rows = int(header[2])
        cols = int(header[3]) if header[3] is not None else 1
        depth = int(header[4]) if header[4] is not None else 1
        size = rows * cols * depth
        if size > max_elements or max(rows, cols, depth) > max_elements:
            raise ValueError(
                f"{name} would allocate {size} elements; MAX_REVERSE_MATRIX_ELEMENTS={max_elements}"
            )
        index += 1
        end = index
        while end < len(lines) and _HEADER.fullmatch(lines[end]) is None:
            end += 1
        body = lines[index:end]
        if name == "B":
            if header[3] is None or header[4] is None:
                raise ValueError("B requires explicit rows, cols and depth")
            if rows > 0 and (cols == 0 or depth == 0):
                raise ValueError("nonempty B requires positive columns and action depth")
            matrices[name] = _transition(body, (rows, cols, depth))
        else:
            numeric = [line for line in body if not line.startswith("#")]
            if len(numeric) != rows:
                raise ValueError(f"{name} requires exactly {rows} rows")
            if name == "A":
                if header[3] is None or header[4] is not None:
                    raise ValueError("A requires rows and cols only")
                matrices[name] = [_row(line, cols) for line in numeric]
            else:
                if cols != 1 or header[4] is not None:
                    raise ValueError(f"{name} requires a one-column vector")
                matrices[name] = [_row(line, 1)[0] for line in numeric]
        index = end
    missing = {"A", "B", "C", "D"} - matrices.keys()
    if missing:
        raise ValueError(f"authoritative matrix fence is missing {', '.join(sorted(missing))}")
    return matrices
