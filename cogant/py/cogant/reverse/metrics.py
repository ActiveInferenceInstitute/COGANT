"""GNN-to-GNN distance and isomorphism metrics.

This module supplies the real, principled distance functions used by
:mod:`cogant.reverse.idempotency` when it asks the question "is the
round-tripped GNN isomorphic to the source GNN?".

Three orthogonal views of "close" are measured and then fused into a
single :class:`IsomorphismReport`:

* **Role distribution** — a Jensen-Shannon divergence between the two
  role multisets (``HIDDEN_STATE``, ``OBSERVATION``, ``ACTION``, ...).
  JS-divergence is bounded in ``[0, log 2]`` for base-``e`` and in
  ``[0, 1]`` for base-2. We use base-2 and invert so that identical
  distributions score 1.0 and disjoint supports score 0.0.
* **Matrix Frobenius distance** — for each Active Inference matrix
  ``A`` (likelihood), ``B`` (transition), ``C`` (preferences),
  ``D`` (prior) present in both packages, we compute the normalized
  Frobenius distance ``||M1 - M2|| / (||M1|| + ||M2|| + eps)`` and
  convert it to a score ``1 - d``. Matrices of mismatched shape are
  zero-padded to a common envelope before subtraction so the metric is
  defined for round-trips that change factor cardinality. We average
  over matrix types present in **both** dicts; if no shared matrix
  types exist the score is the neutral value ``0.5``.
* **Graph structure** — a normalized symmetric-difference distance
  between the *multisets of node roles* and between the *multisets of
  edge-role-pairs*. This is intentionally weaker than exact graph edit
  distance (which is NP-hard and overkill here) but captures the
  right intuition: "did the synthesized package grow or drop nodes
  and edges relative to the source?". The returned score is
  ``1 - normalized_symdiff``.

The three scores are combined with the weights ``0.4 * role +
0.4 * matrix + 0.2 * structural`` — role and matrix carry equal top
billing because they are the scientifically meaningful axes for an
Active Inference model, while structural drift is treated as a
tie-breaker. The cutoff for ``is_isomorphic`` defaults to ``0.7`` and
can be tightened by the caller.

All functions in this module are pure and free of side effects. The
only external dependency is NumPy, which the cogant test environment
provides (``numpy>=2.0``). Inputs may be NumPy arrays or plain
Python lists; they are coerced to ``float64`` on entry.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

__all__ = [
    "IsomorphismReport",
    "compare_role_distributions",
    "compare_matrices",
    "compare_graph_structure",
    "compute_isomorphism_report",
    "DEFAULT_ISOMORPHISM_THRESHOLD",
    "MATRIX_KEYS",
]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_ISOMORPHISM_THRESHOLD: float = 0.7
"""Default cutoff for :attr:`IsomorphismReport.is_isomorphic`."""

MATRIX_KEYS: tuple[str, ...] = ("A", "B", "C", "D")
"""Canonical Active Inference matrix slot names used by COGANT."""

_EPS: float = 1e-12
"""Numerical floor used to avoid division-by-zero in normalized metrics."""


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class IsomorphismReport:
    """Aggregate GNN-to-GNN distance report.

    All ``*_score`` fields are in ``[0.0, 1.0]`` where ``1.0`` means
    "identical" and ``0.0`` means "maximally different under this
    metric". The ``total_score`` is the weighted mean of the three
    component scores and is itself in ``[0.0, 1.0]``. ``is_isomorphic``
    is simply ``total_score >= threshold``.

    Attributes:
        structural_score: Graph-structure similarity in ``[0, 1]``.
        role_score: Role distribution similarity (inverted JS
            divergence) in ``[0, 1]``.
        matrix_score: Frobenius-based matrix similarity in ``[0, 1]``.
        total_score: Weighted mean
            ``0.4 * role + 0.4 * matrix + 0.2 * structural``.
        is_isomorphic: True when ``total_score >= threshold``.
        breakdown: Per-metric diagnostic detail. Keys include the
            three component scores, the threshold, the weighting, and
            (when available) per-matrix Frobenius distances.
    """

    structural_score: float = 0.0
    role_score: float = 0.0
    matrix_score: float = 0.0
    total_score: float = 0.0
    is_isomorphic: bool = False
    breakdown: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        """Return a compact, human-readable one-line summary.

        The format is::

            [ISO] total=0.82 role=0.90 matrix=0.85 struct=0.60

        with ``ISO`` swapped for ``DRIFT`` when
        ``is_isomorphic`` is False.
        """
        status = "ISO" if self.is_isomorphic else "DRIFT"
        return (
            f"[{status}] total={self.total_score:.2f} "
            f"role={self.role_score:.2f} "
            f"matrix={self.matrix_score:.2f} "
            f"struct={self.structural_score:.2f}"
        )


# ---------------------------------------------------------------------------
# Role-distribution distance (Jensen-Shannon divergence, base 2)
# ---------------------------------------------------------------------------


def _to_probability(counts: Mapping[str, float], support: Sequence[str]) -> np.ndarray:
    """Project a count dict onto ``support`` and normalize to a pmf.

    Zero-count entries are kept so the returned vector is aligned with
    ``support``. If the total mass is zero, an all-zero vector is
    returned (the caller is expected to guard against this).
    """
    vec = np.array([float(counts.get(k, 0.0)) for k in support], dtype=np.float64)
    total = float(vec.sum())
    if total <= 0.0:
        return vec
    return vec / total


def _kl_divergence(p: np.ndarray, q: np.ndarray) -> float:
    """Compute ``KL(p || q)`` in bits, with the convention ``0*log 0 = 0``.

    ``q`` is assumed to be non-zero wherever ``p`` is non-zero; the
    Jensen-Shannon midpoint ``M = 0.5*(p+q)`` satisfies this whenever
    both ``p`` and ``q`` are probability vectors, so this helper is
    always called with a safe ``q``.
    """
    mask = p > 0.0
    if not np.any(mask):
        return 0.0
    p_masked = p[mask]
    q_masked = q[mask]
    # Guard against log(0) if q somehow has a zero where p does not.
    q_masked = np.where(q_masked <= 0.0, _EPS, q_masked)
    return float(np.sum(p_masked * np.log2(p_masked / q_masked)))


def compare_role_distributions(
    roles_a: Mapping[str, float],
    roles_b: Mapping[str, float],
) -> float:
    """Return a similarity score in ``[0, 1]`` for two role multisets.

    The underlying distance is the Jensen-Shannon divergence in base 2,
    which for two probability vectors ``p`` and ``q`` is::

        JS(p, q) = 0.5 * KL(p || M) + 0.5 * KL(q || M),  M = 0.5*(p+q)

    and is bounded in ``[0, 1]``. We return ``1 - JS`` so that higher
    is better.

    Edge cases:

    * If both distributions are empty, we return ``0.0`` (there is no
      distribution to compare, and the spec asks for a neutral-low
      value here so that the overall isomorphism score does not
      spuriously inflate on degenerate inputs).
    * If exactly one distribution is empty, we also return ``0.0``
      (maximally different — one side has no roles at all).

    Args:
        roles_a: Mapping from role name to count (or weight).
        roles_b: Mapping from role name to count (or weight).

    Returns:
        Similarity score in ``[0.0, 1.0]``. ``1.0`` means the two role
        distributions are identical; ``0.0`` means their supports are
        disjoint or one side is empty.
    """
    total_a = sum(float(v) for v in roles_a.values())
    total_b = sum(float(v) for v in roles_b.values())

    if total_a <= 0.0 and total_b <= 0.0:
        return 0.0
    if total_a <= 0.0 or total_b <= 0.0:
        return 0.0

    support: list[str] = sorted(set(roles_a.keys()) | set(roles_b.keys()))
    p = _to_probability(roles_a, support)
    q = _to_probability(roles_b, support)

    m = 0.5 * (p + q)
    js = 0.5 * _kl_divergence(p, m) + 0.5 * _kl_divergence(q, m)
    # Numerical clamp: floating point can produce tiny negatives or
    # values a hair above 1.0.
    js = max(0.0, min(1.0, js))
    return 1.0 - js


# ---------------------------------------------------------------------------
# Matrix Frobenius distance
# ---------------------------------------------------------------------------


def _coerce_matrix(value: Any) -> np.ndarray | None:
    """Best-effort conversion of ``value`` to a 2D ``float64`` array.

    Returns ``None`` for empty or non-numeric inputs; callers treat
    ``None`` as "this matrix slot is not present on this side" and
    skip it.
    """
    if value is None:
        return None
    try:
        arr = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError):
        return None
    if arr.size == 0:
        return None
    # Promote 0-d / 1-d scalars to a column vector so Frobenius norm
    # is well defined across both sides without NumPy broadcasting
    # surprises.
    if arr.ndim == 0:
        arr = arr.reshape((1, 1))
    elif arr.ndim == 1:
        arr = arr.reshape((-1, 1))
    return arr


def _pad_to_envelope(m1: np.ndarray, m2: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Zero-pad two arrays to their common bounding shape.

    Supports arbitrary rank (both arrays must share the same
    ``ndim``). Used so Frobenius distance is defined even when the
    round-trip changes a factor's cardinality.
    """
    if m1.ndim != m2.ndim:
        # Rank mismatch: flatten both to vectors. Frobenius on
        # flattened arrays is still a well-defined distance.
        m1 = m1.reshape(-1)
        m2 = m2.reshape(-1)

    shape = tuple(max(a, b) for a, b in zip(m1.shape, m2.shape, strict=False))
    pad1 = [(0, shape[i] - m1.shape[i]) for i in range(len(shape))]
    pad2 = [(0, shape[i] - m2.shape[i]) for i in range(len(shape))]
    return np.pad(m1, pad1), np.pad(m2, pad2)


