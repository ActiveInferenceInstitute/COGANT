#!/usr/bin/env python3
"""Audit active docs/manuscript text for stale COGANT v0.5 terminology."""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class BannedPattern:
    name: str
    regex: re.Pattern[str]
    guidance: str
    applies_to: Callable[[Path], bool] | None = None


def _readme_or_agents(path: Path) -> bool:
    return path.name in {"README.md", "AGENTS.md"}


def _active_status_doc(path: Path) -> bool:
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        return False
    return rel in {
        "README.md",
        "AGENTS.md",
        "PROMOTION.md",
        "manuscript/README.md",
        "manuscript/AGENTS.md",
        "cogant/README.md",
        "cogant/AGENTS.md",
        "cogant/docs/roadmap/README.md",
        "cogant/docs/roadmap/overview.md",
        "cogant/docs/roadmap/performance_targets.md",
        "cogant/docs/roadmap/known_limitations_010.md",
        "cogant/docs/reference/implementation_status.md",
    }


def _current_guidance_doc(path: Path) -> bool:
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        return False
    if not rel.startswith("cogant/docs/"):
        return False
    historical_parts = (
        "/evaluation/R&D_LOG.md",
        "/evaluation/RELEASE_NOTES",
        "/evaluation/ROUNDTRIP_EVAL.md",
        "/evaluation/ROUNDTRIP_IMPROVEMENT.md",
        "/evaluation/FINAL_REPORT.md",
        "/evaluation/FIRST_INFERENCE.md",
        "/evaluation/CONSTRAINT_FIX.md",
        "/evaluation/V1.0_READINESS.md",
        "/roadmap/version_",
        "/roadmap/feature_backlog.md",
    )
    return not any(part in rel for part in historical_parts)


def _active_guidance_doc(path: Path) -> bool:
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        return False
    active_roots = (
        "README.md",
        "AGENTS.md",
        "PROMOTION.md",
        "manuscript/README.md",
        "manuscript/AGENTS.md",
        "cogant/README.md",
        "cogant/AGENTS.md",
    )
    return rel in active_roots or _current_guidance_doc(path)


_MANUSCRIPT_BODY_SKIP = {"AGENTS.md", "README.md", "SYNTAX.md", "supplementary.md"}

ROUNDTRIP_LEGACY_CLAIM_RE = re.compile(
    r"\b23\s*/\s*23\s*(?:\(\s*100\s*%\s*\))?\s*"
    r"(?:ROLE_PRESERVED|role[- ]preserved(?:\s+(?:targets|rows))?)\b"
    r"|\b(?:all\s+)?23\s+(?:targets|rows)\s+(?:are|were|as|reported\s+)?"
    r"(?:ROLE_PRESERVED|role[- ]preserved)\b"
    r"|\bROLE_PRESERVED\b[^\n]{0,120}\b23\s*/\s*23\b",
    re.IGNORECASE,
)

ROUNDTRIP_LEGACY_QUALIFIER_RE = re.compile(
    r"\b("
    r"historical|legacy|STALE_LEGACY|not\s+fresh|"
    r"native\s+(?:v0\.6\s+)?ledger|ledger\s+refresh|"
    r"fresh\s+v0\.6\s+(?:release\s+)?evidence|"
    r"current\s+v0\.6\s+metrics\s+classif"
    r")\b",
    re.IGNORECASE,
)

ROUNDTRIP_LEGACY_QUALIFIER_WINDOW = 320
ROUNDTRIP_LEGACY_SKIP_PREFIXES = ("Plans/", "tests/", "tools/")

ROUNDTRIP_ROLE_THRESHOLD_08_RE = re.compile(
    r"(?:"
    r"s_(?:role|\\text\{role\})\s*(?:>=|≥|\\geq)\s*0\.8"
    r"|s_role\s*(?:>=|≥|\\geq)\s*0\.8"
    r"|ROLE_PRESERVED[^\n]{0,120}(?:threshold|tier)[^\n]{0,120}(?:0\.8|80\s*%)"
    r"|(?:0\.8|80\s*%)[^\n]{0,120}(?:threshold|tier)[^\n]{0,120}ROLE_PRESERVED"
    r"|multiset_sim[^\n]{0,120}(?:0\.8|80\s*%)"
    r")",
    re.IGNORECASE,
)

ROUNDTRIP_ROLE_THRESHOLD_08_QUALIFIER_RE = re.compile(
    r"\b("
    r"historical|legacy|STALE_LEGACY|high[- ]confidence|stricter|"
    r"not\s+the\s+public\s+(?:CLI\s+)?default|benchmark\s+notes?|wave[-_ ]?\d+"
    r")\b",
    re.IGNORECASE,
)

