"""GNN markdown formatter package.

The full formatter is split into a small base class plus five
section-family mixins to keep each file under ~500 lines while
preserving the exact markdown output of the pre-split formatter.

Layout::

    cogant.gnn.formatter/
      __init__.py      -- re-exports GNNMarkdownFormatter
      base.py          -- class, format(), and shared helpers
      upstream.py      -- upstream GNN v1.1 canonical header sections
                          (GNNSection, GNNVersionAndFlags, ModelName,
                          StateSpaceBlock, Connections,
                          InitialParameterization, Time,
                          ActInfOntologyAnnotation, etc.)
      metadata.py      -- model, repo, source, provenance, ...
      structural.py    -- state space, observations, factors, ...
      dynamics.py      -- transitions, likelihoods, time, ...
      semantic.py      -- ontology mapping, Markov blanket

Callers should continue to import from
``cogant.gnn.formatter`` just as before.
"""

from cogant.gnn.formatter.base import GNNMarkdownFormatter
from cogant.gnn.formatter.upstream import (
    UPSTREAM_OPTIONAL_SECTIONS,
    UPSTREAM_REQUIRED_SECTIONS,
)

__all__ = [
    "GNNMarkdownFormatter",
    "UPSTREAM_REQUIRED_SECTIONS",
    "UPSTREAM_OPTIONAL_SECTIONS",
]
