from __future__ import annotations

from pathlib import Path

from cogant_template_contract import contract_paths, project_root, validate_contract


def test_project_root_points_to_cogant_staging_root() -> None:
    root = project_root()

    assert root.name == "cogant"
    assert (root / "AGENTS.md").is_file()
    assert (root / "cogant" / "pyproject.toml").is_file()


def test_contract_paths_map_to_nested_package_layout() -> None:
    paths = contract_paths()

    assert paths.package_root == paths.project_root / "cogant"
    assert paths.package_import_root == paths.package_root / "py" / "cogant"
    assert paths.package_tests == paths.package_root / "tests"
    assert paths.manuscript_root == paths.project_root / "manuscript"
    assert paths.run_all == paths.project_root / "run_all.py"


def test_validate_contract_passes_for_current_checkout() -> None:
    assert validate_contract() == []


def test_validate_contract_reports_missing_labels(tmp_path: Path) -> None:
    (tmp_path / "cogant" / "py" / "cogant").mkdir(parents=True)
    (tmp_path / "manuscript").mkdir()

    missing = validate_contract(tmp_path)

    assert "package_tests" in missing
    assert "run_all" in missing
    assert "tools_root" in missing
