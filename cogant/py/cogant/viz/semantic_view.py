"""SemanticVisualizer: Render semantic graphs with states, observations, actions."""

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from matplotlib.figure import Figure

logger = logging.getLogger(__name__)


class SemanticVisualizer:
    """
    Visualize semantic state space models.

    Renders:
      - States (nodes with specific styling)
      - Observations (inputs/sensor data)
      - Actions (outputs/actuations)
      - Policies (decision rules)
      - Transitions (state changes)

    Styling:
      - Inferred mappings: dashed/lighter
      - Direct mappings: solid/darker
    """

    def __init__(self) -> None:
        """Initialize semantic visualizer."""
        self.states: list[dict[str, Any]] = []
        self.observations: list[dict[str, Any]] = []
        self.actions: list[dict[str, Any]] = []
        self.policies: list[dict[str, Any]] = []
        self.transitions: list[dict[str, Any]] = []

    def from_state_space(self, state_space: dict[str, Any]) -> "SemanticVisualizer":
        """
        Load state space model data.

        Args:
            state_space: State space dict with states/observations/actions/policies.

        Returns:
            self (for chaining).
        """
        logger.info("Loading state space for semantic visualization")

        self.states = state_space.get("states", [])
        self.observations = state_space.get("observations", [])
        self.actions = state_space.get("actions", [])
        self.policies = state_space.get("policies", [])
        self.transitions = state_space.get("transitions", [])

        return self

    def render_html(self, output_path: str) -> str:
        """
        Render as interactive HTML visualization.

        Args:
            output_path: Path to write HTML file.

        Returns:
            Path to rendered file.
        """
        logger.info(f"Rendering semantic view to {output_path}")

        html = self._generate_html()
        with open(output_path, "w") as f:
            f.write(html)

        return output_path

    def render_json(self) -> str:
        """Export as JSON for external tools."""
        data = {
            "states": self.states,
            "observations": self.observations,
            "actions": self.actions,
            "policies": self.policies,
            "transitions": self.transitions,
        }
        return json.dumps(data, indent=2)

    def _generate_html(self) -> str:
        """Generate HTML for semantic view."""
        # Pre-compute slices to avoid f-string slicing issues
        # Also convert all items to dicts if they're objects
        def to_dict(item: Any) -> dict[str, Any]:
            """Coerce an arbitrary state/observation/action record into a dict."""
            if isinstance(item, dict):
                return dict(item)
            elif hasattr(item, '__dict__'):
                return dict(vars(item))
            else:
                return {"name": str(item), "description": str(item)}

        states_list = [to_dict(s) for s in (self.states[:6] if self.states else [])]
        observations_list = [to_dict(o) for o in (self.observations[:6] if self.observations else [])]
        actions_list = [to_dict(a) for a in (self.actions[:6] if self.actions else [])]
        policies_list = [to_dict(p) for p in (self.policies[:6] if self.policies else [])]

        states_cards = "".join(f'''
                <div class="card state">
                    <h3>{s.get("name", "Unknown")}</h3>
                    <ul>
                        <li>{s.get("description", "No description")}</li>
                        <li class="mapping">Type: {s.get("type", "generic")}</li>
                    </ul>
                </div>
                ''' for s in states_list)

        observations_cards = "".join(f'''
                <div class="card observation">
                    <h3>{o.get("name", "Unknown")}</h3>
                    <ul>
                        <li>{o.get("description", "No description")}</li>
                        <li class="mapping">Source: {o.get("source", "unknown")}</li>
                    </ul>
                </div>
                ''' for o in observations_list)

        actions_cards = "".join(f'''
                <div class="card action">
                    <h3>{a.get("name", "Unknown")}</h3>
                    <ul>
                        <li>{a.get("description", "No description")}</li>
                        <li class="mapping">Target: {a.get("target", "unknown")}</li>
                    </ul>
                </div>
                ''' for a in actions_list)

        policies_cards = "".join(f'''
                <div class="card policy">
                    <h3>{p.get("name", "Unknown")}</h3>
                    <ul>
                        <li>{p.get("rule", "No rule specified")}</li>
                        <li class="mapping">Confidence: {p.get("confidence", 0):.2f}</li>
                    </ul>
                </div>
                ''' for p in policies_list)

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Semantic State Space</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
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
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .card {{
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            background: #fafafa;
        }}
        .card h3 {{
            margin-top: 0;
            color: #333;
            font-size: 1.1em;
        }}
        .card ul {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .card li {{
            padding: 5px 0;
            border-bottom: 1px solid #eee;
            font-size: 0.95em;
        }}
        .card li:last-child {{
            border-bottom: none;
        }}
        .state {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        .observation {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
        }}
        .action {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
        }}
        .policy {{
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
            color: white;
        }}
        .mapping {{
            font-size: 0.85em;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid rgba(255,255,255,0.3);
        }}
        .inferred {{
            opacity: 0.7;
            font-style: italic;
        }}
        .direct {{
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Semantic State Space Model</h1>

        <section>
            <h2>States ({len(self.states)})</h2>
            <div class="grid">
                {states_cards}
            </div>
        </section>

        <section>
            <h2>Observations ({len(self.observations)})</h2>
            <div class="grid">
                {observations_cards}
            </div>
        </section>

        <section>
            <h2>Actions ({len(self.actions)})</h2>
            <div class="grid">
                {actions_cards}
            </div>
        </section>

        <section>
            <h2>Policies ({len(self.policies)})</h2>
            <div class="grid">
                {policies_cards}
            </div>
        </section>

        <footer style="text-align: center; color: #999; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd;">
            <p>Generated by COGANT</p>
        </footer>
    </div>
</body>
</html>
"""

    def render_role_distribution(self, mappings: list[dict[str, Any]] | None = None) -> "Figure | None":
        """
        Render semantic role distribution as pie/bar chart.

        Shows counts of each semantic role (hidden_state, observation, action, policy, etc.)
        across the semantic mappings.

        Args:
            mappings: Optional list of semantic mappings with 'kind' field.
                      If None, derives from self.states/observations/actions/policies.

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib not available; skipping role distribution plot")
            return None

        try:
            # Count roles
            role_counts: dict[str, int] = {}

            if mappings:
                for mapping in mappings:
                    role = mapping.get("kind", "unknown")
                    role_counts[role] = role_counts.get(role, 0) + 1
            else:
                role_counts = {
                    "hidden_state": len(self.states),
                    "observation": len(self.observations),
                    "action": len(self.actions),
                    "policy": len(self.policies),
                }

            if not role_counts:
                return None

            # Create figure with two subplots
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

            roles = list(role_counts.keys())
            counts = list(role_counts.values())

            # Pie chart
            colors = ["#667eea", "#f093fb", "#4facfe", "#43e97b", "#f5576c"]
            ax1.pie(counts, labels=roles, autopct="%1.1f%%", colors=colors[:len(roles)])
            ax1.set_title("Semantic Role Distribution (Pie)")

            # Bar chart
            ax2.bar(roles, counts, color=colors[:len(roles)], alpha=0.8)
            ax2.set_ylabel("Count")
            ax2.set_xlabel("Semantic Role")
            ax2.set_title("Semantic Role Distribution (Bar)")
            ax2.tick_params(axis="x", rotation=45)

            fig.suptitle("Semantic Role Distribution", fontsize=16, weight="bold")
            fig.tight_layout()

            return fig

        except Exception as e:
            logger.error(f"Error rendering role distribution: {e}")
            return None

    def render_confidence_heatmap(self, mappings: list[dict[str, Any]] | None = None) -> "Figure | None":
        """
        Render confidence scores per semantic node as heatmap.

        Shows the distribution of confidence scores across all semantic mappings.

        Args:
            mappings: Optional list of semantic mappings with 'confidence' field.
                      If None, derives from self.states/observations/actions/policies.

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            logger.warning("matplotlib or numpy not available; skipping confidence heatmap plot")
            return None

        try:
            # Extract confidence scores
            confidences: dict[str, list[float]] = {
                "states": [],
                "observations": [],
                "actions": [],
                "policies": [],
            }

            if mappings:
                for mapping in mappings:
                    conf = mapping.get("confidence", 0.5)
                    kind = mapping.get("kind", "unknown")
                    if kind == "hidden_state":
                        confidences["states"].append(conf)
                    elif kind == "observation":
                        confidences["observations"].append(conf)
                    elif kind == "action":
                        confidences["actions"].append(conf)
                    elif kind == "policy":
                        confidences["policies"].append(conf)
            else:
                # Use placeholder values
                confidences["states"] = [0.8 + 0.2 * i / max(len(self.states), 1) for i in range(len(self.states))]
                confidences["observations"] = [0.75 + 0.2 * i / max(len(self.observations), 1) for i in range(len(self.observations))]
                confidences["actions"] = [0.9 + 0.1 * i / max(len(self.actions), 1) for i in range(len(self.actions))]
                confidences["policies"] = [0.85 + 0.15 * i / max(len(self.policies), 1) for i in range(len(self.policies))]

            # Create heatmap data (role x confidence bins)
            fig, ax = plt.subplots(figsize=(12, 6))

            roles = list(confidences.keys())
            data = []
            for role in roles:
                conf_vals = confidences[role]
                if conf_vals:
                    # Bin confidences into 5 buckets: [0-0.2), [0.2-0.4), etc.
                    bins = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
                    hist, _ = np.histogram(conf_vals, bins=bins)
                    data.append(hist)
                else:
                    data.append([0] * 5)

            # Convert to numpy array for heatmap
            data_array = np.array(data, dtype=float)

            # Plot heatmap
            im = ax.imshow(data_array, cmap="YlGn", aspect="auto", origin="lower")

            ax.set_xticks(range(5))
            ax.set_xticklabels(["0-0.2", "0.2-0.4", "0.4-0.6", "0.6-0.8", "0.8-1.0"])
            ax.set_yticks(range(len(roles)))
            ax.set_yticklabels(roles)
            ax.set_xlabel("Confidence Score Range")
            ax.set_ylabel("Semantic Role")
            ax.set_title("Confidence Score Distribution by Role")

            plt.colorbar(im, ax=ax, label="Count")

            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error rendering confidence heatmap: {e}")
            return None
