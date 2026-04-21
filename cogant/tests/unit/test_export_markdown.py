"""Unit tests for ``cogant.export.markdown.render_bundle_markdown``."""

from __future__ import annotations

import pytest

from cogant.export.markdown import render_bundle_markdown


@pytest.fixture
def realistic_bundle() -> dict[str, object]:
    """A bundle dict shaped like one written by ``cogant translate``.

    Only the keys actually consumed by the renderer are populated; this
    keeps the fixture small while still exercising every branch.
    """
    return {
        "target": "/tmp/example",
        "errors": [],
        "metadata": {"timing": {"wall_time_ms": 1234}},
        "artifacts": {
            "parsed_modules_detail": [
                {"functions": 3, "classes": 1, "imports": 2},
                {"functions": 1, "classes": 0, "imports": 0},
            ],
            "repo_snapshot": {
                "metadata": {
                    "name": "example",
                    "language": "python",
                    "commit_hash": "deadbeef",
                    "author": "tester",
                }
            },
        },
        "stage_results": {
            "ingest": {"file_count": 2, "language_distribution": {"python": 2}},
            "static": {"modules": [1, 2], "nodes": list(range(5)), "edges": list(range(4))},
            "normalize": {"fact_count": 7, "nodes": list(range(5)), "edges": list(range(4))},
            "graph": {"nodes": dict.fromkeys(range(12)), "edges": dict.fromkeys(range(25))},
            "translate": {"mapping_count": 11, "mapping_ids": list(range(11))},
            "statespace": {
                "states": list(range(3)),
                "observations": list(range(2)),
                "actions": list(range(4)),
            },
            "process": {"stage_count": 6, "dependencies": list(range(2))},
            "validate": {
                "passed": True,
                "warnings": ["w1"],
                "issues": [],
            },
            "export": {"artifacts": list(range(3))},
            "dynamic": {"skipped": True, "reason": "disabled by config"},
        },
    }


def test_renders_header_and_target(realistic_bundle: dict[str, object]) -> None:
    md = render_bundle_markdown(realistic_bundle)
    assert md.startswith("# COGANT Export\n")
    assert "- target: `/tmp/example`" in md
    assert "- wall_time_ms: 1234" in md
    assert "- stages: 10" in md
    assert "- errors: 0" in md


def test_renders_repository_section(realistic_bundle: dict[str, object]) -> None:
    md = render_bundle_markdown(realistic_bundle)
    assert "## Repository" in md
    assert "- files: 2" in md
    assert "  - python: 2" in md


def test_renders_static_analysis_section(realistic_bundle: dict[str, object]) -> None:
    md = render_bundle_markdown(realistic_bundle)
    assert "## Static analysis" in md
    assert "- modules parsed: 2" in md
    assert "- functions: 4" in md
    assert "- classes: 1" in md
    assert "- imports: 2" in md


def test_renders_per_stage_table(realistic_bundle: dict[str, object]) -> None:
    md = render_bundle_markdown(realistic_bundle)
    assert "## Stages" in md
    assert "| graph | nodes=12, edges=25 |" in md
    assert "| translate | mappings=11 |" in md
    assert "| statespace | states=3, obs=2, actions=4 |" in md
    assert "| validate | passed=True, warnings=1, issues=0 |" in md
    assert "| export | artifacts=3 |" in md
    assert "| dynamic | skipped: disabled by config |" in md


def test_renders_source_section(realistic_bundle: dict[str, object]) -> None:
    md = render_bundle_markdown(realistic_bundle)
    assert "## Source" in md
    assert "- name: `example`" in md
    assert "- language: `python`" in md
    assert "- commit_hash: `deadbeef`" in md
    assert "- author: `tester`" in md


def test_renders_errors_section() -> None:
    md = render_bundle_markdown(
        {"target": "/tmp/x", "errors": ["boom", "kaboom"], "stage_results": {}}
    )
    assert "## Errors" in md
    assert "- boom" in md
    assert "- kaboom" in md


def test_minimal_bundle_does_not_raise() -> None:
    md = render_bundle_markdown({})
    assert md.startswith("# COGANT Export\n")
    assert "- target: `<unknown>`" in md
    assert "- stages: 0" in md
    assert "- errors: 0" in md
    assert "## Stages" not in md


def test_rejects_garbage_payload_gracefully() -> None:
    md = render_bundle_markdown(
        {
            "target": "x",
            "stage_results": {
                "graph": "not a dict",
                "translate": ["also not a dict"],
            },
        }
    )
    assert "| graph | - |" in md
    assert "| translate | - |" in md


def test_translate_falls_back_to_mapping_ids_length() -> None:
    md = render_bundle_markdown(
        {
            "target": "x",
            "stage_results": {"translate": {"mapping_ids": list(range(7))}},
        }
    )
    assert "| translate | mappings=7 |" in md
