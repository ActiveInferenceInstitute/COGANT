"""Wave 20b coverage boost: cogant.normalize.canonical missing lines.

Targets uncovered lines (47, 150, 153, 156, 159, 162, 194, 208):
- NormalizedFact.__post_init__ when metadata is explicitly None
- _normalize_metadata visibility branch
- _normalize_metadata is_abstract branch
- _normalize_metadata is_static branch
- _normalize_metadata decorators branch
- _normalize_metadata type_hints branch
- _extract_python_metadata is_generator branch
- _extract_javascript_metadata is_async branch
"""

from __future__ import annotations

import pytest

from cogant.normalize.canonical import (
    CanonicalNormalizer,
    LanguageFact,
    NormalizedFact,
)
from cogant.schemas.core import NodeKind

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# NormalizedFact dataclass __post_init__ (line 47)
# ---------------------------------------------------------------------------


def test_normalized_fact_post_init_replaces_none_metadata_with_empty_dict() -> None:
    nf = NormalizedFact(
        node_kind=NodeKind.CLASS,
        name="X",
        qualified_name="m.X",
    )
    # Default metadata=None triggers __post_init__ to set it to {}
    assert nf.metadata == {}


def test_normalized_fact_post_init_preserves_explicit_metadata() -> None:
    nf = NormalizedFact(
        node_kind=NodeKind.FUNCTION,
        name="f",
        qualified_name="m.f",
        metadata={"key": "value"},
    )
    assert nf.metadata == {"key": "value"}


# ---------------------------------------------------------------------------
# _normalize_metadata common-field branches (lines 150/153/156/159/162)
# ---------------------------------------------------------------------------


def test_normalize_metadata_visibility() -> None:
    """Line 150: visibility branch."""
    normalizer = CanonicalNormalizer()
    fact = LanguageFact(
        fact_type="class",
        language="python",
        data={"name": "Foo", "visibility": "public"},
    )
    result = normalizer.normalize(fact)
    assert result is not None
    assert result.metadata is not None
    assert result.metadata["visibility"] == "public"


def test_normalize_metadata_is_abstract() -> None:
    """Line 153: is_abstract branch."""
    normalizer = CanonicalNormalizer()
    fact = LanguageFact(
        fact_type="class",
        language="python",
        data={"name": "Base", "is_abstract": True},
    )
    result = normalizer.normalize(fact)
    assert result is not None
    assert result.metadata is not None
    assert result.metadata["is_abstract"] is True


def test_normalize_metadata_is_static() -> None:
    """Line 156: is_static branch."""
    normalizer = CanonicalNormalizer()
    fact = LanguageFact(
        fact_type="method",
        language="python",
        data={"name": "static_method", "is_static": True},
    )
    result = normalizer.normalize(fact)
    assert result is not None
    assert result.metadata is not None
    assert result.metadata["is_static"] is True


def test_normalize_metadata_decorators() -> None:
    """Line 159: decorators branch."""
    normalizer = CanonicalNormalizer()
    fact = LanguageFact(
        fact_type="function",
        language="python",
        data={"name": "f", "decorators": ["@cached", "@retry"]},
    )
    result = normalizer.normalize(fact)
    assert result is not None
    assert result.metadata is not None
    assert result.metadata["decorators"] == ["@cached", "@retry"]


def test_normalize_metadata_type_hints() -> None:
    """Line 162: type_hints branch."""
    normalizer = CanonicalNormalizer()
    fact = LanguageFact(
        fact_type="function",
        language="python",
        data={"name": "f", "type_hints": {"return": "int", "x": "str"}},
    )
    result = normalizer.normalize(fact)
    assert result is not None
    assert result.metadata is not None
    assert result.metadata["type_hints"] == {"return": "int", "x": "str"}


# ---------------------------------------------------------------------------
# Python-specific extraction (line 194 - is_generator)
# ---------------------------------------------------------------------------


def test_normalize_python_is_generator() -> None:
    """Line 194: is_generator branch in _extract_python_metadata."""
    normalizer = CanonicalNormalizer()
    fact = LanguageFact(
        fact_type="function",
        language="python",
        data={"name": "yield_things", "is_generator": True},
    )
    result = normalizer.normalize(fact)
    assert result is not None
    assert result.metadata is not None
    assert result.metadata["is_generator"] is True


# ---------------------------------------------------------------------------
# JavaScript-specific extraction (line 208 - is_async)
# ---------------------------------------------------------------------------


def test_normalize_javascript_is_async() -> None:
    """Line 208: is_async branch in _extract_javascript_metadata."""
    normalizer = CanonicalNormalizer()
    fact = LanguageFact(
        fact_type="async_function",
        language="javascript",
        data={"name": "fetcher", "is_async": True},
    )
    result = normalizer.normalize(fact)
    assert result is not None
    assert result.metadata is not None
    assert result.metadata["is_async"] is True


# ---------------------------------------------------------------------------
# Combined: all metadata branches in a single fact
# ---------------------------------------------------------------------------


def test_normalize_metadata_all_common_branches() -> None:
    """All five common-field metadata branches in one go."""
    normalizer = CanonicalNormalizer()
    fact = LanguageFact(
        fact_type="method",
        language="python",
        data={
            "name": "do_thing",
            "visibility": "private",
            "is_abstract": False,
            "is_static": False,
            "decorators": ["@override"],
            "type_hints": {"return": "None"},
            "is_generator": False,
        },
    )
    result = normalizer.normalize(fact)
    assert result is not None
    assert result.metadata is not None
    md = result.metadata
    assert md["visibility"] == "private"
    assert md["is_abstract"] is False
    assert md["is_static"] is False
    assert md["decorators"] == ["@override"]
    assert md["type_hints"] == {"return": "None"}
    assert md["is_generator"] is False
