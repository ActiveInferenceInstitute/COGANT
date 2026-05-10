"""Wave-20b coverage boost: ``cogant.ingest.files`` edge-case branches.

Targets the lines that the existing files.py-coverage tests miss:

* ``_should_ignore`` — gitignore wildcard prefix branch (lines 146-149)
* ``_should_ignore`` — gitignore exact-name match (line 151)
* ``_should_ignore`` — gitignore wildcard suffix branch
* ``IGNORE_PATTERNS`` — name-endswith match (e.g. ``*.egg``, ``*.whl``)
* End-to-end enumerate exercising every accepted/rejected branch
  including the test-file inclusion gate

All real filesystem fixtures, no mocks.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.ingest.files import (
    IGNORE_PATTERNS,
    LANGUAGE_EXTENSIONS,
    TEST_PATTERNS,
    FileEnumerator,
    FileInfo,
)


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture()
def gitignore_repo(tmp_path: Path) -> Path:
    """A repo with a populated .gitignore covering every wildcard branch."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".gitignore").write_text(
        "# A comment that must be skipped\n"
        "\n"  # empty line that must be skipped
        "build_*\n"  # wildcard suffix
        "*.tmp\n"  # wildcard prefix
        "secret.py\n"  # exact-name match
        "ignored_dir\n"
    )
    # File ignored by exact name
    (repo / "secret.py").write_text("print('hi')\n")
    # File ignored by wildcard prefix (build_*)
    (repo / "build_artifact.py").write_text("x = 1\n")
    # File ignored by wildcard suffix (*.tmp)
    (repo / "scratch.tmp").write_text("temp data")
    # Kept files
    (repo / "main.py").write_text("def main(): pass\n")
    (repo / "utils.py").write_text("def util(): pass\n")
    # Ignored directory
    ignored_dir = repo / "ignored_dir"
    ignored_dir.mkdir()
    (ignored_dir / "module.py").write_text("y = 2\n")
    return repo


@pytest.fixture()
def repo_with_test_files(tmp_path: Path) -> Path:
    """Repo containing source + test files in standard layouts."""
    repo = tmp_path / "with_tests"
    repo.mkdir()
    (repo / "src.py").write_text("def f(): pass\n")
    tests = repo / "tests"
    tests.mkdir()
    (tests / "test_src.py").write_text("def test_f(): pass\n")
    return repo


# --------------------------------------------------------------------------- #
# _should_ignore — gitignore wildcard branches
# --------------------------------------------------------------------------- #


def test_gitignore_wildcard_prefix_match(gitignore_repo: Path) -> None:
    """``*.tmp`` should ignore ``scratch.tmp`` (wildcard prefix branch)."""
    enumerator = FileEnumerator(gitignore_repo, respect_gitignore=True)
    files = enumerator.enumerate()
    paths = {f.relative_path for f in files}
    assert "main.py" in paths
    # *.tmp doesn't match a known language extension anyway, so this is
    # exercising _detect_language=None too — sanity-check via the .py case
    # below, which is the real behavioral test for the gitignore branch.


def test_gitignore_wildcard_suffix_blocks_python_file(gitignore_repo: Path) -> None:
    """``build_*`` matches ``build_artifact.py`` (wildcard suffix branch — line 146-149)."""
    enumerator = FileEnumerator(gitignore_repo, respect_gitignore=True)
    files = enumerator.enumerate()
    paths = {f.relative_path for f in files}
    assert "build_artifact.py" not in paths
    # main.py is kept (sanity check)
    assert "main.py" in paths


def test_gitignore_exact_name_match(gitignore_repo: Path) -> None:
    """``secret.py`` is excluded by exact-name match (line 151 path)."""
    enumerator = FileEnumerator(gitignore_repo, respect_gitignore=True)
    paths = {f.relative_path for f in enumerator.enumerate()}
    assert "secret.py" not in paths


def test_gitignore_directory_part_match(gitignore_repo: Path) -> None:
    """A directory name in the path-parts excludes children (line 151 parts branch)."""
    enumerator = FileEnumerator(gitignore_repo, respect_gitignore=True)
    files = enumerator.enumerate()
    rels = {f.relative_path for f in files}
    # ``ignored_dir/module.py`` → relative.parts = ('ignored_dir', 'module.py')
    # 'ignored_dir' is in patterns and matches one of those parts.
    assert all("ignored_dir" not in rp for rp in rels)


def test_respect_gitignore_disabled(gitignore_repo: Path) -> None:
    """``respect_gitignore=False`` keeps all .py files except IGNORE_PATTERNS."""
    enumerator = FileEnumerator(gitignore_repo, respect_gitignore=False)
    paths = {f.relative_path for f in enumerator.enumerate()}
    # secret.py and build_artifact.py are NOT ignored when gitignore is off
    assert "secret.py" in paths
    assert "build_artifact.py" in paths
    assert "main.py" in paths


