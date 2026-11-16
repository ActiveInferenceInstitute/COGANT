"""GNN-specific inherited startup admission for the pinned Python workers.

Copied as sitecustomize.py into one run-owned directory. Python's startup
normally suppresses sitecustomize errors; this adapter must instead terminate
before a numbered script can execute. This is source custody, not a sandbox.
"""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import re
import sys
import types
import uuid
from collections import Counter
from pathlib import Path
from typing import Any


def entrypoint(argv: list[str]) -> str:
    for value in argv[1:]:
        if value in {"-c", "-m"}:
            return value
        if not value.startswith("-"):
            return Path(value).name
    return ""


def install_launch_guard(launches: list[str], startup: Path) -> None:
    """Refuse Python descendants that would bypass the inherited admission."""
    keys = (
        "COGANT_GNN_CUSTODY_FILE",
        "COGANT_GNN_CUSTODY_SHA256",
        "COGANT_GNN_CHILD_RECEIPTS",
        "COGANT_GNN_BOOTSTRAP",
        "COGANT_GNN_MANIFEST",
        "COGANT_GNN_PIN",
        "COGANT_GNN_ORIGIN",
        "COGANT_GNN_SOURCE_ROOT",
    )
    expected = {key: os.environ.get(key) for key in keys}
    startup_file = startup / "sitecustomize.py"
    startup_digest = hashlib.sha256(startup_file.read_bytes()).digest()

    def check_launch(executable: Any, argv: Any, environment: Any) -> None:
        name = Path(os.fsdecode(executable)).name.lower()
        if (
            not name.startswith("python")
            and Path(os.fsdecode(executable)).resolve() != Path(sys.executable).resolve()
        ):
            return
        if Path(os.fsdecode(executable)).resolve() != Path(sys.executable).resolve():
            raise RuntimeError("GNN worker selected a different Python runtime")
        if isinstance(argv, (str, bytes)):
            raise RuntimeError("GNN Python workers require explicit argv")
        tokens = [os.fsdecode(value) for value in argv]
        for token in tokens[1:]:
            if not token.startswith("-") or token in {"-m", "-c"}:
                break
            if any(flag in token[1:] for flag in "ISE"):
                raise RuntimeError("GNN worker flags would bypass source startup admission")
        child_env = os.environ if environment is None else environment
        if any(child_env.get(key) != value for key, value in expected.items()):
            raise RuntimeError("GNN worker dropped its source custody binding")
        if str(startup) not in str(child_env.get("PYTHONPATH", "")).split(os.pathsep):
            raise RuntimeError("GNN worker dropped its checked startup path")
        try:
            if hashlib.sha256(startup_file.read_bytes()).digest() != startup_digest:
                raise RuntimeError("GNN worker startup source changed")
        except OSError as exc:
            raise RuntimeError("GNN worker startup source unavailable") from exc
        launches.append(entrypoint(tokens))

    def audit(event: str, arguments: tuple[Any, ...]) -> None:
        if event == "os.fork":
            raise RuntimeError("GNN descendants require fresh spawn admission, not fork")
        if event == "subprocess.Popen":
            executable, argv, _, environment = arguments
            check_launch(executable, argv, environment)

    # multiprocessing spawn uses fork_exec directly, not subprocess.Popen.
    # Its interpreter flags inherit -I from the fresh qualification worker;
    # replace only that isolation flag with safe-path/no-user-site flags so
    # the independently checked sitecustomize can admit each target worker.
    import multiprocessing.util

    original_spawn = multiprocessing.util.spawnv_passfds

    def spawnv_passfds(executable: Any, argv: Any, passfds: Any) -> Any:
        tokens = [os.fsdecode(value) for value in argv]
        if (
            len(tokens) >= 3
            and tokens[-2] == "-c"
            and re.fullmatch(
                r"from multiprocessing\.resource_tracker import main;main\([0-9]+\)",
                tokens[-1],
            )
        ):
            # Exact isolated stdlib FD housekeeping does not import target
            # source and is not claimed as a qualified GNN worker.
            if Path(os.fsdecode(executable)).resolve() != Path(sys.executable).resolve():
                raise RuntimeError("GNN resource tracker selected a different Python runtime")
            return original_spawn(executable, argv, passfds)
        if (
            len(tokens) < 4
            or tokens[-3] != "-c"
            or not tokens[-2].startswith(
                "from multiprocessing.spawn import spawn_main; spawn_main("
            )
            or tokens[-1] != "--multiprocessing-fork"
        ):
            raise RuntimeError("GNN multiprocessing requires the supported fresh spawn entrypoint")
        rewritten = [
            flag for token in tokens for flag in (["-P", "-s"] if token == "-I" else [token])
        ]
        check_launch(executable, rewritten, None)
        return original_spawn(executable, [os.fsencode(token) for token in rewritten], passfds)

    multiprocessing.util.spawnv_passfds = spawnv_passfds
    sys.addaudithook(audit)


