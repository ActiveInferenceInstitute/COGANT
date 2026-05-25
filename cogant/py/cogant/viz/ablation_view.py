"""Measured rule-family + fixpoint ablation visualization.

Renders a single deterministic publication PNG from the ``ablation`` block of
``cogant/evaluation/METRICS.yaml`` (produced by
``tools/regenerate_ablation.py``). Two panels:

* **Rule-family deltas** — grouped bars of the *net* mapping delta per rule
  family, per fixture (how many ``SemanticMapping`` records are lost when
  that family's rules are withheld and the engine is re-run).
* **Fixpoint convergence** — mappings vs. iteration cap ``K`` per fixture.

The figure visualizes *measured net per-family totals*; it deliberately does
not decompose deltas per ``MappingKind`` (the harness does not emit that).

Pure matplotlib (Agg), no network, deterministic byte output: fixtures and
families are rendered in a fixed sorted order with a fixed colour-blind-safe
palette and no timestamps embedded in the image.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Fixed family order + Okabe-Ito colour-blind-safe palette (deterministic).
_FAMILY_ORDER: tuple[str, ...] = (
    "structural",
    "semantic",
    "control",
    "behavioral",
    "resilience",
)
_FAMILY_COLORS: dict[str, str] = {
    "structural": "#0072B2",
    "semantic": "#D55E00",
    "control": "#009E73",
    "behavioral": "#CC79A7",
    "resilience": "#E69F00",
}
_FIXPOINT_KS: tuple[tuple[str, int], ...] = (("k1", 1), ("k2", 2), ("k5", 5), ("k10", 10))
# Fixed deterministic line palette (no colormap lookup → stable + mypy-clean).
_LINE_COLORS: tuple[str, ...] = (
    "#0072B2",
    "#D55E00",
    "#009E73",
    "#CC79A7",
    "#E69F00",
    "#56B4E9",
    "#F0E442",
    "#000000",
)


def _load_ablation(metrics_path: Path) -> dict[str, Any]:
    """Return the ``ablation`` mapping from a METRICS.yaml file."""
    data = yaml.safe_load(metrics_path.read_text(encoding="utf-8")) or {}
    ablation = data.get("ablation")
    if not isinstance(ablation, dict):
        raise ValueError(f"no 'ablation' block in {metrics_path}")
    return ablation


def render_ablation_png(metrics_path: Path, output_png: Path, *, dpi: int = 150) -> Path:
    """Render the measured ablation figure to ``output_png``.

    Args:
        metrics_path: Path to ``METRICS.yaml`` containing an ``ablation`` block.
        output_png: Destination PNG path (parent dirs are created).
        dpi: Raster resolution.

    Returns:
        ``output_png`` on success.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ablation = _load_ablation(metrics_path)
    rule_family: dict[str, Any] = ablation.get("rule_family", {})
    fixpoint: dict[str, Any] = ablation.get("fixpoint", {})

    fixtures = sorted(rule_family)
    output_png.parent.mkdir(parents=True, exist_ok=True)

    fig, (ax_rf, ax_fp) = plt.subplots(1, 2, figsize=(14, 5.5))

    # --- Panel 1: rule-family net deltas (grouped bars) ---------------------
    n_fam = len(_FAMILY_ORDER)
    group_width = 0.8
    bar_w = group_width / n_fam
    for fam_idx, family in enumerate(_FAMILY_ORDER):
        xs = [i - group_width / 2 + bar_w * (fam_idx + 0.5) for i in range(len(fixtures))]
        ys = [int(rule_family[fx].get(f"{family}_delta", 0)) for fx in fixtures]
        ax_rf.bar(
            xs,
            ys,
            width=bar_w,
            color=_FAMILY_COLORS[family],
            label=family,
            edgecolor="white",
            linewidth=0.4,
        )
    ax_rf.set_xticks(range(len(fixtures)))
    ax_rf.set_xticklabels(fixtures, rotation=30, ha="right", fontsize=9)
    ax_rf.set_ylabel("Net mapping delta when family removed", fontsize=10)
    ax_rf.set_title(
        "Measured rule-family ablation\n(baseline minus rule_filter-restricted run)",
        fontsize=11,
    )
    ax_rf.legend(title="rule family", fontsize=8, title_fontsize=9, frameon=False)
    ax_rf.grid(axis="y", linestyle=":", alpha=0.4)
    for fx_idx, fx in enumerate(fixtures):
        base = rule_family[fx].get("baseline_mappings_total")
        if base is not None:
            ax_rf.annotate(
                f"n={base}",
                (fx_idx, ax_rf.get_ylim()[1] * 0.96),
                ha="center",
                va="top",
                fontsize=7,
                color="#444444",
            )

    # --- Panel 2: fixpoint convergence -------------------------------------
    ks = [k for _, k in _FIXPOINT_KS]
    for idx, fx in enumerate(sorted(fixpoint)):
        ys = [int(fixpoint[fx].get(key, 0)) for key, _ in _FIXPOINT_KS]
        ax_fp.plot(
            ks,
            ys,
            marker="o",
            markersize=4,
            linewidth=1.5,
            label=fx,
            color=_LINE_COLORS[idx % len(_LINE_COLORS)],
        )
    ax_fp.set_xticks(ks)
    ax_fp.set_xlabel("Fixpoint iteration cap K", fontsize=10)
    ax_fp.set_ylabel("Total semantic mappings", fontsize=10)
    ax_fp.set_title("Fixpoint convergence by iteration cap", fontsize=11)
    ax_fp.legend(fontsize=7, frameon=False, ncol=2)
    ax_fp.grid(linestyle=":", alpha=0.4)

    fig.suptitle(
        "COGANT measured ablation (source: evaluation/METRICS.yaml)",
        fontsize=12,
        y=1.02,
    )
    fig.tight_layout()
    fig.savefig(output_png, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_png
