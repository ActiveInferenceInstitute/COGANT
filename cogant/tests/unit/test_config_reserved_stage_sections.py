"""Reserved per-stage pipeline sections warn instead of silently doing nothing.

``pipeline.ingest`` / ``graph`` / ``translate`` / ``statespace`` / ``gnn`` /
``reverse`` are validated but no stage handler reads them yet. A value set in
a config file, the environment, overrides or the CLI layer must raise a
:class:`ReservedConfigWarning` naming the key, while the package's own
presets (which carry some of these values) stay quiet.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest

from cogant.config import ConfigLoader, ReservedConfigWarning
from cogant.config.loaders import ReservedConfigWarning as LoaderReservedConfigWarning


def test_reserved_warning_is_exported_from_config_package() -> None:
    assert ReservedConfigWarning is LoaderReservedConfigWarning
    assert issubclass(ReservedConfigWarning, UserWarning)


def test_file_setting_reserved_stage_field_warns_with_key(tmp_path: Path) -> None:
    path = tmp_path / "cfg.json"
    path.write_text(
        json.dumps(
            {
                "pipeline": {
                    "output_dir": "out",
                    "ingest": {"include_extensions": [".js"]},
                    "graph": {"max_nodes": 1},
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.warns(ReservedConfigWarning) as record:
        config = ConfigLoader.load_project_config(path)

    message = " ".join(str(w.message) for w in record)
    assert "pipeline.ingest.include_extensions" in message
    assert "pipeline.graph.max_nodes" in message
    assert str(path) in message
    # The value is still validated and carried on the model.
    assert config.pipeline.ingest.include_extensions == [".js"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"environment": {"COGANT_PIPELINE__TRANSLATE": '{"disable_rules": ["x"]}'}},
        {"overrides": {"pipeline": {"statespace": {"max_hidden_states": 4}}}},
        {"cli": {"pipeline": {"gnn": {"include_matrices": False}}}},
        {"cli": {"pipeline": {"reverse": {"include_tests": True}}}},
    ],
)
def test_every_user_layer_warns_for_reserved_sections(kwargs: dict[str, object]) -> None:
    with pytest.warns(ReservedConfigWarning, match=r"pipeline\.(translate|statespace|gnn|reverse)"):
        ConfigLoader.load_project_config(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "preset", ["default", "minimal", "standard", "comprehensive", "gnn-focused", "security"]
)
def test_presets_and_plain_configs_do_not_warn(preset: str, tmp_path: Path) -> None:
    path = tmp_path / "cfg.json"
    path.write_text(json.dumps({"pipeline": {"output_dir": "out"}}), encoding="utf-8")
    with warnings.catch_warnings():
        warnings.simplefilter("error", ReservedConfigWarning)
        ConfigLoader.load_project_config(path, preset=preset, environment={})
