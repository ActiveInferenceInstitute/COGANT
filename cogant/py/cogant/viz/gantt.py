"""GanttRenderer: Render process model as timeline/Gantt chart."""

from __future__ import annotations

import html as html_mod
import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cogant.process.timeline import Timeline

logger = logging.getLogger(__name__)


class GanttRenderer:
    """
    Render process/execution models as Gantt charts.

    Shows:
      - Pipeline stages and their duration
      - Dependencies between stages
      - Expected execution ordering
      - Critical path highlighting
      - Parallel stage groups
    """

    def __init__(self) -> None:
        """Initialize Gantt renderer."""
        self.stages: list[dict[str, Any]] = []
        self.dependencies: list[dict[str, Any]] = []
        self.timeline: list[dict[str, Any]] = []
        self.critical_path: list[str] = []
        self.parallel_groups: list[list[str]] = []

    def from_process_model(self, process_model: dict[str, Any]) -> GanttRenderer:
        """
        Load process model data.

        Args:
            process_model: Process model with stages, dependencies, timeline,
                and optional critical_path / parallel_groups.

        Returns:
            self (for chaining).
        """
        logger.info("Loading process model for Gantt visualization")

        self.stages = process_model.get("stages", [])
        self.dependencies = process_model.get("dependencies", [])
        self.timeline = process_model.get("timeline", [])
        self.critical_path = process_model.get("critical_path", [])
        self.parallel_groups = process_model.get("parallel_groups", [])

        return self

    def from_timeline(self, timeline: Timeline) -> GanttRenderer:
        """
        Load from a typed Timeline object.

        Args:
            timeline: Timeline instance with GanttStage objects.

        Returns:
            self (for chaining).
        """
        logger.info("Loading typed Timeline for Gantt visualization")

        self.stages = [
            {
                "id": s.stage_id,
                "name": s.name,
                "start": s.start_time,
                "duration": s.duration,
                "dependencies": s.dependencies,
                "criticality": s.criticality,
            }
            for s in timeline.stages
        ]
        self.critical_path = list(timeline.critical_path)
        self.parallel_groups = [list(g) for g in timeline.parallel_groups]
        self.dependencies = []
        self.timeline = []

        return self

    def render_html(self, output_path: str) -> str:
        """
        Render as interactive HTML Gantt chart.

        Args:
            output_path: Path to write HTML file.

        Returns:
            Path to rendered file.
        """
        logger.info(f"Rendering Gantt chart to {output_path}")

        html = self._generate_html()
        with open(output_path, "w") as f:
            f.write(html)

        return output_path

    def render_json(self) -> str:
        """Export as JSON for external visualization tools."""
        data = {
            "stages": self.stages,
            "dependencies": self.dependencies,
            "timeline": self.timeline,
            "critical_path": self.critical_path,
            "parallel_groups": self.parallel_groups,
        }
        return json.dumps(data, indent=2)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_total_duration(self) -> float:
        """Compute the total time span from stage data."""
        if not self.stages:
            return 1.0
        max_end = 0.0
        for s in self.stages:
            end = s.get("start", 0) + s.get("duration", 1)
            if end > max_end:
                max_end = end
        return max_end if max_end > 0 else 1.0

    def _stage_id(self, stage: dict[str, Any], index: int) -> str:
        """Return a stable identifier for a stage dict."""
        return stage.get("id", stage.get("name", f"stage_{index}"))

    def _is_critical(self, stage: dict[str, Any], index: int) -> bool:
        """Check whether a stage is on the critical path."""
        if not self.critical_path:
            return False
        sid = self._stage_id(stage, index)
        name = stage.get("name", "")
        return sid in self.critical_path or name in self.critical_path

    def _parallel_group_for(self, stage: dict[str, Any], index: int) -> int | None:
        """Return the parallel-group index for a stage, or None."""
        sid = self._stage_id(stage, index)
        name = stage.get("name", "")
        for gi, group in enumerate(self.parallel_groups):
            if sid in group or name in group:
                return gi
        return None

    def _timeline_ticks(self, total: float, num_ticks: int = 5) -> list[str]:
        """Generate evenly spaced tick labels for the timeline axis."""
        if total <= 0:
            return ["0"]
        if num_ticks <= 1:
            return [f"{total:.1f}" if total != int(total) else str(int(total))]
        ticks: list[str] = []
        for i in range(num_ticks):
            val = total * i / (num_ticks - 1)
            ticks.append(f"{val:.1f}" if val != int(val) else str(int(val)))
        return ticks

    # ------------------------------------------------------------------
    # HTML generation
    # ------------------------------------------------------------------

    def _generate_html(self) -> str:
        """Generate HTML with Gantt chart visualization."""
        all_stages = self.stages if self.stages else []
        total_duration = self._compute_total_duration()

        # Build the critical-path set for fast lookup
        set(self.critical_path)

        # Parallel-group colour bands (up to 6 distinct hues)
        pg_colors = [
            "rgba(102,126,234,0.08)",
            "rgba(118,75,162,0.08)",
            "rgba(72,191,145,0.08)",
            "rgba(234,179,8,0.08)",
            "rgba(239,68,68,0.08)",
            "rgba(59,130,246,0.08)",
        ]

        # --- Build label rows ---
        label_rows: list[str] = []
        bar_rows: list[str] = []
        for i, s in enumerate(all_stages):
            name = html_mod.escape(s.get("name", f"Stage {i}"))
            start = s.get("start", 0)
            duration = s.get("duration", 1)
            is_crit = self._is_critical(s, i)
            pg_idx = self._parallel_group_for(s, i)

            # Percentage-based positioning
            left_pct = (start / total_duration) * 100 if total_duration else 0
            width_pct = (duration / total_duration) * 100 if total_duration else 0
            # Ensure a minimum visible width
            width_pct = max(width_pct, 0.5)

            # CSS class for critical path
            bar_class = "gantt-bar gantt-bar-critical" if is_crit else "gantt-bar"

            # Row background for parallel groups
            row_bg = ""
            if pg_idx is not None:
                bg_color = pg_colors[pg_idx % len(pg_colors)]
                row_bg = f' style="background: {bg_color};"'

            # Critical-path label indicator
            crit_marker = ' <span class="crit-badge">CP</span>' if is_crit else ""

            label_rows.append(
                f'<div class="gantt-row"{row_bg}>'
                f'<div class="gantt-label">{name}{crit_marker}</div>'
                f'</div>'
            )
            bar_rows.append(
                f'<div class="gantt-row"{row_bg}>'
                f'<div class="{bar_class}" style="margin-left: {left_pct:.2f}%; width: {width_pct:.2f}%;">'
                f'{name}'
                f'</div>'
                f'</div>'
            )

        gantt_labels = "\n                    ".join(label_rows)
        gantt_bars = "\n                    ".join(bar_rows)

        # --- Dependencies (all of them) ---
        dependencies_html = "".join(
            f'<div class="dependency">'
            f'<strong>{html_mod.escape(str(d.get("from", "?")))}'
            f' &rarr; {html_mod.escape(str(d.get("to", "?")))}</strong>'
            f'<br/>{html_mod.escape(str(d.get("type", "depends_on")))}'
            f'</div>'
            for d in self.dependencies
        )

        # --- Parallel groups legend ---
        pg_legend = ""
        if self.parallel_groups:
            pg_items = "".join(
                f'<span class="pg-chip" style="background: {pg_colors[gi % len(pg_colors)]}; '
                f'border: 1px solid #ccc; padding: 2px 8px; border-radius: 4px; margin-right: 6px;">'
                f'Group {gi + 1}: {", ".join(html_mod.escape(str(s)) for s in g)}'
                f'</span>'
                for gi, g in enumerate(self.parallel_groups)
            )
            pg_legend = f'<div class="parallel-legend"><h3>Parallel Groups</h3>{pg_items}</div>'

        # --- Timeline ticks ---
        ticks = self._timeline_ticks(total_duration)
        timeline_html = "".join(f"<span>{t}</span>" for t in ticks)

        # --- Tasks JSON for potential JS consumers ---
        json.dumps(
            [
                {
                    "id": self._stage_id(s, i),
                    "name": s.get("name", f"Stage {i}"),
                    "start": s.get("start", 0),
                    "duration": s.get("duration", 1),
                    "critical": self._is_critical(s, i),
                }
                for i, s in enumerate(all_stages)
            ]
        )

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Process Model - Gantt Chart</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .gantt-container {{
            margin: 20px 0;
            overflow-x: auto;
        }}
        .gantt {{
            width: 100%;
            display: flex;
            border: 1px solid #ddd;
        }}
        .gantt-labels {{
            min-width: 200px;
            border-right: 1px solid #ddd;
            padding: 10px;
        }}
        .gantt-chart {{
            flex: 1;
            min-width: 600px;
            padding: 10px;
            background: #fafafa;
            position: relative;
        }}
        .gantt-row {{
            display: flex;
            align-items: center;
            height: 40px;
            border-bottom: 1px solid #eee;
        }}
        .gantt-label {{
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            padding-right: 10px;
        }}
        .gantt-bar {{
            height: 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 3px;
            position: relative;
            display: flex;
            align-items: center;
            padding: 0 10px;
            color: white;
            font-size: 12px;
            font-weight: bold;
            box-sizing: border-box;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
        }}
        .gantt-bar:hover {{
            opacity: 0.8;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}
        /* Critical path bars */
        .gantt-bar-critical {{
            background: linear-gradient(135deg, #e53e3e 0%, #c53030 100%);
            border: 2px solid #9b2c2c;
            box-shadow: 0 0 6px rgba(229, 62, 62, 0.4);
        }}
        .crit-badge {{
            display: inline-block;
            background: #e53e3e;
            color: white;
            font-size: 9px;
            font-weight: bold;
            padding: 1px 4px;
            border-radius: 3px;
            margin-left: 6px;
            vertical-align: middle;
        }}
        .timeline {{
            display: flex;
            justify-content: space-between;
            padding: 10px;
            background: #f0f0f0;
            border-top: 1px solid #ddd;
            font-size: 12px;
            color: #666;
        }}
        .dependencies {{
            margin-top: 30px;
        }}
        .dependency {{
            margin: 10px 0;
            padding: 10px;
            background: #f9f9f9;
            border-left: 3px solid #667eea;
            border-radius: 4px;
        }}
        .dependency strong {{
            color: #667eea;
        }}
        .parallel-legend {{
            margin-top: 20px;
            padding: 10px;
            background: #fafafa;
            border: 1px solid #eee;
            border-radius: 6px;
        }}
        .parallel-legend h3 {{
            margin-top: 0;
            color: #667eea;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Process Model - Gantt Chart</h1>

        <div class="gantt-container">
            <div class="gantt">
                <div class="gantt-labels">
                    {gantt_labels}
                </div>
                <div class="gantt-chart">
                    {gantt_bars}
                </div>
            </div>
            <div class="timeline">
                {timeline_html}
            </div>
        </div>

        {pg_legend}

        <div class="dependencies">
            <h2>Dependencies</h2>
            {dependencies_html}
        </div>

        <footer style="text-align: center; color: #999; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd;">
            <p>Generated by COGANT</p>
        </footer>
    </div>
</body>
</html>
"""