ROUNDTRIP_ROLE_THRESHOLD_08_QUALIFIER_WINDOW = 240


def _manuscript_body(path: Path) -> bool:
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        return False
    if path.name in _MANUSCRIPT_BODY_SKIP:
        return False
    return rel.parts[:1] == ("manuscript",) or rel.parts[:2] == ("output", "manuscript")


def _roundtrip_claim_is_qualified(text: str, start: int, end: int) -> bool:
    window_start = max(0, start - ROUNDTRIP_LEGACY_QUALIFIER_WINDOW)
    window_end = min(len(text), end + ROUNDTRIP_LEGACY_QUALIFIER_WINDOW)
    return bool(ROUNDTRIP_LEGACY_QUALIFIER_RE.search(text[window_start:window_end]))


def _skip_roundtrip_legacy_claim_audit(path: Path) -> bool:
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        return False
    return rel.startswith(ROUNDTRIP_LEGACY_SKIP_PREFIXES)


def audit_roundtrip_legacy_claims(file_paths: set[Path], findings: list[str]) -> None:
    """Require legacy 23/23 role-preservation claims to carry provenance.

    The legacy v0.5 JSONL rows do not contain native v0.6 role-score fields, so
    an unqualified "23/23 ROLE_PRESERVED" phrase is evidence laundering. The
    claim may remain in historical release notes or R&D logs only when nearby
    text explicitly labels it historical, legacy, stale, or pending native-ledger
    refresh.
    """
    for file_path in sorted(file_paths):
        if _skip_roundtrip_legacy_claim_audit(file_path):
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for match in ROUNDTRIP_LEGACY_CLAIM_RE.finditer(text):
            if _roundtrip_claim_is_qualified(text, match.start(), match.end()):
                continue
            line_no = text.count("\n", 0, match.start()) + 1
            rel = file_path.relative_to(ROOT) if file_path.is_relative_to(ROOT) else file_path
            snippet = match.group(0).replace("\n", " ")
            findings.append(
                f"{rel}:{line_no}: unqualified-roundtrip-legacy-claim: {snippet!r}. "
                "Label 23/23 role-preservation claims as historical/legacy or cite a native v0.6 ledger."
            )


def _roundtrip_threshold_08_claim_is_qualified(text: str, start: int, end: int) -> bool:
    window_start = max(0, start - ROUNDTRIP_ROLE_THRESHOLD_08_QUALIFIER_WINDOW)
    window_end = min(len(text), end + ROUNDTRIP_ROLE_THRESHOLD_08_QUALIFIER_WINDOW)
    return bool(ROUNDTRIP_ROLE_THRESHOLD_08_QUALIFIER_RE.search(text[window_start:window_end]))


def _roundtrip_threshold_claim_doc(path: Path) -> bool:
    return _manuscript_body(path) or _active_guidance_doc(path)


def audit_roundtrip_threshold_claims(file_paths: set[Path], findings: list[str]) -> None:
    """Reject unqualified stale 0.8 ROLE_PRESERVED threshold claims.

    The public ``cogant roundtrip`` default is ``s_role >= 0.5``. A 0.8 line may
    still appear in historical reports or as a labelled high-confidence analysis
    threshold, but active docs/manuscript text must not call it the default or
    unqualified ROLE_PRESERVED threshold.
    """
    for file_path in sorted(file_paths):
        if _skip_roundtrip_legacy_claim_audit(file_path):
            continue
        if not _roundtrip_threshold_claim_doc(file_path):
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for match in ROUNDTRIP_ROLE_THRESHOLD_08_RE.finditer(text):
            if _roundtrip_threshold_08_claim_is_qualified(
                text, match.start(), match.end()
            ):
                continue
            line_no = text.count("\n", 0, match.start()) + 1
            rel = file_path.relative_to(ROOT) if file_path.is_relative_to(ROOT) else file_path
            snippet = match.group(0).replace("\n", " ")
            findings.append(
                f"{rel}:{line_no}: unqualified-roundtrip-threshold-0.8: {snippet!r}. "
                "Use the public default s_role >= 0.5, or label 0.8 as historical/legacy/high-confidence."
            )