def _matrix_pair_score(m1: np.ndarray, m2: np.ndarray) -> tuple[float, float]:
    """Return ``(score, raw_distance)`` for a single matrix pair.

    ``score`` is ``1 - raw_distance`` clamped to ``[0, 1]``.
    ``raw_distance`` is ``||m1 - m2||_F / (||m1||_F + ||m2||_F + eps)``.
    Both matrices are zero-padded to their common envelope first.
    When both matrices are exactly zero, the raw distance is ``0.0``
    (identical) — without the ``_EPS`` denominator this would be
    ``NaN``.
    """
    m1p, m2p = _pad_to_envelope(m1, m2)
    diff = np.linalg.norm(m1p - m2p)
    denom = np.linalg.norm(m1p) + np.linalg.norm(m2p) + _EPS
    raw = float(diff / denom)
    raw = max(0.0, min(1.0, raw))
    return 1.0 - raw, raw


def compare_matrices(
    matrices_a: Mapping[str, Any],
    matrices_b: Mapping[str, Any],
) -> float:
    """Return an averaged Frobenius-similarity score in ``[0, 1]``.

    For each canonical Active Inference matrix slot
    (``A``, ``B``, ``C``, ``D``) present in **both** input dicts and
    non-empty on both sides, we compute::

        1 - ||m1 - m2||_F / (||m1||_F + ||m2||_F + eps)

    after zero-padding the two matrices to their common bounding
    shape. The returned score is the unweighted mean of these
    per-matrix similarities.

    Edge cases:

    * If neither side has any recognisable numeric matrix entry,
      return ``0.5`` (neutral — the metric is undefined, not zero).
    * If a key is present on only one side it is ignored (the
      structural-graph score is the axis that penalises missing
      slots).
    * Extra keys beyond ``{A, B, C, D}`` are tolerated and included.

    The metric is symmetric: ``compare_matrices(a, b) ==
    compare_matrices(b, a)`` up to floating point round-off.

    Args:
        matrices_a: Dict mapping matrix name to a 2D array-like.
        matrices_b: Dict mapping matrix name to a 2D array-like.

    Returns:
        Mean similarity score in ``[0, 1]``, or ``0.5`` when no
        comparable matrices exist.
    """
    # Stable key ordering: canonical A/B/C/D first, then any extras
    # sorted alphabetically.
    shared_keys: list[str] = []
    for key in MATRIX_KEYS:
        if key in matrices_a and key in matrices_b:
            shared_keys.append(key)
    extras = sorted(
        (set(matrices_a.keys()) & set(matrices_b.keys())) - set(MATRIX_KEYS)
    )
    shared_keys.extend(extras)

    if not shared_keys:
        return 0.5

    scores: list[float] = []
    for key in shared_keys:
        arr_a = _coerce_matrix(matrices_a.get(key))
        arr_b = _coerce_matrix(matrices_b.get(key))
        if arr_a is None or arr_b is None:
            continue
        score, _ = _matrix_pair_score(arr_a, arr_b)
        scores.append(score)

    if not scores:
        return 0.5
    return float(sum(scores) / len(scores))


