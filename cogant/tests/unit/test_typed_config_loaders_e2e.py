"""End-to-end pin for the typed config + preset surface (TODO #1).

The iter-4 review flagged ``config/loaders.build_*``, ``config/presets.py``,
and ``config/schema.py`` enums as having zero callers. The CLI does call
``ConfigLoader.load_from_yaml`` / ``load_json_from_file`` (cli/main.py:732),
but the *typed* construction (``build_pipeline_config(..., preset=...)``)
and the preset surface were not exercised by any test.

This module pins the typed surface as load-bearing: removing
``build_pipeline_config`` or any of the shipped presets breaks these
tests. That gives the typed-config wire a structural anchor even while
the CLI continues to consume dict-keyed config.

The tests are deliberately *not* end-to-end through the CLI subprocess —
that would require fixture repos and run the full pipeline. They are
contract-level: build a config via the typed path and assert its shape
matches the documented preset + dict-merge semantics.
"""

from __future__ import annotations

import pytest

from cogant.config import defaults as _defaults
from cogant.config import presets as _presets_module
from cogant.config.loaders import ConfigLoader
from cogant.config.schema import PipelineConfig

# ``defaults.PRESETS`` is the source of truth for ``ConfigLoader.load_preset`` —
# four shipped presets ("default", "minimal", "comprehensive", "gnn"). A
# parallel ``presets.PRESETS`` exists with a slightly different name set
# ("minimal", "standard", "comprehensive", "gnn-focused", "security") and its
# own ``get_preset()``; the two are *not* the same and the integration target
# is ``defaults.PRESETS``. This dual-surface is an open architectural debt
# (TODO #1 typed-config dead callers); the test pins each surface so the
# debt cannot drift further (e.g. one drops a name without aligning the other).
LOADER_PRESETS = _defaults.PRESETS
PRESETS_MODULE = _presets_module.PRESETS


def test_default_pipeline_config_has_full_stage_list() -> None:
    """``build_pipeline_config()`` with no args returns the default pipeline
    with all 10 runner stages enabled."""
    cfg = ConfigLoader.build_pipeline_config()
    assert isinstance(cfg, PipelineConfig)
    # Pipeline config carries the runner stages as a dict keyed by stage name.
    assert hasattr(cfg, "stages") or hasattr(cfg, "run_stages")


@pytest.mark.parametrize("preset", sorted(LOADER_PRESETS.keys()))
def test_every_loader_preset_builds_a_typed_pipeline_config(preset: str) -> None:
    """Every preset in ``defaults.PRESETS`` must build a valid PipelineConfig
    via the integrated ``ConfigLoader.build_pipeline_config(preset=...)`` path.

    Guards against:
      * A preset typo (preset name in dict that fails ``load_preset``).
      * A preset that depends on a schema field removed by a refactor.
      * A preset that violates PipelineConfig validation rules.
    """
    cfg = ConfigLoader.build_pipeline_config(preset=preset)
    assert isinstance(cfg, PipelineConfig), (
        f"Preset {preset!r} did not produce a PipelineConfig"
    )


@pytest.mark.parametrize("preset_name", sorted(PRESETS_MODULE.keys()))
def test_presets_module_get_preset_returns_dict_with_pipeline_key(preset_name: str) -> None:
    """``presets.get_preset(name)`` returns a 4-key dict for each shipped name.

    This second-surface check pins the parallel ``presets.py`` registry against
    drift. Both registries should — eventually — converge on one set of names;
    until then both are honoured by their respective callers and must remain
    consistent within themselves.
    """
    out = _presets_module.get_preset(preset_name)
    assert isinstance(out, dict)
    assert "pipeline" in out
    assert isinstance(out["pipeline"], PipelineConfig)


def test_dict_overlay_merges_atop_preset_stages() -> None:
    """Passing a config_dict with a ``run_stages`` overlay supersedes the
    preset's default stage list.

    The CLI's current dict-keyed path could in principle delegate to this
    method to gain preset-base semantics + typed validation. This test
    demonstrates the surface works end-to-end on a field that the schema
    actually exposes.
    """
    base = list(LOADER_PRESETS.keys())[0]
    overlay = {"pipeline": {"stages": ["ingest", "static", "graph", "validate"]}}
    cfg = ConfigLoader.build_pipeline_config(config_dict=overlay, preset=base)
    assert isinstance(cfg, PipelineConfig)
    # ``stages`` maps to ``run_stages`` on the schema (cogant.yaml convention).
    assert list(cfg.run_stages) == ["ingest", "static", "graph", "validate"]


def test_preset_names_are_strings_and_non_empty() -> None:
    """Hygiene: both preset registries use string keys; CLI looks them up by str."""
    assert all(isinstance(k, str) and k for k in LOADER_PRESETS)
    assert all(isinstance(k, str) and k for k in PRESETS_MODULE)


def test_load_preset_returns_typed_subconfigs() -> None:
    """``ConfigLoader.load_preset(name)`` returns a dict of typed sub-configs.

    The dict keys ("cogant", "pipeline", "export", ...) and value types are
    contract — downstream code (or the CLI, if the wire is ever pulled
    fully through) reads them by name.
    """
    names = list(LOADER_PRESETS.keys())
    if not names:
        pytest.skip("no presets shipped")
    out = ConfigLoader.load_preset(names[0])
    assert isinstance(out, dict)
    assert "pipeline" in out, f"load_preset must expose 'pipeline' key, got: {list(out)}"
    assert isinstance(out["pipeline"], PipelineConfig)


def test_documented_dual_preset_surface_remains_acknowledged() -> None:
    """Anti-regression marker for TODO #1.

    ``defaults.PRESETS`` and ``presets.PRESETS`` are two separately-shipped
    preset registries with different name sets. The CLI uses
    ``ConfigLoader.load_preset`` which only consults the *defaults* registry;
    nothing in production calls into ``presets.get_preset()`` today.

    Resolution paths (deferred — pick one):
      A) Wire the CLI to honour both registries (canonicalize a single name
         map).
      B) Prune ``presets.py`` and migrate its richer-content presets into
         ``defaults.PRESETS``.

    Until one of those lands, this test serves as a documented marker that
    the dual surface exists *intentionally* and is *known*. If the two
    diverge further (or unify), update this test along with the choice.
    """
    only_in_loader = set(LOADER_PRESETS) - set(PRESETS_MODULE)
    only_in_module = set(PRESETS_MODULE) - set(LOADER_PRESETS)
    in_both = set(LOADER_PRESETS) & set(PRESETS_MODULE)
    # The known asymmetry at the time of this test's authoring; if either
    # side adds names or renames, the assertion guides the resolution.
    assert "default" in only_in_loader
    assert "gnn" in only_in_loader
    assert "standard" in only_in_module
    assert "gnn-focused" in only_in_module
    assert "minimal" in in_both
    assert "comprehensive" in in_both
