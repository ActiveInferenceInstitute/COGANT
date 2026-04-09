"""COGANT Markov blanket extraction.

This submodule partitions a program graph into an Active-Inference-style
Markov blanket: a triple of (internal, blanket={sensory, active}, external)
states that together determine the conditional independence structure of
a system of interest.

The canonical Active Inference decomposition is::

    μ  — internal states  (only interact with sensory/active/other μ)
    s  — sensory states    (internal  ← external, blanket)
    a  — active states     (internal  → external, blanket)
    η  — external states   (only interact with sensory/active/other η)

A Markov blanket is the minimal set ``B = s ∪ a`` such that ``μ ⊥ η | B``.

Public API:
  - :class:`MarkovBlanket` — dataclass holding the partition and metadata.
  - :class:`MarkovBlanketExtractor` — builds a blanket from a :class:`ProgramGraph`
    given a user-supplied "system of interest" seed set or an automatic
    seed chosen by cohesion/coupling scoring.
  - :func:`partition_by_seeds` — low-level partitioning primitive.
  - :func:`serialize_blanket` — JSON-ready dictionary form for the GNN bundle.

See :mod:`cogant.markov.blanket`, :mod:`cogant.markov.extractor`, and
:mod:`cogant.markov.network` for implementation details.
"""

from cogant.markov.blanket import (
    BlanketRole,
    MarkovBlanket,
    partition_by_seeds,
    serialize_blanket,
)
from cogant.markov.extractor import MarkovBlanketExtractor
from cogant.markov.network import BlanketNetwork, build_blanket_network

__all__ = [
    "BlanketRole",
    "MarkovBlanket",
    "MarkovBlanketExtractor",
    "BlanketNetwork",
    "partition_by_seeds",
    "serialize_blanket",
    "build_blanket_network",
]
