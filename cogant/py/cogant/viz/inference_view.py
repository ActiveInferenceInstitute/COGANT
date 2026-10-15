from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from cogant.runtime.inference import load_inference_trace

logger = logging.getLogger(__name__)


def render_inference_trace_png(run_dir: Path | str) -> Path | None:
    """Plot admitted filtering and control records from the run's exact GNN export."""
    root = Path(run_dir)
    trace = load_inference_trace(root)
    try:
        import matplotlib.pyplot as plt
        from PIL import Image
    except ImportError:
        logger.warning("Matplotlib is unavailable; inference trace PNG was not rendered")
        return None
    records = trace.trace
    times = [record.t for record in records]
    tick_records = records[:: max(1, (len(records) + 7) // 8)]
    ticks = [record.t for record in tick_records]
    ns = len(trace.matrices.D)
    na = len(trace.matrices.B[0][0])
    figure = plt.figure(figsize=(15, 9), dpi=160, layout="constrained")
    posterior_axis = figure.add_subplot(2, 2, 1)
    prediction_axis = figure.add_subplot(2, 2, 2)
    policy_axis = figure.add_subplot(2, 2, 3)
    energy_axis = figure.add_subplot(2, 2, 4)
    for axis, values, title in (
        (
            posterior_axis,
            [[r.posterior[s] for r in records] for s in range(ns)],
            "Filtered posterior q(s | observation)",
        ),
        (
            prediction_axis,
            [[r.predicted_belief[s] for r in records] for s in range(ns)],
            "Next prediction after selected action",
        ),
    ):
        image = axis.imshow(values, aspect="auto", vmin=0.0, vmax=1.0, cmap="cividis")
        axis.set_title(title)
        axis.set_xlabel("Step")
        axis.set_ylabel("Matrix state index")
        axis.set_xticks(ticks)
        stride = max(1, (ns + 19) // 20)
        shown = list(range(0, ns, stride))
        axis.set_yticks(shown, [trace.labels.states[index] for index in shown])
        figure.colorbar(image, ax=axis, label="Probability")
    for action in range(na if na <= 6 else 0):
        policy_axis.plot(
            times,
            [record.policy_scores[action] for record in records],
            label=f"{action}: {trace.labels.actions[action]}",
            linewidth=1.4,
        )
    if na > 6:
        policy_axis.fill_between(
            times,
            [min(r.policy_scores) for r in records],
            [max(r.policy_scores) for r in records],
            alpha=0.2,
            label="All-action score range",
        )
    policy_axis.scatter(
        times,
        [r.policy_scores[r.action] for r in records],
        marker="o",
        color="black",
        s=25,
        label="Selected minimum",
    )
    policy_axis.set_title("One-step expected free energy: risk + ambiguity")
    policy_axis.set_xlabel("Step (observations / actions below)")
    policy_axis.set_ylabel("G (nats)")
    policy_axis.set_xticks(ticks, [f"{r.t}\no={r.observation} a={r.action}" for r in tick_records])
    policy_axis.grid(alpha=0.2)
    policy_axis.legend(fontsize=8, ncols=max(1, min(3, na)))
    energy_axis.plot(times, [r.free_energy for r in records], marker="o", color="#17637b")
    energy_axis.set_title("Filtering variational free energy before control")
    energy_axis.set_xlabel("Step")
    energy_axis.set_ylabel("F (nats)")
    energy_axis.set_xticks(ticks)
    energy_axis.grid(alpha=0.2)
    scope = (
        "Modal model-generated observations"
        if trace.mode == "model_rollout"
        else "Supplied observations"
    )
    figure.suptitle(
        f"{trace.model_name}: exported GNN inference\n{scope} | source {trace.source_sha256[:12]}",
        fontsize=15,
    )
    output = root / "figures" / "inference_trace.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        figure.savefig(output)
    finally:
        plt.close(figure)
    with Image.open(output) as rendered:
        rgb = rendered.convert("RGB")
        colors = rgb.getcolors(maxcolors=16)
        nonblank = colors is None or len(colors) > 1
        diverse = colors is None
    data = root / "data" if (root / "data").is_dir() else root
    sidecar = {
        "render_backend": "matplotlib_native",
        "degraded_renderer": False,
        "degraded_rasterization": False,
        "source_sha256": trace.source_sha256,
        "matrices_sha256": trace.matrices_sha256,
        "trace_sha256": hashlib.sha256((data / "inference_trace.json").read_bytes()).hexdigest(),
        "observation_mode": trace.mode,
        "panels": [
            {"key": key}
            for key in [
                "posterior",
                "next_prediction",
                "policy_expected_free_energy",
                "filtering_free_energy",
            ]
        ],
        "displayed_counts": {
            "steps": len(records),
            "states": ns,
            "observations": len(trace.matrices.A),
            "actions": na,
        },
        "visual_qa": {"nonblank": nonblank, "color_diversity_ok": diverse},
    }
    output.with_suffix(".figure.json").write_text(
        json.dumps(sidecar, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output
