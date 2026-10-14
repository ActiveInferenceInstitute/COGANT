"""CALLS edges must only point at callables the caller can actually reach.

The graph stage's call resolver used to fall back to *any* repo callable
whose name ended in ``.<attr>``, so ``out.append(x)`` on a local list or
``config.get("x")`` on a dict became CALLS edges to unrelated repo methods
named ``append``/``get``. Its indexes were also keyed by file stem, so two
``utils.py`` files in different packages overwrote each other: calls
resolved into the wrong package and one package's INHERITS edge vanished.

Resolution is now scoped to the caller's own module, its own class, and
names bound by in-repo imports. Fixtures are real on-disk packages driven
through the public orchestration API (no mocks).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.api.bundle import Bundle
from cogant.api.orchestration import run_graph
from cogant.ingest.repo import RepoIngester
from cogant.schemas.core import EdgeKind

pytestmark = pytest.mark.unit


def _write(repo: Path, rel_path: str, body: str) -> None:
    path = repo / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _graph(repo: Path):
    bundle = Bundle(target=str(repo))
    bundle.artifacts["repo_snapshot"] = RepoIngester().ingest_local(repo, include_test_files=False)
    run_graph(bundle, str(repo))
    return bundle.artifacts["_program_graph"]


def _edges(pg, kind: EdgeKind) -> set[tuple[str, str]]:
    def label(node_id: str) -> str:
        node = pg.nodes[node_id]
        return f"{node.path}::{node.qualified_name}"

    return {(label(e.source_id), label(e.target_id)) for e in pg.edges.values() if e.kind == kind}


def test_builtin_method_calls_on_locals_do_not_hit_repo_methods(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(
        repo,
        "registry.py",
        "class Registry:\n"
        "    def get(self, key):\n"
        "        return key\n"
        "\n"
        "    def append(self, item):\n"
        "        return item\n",
    )
    _write(
        repo,
        "worker.py",
        "def work(config):\n    out = []\n    out.append(config.get('x'))\n    return out\n",
    )

    assert _edges(_graph(repo), EdgeKind.CALLS) == set()


def test_same_stem_modules_in_different_packages_stay_separate(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    for package in ("alpha", "beta"):
        _write(repo, f"{package}/__init__.py", "")
        _write(
            repo,
            f"{package}/utils.py",
            "class Base:\n"
            "    pass\n"
            "\n\n"
            "class Child(Base):\n"
            "    pass\n"
            "\n\n"
            "def helper():\n"
            "    return 1\n"
            "\n\n"
            "def use():\n"
            "    return helper()\n",
        )

    pg = _graph(repo)

    assert _edges(pg, EdgeKind.CALLS) == {
        ("alpha/utils.py::utils.use", "alpha/utils.py::utils.helper"),
        ("beta/utils.py::utils.use", "beta/utils.py::utils.helper"),
    }
    assert _edges(pg, EdgeKind.INHERITS) == {
        ("alpha/utils.py::utils.Child", "alpha/utils.py::utils.Base"),
        ("beta/utils.py::utils.Child", "beta/utils.py::utils.Base"),
    }


def test_calls_through_in_repo_imports_still_resolve(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "pkg/__init__.py", "")
    _write(repo, "pkg/maths.py", "def mul(a, b):\n    return a * b\n")
    _write(
        repo,
        "pkg/models.py",
        "class Model:\n    @staticmethod\n    def build():\n        return Model()\n",
    )
    _write(
        repo,
        "app.py",
        "import pkg.maths as m\n"
        "from pkg import maths\n"
        "from pkg.maths import mul as times\n"
        "from pkg.models import Model\n"
        "\n\n"
        "def by_alias(a):\n"
        "    return m.mul(a, 2)\n"
        "\n\n"
        "def by_submodule(a):\n"
        "    return maths.mul(a, 3)\n"
        "\n\n"
        "def by_name(a):\n"
        "    return times(a, 4)\n"
        "\n\n"
        "def by_class():\n"
        "    return Model.build()\n",
    )
    _write(
        repo,
        "pkg/relative.py",
        "from .maths import mul\n\n\ndef twice(a):\n    return mul(a, 2)\n",
    )

    assert _edges(_graph(repo), EdgeKind.CALLS) == {
        ("app.py::app.by_alias", "pkg/maths.py::maths.mul"),
        ("app.py::app.by_submodule", "pkg/maths.py::maths.mul"),
        ("app.py::app.by_name", "pkg/maths.py::maths.mul"),
        ("app.py::app.by_class", "pkg/models.py::models.Model.build"),
        ("pkg/relative.py::relative.twice", "pkg/maths.py::maths.mul"),
    }


def test_call_through_package_reexport_resolves_to_definition(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "pkg/__init__.py", "from .impl import run\n")
    _write(repo, "pkg/impl.py", "def run():\n    return 1\n")
    _write(repo, "main.py", "from pkg import run\n\n\ndef main():\n    return run()\n")

    assert _edges(_graph(repo), EdgeKind.CALLS) == {
        ("main.py::main.main", "pkg/impl.py::impl.run"),
    }


def test_calls_on_locals_of_an_evident_in_repo_class_resolve(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(
        repo,
        "store.py",
        "class Store:\n"
        "    def get(self, key):\n"
        "        return key\n"
        "\n"
        "    @classmethod\n"
        "    def make(cls):\n"
        "        return cls.build_default()\n"
        "\n"
        "    @classmethod\n"
        "    def build_default(cls):\n"
        "        return cls()\n",
    )
    _write(
        repo,
        "user.py",
        "from store import Store\n"
        "\n\n"
        "def constructed():\n"
        "    s = Store()\n"
        "    return s.get(1)\n"
        "\n\n"
        "def annotated(s: Store):\n"
        "    return s.get(2)\n"
        "\n\n"
        "def rebound(load):\n"
        "    s = Store()\n"
        "    s = load()\n"
        "    return s.get(3)\n",
    )

    assert _edges(_graph(repo), EdgeKind.CALLS) == {
        ("store.py::store.Store.make", "store.py::store.Store.build_default"),
        ("user.py::user.constructed", "store.py::store.Store.get"),
        ("user.py::user.annotated", "store.py::store.Store.get"),
    }


def test_stub_file_does_not_shadow_its_implementation(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "core.py", "def helper():\n    return 1\n\n\ndef run():\n    return helper()\n")
    _write(repo, "core.pyi", "def helper() -> int: ...\ndef run() -> int: ...\n")

    calls = _edges(_graph(repo), EdgeKind.CALLS)

    assert calls == {("core.py::core.run", "core.py::core.helper")}
