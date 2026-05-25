"""Targeted branch tests for: ``cogant.api.orchestration`` translate APIs.

Targets the lines that the existing ``test_api_orchestration_stage_functions.py``
skips:

* ``_materialize_source_dir`` — empty source + bad language (lines 1086-1091)
* ``_summarize_bundle`` — role counting + bundle summary (lines 1105-1114)
* ``translate_source`` end-to-end on real Python source (lines 1153-1164)
* ``translate_stream`` async generator — empty list, normal flow,
  error in one of multiple sources (lines 1196-1244)
* ``translate_batch`` — happy + error paths (lines 1269-1307)

Real source code, real pipeline, no mocks. ``translate_source`` runs
the actual analyse stages over a tiny Python snippet.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from cogant.api.orchestration import (
    _LANGUAGE_EXTENSIONS,
    _materialize_source_dir,
    _summarize_bundle,
    translate_batch,
    translate_source,
    translate_stream,
)

# --------------------------------------------------------------------------- #
# constants
# --------------------------------------------------------------------------- #


PYTHON_SNIPPET = '''\
"""Sample module."""

class Counter:
    """A counter."""

    def __init__(self) -> None:
        self.value = 0

    def increment(self) -> int:
        self.value += 1
        return self.value


def make_counter() -> Counter:
    return Counter()
'''


# --------------------------------------------------------------------------- #
# _materialize_source_dir
# --------------------------------------------------------------------------- #


def test_materialize_source_dir_python() -> None:
    """Python snippet is written to ``main.py`` in a fresh temp dir."""
    tmpdir = _materialize_source_dir("python", "x = 1\n")
    try:
        path = Path(tmpdir.name)
        assert path.is_dir()
        files = list(path.iterdir())
        assert len(files) == 1
        assert files[0].name == "main.py"
        assert files[0].read_text(encoding="utf-8") == "x = 1\n"
    finally:
        tmpdir.cleanup()


def test_materialize_source_dir_javascript() -> None:
    """JS snippet is written with ``.js`` extension."""
    tmpdir = _materialize_source_dir("javascript", "const x = 1;\n")
    try:
        path = Path(tmpdir.name)
        files = list(path.iterdir())
        assert files[0].name == "main.js"
    finally:
        tmpdir.cleanup()


def test_materialize_source_dir_typescript() -> None:
    """TS snippet is written with ``.ts`` extension."""
    tmpdir = _materialize_source_dir("typescript", "const x: number = 1;\n")
    try:
        path = Path(tmpdir.name)
        files = list(path.iterdir())
        assert files[0].name == "main.ts"
    finally:
        tmpdir.cleanup()


def test_materialize_source_dir_empty_source_raises() -> None:
    """Empty / whitespace-only source raises ``ValueError``."""
    with pytest.raises(ValueError, match="non-empty"):
        _materialize_source_dir("python", "")
    with pytest.raises(ValueError, match="non-empty"):
        _materialize_source_dir("python", "   \n\t  ")


def test_materialize_source_dir_unsupported_language_raises() -> None:
    """Unknown language reports the supported list."""
    with pytest.raises(ValueError, match="unsupported language"):
        _materialize_source_dir("rust", "fn main() {}\n")


def test_language_extensions_complete() -> None:
    """Sanity-check the language→extension mapping for the public API."""
    assert "python" in _LANGUAGE_EXTENSIONS
    assert "javascript" in _LANGUAGE_EXTENSIONS
    assert "typescript" in _LANGUAGE_EXTENSIONS
    assert _LANGUAGE_EXTENSIONS["python"] == "py"


# --------------------------------------------------------------------------- #
# translate_source — real pipeline run
# --------------------------------------------------------------------------- #


def test_translate_source_runs_default_stages() -> None:
    """``translate_source`` returns a populated ``Bundle`` for a Python snippet."""
    bundle = translate_source("python", PYTHON_SNIPPET)
    # Default stages include ingest → static → normalize → graph → translate → statespace
    completed = set(bundle.stage_results.keys())
    assert "ingest" in completed
    assert "graph" in completed
    assert "translate" in completed
    # The bundle should have a populated program graph
    pg = bundle.get_artifact("_program_graph")
    assert pg is not None


def test_translate_source_custom_stage_subset() -> None:
    """Caller can override the stage list to a tiny analyse subset."""
    bundle = translate_source("python", PYTHON_SNIPPET, stages=["ingest", "static"])
    completed = set(bundle.stage_results.keys())
    assert completed == {"ingest", "static"}


def test_translate_source_invalid_language_raises() -> None:
    """Bad language bubbles up the ``_materialize_source_dir`` error."""
    with pytest.raises(ValueError, match="unsupported language"):
        translate_source("ada", "procedure Main is begin null; end Main;\n")


def test_translate_source_empty_raises() -> None:
    """Empty source bubbles up."""
    with pytest.raises(ValueError, match="non-empty"):
        translate_source("python", "")


# --------------------------------------------------------------------------- #
# _summarize_bundle
# --------------------------------------------------------------------------- #


def test_summarize_bundle_real_pipeline_output() -> None:
    """``_summarize_bundle`` distills a real bundle into a JSON-safe dict."""
    bundle = translate_source("python", PYTHON_SNIPPET)
    summary = _summarize_bundle(bundle, "python")
    assert summary["language"] == "python"
    assert "gnn_bundle" in summary
    assert isinstance(summary["gnn_bundle"], str)
    assert summary["semantic_mappings_count"] >= 0
    assert isinstance(summary["roles"], dict)
    assert isinstance(summary["stages_completed"], list)
    # stages_completed is sorted
    assert summary["stages_completed"] == sorted(summary["stages_completed"])
    assert isinstance(summary["errors"], list)


# --------------------------------------------------------------------------- #
# translate_batch
# --------------------------------------------------------------------------- #


def test_translate_batch_mixed_success_and_invalid_request() -> None:
    """Batch processes every entry; invalid requests get a structured error."""
    requests = [
        {"language": "python", "source_code": PYTHON_SNIPPET},
        {"language": "python"},  # missing source_code
        {"source_code": "x=1"},  # missing language
        {"language": 123, "source_code": "x=1"},  # non-string language
    ]
    results = translate_batch(requests)
    assert len(results) == 4
    # First request succeeds
    assert results[0]["status"] == "success"
    assert "result" in results[0]
    assert results[0]["result"]["language"] == "python"
    # The other three fail validation up front
    for failed in results[1:]:
        assert failed["status"] == "error"
        assert "language" in failed["error"] or "source_code" in failed["error"]


def test_translate_batch_unsupported_language_returns_error() -> None:
    """A request with an unsupported language returns ``status=error``."""
    requests = [{"language": "elixir", "source_code": "IO.puts(\"hi\")\n"}]
    results = translate_batch(requests)
    assert len(results) == 1
    assert results[0]["status"] == "error"
    # Either ValueError or some other exception type — message includes the type
    assert "unsupported language" in results[0]["error"] or "ValueError" in results[0]["error"]


def test_translate_batch_empty_request_list() -> None:
    """An empty batch produces an empty result list."""
    assert translate_batch([]) == []


def test_translate_batch_with_explicit_stages() -> None:
    """Per-request ``stages`` overrides the default analyse stages."""
    requests = [
        {
            "language": "python",
            "source_code": PYTHON_SNIPPET,
            "stages": ["ingest", "static"],
        }
    ]
    results = translate_batch(requests)
    assert len(results) == 1
    assert results[0]["status"] == "success"
    completed = results[0]["result"]["stages_completed"]
    assert completed == ["ingest", "static"]


# --------------------------------------------------------------------------- #
# translate_stream (async generator)
# --------------------------------------------------------------------------- #


def _drain_async_gen(gen):
    """Drain an async generator into a list synchronously."""

    async def _drain():
        events = []
        async for event in gen:
            events.append(event)
        return events

    return asyncio.run(_drain())


def test_translate_stream_empty_sources_yields_progress() -> None:
    """An empty source list yields a single 100% progress event."""
    gen = translate_stream([])
    events = _drain_async_gen(gen)
    assert len(events) == 1
    assert events[0]["event"] == "progress"
    assert events[0]["percent_complete"] == 100
    assert events[0]["total"] == 0


def test_translate_stream_single_source_emits_full_lifecycle() -> None:
    """A single Python source produces start → stage_complete* → complete → progress."""
    gen = translate_stream(
        [("python", PYTHON_SNIPPET)],
        options={"stages": ["ingest", "static"]},
    )
    events = _drain_async_gen(gen)
    event_kinds = [e["event"] for e in events]
    assert "translation_start" in event_kinds
    assert "stage_complete" in event_kinds
    assert "translation_complete" in event_kinds
    assert "progress" in event_kinds
    # Final progress hits 100%
    assert events[-1]["event"] == "progress"
    assert events[-1]["percent_complete"] == 100
    assert events[-1]["processed"] == 1
    assert events[-1]["total"] == 1
    # Translation complete carries the summary dict
    complete_event = next(e for e in events if e["event"] == "translation_complete")
    assert complete_event["status"] == "success"
    assert "result" in complete_event
    assert complete_event["result"]["language"] == "python"


def test_translate_stream_multiple_sources_with_failure() -> None:
    """Stream continues past a translation_error and processes the next source."""
    gen = translate_stream(
        [
            ("python", PYTHON_SNIPPET),
            ("erlang", "-module(x).\n"),  # unsupported language → error
            ("python", "y = 2\n"),  # valid trailing source
        ],
        options={"stages": ["ingest", "static"]},
    )
    events = _drain_async_gen(gen)
    error_events = [e for e in events if e["event"] == "translation_error"]
    assert len(error_events) == 1
    assert error_events[0]["status"] == "failed"
    assert "ValueError" in error_events[0]["error"] or "unsupported" in error_events[0]["error"]
    # And the final progress reaches 100%
    assert events[-1]["event"] == "progress"
    assert events[-1]["percent_complete"] == 100
    # All three start events present
    start_events = [e for e in events if e["event"] == "translation_start"]
    assert len(start_events) == 3


def test_translate_stream_default_stages_without_options() -> None:
    """Omitting ``options`` uses the default analyse stages."""
    gen = translate_stream([("python", "x = 1\n")])
    events = _drain_async_gen(gen)
    # Verify it didn't crash and produced at least the progress events.
    kinds = {e["event"] for e in events}
    assert "translation_start" in kinds
    assert "progress" in kinds


# --------------------------------------------------------------------------- #
# Edge: program_graph_to_dict with statistics override
# --------------------------------------------------------------------------- #


def test_program_graph_to_dict_with_explicit_statistics() -> None:
    """``program_graph_to_dict`` embeds the supplied statistics dict."""
    from cogant.api.orchestration import program_graph_to_dict

    bundle = translate_source("python", PYTHON_SNIPPET)
    pg = bundle.get_artifact("_program_graph")
    assert pg is not None

    stats = {"node_count": 999, "edge_count": 888}
    result = program_graph_to_dict(pg, statistics=stats)
    assert result["statistics"] == stats
    assert result["type"] == "program_graph"
    assert "metadata" in result
    assert "nodes" in result
    assert "edges" in result


def test_program_graph_to_dict_without_statistics_uses_empty() -> None:
    """Default statistics is the empty dict, not ``None``."""
    from cogant.api.orchestration import program_graph_to_dict

    bundle = translate_source("python", "z = 0\n")
    pg = bundle.get_artifact("_program_graph")
    assert pg is not None
    result = program_graph_to_dict(pg)
    assert result["statistics"] == {}