BANNED_PATTERNS = [
    BannedPattern(
        "preview-stubs",
        re.compile(r"\bPreview stubs?\b|\bpreview stubs?\b"),
        "Describe analyze-static/analyze-graph/visualize/export as real commands.",
    ),
    BannedPattern(
        "nineteen-built-in",
        re.compile(r"\b19\s+built[- ]in\b", re.IGNORECASE),
        "Use the live translation-rule count from METRICS.yaml.",
    ),
    BannedPattern(
        "epsilon-similarity-threshold",
        re.compile(r"(?:ε|epsilon)\s*(?:≥|>=|\\geq)\s*0?\.\d+", re.IGNORECASE),
        "Use s_role / role_preservation_score for higher-is-better similarity thresholds.",
    ),
    BannedPattern(
        "role-only-isomorphic-claim",
        re.compile(r"\b23\s*/\s*23\s+ISOMORPHIC\b", re.IGNORECASE),
        "Report role-preserved and strict structural-isomorphism counts separately.",
    ),
    BannedPattern(
        "old-roundtrip-tier-list",
        re.compile(r"\bISOMORPHIC\s*/\s*APPROXIMATE\s*/\s*DIVERGENT\b", re.IGNORECASE),
        "Use STRUCTURALLY_ISOMORPHIC / ROLE_PRESERVED / DRIFT / FAILED.",
    ),
    BannedPattern(
        "current-wave-label",
        re.compile(r"\bwave[-_ ]?(?:20|21|22)[a-z]*\b", re.IGNORECASE),
        "Use feature or date-based language in active README/AGENTS files; reserve wave labels for source history.",
        applies_to=_readme_or_agents,
    ),
    BannedPattern(
        "legacy-server-roundtrip-field",
        re.compile(r"\bisomorphic\s*:\s*bool\b", re.IGNORECASE),
        "Document roundtrip_status, role_preservation_score, and strict structural booleans instead.",
        applies_to=_readme_or_agents,
    ),
    BannedPattern(
        "raw-manuscript-fragment-label",
        re.compile(r"\b08_0[1-4]\b"),
        "Use pandoc-crossref section references such as @sec:08-01-landscape-and-tool-categories.",
        applies_to=_manuscript_body,
    ),
    BannedPattern(
        "manuscript-mkdocs-see-also",
        re.compile(r"^##\s+See also\s+\(MkDocs\)\s*$", re.MULTILINE),
        "Do not end manuscript sections with generic MkDocs navigation blocks; "
        "keep package-doc pointers inline or in Appendix F.",
        applies_to=_manuscript_body,
    ),
    BannedPattern(
        "active-v05-wave21-release-label",
        re.compile(r"\bv0\.5\.0\s*\+\s*wave[-_ ]?21\b", re.IGNORECASE),
        "Active status docs should use the current v0.6 hardening / role-preservation terminology.",
        applies_to=_active_status_doc,
    ),
    BannedPattern(
        "active-roundtrip-epsilon-equals-similarity",
        re.compile(r"\bRound-?trip[^\n|]*ε\s*=\s*1\.0", re.IGNORECASE),
        "Use s_role / role_preservation_score for role preservation and reserve epsilon for divergence.",
        applies_to=_active_status_doc,
    ),
    BannedPattern(
        "manuscript-readme-raw-related-work-fragment-range",
        re.compile(r"forward pointers to `08_01_`(?:–|-|—)`08_04_` subsections"),
        "Describe related-work subsections by title or @sec identifier, not raw fragment ranges.",
        applies_to=lambda path: (
            path.is_relative_to(ROOT)
            and path.relative_to(ROOT).as_posix() == "manuscript/README.md"
        ),
    ),
    BannedPattern(
        "stale-v01x-current-doc",
        re.compile(r"\bv0\.1\.x\b", re.IGNORECASE),
        "Active docs should describe the current v0.6 behaviour or mark older text as historical.",
        applies_to=_current_guidance_doc,
    ),
    BannedPattern(
        "hardcoded-manuscript-section-current-doc",
        re.compile(
            r"\bmanuscript'?s?\s+Section\s+\d+\b|"
            r"\bSection\s+\d+\s+(?:cites|mentions|justifies|argues)\b|"
            r"\b(?:coverage|ablation|related[- ]work)\s+table\s+\(Section\s+\d+",
            re.IGNORECASE,
        ),
        "Use a title, file path, or manuscript cross-reference instead of hard-coded section numbers.",
        applies_to=_active_guidance_doc,
    ),
    BannedPattern(
        "current-doc-role-multiset-isomorphic",
        re.compile(r"\brole[- ]multiset isomorphic\b", re.IGNORECASE),
        "Use role-preserved / role_preservation_score unless strict structural isomorphism is meant.",
        applies_to=_current_guidance_doc,
    ),
]


