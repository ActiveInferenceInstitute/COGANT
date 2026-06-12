"""Regression tests for ``tools/audit_manuscript_math_adjacency.py``.

Guards the Pandoc inline-math leak: a closing ``$`` immediately followed by a
digit (e.g. ``$-$10``) is not parsed as math and renders the dollars literally.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "audit_manuscript_math_adjacency.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("audit_manuscript_math_adjacency", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_flags_minus_before_digit() -> None:
    module = _load_module()
    # The exact bug shape that leaked in 09_ablation.md.
    violations = module.find_digit_adjacent_math("| family | $-$10 | $-$53 |\n")
    assert len(violations) == 2
    assert all(v[0] == 1 for v in violations)


def test_accepts_math_opening_with_digit() -> None:
    module = _load_module()
    # `$10^{-6}$` and `$0.65$` open with a digit — that is fine; only a closing
    # `$` followed by a digit breaks. These must NOT be flagged.
    text = "tolerance of $10^{-6}$ and bands $0.65$ `SingletonAccessRule`, $0.70$.\n"
    assert module.find_digit_adjacent_math(text) == []


def test_ignores_dollars_in_code() -> None:
    module = _load_module()
    assert module.find_digit_adjacent_math("`$-$10` and ```\n$-$10\n```\n") == []


def test_accepts_unicode_minus_fix() -> None:
    module = _load_module()
    # The applied fix: Unicode minus before the number, no math delimiters.
    assert module.find_digit_adjacent_math("| family | −10 | −53 |\n") == []


def test_live_manuscript_is_clean() -> None:
    module = _load_module()
    # The shipped manuscript must stay free of the leak.
    assert module.audit(module.MANUSCRIPT_DIR) == []
