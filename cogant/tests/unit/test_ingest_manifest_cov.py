"""Behavioral tests for cogant.ingest.manifest.ManifestParser.

Exercises every manifest format (pyproject.toml, setup.py, package.json,
Cargo.toml, requirements.txt) with real files on disk, plus error
handling and the small private helpers.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cogant.ingest.manifest import Dependency, ManifestParser

# --------------------------- pyproject.toml ----------------------------- #


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text)
    return p


def test_parse_pyproject_extracts_metadata_and_deps(tmp_path):
    """pyproject.toml round-trips name/version/deps and dev extras."""
    pyproject = _write(
        tmp_path,
        "pyproject.toml",
        """
[project]
name = "cogant-sample"
version = "1.2.3"
description = "sample package"
dependencies = ["requests>=2.0", "click"]

[project.optional-dependencies]
dev = ["pytest>=7", "black"]
test = ["pytest-cov"]
other = ["numpy"]
""",
    )
    meta, deps = ManifestParser().parse_pyproject_toml(pyproject)

    assert meta["name"] == "cogant-sample"
    assert meta["version"] == "1.2.3"
    assert meta["description"] == "sample package"

    dep_names = {d.name for d in deps}
    assert {"requests", "click", "pytest", "black", "pytest-cov", "numpy"}.issubset(dep_names)

    # dev extras are flagged
    dev_names = {d.name for d in deps if d.is_dev}
    assert {"pytest", "black", "pytest-cov"}.issubset(dev_names)

    # non-dev extras (other → numpy) are NOT flagged
    numpy_dep = next(d for d in deps if d.name == "numpy")
    assert numpy_dep.is_dev is False


def test_parse_pyproject_missing_file_logs_and_returns_empty(tmp_path):
    """A missing file is handled gracefully (warning, empty results)."""
    meta, deps = ManifestParser().parse_pyproject_toml(tmp_path / "missing.toml")
    assert meta == {}
    assert deps == []


# --------------------------- setup.py ----------------------------------- #


def test_parse_setup_py_extracts_name_version_and_install_requires(tmp_path):
    """setup.py regex parser pulls name/version/deps and dev extras."""
    setup_py = _write(
        tmp_path,
        "setup.py",
        """
from setuptools import setup

setup(
    name="my-pkg",
    version="0.9.0",
    description="a description",
    install_requires=[
        "requests>=2.0",
        "click",
    ],
    extras_require={
        "dev": ["pytest", "black"],
        "test": ["coverage"],
    },
)
""",
    )
    meta, deps = ManifestParser().parse_setup_py(setup_py)
    assert meta["name"] == "my-pkg"
    assert meta["version"] == "0.9.0"
    assert meta["description"] == "a description"

    names = {d.name for d in deps}
    assert {"requests", "click", "pytest", "black", "coverage"}.issubset(names)

    dev = {d.name for d in deps if d.is_dev}
    assert {"pytest", "black", "coverage"}.issubset(dev)


def test_parse_setup_py_missing_file_returns_empty(tmp_path):
    """Parsing a non-existent setup.py yields empty outputs, not an error."""
    meta, deps = ManifestParser().parse_setup_py(tmp_path / "no_setup.py")
    assert meta == {}
    assert deps == []


# --------------------------- requirements.txt --------------------------- #


def test_parse_requirements_txt_skips_comments_and_blanks(tmp_path):
    """Blank lines and '#' comments are stripped; everything else parsed."""
    req = _write(
        tmp_path,
        "requirements.txt",
        """
# This is a comment
requests>=2.0

click==8.1.0

# another comment
typing-extensions
""",
    )
    deps = ManifestParser().parse_requirements_txt(req)
    names = {d.name for d in deps}
    assert names == {"requests", "click", "typing-extensions"}

    click = next(d for d in deps if d.name == "click")
    assert click.version == "==8.1.0"


def test_parse_requirements_txt_missing_file_returns_empty(tmp_path):
    """Missing requirements.txt yields [] without raising."""
    assert ManifestParser().parse_requirements_txt(tmp_path / "no.txt") == []


# --------------------------- package.json ------------------------------- #


def test_parse_package_json_extracts_deps_and_dev_deps(tmp_path):
    """package.json populates metadata, dependencies, and devDependencies."""
    pkg = _write(
        tmp_path,
        "package.json",
        json.dumps(
            {
                "name": "my-app",
                "version": "0.0.1",
                "description": "a node app",
                "dependencies": {"express": "^4.18.0", "lodash": "4.17.21"},
                "devDependencies": {"jest": "^29.0.0"},
            }
        ),
    )
    meta, deps = ManifestParser().parse_package_json(pkg)
    assert meta["name"] == "my-app"
    assert meta["version"] == "0.0.1"

    by_name = {d.name: d for d in deps}
    assert by_name["express"].version == "^4.18.0"
    assert by_name["express"].is_dev is False
    assert by_name["jest"].is_dev is True


def test_parse_package_json_invalid_file_handles_gracefully(tmp_path):
    """A malformed JSON file is caught by the try/except and returns ({}, [])."""
    bad = _write(tmp_path, "package.json", "{not json")
    meta, deps = ManifestParser().parse_package_json(bad)
    assert meta == {}
    assert deps == []


# --------------------------- Cargo.toml --------------------------------- #


def test_parse_cargo_toml_handles_string_and_table_deps(tmp_path):
    """Cargo.toml dependencies can be strings or tables; both work."""
    cargo = _write(
        tmp_path,
        "Cargo.toml",
        """