DEFAULT_SCAN_PATHS = [
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "TODO.md",
    ROOT / "PROMOTION.md",
    ROOT / "tools",
    ROOT / "manuscript",
    ROOT / "output" / "manuscript",
    ROOT / "cogant" / "README.md",
    ROOT / "cogant" / "AGENTS.md",
    ROOT / "cogant" / "docs",
    ROOT / "cogant" / "py" / "cogant" / "cli" / "README.md",
    ROOT / "cogant" / "py" / "cogant" / "server" / "AGENTS.md",
    ROOT / "cogant" / "py" / "cogant" / "translate" / "README.md",
    ROOT / "cogant" / "rust",
    ROOT / "cogant" / "tests",
]


TEXT_SUFFIXES = {".md", ".rst", ".txt", ".ipynb"}

SKIPPED_PATH_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "htmlcov",
    "node_modules",
    "output",
    "site",
    "target",
}


def _skip_path(path: Path) -> bool:
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        rel = path
    if any(part in SKIPPED_PATH_PARTS for part in rel.parts):
        return True
    return rel.as_posix().startswith("cogant/evaluation/eval_repos/")


def _iter_manuscript_body(manuscript_dir: Path) -> list[Path]:
    if not manuscript_dir.is_dir():
        return []
    return [
        path
        for path in sorted(manuscript_dir.glob("*.md"))
        if path.name not in _MANUSCRIPT_BODY_SKIP
    ]


def audit_ir_expansion(findings: list[str]) -> None:
    expansion_re = re.compile(r"\bintermediate representations?\s*\(IR\)", re.IGNORECASE)
    ir_re = re.compile(r"\bIR\b")
    for manuscript_dir in (ROOT / "manuscript", ROOT / "output" / "manuscript"):
        files = _iter_manuscript_body(manuscript_dir)
        if not files:
            continue
        combined_parts: list[str] = []
        offsets: list[tuple[int, Path]] = []
        cursor = 0
        for path in files:
            text = path.read_text(encoding="utf-8")
            offsets.append((cursor, path))
            combined_parts.append(text)
            cursor += len(text) + 1
        combined = "\n".join(combined_parts)
        first_ir = ir_re.search(combined)
        first_expansion = expansion_re.search(combined)
        if first_ir and (first_expansion is None or first_ir.start() < first_expansion.start()):
            file_for_ir = files[0]
            for offset, path in offsets:
                if offset <= first_ir.start():
                    file_for_ir = path
                else:
                    break
            rel = file_for_ir.relative_to(ROOT)
            findings.append(
                f"{rel}:1: ir-before-expansion: first `IR` appears before "
                "`intermediate representation (IR)`."
            )


def iter_files(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for path in paths:
        if not path.exists() or _skip_path(path):
            continue
        if path.is_file():
            if path.suffix.lower() in TEXT_SUFFIXES:
                out.append(path)
            continue
        for child in sorted(path.rglob("*")):
            if _skip_path(child):
                continue
            if child.is_file() and child.suffix.lower() in TEXT_SUFFIXES:
                out.append(child)
    return out


def iter_readme_agents() -> list[Path]:
    out: list[Path] = []
    for path in ROOT.rglob("*"):
        if path.name not in {"README.md", "AGENTS.md"} or not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if _skip_path(path):
            continue
        if rel.as_posix().startswith("cogant/evaluation/eval_repos/"):
            continue
        out.append(path)
    return sorted(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="Optional explicit files/directories")
    args = parser.parse_args(argv)

    scan_paths = args.paths or DEFAULT_SCAN_PATHS
    findings: list[str] = []
    file_paths = set(iter_files([p.expanduser().resolve() for p in scan_paths]))
    if not args.paths:
        file_paths.update(iter_readme_agents())
    for file_path in sorted(file_paths):
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in BANNED_PATTERNS:
            if pattern.applies_to is not None and not pattern.applies_to(file_path):
                continue
            for match in pattern.regex.finditer(text):
                line_no = text.count("\n", 0, match.start()) + 1
                rel = file_path.relative_to(ROOT) if file_path.is_relative_to(ROOT) else file_path
                snippet = match.group(0).replace("\n", " ")
                findings.append(
                    f"{rel}:{line_no}: {pattern.name}: {snippet!r}. {pattern.guidance}"
                )

    audit_roundtrip_legacy_claims(file_paths, findings)
    audit_roundtrip_threshold_claims(file_paths, findings)
    audit_ir_expansion(findings)

    if findings:
        print("Stale docs/manuscript terminology found:", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        return 1
    print("Docs/constants audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
