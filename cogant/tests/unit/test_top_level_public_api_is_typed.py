"""Regression pin: ``cogant`` top-level public API names resolve to real
classes/functions, never to ``None``.

Before 2026-05-19 the package's ``__init__.py`` wrapped each first-party
import in ``try/except (ImportError, ModuleNotFoundError)`` and silently
set the name to ``None`` on failure (RedTeam F15). The matching
``__init__.pyi`` advertised these names as concrete classes, so a
consumer trusting mypy could hit ``AttributeError: 'NoneType' object``
at runtime. The fix removed the silent fallback for first-party
modules; this test pins the contract.

The keystone assertion: every name listed in ``cogant.__all__`` that
points to a class/function must actually be that class/function, not
``None`` and not a placeholder.
"""

from __future__ import annotations

import inspect

import cogant


def test_top_level_class_names_are_classes_not_none() -> None:
    """The named API classes must resolve to real classes when the package
    is imported normally."""
    expected_classes = (
        "Session",
        "PipelineRunner",
        "Bundle",
        "ProgramGraphBuilder",
        "TranslationEngine",
        "StateSpaceCompiler",
        "GNNMarkdownFormatter",
    )
    for name in expected_classes:
        obj = getattr(cogant, name, None)
        assert obj is not None, f"cogant.{name} is None — silent-fallback regression"
        assert inspect.isclass(obj), f"cogant.{name} is not a class: {obj!r}"


def test_program_graph_is_a_class() -> None:
    """``cogant.ProgramGraph`` may come from either the pydantic or the
    compatibility dataclass module, but it must be a class either way."""
    obj = getattr(cogant, "ProgramGraph", None)
    assert obj is not None
    assert inspect.isclass(obj)


def test_session_aliases_are_consistent() -> None:
    """``CogantSession`` aliases ``Session``; ``GNNBundle`` aliases ``Bundle``.
    The aliasing was made non-conditional in the same fix."""
    assert cogant.CogantSession is cogant.Session
    assert cogant.GNNBundle is cogant.Bundle


def test_session_can_be_instantiated(tmp_path) -> None:
    """A ``Session(target=...)`` call must not raise ``TypeError: 'NoneType'
    object is not callable`` — that was the runtime symptom of the
    silent-fallback bug. The Session constructor itself requires either
    ``target=`` or ``repo_path=``; we pass a real tmp dir."""
    repo = tmp_path / "empty"
    repo.mkdir()
    session = cogant.Session(target=str(repo))
    assert isinstance(session, cogant.Session)


def test_rust_availability_flag_is_a_bool() -> None:
    """The Rust extension IS optional; this stays a flag. We just pin the
    type so the .pyi's ``_RUST_AVAILABLE: bool`` declaration doesn't
    drift into a tri-state (True/False/None)."""
    assert isinstance(cogant._RUST_AVAILABLE, bool)
