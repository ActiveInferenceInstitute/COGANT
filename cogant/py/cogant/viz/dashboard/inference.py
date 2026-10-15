"""Render a dashboard panel from an admitted categorical execution trace."""

from __future__ import annotations

import html

from cogant.runtime.inference_records import InferenceTrace


def _free_energy_chart(trace: InferenceTrace) -> str:
    records = trace.trace[:100]
    values = [record.free_energy for record in records]
    low, high = min(values), max(values)
    if low == high:
        low, high = low - 0.5, high + 0.5
    span = high - low
    points = [
        (50 + 700 * index / max(len(records) - 1, 1), 250 - 200 * (value - low) / span)
        for index, value in enumerate(values)
    ]
    ticks = "".join(
        f'<text x="44" y="{254 - 50 * index}" text-anchor="end">{low + span * index / 4:.3g}</text>'
        for index in range(5)
    )
    polyline = " ".join(f"{x:.3f},{y:.3f}" for x, y in points)
    circles = "".join(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="3"/>' for x, y in points)
    return (
        '<svg viewBox="0 0 800 300" role="img" '
        'aria-label="Recorded posterior variational free energy in nats" '
        'style="width:100%;max-width:800px;color:inherit">'
        '<g fill="currentColor" font-size="12">'
        f"{ticks}"
        '<text x="400" y="18" text-anchor="middle">Posterior VFE (nats)</text>'
        f'<text x="50" y="272" text-anchor="middle">{records[0].t}</text>'
        f'<text x="750" y="272" text-anchor="middle">{records[-1].t}</text>'
        '<text x="400" y="292" text-anchor="middle">Observation step</text></g>'
        '<path d="M50 50V250H750" fill="none" stroke="currentColor"/>'
        f'<polyline points="{polyline}" fill="none" stroke="currentColor" stroke-width="2"/>'
        f'<g fill="currentColor">{circles}</g></svg>'
        f"<p>Showing {len(records)} of {len(trace.trace)} recorded observations.</p>"
    )


def render_inference_tab(trace: InferenceTrace | None) -> str:
    """Display measured records; callers admit persisted traces before rendering."""
    if trace is None:
        content = "<p>No active inference trace data available</p>"
    else:
        rows = []
        for record in trace.trace[:20]:
            beliefs = ", ".join(
                f"{html.escape(label)}: {probability:.4f}"
                for label, probability in list(
                    zip(trace.labels.states, record.posterior, strict=True)
                )[:6]
            )
            rows.append(
                f"<tr><td>{record.t}</td>"
                f"<td>{html.escape(trace.labels.observations[record.observation])}</td>"
                f"<td>{html.escape(trace.labels.actions[record.action])}</td>"
                f"<td>{record.policy_scores[record.action]:.4f}</td>"
                f"<td>{record.free_energy:.4f}</td><td>{beliefs}</td></tr>"
            )
        content = (
            f"<p>Mode: <strong>{trace.mode}</strong>; horizon: {trace.policy_horizon}; "
            f"objective: {trace.policy_objective}.</p>"
            "<p>Model-generated observations are a rollout of the exported matrices. "
            "Actions select transition slices; this does not establish source-program "
            "behavioral equivalence or empirical adequacy.</p>"
            f'<p style="overflow-wrap:anywhere">GNN SHA256: <code>{trace.source_sha256}</code><br>'
            f"Matrix SHA256: <code>{trace.matrices_sha256}</code></p>"
            f"{_free_energy_chart(trace)}"
            '<h3>Filtering and control records</h3><div style="overflow-x:auto" '
            'tabindex="0" role="region" aria-label="Inference records"><table><thead><tr>'
            "<th>Step</th><th>Observation</th><th>Action</th><th>Selected G (nats)</th>"
            "<th>Posterior F (nats)</th><th>Posterior beliefs</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
            f"<p>Table shows {len(rows)} of {len(trace.trace)} observations and the first "
            f"{min(6, len(trace.labels.states))} of {len(trace.labels.states)} state probabilities.</p>"
        )
    return (
        '<div id="active-inference" class="tab-content"><div class="container">'
        "<h2>Exported-model inference</h2>" + content + "</div></div>"
    )
