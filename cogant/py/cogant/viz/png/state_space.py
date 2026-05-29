from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, cast

from cogant.viz.png.config import (
    DEFAULT_CONFIG,
    RenderConfig,
    draw_color_legend,
    draw_footer,
    draw_metadata_banner,
    sha256_file,
    truncate,
    write_figure_sidecar,
)

logger = logging.getLogger(__name__)


def _state_space_entities(
    state_space: Any,
) -> tuple[list[Any], list[Any], list[Any]]:
    """Return (variables, observations, actions) from a StateSpaceModel.

    Accepts both the dataclass (``variables`` / ``observations`` / ``actions``)
    and the Pydantic (``state_variables`` / ``observation_modalities``) shapes.
    """
    variables_raw = (
        getattr(state_space, "variables", None)
        or getattr(state_space, "state_variables", None)
        or {}
    )
    observations_raw = (
        getattr(state_space, "observations", None)
        or getattr(state_space, "observation_modalities", None)
        or {}
    )
    actions_raw = getattr(state_space, "actions", None) or {}
    variables = (
        list(variables_raw.values()) if isinstance(variables_raw, dict) else list(variables_raw)
    )
    observations = (
        list(observations_raw.values())
        if isinstance(observations_raw, dict)
        else list(observations_raw)
    )
    actions = list(actions_raw.values()) if isinstance(actions_raw, dict) else list(actions_raw)
    return variables, observations, actions


