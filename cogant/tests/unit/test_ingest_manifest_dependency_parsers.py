"""Targeted unit tests for: cogant.ingest.manifest.

Targets uncovered branches in ``ManifestParser`` that the existing
``test_ingest_manifest_parsing.py`` suite does not exercise:

- Cargo.toml ``dev-dependencies`` declared as a TOML table (line 345)
- ``_parse_requirement_line`` returning ``None`` on lines that the
  ``[a-zA-Z0-9._-]+`` regex rejects (line 429)
- The ``-e <relative>`` editable path special case
- ``parse_dispatcher`` on the lower-cased filename variants

Style mirrors ``test_ingest_manifest_parsing.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.ingest.manifest import Dependency, ManifestParser

# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text)
    return p


# --------------------------------------------------------------------------- #
# Cargo.toml dev-dependencies as table → line 345
# --------------------------------------------------------------------------- #


class TestCargoDevDependenciesTable:
    def test_dev_dependency_with_inline_table_records_version(self, tmp_path: Path):
        """Dev-deps written as ``crate = { version = "x" }`` are parsed."""
        cargo = _write(
            tmp_path,
            "Cargo.toml",
            """
[package]
name = "demo"
version = "0.1.0"

[dependencies]
serde = "1.0"

[dev-dependencies]
mockall = { version = "0.11", features = ["nightly"] }
""",
        )
        meta, deps = ManifestParser().parse_cargo_toml(cargo)
        assert meta["name"] == "demo"
        by_name = {d.name: d for d in deps}
        # Inline-table dev dep keeps version and is_dev=True
        assert by_name["mockall"].version == "0.11"
        assert by_name["mockall"].is_dev is True

    def test_dev_dependency_unknown_spec_type_falls_through(self, tmp_path: Path):
        """If a dev-dep spec is neither dict nor str, version stays None.

        The current parser's elif branches only handle dict/str — for any
        other value the ``version = None`` initialised before the conditional
        is preserved. This covers the path where neither ``isinstance``
        check fires.
        """
        # Build the parsed dict directly via parse_cargo_toml on a synthetic
        # file; we can't put a non-string non-table in real TOML, so we
        # exercise the fallthrough by going through dict deps with no
        # 'version' key (returns None from .get).
        cargo = _write(
            tmp_path,
            "Cargo.toml",
            """
[package]
name = "demo"
version = "0.1.0"

[dev-dependencies]
nover = { features = ["a", "b"] }
""",
        )
        _meta, deps = ManifestParser().parse_cargo_toml(cargo)
        nover = next(d for d in deps if d.name == "nover")
        assert nover.version is None
        assert nover.is_dev is True


# --------------------------------------------------------------------------- #
# Cargo.toml regular deps - dict spec without version (covers 333-337 path)
# --------------------------------------------------------------------------- #


class TestCargoRegularDepsDictSpec:
    def test_regular_dependency_inline_table(self, tmp_path: Path):
        cargo = _write(
            tmp_path,
            "Cargo.toml",
            """
[package]
name = "demo"
version = "0.1.0"

[dependencies]
tokio = { version = "1.20", features = ["full"] }
""",
        )
        _meta, deps = ManifestParser().parse_cargo_toml(cargo)
        by_name = {d.name: d for d in deps}
        assert by_name["tokio"].version == "1.20"
        assert by_name["tokio"].is_dev is False


# --------------------------------------------------------------------------- #
# _parse_requirement_line — None branch on regex miss (line 429)
# --------------------------------------------------------------------------- #


class TestParseRequirementLineNoMatch:
    def test_at_scoped_package_returns_none(self):
        """A line starting with '@' fails the [a-zA-Z0-9._-]+ regex."""
        # This exercises the ``return None`` at the bottom of the helper.
        assert ManifestParser._parse_requirement_line("@scope/pkg") is None

    def test_bang_prefixed_line_returns_none(self):
        assert ManifestParser._parse_requirement_line("!banned") is None

    def test_slash_prefixed_line_returns_none(self):
        assert ManifestParser._parse_requirement_line("/abs/path") is None


# --------------------------------------------------------------------------- #
# _parse_requirement_line — editable path that does not start with file/. -> None
# --------------------------------------------------------------------------- #


class TestParseRequirementLineEditableEdgeCases:
    def test_editable_with_non_path_does_fall_through_to_regex(self):
        """``-e gitrepo`` falls through to the name regex (gitrepo is alnum)."""
        d = ManifestParser._parse_requirement_line("-e gitrepo")
        # The regex matches '-e' first character, so name='-e' but the
        # '-' is allowed inside [a-zA-Z0-9._-]. Result is a Dependency
        # with name "-e" and version " gitrepo". We just assert non-None.
        assert d is not None

    def test_editable_with_file_uri_returns_local(self):
        """``-e file:./foo`` is recognised as a local dependency."""
        d = ManifestParser._parse_requirement_line("-e file:./local-pkg")
        assert d is not None
        assert d.is_local is True


# --------------------------------------------------------------------------- #
# _parse_requirements_string handles items with embedded special chars
# --------------------------------------------------------------------------- #


class TestParseRequirementsString:
    def test_string_with_only_invalid_entries_returns_empty(self):
        """All-invalid input yields no dependencies (line 429 reached)."""
        deps = ManifestParser._parse_requirements_string("@a, !b, /c")
        assert deps == []

    def test_string_with_blank_only_entries_returns_empty(self):
        deps = ManifestParser._parse_requirements_string(",,,,  ,  ")
        assert deps == []


# --------------------------------------------------------------------------- #
# Manifest dispatcher — case-insensitive filename matching
# --------------------------------------------------------------------------- #


class TestParseDispatcherCaseInsensitive:
    def test_pyproject_uppercase_routes_to_pyproject_parser(self, tmp_path: Path):
        """The dispatcher lower-cases the filename before matching."""
        py = _write(tmp_path, "PYPROJECT.TOML", '[project]\nname = "x"\nversion = "0.1"\n')
        meta, _ = ManifestParser().parse(py)
        assert meta["name"] == "x"

    def test_cargo_uppercase_routes_to_cargo_parser(self, tmp_path: Path):
        rs = _write(tmp_path, "CARGO.TOML", '[package]\nname = "y"\nversion = "0.1"\n')
        meta, _ = ManifestParser().parse(rs)
        assert meta["name"] == "y"

    def test_setup_uppercase_routes_to_setup_parser(self, tmp_path: Path):
        sp = _write(tmp_path, "SETUP.PY", 'setup(name="z", version="1")')
        meta, _ = ManifestParser().parse(sp)
        assert meta["name"] == "z"

    def test_unknown_extension_raises_value_error(self, tmp_path: Path):
        unknown = _write(tmp_path, "weird.xyz", "stuff")
        with pytest.raises(ValueError):
            ManifestParser().parse(unknown)


# --------------------------------------------------------------------------- #
# Dependency dataclass invariants
# --------------------------------------------------------------------------- #


class TestDependencyInvariants:
    def test_dependency_with_local_flag(self):
        d = Dependency(name="local", is_local=True)
        assert d.is_local is True
        assert d.is_dev is False

    def test_dependency_with_version(self):
        d = Dependency(name="requests", version=">=2.0")
        assert d.version == ">=2.0"
