"""Golden-style smoke: bundle JSON shape expected by CLI render/validate."""

from __future__ import annotations

import json
from pathlib import Path

from cogant.api.bundle import Bundle


def test_bundle_save_json_top_level_keys(tmp_path: Path) -> None:
    bundle = Bundle(
        target=str(tmp_path),
        stage_results={"ingest": {"file_count": 1, "language_distribution": {"python": 1}}},
        metadata={"version": "test"},
    )
    out = tmp_path / "bundle.json"
    bundle.save_json(str(out))
    data = json.loads(out.read_text(encoding="utf-8"))
    assert set(data.keys()) >= {"target", "artifacts", "stage_results", "errors", "metadata"}
    assert data["stage_results"]["ingest"]["file_count"] == 1