# ---------------------------------------------------------------------------
# Graph structure distance
# ---------------------------------------------------------------------------


def _node_role_label(node: Any) -> str:
    """Extract a stable role-ish label from a node object or dict.

    We deliberately key on *role*, not node identity, because the
    round-trip is allowed to rename nodes — what must be preserved is
    the role multiset, not the exact IDs. We try a cascade of fallback
    keys so this function works on plain dicts, dataclasses, and
    attribute-style objects.
    """
    if isinstance(node, Mapping):
        for key in ("role", "kind", "type", "label"):
            val = node.get(key)
            if val:
                return str(val)
        # Last resort: a stringified sorted key tuple so at least
        # structurally identical dicts collapse to the same label.
        return "NODE"
    # Attribute-style fallback.
    for attr in ("role", "kind", "type", "label"):
        val = getattr(node, attr, None)
        if val:
            return str(val)
    return "NODE"


def _edge_role_pair(edge: Any) -> tuple[str, str]:
    """Return a ``(source_role, target_role)`` label pair for an edge.

    As with :func:`_node_role_label`, we key on role labels (not node
    IDs) so edge multisets compare correctly across renamings.
    """
    if isinstance(edge, Mapping):
        src = edge.get("source_role") or edge.get("source") or edge.get("src") or ""
        dst = edge.get("target_role") or edge.get("target") or edge.get("dst") or ""
        return (str(src), str(dst))
    src = getattr(edge, "source_role", None) or getattr(edge, "source", "")
    dst = getattr(edge, "target_role", None) or getattr(edge, "target", "")
    return (str(src), str(dst))


