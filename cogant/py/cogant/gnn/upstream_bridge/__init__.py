"""Integration with the Active Inference Institute **generalized-notation-notation** package.

The PyPI distribution name is ``generalized-notation-notation``; the import path is
``src.gnn`` (not top-level ``gnn``). This is a **core** COGANT dependency.

Upstream is **CC-BY-NC-SA-4.0**; see ``LICENSES.md`` at the package root.

All call sites use lazy ``importlib`` loading so importing ``cogant`` does not
eagerly initialize JAX/PyTorch until a bridge function runs.

Disable upstream validation in :class:`cogant.gnn.validator.GNNValidator` via
``COGANT_DISABLE_UPSTREAM_GNN=1`` (or pipeline / CLI flags).
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

from cogant.gnn.upstream_bridge.pipeline import (
    DEFAULT_SKIP_STEPS,
    UPSTREAM_STEP_SCRIPTS,
    UpstreamPipelineConfig,
    UpstreamPipelineResult,
    UpstreamStepResult,
    resolve_steps,
    run_upstream_pipeline,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _require_src_gnn() -> Any:
    """Import and return the ``src.gnn`` module (core dependency)."""
    try:
        return importlib.import_module("src.gnn")
    except ImportError as e:
        raise ImportError(
            "generalized-notation-notation (import path src.gnn) is a core COGANT "
            "dependency but failed to import. Re-run `uv sync` from the package root."
        ) from e


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
    """Outcome of calling upstream ``validate_gnn`` on markdown content."""

    available: bool
    ok: bool
    errors: list[str] = field(default_factory=list)
    version: str | None = None
    skipped_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "ok": self.ok,
            "errors": list(self.errors),
            "version": self.version,
            "skipped_reason": self.skipped_reason,
        }


def is_upstream_gnn_available() -> bool:
    """Return True if ``src.gnn`` imports successfully."""
    try:
        importlib.import_module("src.gnn")
    except ImportError:
        return False
    return True


def upstream_version() -> str | None:
    """Return ``src.gnn.__version__`` if present."""
    try:
        mod = _require_src_gnn()
        v = getattr(mod, "__version__", None)
        return v if isinstance(v, str) else None
    except ImportError:
        return None


def run_upstream_validate_gnn(markdown: str) -> UpstreamGNNValidation:
    """Run upstream ``validate_gnn`` on GNN markdown (full type-check pipeline).

    Upstream ``src.gnn.validate_gnn`` accepts ``Union[str, Path]`` but probes
    ``Path(x).exists()`` first. On POSIX, passing raw markdown with embedded
    newlines raises ``OSError: [Errno 63] File name too long`` before the
    content branch is reached (upstream 1.1.x). The defensive workaround here
    stages the markdown to a temp file and passes the path so the content
    branch is never exercised.
    """
    import tempfile

    try:
        mod = _require_src_gnn()
    except ImportError as e:
        return UpstreamGNNValidation(
            available=False,
            ok=True,
            skipped_reason=str(e),
        )

    validate_gnn = getattr(mod, "validate_gnn", None)
    if validate_gnn is None:
        return UpstreamGNNValidation(
            available=False,
            ok=True,
            skipped_reason="src.gnn has no validate_gnn",
        )

    ver = upstream_version()

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
            ok, errors = validate_gnn(tmp_path)
        finally:
            try:
                tmp_path.unlink()
            except OSError:
                pass
        err_list = list(errors) if errors else []
        return UpstreamGNNValidation(
            available=True,
            ok=bool(ok),
            errors=err_list,
            version=ver,
        )
    except Exception as e:
        logger.warning("Upstream validate_gnn raised: %s", e, exc_info=True)
        return UpstreamGNNValidation(
            available=True,
            ok=False,
            errors=[f"upstream validate_gnn raised: {e}"],
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
    """Call upstream ``validate_gnn_file`` (path or raw content)."""
    mod = _require_src_gnn()
    fn = getattr(mod, "validate_gnn_file", None)
    if fn is None:
        return {"is_valid": False, "errors": ["src.gnn has no validate_gnn_file"]}
    r = fn(content, is_content=is_content)
    return json_safe(r) if isinstance(r, dict) else {"result": json_safe(r)}


def upstream_parse_file(path: str | Path) -> Any:
    """Call upstream ``parse_gnn_file``."""
    mod = _require_src_gnn()
    return mod.parse_gnn_file(Path(path))


def upstream_discover_files(root: str | Path) -> Any:
    """Call upstream ``discover_gnn_files``."""
    mod = _require_src_gnn()
    return mod.discover_gnn_files(Path(root))


def upstream_process_directory(
    input_dir: str | Path,
    output_dir: str | Path,
    **kwargs: Any,
) -> Any:
    """Call upstream ``process_gnn_directory``."""
    mod = _require_src_gnn()
    return mod.process_gnn_directory(Path(input_dir), Path(output_dir), **kwargs)


def upstream_process_directory_lightweight(
    input_dir: str | Path,
    output_dir: str | Path,
    **kwargs: Any,
) -> Any:
    """Call upstream ``process_gnn_directory_lightweight``."""
    mod = _require_src_gnn()
    return mod.process_gnn_directory_lightweight(
        Path(input_dir), Path(output_dir), **kwargs
    )


def upstream_generate_report(*args: Any, **kwargs: Any) -> Any:
    """Call upstream ``generate_gnn_report``."""
    mod = _require_src_gnn()
    return mod.generate_gnn_report(*args, **kwargs)


def upstream_validate_structure(*args: Any, **kwargs: Any) -> Any:
    """Call upstream ``validate_gnn_structure``."""
    mod = _require_src_gnn()
    return mod.validate_gnn_structure(*args, **kwargs)


def upstream_module_info(*args: Any, **kwargs: Any) -> Any:
    """Call upstream ``get_module_info``."""
    mod = _require_src_gnn()
    return mod.get_module_info(*args, **kwargs)


def upstream_process_multi_format(
    input_dir: str | Path,
    output_dir: str | Path,
    log: Any | None = None,
    **kwargs: Any,
) -> Any:
    """Call upstream ``process_gnn_multi_format`` (may import upstream pipeline helpers)."""
    mod = _require_src_gnn()
    return mod.process_gnn_multi_format(
        Path(input_dir), Path(output_dir), log or logger, **kwargs
    )


def upstream_parse_formal(*args: Any, **kwargs: Any) -> Any:
    """Call upstream ``parse_gnn_formal``."""
    mod = _require_src_gnn()
    return mod.parse_gnn_formal(*args, **kwargs)


def upstream_validate_syntax_formal(*args: Any, **kwargs: Any) -> Any:
    """Call upstream ``validate_gnn_syntax_formal``."""
    mod = _require_src_gnn()
    return mod.validate_gnn_syntax_formal(*args, **kwargs)


def get_upstream_parsing_system() -> Any:
    """Return a new ``GNNParsingSystem`` instance."""
    mod = _require_src_gnn()
    return mod.GNNParsingSystem()


def get_upstream_gnn_format_enum() -> Any:
    """Return `GNNFormat` enum class from upstream."""
    mod = _require_src_gnn()
    return mod.GNNFormat


def parse_upstream_model_gnn_md(package_dir: str | Path) -> dict[str, Any]:
    """Parse ``model.gnn.md`` inside a COGANT GNN package directory; JSON-safe summary."""
    p = Path(package_dir) / "model.gnn.md"
    if not p.is_file():
        return {"error": f"missing {p}"}
    try:
        info = upstream_parse_file(p)
        return {"path": str(p), "parse": json_safe(info)}
    except Exception as e:
        logger.warning("upstream parse_gnn_file failed: %s", e, exc_info=True)
        return {"path": str(p), "error": str(e)}


__all__ = [
    "DEFAULT_SKIP_STEPS",
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
