"""Integration with the Active Inference Institute **generalized-notation-notation** package.

The PyPI distribution name is ``generalized-notation-notation``; since GNN 4.x
the installed wheel ships the top-level ``gnn`` package (the GNN 2.x
``src.gnn`` import surface was removed upstream). This is an **optional**
COGANT extra (``cogant[upstream]``); the bridge requires GNN >= 4.0, whose
public API uses ``validate_gnn_syntax`` / ``validate_gnn_source`` /
``check_gnn_file_structure`` (the GNN 2.x ``validate_gnn*`` aliases were
deleted upstream).

Upstream is **CC-BY-NC-SA-4.0**; see ``LICENSES.md`` at the package root.

All call sites use lazy ``importlib`` loading so importing ``cogant`` does not
eagerly initialize JAX/PyTorch until a bridge function runs.

Enable upstream validation explicitly with ``COGANT_ENABLE_UPSTREAM_GNN=1`` or
the validator/pipeline/CLI option.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cogant.gnn.upstream_bridge.pipeline import (
    DEFAULT_SKIP_STEPS,
    UPSTREAM_STEP_SCRIPTS,
    UpstreamPipelineConfig,
    UpstreamPipelineResult,
    UpstreamStepResult,
    resolve_steps,
    run_upstream_pipeline,
)
from cogant.gnn.upstream_bridge.qualification import OPERATIONS, invoke

logger = logging.getLogger(__name__)

UPSTREAM_DISTRIBUTION = "generalized-notation-notation"
"""PyPI distribution that provides the upstream ``gnn`` package."""

UPSTREAM_IMPORT_NAME = "gnn"
"""Top-level import package shipped by the upstream wheel (GNN >= 4.0)."""

MIN_UPSTREAM_MAJOR = 4
"""Oldest upstream major release whose public API this bridge targets."""

DEFAULT_VALIDATION_LEVEL = "standard"
"""Upstream ``ValidationLevel`` used by :func:`run_upstream_validate_gnn`."""


def _major_version(version: str | None) -> int | None:
    if not version:
        return None
    head = version.strip().lstrip("v").split(".", 1)[0]
    return int(head) if head.isdigit() else None


class _Upstream:
    """Data-only calls; target objects and lazy imports stay in a fresh worker."""

    def __init__(self) -> None:
        self.source_qualification: dict[str, Any] = {}
        self._version: str | None = None

    def _call(self, operation: str, *args: Any, **kwargs: Any) -> Any:
        if operation == "validate_gnn_syntax" and args and isinstance(args[0], Path):
            operation = "syntax-file"
        response = invoke(operation, *args, **kwargs)
        self.source_qualification = response["qualification"]
        self._version = response.get("version")
        return response["value"]

    @property
    def __version__(self) -> str | None:
        if self._version is None:
            self._version = self._call("version")
        return self._version

    def __getattr__(self, name: str) -> Any:
        if name not in OPERATIONS:
            raise AttributeError(name)
        return lambda *args, **kwargs: self._call(name, *args, **kwargs)


def _require_upstream_gnn() -> Any:
    """Select optional execution; the worker authenticates origin and full content."""
    import importlib.metadata
    import os

    if os.environ.get("COGANT_GNN_ORIGIN", "installed") == "installed":
        try:
            version = importlib.metadata.version(UPSTREAM_DISTRIBUTION)
        except importlib.metadata.PackageNotFoundError as exc:
            raise ImportError(
                "Install the pinned optional cogant[upstream] extra; core COGANT remains usable without it."
            ) from exc
        major = _major_version(version)
        if major is None or major < MIN_UPSTREAM_MAJOR:
            raise ImportError(
                f"generalized-notation-notation {version} does not meet the bridge API floor"
            )
    return _Upstream()


def json_safe(obj: Any) -> Any:
    """Best-effort JSON-serializable view of an upstream return value."""
    if obj is None or isinstance(obj, str | int | float | bool):
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(x) for x in obj]
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        try:
            return json_safe(obj.model_dump())
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        try:
            return json_safe(vars(obj))
        except Exception:
            pass
    return str(obj)


@dataclass(frozen=True)
class UpstreamGNNValidation:
    """Outcome of calling upstream ``validate_gnn_syntax`` on markdown content."""

    available: bool
    ok: bool
    errors: list[str] = field(default_factory=list)
    version: str | None = None
    skipped_reason: str | None = None
    source_qualification: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "ok": self.ok,
            "errors": list(self.errors),
            "version": self.version,
            "skipped_reason": self.skipped_reason,
            "source_qualification": self.source_qualification,
        }


def is_upstream_gnn_available() -> bool:
    """Return True if the upstream ``gnn`` package (GNN >= 4.0) imports successfully."""
    try:
        _ = _require_upstream_gnn().__version__
    except ImportError:
        return False
    return True


def upstream_version() -> str | None:
    """Return the upstream ``gnn.__version__`` if available."""
    try:
        mod = _require_upstream_gnn()
    except ImportError:
        return None
    v = getattr(mod, "__version__", None)
    return v if isinstance(v, str) else None


def run_upstream_validate_gnn(
    markdown: str,
    *,
    validation_level: str = DEFAULT_VALIDATION_LEVEL,
) -> UpstreamGNNValidation:
    """Run upstream ``validate_gnn_syntax`` on GNN markdown.

    Upstream ``gnn.validate_gnn_syntax`` delegates to the formal
    ``schema_validator`` pipeline: every required section must be present with
    substantive content, and (at ``standard`` and above) connection endpoints
    must reference declared variables. The markdown is staged to a temporary
    ``.gnn.md`` file so the verdict never depends on upstream's
    path-versus-content probe of the input string.

    Args:
        markdown: GNN markdown document.
        validation_level: Upstream ``ValidationLevel`` name
            (``basic`` / ``standard`` / ``strict`` / ``research`` /
            ``round_trip``). Unknown levels are reported as a validation
            error by upstream rather than silently skipped.
    """
    import tempfile

    try:
        mod = _require_upstream_gnn()
    except ImportError as e:
        return UpstreamGNNValidation(
            available=False,
            ok=False,
            skipped_reason=(
                f"{e} core COGANT validation remains available; this optional upstream "
                "check was skipped."
            ),
        )

    validate_gnn_syntax = getattr(mod, "validate_gnn_syntax", None)
    if validate_gnn_syntax is None:
        return UpstreamGNNValidation(
            available=False,
            ok=False,
            skipped_reason="upstream gnn has no validate_gnn_syntax",
        )

    ver = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".gnn.md",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write(markdown)
            tmp_path = Path(tmp.name)
        try:
            ok, errors = validate_gnn_syntax(tmp_path, validation_level)
        finally:
            try:
                tmp_path.unlink()
            except OSError:
                pass
        err_list = [str(e) for e in errors] if errors else []
        ver = getattr(mod, "__version__", None)
        return UpstreamGNNValidation(
            available=True,
            ok=bool(ok),
            errors=err_list,
            version=ver,
            source_qualification=getattr(mod, "source_qualification", {}),
        )
    except ImportError as e:
        return UpstreamGNNValidation(available=False, ok=False, skipped_reason=str(e))
    except Exception as e:
        try:
            ver = getattr(mod, "__version__", None)
        except ImportError:
            ver = None
        logger.warning("Upstream validate_gnn_syntax raised: %s", e, exc_info=True)
        return UpstreamGNNValidation(
            available=True,
            ok=False,
            errors=[f"upstream validate_gnn_syntax raised: {e}"],
            version=ver,
        )


def upstream_validate_markdown(markdown: str) -> UpstreamGNNValidation:
    """Alias for :func:`run_upstream_validate_gnn`."""
    return run_upstream_validate_gnn(markdown)


def upstream_validate_file_content(
    content: str,
    *,
    is_content: bool = True,
) -> dict[str, Any]:
    """Call upstream ``validate_gnn_source`` (path or raw content)."""
    mod = _require_upstream_gnn()
    fn = getattr(mod, "validate_gnn_source", None)
    if fn is None:
        return {"is_valid": False, "errors": ["upstream gnn has no validate_gnn_source"]}
    r = fn(content, is_content=is_content)
    return json_safe(r) if isinstance(r, dict) else {"result": json_safe(r)}


def upstream_parse_file(path: str | Path) -> Any:
    """Call upstream ``parse_gnn_file``."""
    mod = _require_upstream_gnn()
    return json_safe(mod.parse_gnn_file(Path(path)))


def upstream_discover_files(root: str | Path) -> Any:
    """Call upstream ``discover_gnn_files``."""
    mod = _require_upstream_gnn()
    return json_safe(mod.discover_gnn_files(Path(root)))


def upstream_process_directory(
    input_dir: str | Path,
    output_dir: str | Path,
    **kwargs: Any,
) -> Any:
    """Call upstream ``process_gnn_directory``."""
    mod = _require_upstream_gnn()
    return mod.process_gnn_directory(Path(input_dir), Path(output_dir), **kwargs)


def upstream_process_directory_lightweight(
    input_dir: str | Path,
    output_dir: str | Path,
    **kwargs: Any,
) -> Any:
    """Call upstream ``process_gnn_directory_lightweight``."""
    mod = _require_upstream_gnn()
    return mod.process_gnn_directory_lightweight(Path(input_dir), Path(output_dir), **kwargs)


def upstream_generate_report(*args: Any, **kwargs: Any) -> Any:
    """Call upstream ``generate_gnn_report``."""
    mod = _require_upstream_gnn()
    return mod.generate_gnn_report(*args, **kwargs)


def upstream_validate_structure(*args: Any, **kwargs: Any) -> Any:
    """Call upstream ``check_gnn_file_structure`` (GNN 2.x ``validate_gnn_structure``)."""
    mod = _require_upstream_gnn()
    return mod.check_gnn_file_structure(*args, **kwargs)


def upstream_module_info(*args: Any, **kwargs: Any) -> Any:
    """Call upstream ``get_module_info``."""
    mod = _require_upstream_gnn()
    return mod.get_module_info(*args, **kwargs)


def upstream_process_multi_format(
    input_dir: str | Path,
    output_dir: str | Path,
    log: Any | None = None,
    **kwargs: Any,
) -> Any:
    """Call upstream ``process_gnn_multi_format`` (may import upstream pipeline helpers)."""
    mod = _require_upstream_gnn()
    return mod.process_gnn_multi_format(Path(input_dir), Path(output_dir), None, **kwargs)


def upstream_parse_formal(*args: Any, **kwargs: Any) -> Any:
    """Call upstream ``parse_gnn_formal``."""
    mod = _require_upstream_gnn()
    return mod.parse_gnn_formal(*args, **kwargs)


def upstream_validate_syntax_formal(*args: Any, **kwargs: Any) -> Any:
    """Call upstream ``validate_gnn_syntax`` (GNN 2.x ``validate_gnn_syntax_formal``)."""
    mod = _require_upstream_gnn()
    return mod.validate_gnn_syntax(*args, **kwargs)


def get_upstream_parsing_system() -> Any:
    """Construct a real parser inside the caller's qualified_upstream scope."""
    from cogant.gnn.upstream_bridge.qualification import active_upstream

    return active_upstream().GNNParsingSystem()


