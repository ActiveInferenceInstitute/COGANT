"""Variational free energy and KL divergence for Active Inference.

All functions are pure-Python with no external dependencies. Numerical
safety is ensured by adding a small epsilon (1e-10) inside logarithms
to avoid domain errors on zero-probability entries.

Variational Free Energy (VFE) approximation
--------------------------------------------
Given a state distribution ``q(s)``, an observation index ``obs_idx``,
a likelihood matrix ``A`` (shape ``[n_obs x n_states]``), a
log-preference vector ``C`` (shape ``[n_obs]``), and a prior ``D``
(shape ``[n_states]``):

    VFE = -log P(o | q) + KL(q || D)

where ``P(o | q) = sum_s A[o][s] * q(s)`` is the marginal likelihood
of the observed modality under the current belief.
"""

from __future__ import annotations

import math

_EPS = 1e-10


def kl_divergence(p: list[float], q: list[float]) -> float:
    """Compute KL(p || q) = sum_i p[i] * log(p[i] / (q[i] + eps)).

    Args:
        p: First distribution (the one we are measuring from).
        q: Second distribution (the reference).

    Returns:
        Non-negative KL divergence value.
    """
    kl = 0.0
    for pi, qi in zip(p, q, strict=False):
        if pi > _EPS:
            kl += pi * math.log(pi / (qi + _EPS))
    return kl


def free_energy(
    state_dist: list[float],
    obs_idx: int,
    A: list[list[float]],
    C: list[float],
    D: list[float],
) -> float:
    """Compute variational free energy for a single observation.

    VFE = -log P(o=obs_idx | state_dist) + KL(state_dist || D)

    The first term is the negative log-evidence (surprise) of the
    observed modality under the current belief about hidden states.
    The second term penalises deviation from the prior.

    Args:
        state_dist: Current belief over hidden states (sums to 1).
        obs_idx: Index of the observed modality.
        A: Likelihood matrix ``[n_obs x n_states]``.
        C: Log-preference vector ``[n_obs]`` (unused in basic VFE
            but available for expected free energy extensions).
        D: Prior distribution over hidden states.

    Returns:
        Variational free energy (finite float).
    """
    # Marginal likelihood: P(o=obs_idx) = sum_s A[obs_idx][s] * q(s)
    n_obs = len(A)
    if obs_idx < 0 or obs_idx >= n_obs:
        obs_idx = 0
    row = A[obs_idx] if obs_idx < n_obs else []
    p_obs = _EPS
    for a_val, s_val in zip(row, state_dist, strict=False):
        p_obs += a_val * s_val

    neg_log_evidence = -math.log(max(p_obs, _EPS))

    # KL divergence from prior
    kl = kl_divergence(state_dist, D)

    return neg_log_evidence + kl


__all__ = ["free_energy", "kl_divergence"]
