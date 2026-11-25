"""Independent, byte-bound admission before executing any optional GNN code.

The producer owns pin parsing and source/origin qualification. Artifact paths
are explicit runtime inputs; neither a target installation nor its version is
an authority for the expected bootstrap or complete manifest.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib
import json
import logging
import os
import subprocess
import sys
import tempfile
import types
from collections.abc import Iterator
from pathlib import Path
from typing import Any

BOOTSTRAP_SHA256 = "f638d4c01fe7de31e43d793e59bf382d0c3d1a82f365c59238334a2b40adfb37"
MANIFEST_SHA256 = "43b33c0b2b40386afa3f306fec4cc13bc1fd7c3b570fbf11d5008bad5c8e6b51"
PIN_PATH = Path(__file__).resolve().parents[5] / ".github" / "gnn-pin.json"
_ACTIVE_MODULE: Any = None

# Fixed public data-returning operations; no arbitrary module, shell or argv API.
OPERATIONS = frozenset(
    {
        "validate_gnn_source",
        "parse_gnn_file",
        "discover_gnn_files",
        "process_gnn_directory",
        "process_gnn_directory_lightweight",
        "generate_gnn_report",
        "check_gnn_file_structure",
        "get_module_info",
        "process_gnn_multi_format",
        "parse_gnn_formal",
        "validate_gnn_syntax",
    }
)


def _artifact(variable: str, expected: str) -> tuple[Path, bytes]:
    raw = os.environ.get(variable)
    if not raw:
        raise ImportError(f"{variable} must select the independently reviewed producer artifact")
    path = Path(raw).expanduser().resolve()
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise ImportError(f"{variable} is unavailable: {type(exc).__name__}") from exc
    if hashlib.sha256(content).hexdigest() != expected:
        raise ImportError(f"{variable} failed its frozen SHA-256 binding")
    return path, content


def load_bootstrap() -> types.ModuleType:
    path, checked_bytes = _artifact("COGANT_GNN_BOOTSTRAP", BOOTSTRAP_SHA256)
    module = types.ModuleType("_cogant_reviewed_gnn_bootstrap")
    module.__file__ = str(path)
    # Dataclasses resolve their defining module during execution.
    sys.modules[module.__name__] = module
    try:
        exec(compile(checked_bytes, str(path), "exec", dont_inherit=True), module.__dict__)
    except BaseException:
        sys.modules.pop(module.__name__, None)
        raise
    return module


def read_consumer_pin(path: Path | None = None) -> Any:
    """Use the reviewed producer reader without importing the target package."""
    bootstrap = load_bootstrap()
    selected = path or Path(os.environ.get("COGANT_GNN_PIN", str(PIN_PATH)))
    return bootstrap.read_pin(selected)


@contextlib.contextmanager
def qualified_upstream() -> Iterator[tuple[Any, dict[str, Any]]]:
    """Own one fresh-process lifetime, including lazy calls and serialization.

    Normal exit finalizes the producer receipt. Source mode is explicit and
    never a fallback for an installed-origin refusal. No target object may be
    used outside this scope; ordinary bridge calls use a fresh child instead.
    """
    global _ACTIVE_MODULE
    bootstrap = load_bootstrap()
    _, manifest = _artifact("COGANT_GNN_MANIFEST", MANIFEST_SHA256)
    pin = bootstrap.read_pin(Path(os.environ.get("COGANT_GNN_PIN", str(PIN_PATH))))
    mode = os.environ.get("COGANT_GNN_ORIGIN", "installed")
    selected = os.environ.get("COGANT_GNN_SOURCE_ROOT")
    package_root = Path(selected).expanduser().resolve() if selected else None
    original_path = list(sys.path)
    if mode == "source":
        if package_root is None:
            raise ImportError("explicit source mode requires COGANT_GNN_SOURCE_ROOT")
        sys.path.insert(0, str(package_root.parent))
    elif mode != "installed":
        raise ImportError("COGANT_GNN_ORIGIN must be installed or source")
    try:
        with bootstrap.qualified_source(
            pin,
            manifest=manifest,
            manifest_sha256=MANIFEST_SHA256,
            package_root=package_root,
            origin_mode=mode,
        ) as receipt:
            module = importlib.import_module("gnn")
            _ACTIVE_MODULE = module
            try:
                yield module, receipt
            finally:
                _ACTIVE_MODULE = None
        # Execute the checked buffer only, and also refuse later artifact drift.
        _artifact("COGANT_GNN_BOOTSTRAP", BOOTSTRAP_SHA256)
        _artifact("COGANT_GNN_MANIFEST", MANIFEST_SHA256)
    except bootstrap.SourceQualificationError as exc:
        raise ImportError(f"{exc.code}: {exc}") from exc
    finally:
        sys.path[:] = original_path


def active_upstream() -> Any:
    """Return the module only inside an explicitly owned qualified lifetime."""
    if _ACTIVE_MODULE is None:
        raise ImportError("live upstream objects require qualified_upstream() in a fresh process")
    return _ACTIVE_MODULE


def invoke(operation: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
    """Return data only after the fresh worker's postflight has succeeded."""
    if any(name == "gnn" or name.startswith("gnn.") for name in sys.modules):
        raise ImportError("source-already-imported: a preloaded GNN cannot authorize a bridge call")
    if operation not in OPERATIONS | {
        "version",
        "importer-check",
        "main-available",
        "pipeline",
        "syntax-file",
    }:
        raise ValueError(f"unsupported upstream operation: {operation}")
    request = json.dumps(
        {"operation": operation, "args": args, "kwargs": kwargs, "sys_path": sys.path},
        default=lambda value: str(value) if isinstance(value, Path) else _unsupported(value),
    )
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(Path(__file__).resolve())],
            input=request,
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ImportError(f"qualified upstream worker unavailable: {type(exc).__name__}") from exc
    try:
        response = json.loads(result.stdout)
    except ValueError as exc:
        raise ImportError("qualified upstream worker returned no valid result") from exc
    if not isinstance(response, dict) or response.get("ok") is not True:
        message = (
            response.get("error", "upstream worker failed")
            if isinstance(response, dict)
            else "invalid worker response"
        )
        if isinstance(response, dict) and response.get("available"):
            raise RuntimeError(message)
        raise ImportError(message)
    receipt = response.get("qualification", {})
    if result.returncode or not receipt.get("ok") or not receipt.get("imports_verified"):
        raise ImportError("upstream worker did not finalize source qualification")
    return response