def _multiset(items: Iterable[Any]) -> dict[Any, int]:
    """Return a counter-style multiset dict from any iterable."""
    result: dict[Any, int] = {}
    for item in items:
        result[item] = result.get(item, 0) + 1
    return result


def _multiset_symmetric_difference(a: dict[Any, int], b: dict[Any, int]) -> int:
    """Size of the symmetric difference of two count-dict multisets."""
    keys = set(a.keys()) | set(b.keys())
    return sum(abs(a.get(k, 0) - b.get(k, 0)) for k in keys)


def compare_graph_structure(
    nodes_a: Sequence[Any],
    edges_a: Sequence[Any],
    nodes_b: Sequence[Any],
    edges_b: Sequence[Any],
) -> float:
    """Return a graph-structure similarity score in ``[0, 1]``.

    We build two multisets for each graph:

    1. ``role(nodes)`` — one bucket per node role label.
    2. ``(source_role, target_role)`` — one bucket per edge.

    We then compute the normalized symmetric difference of each
    multiset separately and return ``1 - mean(d_nodes, d_edges)``.
    Nodes-only graphs (no edges on either side) skip the edge term.

    Edge cases:

    * Both graphs empty → return ``1.0`` (vacuously identical).
    * One graph empty, other non-empty → return ``0.0``.

    Args:
        nodes_a: Iterable of node-like objects for graph A.
        edges_a: Iterable of edge-like objects for graph A.
        nodes_b: Iterable of node-like objects for graph B.
        edges_b: Iterable of edge-like objects for graph B.

    Returns:
        Similarity score in ``[0.0, 1.0]``.
    """
    n_a = list(nodes_a or [])
    n_b = list(nodes_b or [])
    e_a = list(edges_a or [])
    e_b = list(edges_b or [])

    if not n_a and not n_b and not e_a and not e_b:
        return 1.0
    if (not n_a and n_b) or (n_a and not n_b):
        # One side has zero nodes, the other has some — maximally
        # different at the structural level.
        if not e_a and not e_b:
            return 0.0

    node_labels_a = _multiset(_node_role_label(n) for n in n_a)
    node_labels_b = _multiset(_node_role_label(n) for n in n_b)
    node_total = sum(node_labels_a.values()) + sum(node_labels_b.values())
    node_symdiff = _multiset_symmetric_difference(node_labels_a, node_labels_b)
    node_distance = (node_symdiff / node_total) if node_total > 0 else 0.0

    edge_labels_a = _multiset(_edge_role_pair(e) for e in e_a)
    edge_labels_b = _multiset(_edge_role_pair(e) for e in e_b)
    edge_total = sum(edge_labels_a.values()) + sum(edge_labels_b.values())
    if edge_total > 0:
        edge_symdiff = _multiset_symmetric_difference(edge_labels_a, edge_labels_b)
        edge_distance = edge_symdiff / edge_total
        distance = 0.5 * (node_distance + edge_distance)
    else:
        distance = node_distance

    distance = max(0.0, min(1.0, distance))
    return 1.0 - distance


# ---------------------------------------------------------------------------
# Top-level report
# ---------------------------------------------------------------------------


_ROLE_WEIGHT: float = 0.4
_MATRIX_WEIGHT: float = 0.4
_STRUCTURAL_WEIGHT: float = 0.2