def render_state_space_factor_png(
    state_space: Any,
    output_png: Path,
    *,
    cfg: RenderConfig | None = None,
    figsize: tuple[float, float] | None = None,
    dpi: int | None = None,
    source_label: str | None = None,
) -> bool:
    """Render a StateSpaceModel as a factor-graph PNG (matplotlib + networkx).

    The output shows hidden states (blue), observations (green), and actions
    (orange) in a layered layout with likelihood and control edges. Labels
    use actual variable names, not ``s0``/``o1`` placeholders, and the banner
    reports cardinality and factor counts.
    """
    cfg = cfg or DEFAULT_CONFIG
    figsize = figsize or cfg.figsize
    dpi = dpi or cfg.dpi

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import networkx as nx
    except ImportError:
        return False

    if state_space is None:
        return False

    try:
        variables, observations, actions = _state_space_entities(state_space)
        if not variables and not observations and not actions:
            return False

        original_var_n = len(variables)
        original_obs_n = len(observations)
        original_act_n = len(actions)

        # Cap per-layer sizes so the factor graph stays legible and the
        # likelihood edge set never explodes past ~(layer_cap^2). For a repo
        # with 1200 observations and 200 variables, the uncapped graph would
        # have ~240k edges and hang matplotlib; we take the first ``layer_cap``
        # entries from each list (the state-space compiler preserves insertion
        # order, so this keeps the earliest-registered variables).
        layer_cap = max(1, min(cfg.max_render_nodes // 3, 80))
        variables = list(variables)[:layer_cap]
        observations = list(observations)[:layer_cap]
        actions = list(actions)[:layer_cap]

        g = nx.DiGraph()
        var_ids: list[str] = []
        obs_ids: list[str] = []
        act_ids: list[str] = []

        def _display_name(obj: Any, fallback: str) -> str:
            return str(getattr(obj, "name", None) or getattr(obj, "id", None) or fallback)

        def _cardinality(obj: Any) -> int | None:
            return getattr(obj, "cardinality", None) or getattr(obj, "size", None)

        for i, v in enumerate(variables):
            name = _display_name(v, f"s_{i}")
            card = _cardinality(v)
            vid = f"s:{name}"
            var_ids.append(vid)
            g.add_node(
                vid,
                label=f"s\n{truncate(name, 16)}" + (f"\n|{card}|" if card else ""),
                kind="state",
            )
        for i, o in enumerate(observations):
            name = _display_name(o, f"o_{i}")
            card = _cardinality(o)
            oid = f"o:{name}"
            obs_ids.append(oid)
            g.add_node(
                oid,
                label=f"o\n{truncate(name, 16)}" + (f"\n|{card}|" if card else ""),
                kind="obs",
            )
        for i, a in enumerate(actions):
            name = _display_name(a, f"u_{i}")
            aid = f"u:{name}"
            act_ids.append(aid)
            g.add_node(aid, label=f"u\n{truncate(name, 16)}", kind="act")

        # Likelihood edges connect every (state, obs) pair, which is quadratic
        # in layer size. For the default ``layer_cap=80`` this yields up to
        # 6400 edges which still renders in ~1 s. Any cap above that and the
        # factor graph becomes visually unreadable anyway.
        for vid in var_ids:
            for oid in obs_ids:
                g.add_edge(vid, oid, kind="likelihood (A)")
            for aid in act_ids:
                g.add_edge(aid, vid, kind="control (B)")

        pos: dict[str, tuple[float, float]] = {}

        def _layer(ids: list[str], y: float) -> None:
            n = max(len(ids), 1)
            for i, nid in enumerate(ids):
                pos[nid] = ((i + 1) / (n + 1), y)

        _layer(obs_ids, 0.95)
        _layer(var_ids, 0.55)
        _layer(act_ids, 0.12)

        color_by = {
            "state (s)": "#8e44ad",
            "observation (o)": "#27ae60",
            "action (u)": "#e67e22",
        }
        node_color_map = {"state": "#8e44ad", "obs": "#27ae60", "act": "#e67e22"}

        fig, ax = plt.subplots(figsize=figsize)
        for kind, color in node_color_map.items():
            ids = [n_ for n_, data in g.nodes(data=True) if data.get("kind") == kind]
            if ids:
                nx.draw_networkx_nodes(
                    g,
                    pos,
                    nodelist=ids,
                    node_color=color,
                    node_size=cfg.node_size,
                    alpha=0.95,
                    edgecolors="#222222",
                    linewidths=1.3,
                    ax=ax,
                )
        nx.draw_networkx_edges(
            g,
            pos,
            edge_color="#2c3e50",
            arrows=True,
            arrowsize=18,
            width=1.3,
            alpha=0.75,
            connectionstyle="arc3,rad=0.07",
            ax=ax,
        )
        nx.draw_networkx_labels(
            g,
            pos,
            labels={n_: g.nodes[n_].get("label", n_) for n_ in g.nodes()},
            font_size=cfg.node_fontsize - 1,
            font_color="white",
            font_weight="bold",
            ax=ax,
        )
        edge_kind_labels = {(u, v): d.get("kind", "") for u, v, d in g.edges(data=True)}
        # Only label a subset to avoid clutter: label the first control/likelihood edge only.
        seen_kinds: set[str] = set()
        minimal_labels: dict[tuple[str, str], str] = {}
        for key, k in edge_kind_labels.items():
            if k and k not in seen_kinds:
                minimal_labels[key] = k
                seen_kinds.add(k)
        if minimal_labels:
            nx.draw_networkx_edge_labels(
                g,
                pos,
                edge_labels=minimal_labels,
                font_size=cfg.edge_fontsize,
                bbox={
                    "boxstyle": "round,pad=0.25",
                    "facecolor": cfg.edge_label_bg,
                    "edgecolor": "none",
                },
                ax=ax,
            )

        ax.set_xlim(-0.05, 1.05)
        ax.set_ylim(-0.1, 1.15)
        ax.set_axis_off()

        def _fmt_count(displayed: int, real: int) -> str:
            return f"{displayed}" if displayed == real else f"{displayed}/{real}"

        draw_metadata_banner(
            ax,
            title="State-Space Factor Graph",
            subtitle=source_label,
            stats={
                "states (s)": _fmt_count(len(var_ids), original_var_n),
                "obs (o)": _fmt_count(len(obs_ids), original_obs_n),
                "actions (u)": _fmt_count(len(act_ids), original_act_n),
            },
            cfg=cfg,
        )
        draw_color_legend(ax, color_by, title="Factors", cfg=cfg)
        draw_footer(fig, source=source_label or "state_space", cfg=cfg)

        plt.tight_layout(rect=(0, 0.02, 1, 0.97))
        output_png.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_png, dpi=dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        displayed_counts = {
            "hidden_states": len(var_ids),
            "observations": len(obs_ids),
            "actions": len(act_ids),
            "likelihood_edges": len(var_ids) * len(obs_ids),
            "control_edges": len(var_ids) * len(act_ids),
            "source_hidden_states": original_var_n,
            "source_observations": original_obs_n,
            "source_actions": original_act_n,
        }
        write_figure_sidecar(
            output_png,
            {
                "renderer": "cogant.viz.png.render_state_space_factor_png",
                "method": (
                    "Layered factor graph over compiled hidden-state, observation, "
                    "and action factors."
                ),
                "source_artifact": source_label,
                "layout_method": "deterministic layered factor layout",
                "layout_seed": None,
                "displayed_counts": displayed_counts,
                "displayed_count_checks": {
                    "hidden_states_match_source": len(var_ids) == original_var_n,
                    "observations_match_source": len(obs_ids) == original_obs_n,
                    "actions_match_source": len(act_ids) == original_act_n,
                    "layer_cap": layer_cap,
                    "downsampled": (
                        len(var_ids) != original_var_n
                        or len(obs_ids) != original_obs_n
                        or len(act_ids) != original_act_n
                    ),
                },
                "panel_metadata": {
                    "panels": [
                        {
                            "key": "factor_graph",
                            "encoding": (
                                "purple hidden states, green observations, "
                                "orange actions, directed A/B relation edges"
                            ),
                            "displayed_counts": displayed_counts,
                        }
                    ]
                },
                "limitations": (
                    "Displays compiled factors and relation opportunities; it is "
                    "not a proof of behavioral adequacy or complete runtime coverage."
                ),
                "known_limitations": (
                    "Displays compiled factors and relation opportunities; it is "
                    "not a proof of behavioral adequacy or complete runtime coverage."
                ),
            },
            cfg,
        )
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("State-space factor PNG failed: %s", e)
        return False


def render_connections_matrix_png(
    state_space: Any,
    output_png: Path,
    *,
    cfg: RenderConfig | None = None,
    source_label: str | None = None,
    matrix_source_json: Path | None = None,
) -> bool:
    """Render the structural A/B/C/D connection matrices as a 2×2 heatmap grid.

    Each quadrant is a small heatmap describing the shape of a canonical
    Active-Inference tensor: A (likelihood, |o|×|s|), B (transitions,
    |s|×|s|), C (preferences, |o|), D (prior, |s|). Real counts are used
    when available; uninhabited cells render as empty.
    """
    cfg = cfg or DEFAULT_CONFIG
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np  # type: ignore[import-not-found,unused-ignore]
    except ImportError:
        return False

    if state_space is None:
        return False

    try:
        variables, observations, actions = _state_space_entities(state_space)
        original_n_s = max(len(variables), 1)
        original_n_o = max(len(observations), 1)
        original_n_a = max(len(actions), 1)

        # Cap the *visualised* matrix shape so the renderer never hangs on a
        # repo with thousands of mapped variables. The true counts are still
        # surfaced in the banner; we just render the top-K rows/cols.
        tick_cap = 60
        n_s = min(original_n_s, tick_cap)
        n_o = min(original_n_o, tick_cap)

        def _mat(rows: int, cols: int, rng_seed: int) -> Any:
            rng = np.random.default_rng(rng_seed)
            m = rng.random((rows, cols))
            m = m / max(m.sum(axis=0, keepdims=True).max(), 1e-9)
            return m

        source_matrix_shapes: dict[str, list[int]] = {}
        matrix_values_from_artifact = False

        def _matrix_payload(path: Path | None) -> dict[str, Any]:
            if path is None or not path.is_file():
                return {}
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return {}
            if isinstance(payload, dict) and isinstance(payload.get("matrices"), dict):
                return cast(dict[str, Any], payload["matrices"])
            return payload if isinstance(payload, dict) else {}

        payload = _matrix_payload(matrix_source_json)

        def _from_payload(key: str) -> Any | None:
            raw = payload.get(key) or payload.get(f"{key}_matrix") or payload.get(f"{key}_mat")
            if raw is None:
                return None
            try:
                arr = np.asarray(raw, dtype=float)
            except (TypeError, ValueError):
                return None
            if arr.size == 0:
                return None
            source_matrix_shapes[key] = [int(dim) for dim in arr.shape]
            if key == "B" and arr.ndim == 3:
                arr = arr.max(axis=2)
            if arr.ndim == 1:
                arr = arr.reshape((arr.shape[0], 1))
            if arr.ndim != 2:
                return None
            return arr[
                : (n_o if key in {"A", "C"} else n_s), : (n_s if key in {"A", "B", "D"} else 1)
            ]

        A = _from_payload("A")
        B = _from_payload("B")
        C = _from_payload("C")
        D = _from_payload("D")
        matrix_values_from_artifact = all(m is not None for m in (A, B, C, D))
        if A is None:
            A = _mat(n_o, n_s, 11)  # likelihood shape proxy
        if B is None:
            B = _mat(n_s, n_s, 13)  # transition shape proxy
        if C is None:
            C = _mat(n_o, 1, 17)  # preference shape proxy
        if D is None:
            D = _mat(n_s, 1, 19)  # prior shape proxy

        fig, axes = plt.subplots(2, 2, figsize=cfg.figsize)
        cmaps = ["Blues", "Greens", "Oranges", "Purples"]

        def _shape_label(name: str, displayed: tuple[int, int], real: tuple[int, int]) -> str:
            if displayed == real:
                return f"{name}  {displayed[0]}×{displayed[1]}"
            return f"{name}  {displayed[0]}×{displayed[1]}  (of {real[0]}×{real[1]})"

        mats = [
            ("A — likelihood (o | s)", A, cmaps[0], (n_o, n_s), (original_n_o, original_n_s)),
            ("B — transition (s' | s)", B, cmaps[1], (n_s, n_s), (original_n_s, original_n_s)),
            ("C — preference (o)", C, cmaps[2], (n_o, 1), (original_n_o, 1)),
            ("D — prior (s)", D, cmaps[3], (n_s, 1), (original_n_s, 1)),
        ]
        for ax, (name, m, cmap, shape, real_shape) in zip(axes.flat, mats, strict=False):
            im = ax.imshow(m, aspect="auto", cmap=cmap)
            ax.set_title(
                _shape_label(name, shape, real_shape),
                fontsize=cfg.subtitle_fontsize,
            )
            # Only draw ticks when the matrix is small enough to be readable;
            # beyond ~40 ticks per axis, matplotlib spends quadratic time on
            # layout for diminishing visual benefit.
            if m.shape[1] <= 40:
                ax.set_xticks(range(m.shape[1]))
            if m.shape[0] <= 40:
                ax.set_yticks(range(m.shape[0]))
            ax.tick_params(axis="both", labelsize=cfg.edge_fontsize)
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        fig.suptitle(
            "Connection Matrices (A/B/C/D)",
            fontsize=cfg.title_fontsize,
            fontweight="bold",
            color="#1a1a1a",
        )
        if source_label:
            fig.text(
                0.5,
                0.945,
                source_label,
                ha="center",
                va="top",
                fontsize=cfg.subtitle_fontsize,
                color="#555555",
            )
        draw_footer(fig, source=source_label or "state_space", cfg=cfg)
        plt.tight_layout(rect=(0, 0.03, 1, 0.93))
        output_png.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_png, dpi=cfg.dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        matrix_shapes = {
            "A": [n_o, n_s],
            "B": [n_s, n_s],
            "C": [n_o, 1],
            "D": [n_s, 1],
        }
        fallback_source_matrix_shapes: dict[str, list[int]] = {
            "A": [original_n_o, original_n_s],
            "B": [original_n_s, original_n_s],
            "C": [original_n_o, 1],
            "D": [original_n_s, 1],
        }
        for key, fallback_shape in fallback_source_matrix_shapes.items():
            source_matrix_shapes.setdefault(key, fallback_shape)
        displayed_counts = {
            "matrices": 4,
            "hidden_states": n_s,
            "observations": n_o,
            "actions": original_n_a,
            "source_hidden_states": original_n_s,
            "source_observations": original_n_o,
            "source_actions": original_n_a,
        }
        write_figure_sidecar(
            output_png,
            {
                "renderer": "cogant.viz.png.render_connections_matrix_png",
                "method": (
                    "Four-panel heatmap rendering of canonical A/B/C/D matrix "
                    "shapes and values when a model.gnn.json matrix artifact is supplied."
                ),
                "source_artifact": source_label,
                "matrix_source_artifact": str(matrix_source_json) if matrix_source_json else None,
                "source_artifact_digest": sha256_file(matrix_source_json)
                if matrix_source_json
                else None,
                "layout_method": "fixed 2x2 matrix heatmap grid",
                "layout_seed": None,
                "displayed_counts": displayed_counts,
                "displayed_count_checks": {
                    "hidden_states_match_source": n_s == original_n_s,
                    "observations_match_source": n_o == original_n_o,
                    "tick_cap": tick_cap,
                    "downsampled": n_s != original_n_s or n_o != original_n_o,
                },
                "matrix_values_from_artifact": matrix_values_from_artifact,
                "matrix_shapes": matrix_shapes,
                "source_matrix_shapes": source_matrix_shapes,
                "panel_metadata": {
                    "panels": [{"key": key, "shape": shape} for key, shape in matrix_shapes.items()]
                },
                "limitations": (
                    "Heatmaps show exported matrix values when available; otherwise "
                    "they show deterministic shape proxies. Machine validation uses exported JSON."
                ),
                "known_limitations": (
                    "Heatmaps show exported matrix values when available; otherwise "
                    "they show deterministic shape proxies. Machine validation uses exported JSON."
                ),
            },
            cfg,
        )
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("Connections matrix PNG failed: %s", e)
        return False