def _unsupported(value: Any) -> Any:
    raise TypeError(f"upstream arguments must be JSON data or paths, not {type(value).__name__}")


def _prepare_children(
    output: Path,
) -> tuple[list[str], Path, Path, tempfile.TemporaryDirectory[str]]:
    """Bind one run-owned startup and receipt directory for Python children."""
    from cogant.gnn.upstream_bridge.source_startup import install_launch_guard

    output.mkdir(parents=True, exist_ok=True)
    run_root = Path(tempfile.mkdtemp(prefix="_cogant_source_", dir=output))
    # Runtime Python must not become part of the next analyzed source snapshot.
    startup_owner = tempfile.TemporaryDirectory(prefix="cogant_gnn_source_")
    startup = Path(startup_owner.name)
    receipts = run_root / "workers"
    receipts.mkdir()
    (startup / "sitecustomize.py").write_bytes(
        Path(__file__).with_name("source_startup.py").read_bytes()
    )
    custody = Path(__file__).resolve()
    os.environ.update(
        COGANT_GNN_CUSTODY_FILE=str(custody),
        COGANT_GNN_CUSTODY_SHA256=hashlib.sha256(custody.read_bytes()).hexdigest(),
        COGANT_GNN_CHILD_RECEIPTS=str(receipts),
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=os.pathsep.join(
            value for value in (str(startup), os.environ.get("PYTHONPATH", "")) if value
        ),
    )
    launches: list[str] = []
    install_launch_guard(launches, startup)
    return launches, receipts, run_root, startup_owner


def _finish_children(
    state: tuple[list[str], Path, Path, tempfile.TemporaryDirectory[str]],
) -> dict[str, Any]:
    from cogant.gnn.upstream_bridge.source_startup import verify_children

    launches, receipts, run_root, startup_owner = state
    try:
        records = [
            json.loads(path.read_text(encoding="utf-8")) for path in sorted(receipts.glob("*.json"))
        ]
        verify_children(os.getpid(), launches, records, MANIFEST_SHA256)
        return {"worker_receipts": records, "custody_dir": str(run_root)}
    finally:
        startup_owner.cleanup()


