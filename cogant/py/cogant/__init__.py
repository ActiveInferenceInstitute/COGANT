"""COGANT: Codebase-to-GNN Translation Engine.

Translates software repositories into Generalized Notation Notation (GNN) — the
Active Inference Institute's structured state-space / process-model notation
(NOT graph neural networks). See
https://github.com/ActiveInferenceInstitute/GeneralizedNotationNotation.

The output of a COGANT run is a GNN-compatible model bundle: hidden states,
observation modalities, actions, policies, transitions, likelihoods,
preferences, factors, provenance, and confidence — all derived from static
and dynamic program evidence and all traceable back to source spans.
"""

__version__ = "0.2.0"
__author__ = "COGANT Contributors"

# Optional Rust acceleration backend. Built from `rust/cogant-ffi` via maturin
# and exposed as the `cogant._rust` extension module. When the compiled
# extension is not available (e.g. Rust toolchain missing or wheel not
# installed) the flag stays False and callers fall back to the pure-Python
# implementation.
try:
    from cogant import (
        _rust,  # type: ignore[import-not-found,unused-ignore]  # optional Rust extension  # noqa: F401
    )
    from cogant._rust import get_version as _rust_version  # type: ignore[import-not-found,unused-ignore]

    _RUST_AVAILABLE = True
    __rust_version__: str | None = _rust_version()
except (ImportError, ModuleNotFoundError):
    _RUST_AVAILABLE = False
    __rust_version__ = None

try:
    from cogant.api.session import Session
except (ImportError, ModuleNotFoundError):
    Session = None  # type: ignore[assignment,misc]

try:
    from cogant.api.pipeline import PipelineRunner
except (ImportError, ModuleNotFoundError):
    PipelineRunner = None  # type: ignore[assignment,misc]

try:
    from cogant.api.bundle import Bundle
except (ImportError, ModuleNotFoundError):
    Bundle = None  # type: ignore[assignment,misc]

try:
    from cogant.graph.builder import ProgramGraphBuilder
except (ImportError, ModuleNotFoundError):
    ProgramGraphBuilder = None  # type: ignore[assignment,misc]

try:
    from cogant.translate.engine import TranslationEngine
except (ImportError, ModuleNotFoundError):
    TranslationEngine = None  # type: ignore[assignment,misc]

try:
    from cogant.statespace.compiler import StateSpaceCompiler
except (ImportError, ModuleNotFoundError):
    StateSpaceCompiler = None  # type: ignore[assignment,misc]

try:
    from cogant.gnn.formatter import GNNMarkdownFormatter
except (ImportError, ModuleNotFoundError):
    GNNMarkdownFormatter = None  # type: ignore[assignment,misc]

__all__ = [
    "Session",
    "PipelineRunner",
    "Bundle",
    "ProgramGraphBuilder",
    "TranslationEngine",
    "StateSpaceCompiler",
    "GNNMarkdownFormatter",
    "__version__",
    "__rust_version__",
    "_RUST_AVAILABLE",
]
