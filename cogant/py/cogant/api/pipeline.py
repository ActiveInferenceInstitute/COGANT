"""PipelineRunner: Orchestrates all analysis stages in sequence."""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cogant.api import orchestration
from cogant.api.bundle import Bundle

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution."""

    stages: list[str] = field(default_factory=lambda: [
        "ingest",
        "static",
        "normalize",
        "graph",
        "dynamic",
        "translate",
        "statespace",
        "process",
        "export",
        "validate",
    ])
    """Stages to execute in order."""

    skip_stages: list[str] = field(default_factory=list)
    """Stages to skip."""

    plugins: dict[str, dict[str, Any]] = field(default_factory=dict)
    """Plugin configurations."""

    output_dir: str = "output"
    """Output directory for artifacts."""

    verbose: bool = False
    """Enable verbose logging."""

    dry_run: bool = False
    """Run without side effects."""

    layout_output: bool = False
    """After export, move flat artifacts into data/, diagrams/, site/, reports/, figures/."""

    skip_dynamic: bool = False
    """Explicit opt-out for the dynamic-analysis enrichment stage.

    When ``True``, the ``dynamic`` stage is treated as skipped for the
    duration of a single ``run()`` even when it would otherwise appear in
    ``stages``. This is the flag wired to the ``--no-dynamic`` CLI option
    and lets callers disable dynamic enrichment without having to edit
    the stage list by hand.
    """

    coverage_path: str | None = None
    """Explicit path to a coverage database (``.coverage`` or ``coverage.xml``).

    When set, the dynamic stage uses this file directly. When ``None``,
    the dynamic stage looks for ``plugins['dynamic']['coverage_path']``,
    then falls back to auto-detecting a ``.coverage`` file at the target
    root before deciding there is no coverage data available.
    """

    trace_path: str | None = None
    """Explicit path to a Chrome DevTools trace JSON file.

    When set, the dynamic stage uses this file directly. When ``None``,
    the dynamic stage looks for ``plugins['dynamic']['trace_path']``
    before deciding there is no trace data available.
    """

    incremental_since: str | None = None
    """Git ref (commit, tag, branch) to use as the incremental baseline.

    When set, ``PipelineRunner.run`` will attempt to load a previously
    cached bundle for the target and only re-run the ingest / static /
    graph stages for Python files that changed between ``incremental_since``
    and ``HEAD``. A dict summarising the incremental run is recorded on
    ``bundle.metadata['incremental_stats']`` with the following keys:

    * ``enabled`` — ``True`` whenever this field is set
    * ``since`` — the ref that was passed in
    * ``files_total`` — number of Python files in the repo
    * ``files_reparsed`` — number of Python files that needed re-parsing
    * ``cache_hit`` — ``True`` if a cached bundle was found and used
    * ``reason`` — free-form explanation when ``cache_hit`` is ``False``

    When ``None`` (the default), the pipeline behaves exactly as before
    and never touches the cache. This makes incremental mode strictly
    opt-in so existing callers and tests keep the same semantics.
    """

    cache_dir: str | None = None
    """Override for the cache directory used by incremental mode.

    When ``None``, incremental mode uses ``~/.cache/cogant``. Setting
    this lets tests and benchmarks isolate cache state to a tmp dir.
    """


__all__ = ["PipelineConfig", "PipelineRunner"]


class PipelineRunner:
    """
    Orchestrates the full analysis pipeline.

    Pipeline stages:
      1. ingest: Load and parse target codebase
      2. static: Extract static analysis (AST, types)
      3. normalize: Normalize representations
      4. graph: Build program dependency graph
      5. dynamic: Enrich graph with coverage/trace data
      6. translate: Translate to GNN
      7. statespace: Compile state space model
      8. process: Extract process/execution model
      9. export: Export all artifacts
     10. validate: Run validation checks

    Usage:
        runner = PipelineRunner()
        bundle = runner.run("path/to/repo", config)
    """

    def __init__(self) -> None:
        """Initialize pipeline runner."""
        self.stage_handlers: dict[str, Callable[..., Any]] = {
            "ingest": self._stage_ingest,
            "static": self._stage_static,
            "normalize": self._stage_normalize,
            "graph": self._stage_graph,
            "dynamic": self._stage_dynamic,
            "translate": self._stage_translate,
            "statespace": self._stage_statespace,
            "process": self._stage_process,
            "export": self._stage_export,
            "validate": self._stage_validate,
        }

    def run(
        self, target: str, config: PipelineConfig | None = None
    ) -> Bundle:
        """
        Execute the full pipeline.

        Args:
            target: Path or URL to analyze.
            config: Pipeline configuration.

        Returns:
            Bundle with all artifacts.
        """
        if config is None:
            config = PipelineConfig()

        logger.info(f"Starting pipeline for target: {target}")

        bundle = Bundle(target=target, metadata={"config": vars(config)})

        # Incremental-mode pre-flight: try to short-circuit the full run
        # when the caller opted in and a cached bundle is available. On a
        # full cache hit we return the cached bundle unmodified; on a
        # partial hit we stash the restricted file list under
        # ``bundle.metadata['_incremental']`` so ``run_ingest`` can pick
        # it up and re-parse only the changed subset.
        if config.incremental_since:
            cache_outcome = self._incremental_preflight(target, bundle, config)
            if cache_outcome == "full_hit":
                logger.info(
                    "Incremental mode: full cache hit, returning cached bundle"
                )
                return bundle

        # Build the effective skip set. ``skip_dynamic`` acts as a shorthand
        # for adding ``"dynamic"`` to ``skip_stages`` without mutating the
        # caller-provided config object.
        effective_skip: set[str] = set(config.skip_stages)
        if config.skip_dynamic:
            effective_skip.add("dynamic")

        # Execute each stage in order
        for stage in config.stages:
            if stage in effective_skip:
                logger.info(f"Skipping stage: {stage}")
                if stage == "dynamic" and config.skip_dynamic:
                    bundle.stage_results[stage] = {
                        "type": "dynamic_enrichment",
                        "skipped": True,
                        "reason": "skip_dynamic=True",
                    }
                continue

            if stage not in self.stage_handlers:
                error = f"Unknown stage: {stage}"
                logger.error(error)
                bundle.errors.append(error)
                continue

            try:
                logger.info(f"Running stage: {stage}")
                handler = self.stage_handlers[stage]
                result = handler(bundle, config)
                bundle.stage_results[stage] = result
                logger.info(f"Stage {stage} completed successfully")
            except Exception as e:
                error = f"Stage {stage} failed: {str(e)}"
                logger.error(error)
                bundle.errors.append(error)
                # Continue to next stage even if one fails
                continue

        if (
            config.layout_output
            and not config.dry_run
            and "export" in config.stages
            and "export" not in config.skip_stages
        ):
            try:
                from cogant.tools.organize_example_outputs import organize_run_dir

                organize_run_dir(Path(config.output_dir), dry_run=False)
            except Exception as e:
                logger.warning("layout_output post-pass failed: %s", e)

        # Write an incremental-mode cache snapshot at the end of every
        # run that touched real stages. This is the "save" half of the
        # incremental round trip: the very next run against the same
        # target will see this bundle via ``_incremental_preflight``.
        if config.incremental_since is not None and not config.dry_run:
            try:
                self._incremental_cache_save(target, bundle, config)
            except Exception as e:  # pragma: no cover - defensive
                logger.warning("Incremental cache save failed: %s", e)

        logger.info(f"Pipeline completed with {len(bundle.errors)} errors")
        return bundle

    # ------------------------------------------------------------------
    # Incremental-mode helpers
    # ------------------------------------------------------------------

    def _incremental_preflight(
        self, target: str, bundle: Bundle, config: PipelineConfig
    ) -> str:
        """Inspect the cache and prepare a restricted run.

        Returns one of:

        * ``"full_hit"`` — nothing changed since ``config.incremental_since``
          and a cached bundle was successfully restored onto ``bundle``.
          The caller should return the bundle directly.
        * ``"partial"`` — a cached bundle exists but some files changed;
          the restricted file list is recorded on
          ``bundle.metadata['_incremental']`` so ``run_ingest`` can honor
          it. Downstream stages still run over the merged result.
        * ``"miss"`` — no usable cache entry or no git repo; the caller
          falls back to a full run (incremental stats still recorded).
        """
        from cogant import __version__ as _cogant_version
        from cogant.cache.store import CacheKey, CacheStore
        from cogant.ingest.incremental import IncrementalIngester

        repo_path = Path(target).expanduser().resolve()
        stats: dict[str, Any] = {
            "enabled": True,
            "since": config.incremental_since,
            "files_total": 0,
            "files_reparsed": 0,
            "cache_hit": False,
            "reason": None,
        }
        bundle.metadata["incremental_stats"] = stats

        if not repo_path.is_dir():
            stats["reason"] = "target is not a directory"
            return "miss"

        ingester = IncrementalIngester(repo_path)
        if not ingester.is_git_repo():
            stats["reason"] = "target is not a git repository"
            return "miss"

        # Count total Python files (used to compute the "reparsed ratio"
        # and to drive the content-hash key for the cache).
        all_py = [
            p
            for p in repo_path.rglob("*.py")
            if not any(
                part in {".git", ".venv", "__pycache__", "node_modules"}
                for part in p.parts
            )
        ]
        stats["files_total"] = len(all_py)

        # Build the cache key. ``content_hash`` here is a stable digest
        # of ``(repo_path, cogant_version)`` — not a content hash of the
        # repo itself. Incremental mode uses the git working tree as
        # its authoritative source of truth, so we don't want to invalidate
        # the cache on *every* file edit; instead, the cache is keyed on
        # the repo identity and we let the git diff decide what to reuse.
        import hashlib

        digest = hashlib.sha256()
        digest.update(str(repo_path).encode())
        digest.update(_cogant_version.encode())
        key = CacheKey(
            repo_path=str(repo_path),
            content_hash=digest.hexdigest(),
            cogant_version=_cogant_version,
        )

        cache_dir = Path(config.cache_dir) if config.cache_dir else None
        store = CacheStore(cache_dir=cache_dir)
        entry = store.get(key)

        changed = ingester.python_files_changed_since(config.incremental_since)
        # ``changed`` contains absolute paths already resolved against the
        # repo root. Keep only the ones that actually exist on disk.
        changed = [p for p in changed if p.exists()]
        stats["files_reparsed"] = len(changed)

        if entry is None:
            stats["reason"] = "no cached bundle"
            return "miss"

        # Restore the cached stage_results onto the bundle. Artifacts are
        # *not* restored (they contain live Python objects that would not
        # round-trip through JSON), but stage_results carry every piece
        # of information the CLI actually displays to the user.
        cached = entry.stage_results
        bundle.stage_results.update(cached.get("stage_results") or {})
        bundle.errors = list(cached.get("errors") or [])
        stats["cache_hit"] = True

        if not changed:
            # Full hit: the user asked "what changed since <ref>?" and
            # the answer is "nothing". Return the cached bundle as-is.
            return "full_hit"

        # Partial hit: downstream stages will re-run, but ``run_ingest``
        # will restrict itself to the changed files. Pass the restricted
        # list through bundle metadata so orchestration.run_ingest can
        # read it without us having to thread a new parameter through
        # every stage signature.
        bundle.metadata["_incremental"] = {
            "changed_files": [str(p) for p in changed],
            "changed_count": len(changed),
        }
        stats["reason"] = f"{len(changed)} file(s) changed"
        return "partial"

    def _incremental_cache_save(
        self, target: str, bundle: Bundle, config: PipelineConfig
    ) -> None:
        """Persist the bundle's stage_results into the incremental cache.

        Only JSON-serialisable content is stored (``stage_results`` +
        ``errors``). Live artifacts such as the ``ProgramGraph`` live
        on ``bundle.artifacts`` and are rebuilt from ``stage_results``
        on the next run via the normal pipeline re-execution.

        ``stage_results`` can contain datetimes and other rich types
        that plain ``json.dump`` rejects. We round-trip through the
        Bundle's own ``_json_default`` to coerce them to JSON-native
        values before handing the dict to the cache store, which
        itself uses plain ``json.dump``.
        """
        import hashlib
        import json as _json

        from cogant import __version__ as _cogant_version
        from cogant.api.bundle import _json_default
        from cogant.cache.store import CacheKey, CacheStore

        repo_path = Path(target).expanduser().resolve()
        digest = hashlib.sha256()
        digest.update(str(repo_path).encode())
        digest.update(_cogant_version.encode())
        key = CacheKey(
            repo_path=str(repo_path),
            content_hash=digest.hexdigest(),
            cogant_version=_cogant_version,
        )
        cache_dir = Path(config.cache_dir) if config.cache_dir else None
        store = CacheStore(cache_dir=cache_dir)

        safe_results = _json.loads(
            _json.dumps(bundle.stage_results, default=_json_default)
        )
        safe_errors = list(bundle.errors)
        store.put(
            key,
            {
                "stage_results": safe_results,
                "errors": safe_errors,
            },
        )

    def _stage_ingest(
        self, bundle: Bundle, config: PipelineConfig
    ) -> dict[str, Any]:
        """Ingest: Load and parse target codebase."""
        if config.dry_run:
            return {"type": "ingest", "dry_run": True, "target": bundle.target}
        return orchestration.run_ingest(bundle.target, bundle)

    def _stage_static(
        self, bundle: Bundle, config: PipelineConfig
    ) -> dict[str, Any]:
        """Static analysis: Extract AST, types, symbols."""
        if config.dry_run:
            return {"type": "static_analysis", "dry_run": True}
        return orchestration.run_static(bundle)

    def _stage_normalize(
        self, bundle: Bundle, config: PipelineConfig
    ) -> dict[str, Any]:
        """Normalize: Unify representations."""
        if config.dry_run:
            return {"type": "normalized", "dry_run": True}
        return orchestration.run_normalize(bundle)

    def _stage_graph(
        self, bundle: Bundle, config: PipelineConfig
    ) -> dict[str, Any]:
        """Graph: Build program dependency graph."""
        if config.dry_run:
            return {"type": "program_graph", "dry_run": True}
        return orchestration.run_graph(bundle, bundle.target)

    def _stage_dynamic(
        self, bundle: Bundle, config: PipelineConfig
    ) -> dict[str, Any]:
        """Run dynamic analysis enrichment.

        Resolution order for coverage / trace paths:

        1. Explicit ``config.coverage_path`` / ``config.trace_path`` fields.
        2. ``config.plugins['dynamic']['coverage_path']`` / ``['trace_path']``.
        3. Auto-detection of ``.coverage`` at the target root for coverage.

        When neither path can be resolved, the stage is a no-op and reports
        ``skipped=True`` with ``reason='no dynamic data available'`` so that
        downstream tooling and tests can tell the difference between "ran
        and had nothing to enrich" and "explicitly disabled".
        """
        if config.dry_run:
            return {"type": "dynamic_enrichment", "dry_run": True}

        plugins_dynamic = config.plugins.get("dynamic", {}) if config.plugins else {}
        coverage_path = config.coverage_path or plugins_dynamic.get("coverage_path")
        trace_path = config.trace_path or plugins_dynamic.get("trace_path")

        # Auto-detect a .coverage file under the target if nothing was supplied.
        if coverage_path is None:
            try:
                from pathlib import Path as _Path

                target_path = _Path(bundle.target)
                if target_path.exists() and target_path.is_dir():
                    candidate = target_path / ".coverage"
                    if candidate.exists() and candidate.is_file():
                        coverage_path = str(candidate)
                        logger.info(
                            "Dynamic stage auto-detected coverage at %s", coverage_path
                        )
            except Exception:  # noqa: BLE001
                logger.debug("Coverage auto-detection skipped", exc_info=True)

        if coverage_path is None and trace_path is None:
            logger.info(
                "Dynamic stage: no coverage or trace data found; skipping enrichment"
            )
            return {
                "type": "dynamic_enrichment",
                "skipped": True,
                "reason": "no dynamic data available",
                "coverage_nodes_enriched": 0,
                "trace_nodes_enriched": 0,
            }

        result = orchestration.run_dynamic(
            bundle,
            coverage_path=coverage_path,
            trace_path=trace_path,
        )
        if coverage_path is not None:
            result["coverage_path"] = coverage_path
        if trace_path is not None:
            result["trace_path"] = trace_path
        return result

    def _stage_translate(
        self, bundle: Bundle, config: PipelineConfig
    ) -> dict[str, Any]:
        """Translate: Convert to GNN representation."""
        if config.dry_run:
            return {"type": "gnn_model", "dry_run": True}
        return orchestration.run_translate(bundle)

    def _stage_statespace(
        self, bundle: Bundle, config: PipelineConfig
    ) -> dict[str, Any]:
        """Statespace: Compile semantic state space."""
        if config.dry_run:
            return {"type": "state_space_model", "dry_run": True}
        return orchestration.run_statespace(bundle, bundle.target)

    def _stage_process(
        self, bundle: Bundle, config: PipelineConfig
    ) -> dict[str, Any]:
        """Process: Extract execution model."""
        if config.dry_run:
            return {"type": "process_model", "dry_run": True}
        return orchestration.run_process(bundle, bundle.target)

    def _stage_export(
        self, bundle: Bundle, config: PipelineConfig
    ) -> dict[str, Any]:
        """Export: Write all artifacts to disk."""
        if config.dry_run:
            return {"type": "export", "dry_run": True, "output_dir": config.output_dir}
        return orchestration.run_export(bundle, config.output_dir)

    def _stage_validate(
        self, bundle: Bundle, config: PipelineConfig
    ) -> dict[str, Any]:
        """Validate: Run validation checks."""
        if config.dry_run:
            return {"type": "validation", "dry_run": True, "passed": True}
        return orchestration.run_validate(bundle)
