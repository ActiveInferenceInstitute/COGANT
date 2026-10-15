from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from manuscript_figures import MANUSCRIPT_FIGURES, copy_manuscript_figures  # noqa: E402

MODEL = """## ModelName
PublicationControl

## State Space
```gnn-matrices
A[[rows=1][cols=1]]
1.0
B[[rows=1][cols=1][depth=1]]
# action=0
1.0
C[[rows=1][cols=1]]
0.0
D[[rows=1][cols=1]]
1.0
```
"""


def test_strict_promotion_requires_replayable_trace_even_with_old_png(tmp_path: Path) -> None:
    from cogant.runtime.inference import write_inference_trace_artifact

    figure = next(item for item in MANUSCRIPT_FIGURES if item.key == "inference_trace")
    run = tmp_path / "cogant" / "output" / "calculator"
    (run / "gnn_package").mkdir(parents=True)
    (run / "data").mkdir()
    source = run / "gnn_package" / "model.gnn.md"
    source.write_text(MODEL)
    trace = write_inference_trace_artifact(run, steps=2)
    manifest_path = copy_manuscript_figures(tmp_path, figures=(figure,), strict=True)
    record = json.loads(manifest_path.read_text())["figures"][0]
    assert record["metadata_complete"]
    assert record["source_artifact"] == figure.source_artifact
    assert record["source_figure_metadata"]["source_sha256"]
    assert len(record["panels"]) == 4
    old_png = (tmp_path / figure.source).read_bytes()
    source.write_text(MODEL + "\n")
    with pytest.raises(ValueError, match="stale"):
        copy_manuscript_figures(tmp_path, figures=(figure,), strict=True)
    assert (tmp_path / figure.source).read_bytes() == old_png
    source.write_text(MODEL)
    trace.rename(trace.with_suffix(".preserved"))
    with pytest.raises(FileNotFoundError):
        copy_manuscript_figures(tmp_path, figures=(figure,), strict=True)


def test_fresh_optional_promotion_records_missing_inference(tmp_path: Path) -> None:
    figure = next(item for item in MANUSCRIPT_FIGURES if item.key == "inference_trace")
    manifest = copy_manuscript_figures(tmp_path, figures=(figure,))
    assert json.loads(manifest.read_text())["missing_count"] == 1
