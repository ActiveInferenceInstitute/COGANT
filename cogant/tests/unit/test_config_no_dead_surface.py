"""Drift gate for the ``cogant.yaml`` advertised-config surface.

Background (review 2026-05-19, TODO.md §8 "Typed config / preset subsystem
has zero callers"): ``cogant.yaml`` advertises many top-level configuration
sections, but only the ``pipeline:`` section is actually consumed by the CLI
(``cli/main.py`` reads it via ``ConfigLoader`` as a raw dict). The remaining
sections, plus ``config/presets.py`` / ``config/schema.py``, have no
non-test callers — a silent "advertised but dead" surface.

This test does **not** make the contestable wire-vs-prune decision. It does
the conservative, durable thing instead: it pins the exact advertised
inventory and records, in one reviewed place, which sections are wired vs.
documented-only. Effect:

* Adding a new ``cogant.yaml`` top-level section that nothing consumes now
  fails CI here (no more *silent* dead surface).
* Removing/pruning a section is a deliberate edit to ``EXPECTED`` that a
  reviewer sees.
* The honest consumption status is inventoried, not hidden one level down.

When the wire-or-prune decision (TODO §8) is made, update ``EXPECTED`` and
move sections between ``WIRED`` and ``DOCUMENTED_ONLY`` accordingly.

No mocks (repo policy): pure file read + set assertions.
"""

from __future__ import annotations

from pathlib import Path

import yaml

# Section that is actually consumed by the CLI today (cli/main.py ->
# ConfigLoader.load_from_yaml -> raw `pipeline:` dict, ~8 keys).
WIRED: frozenset[str] = frozenset({"pipeline"})

# Advertised in cogant.yaml but NOT consumed by any non-test code path as of
# 2026-05-19 (config/loaders build_*, config/presets, config/schema enums are
# dead). Inventoried here so the surface is explicit, not silent. `version`
# is metadata, not a behavioural section.
DOCUMENTED_ONLY: frozenset[str] = frozenset(
    {
        "advanced",
        "export",
        "graph",
        "ingest",
        "normalize",
        "parser",
        "process",
        "provenance",
        "statespace",
        "system",
        "translation",
        "validate",
        "version",
        "visualization",
    }
)

EXPECTED: frozenset[str] = WIRED | DOCUMENTED_ONLY


def _cogant_yaml_path() -> Path:
    """Resolve cogant.yaml from the package root regardless of CWD."""
    here = Path(__file__).resolve()
    for cand in (
        here.parents[2] / "cogant.yaml",  # tests/unit/ -> package root
        here.parents[3] / "cogant.yaml",
        Path.cwd() / "cogant.yaml",
    ):
        if cand.is_file():
            return cand
    raise AssertionError("cogant.yaml not found from any candidate path")


def test_cogant_yaml_inventory_has_not_drifted() -> None:
    """The advertised top-level config surface must match the reviewed inventory.

    A mismatch means a section was added or removed without updating this
    gate — i.e. the dead-surface accounting drifted. That is the failure
    this test exists to catch.
    """
    data = yaml.safe_load(_cogant_yaml_path().read_text(encoding="utf-8"))
    actual = frozenset(data.keys())
    added = actual - EXPECTED
    removed = EXPECTED - actual
    assert not added, (
        f"cogant.yaml advertises new top-level section(s) {sorted(added)} "
        "with no entry in WIRED/DOCUMENTED_ONLY. Wire them into the CLI or "
        "add them to DOCUMENTED_ONLY with a TODO §8 note — do not ship a "
        "silently-dead config section."
    )
    assert not removed, (
        f"cogant.yaml no longer advertises {sorted(removed)}; update "
        "WIRED/DOCUMENTED_ONLY to match the pruned surface."
    )


def test_wired_sections_are_present() -> None:
    """Sections we claim are wired must still exist in cogant.yaml."""
    data = yaml.safe_load(_cogant_yaml_path().read_text(encoding="utf-8"))
    actual = frozenset(data.keys())
    missing = WIRED - actual
    assert not missing, (
        f"WIRED section(s) {sorted(missing)} vanished from cogant.yaml — "
        "the CLI config path would break."
    )


def test_dead_surface_is_explicitly_inventoried_not_silent() -> None:
    """Guard the invariant that every advertised section is classified.

    This is the anti-silent-dead-surface contract: no cogant.yaml section
    may exist without being explicitly placed in WIRED or DOCUMENTED_ONLY.
    """
    data = yaml.safe_load(_cogant_yaml_path().read_text(encoding="utf-8"))
    for key in data.keys():
        assert key in EXPECTED, (
            f"cogant.yaml section {key!r} is unclassified — every advertised "
            "section must be explicitly WIRED or DOCUMENTED_ONLY (TODO §8)."
        )