[package]
name = "my-crate"
version = "0.1.0"
description = "a rust crate"

[dependencies]
serde = "1.0"
tokio = { version = "1.0", features = ["full"] }

[dev-dependencies]
criterion = "0.5"
""",
    )
    meta, deps = ManifestParser().parse_cargo_toml(cargo)
    assert meta["name"] == "my-crate"
    assert meta["version"] == "0.1.0"

    by_name = {d.name: d for d in deps}
    assert by_name["serde"].version == "1.0"
    assert by_name["tokio"].version == "1.0"
    assert by_name["criterion"].is_dev is True


def test_parse_cargo_toml_missing_file_returns_empty(tmp_path):
    meta, deps = ManifestParser().parse_cargo_toml(tmp_path / "no.toml")
    assert meta == {}
    assert deps == []


# --------------------------- parse() dispatcher ------------------------- #


def test_parse_dispatcher_handles_all_known_types(tmp_path):
    """parse() routes to the appropriate format-specific parser."""
    parser = ManifestParser()

    # pyproject.toml
    py = _write(tmp_path, "pyproject.toml", '[project]\nname = "a"\nversion = "0.1"\n')
    meta, _ = parser.parse(py)
    assert meta["name"] == "a"

    # package.json
    js = _write(tmp_path, "package.json", json.dumps({"name": "b"}))
    meta, _ = parser.parse(js)
    assert meta["name"] == "b"

    # Cargo.toml
    rs = _write(tmp_path, "Cargo.toml", '[package]\nname = "c"\nversion = "0.1"\n')
    meta, _ = parser.parse(rs)
    assert meta["name"] == "c"

    # setup.py
    sp = _write(tmp_path, "setup.py", 'setup(name="d", version="1")')
    meta, _ = parser.parse(sp)
    assert meta["name"] == "d"

    # requirements.txt returns ({}, [Dependency])
    rt = _write(tmp_path, "requirements.txt", "requests\n")
    meta, deps = parser.parse(rt)
    assert meta == {}
    assert deps and deps[0].name == "requests"


def test_parse_unknown_filename_raises_value_error(tmp_path):
    """An unrecognised filename raises ValueError."""
    unknown = _write(tmp_path, "my_weird_file.xyz", "stuff")
    with pytest.raises(ValueError):
        ManifestParser().parse(unknown)


# --------------------------- private helpers ---------------------------- #


def test_parse_requirement_line_basic_and_versioned():
    """_parse_requirement_line pulls name and version specifier."""
    d = ManifestParser._parse_requirement_line("requests>=2.0,<3.0")
    assert d is not None
    assert d.name == "requests"
    assert d.version is not None and ">=2.0" in d.version

    d2 = ManifestParser._parse_requirement_line("click")
    assert d2 is not None and d2.name == "click"

    # Empty lines / whitespace-only return None
    assert ManifestParser._parse_requirement_line("") is None
    assert ManifestParser._parse_requirement_line("   ") is None


def test_parse_requirement_line_editable_local_dependency():
    """'-e ./path' is recognised as a local dependency."""
    d = ManifestParser._parse_requirement_line("-e ./local-pkg")
    assert d is not None
    assert d.is_local is True


def test_parse_requirements_string_splits_on_commas():
    """_parse_requirements_string handles comma-separated setup.py lists."""
    deps = ManifestParser._parse_requirements_string('"requests>=2.0", "click"')
    names = {d.name for d in deps}
    assert names == {"requests", "click"}


def test_parse_requirement_list_from_plain_list():
    """_parse_requirement_list walks each entry through _parse_requirement_line."""
    deps = ManifestParser._parse_requirement_list(["requests", "click>=7"])
    names = {d.name for d in deps}
    assert names == {"requests", "click"}


def test_dependency_dataclass_defaults():
    """Dependency defaults reflect non-dev, non-local, no-version."""
    d = Dependency(name="foo")
    assert d.version is None
    assert d.is_dev is False
    assert d.is_local is False