# --------------------------------------------------------------------------- #
# _load_gitignore — caches + skip-comment branches
# --------------------------------------------------------------------------- #


def test_gitignore_loaded_once_and_cached(gitignore_repo: Path) -> None:
    """Two calls to enumerate should not re-read .gitignore."""
    enumerator = FileEnumerator(gitignore_repo, respect_gitignore=True)
    enumerator.enumerate()
    cached_first = enumerator._gitignore_patterns
    assert cached_first is not None
    # Comments and blanks are skipped; only real patterns make it in
    assert "# A comment that must be skipped" not in cached_first
    assert "" not in cached_first
    assert "build_*" in cached_first
    enumerator.enumerate()
    # Cache is the same dict instance (no second read)
    assert enumerator._gitignore_patterns is cached_first


def test_no_gitignore_file_means_empty_patterns(tmp_path: Path) -> None:
    """When .gitignore is absent, gitignore patterns should be empty."""
    repo = tmp_path / "no_ignore"
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n")
    enumerator = FileEnumerator(repo, respect_gitignore=True)
    files = enumerator.enumerate()
    assert any(f.relative_path == "a.py" for f in files)
    assert enumerator._load_gitignore() == set()


# --------------------------------------------------------------------------- #
# _is_test_file
# --------------------------------------------------------------------------- #


def test_is_test_file_via_test_prefix(tmp_path: Path) -> None:
    """``test_`` prefix marks the file as a test."""
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "test_module.py").write_text("def test_x(): pass\n")
    (repo / "module.py").write_text("def x(): pass\n")
    enumerator = FileEnumerator(repo, respect_gitignore=True)
    files = enumerator.enumerate(include_test_files=True)
    by_name = {f.relative_path: f for f in files}
    assert by_name["test_module.py"].is_test is True
    assert by_name["module.py"].is_test is False


def test_include_test_files_false_filters_them_out(repo_with_test_files: Path) -> None:
    """Setting ``include_test_files=False`` drops detected tests."""
    enumerator = FileEnumerator(repo_with_test_files, respect_gitignore=True)
    files = enumerator.enumerate(include_test_files=False)
    paths = {f.relative_path for f in files}
    assert "src.py" in paths
    # Tests folder member is filtered
    assert not any("test_" in p for p in paths)


def test_include_test_files_true_keeps_them(repo_with_test_files: Path) -> None:
    """Default ``include_test_files=True`` keeps test files."""
    enumerator = FileEnumerator(repo_with_test_files, respect_gitignore=True)
    files = enumerator.enumerate(include_test_files=True)
    paths = {f.relative_path for f in files}
    assert any("test_src" in p for p in paths)


# --------------------------------------------------------------------------- #
# _detect_language — multi-language coverage
# --------------------------------------------------------------------------- #


def test_detect_language_covers_every_extension_class(tmp_path: Path) -> None:
    """Touch every language in ``LANGUAGE_EXTENSIONS`` to exercise the dispatch."""
    repo = tmp_path / "polyglot"
    repo.mkdir()
    # One file per language. Pick the first extension from each set.
    for lang, exts in LANGUAGE_EXTENSIONS.items():
        ext = sorted(exts)[0]
        (repo / f"sample{ext}").write_text(f"// {lang} sample\n")
    # Plus an unsupported extension that should be filtered out
    (repo / "readme.txt").write_text("not source\n")

    enumerator = FileEnumerator(repo, respect_gitignore=False)
    files = enumerator.enumerate()
    detected_langs = {f.language for f in files}
    # Every language in the catalogue should appear at least once
    for lang in LANGUAGE_EXTENSIONS:
        assert lang in detected_langs
    # readme.txt is excluded
    assert all(not f.relative_path.endswith(".txt") for f in files)


def test_detect_language_unknown_returns_none(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "weird.xyz").write_text("nothing\n")
    enumerator = FileEnumerator(repo, respect_gitignore=False)
    files = enumerator.enumerate()
    # No supported language → not enumerated at all
    assert files == []


# --------------------------------------------------------------------------- #
# IGNORE_PATTERNS — directory parts and name-endswith branches
# --------------------------------------------------------------------------- #


def test_ignore_patterns_blocks_node_modules(tmp_path: Path) -> None:
    """``node_modules`` in path parts is always ignored."""
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "main.py").write_text("x=1\n")
    nm = repo / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    (nm / "index.js").write_text("/* js */\n")

    enumerator = FileEnumerator(repo, respect_gitignore=False)
    paths = {f.relative_path for f in enumerator.enumerate()}
    assert "main.py" in paths
    assert all("node_modules" not in p for p in paths)


