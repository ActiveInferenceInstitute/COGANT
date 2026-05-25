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

__version__ = "0.6.0"
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
    from cogant._rust import (
        get_version as _rust_version,  # type: ignore[import-not-found,unused-ignore]
    )

    _RUST_AVAILABLE = True
    __rust_version__: str | None = _rust_version()
except (ImportError, ModuleNotFoundError):
    _RUST_AVAILABLE = False
    __rust_version__ = None

# First-party cogant submodules. Previously wrapped in try/except blocks that
# silently set these names to ``None`` on ImportError — but the matching .pyi
# (``cogant/__init__.pyi``) declares them as concrete classes, so a consumer
# trusting mypy's view of ``cogant.Session`` could hit ``AttributeError: None
# has no attribute ...`` at runtime. The honest fix is to let the import
# fail loudly: these are first-party modules, not optional deps. If any of
# them cannot be imported, the cogant install is broken and the user needs to
# see that, not get a silent None. See RedTeam F15 (2026-05-19).
from cogant.api.bundle import Bundle
from cogant.api.pipeline import PipelineRunner
from cogant.api.session import Session
from cogant.gnn.formatter import GNNMarkdownFormatter
from cogant.graph.builder import ProgramGraphBuilder
from cogant.statespace.compiler import StateSpaceCompiler
from cogant.translate.engine import TranslationEngine

# ``ProgramGraph`` has two homes — the newer pydantic schema and the legacy
# dataclass module. Keep the fallback because they ARE legitimately
# alternative implementations selected by call site, not a broken-install
# signal.
try:
    from cogant.schemas.program_graph import ProgramGraph
except (ImportError, ModuleNotFoundError):
    from cogant.schemas.graph import ProgramGraph  # type: ignore[assignment]

# Type infrastructure (always available).
try:
    from cogant.protocols import (
        Analyzable,
        Exportable,
        GraphBackend,
        PipelineStage,
        Serializable,
        Translatable,
        TranslationRule,
        Validatable,
        Visualizable,
    )
except (ImportError, ModuleNotFoundError):
    Analyzable = None  # type: ignore[assignment,misc]
    Exportable = None  # type: ignore[assignment,misc]
    GraphBackend = None  # type: ignore[assignment,misc]
    PipelineStage = None  # type: ignore[assignment,misc]
    Serializable = None  # type: ignore[assignment,misc]
    TranslationRule = None  # type: ignore[assignment,misc]
    Translatable = None  # type: ignore[assignment,misc]
    Validatable = None  # type: ignore[assignment,misc]
    Visualizable = None  # type: ignore[assignment,misc]

try:
    from cogant.types import (
        AMatrix,
        BMatrix,
        ConfidenceScore,
        CVector,
        DotStr,
        DVector,
        EdgeAttrs,
        EdgeKind,
        FilePath,
        GNNBundle,
        JsonStr,
        MermaidStr,
        NodeAttrs,
        NodeId,
        RoleName,
    )
except (ImportError, ModuleNotFoundError):
    AMatrix = None  # type: ignore[assignment,misc]
    BMatrix = None  # type: ignore[assignment,misc]
    CVector = None  # type: ignore[assignment,misc]
    ConfidenceScore = None  # type: ignore[assignment,misc]
    DVector = None  # type: ignore[assignment,misc]
    DotStr = None  # type: ignore[assignment,misc]
    EdgeAttrs = None  # type: ignore[assignment,misc]
    EdgeKind = None  # type: ignore[assignment,misc]
    FilePath = None  # type: ignore[assignment,misc]
    GNNBundle = None  # type: ignore[assignment,misc]
    JsonStr = None  # type: ignore[assignment,misc]
    MermaidStr = None  # type: ignore[assignment,misc]
    NodeAttrs = None  # type: ignore[assignment,misc]
    NodeId = None  # type: ignore[assignment,misc]
    RoleName = None  # type: ignore[assignment,misc]

# Convenience aliases for the public API.
# Users can write:
#   from cogant import CogantSession, run_pipeline, GNNBundle, ProgramGraph
CogantSession = Session
"""Alias for :class:`cogant.api.session.Session`."""

GNNBundle = Bundle
"""Alias for :class:`cogant.api.bundle.Bundle`."""


def run_pipeline(target: str, output_dir: str = "output") -> object:
    """Run the full COGANT pipeline on *target* and return the completed session.

    This is a convenience wrapper around :class:`Session` that runs all stages
    (static extraction, graph build, translation, state-space compilation, and
    export) in one call.

    Args:
        target: Filesystem path or URL of the repository to analyse.
        output_dir: Directory where artifacts are written. Defaults to ``"output"``.

    Returns:
        The :class:`Session` object after ``export_all`` has been called, or
        ``None`` if the session API is unavailable.
    """
    if Session is None:
        raise ImportError("cogant.api.session is not available; check your installation.")
    sess = Session(target=target)
    sess.extract_static()
    sess.build_graph()
    sess.translate_to_gnn()
    sess.compile_state_space()
    sess.export_all(output_dir)
    return sess


__all__ = [
    # Core API
    "Session",
    "PipelineRunner",
    "Bundle",
    "ProgramGraphBuilder",
    "TranslationEngine",
    "StateSpaceCompiler",
    "GNNMarkdownFormatter",
    "ProgramGraph",
    # Convenience aliases
    "CogantSession",
    "GNNBundle",
    "run_pipeline",
    # Type infrastructure: Protocols
    "Translatable",
    "Analyzable",
    "Serializable",
    "Visualizable",
    "Validatable",
    "Exportable",
    "PipelineStage",
    "TranslationRule",
    "GraphBackend",
    # Type infrastructure: Shared TypedDicts and aliases
    "NodeAttrs",
    "EdgeAttrs",
    "NodeId",
    "EdgeKind",
    "RoleName",
    "FilePath",
    "ConfidenceScore",
    "AMatrix",
    "BMatrix",
    "CVector",
    "DVector",
    "MermaidStr",
    "DotStr",
    "JsonStr",
    # Version info
    "__version__",
    "__rust_version__",
    "_RUST_AVAILABLE",
]
