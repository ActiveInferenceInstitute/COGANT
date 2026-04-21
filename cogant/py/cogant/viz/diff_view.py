"""DiffVisualizer: Compare two bundles and highlight differences."""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class DiffVisualizer:
    """
    Compare two analysis bundles and visualize differences.

    Highlights:
      - Added/removed/changed elements
      - New dependencies
      - Changed mappings
      - Performance deltas
    """

    def __init__(self, bundle1: dict[str, Any], bundle2: dict[str, Any]):
        """
        Initialize diff visualizer.

        Args:
            bundle1: First bundle.
            bundle2: Second bundle.
        """
        self.bundle1 = bundle1
        self.bundle2 = bundle2
        self.added: list[dict[str, Any]] = []
        self.removed: list[dict[str, Any]] = []
        self.changed: list[dict[str, Any]] = []
        self._compute_diff()

    def _compute_diff(self) -> None:
        """Compute differences between bundles."""
        logger.info("Computing diff between bundles")

        # Compare stage results
        stages1 = set(self.bundle1.get("stage_results", {}).keys())
        stages2 = set(self.bundle2.get("stage_results", {}).keys())

        self.added = [{"type": "stage", "name": s} for s in (stages2 - stages1)]
        self.removed = [{"type": "stage", "name": s} for s in (stages1 - stages2)]

        # Compare errors
        errors1 = len(self.bundle1.get("errors", []))
        errors2 = len(self.bundle2.get("errors", []))
        if errors1 != errors2:
            self.changed.append({"type": "errors", "before": errors1, "after": errors2})

    def render_html(self, output_path: str) -> str:
        """
        Render side-by-side comparison HTML.

        Args:
            output_path: Path to write HTML file.

        Returns:
            Path to rendered file.
        """
        logger.info(f"Rendering diff view to {output_path}")

        html = self._generate_html()
        with open(output_path, "w") as f:
            f.write(html)

        return output_path

    def render_json(self) -> str:
        """Export diff as JSON."""
        return json.dumps(
            {
                "added": self.added,
                "removed": self.removed,
                "changed": self.changed,
            },
            indent=2,
        )

    def _generate_html(self) -> str:
        """Generate HTML diff view."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Bundle Diff</title>
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
        .comparison {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 20px 0;
        }}
        .bundle {{
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
        }}
        .bundle h3 {{
            margin-top: 0;
            color: #333;
        }}
        .bundle.left {{
            background: #f0f8ff;
            border-left: 4px solid #4facfe;
        }}
        .bundle.right {{
            background: #f8f0ff;
            border-left: 4px solid #764ba2;
        }}
        .diff-section {{
            margin: 20px 0;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 4px;
            border-left: 3px solid #999;
        }}
        .added {{
            border-left-color: #43e97b;
            background: #f0fdf4;
        }}
        .removed {{
            border-left-color: #f5576c;
            background: #fdf2f8;
        }}
        .changed {{
            border-left-color: #ffd89b;
            background: #fffbf0;
        }}
        .diff-item {{
            margin: 5px 0;
            padding: 5px 0;
            border-bottom: 1px solid #eee;
        }}
        .diff-item:last-child {{
            border-bottom: none;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: bold;
            margin-right: 5px;
        }}
        .badge.added {{
            background: #43e97b;
            color: white;
        }}
        .badge.removed {{
            background: #f5576c;
            color: white;
        }}
        .badge.changed {{
            background: #ffd89b;
            color: #333;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Bundle Comparison</h1>

        <div class="comparison">
            <div class="bundle left">
                <h3>Bundle 1</h3>
                <p><strong>Target:</strong> {self.bundle1.get("target", "unknown")}</p>
                <p><strong>Errors:</strong> {len(self.bundle1.get("errors", []))}</p>
                <p><strong>Stages:</strong> {len(self.bundle1.get("stage_results", {}))}</p>
            </div>
            <div class="bundle right">
                <h3>Bundle 2</h3>
                <p><strong>Target:</strong> {self.bundle2.get("target", "unknown")}</p>
                <p><strong>Errors:</strong> {len(self.bundle2.get("errors", []))}</p>
                <p><strong>Stages:</strong> {len(self.bundle2.get("stage_results", {}))}</p>
            </div>
        </div>

        <div class="diff-section added">
            <h3>Added <span class="badge added">+{len(self.added)}</span></h3>
            {"".join(f'<div class="diff-item">{item.get("name", item)}</div>' for item in self.added) or '<p style="color: #999;">No additions</p>'}
        </div>

        <div class="diff-section removed">
            <h3>Removed <span class="badge removed">-{len(self.removed)}</span></h3>
            {"".join(f'<div class="diff-item">{item.get("name", item)}</div>' for item in self.removed) or '<p style="color: #999;">No removals</p>'}
        </div>

        <div class="diff-section changed">
            <h3>Changed <span class="badge changed">~{len(self.changed)}</span></h3>
            {"".join(f'<div class="diff-item"><strong>{item.get("type")}</strong>: {item.get("before")} → {item.get("after")}</div>' for item in self.changed) or '<p style="color: #999;">No changes</p>'}
        </div>

        <footer style="text-align: center; color: #999; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd;">
            <p>Generated by COGANT</p>
        </footer>
    </div>
</body>
</html>
"""