def get_upstream_gnn_format_enum() -> Any:
    """Access the real enum inside the caller's qualified_upstream scope."""
    from cogant.gnn.upstream_bridge.qualification import active_upstream

    return active_upstream().GNNFormat


def parse_upstream_model_gnn_md(package_dir: str | Path) -> dict[str, Any]:
    """Parse ``model.gnn.md`` inside a COGANT GNN package directory; JSON-safe summary.

    Returns ``{"path", "parse"}`` on success. When the optional
    ``cogant[upstream]`` extra is not installed (an expected configuration)
    returns ``{"path", "error", "available": False}`` and logs only at debug
    level; a genuine upstream parse failure returns ``{"path", "error"}`` and
    logs a warning with the traceback.
    """
    p = Path(package_dir) / "model.gnn.md"
    if not p.is_file():
        return {"error": f"missing {p}"}
    try:
        _require_upstream_gnn()
    except ImportError as e:
        logger.debug("upstream parse_gnn_file skipped: %s", e)
        return {"path": str(p), "error": str(e), "available": False}
    try:
        info = upstream_parse_file(p)
        return {"path": str(p), "parse": json_safe(info)}
    except Exception as e:
        logger.warning("upstream parse_gnn_file failed: %s", e, exc_info=True)
        return {"path": str(p), "error": str(e)}


__all__ = [
    "DEFAULT_SKIP_STEPS",
    "DEFAULT_VALIDATION_LEVEL",
    "MIN_UPSTREAM_MAJOR",
    "UPSTREAM_DISTRIBUTION",
    "UPSTREAM_IMPORT_NAME",
    "UPSTREAM_STEP_SCRIPTS",
    "UpstreamGNNValidation",
    "UpstreamPipelineConfig",
    "UpstreamPipelineResult",
    "UpstreamStepResult",
    "get_upstream_gnn_format_enum",
    "get_upstream_parsing_system",
    "is_upstream_gnn_available",
    "json_safe",
    "parse_upstream_model_gnn_md",
    "resolve_steps",
    "run_upstream_pipeline",
    "run_upstream_validate_gnn",
    "upstream_discover_files",
    "upstream_generate_report",
    "upstream_module_info",
    "upstream_parse_file",
    "upstream_parse_formal",
    "upstream_process_directory",
    "upstream_process_directory_lightweight",
    "upstream_process_multi_format",
    "upstream_validate_file_content",
    "upstream_validate_markdown",
    "upstream_validate_structure",
    "upstream_validate_syntax_formal",
    "upstream_version",
]
