#!/usr/bin/env python3
"""Audit the manuscript robustness table against the generator artifact.

The robustness harness (``cogant/evaluation/robustness/harness.py``) is the
canonical source of truth for the semantics-preserving / sensitivity / negative-
control transform results: it writes
``cogant/evaluation/robustness/robustness_results.json`` and a generated
``robustness_table.md``. The manuscript also carries a hand-authored table
(``{#tbl:robustness-transforms}`` in ``manuscript/08_05_threats_to_validity.md``)
with per-transform *Role similarity* and *Verdict* cells.

The project claim policy states: *no manuscript metric unless injected from a
generator or checked by an audit*. The manuscript robustness numbers were
hand-written and bound to nothing — a RedTeam science-gap finding (2026-06-09).
This auditor closes that hole. It parses the manuscript table and the generator
JSON and fails when any row drifts from the generated result, so the literal
``1.0000`` / ``< 0.99`` / ``ROBUST`` / ``DETECTED`` cells can no longer silently
diverge from what the harness actually measured.

Usage (from the COGANT project root):

    uv run python tools/audit_robustness_table.py
    uv run python tools/audit_robustness_table.py --strict   # also require row order to match

Exit codes:
  0 — every manuscript robustness row agrees with robustness_results.json and the
      transform sets are identical.
  1 — at least one row drifts, is missing, or is extra. Stdout reports the diff.
  2 — a required input (manuscript file or generator JSON) is missing/unparseable.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS_JSON = ROOT / "cogant" / "evaluation" / "robustness" / "robustness_results.json"
MANUSCRIPT_TABLE = ROOT / "manuscript" / "08_05_threats_to_validity.md"

# Marker that identifies the manuscript robustness table block.
TABLE_LABEL = "{#tbl:robustness-transforms}"

# Map manuscript "Class" prose to the harness JSON ``category`` field.
CLASS_TO_CATEGORY = {
    "semantics-preserving": "semantics_preserving",
    "sensitivity probe": "sensitivity_probe",
    "negative control": "negative_control",
}

# Verdicts the harness can emit per category.
VALID_VERDICTS = {"ROBUST", "PRESERVED", "DETECTED"}


@dataclass(frozen=True)
class ManuscriptRow:
    name: str
    klass: str
    similarity_cell: str
    verdict: str
    line_no: int


def _strip_md(cell: str) -> str:
    """Remove inline markdown emphasis/backticks from a table cell."""
    return cell.replace("**", "").replace("`", "").strip()


def _backtick_token(cell: str) -> str | None:
    m = re.search(r"`([A-Za-z0-9_]+)`", cell)
    return m.group(1) if m else None


def _parse_manuscript_rows(text: str) -> list[ManuscriptRow]:
    """Extract the data rows of the robustness table that precedes TABLE_LABEL.

    Assumes the pandoc caption-BELOW-table layout the manuscript uses
    (``: caption {#tbl:...}`` on the line after the table). The auditor walks
    UP from the label to collect the contiguous pipe-table block. If the table
    is ever reformatted to caption-ABOVE, the upward walk finds no rows and the
    audit fails CLOSED (every transform reported "absent") — a spurious failure,
    never a silent pass. Keep the caption below the table, or update this walk.
    """
    lines = text.splitlines()
    label_idx = next(
        (i for i, ln in enumerate(lines) if TABLE_LABEL in ln),
        None,
    )
    if label_idx is None:
        raise ValueError(
            f"robustness table label {TABLE_LABEL!r} not found in {MANUSCRIPT_TABLE.name}"
        )
    # Walk backwards from the label to collect contiguous pipe-table rows.
    rows: list[ManuscriptRow] = []
    i = label_idx
    # The caption line (with the label) may be separated from the table by blank
    # lines; scan upward for the table block.
    block: list[tuple[int, str]] = []
    seen_table = False
    while i >= 0:
        ln = lines[i]
        if ln.lstrip().startswith("|"):
            block.append((i, ln))
            seen_table = True
        elif seen_table and ln.strip() == "":
            # allow no blank lines inside the table; a blank after we started
            # collecting means we've passed the top of the table.
            break
        elif seen_table:
            break
        i -= 1
    for line_no, ln in sorted(block):
        cells = list(ln.split("|"))
        # A markdown row is `| a | b | c | d |` → split gives ['', a, b, c, d, '']
        inner = [c.strip() for c in cells[1:-1]] if len(cells) >= 2 else []
        if len(inner) < 4:
            continue
        # Skip header (`Transform`) and separator (`---`) rows.
        joined = "".join(inner)
        if set(joined) <= set("-: "):
            continue
        name = _backtick_token(inner[0])
        if name is None:
            # header row "Transform | Class | ..." has no backticked token
            continue
        rows.append(
            ManuscriptRow(
                name=name,
                klass=_strip_md(inner[1]).lower(),
                similarity_cell=_strip_md(inner[2]),
                verdict=_strip_md(inner[3]).upper(),
                line_no=line_no + 1,
            )
        )
    return rows


def _load_results() -> dict:
    if not RESULTS_JSON.exists():
        print(f"ERROR: generator artifact missing: {RESULTS_JSON}", file=sys.stderr)
        sys.exit(2)
    try:
        return json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - surfaced to caller
        print(f"ERROR: cannot parse {RESULTS_JSON}: {exc}", file=sys.stderr)
        sys.exit(2)


def audit(*, strict: bool = False) -> list[str]:
    """Return a list of drift messages (empty == pass)."""
    results = _load_results()
    per = results.get("per_transform", {})
    threshold = float(results.get("summary", {}).get("robust_threshold", 0.99)) if isinstance(
        results.get("summary"), dict
    ) else 0.99
    # robust_threshold lives at top level in this schema; fall back to it.
    threshold = float(results.get("robust_threshold", threshold))

    text = MANUSCRIPT_TABLE.read_text(encoding="utf-8")
    rows = _parse_manuscript_rows(text)

    problems: list[str] = []
    seen: set[str] = set()

    for row in rows:
        seen.add(row.name)
        loc = f"{MANUSCRIPT_TABLE.name}:{row.line_no}"
        if row.name not in per:
            problems.append(
                f"{loc}: transform `{row.name}` is in the manuscript table but NOT in "
                f"robustness_results.json (generator never measured it)"
            )
            continue
        gen = per[row.name]
        gen_status = str(gen.get("status", "")).upper()
        gen_category = str(gen.get("category", ""))
        gen_min = float(gen.get("min_similarity", float("nan")))
        gen_mean = float(gen.get("mean_similarity", float("nan")))

        # Verdict must match the generator status exactly.
        if row.verdict not in VALID_VERDICTS:
            problems.append(f"{loc}: unknown verdict {row.verdict!r} (expected one of {sorted(VALID_VERDICTS)})")
        elif row.verdict != gen_status:
            problems.append(
                f"{loc}: `{row.name}` verdict={row.verdict} but generator status={gen_status}"
            )

        # Class/category must agree.
        expected_category = CLASS_TO_CATEGORY.get(row.klass)
        if expected_category is None:
            problems.append(
                f"{loc}: `{row.name}` Class={row.klass!r} not a known class "
                f"(expected one of {sorted(CLASS_TO_CATEGORY)})"
            )
        elif expected_category != gen_category:
            problems.append(
                f"{loc}: `{row.name}` Class={row.klass!r}→{expected_category} but "
                f"generator category={gen_category}"
            )

        # Similarity cell must be consistent with the measured numbers.
        cell = row.similarity_cell
        float_match = re.fullmatch(r"\d+\.\d+", cell)
        if gen_status in {"ROBUST", "PRESERVED"}:
            # A preserving/sensitivity row claims a concrete similarity; it must
            # equal the generated mean (rounded to the cell's precision) and the
            # generated minimum must be at/above threshold.
            if not float_match:
                problems.append(
                    f"{loc}: `{row.name}` is {gen_status} so the similarity cell must be a "
                    f"concrete number (mean={gen_mean:.4f}); got {cell!r}"
                )
            else:
                stated = float(cell)
                if abs(stated - round(gen_mean, 4)) > 1e-4:
                    problems.append(
                        f"{loc}: `{row.name}` similarity cell={stated:.4f} but generator "
                        f"mean_similarity={gen_mean:.4f}"
                    )
                if gen_min < threshold:
                    problems.append(
                        f"{loc}: `{row.name}` is {gen_status} but generator "
                        f"min_similarity={gen_min:.4f} < threshold {threshold}"
                    )
        elif gen_status == "DETECTED":
            # A negative control reports a bound, not a point value. The cell must
            # express "< <threshold>" and the generator min must actually be below it.
            if float_match:
                problems.append(
                    f"{loc}: `{row.name}` is a DETECTED negative control; cell should state a "
                    f"bound like '< {threshold}', not a point value {cell!r}"
                )
            else:
                m = re.search(r"<\s*([0-9.]+)", cell)
                if not m:
                    problems.append(
                        f"{loc}: `{row.name}` DETECTED cell {cell!r} must state a '< X' bound"
                    )
                else:
                    bound = float(m.group(1))
                    if abs(bound - threshold) > 1e-9:
                        problems.append(
                            f"{loc}: `{row.name}` cell bound '< {bound}' != generator "
                            f"robust_threshold {threshold}"
                        )
                    if not gen_min < bound:
                        problems.append(
                            f"{loc}: `{row.name}` claims '< {bound}' but generator "
                            f"min_similarity={gen_min:.4f} is NOT below it"
                        )

    # Every generated transform must appear in the manuscript table.
    missing = sorted(set(per) - seen)
    for name in missing:
        problems.append(
            f"{MANUSCRIPT_TABLE.name}: generator measured `{name}` but it is absent from the "
            f"manuscript robustness table {TABLE_LABEL}"
        )

    if strict:
        # Row order should follow the generator's sorted key order for stability.
        manuscript_order = [r.name for r in rows]
        gen_order = sorted(per)
        if [n for n in manuscript_order if n in per] != [n for n in gen_order if n in seen]:
            problems.append(
                "row order differs from sorted generator order (--strict): "
                f"manuscript={manuscript_order} generator={gen_order}"
            )

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="also require row order to match")
    args = parser.parse_args(argv)

    problems = audit(strict=args.strict)
    if problems:
        print("robustness-table audit: DRIFT detected\n")
        for p in problems:
            print(f"  FAIL  {p}")
        print(
            f"\n{len(problems)} problem(s). The manuscript robustness table must agree with "
            f"{RESULTS_JSON.relative_to(ROOT)} (re-run cogant/evaluation/robustness/harness.py "
            f"to regenerate, then update the table)."
        )
        return 1

    results = _load_results()
    n = len(results.get("per_transform", {}))
    print(
        f"robustness-table audit: PASS — {n} transform row(s) in "
        f"{MANUSCRIPT_TABLE.name} agree with robustness_results.json"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