def _execute_pipeline(args: list[str]) -> dict[str, Any]:
    """Run the actual pinned main and admit its Python descendants individually."""
    state = _prepare_children(Path(args[args.index("--output-dir") + 1]).resolve())
    original_argv = sys.argv
    sys.argv = ["gnn.main", *args]
    code = 0
    try:
        try:
            code = int(importlib.import_module("gnn.main").main())
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 0 if exc.code is None else 1
    finally:
        sys.argv = original_argv
    return {"returncode": code, **_finish_children(state)}


def _write_pipeline_receipt(output: Path, receipt: dict[str, Any], value: dict[str, Any]) -> None:
    target = output / "upstream_source_qualification.json"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=output, prefix=".gnn-source-", delete=False
    ) as stream:
        temporary = Path(stream.name)
        json.dump(
            {"ok": True, "run_id": os.environ.get("GNN_RUN_ID"), "main": receipt, **value}, stream
        )
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _worker() -> int:
    if sys.argv[1:2] == ["--pipeline"]:
        request: dict[str, Any] = {
            "operation": "pipeline",
            "args": sys.argv[2:],
            "kwargs": {},
            "sys_path": list(sys.path),
        }
    else:
        request = json.load(sys.stdin)
    # Import COGANT from its actual source/install location, then reproduce the
    # caller's target resolution. A shadowed GNN is checked, never imported first.
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from cogant.gnn.upstream_bridge import json_safe

    sys.path[:] = request["sys_path"]
    operation = request["operation"]
    available = False
    child_proof: dict[str, Any] = {}
    try:
        with contextlib.redirect_stdout(sys.stderr):
            with qualified_upstream() as (module, receipt):
                available = True
                args = list(request["args"])
                kwargs = request["kwargs"]
                if operation == "version":
                    value = module.__version__
                elif operation == "importer-check":
                    bootstrap = sys.modules["_cogant_reviewed_gnn_bootstrap"]
                    value = bootstrap.check_importer(Path(args[0]), **kwargs)
                elif operation == "syntax-file":
                    value = json_safe(
                        module.validate_gnn_syntax(Path(args[0]), *args[1:], **kwargs)
                    )
                elif operation == "main-available":
                    importlib.import_module("gnn.main")
                    value = True
                elif operation == "pipeline":
                    value = _execute_pipeline(args)
                elif operation in OPERATIONS:
                    if (
                        operation in {"parse_gnn_file", "discover_gnn_files", "parse_gnn_formal"}
                        and args
                    ):
                        args[0] = Path(args[0])
                    if operation in {
                        "process_gnn_directory",
                        "process_gnn_directory_lightweight",
                        "process_gnn_multi_format",
                    }:
                        args[:2] = [Path(value) for value in args[:2]]
                        if operation == "process_gnn_multi_format":
                            name = args[2]
                            if name is not None and not isinstance(name, str):
                                raise ValueError("upstream logger name must be a string or null")
                            args[2] = logging.getLogger(name or "cogant.gnn.upstream_bridge")
                        child_state = _prepare_children(Path(args[1]))
                    else:
                        child_state = None
                    value = getattr(module, operation)(*args, **kwargs)
                    # Exhaust lazy discovery and convert target-owned objects
                    # before leaving the checked-loader lifetime.
                    if isinstance(value, Iterator):
                        value = list(value)
                    value = json_safe(value)
                    if child_state is not None:
                        child_proof = _finish_children(child_state)
                else:
                    raise ValueError(f"unsupported upstream operation: {operation}")
                version = getattr(module, "__version__", None)
        if operation == "importer-check":
            value["source_qualification"] = receipt
            value["qualified"] = bool(
                value["ok"] and value["specs"].get("validated") and receipt["imports_verified"]
            )
        if operation == "pipeline":
            _write_pipeline_receipt(Path(args[args.index("--output-dir") + 1]), receipt, value)
        print(
            json.dumps(
                {
                    "ok": True,
                    "value": value,
                    "version": version,
                    "qualification": receipt,
                    "worker_qualification": child_proof,
                }
            )
        )
        return int(value["returncode"]) if operation == "pipeline" else 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "available": available and not isinstance(exc, ImportError),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(_worker())
