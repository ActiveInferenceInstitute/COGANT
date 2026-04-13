"""Smoke and scenario tests for ``docs/verify_doc_links.py``.

The first two tests run against the real ``docs/`` tree (guards against
actual drift in committed docs). The remaining tests drive a copy of the
script rewired to a synthetic docs tree in ``tmp_path`` so we can exercise
the broken-link, escape-root, and anchor-fragment code paths without
disturbing the real tree.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_verify_module():
    script = _REPO_ROOT / "docs" / "verify_doc_links.py"
    assert script.is_file(), f"missing {script}"
    spec = importlib.util.spec_from_file_location("verify_doc_links", script)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_verify_doc_links_no_errors() -> None:
    mod = _load_verify_module()
    errors = mod.verify_docs()
    assert errors == [], "\n".join(errors)


def test_verify_doc_links_main_exits_zero() -> None:
    mod = _load_verify_module()
    assert mod.main() == 0


def test_verify_doc_links_summary_counters_populated() -> None:
    mod = _load_verify_module()
    mod.verify_docs()
    assert mod._LAST_FILES_SCANNED > 0
    assert mod._LAST_LINKS_CHECKED >= 0


# ---------------------------------------------------------------------------
# Scenario tests: drive a copy of the verifier against a synthetic tree.
# ---------------------------------------------------------------------------


_VERIFIER_SOURCE = (_REPO_ROOT / "docs" / "verify_doc_links.py").read_text(
    encoding="utf-8"
)


def _write_fake_verifier(tmp_path: Path) -> Path:
    """Write a copy of the verifier wired to ``tmp_path/docs`` as its docs root.

    The real script hard-codes ``_DOCS_DIR`` from ``__file__``, so we copy it
    into a throwaway location and overwrite the two anchor constants to
    point at a synthetic tree we control.
    """
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    fake = tmp_path / "verify_doc_links_fake.py"
    patched = _VERIFIER_SOURCE.replace(
        "_DOCS_DIR = Path(__file__).resolve().parent",
        f"_DOCS_DIR = Path({str(docs_dir)!r})",
    ).replace(
        "_REPO_ROOT = _DOCS_DIR.parent",
        f"_REPO_ROOT = Path({str(tmp_path)!r})",
    )
    fake.write_text(patched, encoding="utf-8")
    return fake


def _run_fake(fake: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(fake)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_fake_tree_all_good(tmp_path: Path) -> None:
    fake = _write_fake_verifier(tmp_path)
    docs_dir = tmp_path / "docs"
    (docs_dir / "a.md").write_text("[link](b.md)\n", encoding="utf-8")
    (docs_dir / "b.md").write_text("target\n", encoding="utf-8")
    result = _run_fake(fake)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "0 broken" in result.stdout


def test_fake_tree_broken_link_exits_one(tmp_path: Path) -> None:
    fake = _write_fake_verifier(tmp_path)
    docs_dir = tmp_path / "docs"
    (docs_dir / "a.md").write_text("[broken](no_such.md)\n", encoding="utf-8")
    result = _run_fake(fake)
    assert result.returncode == 1
    assert "no_such.md" in result.stdout
    assert "1 broken" in result.stdout


def test_fake_tree_external_and_fragment_links_are_ignored(tmp_path: Path) -> None:
    fake = _write_fake_verifier(tmp_path)
    docs_dir = tmp_path / "docs"
    (docs_dir / "a.md").write_text(
        textwrap.dedent(
            """
            [http](https://example.com)
            [mail](mailto:nobody@example.com)
            [anchor](#section)
            [local](b.md)
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (docs_dir / "b.md").write_text("ok\n", encoding="utf-8")
    result = _run_fake(fake)
    assert result.returncode == 0, result.stdout + result.stderr


def test_fake_tree_escaping_link_is_reported(tmp_path: Path) -> None:
    fake = _write_fake_verifier(tmp_path)
    docs_dir = tmp_path / "docs"
    # Link pointing outside the fake repo root → escape error.
    (docs_dir / "a.md").write_text(
        "[escape](../../../etc/passwd)\n", encoding="utf-8"
    )
    result = _run_fake(fake)
    assert result.returncode == 1
    assert "escapes repo root" in result.stdout