def verify_children(
    parent_pid: int, launches: list[str], records: list[dict[str, Any]], manifest_sha256: str
) -> None:
    expected = Counter(launches)
    observed = Counter(
        record["entrypoint"] for record in records if record["parent_pid"] == parent_pid
    )
    if expected != observed:
        raise RuntimeError(
            f"GNN worker source receipts incomplete: expected={dict(expected)}, observed={dict(observed)}"
        )
    for record in records:
        receipt = record["qualification"]
        if (
            not receipt.get("ok")
            or not receipt.get("imports_verified")
            or receipt.get("manifest_sha256") != manifest_sha256
        ):
            raise RuntimeError("GNN worker did not finalize source qualification")
        expected_children = Counter(record["children"])
        actual_children = Counter(
            child["entrypoint"] for child in records if child["parent_pid"] == record["pid"]
        )
        if expected_children != actual_children:
            raise RuntimeError("GNN descendant source receipts incomplete")


def start() -> None:
    guard = None
    active = False
    launches: list[str] = []
    try:
        path = Path(os.environ["COGANT_GNN_CUSTODY_FILE"])
        checked = path.read_bytes()
        if hashlib.sha256(checked).hexdigest() != os.environ["COGANT_GNN_CUSTODY_SHA256"]:
            raise ImportError("COGANT worker custody code changed")
        owner = types.ModuleType("_cogant_gnn_worker_custody")
        owner.__file__ = str(path)
        sys.modules[owner.__name__] = owner
        exec(compile(checked, str(path), "exec", dont_inherit=True), owner.__dict__)
        _, manifest = owner._artifact("COGANT_GNN_MANIFEST", owner.MANIFEST_SHA256)
        files = json.loads(manifest)["files"]
        guard = owner.qualified_upstream()
        destination = Path(os.environ["COGANT_GNN_CHILD_RECEIPTS"])
        script_name = Path(sys.argv[0]).name

        def finish() -> None:
            if not active or guard is None:
                return
            try:
                guard.__exit__(None, None, None)
                record = {
                    "pid": os.getpid(),
                    "parent_pid": os.getppid(),
                    "entrypoint": script_name,
                    "children": launches,
                    "qualification": receipt,
                }
                target = destination / f"{os.getpid()}-{uuid.uuid4().hex}.json"
                temporary = target.with_suffix(".tmp")
                temporary.write_text(json.dumps(record), encoding="utf-8")
                os.replace(temporary, target)
            except BaseException as exc:
                print(f"GNN source postflight refused: {exc}", file=sys.stderr, flush=True)
                os._exit(78)

        # Register before target imports so their exit handlers run inside the
        # source lifetime, before this postflight finalizes it.
        atexit.register(finish)
        _, receipt = guard.__enter__()
        active = True
        root = Path(receipt["package_root"])

        def check_compile(event: str, arguments: tuple[Any, ...]) -> None:
            if event != "compile":
                return
            source, filename = arguments
            try:
                relative = Path(os.fsdecode(filename)).resolve().relative_to(root).as_posix()
            except (TypeError, ValueError):
                return
            expected = files.get("src/gnn/" + relative)
            if expected is None:
                raise ImportError(
                    "GNN script is outside the independently frozen package inventory"
                )
            content = source.encode("utf-8") if isinstance(source, str) else source
            if not isinstance(content, bytes) or hashlib.sha256(content).hexdigest() != expected:
                raise ImportError(
                    "GNN script compile bytes differ from the frozen package inventory"
                )

        # Numbered scripts are executed as files, not imported by the checked
        # finder. Bind their actual compile bytes before Python executes them.
        sys.addaudithook(check_compile)
        install_launch_guard(launches, Path(__file__).resolve().parent)
    except BaseException as exc:
        print(f"GNN source startup refused: {exc}", file=sys.stderr, flush=True)
        os._exit(78)


if __name__ == "sitecustomize":
    start()
