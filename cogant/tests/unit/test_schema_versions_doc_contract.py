"""Scope contract for the ``cogant.schema.versions`` identifier documentation.

``CURRENT_GNN_VERSION`` is COGANT's own schema identifier, so the module
docstring may only attribute the two-numeric-component limit to the anchored
upstream schema patterns that actually impose it. Upstream's BNF grammar, its
verbatim ``GNNVersionAndFlags`` parser and its committed ``GNN v1.4.1`` example
all admit three components, so claiming that a three-component version is "not
an upstream version" overstates what the pinned upstream says.
"""

from __future__ import annotations

import re

from cogant.schema import versions

# ``GNNVersionAndFlags`` patterns quoted verbatim from the pinned upstream
# commit (``.github/gnn-pin.json`` -> ``v5.1.0`` / ``75c834bd``):
# ``src/gnn/schemas/json.json`` and ``src/gnn/schemas/yaml.yaml``.
JSON_SCHEMA_PATTERN = r"^GNN v[0-9]+\.[0-9]+$|^GNN v[0-9]+$"
YAML_SCHEMA_PATTERN = r"^GNN v[0-9]+(\.[0-9]+)?( .+)?$"


def test_docstring_attributes_component_limit_to_published_patterns() -> None:
    doc = " ".join((versions.__doc__ or "").split())
    assert "at most two numeric components" in doc
    for published in ("json.json", "yaml.yaml"):
        assert published in doc
    assert "bnf.bnf" in doc
    assert re.search(r"three-component.{0,40}not an upstream", doc) is None


def test_published_patterns_reject_the_three_component_identifier() -> None:
    for pattern in (JSON_SCHEMA_PATTERN, YAML_SCHEMA_PATTERN):
        assert re.fullmatch(pattern, "GNN v1.1") is not None
        assert re.fullmatch(pattern, f"GNN v{versions.CURRENT_GNN_VERSION}") is None
