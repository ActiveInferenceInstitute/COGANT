#!/usr/bin/env python3
"""Pair every manuscript citation with the claim sentence it supports.

The structural citation audit (``audit_manuscript_citations.py``) proves that
every ``[@key]`` resolves to a BibTeX entry and that every entry is used. It is
deterministic and CI-safe, but it is *structural*: it cannot tell whether a
citation actually supports the sentence it is attached to. A misattribution —
a real paper dropped next to a claim it does not make — passes every structural
gate.

This tool extracts the reviewable raw material for that semantic check: for each
citation occurrence it emits the cited key, the BibTeX title, and the enclosing
claim sentence, as JSONL. A human (or an LLM-judge pass, run out of band) can
then verify each (claim, source) pair. It is deterministic and adds no model
dependency, so it is safe to run anywhere; the judgement step stays external.

Usage::

    python tools/citation_claim_ledger.py                 # all citations -> stdout JSONL
    python tools/citation_claim_ledger.py --keys smithe2024structured,grohe2024similarity
    python tools/citation_claim_ledger.py --output /tmp/citation_claims.jsonl

Exit codes
----------
* ``0`` — ledger written.
* ``1`` — manuscript or bib could not be read.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
BIB_PATH = MANUSCRIPT_DIR / "references.bib"
SKIP_NAMES = frozenset({"AGENTS.md", "README.md", "SYNTAX.md"})

CITATION_RE = re.compile(r"(?<![\w])@([A-Za-z][A-Za-z0-9_:-]+)")
BIB_ENTRY_RE = re.compile(r"@\w+\{([^,\s]+)\s*,(.*?)\n\}", re.S)
TITLE_RE = re.compile(r"title\s*=\s*[{\"](.+?)[}\"]\s*,?\s*$", re.M | re.S)
XREF_PREFIXES = ("sec:", "tbl:", "fig:", "eq:")


def _strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"~~~.*?~~~", "", text, flags=re.S)
    return re.sub(r"`[^`]*`", "", text)


def bib_titles(bib_path: Path) -> dict[str, str]:
    titles: dict[str, str] = {}
    text = bib_path.read_text(encoding="utf-8")
    for key, body in BIB_ENTRY_RE.findall(text):
        m = TITLE_RE.search(body)
        title = re.sub(r"[{}]", "", m.group(1)).strip() if m else ""
        title = re.sub(r"\s+", " ", title)
        titles[key.strip()] = title
    return titles


def _sentences(paragraph: str) -> list[str]:
    flat = re.sub(r"\s+", " ", paragraph).strip()
    # Split on sentence-final punctuation followed by a space + capital/cite.
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\[(])", flat)
    return [p.strip() for p in parts if p.strip()]


def collect(manuscript_dir: Path, titles: dict[str, str], keys: set[str] | None) -> list[dict]:
    records: list[dict] = []
    for path in sorted(manuscript_dir.glob("*.md")):
        if path.name in SKIP_NAMES:
            continue
        raw = path.read_text(encoding="utf-8")
        stripped = _strip_code(raw)
        for para in re.split(r"\n\s*\n", stripped):
            if "@" not in para:
                continue
            for sentence in _sentences(para):
                found = [
                    k for k in CITATION_RE.findall(sentence)
                    if not k.startswith(XREF_PREFIXES)
                ]
                for key in dict.fromkeys(found):  # de-dup, preserve order
                    if keys is not None and key not in keys:
                        continue
                    records.append(
                        {
                            "key": key,
                            "title": titles.get(key, ""),
                            "file": str(path.relative_to(ROOT)),
                            "claim": sentence,
                        }
                    )
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manuscript-dir", type=Path, default=MANUSCRIPT_DIR)
    parser.add_argument("--bib", type=Path, default=BIB_PATH)
    parser.add_argument("--keys", type=str, default=None, help="comma-separated subset of keys")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        titles = bib_titles(args.bib)
        keyset = set(args.keys.split(",")) if args.keys else None
        records = collect(args.manuscript_dir, titles, keyset)
    except OSError as exc:
        print(f"citation-claim ledger failed: {exc}", file=sys.stderr)
        return 1

    lines = [json.dumps(r, ensure_ascii=False) for r in records]
    if args.output:
        args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"citation-claim ledger: {len(records)} (claim, source) pair(s) -> {args.output}")
    else:
        for line in lines:
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
