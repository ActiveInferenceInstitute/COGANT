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

    The output shows hidden states (blue), observations (teal), and actions
    (orange) in a colorblind-safe layered layout with likelihood and control edges. Labels
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

        likelihood_edge_count = len(var_ids) * len(obs_ids)
        control_edge_count = len(var_ids) * len(act_ids)
        relation_edge_count = likelihood_edge_count + control_edge_count
        draw_full_edges = relation_edge_count <= cfg.max_render_edges
        aggregate_band_count = int(bool(var_ids and obs_ids)) + int(bool(act_ids and var_ids))
        if draw_full_edges:
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
            "state (s)": "#0072B2",
            "observation (o)": "#009E73",
            "action (u)": "#E69F00",
        }
        node_color_map = {"state": "#0072B2", "obs": "#009E73", "act": "#E69F00"}

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
        if draw_full_edges:
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
        else:
            if var_ids and obs_ids:
                ax.annotate(
                    "",
                    xy=(0.35, 0.88),
                    xytext=(0.35, 0.62),
                    arrowprops={
                        "arrowstyle": "->",
                        "color": "#2c3e50",
                        "lw": 4.0,
                        "alpha": 0.45,
                    },
                )
                ax.text(
                    0.37,
                    0.75,
                    f"A relations: {likelihood_edge_count}",
                    fontsize=cfg.edge_fontsize,
                    color="#2c3e50",
                    va="center",
                    bbox={
                        "boxstyle": "round,pad=0.25",
                        "facecolor": cfg.edge_label_bg,
                        "edgecolor": "none",
                    },
                )
            if act_ids and var_ids:
                ax.annotate(
                    "",
                    xy=(0.65, 0.46),
                    xytext=(0.65, 0.19),
                    arrowprops={
                        "arrowstyle": "->",
                        "color": "#2c3e50",
                        "lw": 4.0,
                        "alpha": 0.45,
                    },
                )
                ax.text(
                    0.67,
                    0.32,
                    f"B relations: {control_edge_count}",
                    fontsize=cfg.edge_fontsize,
                    color="#2c3e50",
                    va="center",
                    bbox={
                        "boxstyle": "round,pad=0.25",
                        "facecolor": cfg.edge_label_bg,
                        "edgecolor": "none",
                    },
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
        if minimal_labels and draw_full_edges:
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
            "likelihood_edges": likelihood_edge_count,
            "control_edges": control_edge_count,
            "drawn_relation_edges": (
                relation_edge_count if draw_full_edges else aggregate_band_count
            ),
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
                    "edge_draw_cap": cfg.max_render_edges,
                    "edge_draw_strategy": (
                        "full_relation_edges"
                        if draw_full_edges
                        else "aggregate_relation_bands"
                    ),
                },
                "panel_metadata": {
                    "panels": [
                        {
                            "key": "factor_graph",
                            "encoding": (
                                "blue hidden states, teal observations, "
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
    strict_real_matrices: bool = False,
) -> bool:
    """Render the structural A/B/C/D connection matrices as a 2×2 heatmap grid.

    Each quadrant is a small heatmap describing the shape of a canonical
    Active-Inference tensor: A (likelihood, |o|×|s|), B (transitions,
    |s|×|s|), C (preferences, |o|), D (prior, |s|). Real counts are used
    when available; uninhabited cells render as empty. Direct dev calls may
    fall back to deterministic shape proxies, but strict publication calls
    require every panel to come from ``matrix_source_json``.
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
        display_matrix_shapes: dict[str, list[int]] = {}
        matrix_reducers: dict[str, dict[str, Any]] = {}
        source_arrays: dict[str, Any] = {}
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
        matrix_validation_errors: list[str] = []
        if strict_real_matrices:
            try:
                from cogant.gnn.validator import GNNValidator

                matrix_validation_errors = GNNValidator().validate_matrices(payload)
            except Exception as exc:  # noqa: BLE001
                matrix_validation_errors = [f"matrix validation unavailable: {exc}"]
            if matrix_validation_errors:
                for stale in (output_png, output_png.with_suffix(".figure.json")):
                    try:
                        stale.unlink()
                    except FileNotFoundError:
                        pass
                    except OSError as exc:
                        logger.warning(
                            "Could not remove stale strict matrix artifact %s: %s",
                            stale,
                            exc,
                        )
                logger.warning(
                    "Connections matrix PNG requires structurally valid A/B/C/D values: %s",
                    "; ".join(matrix_validation_errors),
                )
                return False

        def _from_payload(key: str) -> Any | None:
            raw = None
            for candidate in (key, f"{key}_matrix", f"{key}_mat"):
                if candidate in payload:
                    raw = payload.get(candidate)
                    break
            if raw is None:
                return None
            try:
                arr = np.asarray(raw, dtype=float)
            except (TypeError, ValueError):
                return None
            if arr.size == 0:
                return None
            source_matrix_shapes[key] = [int(dim) for dim in arr.shape]
            source_arrays[key] = arr.copy()
            if key == "B" and arr.ndim == 3:
                matrix_reducers[key] = {
                    "method": "max_over_actions",
                    "axis": 2,
                    "source_action_count": int(arr.shape[2]),
                    "reason": "display a 2D transition summary from the exported 3D B tensor",
                }
                arr = arr.max(axis=2)
            if arr.ndim == 1:
                arr = arr.reshape((arr.shape[0], 1))
            if arr.ndim != 2:
                return None
            displayed = arr[
                : (n_o if key in {"A", "C"} else n_s), : (n_s if key in {"A", "B", "D"} else 1)
            ]
            display_matrix_shapes[key] = [int(dim) for dim in displayed.shape]
            return displayed

        A = _from_payload("A")
        B = _from_payload("B")
        C = _from_payload("C")
        D = _from_payload("D")
        matrices_by_key = {"A": A, "B": B, "C": C, "D": D}
        fallback_panels = [key for key, value in matrices_by_key.items() if value is None]
        matrix_values_from_artifact = not fallback_panels
        visual_source_label = source_label
        if matrix_values_from_artifact and matrix_source_json is not None:
            if matrix_source_json.parent.name == "gnn_package":
                visual_source_label = (
                    f"matrix source: {matrix_source_json.parent.parent.name}/"
                    f"gnn_package/{matrix_source_json.name}"
                )
            else:
                visual_source_label = f"matrix source: {matrix_source_json.name}"

        if strict_real_matrices and fallback_panels:
            for stale in (output_png, output_png.with_suffix(".figure.json")):
                try:
                    stale.unlink()
                except FileNotFoundError:
                    pass
                except OSError as exc:
                    logger.warning("Could not remove stale strict matrix artifact %s: %s", stale, exc)
            logger.warning(
                "Connections matrix PNG requires real A/B/C/D values; missing %s from %s",
                ", ".join(fallback_panels),
                matrix_source_json or "<no matrix source>",
            )
            return False

        if A is None:
            A = _mat(n_o, n_s, 11)  # likelihood shape proxy
        if B is None:
            B = _mat(n_s, n_s, 13)  # transition shape proxy
        if C is None:
            C = _mat(n_o, 1, 17)  # preference shape proxy
        if D is None:
            D = _mat(n_s, 1, 19)  # prior shape proxy

        rendered_matrices = {"A": A, "B": B, "C": C, "D": D}
        for key, matrix in rendered_matrices.items():
            display_matrix_shapes.setdefault(key, [int(dim) for dim in matrix.shape])
        matrix_shapes = {
            key: display_matrix_shapes[key]
            for key in ("A", "B", "C", "D")
        }

        fallback_source_matrix_shapes: dict[str, list[int]] = {
            "A": [original_n_o, original_n_s],
            "B": [original_n_s, original_n_s],
            "C": [original_n_o],
            "D": [original_n_s],
        }
        for key, fallback_shape in fallback_source_matrix_shapes.items():
            source_matrix_shapes.setdefault(key, fallback_shape)

        def _two_dim_source_shape(key: str) -> list[int]:
            shape = source_matrix_shapes.get(key, matrix_shapes[key])
            if key == "B" and len(shape) >= 2:
                return [shape[0], shape[1]]
            if len(shape) == 1:
                return [shape[0], 1]
            return shape[:2]

        def _float(value: Any) -> float:
            return round(float(value), 6)

        def _as_int_like(value: Any, default: int) -> int:
            if isinstance(value, bool):
                return default
            if isinstance(value, int):
                return value
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        def _generic_matrix_diagnostics(matrix: Any) -> dict[str, Any]:
            arr = np.asarray(matrix, dtype=float)
            flat = arr.ravel()
            total = int(flat.size)
            nonzero = int(np.count_nonzero(np.abs(flat) > 1e-12))
            unique_values = int(len(np.unique(np.round(flat, 12)))) if total else 0
            return {
                "cells": total,
                "nonzero_cells": nonzero,
                "zero_cells": total - nonzero,
                "nonzero_fraction": _float(nonzero / total) if total else 0.0,
                "zero_fraction": _float((total - nonzero) / total) if total else 0.0,
                "distinct_values": unique_values,
                "min": _float(np.min(flat)) if total else 0.0,
                "max": _float(np.max(flat)) if total else 0.0,
                "mean": _float(np.mean(flat)) if total else 0.0,
                "constant": unique_values <= 1,
                "all_zero": bool(total and nonzero == 0),
            }

        def _source_matrix_diagnostics(key: str) -> dict[str, Any]:
            raw = source_arrays.get(key, rendered_matrices[key])
            arr = np.asarray(raw, dtype=float)
            diagnostics = _generic_matrix_diagnostics(arr)
            if key == "A" and arr.ndim == 2:
                uniform_columns = int(
                    sum(
                        bool(np.allclose(arr[:, col], arr[0, col], atol=1e-12))
                        for col in range(arr.shape[1])
                    )
                )
                diagnostics.update(
                    {
                        "uniform_columns": uniform_columns,
                        "column_count": int(arr.shape[1]),
                        "uniform_column_fraction": _float(uniform_columns / arr.shape[1])
                        if arr.shape[1]
                        else 0.0,
                    }
                )
            elif key == "B" and arr.ndim == 3:
                identity_slices = 0
                square = arr.shape[0] == arr.shape[1]
                if square:
                    eye = np.eye(arr.shape[0])
                    identity_slices = int(
                        sum(
                            bool(np.allclose(arr[:, :, action], eye, atol=1e-12))
                            for action in range(arr.shape[2])
                        )
                    )
                diagnostics.update(
                    {
                        "identity_action_slices": identity_slices,
                        "action_slice_count": int(arr.shape[2]),
                        "identity_action_slice_fraction": _float(identity_slices / arr.shape[2])
                        if arr.shape[2]
                        else 0.0,
                    }
                )
            elif key == "D" and arr.ndim == 1:
                diagnostics["uniform_prior"] = bool(
                    arr.size and np.allclose(arr, arr[0], atol=1e-12)
                )
            elif key == "C" and arr.ndim == 1:
                diagnostics["zero_preference_vector"] = bool(
                    arr.size and np.allclose(arr, 0.0, atol=1e-12)
                )
            return diagnostics

        source_matrix_diagnostics = {
            key: _source_matrix_diagnostics(key)
            for key in ("A", "B", "C", "D")
        }
        panel_diagnostics = {
            key: _generic_matrix_diagnostics(matrix)
            for key, matrix in rendered_matrices.items()
        }
        for key in ("A", "B", "C", "D"):
            panel_diagnostics[key]["source_diagnostics"] = source_matrix_diagnostics[key]

        def _diagnostic_label(key: str) -> str:
            diagnostics = panel_diagnostics[key]
            base = (
                f"distinct={diagnostics['distinct_values']} | "
                f"nz={diagnostics['nonzero_cells']}/{diagnostics['cells']} | "
                f"min={diagnostics['min']:.3g} max={diagnostics['max']:.3g}"
            )
            source_diag = source_matrix_diagnostics[key]
            if key == "A" and "uniform_columns" in source_diag:
                base += (
                    f" | uniform cols={source_diag['uniform_columns']}/"
                    f"{source_diag['column_count']}"
                )
            elif key == "B" and "identity_action_slices" in source_diag:
                base += (
                    f" | B reducer=max over {source_diag['action_slice_count']} actions; "
                    f"id slices={source_diag['identity_action_slices']}"
                )
            elif key == "C" and source_diag.get("zero_preference_vector"):
                base += " | real zero preference vector"
            elif key == "D" and source_diag.get("uniform_prior"):
                base += " | uniform prior"
            return base

        matrix_hidden_states = _as_int_like(
            source_matrix_shapes.get("A", [0, 0])[1]
            if len(source_matrix_shapes.get("A", [])) >= 2
            else source_matrix_shapes.get("D", [original_n_s])[0],
            original_n_s,
        )
        matrix_observations = _as_int_like(
            source_matrix_shapes.get("A", [original_n_o])[0],
            original_n_o,
        )
        matrix_actions = _as_int_like(
            source_matrix_shapes.get("B", [0, 0, original_n_a])[2]
            if len(source_matrix_shapes.get("B", [])) >= 3
            else original_n_a,
            original_n_a,
        )
        dimension_alignment = {
            "state_space_hidden_states": original_n_s,
            "matrix_hidden_states": matrix_hidden_states,
            "state_space_observations": original_n_o,
            "matrix_observations": matrix_observations,
            "state_space_actions": original_n_a,
            "matrix_actions": matrix_actions,
            "hidden_states_match": original_n_s == matrix_hidden_states,
            "observations_match": original_n_o == matrix_observations,
            "actions_match": original_n_a == matrix_actions,
        }
        if strict_real_matrices and not all(
            bool(dimension_alignment[key])
            for key in ("hidden_states_match", "observations_match", "actions_match")
        ):
            for stale in (output_png, output_png.with_suffix(".figure.json")):
                try:
                    stale.unlink()
                except FileNotFoundError:
                    pass
                except OSError as exc:
                    logger.warning("Could not remove stale strict matrix artifact %s: %s", stale, exc)
            logger.warning(
                "Connections matrix PNG requires matrix dimensions to match state_space.json; "
                "alignment=%s source=%s",
                dimension_alignment,
                matrix_source_json or "<no matrix source>",
            )
            return False

        fig_size = (max(cfg.figsize[0], 18.0), max(cfg.figsize[1], 13.0))
        fig, axes = plt.subplots(2, 2, figsize=fig_size)
        cmaps = ["Blues", "Greens", "Oranges", "Purples"]

        def _shape_label(name: str, displayed: tuple[int, int], real: tuple[int, int]) -> str:
            if displayed == real:
                return f"{name}  {displayed[0]}×{displayed[1]}"
            return f"{name}  {displayed[0]}×{displayed[1]}  (of {real[0]}×{real[1]})"

        mats = [
            ("A", "A — likelihood (o | s)", A, cmaps[0]),
            ("B", "B — transition (s' | s)", B, cmaps[1]),
            ("C", "C — preference (o)", C, cmaps[2]),
            ("D", "D — prior (s)", D, cmaps[3]),
        ]
        for ax, (key, name, m, cmap) in zip(axes.flat, mats, strict=False):
            im = ax.imshow(m, aspect="auto", cmap=cmap)
            ax.set_title(
                _shape_label(
                    name,
                    tuple(display_matrix_shapes[key]),  # type: ignore[arg-type]
                    tuple(_two_dim_source_shape(key)),  # type: ignore[arg-type]
                )
                + "\n"
                + _diagnostic_label(key),
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
        if visual_source_label:
            fig.text(
                0.5,
                0.945,
                visual_source_label,
                ha="center",
                va="top",
                fontsize=cfg.subtitle_fontsize,
                color="#555555",
            )
        draw_footer(fig, source=visual_source_label or "state_space", cfg=cfg)
        plt.tight_layout(rect=(0, 0.03, 1, 0.93))
        output_png.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_png, dpi=cfg.dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        displayed_counts = {
            "matrices": 4,
            "hidden_states": matrix_hidden_states,
            "observations": matrix_observations,
            "actions": matrix_actions,
            "source_hidden_states": matrix_hidden_states,
            "source_observations": matrix_observations,
            "source_actions": matrix_actions,
            "state_space_hidden_states": original_n_s,
            "state_space_observations": original_n_o,
            "state_space_actions": original_n_a,
        }
        panel_sources = {
            key: ("shape_proxy" if key in fallback_panels else "matrix_source_artifact")
            for key in ("A", "B", "C", "D")
        }
        panel_rows: list[dict[str, Any]] = []
        for key, matrix_shape in matrix_shapes.items():
            row: dict[str, Any] = {
                "key": key,
                "shape": matrix_shape,
                "displayed_shape": display_matrix_shapes.get(key, matrix_shape),
                "source_shape": source_matrix_shapes.get(key),
                "source": panel_sources[key],
                "diagnostics": panel_diagnostics.get(key, {}),
            }
            if key in matrix_reducers:
                row["reducer"] = matrix_reducers[key]
            panel_rows.append(row)
        if fallback_panels:
            limitations = (
                "Panels listed in fallback_panels use deterministic shape proxies for direct "
                "developer inspection only; publication/manuscript renders require exported "
                "matrix values."
            )
        else:
            limitations = (
                "Heatmaps show exported matrix values from matrix_source_artifact. The B panel "
                "summarizes the exported transition tensor using the recorded reducer."
            )
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
                "matrix_source_artifact_digest": sha256_file(matrix_source_json)
                if matrix_source_json
                else None,
                "source_artifact_digest": sha256_file(matrix_source_json)
                if matrix_source_json
                else None,
                "strict_real_matrices": strict_real_matrices,
                "layout_method": "fixed 2x2 matrix heatmap grid",
                "layout_seed": None,
                "displayed_counts": displayed_counts,
                "displayed_count_checks": {
                    "hidden_states_match_source": dimension_alignment["hidden_states_match"],
                    "observations_match_source": dimension_alignment["observations_match"],
                    "actions_match_source": dimension_alignment["actions_match"],
                    "tick_cap": tick_cap,
                    "downsampled": any(
                        source_matrix_shapes[key] != display_matrix_shapes[key]
                        for key in ("A", "B", "C", "D")
                        if len(source_matrix_shapes.get(key, [])) == 2
                    ),
                },
                "state_space_counts": {
                    "hidden_states": original_n_s,
                    "observations": original_n_o,
                    "actions": original_n_a,
                },
                "matrix_dimensions": {
                    "hidden_states": matrix_hidden_states,
                    "observations": matrix_observations,
                    "actions": matrix_actions,
                },
                "dimension_alignment": dimension_alignment,
                "matrix_values_from_artifact": matrix_values_from_artifact,
                "matrix_validation_errors": matrix_validation_errors,
                "fallback_panels": fallback_panels,
                "degraded_panels": [],
                "panel_sources": panel_sources,
                "matrix_shapes": matrix_shapes,
                "source_matrix_shapes": source_matrix_shapes,
                "display_matrix_shapes": display_matrix_shapes,
                "displayed_matrix_shapes": display_matrix_shapes,
                "source_matrix_diagnostics": source_matrix_diagnostics,
                "panel_diagnostics": panel_diagnostics,
                "matrix_reducers": matrix_reducers,
                "panel_metadata": {
                    "panels": panel_rows,
                },
                "panels": panel_rows,
                "limitations": limitations,
                "known_limitations": limitations,
            },
            cfg,
        )
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("Connections matrix PNG failed: %s", e)
        return False
