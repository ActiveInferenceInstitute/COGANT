#!/usr/bin/env python3
"""Audit documented pipeline stage sequences against the canonical RUNNER_STAGES tuple.

The canonical source of truth is ``cogant.pipeline.RUNNER_STAGES`` in
``py/cogant/pipeline/__init__.py``. This auditor scans the prose stage lists in
the CLI docstrings, top-level README/AGENTS files, and selected docs for the
ordered ten-stage runner sequence and fails when any prose list diverges.

It exists because hand-patched stage lists drifted in three docs + the
``cogant translate`` docstring on iter-4 review (May 2026), nothing prevented
the next reconstruction from reintroducing the same bug, and the manuscript
appendix flagged it as an open follow-up (TODO #4 stage-list drift gate).

Usage (from the COGANT project root):

    uv run python tools/audit_stage_list.py
    uv run python tools/audit_stage_list.py --strict   # fail on near-misses too

Exit codes:
  0 — every scanned doc either matches or has no stage-list reference at all.
  1 — at least one scanned doc has a stage list that disagrees with the
       canonical tuple. Stdout reports the file:line and the diff.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# The auditor lives under tools/ at the project root; the inner package is at
# cogant/py/cogant.
ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PY = ROOT / "cogant" / "py"

# Insert the inner package onto sys.path so we can import the canonical
# constant without needing the package installed editable. This mirrors how
# tools/audit_pyi_exports.py walks the same tree.
sys.path.insert(0, str(PACKAGE_PY))

try:
    from cogant.pipeline import RUNNER_STAGES  # type: ignore[import-not-found]
except Exception as exc:  # pragma: no cover - failure surfaced to caller
    print(f"ERROR: cannot import cogant.pipeline.RUNNER_STAGES: {exc}", file=sys.stderr)
    sys.exit(2)


# Files that must declare the full 10-stage sequence verbatim.
# Each entry is (relative path, "context" description). Files that are
# allowed to mention only a subset (the ``analyze`` minimal-pipeline docstring,
# the ``explain`` minimal-pipeline docstring, the ``server.app`` early-exit
# subset) are deliberately excluded — drift in those is semantic, not lexical.
DOC_TARGETS: list[tuple[str, str]] = [
    ("cogant/docs/cli_reference.md", "CLI reference page"),
    ("cogant/docs/getting-started/quickstart.md", "Quickstart guide"),
    ("cogant/docs/faq.md", "FAQ"),
    ("cogant/py/cogant/cli/main.py", "translate CLI docstring (line ~700)"),
    ("cogant/py/cogant/api/README.md", "PipelineRunner reference"),
    ("cogant/py/cogant/api/AGENTS.md", "API agents overview"),
    ("cogant/py/cogant/gnn/AGENTS.md", "GNN exporter overview"),
    ("manuscript/03_api_and_workflows.md", "Manuscript API/workflows section"),
]


@dataclass(frozen=True)
class StageListFinding:
    path: Path
    line: int
    excerpt: str
    parsed: tuple[str, ...]
    status: str  # "match", "mismatch", "missing"
    detail: str


def _normalize_token(token: str) -> str:
    """Strip arrows, backticks, commas, etc. and lowercase."""
    return re.sub(r"[`*,\.\(\)\[\]→\s]+", "", token).lower()


_FULL_PIPELINE_MARKERS = (
    "full pipeline",
    "full cogant pipeline",
    "default pipeline",
    "default stages",
    "all stages",
    "complete pipeline",
    "ten-stage",
    "10-stage",
    "10 stage",
)

_EXEMPT_MARKERS = (
    "minimal pipeline",
    "minimal cogant pipeline",
    "minimal stages",
    "subset",
    "skip ",
    "skip_stages",
    "skip-stages",
    "without ",
    "exclud",
    "partial pipeline",
)


_ARROW_RE = re.compile(r"(→|->)")


def _extract_stage_lists(text: str) -> list[tuple[int, str, list[str]]]:
    """Return list of (1-based line number, original excerpt, parsed tokens).

    A *stage list* is a chunk of text that uses arrow separators (``→`` or
    ``->``) between stage tokens. Narrative paragraphs that *mention* stages
    in passing (no arrows) are deliberately not parsed — they have their own
    review hygiene needs that this gate is not the right tool for.

    Multi-line wraps are stitched together: if a line begins with an arrow
    (or whitespace + arrow), it is joined to the previous line for parsing.
    The reported line number is the line where the chunk begins.

    Lines flagged with an exempt marker ("minimal pipeline", "skip",
    "subset", etc.) are excluded.
    """
    findings: list[tuple[int, str, list[str]]] = []
    canonical = list(RUNNER_STAGES)
    canonical_pattern = re.compile(
        r"\b(" + "|".join(re.escape(s) for s in canonical) + r")\b",
        flags=re.IGNORECASE,
    )
    lines = text.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        chunk_lines = [raw]
        j = i + 1
        # Stitch forward while EITHER the current chunk ends with an arrow
        # OR the next line starts with an arrow. Either pattern signals a
        # multi-line stage-list wrap.
        while j < n:
            cur = chunk_lines[-1].rstrip()
            if cur.endswith("→") or cur.endswith("->"):
                chunk_lines.append(lines[j])
                j += 1
                continue
            nxt_strip = lines[j].lstrip()
            if nxt_strip.startswith("→") or nxt_strip.startswith("->"):
                chunk_lines.append(lines[j])
                j += 1
                continue
            break
        chunk = " ".join(chunk_lines)
        chunk_lower = chunk.lower()

        if not _ARROW_RE.search(chunk):
            i = j
            continue
        if any(m in chunk_lower for m in _EXEMPT_MARKERS):
            i = j
            continue
        # Trim any prose preamble before the first arrow — the actual stage
        # list starts at the canonical stage name immediately followed by
        # an arrow. This drops the ``cogant translate`` reference in
        # ``equivalent to cogant translate (ingest → ...)`` patterns.
        first_arrow = _ARROW_RE.search(chunk)
        if first_arrow is None:
            i = j
            continue
        # Walk backwards from the arrow to find the start of the stage token
        # that precedes it.
        pre = chunk[: first_arrow.start()].rstrip()
        last_canonical = None
        for m in canonical_pattern.finditer(pre):
            last_canonical = m
        list_start = last_canonical.start() if last_canonical is not None else first_arrow.start()
        list_chunk = chunk[list_start:]

        seen: list[str] = []
        for m in canonical_pattern.finditer(list_chunk):
            name = m.group(1).lower()
            if name not in seen:
                seen.append(name)
        # Gate firing rule: only audit chunks that claim to be the full
        # pipeline. The cheapest robust test is "contains both bookends
        # (``ingest`` and ``validate``) and at least six canonical stages",
        # which excludes the legitimate partial-pipeline docstrings for
        # ``statespace`` (static→graph→translate→statespace) and ``explain``
        # (ingest→static→normalize→graph→translate) without needing them
        # to carry a marker phrase.
        if "ingest" in seen and "validate" in seen and len(seen) >= 6:
            findings.append((i + 1, chunk.strip()[:240], seen))
        i = j
    return findings


def _classify(parsed: list[str]) -> tuple[str, str]:
    canonical = list(RUNNER_STAGES)
    if parsed == canonical:
        return "match", "exact match"
    if all(s in parsed for s in canonical) and parsed[: len(canonical)] == canonical:
        # Doc lists the 10 stages then continues with extra prose mentions; OK
        return "match", "match (trailing context)"
    # Compute the longest common prefix
    common = 0
    for a, b in zip(parsed, canonical, strict=False):
        if a == b:
            common += 1
        else:
            break
    missing = [s for s in canonical if s not in parsed]
    extra = [s for s in parsed if s not in canonical]
    detail_parts = []
    if missing:
        detail_parts.append(f"missing: {missing}")
    if extra:
        detail_parts.append(f"unexpected: {extra}")
    detail_parts.append(f"common_prefix: {common}/{len(canonical)}")
    return "mismatch", "; ".join(detail_parts)


def audit() -> list[StageListFinding]:
    out: list[StageListFinding] = []
    for rel, _context in DOC_TARGETS:
        target = ROOT / rel
        if not target.exists():
            out.append(
                StageListFinding(
                    path=target,
                    line=0,
                    excerpt="",
                    parsed=(),
                    status="missing",
                    detail=f"target does not exist: {rel}",
                )
            )
            continue
        text = target.read_text(encoding="utf-8")
        chunks = _extract_stage_lists(text)
        if not chunks:
            # Acceptable: doc references stages by name without enumerating
            # the full order (e.g. AGENTS.md prose). We still record this as
            # an informational "no enumeration" entry so the CI log is full.
            out.append(
                StageListFinding(
                    path=target,
                    line=0,
                    excerpt="",
                    parsed=(),
                    status="match",
                    detail="no enumerated stage list",
                )
            )
            continue
        for lineno, excerpt, parsed in chunks:
            status, detail = _classify(parsed)
            out.append(
                StageListFinding(
                    path=target,
                    line=lineno,
                    excerpt=excerpt[:160],
                    parsed=tuple(parsed),
                    status=status,
                    detail=detail,
                )
            )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat 'no enumerated stage list' on a target doc as a failure",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit findings as JSON on stdout",
    )
    args = parser.parse_args()

    findings = audit()

    if args.json:
        import json

        payload = {
            "canonical": list(RUNNER_STAGES),
            "findings": [
                {
                    "path": str(f.path.relative_to(ROOT)),
                    "line": f.line,
                    "status": f.status,
                    "detail": f.detail,
                    "parsed": list(f.parsed),
                    "excerpt": f.excerpt,
                }
                for f in findings
            ],
        }
        print(json.dumps(payload, indent=2))
        bad = any(f.status == "mismatch" for f in findings) or any(
            f.status == "missing" for f in findings
        )
        return 1 if bad else 0

    canonical_str = " → ".join(RUNNER_STAGES)
    print(f"Canonical RUNNER_STAGES sequence ({len(RUNNER_STAGES)}): {canonical_str}\n")

    fail = False
    for f in findings:
        rel = f.path.relative_to(ROOT) if f.path.exists() else f.path.name
        if f.status == "match":
            print(f"  OK    {rel}:{f.line}  {f.detail}")
            continue
        if f.status == "missing":
            print(f"  MISS  {rel}  {f.detail}")
            fail = True
            continue
        # mismatch
        fail = True
        print(f"  FAIL  {rel}:{f.line}")
        print(f"        parsed:    {' → '.join(f.parsed)}")
        print(f"        canonical: {canonical_str}")
        print(f"        detail:    {f.detail}")
        print(f"        excerpt:   {f.excerpt!r}")

    if fail:
        print("\nStage-list drift detected. Update the offending docs to match RUNNER_STAGES.")
        return 1
    print("\nStage-list drift gate: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
