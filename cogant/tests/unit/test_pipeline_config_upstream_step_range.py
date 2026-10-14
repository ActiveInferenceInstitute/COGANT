"""``PipelineConfig.validate`` accepts every step of the 25-step upstream pipeline.

The upstream GNN pipeline has steps 0..24 (the CLI's ``--upstream-gnn-*-steps``
flags accept that range and step 13 is the LLM step), so the diagnostic must
not report steps 13..24 as out of range.
"""

from __future__ import annotations

import pytest

from cogant.config.pipeline import PipelineConfig
from cogant.gnn.upstream_bridge.pipeline import UPSTREAM_STEP_SCRIPTS


@pytest.mark.parametrize("step", [0, 12, 13, 24])
def test_every_upstream_step_index_is_in_range(step: int) -> None:
    config = PipelineConfig(upstream_gnn_only_steps=[step], upstream_gnn_skip_steps=[step])
    assert config.validate() == []


@pytest.mark.parametrize("step", [-1, 25, 100])
def test_steps_outside_the_upstream_pipeline_are_reported(step: int) -> None:
    errors = PipelineConfig(upstream_gnn_only_steps=[step]).validate()
    assert errors == ["upstream_gnn_only_steps contains an out-of-range step"]


def test_valid_range_matches_upstream_step_table() -> None:
    last = len(UPSTREAM_STEP_SCRIPTS) - 1
    assert PipelineConfig(upstream_gnn_skip_steps=[last]).validate() == []
    assert PipelineConfig(upstream_gnn_skip_steps=[last + 1]).validate() != []
