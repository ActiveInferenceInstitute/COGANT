"""PipelineRunner: Orchestrates all analysis stages in sequence."""

import hashlib
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cogant.api import orchestration
from cogant.api.bundle import Bundle, StageOutcome
from cogant.config.pipeline import PipelineConfig

logger = logging.getLogger(__name__)




@dataclass
class PipelineResult:
    """Result of a full pipeline run.

    Wraps the output of a complete pipeline execution with timing,
    stage outputs, warnings, and the final bundle.

    Attributes:
        bundle: The final artifact bundle.
        timing: Per-stage timing breakdown in milliseconds.
        stage_outputs: Raw outputs from each executed stage.
        warnings: Non-fatal warnings collected during execution.
        total_duration_ms: Total pipeline duration in milliseconds.
    """

    bundle: Bundle
    timing: dict[str, float] = field(default_factory=dict)
    stage_outputs: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    total_duration_ms: float = 0.0


__all__ = ["PipelineConfig", "PipelineResult", "PipelineRunner"]


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

    def run(self, target: str, config: PipelineConfig | None = None) -> Bundle:
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

        logger.info(
            "Starting pipeline for target: %s (%d stages, %d skipped)",
            target,
            len(config.stages),
            len(config.skip_stages),
        )

        bundle = Bundle(target=target, metadata={"config": config.model_dump(mode="json")})
        bundle.metadata["version"] = self._package_version()
        contract = self._contract_metadata()
        bundle.metadata.update(contract)
        try:
            from cogant.cache.hasher import hash_repo

            source_path = Path(target).expanduser().resolve()
            if source_path.is_dir():
                bundle.metadata["source_content_digest"] = hash_repo(source_path)
        except (OSError, ValueError):
            # Remote/non-filesystem targets retain their identity without a
            # misleading local content digest.
            pass

        # Incremental-mode pre-flight: try to short-circuit the full run
        # when the caller opted in and a cached bundle is available. On a
        # full cache hit we return the cached bundle unmodified; on a
        # partial hit we stash the restricted file list under
        # ``bundle.metadata['_incremental']`` so ``run_ingest`` can pick
        # it up and re-parse only the changed subset.
        if config.incremental_since:
            cache_outcome = self._incremental_preflight(target, bundle, config)
            if cache_outcome == "full_hit":
                logger.info("Incremental mode: full cache hit, returning cached bundle")
                bundle.metadata["stage_outcomes"] = {
                    name: outcome.value for name, outcome in bundle.stage_outcomes.items()
                }
                bundle.metadata["artifact_manifest"] = bundle.artifact_manifest()
                return bundle

        # Build the effective skip set. ``skip_dynamic`` acts as a shorthand
        # for adding ``"dynamic"`` to ``skip_stages`` without mutating the
        # caller-provided config object.
        effective_skip: set[str] = set(config.skip_stages)
        if config.skip_dynamic:
            effective_skip.add("dynamic")

        timing: dict[str, float] = {}
        total_start = time.perf_counter()

        # Execute each stage in order
        for stage in config.stages:
            if stage in effective_skip:
                logger.info("Skipping stage: %s", stage)
                if stage == "dynamic" and config.skip_dynamic:
                    bundle.stage_results[stage] = {
                        "type": "dynamic_enrichment",
                        "skipped": True,
                        "reason": "skip_dynamic=True",
                    }
                bundle.stage_outcomes[stage] = StageOutcome.SKIPPED
                timing[stage] = 0.0
                continue

            if stage not in self.stage_handlers:
                error = f"Unknown stage: {stage}"
                logger.error(error)
                bundle.errors.append(error)
                bundle.stage_outcomes[stage] = StageOutcome.FAILED
                timing[stage] = 0.0
                continue

            try:
                logger.info("Running stage: %s", stage)
                stage_start = time.perf_counter()
                handler = self.stage_handlers[stage]
                result = handler(bundle, config)
                stage_duration = time.perf_counter() - stage_start
                timing[stage] = round(stage_duration * 1000, 3)
                bundle.stage_results[stage] = result
                bundle.stage_outcomes[stage] = self._classify_stage_result(result, config)
                logger.info(
                    "Stage %s completed in %.1fms",
                    stage,
                    timing[stage],
                )
            except Exception as e:
                error = f"Stage {stage} failed: {str(e)}"
                logger.error(error)
                bundle.errors.append(error)
                bundle.stage_outcomes[stage] = StageOutcome.FAILED
                stage_duration = time.perf_counter() - stage_start
                timing[stage] = round(stage_duration * 1000, 3)
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

        total_duration = time.perf_counter() - total_start
        timing["total"] = round(total_duration * 1000, 3)
        bundle.metadata["timing"] = timing
        bundle.metadata["stage_outcomes"] = {
            name: outcome.value for name, outcome in sorted(bundle.stage_outcomes.items())
        }
        bundle.metadata["artifact_manifest"] = bundle.artifact_manifest()

        ran_stages = [s for s in config.stages if s in timing and timing[s] > 0]
        skipped_stages = [s for s in config.stages if s in effective_skip]
        logger.info(
            "Pipeline completed: %d/%d stages ran, %d skipped, %d errors, %.1fms total",
            len(ran_stages),
            len(config.stages),
            len(skipped_stages),
            len(bundle.errors),
            timing["total"],
        )
        return bundle

    @staticmethod
    def _package_version() -> str | None:
        try:
            from cogant import __version__

            return __version__
        except Exception:  # pragma: no cover - defensive import boundary
            return None

    @staticmethod
    def _classify_stage_result(result: Any, config: PipelineConfig) -> StageOutcome:
        """Map a stage result to the explicit release-gate vocabulary."""

        if config.dry_run:
            return StageOutcome.SKIPPED
        if isinstance(result, dict):
            status = str(result.get("status", "")).lower()
            if status in {outcome.value for outcome in StageOutcome}:
                return StageOutcome(status)
            if result.get("passed") is False:
                return StageOutcome.FAILED
            if result.get("unavailable") or result.get("available") is False:
                return StageOutcome.UNAVAILABLE
            if result.get("partial") or result.get("degraded"):
                return StageOutcome.PARTIAL
            if result.get("errors"):
                return StageOutcome.PARTIAL
        return StageOutcome.SUCCESS

    @staticmethod
    def _digest_payload(payload: Any) -> str:
        """Hash a canonical JSON representation of a pipeline contract."""
        from cogant.api.bundle import _json_default

        encoded = json.dumps(
            payload,
            default=_json_default,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(encoded).hexdigest()

    @classmethod
    def _contract_metadata(cls) -> dict[str, Any]:
        """Return serializable parser/rule contract metadata."""
        from cogant.parsers.registry import parser_capability_report

        capabilities = parser_capability_report()
        rule_root = Path(__file__).resolve().parents[1] / "translate" / "rules"
        from cogant.cache.hasher import hash_repo

        rule_digest = hash_repo(rule_root, extensions=[".py"])
        return {
            "parser_capabilities": capabilities,
            "parser_digest": cls._digest_payload(capabilities),
            "rule_digest": rule_digest,
        }

    @classmethod
    def _cache_key(cls, target: str, config: PipelineConfig) -> Any:
        """Build a content/config/parser/rule-addressed cache key."""
        from cogant import __version__ as cogant_version
        from cogant.cache.hasher import hash_repo
        from cogant.cache.store import CacheKey

        repo_path = Path(target).expanduser().resolve()
        content_hash = hash_repo(repo_path)
        contract = cls._contract_metadata()
        config_payload = config.model_dump(mode="json")
        # These values describe this invocation's transport/output context,
        # not the analysis semantics. Excluding them permits a warm cache to
        # be reused when a caller changes only the destination or ref used to
        # discover the delta.
        for ephemeral in (
            "output_dir",
            "cache_dir",
            "incremental_since",
            "verbose",
            "dry_run",
            "layout_output",
            "upstream_gnn_output_dir",
        ):
            config_payload.pop(ephemeral, None)
        return CacheKey(
            repo_path=str(repo_path),
            content_hash=content_hash,
            cogant_version=cogant_version,
            config_digest=cls._digest_payload(config_payload),
            parser_digest=str(contract["parser_digest"]),
            rule_digest=str(contract["rule_digest"]),
        )

    # ------------------------------------------------------------------
    # Incremental-mode helpers
    # ------------------------------------------------------------------

    def _incremental_preflight(self, target: str, bundle: Bundle, config: PipelineConfig) -> str:
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
        from cogant.cache.store import CacheStore
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
            if not any(part in {".git", ".venv", "__pycache__", "node_modules"} for part in p.parts)
        ]
        stats["files_total"] = len(all_py)

        key = self._cache_key(target, config)

        cache_dir = Path(config.cache_dir) if config.cache_dir else None
        store = CacheStore(cache_dir=cache_dir)
        entry = store.get(key)
        if entry is None:
            # A changed content digest should still be able to find the
            # previous snapshot, but only when all other contracts match.
            entry = store.get_latest(
                repo_path=key.repo_path,
                cogant_version=key.cogant_version,
                config_digest=key.config_digest,
                parser_digest=key.parser_digest,
                rule_digest=key.rule_digest,
            )

        changes = ingester.source_changes_since(config.incremental_since)
        changed = [
            change.path
            for change in changes
            if change.change_type != "D" and change.path.exists()
        ]
        stats["files_reparsed"] = len(changed)
        stats["files_changed"] = len(changes)

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
        for name, outcome in (cached.get("stage_outcomes") or {}).items():
            try:
                bundle.stage_outcomes[name] = StageOutcome(outcome)
            except ValueError:
                bundle.stage_outcomes[name] = StageOutcome.PARTIAL
        stats["cache_hit"] = True

        if not changes and entry.key.content_hash == key.content_hash:
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
            "change_records": [
                {"path": str(change.path), "change_type": change.change_type}
                for change in changes
            ],
        }
        stats["reason"] = f"{len(changes)} source change(s) detected"
        return "partial"

    def _incremental_cache_save(self, target: str, bundle: Bundle, config: PipelineConfig) -> None:
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
        import json as _json

        from cogant.api.bundle import _json_default
        from cogant.cache.store import CacheStore

        key = self._cache_key(target, config)
        cache_dir = Path(config.cache_dir) if config.cache_dir else None
        store = CacheStore(cache_dir=cache_dir)

        safe_results = _json.loads(_json.dumps(bundle.stage_results, default=_json_default))
        safe_errors = list(bundle.errors)
        store.put(
            key,
            {
                "stage_results": safe_results,
                "errors": safe_errors,
                "stage_outcomes": {
                    name: outcome.value for name, outcome in bundle.stage_outcomes.items()
                },
            },
        )

    def _stage_ingest(self, bundle: Bundle, config: PipelineConfig) -> dict[str, Any]:
        """Ingest: Load and parse target codebase."""
        if config.dry_run:
            return {"type": "ingest", "dry_run": True, "target": bundle.target}
        return orchestration.run_ingest(bundle.target, bundle)

    def _stage_static(self, bundle: Bundle, config: PipelineConfig) -> dict[str, Any]:
        """Static analysis: Extract AST, types, symbols."""
        if config.dry_run:
            return {"type": "static_analysis", "dry_run": True}
        return orchestration.run_static(bundle)

    def _stage_normalize(self, bundle: Bundle, config: PipelineConfig) -> dict[str, Any]:
        """Normalize: Unify representations."""
        if config.dry_run:
            return {"type": "normalized", "dry_run": True}
        return orchestration.run_normalize(bundle)

    def _stage_graph(self, bundle: Bundle, config: PipelineConfig) -> dict[str, Any]:
        """Graph: Build program dependency graph."""
        if config.dry_run:
            return {"type": "program_graph", "dry_run": True}
        return orchestration.run_graph(bundle, bundle.target)

    def _stage_dynamic(self, bundle: Bundle, config: PipelineConfig) -> dict[str, Any]:
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
                        logger.info("Dynamic stage auto-detected coverage at %s", coverage_path)
            except Exception:  # noqa: BLE001
                logger.debug("Coverage auto-detection skipped", exc_info=True)

        if coverage_path is None and trace_path is None:
            logger.info("Dynamic stage: no coverage or trace data found; skipping enrichment")
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

    def _stage_translate(self, bundle: Bundle, config: PipelineConfig) -> dict[str, Any]:
        """Translate: Convert to GNN representation."""
        if config.dry_run:
            return {"type": "gnn_model", "dry_run": True}
        return orchestration.run_translate(bundle, min_confidence=config.min_confidence)

    def _stage_statespace(self, bundle: Bundle, config: PipelineConfig) -> dict[str, Any]:
        """Statespace: Compile semantic state space."""
        if config.dry_run:
            return {"type": "state_space_model", "dry_run": True}
        return orchestration.run_statespace(bundle, bundle.target)

    def _stage_process(self, bundle: Bundle, config: PipelineConfig) -> dict[str, Any]:
        """Process: Extract execution model."""
        if config.dry_run:
            return {"type": "process_model", "dry_run": True}
        return orchestration.run_process(bundle, bundle.target)

    def _stage_export(self, bundle: Bundle, config: PipelineConfig) -> dict[str, Any]:
        """Export: Write all artifacts to disk."""
        if config.dry_run:
            return {"type": "export", "dry_run": True, "output_dir": config.output_dir}
        return orchestration.run_export(
            bundle,
            config.output_dir,
            render_visualizations=config.render_visualizations,
        )

    def _stage_validate(self, bundle: Bundle, config: PipelineConfig) -> dict[str, Any]:
        """Validate: Run validation checks."""
        if config.dry_run:
            return {"type": "validation", "dry_run": True, "passed": True}
        upstream_pipeline_dir: Path | None = None
        if config.upstream_gnn_pipeline:
            upstream_pipeline_dir = (
                Path(config.upstream_gnn_output_dir).resolve()
                if config.upstream_gnn_output_dir
                else Path(config.output_dir).resolve() / "upstream_pipeline"
            )
        return orchestration.run_validate(
            bundle,
            upstream_gnn=config.upstream_gnn_validation,
            upstream_pipeline=config.upstream_gnn_pipeline,
            upstream_pipeline_output_dir=upstream_pipeline_dir,
            upstream_pipeline_only_steps=config.upstream_gnn_only_steps,
            upstream_pipeline_skip_steps=list(config.upstream_gnn_skip_steps),
            upstream_pipeline_frameworks=config.upstream_gnn_frameworks,
            upstream_pipeline_llm_model=config.upstream_gnn_llm_model,
        )