def compute_isomorphism_report(
    gnn_a: Mapping[str, Any],
    gnn_b: Mapping[str, Any],
    threshold: float = DEFAULT_ISOMORPHISM_THRESHOLD,
) -> IsomorphismReport:
    """Compute a full :class:`IsomorphismReport` for two GNN packages.

    ``gnn_a`` and ``gnn_b`` are expected to be dict-like bundles with
    the following optional keys:

    * ``roles`` — ``{role_name: count}`` multiset.
    * ``matrices`` — ``{"A"|"B"|"C"|"D": array_like}`` dict.
    * ``nodes`` — iterable of node objects or dicts.
    * ``edges`` — iterable of edge objects or dicts.

    Missing keys are tolerated: the corresponding component score
    falls back to its documented neutral value (``0.0`` for roles,
    ``0.5`` for matrices, ``1.0`` for an empty graph).

    The three component scores are combined with fixed weights::

        total = 0.4 * role + 0.4 * matrix + 0.2 * structural

    and ``is_isomorphic`` is ``total >= threshold``.

    Args:
        gnn_a: First GNN package dict.
        gnn_b: Second GNN package dict.
        threshold: Cutoff for :attr:`IsomorphismReport.is_isomorphic`.
            Defaults to :data:`DEFAULT_ISOMORPHISM_THRESHOLD` (0.7).

    Returns:
        A fully populated :class:`IsomorphismReport`.
    """
    roles_a: Mapping[str, float] = gnn_a.get("roles", {}) or {}
    roles_b: Mapping[str, float] = gnn_b.get("roles", {}) or {}
    matrices_a: Mapping[str, Any] = gnn_a.get("matrices", {}) or {}
    matrices_b: Mapping[str, Any] = gnn_b.get("matrices", {}) or {}
    nodes_a: Sequence[Any] = gnn_a.get("nodes", []) or []
    nodes_b: Sequence[Any] = gnn_b.get("nodes", []) or []
    edges_a: Sequence[Any] = gnn_a.get("edges", []) or []
    edges_b: Sequence[Any] = gnn_b.get("edges", []) or []

    role_score = compare_role_distributions(roles_a, roles_b)
    matrix_score = compare_matrices(matrices_a, matrices_b)
    structural_score = compare_graph_structure(nodes_a, edges_a, nodes_b, edges_b)

    total_score = (
        _ROLE_WEIGHT * role_score
        + _MATRIX_WEIGHT * matrix_score
        + _STRUCTURAL_WEIGHT * structural_score
    )
    # Clamp for floating-point safety.
    total_score = max(0.0, min(1.0, total_score))

    breakdown: dict[str, Any] = {
        "role_score": role_score,
        "matrix_score": matrix_score,
        "structural_score": structural_score,
        "weights": {
            "role": _ROLE_WEIGHT,
            "matrix": _MATRIX_WEIGHT,
            "structural": _STRUCTURAL_WEIGHT,
        },
        "threshold": threshold,
        "roles_a_total": sum(float(v) for v in roles_a.values()),
        "roles_b_total": sum(float(v) for v in roles_b.values()),
        "matrix_keys_a": sorted(matrices_a.keys()),
        "matrix_keys_b": sorted(matrices_b.keys()),
        "n_nodes_a": len(list(nodes_a)),
        "n_nodes_b": len(list(nodes_b)),
        "n_edges_a": len(list(edges_a)),
        "n_edges_b": len(list(edges_b)),
    }

    # Per-matrix raw Frobenius detail, if we can compute it cheaply.
    per_matrix: dict[str, float] = {}
    for key in MATRIX_KEYS:
        if key in matrices_a and key in matrices_b:
            arr_a = _coerce_matrix(matrices_a.get(key))
            arr_b = _coerce_matrix(matrices_b.get(key))
            if arr_a is not None and arr_b is not None:
                _, raw = _matrix_pair_score(arr_a, arr_b)
                per_matrix[key] = raw
    if per_matrix:
        breakdown["per_matrix_frobenius"] = per_matrix

    return IsomorphismReport(
        structural_score=float(structural_score),
        role_score=float(role_score),
        matrix_score=float(matrix_score),
        total_score=float(total_score),
        is_isomorphic=bool(total_score >= threshold),
        breakdown=breakdown,
    )


# Silence linter "unused import" warnings for ``math`` — kept as a
# future-proofing hook if we want to swap to natural-log JS divergence.
_ = math
