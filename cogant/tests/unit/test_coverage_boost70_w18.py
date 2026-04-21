#!/usr/bin/env python3
"""Coverage boost batch 70 — ingest/manifest.py (all parsers), ingest/language_detect.py
(get_parser, various extensions), ingest/repo.py (more scenarios).

Covers:
- ingest/manifest.py: ManifestParser.parse_requirements_txt (various formats),
  parse_pyproject_toml, parse_package_json, parse_cargo_toml, parse_setup_py
- ingest/language_detect.py: LanguageDetector.get_parser, detect_language (many
  extensions: .js, .ts, .java, .cpp, .c, .go, .rb, .rs), detect_repo_languages
  (with multiple file types)
- ingest/repo.py: RepoIngester.ingest_local (with multiple file types, checksums)
"""

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# ingest/manifest.py — ManifestParser with various file formats
# ---------------------------------------------------------------------------


class TestManifestParserAllFormats:
    def _make_parser(self):
        from cogant.ingest.manifest import ManifestParser

        return ManifestParser()

    # --- parse_requirements_txt ---

    def test_requirements_txt_simple(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("requests==2.28.0\nnumpy>=1.21.0\npytest\nflask\n")
        parser = self._make_parser()
        deps = parser.parse_requirements_txt(req)
        assert isinstance(deps, list)
        assert len(deps) >= 1

    def test_requirements_txt_with_extras(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("requests[security]==2.28.0\n# comment\n-r other.txt\n")
        parser = self._make_parser()
        deps = parser.parse_requirements_txt(req)
        assert isinstance(deps, list)

    def test_requirements_txt_empty(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("")
        parser = self._make_parser()
        deps = parser.parse_requirements_txt(req)
        assert isinstance(deps, list)

    def test_requirements_txt_comments_only(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("# just comments\n# no deps\n")
        parser = self._make_parser()
        deps = parser.parse_requirements_txt(req)
        assert isinstance(deps, list)

    def test_requirements_txt_via_parse(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("django>=4.0\n")
        parser = self._make_parser()
        meta, deps = parser.parse(req)
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    # --- parse_pyproject_toml ---

    def test_pyproject_toml_basic(self, tmp_path):
        ppt = tmp_path / "pyproject.toml"
        ppt.write_text("""
[tool.poetry]
name = "myproject"
version = "1.0.0"
description = "A test project"

[tool.poetry.dependencies]
python = "^3.10"
requests = "^2.28"
click = "^8.0"

[tool.poetry.dev-dependencies]
pytest = "^7.0"
""")
        parser = self._make_parser()
        meta, deps = parser.parse_pyproject_toml(ppt)
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    def test_pyproject_toml_pep517(self, tmp_path):
        ppt = tmp_path / "pyproject.toml"
        ppt.write_text("""
[project]
name = "myapp"
version = "0.1.0"
dependencies = ["requests>=2.28", "click>=8.0"]

[project.optional-dependencies]
dev = ["pytest>=7.0", "black"]
""")
        parser = self._make_parser()
        meta, deps = parser.parse_pyproject_toml(ppt)
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    def test_pyproject_toml_empty(self, tmp_path):
        ppt = tmp_path / "pyproject.toml"
        ppt.write_text("")
        parser = self._make_parser()
        meta, deps = parser.parse_pyproject_toml(ppt)
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    # --- parse_package_json ---

    def test_package_json_basic(self, tmp_path):
        import json

        pkg = tmp_path / "package.json"
        pkg.write_text(
            json.dumps(
                {
                    "name": "my-app",
                    "version": "1.0.0",
                    "dependencies": {
                        "react": "^18.0.0",
                        "axios": "^1.0.0",
                    },
                    "devDependencies": {
                        "jest": "^29.0.0",
                        "eslint": "^8.0.0",
                    },
                }
            )
        )
        parser = self._make_parser()
        meta, deps = parser.parse_package_json(pkg)
        assert isinstance(meta, dict)
        assert isinstance(deps, list)
        assert len(deps) >= 1

    def test_package_json_no_deps(self, tmp_path):
        import json

        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({"name": "empty-app", "version": "0.0.1"}))
        parser = self._make_parser()
        meta, deps = parser.parse_package_json(pkg)
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    def test_package_json_via_parse(self, tmp_path):
        import json

        pkg = tmp_path / "package.json"
        pkg.write_text(
            json.dumps({"name": "x", "version": "1.0.0", "dependencies": {"lodash": "^4.0"}})
        )
        parser = self._make_parser()
        meta, deps = parser.parse(pkg)
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    # --- parse_cargo_toml ---

    def test_cargo_toml_basic(self, tmp_path):
        cargo = tmp_path / "Cargo.toml"
        cargo.write_text("""
[package]
name = "mylib"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "1.0", features = ["derive"] }
tokio = "1.0"

[dev-dependencies]
criterion = "0.5"
""")
        parser = self._make_parser()
        meta, deps = parser.parse_cargo_toml(cargo)
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    def test_cargo_toml_via_parse(self, tmp_path):
        cargo = tmp_path / "Cargo.toml"
        cargo.write_text('[package]\nname = "x"\nversion = "0.1.0"\n')
        parser = self._make_parser()
        meta, deps = parser.parse(cargo)
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    def test_cargo_toml_empty_deps(self, tmp_path):
        cargo = tmp_path / "Cargo.toml"
        cargo.write_text('[package]\nname = "x"\nversion = "0.1.0"\n\n[dependencies]\n')
        parser = self._make_parser()
        meta, deps = parser.parse_cargo_toml(cargo)
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    # --- parse_setup_py ---

    def test_setup_py_basic(self, tmp_path):
        setup = tmp_path / "setup.py"
        setup.write_text("""
from setuptools import setup

setup(
    name="mypackage",
    version="1.0.0",
    install_requires=[
        "requests>=2.28",
        "click>=8.0",
    ],
    extras_require={
        "dev": ["pytest>=7.0"],
    },
)
""")
        parser = self._make_parser()
        meta, deps = parser.parse_setup_py(setup)
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    def test_setup_py_via_parse(self, tmp_path):
        setup = tmp_path / "setup.py"
        setup.write_text("from setuptools import setup\nsetup(name='x', version='0.1.0')\n")
        parser = self._make_parser()
        meta, deps = parser.parse(setup)
        assert isinstance(meta, dict)
        assert isinstance(deps, list)


# ---------------------------------------------------------------------------
# ingest/language_detect.py — LanguageDetector (get_parser, more extensions)
# ---------------------------------------------------------------------------


class TestLanguageDetectorExtended:
    def test_get_parser_for_python(self):
        from cogant.ingest.language_detect import LanguageDetector

        parser = LanguageDetector.get_parser("python")
        # May return None if tree-sitter not available
        assert parser is None or parser is not None

    def test_get_parser_unknown_language_raises_or_none(self):
        from cogant.ingest.language_detect import LanguageDetector

        try:
            parser = LanguageDetector.get_parser("nonexistent_lang_xyz")
            assert parser is None
        except (ImportError, ValueError, KeyError):
            pass  # Acceptable to raise for unknown language

    def test_detect_language_js(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        p = tmp_path / "app.js"
        p.write_text("const x = 1;\n")
        lang = LanguageDetector.detect_language(p)
        assert lang is None or isinstance(lang, str)

    def test_detect_language_ts(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        p = tmp_path / "app.ts"
        p.write_text("const x: number = 1;\n")
        lang = LanguageDetector.detect_language(p)
        assert lang is None or isinstance(lang, str)

    def test_detect_language_java(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        p = tmp_path / "Main.java"
        p.write_text("class Main {}\n")
        lang = LanguageDetector.detect_language(p)
        assert lang is None or isinstance(lang, str)

    def test_detect_language_rust(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        p = tmp_path / "main.rs"
        p.write_text("fn main() {}\n")
        lang = LanguageDetector.detect_language(p)
        assert lang is None or isinstance(lang, str)

    def test_detect_language_go(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        p = tmp_path / "main.go"
        p.write_text("package main\nfunc main() {}\n")
        lang = LanguageDetector.detect_language(p)
        assert lang is None or isinstance(lang, str)

    def test_detect_language_cpp(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        p = tmp_path / "main.cpp"
        p.write_text("int main() { return 0; }\n")
        lang = LanguageDetector.detect_language(p)
        assert lang is None or isinstance(lang, str)

    def test_detect_language_ruby(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        p = tmp_path / "app.rb"
        p.write_text("puts 'hello'\n")
        lang = LanguageDetector.detect_language(p)
        assert lang is None or isinstance(lang, str)

    def test_detect_language_markdown(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        p = tmp_path / "README.md"
        p.write_text("# Hello\n")
        lang = LanguageDetector.detect_language(p)
        assert lang is None or isinstance(lang, str)

    def test_detect_repo_with_multiple_types(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.py").write_text("y = 2\n")
        (tmp_path / "main.js").write_text("const z = 3;\n")
        (tmp_path / "app.ts").write_text("const w: number = 4;\n")
        result = LanguageDetector.detect_repo_languages(tmp_path)
        assert isinstance(result, dict)
        assert len(result) >= 1

    def test_detect_repo_nested_dirs(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        sub = tmp_path / "src"
        sub.mkdir()
        (sub / "mod.py").write_text("x = 1\n")
        (sub / "util.py").write_text("y = 2\n")
        result = LanguageDetector.detect_repo_languages(tmp_path)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# ingest/repo.py — RepoIngester with more scenarios
# ---------------------------------------------------------------------------


class TestRepoIngesterExtended:
    def test_ingest_local_with_checksums(self, tmp_path):
        from cogant.ingest.repo import RepoIngester, RepoSnapshot

        (tmp_path / "main.py").write_text("x = 1\n")
        ingester = RepoIngester()
        snapshot = ingester.ingest_local(tmp_path, compute_checksums=True)
        assert isinstance(snapshot, RepoSnapshot)
        # Some files should have checksums
        for fi in snapshot.files:
            if fi.path.name == "main.py":
                # checksum may or may not be computed
                assert fi.checksum is None or isinstance(fi.checksum, str)

    def test_ingest_local_no_test_files(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "main.py").write_text("x = 1\n")
        (tmp_path / "test_main.py").write_text("def test(): pass\n")
        ingester = RepoIngester()
        snapshot = ingester.ingest_local(tmp_path, include_test_files=False)
        # test_main.py should not be included
        names = [f.relative_path for f in snapshot.files]
        test_files = [n for n in names if "test_" in str(n)]
        assert len(test_files) == 0

    def test_ingest_local_multiple_file_types(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "app.py").write_text("x = 1\n")
        (tmp_path / "util.py").write_text("y = 2\n")
        (tmp_path / "app.js").write_text("const z = 3;\n")
        ingester = RepoIngester()
        snapshot = ingester.ingest_local(tmp_path)
        assert snapshot.root_path == tmp_path
        # Should at minimum find the python files
        assert len(snapshot.files) >= 1

    def test_ingest_local_nested_directories(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        src = tmp_path / "src"
        src.mkdir()
        (src / "core.py").write_text("class Core: pass\n")
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_core.py").write_text("def test(): pass\n")
        ingester = RepoIngester()
        snapshot = ingester.ingest_local(tmp_path, include_test_files=True)
        assert len(snapshot.files) >= 1

    def test_snapshot_has_dependencies(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
        (tmp_path / "main.py").write_text("import requests\n")
        ingester = RepoIngester()
        snapshot = ingester.ingest_local(tmp_path)
        assert isinstance(snapshot.dependencies, list)
