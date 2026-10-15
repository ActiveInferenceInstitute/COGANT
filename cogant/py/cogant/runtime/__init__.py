"""Active Inference agent runtime for COGANT synthesized packages.

This module provides an executable perception-action loop that operates
on the A/B/C/D matrices produced by :func:`cogant.reverse.synthesizer.synthesize_package`.
The categorical arithmetic is pure Python without numerical dependencies.
The typed trace layer uses Pydantic; the installed package requires its
declared dependencies.

Public API
----------
* :class:`AgentConfig` -- configuration dataclass (max_steps, convergence, etc.)
* :class:`AgentStep` -- immutable record of one inference step
* :class:`AgentRuntime` -- the core runtime wrapping a matrices module
* :func:`run_n_steps` -- convenience: run N steps
* :func:`run_until_convergence` -- convenience: run until belief stabilises
"""

from cogant.runtime.config import AgentConfig
from cogant.runtime.inference import (
    load_inference_trace,
    run_gnn_inference,
    write_inference_trace_artifact,
)
from cogant.runtime.inference_records import InferenceOptions, InferenceTrace
from cogant.runtime.loop import (
    AgentRuntime,
    AgentStep,
    EpisodeResult,
    MultiEpisodeResult,
    run_n_steps,
    run_until_convergence,
)

__all__ = [
    "AgentConfig",
    "AgentStep",
    "AgentRuntime",
    "EpisodeResult",
    "MultiEpisodeResult",
    "InferenceOptions",
    "InferenceTrace",
    "load_inference_trace",
    "run_gnn_inference",
    "run_n_steps",
    "run_until_convergence",
    "write_inference_trace_artifact",
]
