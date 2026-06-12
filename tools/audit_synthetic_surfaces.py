#!/usr/bin/env python3
"""Classify synthetic-surface terms in project-owned files and artifacts.

This gate does not try to ban every word such as ``fallback`` or ``stub``.
Those words name real COGANT contracts: maximum-entropy degraded-output
defaults, manuscript template variables, public ``.pyi`` type stubs, test
negative controls, and UI empty states. The gate instead rejects occurrences
that are not classified into one of those evidence-backed buckets.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_TERM_RE = re.compile(r"\b(fallback|mock|placeholder|stub)\b", re.IGNORECASE)
TEMPLATE_TOKEN_RE = re.compile(r"\{\{([A-Za-z0-9_]+)\}\}")

ALLOWED_CATEGORIES = {
    "degraded_output",
    "template_variable",
    "type_stub",
    "negative_control",
    "ui_empty_state",
}

DEFAULT_EXCLUDE_PREFIXES = (
    ".git/",
    "cogant/.venv/",
    "cogant/evaluation/eval_repos/",
    "cogant/output/",
    "output/",
)


@dataclass(frozen=True)
class AllowRule:
    """One classification rule for a synthetic-surface term."""

    path: str
    terms: tuple[str, ...]
    category: str
    justification: str
    line: str | None = None

    def __post_init__(self) -> None:
        if self.category not in ALLOWED_CATEGORIES:
            raise ValueError(f"unknown synthetic-surface category: {self.category}")

    def matches(self, rel_path: str, term: str, line_text: str) -> bool:
        if not re.search(self.path, rel_path):
            return False
        if self.terms and term.lower() not in self.terms:
            return False
        return self.line is None or re.search(self.line, line_text, re.IGNORECASE) is not None


@dataclass(frozen=True)
class Occurrence:
    """A classified or unclassified synthetic-surface term occurrence."""

    path: str
    line_no: int
    term: str
    line: str
    category: str | None
    justification: str | None

    @property
    def classified(self) -> bool:
        return self.category is not None


@dataclass(frozen=True)
class AuditFinding:
    """A strict-mode audit finding."""

    path: str
    message: str
    line_no: int | None = None

    def format(self) -> str:
        loc = f"{self.path}:{self.line_no}" if self.line_no is not None else self.path
        return f"{loc}: {self.message}"


ALLOW_RULES: tuple[AllowRule, ...] = (
    AllowRule(
        path=r"^tools/audit_synthetic_surfaces\.py$",
        terms=("fallback", "mock", "placeholder", "stub"),
        category="negative_control",
        justification="this audit tool names the forbidden tokens it checks",
    ),
    AllowRule(
        path=r"^tests/test_audit_synthetic_surfaces\.py$",
        terms=("fallback", "mock", "placeholder", "stub"),
        category="negative_control",
        justification="scanner tests deliberately forge positive and negative controls",
    ),
    AllowRule(
        path=r"^\.github/workflows/.*\.ya?ml$",
        terms=("fallback", "mock", "placeholder", "stub"),
        category="negative_control",
        justification="CI comments name the synthetic-surface terms enforced by this audit",
    ),
    AllowRule(
        path=r"(^tests/|^cogant/tests/)",
        terms=("fallback", "mock", "placeholder", "stub"),
        category="negative_control",
        justification="test files exercise error, degradation, and compatibility paths",
    ),
    AllowRule(
        path=r"\.pyi$",
        terms=("stub", "placeholder"),
        category="type_stub",
        justification="public type stub files are checked by tools/audit_pyi_exports.py",
    ),
    AllowRule(
        path=r"(^tools/audit_pyi_exports\.py$|^tests/test_audit_pyi_exports\.py$|^cogant/docs/faq\.md$|^cogant/docs/roadmap/feature_backlog\.md$|^cogant/py/cogant/.*/AGENTS\.md$)",
        terms=("stub",),
        category="type_stub",
        justification="documentation or audit code for the public type-stub contract",
    ),
    AllowRule(
        path=r"^cogant/evaluation/dataset/generate_dataset\.py$",
        terms=("mock", "placeholder"),
        category="negative_control",
        justification="dataset generator explicitly rejects synthetic rows and placeholder zeros",
    ),
    AllowRule(
        path=r"(^AGENTS\.md$|^PROMOTION\.md$|^scripts/AGENTS\.md$|^scripts/z_generate_manuscript_variables\.py$|^tools/(AGENTS\.md|README\.md|manuscript_vars\.py|inject_manuscript_vars\.py|claim_ledger\.py|audit_folder_docs\.py|regenerate_metrics\.py)$|^manuscript/(AGENTS\.md|README\.md|S06_appendix_source_references\.md|.*\.md)$)",
        terms=("placeholder",),
        category="template_variable",
        justification="registered manuscript template variables are resolved before publication",
    ),
    AllowRule(
        path=r"(^cogant/docs/reference/batch_dashboard\.md$|^cogant/py/cogant/viz/(batch_dashboard|boundary|dashboard/generator|dashboard/assets|bundle_site|pipeline_view|semantic_view)\.py$|^cogant/docs/reference/visualization\.md$)",
        terms=("placeholder",),
        category="ui_empty_state",
        justification="UI text or diagram sentinels represent empty states, not fabricated data",
    ),
    AllowRule(
        path=r"(^cogant/docs/(concepts/roundtrip\.md|evaluation/CALIBRATION\.md|reference/calibration_guide\.md|tutorials/05_gnn_interpretation\.md)$)",
        terms=("placeholder",),
        category="degraded_output",
        justification="maximum-entropy priors and structural defaults are documented degraded-output values",
    ),
    AllowRule(
        path=r"(^\.github/workflows/.*\.ya?ml$|^README\.md$|^THERMO_NUCLEAR_REVIEW\.md$|^TODO\.md$|^cogant/(\.gitignore|AGENTS\.md|CHANGELOG\.md|CONTRIBUTING\.md|Makefile|README\.md|pyproject\.toml)$|^cogant/docs/|^cogant/evaluation/|^cogant/examples/|^cogant/parsers/|^cogant/specs/|^cogant/rust/|^manuscript/|^scripts/|^tools/)",
        terms=("fallback", "mock", "stub"),
        category="degraded_output",
        justification="project documentation, examples, and release notes describe audited degradation or compatibility behavior",
    ),
    AllowRule(
        path=r"^cogant/py/cogant/",
        terms=("fallback", "stub"),
        category="degraded_output",
        justification="production occurrences are runtime degradation, compatibility, or disclosure paths covered by package tests",
    ),
    AllowRule(
        path=r"^cogant/py/cogant/",
        terms=("placeholder",),
        category="ui_empty_state",
        line=r"(empty|no data|\+N more|container|title|values|prior|convention|structural|sentence|svg|D3|formatting)",
        justification="production placeholder wording is limited to empty-state UI or named degraded defaults",
    ),
)


def _run(cmd: Sequence[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def tracked_files(root: Path) -> list[Path]:
    """Return tracked files in ``root`` using Git as the source of truth."""
    result = _run(["git", "ls-files", "-z"], cwd=root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git ls-files failed")
    files: list[Path] = []
    for raw in result.stdout.split("\0"):
        if not raw:
            continue
        if raw.startswith(DEFAULT_EXCLUDE_PREFIXES):
            continue
        files.append(root / raw)
    return files


def project_files(root: Path, *, include_untracked: bool = False) -> list[Path]:
    """Return tracked project files and, in strict mode, untracked source files."""
    files = tracked_files(root)
    if not include_untracked:
        return files
    result = _run(["git", "ls-files", "-z", "--others", "--exclude-standard"], cwd=root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git ls-files --others failed")
    seen = {path.resolve() for path in files}
    for raw in result.stdout.split("\0"):
        if not raw:
            continue
        if raw.startswith(DEFAULT_EXCLUDE_PREFIXES):
            continue
        path = root / raw
        resolved = path.resolve()
        if resolved not in seen:
            files.append(path)
            seen.add(resolved)
    return files


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def _load_registered_template_tokens(root: Path) -> tuple[set[str], list[AuditFinding]]:
    registry_path = root / "tools" / "manuscript_vars.py"
    if not registry_path.exists():
        return set(), [AuditFinding("tools/manuscript_vars.py", "MANUSCRIPT_VARS registry is missing")]
    spec = importlib.util.spec_from_file_location("_cogant_manuscript_vars_audit", registry_path)
    if spec is None or spec.loader is None:
        return set(), [AuditFinding("tools/manuscript_vars.py", "could not load MANUSCRIPT_VARS registry")]
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001
        return set(), [AuditFinding("tools/manuscript_vars.py", f"could not load MANUSCRIPT_VARS: {exc}")]
    registry = getattr(module, "MANUSCRIPT_VARS", None)
    if not isinstance(registry, dict):
        return set(), [AuditFinding("tools/manuscript_vars.py", "MANUSCRIPT_VARS must be a dictionary")]
    return {str(token) for token in registry}, []


def classify_occurrence(
    rel_path: str,
    line_no: int,
    line: str,
    term: str,
    *,
    rules: Sequence[AllowRule] = ALLOW_RULES,
) -> Occurrence:
    for rule in rules:
        if rule.matches(rel_path, term, line):
            return Occurrence(rel_path, line_no, term, line.strip(), rule.category, rule.justification)
    return Occurrence(rel_path, line_no, term, line.strip(), None, None)


def scan_paths(root: Path, paths: Iterable[Path], *, rules: Sequence[AllowRule] = ALLOW_RULES) -> list[Occurrence]:
    """Scan text files for synthetic-surface terms and classify every match."""
    occurrences: list[Occurrence] = []
    for path in sorted(paths):
        if not path.is_file():
            continue
        text = _read_text(path)
        if text is None:
            continue
        rel_path = path.relative_to(root).as_posix()
        for line_no, line in enumerate(text.splitlines(), start=1):
            for match in SYNTHETIC_TERM_RE.finditer(line):
                occurrences.append(
                    classify_occurrence(
                        rel_path,
                        line_no,
                        line,
                        match.group(1),
                        rules=rules,
                    )
                )
    return occurrences


def source_template_findings(root: Path) -> list[AuditFinding]:
    """Fail if renderable manuscript Markdown uses an unregistered template token."""
    registered, findings = _load_registered_template_tokens(root)
    if findings:
        return findings

    manuscript_root = root / "manuscript"
    if not manuscript_root.exists():
        return [AuditFinding("manuscript", "manuscript source directory is missing")]

    for path in sorted(manuscript_root.glob("*.md")):
        text = _read_text(path)
        if text is None:
            continue
        rel = path.relative_to(root).as_posix()
        for line_no, line in enumerate(text.splitlines(), start=1):
            for match in TEMPLATE_TOKEN_RE.finditer(line):
                token = "{{" + match.group(1) + "}}"
                if token not in registered:
                    findings.append(
                        AuditFinding(
                            rel,
                            f"unregistered manuscript template variable: {token}",
                            line_no,
                        )
                    )
    return findings


def registered_template_findings(root: Path) -> list[AuditFinding]:
    """Fail if generated manuscript Markdown still contains template tokens."""
    generated_root = root / "output" / "manuscript"
    if not generated_root.exists():
        return [AuditFinding("output/manuscript", "generated manuscript directory is missing")]

    findings: list[AuditFinding] = []
    for path in sorted(generated_root.glob("*.md")):
        if not path.is_file():
            continue
        text = _read_text(path)
        if text is None:
            continue
        rel = path.relative_to(root).as_posix()
        for line_no, line in enumerate(text.splitlines(), start=1):
            for match in TEMPLATE_TOKEN_RE.finditer(line):
                token = "{{" + match.group(1) + "}}"
                findings.append(
                    AuditFinding(
                        rel,
                        f"template variable remained in generated manuscript Markdown: {token}",
                        line_no,
                    )
                )
    return findings


def _require_matrix_sidecar(path: Path, root: Path) -> list[AuditFinding]:
    rel = path.relative_to(root).as_posix()
    if not path.exists():
        return [AuditFinding(rel, "matrix provenance sidecar is missing")]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [AuditFinding(rel, f"matrix provenance sidecar is unreadable: {exc}")]

    findings: list[AuditFinding] = []
    if data.get("matrix_values_from_artifact") is not True:
        findings.append(AuditFinding(rel, "matrix_values_from_artifact must be true"))
    if data.get("matrix_validation_errors") not in ([], ()):
        findings.append(AuditFinding(rel, "matrix_validation_errors must be empty"))
    if data.get("fallback_panels") not in ([], ()):
        findings.append(AuditFinding(rel, "fallback_panels must be empty for publication matrices"))
    if data.get("degraded_panels") not in ([], ()):
        findings.append(AuditFinding(rel, "degraded_panels must be empty for publication matrices"))
    if not data.get("matrix_source_artifact"):
        findings.append(AuditFinding(rel, "matrix_source_artifact is missing"))
    digest = data.get("matrix_source_artifact_digest") or data.get("source_artifact_digest")
    if not digest:
        findings.append(AuditFinding(rel, "matrix source digest is missing"))

    source_shapes = data.get("source_matrix_shapes")
    if not isinstance(source_shapes, dict) or not {"A", "B", "C", "D"}.issubset(source_shapes):
        findings.append(AuditFinding(rel, "source_matrix_shapes must include A/B/C/D"))

    reducers = data.get("matrix_reducers")
    if not isinstance(reducers, dict) or reducers.get("B", {}).get("method") != "max_over_actions":
        findings.append(AuditFinding(rel, "B reducer metadata must record max_over_actions"))

    panel_sources = data.get("panel_sources") or {}
    if isinstance(panel_sources, dict) and any(value == "shape_proxy" for value in panel_sources.values()):
        findings.append(AuditFinding(rel, "publication matrix panels must not use shape_proxy"))

    alignment = data.get("dimension_alignment")
    if not isinstance(alignment, dict) or not alignment:
        findings.append(AuditFinding(rel, "dimension_alignment is missing"))
    else:
        for key in ("hidden_states_match", "observations_match", "actions_match"):
            if alignment.get(key) is not True:
                findings.append(AuditFinding(rel, f"dimension_alignment.{key} must be true"))

    return findings


def _registered_forward_matrix_sidecars(root: Path) -> tuple[list[Path], list[AuditFinding]]:
    """Return public and source matrix sidecars from the manuscript registry."""
    registry_path = root / "tools" / "manuscript_figure_registry.py"
    if not registry_path.exists():
        return [], [AuditFinding("tools/manuscript_figure_registry.py", "figure registry is missing")]
    spec = importlib.util.spec_from_file_location("_cogant_manuscript_figure_registry_audit", registry_path)
    if spec is None or spec.loader is None:
        return [], [AuditFinding("tools/manuscript_figure_registry.py", "could not load figure registry")]
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001
        return [], [AuditFinding("tools/manuscript_figure_registry.py", f"could not load figure registry: {exc}")]
    figures = getattr(module, "MANUSCRIPT_FIGURES", ())
    for figure in figures:
        if getattr(figure, "key", None) != "forward_abcd_matrices":
            continue
        destination = getattr(figure, "destination", "")
        source = getattr(figure, "source", "")
        paths = [
            root / "output" / "figures" / Path(destination).with_suffix(".figure.json").name,
        ]
        if source:
            paths.append((root / source).with_suffix(".figure.json"))
        return paths, []
    return [], [AuditFinding("tools/manuscript_figure_registry.py", "forward_abcd_matrices registry entry is missing")]


def matrix_provenance_findings(root: Path) -> list[AuditFinding]:
    """Validate public/source matrix sidecars produced by the manuscript path."""
    paths, findings = _registered_forward_matrix_sidecars(root)
    for path in paths:
        findings.extend(_require_matrix_sidecar(path, root))
    return findings


def stub_parity_findings(root: Path, runner: Callable[[Path], list[str]] | None = None) -> list[AuditFinding]:
    """Run the existing type-stub parity gate when type stubs are present."""
    runner = runner or _default_stub_parity_runner
    return [AuditFinding("tools/audit_pyi_exports.py", message) for message in runner(root)]


def _default_stub_parity_runner(root: Path) -> list[str]:
    audit = root / "tools" / "audit_pyi_exports.py"
    if not audit.exists():
        return ["type-stub parity audit is missing"]
    result = _run([sys.executable, str(audit)], cwd=root)
    if result.returncode == 0:
        return []
    output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
    return [output or "type-stub parity audit failed"]


def audit(
    root: Path = ROOT,
    *,
    strict: bool = False,
    rules: Sequence[AllowRule] = ALLOW_RULES,
    stub_runner: Callable[[Path], list[str]] | None = None,
) -> tuple[list[Occurrence], list[AuditFinding]]:
    occurrences = scan_paths(root, project_files(root, include_untracked=strict), rules=rules)
    findings = [
        AuditFinding(o.path, f"unclassified synthetic-surface term {o.term!r}: {o.line}", o.line_no)
        for o in occurrences
        if not o.classified
    ]
    if strict:
        findings.extend(source_template_findings(root))
        findings.extend(registered_template_findings(root))
        findings.extend(matrix_provenance_findings(root))
        findings.extend(stub_parity_findings(root, runner=stub_runner))
    return occurrences, findings


def _category_counts(occurrences: Sequence[Occurrence]) -> dict[str, int]:
    counts = dict.fromkeys(sorted(ALLOWED_CATEGORIES), 0)
    counts["unclassified"] = 0
    for occurrence in occurrences:
        counts[occurrence.category or "unclassified"] += 1
    return counts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit fallback/mock/placeholder/stub occurrences and public provenance gates."
    )
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root to audit.")
    parser.add_argument("--strict", action="store_true", help="Also validate generated public artifacts.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    occurrences, findings = audit(root, strict=args.strict)
    payload = {
        "root": str(root),
        "strict": args.strict,
        "occurrence_count": len(occurrences),
        "category_counts": _category_counts(occurrences),
        "finding_count": len(findings),
        "findings": [finding.format() for finding in findings],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "synthetic-surface audit: "
            f"{payload['occurrence_count']} occurrence(s), "
            f"{payload['finding_count']} finding(s)"
        )
        for category, count in payload["category_counts"].items():
            print(f"  {category}: {count}")
        for finding in findings:
            print(f"ERROR: {finding.format()}", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