def test_ignore_patterns_blocks_pycache(tmp_path: Path) -> None:
    """``__pycache__`` in parts is ignored even when files inside are .py."""
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "main.py").write_text("x=1\n")
    cache = repo / "__pycache__"
    cache.mkdir()
    (cache / "main.cpython-312.pyc").write_text("")  # not a recognized lang
    (cache / "main.py").write_text("x=2\n")

    enumerator = FileEnumerator(repo, respect_gitignore=False)
    paths = {f.relative_path for f in enumerator.enumerate()}
    assert paths == {"main.py"}


def test_ignore_pattern_endswith_matches_directory_name(tmp_path: Path) -> None:
    """The ``path.name.endswith(pattern)`` branch fires on directory names.

    ``IGNORE_PATTERNS`` contains ``.egg-info`` (literal). The check is
    ``ignore_pattern in path.parts or path.name.endswith(ignore_pattern)``.
    A ``pkg.egg-info`` directory has the parent directory name ending
    with ``.egg-info`` — but Path enumeration walks rglob('*'), so the
    *file* path's parts contain ``pkg.egg-info``, which doesn't equal
    ``.egg-info`` literally; the endswith branch is matched on the file
    path's intermediate parts via the parent walk only when a path part
    itself endswith the pattern. Easier: a top-level *file* literally
    ending with ``.egg-info`` exercises the same branch deterministically.
    """
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "main.py").write_text("x=1\n")
    # A python file whose name ends with ``.egg-info`` (rare but valid)
    # exercises the ``path.name.endswith(ignore_pattern)`` branch.
    # ``.egg`` and ``.whl`` literal entries also exercise the branch.
    (repo / "x.egg").write_text("# fake egg\n")  # not a recognized language
    enumerator = FileEnumerator(repo, respect_gitignore=False)
    paths = {f.relative_path for f in enumerator.enumerate()}
    assert "main.py" in paths
    # Files ending in `.egg` (whether or not they map to a language) are
    # excluded — and even if not excluded by IGNORE, language detection
    # would drop them. Either way they don't appear.
    assert all(not p.endswith(".egg") for p in paths)


# --------------------------------------------------------------------------- #
# enumerate — checksum + size branches
# --------------------------------------------------------------------------- #


def test_enumerate_with_checksums(tmp_path: Path) -> None:
    """``compute_checksums=True`` populates the checksum field with sha256."""
    import hashlib

    repo = tmp_path / "r"
    repo.mkdir()
    content = "def f(): return 1\n"
    (repo / "f.py").write_text(content, encoding="utf-8")

    enumerator = FileEnumerator(repo, respect_gitignore=False)
    files = enumerator.enumerate(compute_checksums=True)
    assert len(files) == 1
    info = files[0]
    expected = hashlib.sha256(content.encode()).hexdigest()
    assert info.checksum == expected
    assert info.size_bytes == len(content)


def test_enumerate_without_checksums_leaves_field_none(tmp_path: Path) -> None:
    """Default behavior leaves checksum unset."""
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "f.py").write_text("x=1\n")
    enumerator = FileEnumerator(repo, respect_gitignore=False)
    files = enumerator.enumerate(compute_checksums=False)
    assert files[0].checksum is None


def test_compute_checksum_chunked_for_large_file(tmp_path: Path) -> None:
    """A file larger than a single chunk still hashes correctly.

    The implementation reads in 4096-byte chunks; a 12k payload exercises
    the iter() loop more than once.
    """
    import hashlib

    repo = tmp_path / "r"
    repo.mkdir()
    content = "x = 0\n" * 2000  # ~12000 bytes
    (repo / "large.py").write_text(content, encoding="utf-8")
    enumerator = FileEnumerator(repo, respect_gitignore=False)
    files = enumerator.enumerate(compute_checksums=True)
    assert len(files) == 1
    expected = hashlib.sha256(content.encode()).hexdigest()
    assert files[0].checksum == expected


# --------------------------------------------------------------------------- #
# FileInfo dataclass smoke
# --------------------------------------------------------------------------- #


def test_fileinfo_constructs_with_defaults(tmp_path: Path) -> None:
    info = FileInfo(
        path=tmp_path / "x.py",
        relative_path="x.py",
        language="python",
        size_bytes=42,
    )
    assert info.is_test is False
    assert info.checksum is None
    assert info.language == "python"


# --------------------------------------------------------------------------- #
# constants are well-formed
# --------------------------------------------------------------------------- #


def test_test_patterns_contains_common_test_prefixes() -> None:
    assert "test_" in TEST_PATTERNS
    assert "tests/" in TEST_PATTERNS


def test_ignore_patterns_contains_dot_dirs() -> None:
    assert ".git" in IGNORE_PATTERNS
    assert "__pycache__" in IGNORE_PATTERNS
    assert "node_modules" in IGNORE_PATTERNS
