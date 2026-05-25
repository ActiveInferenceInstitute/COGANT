"""Template-facing project contract for the nested COGANT package.

The parent `docxology/template` infrastructure treats an active project as a
directory with top-level `src/`, `tests/`, `scripts/`, and `manuscript/`
surfaces. COGANT intentionally keeps its real Python/Rust package in the
nested `cogant/` directory, so this module gives the template a small,
importable source file while keeping implementation ownership clear.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TemplateContractPaths:
    """Resolved paths that bind the template shell to the real package."""

    project_root: Path
    package_root: Path
    package_import_root: Path
    package_tests: Path
    manuscript_root: Path
    tools_root: Path
    scripts_root: Path
    run_all: Path


def project_root() -> Path:
    """Return the COGANT staging/project root containing this `src/` directory."""
    return Path(__file__).resolve().parents[1]


def contract_paths(root: Path | None = None) -> TemplateContractPaths:
    """Return canonical COGANT paths for template-level checks."""
    base = (root or project_root()).resolve()
    package_root = base / "cogant"
    return TemplateContractPaths(
        project_root=base,
        package_root=package_root,
        package_import_root=package_root / "py" / "cogant",
        package_tests=package_root / "tests",
        manuscript_root=base / "manuscript",
        tools_root=base / "tools",
        scripts_root=base / "scripts",
        run_all=base / "run_all.py",
    )


def validate_contract(root: Path | None = None) -> list[str]:
    """Return missing contract labels; an empty list means the shell is valid."""
    paths = contract_paths(root)
    required_dirs = {
        "package_root": paths.package_root,
        "package_import_root": paths.package_import_root,
        "package_tests": paths.package_tests,
        "manuscript_root": paths.manuscript_root,
        "tools_root": paths.tools_root,
        "scripts_root": paths.scripts_root,
    }
    required_files = {
        "package_pyproject": paths.package_root / "pyproject.toml",
        "run_all": paths.run_all,
        "manuscript_config": paths.manuscript_root / "config.yaml",
        "manuscript_variables": paths.tools_root / "manuscript_vars.py",
        "manuscript_generator": paths.scripts_root / "z_generate_manuscript_variables.py",
    }

    missing = [label for label, path in required_dirs.items() if not path.is_dir()]
    missing.extend(label for label, path in required_files.items() if not path.is_file())
    return sorted(missing)
