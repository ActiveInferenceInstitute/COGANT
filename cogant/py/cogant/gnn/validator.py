"""
GNN validator — validates a GNN package against the GNN specification.

Checks:
- All required files present
- JSON valid and well-formed
- Markdown has all canonical sections in correct order
- State space well-formed and connected
- No orphan references
- Checksums match
- Provenance complete
"""

import hashlib
import json
import logging
import math
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class GNNCapabilityError(RuntimeError):
    """Raised when an explicitly requested validator capability is unavailable."""

    code = "CAPABILITY_UNAVAILABLE"


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def _upstream_enabled_by_env() -> bool:
    """Return whether the optional upstream validator was explicitly enabled."""
    return _env_truthy("COGANT_ENABLE_UPSTREAM_GNN")


def _resolve_upstream_flag(explicit: bool | None) -> bool:
    """Resolve whether to run upstream ``validate_gnn`` on ``model.gnn.md``.

    * ``explicit is not None`` — caller/pipeline/CLI choice wins.
    * ``None`` — use COGANT's self-contained validator.  The optional upstream
      validator runs only when :envvar:`COGANT_ENABLE_UPSTREAM_GNN` is truthy.
    """
    if explicit is not None:
        return explicit
    return _upstream_enabled_by_env()


class ValidationResult:
    """Result of a GNN package validation."""

    def __init__(
        self,
        valid: bool = False,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        score: float = 0.0,
        advisories: list[str] | None = None,
        capabilities: dict[str, Any] | None = None,
        artifact_digests: dict[str, str] | None = None,
        dimensions: dict[str, Any] | None = None,
    ):
        """
        Initialize validation result.

        Args:
            valid: Whether package is valid.
            errors: List of error messages.
            warnings: List of warning messages.
            score: Validation score 0-100.
        """
        self.valid = valid
        self.errors: list[str] = errors or []
        self.advisories: list[str] = list(advisories if advisories is not None else warnings or [])
        self.score = score
        self.details: dict[str, Any] = {}
        self.section_scores: dict[str, float] = {}
        self.capabilities: dict[str, Any] = dict(capabilities or {})
        self.artifact_digests: dict[str, str] = dict(artifact_digests or {})
        self.dimensions: dict[str, Any] = dict(dimensions or {})

    @property
    def warnings(self) -> list[str]:
        """Backward-compatible view of non-fatal validation advisories."""

        return self.advisories

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "score": self.score,
            "errors": self.errors,
            "warnings": self.advisories,
            "advisories": self.advisories,
            "capabilities": self.capabilities,
            "artifact_digests": self.artifact_digests,
            "dimensions": self.dimensions,
            "details": self.details,
            "section_scores": self.section_scores,
        }

    def to_markdown(self) -> str:
        """Generate a human-readable markdown report.

        Returns:
            A markdown string containing a formatted report of the
            validation result, including scores, errors, warnings,
            and section breakdowns.
        """
        lines: list[str] = []

        # Header
        status = "✓ VALID" if self.valid else "✗ INVALID"
        lines.append("# GNN Validation Report\n")
        lines.append(f"**Status**: {status}\n")
        lines.append(f"**Overall Score**: {self.score:.1f}/100\n")

        # Section scores
        if self.section_scores:
            lines.append("## Section Scores\n")
            for section, score in sorted(self.section_scores.items()):
                bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
                lines.append(f"- **{section}**: {score:.1f}/100 [{bar}]")
            lines.append("")

        # Errors
        if self.errors:
            lines.append("## Errors\n")
            for err in self.errors:
                lines.append(f"- ❌ {err}")
            lines.append("")

        # Warnings
        if self.warnings:
            lines.append("## Warnings\n")
            for warn in self.warnings:
                lines.append(f"- ⚠ {warn}")
            lines.append("")

        # Details
        if self.details:
            lines.append("## Details\n")
            for key, val in self.details.items():
                if isinstance(val, dict):
                    lines.append(f"### {key}")
                    for k, v in val.items():
                        lines.append(f"- {k}: {v}")
                else:
                    lines.append(f"- **{key}**: {val}")
            lines.append("")

        return "\n".join(lines)

    def badge_svg(self) -> str:
        """Generate SVG badge."""
        status = "VALID" if self.valid else "INVALID"
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="120" height="20">
  <rect width="120" height="20" fill="#333"/>
  <text x="10" y="15" fill="white" font-size="12" font-family="Arial">
    GNN {status} ({self.score:.0f}%)
  </text>
</svg>"""


class GNNValidator:
    """Validates a GNN package against the GNN specification."""

    REQUIRED_FILES = [
        "manifest.json",
        "model.gnn.md",
        "model.gnn.json",
        "state_space.json",
        "observations.json",
        "actions.json",
        "transitions.json",
        "preferences.json",
        "factors.json",
        "provenance.json",
        "ontology.json",
        "actions_policies.json",
        "connections.json",
        "preferences_constraints.json",
        "markov_blanket.json",
        "markov_network.json",
    ]

    CANONICAL_SECTIONS = [
        "model_metadata",
        "repository_metadata",
        "source_coverage",
        "state_space",
        "observation_modalities",
        "actions_policies",
        "program_graph_connections",
        "factors",
        "transition_structure",
        "likelihood_structure",
        "preferences_constraints",
        "time_settings",
        "parameterization",
        "ontology_mapping",
        "markov_blanket",
        "provenance",
        "confidence",
        "rendering_hints",
        "validation_notes",
    ]

    # Upstream GNN 2.0.0 headers. COGANT emits these at the top of
    # ``model.gnn.md`` for upstream validation.
    UPSTREAM_SECTIONS = [
        "GNNSection",
        "GNNVersionAndFlags",
        "ModelName",
        "StateSpaceBlock",
        "Connections",
        "InitialParameterization",
        "Equations",
        "Time",
        "ActInfOntologyAnnotation",
        "ModelParameters",
        "Footer",
        "Signature",
    ]

    def __init__(self) -> None:
        """Initialize validator."""
        # ``validate_package`` is the single entry point and always
        # reassigns these before they're read. Type-annotating as
        # non-optional avoids a cascade of union-attr noise in the
        # private ``_check_*`` helpers below without hiding any real
        # null-dereference bug (the helpers are never called first).
        self.result: ValidationResult = ValidationResult()
        self.package_dir: Path = Path(".")
        self._upstream_gnn: bool = False

    def validate_package(
        self,
        package_dir: str,
        *,
        upstream_gnn: bool | None = None,
    ) -> ValidationResult:
        """
        Validate a GNN package.

        Args:
            package_dir: Path to the package directory.
            upstream_gnn: When True, run the Active Inference Institute
                ``generalized-notation-notation`` validator (``src.gnn``) on
                ``model.gnn.md``. When ``None``, upstream runs by default unless
                :envvar:`COGANT_DISABLE_UPSTREAM_GNN` is set.

        Returns:
            ValidationResult object.
        """
        self.package_dir = Path(package_dir)
        self.result = ValidationResult()
        self._upstream_gnn = _resolve_upstream_flag(upstream_gnn)
        self.result.capabilities["upstream_gnn"] = {
            "requested": self._upstream_gnn,
            "available": False,
        }
        try:
            from cogant.parsers.registry import parser_capabilities

            self.result.capabilities["parsers"] = {
                language: capability.__dict__ for language, capability in parser_capabilities().items()
            }
        except Exception as exc:
            self.result.capabilities["parsers"] = {"error": str(exc)}

        logger.info(
            "Validating GNN package: %s (upstream_gnn=%s)",
            self.package_dir,
            self._upstream_gnn,
        )

        # Check 1: Directory exists
        if not self.package_dir.exists():
            self.result.errors.append(f"Package directory not found: {self.package_dir}")
            self.result.valid = False
            self.result.score = 0.0
            return self.result

        if not self.package_dir.is_dir():
            self.result.errors.append(f"Package path is not a directory: {self.package_dir}")
            self.result.score = 0.0
            return self.result

        self.result.artifact_digests = self._artifact_digests()

        # Check 2: Required files present
        self._check_required_files()

        # Check 3: Manifest valid
        manifest = self._check_manifest()

        # Check 4: JSON files valid
        self._check_json_files()

        # Check 5: A/B/C/D matrix block valid
        self._check_matrices()

        # Check 6: Markdown valid
        self._check_markdown()

        # Check 7: State space valid
        self._check_state_space()

        # Check 8: Provenance valid
        self._check_provenance()

        # Check 9: Checksums match
        if manifest:
            self._check_checksums(manifest)

        # Compute final score and validity
        self._compute_final_score()

        logger.info(
            "Validation complete: %s (score=%.1f%%, %d errors, %d warnings)",
            self.result.valid,
            self.result.score,
            len(self.result.errors),
            len(self.result.warnings),
        )
        return self.result

    def validate_markdown(self, markdown: str) -> list[str]:
        """
        Validate GNN markdown structure.

        Checks both the COGANT-extended canonical sections
        (``## Model Metadata``, ``## Source Coverage``, ``## Markov
        Blanket``, etc.) and the upstream GNN 2.0.0 required headers
        (``## GNNSection``, ``## StateSpaceBlock``, ``## Connections``,
        ``## InitialParameterization``, ``## Equations``, ``## Time``,
        ``## ActInfOntologyAnnotation``, ``## ModelParameters``, etc.). Upstream section
        checks are ordered: they must appear in the spec-mandated
        order at the TOP of the file.

        Args:
            markdown: Markdown content.

        Returns:
            List of errors (empty if valid).
        """
        errors: list[str] = []
        lowered = markdown.lower()

        # 1) COGANT-extended canonical sections (case-insensitive presence check).
        for section in self.CANONICAL_SECTIONS:
            section_header = f"## {section.replace('_', ' ').title()}"
            if section_header.lower() not in lowered:
                errors.append(f"Missing canonical section: {section}")

        # 2) Upstream GNN 2.0.0 required sections — each must be present.
        missing_upstream: list[str] = []
        upstream_offsets: list[tuple[str, int]] = []
        for section in self.UPSTREAM_SECTIONS:
            marker = f"## {section}"
            idx = markdown.find(marker)
            if idx < 0:
                missing_upstream.append(section)
            else:
                upstream_offsets.append((section, idx))
        for section in missing_upstream:
            errors.append(f"Missing upstream GNN 2.0.0 section: {section}")

        # 3) Upstream sections must appear in canonical order.
        if not missing_upstream and upstream_offsets:
            expected_order = list(self.UPSTREAM_SECTIONS)
            found_order = [section for section, _ in sorted(upstream_offsets, key=lambda x: x[1])]
            if expected_order != found_order:
                errors.append(
                    "Upstream GNN 2.0.0 sections out of canonical order: "
                    f"found {found_order}, expected {expected_order}"
                )

        return errors

    def validate_state_space(self, state_space_json: dict[str, Any]) -> list[str]:
        """
        Validate state space structure.

        Args:
            state_space_json: State space JSON.

        Returns:
            List of errors (empty if valid).
        """
        if not isinstance(state_space_json, dict):
            return ["State-space root must be a JSON object"]
        errors: list[str] = []

        # Check required keys
        required_keys = ["variables", "observations", "actions", "transitions"]
        for key in required_keys:
            if key not in state_space_json:
                errors.append(f"Missing state space key: {key}")

        # Check variables are well-formed
        variables = state_space_json.get("variables", [])
        if not isinstance(variables, list):
            errors.append("Variables must be a list")
        elif any(not isinstance(item, dict) for item in variables):
            errors.append("Variables entries must be objects")

        # Check observations are well-formed
        observations = state_space_json.get("observations", [])
        if not isinstance(observations, list):
            errors.append("Observations must be a list")
        elif any(not isinstance(item, dict) for item in observations):
            errors.append("Observations entries must be objects")

        # Check actions are well-formed
        actions = state_space_json.get("actions", [])
        if not isinstance(actions, list):
            errors.append("Actions must be a list")
        elif any(not isinstance(item, dict) for item in actions):
            errors.append("Actions entries must be objects")

        # Check transitions are well-formed
        transitions = state_space_json.get("transitions", {})
        if not isinstance(transitions, dict):
            errors.append("Transitions must be a dict")
        else:
            if not isinstance(transitions.get("transition_count"), int):
                errors.append("Transitions must declare an integer transition_count")
            if not isinstance(transitions.get("time_regime"), str) or not transitions.get("time_regime"):
                errors.append("Transitions must declare a non-empty time_regime")

        metadata = state_space_json.get("metadata")
        if metadata is not None:
            if not isinstance(metadata, dict):
                errors.append("State-space metadata must be an object")
            else:
                for key, values in (
                    ("num_variables", variables),
                    ("num_observations", observations),
                    ("num_actions", actions),
                ):
                    declared = metadata.get(key)
                    if isinstance(values, list) and declared != len(values):
                        errors.append(f"State-space metadata {key} does not match emitted entries")

        return errors

    def validate_matrices(self, matrices_json: dict[str, Any]) -> list[str]:
        """Validate the AII Active Inference matrix block.

        Checks presence and shape of the A/B/C/D matrices emitted by
        :class:`cogant.gnn.matrices.GNNMatrices`. The matrices must
        satisfy:

        * A: shape ``[n_obs x n_states]``, columns sum to 1.0.
        * B: shape ``[n_states x n_states x n_actions]``.
        * C: length equal to ``n_obs``.
        * D: length equal to ``n_states``, sums to 1.0.

        Args:
            matrices_json: Dict of the form
                ``{"A": ..., "B": ..., "C": ..., "D": ...,
                "dimensions": {"n_states", "n_obs", "n_actions"}}``.

        Returns:
            List of errors (empty if matrices are well-formed).
        """
        errors: list[str] = []

        for key in ("A", "B", "C", "D"):
            if key not in matrices_json:
                errors.append(f"Missing matrix: {key}")

        A = matrices_json.get("A", [])
        B = matrices_json.get("B", [])
        C = matrices_json.get("C", [])
        D = matrices_json.get("D", [])

        if not isinstance(A, list):
            errors.append("A must be a list")
            A = []
        if not isinstance(B, list):
            errors.append("B must be a list")
            B = []
        if not isinstance(C, list):
            errors.append("C must be a list")
            C = []
        if not isinstance(D, list):
            errors.append("D must be a list")
            D = []
        if any(not isinstance(row, list) for row in A):
            errors.append("A rows must be lists")
            A = [row for row in A if isinstance(row, list)]
        if any(not isinstance(row, list) for row in B):
            errors.append("B rows must be lists")
            B = [row for row in B if isinstance(row, list)]
        if any(not isinstance(cell, list) for row in B for cell in row):
            errors.append("B cells must be lists")
            B = [
                [cell for cell in row if isinstance(cell, list)]
                for row in B
            ]

        dims = matrices_json.get("dimensions")
        if not isinstance(dims, dict):
            if dims is None:
                errors.append("dimensions must be declared as an object")
            else:
                errors.append("dimensions must be an object")
            dims = {}

        inferred_states = len(D) or (len(A[0]) if A and A[0] else 0)
        inferred_obs = len(A) or len(C)
        inferred_actions = len(B[0][0]) if B and B[0] and B[0][0] else 0

        def dimension(name: str, inferred: int) -> int:
            if name not in dims:
                return inferred
            value = dims[name]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                errors.append(f"dimensions.{name} must be a non-negative integer")
                return inferred
            return value

        n_states = dimension("n_states", inferred_states)
        n_obs = dimension("n_obs", inferred_obs)
        n_actions = dimension("n_actions", inferred_actions)

        shapes = matrices_json.get("shapes")
        if not isinstance(shapes, dict):
            errors.append("shapes must be declared as an object")
        else:
            expected_shapes = {
                "A": [n_obs, n_states],
                "B": [n_states, n_states, n_actions],
                "C": [n_obs],
                "D": [n_states],
            }
            for key, expected in expected_shapes.items():
                actual_shape = shapes.get(key)
                if actual_shape != expected:
                    errors.append(f"declared shape for {key} does not match dimensions")

        for name, value, actual in (
            ("n_states", n_states, len(D)),
            ("n_obs", n_obs, len(C)),
        ):
            if name in dims and actual != value:
                errors.append(f"declared {name}={value} does not match {name} vector length {actual}")
        if "n_states" in dims and A and any(len(row) != n_states for row in A):
            errors.append(f"declared n_states={n_states} does not match A column count")
        if "n_obs" in dims and A and len(A) != n_obs:
            errors.append(f"declared n_obs={n_obs} does not match A row count")
        if "n_actions" in dims and B and B[0] and any(
            len(cell) != n_actions for row in B for cell in row
        ):
            errors.append(f"declared n_actions={n_actions} does not match B depth")

        # A: rows == n_obs, cols == n_states, columns sum to 1 (column-stochastic).
        if n_obs > 0 and n_states > 0:
            if len(A) != n_obs:
                errors.append(f"A row count {len(A)} != n_obs {n_obs}")
            elif A and any(len(row) != n_states for row in A):
                errors.append(f"A column count mismatch; expected {n_states}")
            else:
                # Tolerance 1e-6 — stability constant. A-matrix encodes
                # P(o|s) and is column-stochastic (AII/pymdp convention):
                # for each fixed hidden state s (a column), the distribution
                # over observation outcomes sums to 1. float64 accumulation
                # introduces ~n_obs * eps drift; 1e-6 leaves ~8 orders of
                # magnitude headroom and matches the pymdp / scipy convention
                # for stochastic-matrix normalization checks.
                if any(
                    not isinstance(A[i][j], (int, float))
                    or not math.isfinite(float(A[i][j]))
                    or A[i][j] < -1e-9
                    for i in range(len(A))
                    for j in range(n_states)
                ):
                    errors.append("A contains negative probabilities")
                for j in range(n_states):
                    col_sum = sum(A[i][j] for i in range(len(A)))
                    if abs(col_sum - 1.0) > 1e-6:
                        errors.append(f"A column {j} does not sum to 1 (sum={col_sum:.6f})")

        elif A:
            errors.append("A must be empty when observations or hidden states are zero")

        # B: shape n_states x n_states x n_actions.
        if n_states > 0:
            if n_actions == 0 and not B:
                pass
            elif len(B) != n_states:
                errors.append(f"B first dim {len(B)} != n_states {n_states}")
            elif any(len(row) != n_states for row in B):
                errors.append(f"B second dim mismatch; expected {n_states}")
            elif any(len(cell) != n_actions for row in B for cell in row):
                errors.append(f"B third dim mismatch; expected {n_actions}")
            else:
                if any(
                    not isinstance(B[i][j][k], (int, float))
                    or not math.isfinite(float(B[i][j][k]))
                    or B[i][j][k] < -1e-9
                    for i in range(n_states)
                    for j in range(n_states)
                    for k in range(n_actions)
                ):
                    errors.append("B contains negative probabilities")
                for k in range(n_actions):
                    for j in range(n_states):
                        col_sum = sum(B[i][j][k] for i in range(n_states))
                        if abs(col_sum - 1.0) > 1e-6:
                            errors.append(
                                f"B action {k} column {j} does not sum to 1 "
                                f"(sum={col_sum:.6f})"
                            )

        elif B:
            errors.append("B must be empty when hidden states are zero")

        # C: length n_obs.
        if len(C) != n_obs:
            errors.append(f"C length {len(C)} != n_obs {n_obs}")
        elif any(not isinstance(value, (int, float)) or not math.isfinite(float(value)) for value in C):
            errors.append("C contains non-finite values")

        # D: length n_states, sums to 1.
        if len(D) != n_states:
            errors.append(f"D length {len(D)} != n_states {n_states}")
        elif n_states > 0:
            if any(
                not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or value < -1e-9
                for value in D
            ):
                errors.append("D contains negative probabilities")
            elif D and abs(sum(D) - 1.0) > 1e-6:
                # Tolerance 1e-6 — stability constant, same rationale as
                # A-column tolerance above (pymdp/scipy convention for
                # probability-simplex sum checks; ~8 orders of magnitude
                # headroom over float64 accumulation drift).
                errors.append(f"D does not sum to 1 (sum={sum(D):.6f})")

        return errors

    def _effective_matrix_dimensions(self, matrices_json: dict[str, Any]) -> dict[str, int]:
        """Return matrix dimensions declared in, or inferred from, A/B/C/D."""
        B = matrices_json.get("B", [])
        C = matrices_json.get("C", [])
        D = matrices_json.get("D", [])
        dims = matrices_json.get("dimensions")
        dims = dims if isinstance(dims, dict) else {}
        n_states = dims.get("n_states", len(D) if isinstance(D, list) else 0)
        n_obs = dims.get("n_obs", len(C) if isinstance(C, list) else 0)
        n_actions = dims.get(
            "n_actions",
            len(B[0][0]) if isinstance(B, list) and B and B[0] and B[0][0] else 0,
        )
        if not all(isinstance(value, int) and not isinstance(value, bool) for value in (n_states, n_obs, n_actions)):
            return {"n_states": 0, "n_obs": 0, "n_actions": 0}
        return {"n_states": n_states, "n_obs": n_obs, "n_actions": n_actions}

    def _state_space_dimensions(self) -> dict[str, int] | None:
        """Return compiled state-space dimensions from ``state_space.json``."""
        state_space_path = self.package_dir / "state_space.json"
        if not state_space_path.exists():
            return None
        try:
            with open(state_space_path) as f:
                loaded = json.load(f)
        except Exception as exc:
            self.result.warnings.append(
                f"Matrix validation skipped state-space alignment: {exc}"
            )
            return None
        state_space = loaded if isinstance(loaded, dict) else {}

        def _count(key: str) -> int:
            value = state_space.get(key)
            if isinstance(value, (list, dict)):
                return len(value)
            return 0

        return {
            "n_states": _count("variables"),
            "n_obs": _count("observations"),
            "n_actions": _count("actions"),
        }

    def _matrix_state_space_alignment_errors(
        self,
        matrix_dimensions: dict[str, int],
        state_space_dimensions: dict[str, int] | None,
    ) -> tuple[list[str], dict[str, Any]]:
        """Compare matrix dimensions with compiled state-space dimensions."""
        if state_space_dimensions is None:
            return [], {}

        alignment: dict[str, Any] = {
            "matrix_dimensions": matrix_dimensions,
            "state_space_dimensions": state_space_dimensions,
        }
        errors: list[str] = []
        comparisons = (
            ("n_states", "hidden-state"),
            ("n_obs", "observation"),
            ("n_actions", "action"),
        )
        for key, label in comparisons:
            matrix_value = matrix_dimensions.get(key, 0)
            state_value = state_space_dimensions.get(key, 0)
            match = matrix_value == state_value
            alignment[f"{key}_match"] = match
            if not match:
                errors.append(
                    f"{label} dimension mismatch: matrix {key}={matrix_value} "
                    f"!= state_space {key}={state_value}"
                )
        return errors, alignment

    def _matrix_degenerate_warnings(
        self,
        matrices: dict[str, Any],
        matrix_dimensions: dict[str, int],
        state_space_dimensions: dict[str, int] | None,
    ) -> list[str]:
        """Return non-public warnings for valid but degenerate matrix exports."""
        warnings: list[str] = []
        if state_space_dimensions is None:
            return warnings
        if (
            state_space_dimensions.get("n_obs") == 0
            and matrix_dimensions.get("n_obs") == 0
            and not matrices.get("A")
            and not matrices.get("C")
        ):
            warnings.append(
                "Matrix validation: degenerate model has no observation modalities; "
                "A/C are empty and not publication-ready evidence"
            )
        if (
            state_space_dimensions.get("n_states") == 0
            and matrix_dimensions.get("n_states") == 0
            and (not matrices.get("A") or not matrices.get("B") or not matrices.get("D"))
        ):
            warnings.append(
                "Matrix validation: degenerate model has no hidden-state variables; "
                "A/B/D are empty and not publication-ready evidence"
            )
        return warnings

    def validate_provenance(self, provenance_json: dict[str, Any]) -> list[str]:
        """
        Validate provenance structure.

        Args:
            provenance_json: Provenance JSON.

        Returns:
            List of errors (empty if valid).
        """
        if not isinstance(provenance_json, dict):
            return ["Provenance root must be a JSON object"]
        errors: list[str] = []

        # Check required keys
        required_keys = ["timestamp", "sources"]
        for key in required_keys:
            if key not in provenance_json:
                errors.append(f"Missing provenance key: {key}")

        # Check sources
        sources = provenance_json.get("sources", {})
        if not isinstance(sources, dict):
            errors.append("Provenance sources must be a dict")

        return errors

    def generate_validation_badge(self, result: ValidationResult) -> str:
        """
        Generate SVG validation badge.

        Args:
            result: Validation result.

        Returns:
            SVG string.
        """
        return result.badge_svg()

    # Private validation methods

    def _check_required_files(self) -> None:
        """Check that all required files are present."""
        for filename in self.REQUIRED_FILES:
            filepath = self.package_dir / filename
            if not filepath.exists():
                self.result.errors.append(f"Missing required file: {filename}")
            else:
                logger.debug(f"  ✓ Found {filename}")

    def _check_manifest(self) -> dict[str, Any] | None:
        """Check manifest validity and return parsed manifest."""
        manifest_path = self.package_dir / "manifest.json"
        if not manifest_path.exists():
            self.result.errors.append("Missing manifest.json")
            return None

        try:
            with open(manifest_path) as f:
                loaded = json.load(f)
            if not isinstance(loaded, dict):
                self.result.errors.append("manifest.json must contain a JSON object")
                return None
            manifest = dict(loaded)
            logger.debug("  ✓ manifest.json is valid JSON")
            self.result.details["manifest"] = manifest
            return manifest
        except json.JSONDecodeError as e:
            self.result.errors.append(f"Invalid JSON in manifest.json: {e}")
            return None
        except Exception as e:
            self.result.errors.append(f"Failed to read manifest.json: {e}")
            return None

    def _check_json_files(self) -> None:
        """Check that all JSON files are valid."""
        json_files = [
            filename
            for filename in self.REQUIRED_FILES
            if filename.endswith(".json") and filename != "manifest.json"
        ]

        for filename in json_files:
            filepath = self.package_dir / filename
            if not filepath.exists():
                continue

            try:
                with open(filepath) as f:
                    loaded = json.load(f)
                    if not isinstance(loaded, dict):
                        self.result.errors.append(f"JSON root must be an object in {filename}")
                        continue
                logger.debug(f"  ✓ {filename} is valid JSON")
            except json.JSONDecodeError as e:
                self.result.errors.append(f"Invalid JSON in {filename}: {e}")
            except Exception as e:
                self.result.errors.append(f"Failed to read {filename}: {e}")

    def _check_matrices(self) -> None:
        """Validate the exported ``model.gnn.json`` A/B/C/D matrix block."""
        model_path = self.package_dir / "model.gnn.json"
        if not model_path.exists():
            self.result.errors.append("Missing model.gnn.json for matrix validation")
            return

        try:
            with open(model_path) as f:
                loaded = json.load(f)
            model = loaded if isinstance(loaded, dict) else {}
            matrices_raw = model.get("matrices")
            if not isinstance(matrices_raw, dict):
                self.result.errors.append("Missing matrices block in model.gnn.json")
                self.result.details["matrices"] = {
                    "present": False,
                    "validation_errors": ["Missing matrices block in model.gnn.json"],
                }
                return
            matrices = matrices_raw
            errors = self.validate_matrices(matrices)
            matrix_dimensions = self._effective_matrix_dimensions(matrices)
            state_space_dimensions = self._state_space_dimensions()
            alignment_errors, dimension_alignment = self._matrix_state_space_alignment_errors(
                matrix_dimensions,
                state_space_dimensions,
            )
            errors.extend(alignment_errors)
            warnings = self._matrix_degenerate_warnings(
                matrices,
                matrix_dimensions,
                state_space_dimensions,
            )
            self.result.details["matrices"] = {
                "present": True,
                "shapes": matrices.get("shapes") if isinstance(matrices.get("shapes"), dict) else {},
                "dimensions": (
                    matrices.get("dimensions") if isinstance(matrices.get("dimensions"), dict) else {}
                ),
                "effective_dimensions": matrix_dimensions,
                "state_space_dimensions": state_space_dimensions or {},
                "dimension_alignment": dimension_alignment,
                "truncation": matrices.get("truncation"),
                "matrix_keys": [key for key in ("A", "B", "C", "D") if key in matrices],
                "validation_errors": errors,
                "validation_warnings": warnings,
            }
            self.result.dimensions = {
                "matrices": matrix_dimensions,
                "state_space": state_space_dimensions or {},
                "alignment": dimension_alignment,
            }
            if errors:
                self.result.errors.extend(f"Matrix validation: {error}" for error in errors)
            else:
                logger.debug("  ✓ model.gnn.json matrices are well-formed")
            self.result.warnings.extend(warnings)
        except Exception as e:
            self.result.errors.append(f"Failed to validate model.gnn.json matrices: {e}")

    def _check_markdown(self) -> None:
        """Check markdown validity."""
        markdown_path = self.package_dir / "model.gnn.md"
        if not markdown_path.exists():
            self.result.errors.append("Missing model.gnn.md")
            return

        try:
            markdown = markdown_path.read_text(encoding="utf-8")
            errors = self.validate_markdown(markdown)
            if errors:
                self.result.errors.extend(f"Markdown validation: {error}" for error in errors)
            else:
                logger.debug("  ✓ model.gnn.md has all canonical sections")

            if getattr(self, "_upstream_gnn", False):
                from cogant.gnn.upstream_bridge import run_upstream_validate_gnn

                up = run_upstream_validate_gnn(markdown)
                self.result.details["upstream_gnn"] = up.to_dict()
                self.result.capabilities["upstream_gnn"] = up.to_dict()
                if not up.available:
                    self.result.capabilities["upstream_gnn"] = {
                        **up.to_dict(),
                        "requested": True,
                        "available": False,
                        "error_code": GNNCapabilityError.code,
                    }
                    self.result.errors.append(
                        f"{GNNCapabilityError.code}: requested upstream GNN validation is unavailable: "
                        f"{up.skipped_reason or 'install the cogant[upstream] extra'}"
                    )
                elif not up.ok:
                    self.result.errors.extend(f"[upstream GNN] {err}" for err in up.errors)
        except Exception as e:
            self.result.errors.append(f"Failed to read model.gnn.md: {e}")

    def _check_state_space(self) -> None:
        """Check state space validity."""
        state_space_path = self.package_dir / "state_space.json"
        if not state_space_path.exists():
            self.result.errors.append("Missing state_space.json")
            return

        try:
            with open(state_space_path) as f:
                state_space = json.load(f)
            if not isinstance(state_space, dict):
                self.result.errors.append("State-space validation: state_space.json root must be an object")
                return
            errors = self.validate_state_space(state_space)
            if errors:
                self.result.errors.extend(f"State-space validation: {error}" for error in errors)
            else:
                logger.debug("  ✓ state_space.json is well-formed")
        except Exception as e:
            self.result.errors.append(f"Failed to validate state_space.json: {e}")

    def _check_provenance(self) -> None:
        """Check provenance validity."""
        provenance_path = self.package_dir / "provenance.json"
        if not provenance_path.exists():
            self.result.errors.append("Missing provenance.json")
            return

        try:
            with open(provenance_path) as f:
                provenance = json.load(f)
            if not isinstance(provenance, dict):
                self.result.errors.append("Provenance validation: provenance.json root must be an object")
                return
            errors = self.validate_provenance(provenance)
            if errors:
                self.result.errors.extend(f"Provenance validation: {error}" for error in errors)
            else:
                logger.debug("  ✓ provenance.json is well-formed")
        except Exception as e:
            self.result.errors.append(f"Failed to validate provenance.json: {e}")

    def _check_checksums(self, manifest: dict[str, Any]) -> None:
        """Check that checksums match."""
        checksums = manifest.get("checksums")
        if not isinstance(checksums, dict) or not checksums:
            self.result.errors.append("Manifest must contain checksums for evidence validation")
            return

        # The manifest owns this table, so including its own digest would be
        # recursive. Every other required artifact must be covered.
        for required in self.REQUIRED_FILES:
            if required == "manifest.json":
                continue
            if required not in checksums:
                self.result.errors.append(f"Manifest is missing checksum for required file: {required}")

        for filename, expected_checksum in checksums.items():
            if not isinstance(filename, str) or not isinstance(expected_checksum, str):
                self.result.errors.append("Manifest checksums must map string filenames to digests")
                continue
            filepath = (self.package_dir / filename).resolve()
            if self.package_dir.resolve() not in filepath.parents:
                self.result.errors.append(f"Checksum path escapes package directory: {filename}")
                continue
            if not filepath.is_file():
                self.result.errors.append(f"Checksum references missing file: {filename}")
                continue

            try:
                if filepath.suffix == ".json":
                    with open(filepath) as f:
                        data = json.load(f)
                    actual = hashlib.sha256(
                        json.dumps(data, sort_keys=True, default=str).encode()
                    ).hexdigest()
                else:
                    actual = hashlib.sha256(filepath.read_bytes()).hexdigest()

                if actual != expected_checksum:
                    message = (
                        f"Checksum mismatch for {filename}: "
                        f"expected {expected_checksum}, got {actual}"
                    )
                    self.result.errors.append(message)
                else:
                    logger.debug(f"  ✓ {filename} checksum matches")
            except Exception as e:
                message = f"Failed to verify checksum for {filename}: {e}"
                self.result.errors.append(message)

    def _artifact_digests(self) -> dict[str, str]:
        """Return raw SHA-256 digests for every regular package artifact."""
        digests: dict[str, str] = {}
        for path in sorted(self.package_dir.rglob("*")):
            if path.is_file() and path.name != "manifest.json":
                digests[str(path.relative_to(self.package_dir))] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
        return digests

    def _compute_final_score(self) -> None:
        """Compute final validation score and validity.

        The score is a human-readable quality signal only. Certification is
        evidence-based: any hard validation error makes the package invalid,
        while advisories remain visible without being converted into a pass.
        """
        # Keep the score monotonic for reports, but never use it to certify a
        # package. One hard error is enough to invalidate evidence.
        max_points = 100  # percentage scale
        points_per_error = 10  # 10 errors → zero score
        points_per_warning = 2  # 5:1 severity ratio vs. errors

        score = max_points
        score -= len(self.result.errors) * points_per_error
        score -= len(self.result.warnings) * points_per_warning
        score = max(0, min(100, score))

        self.result.score = float(score)
        self.result.valid = len(self.result.errors) == 0

        logger.debug(
            f"  Final score: {self.result.score:.1f}% - {'VALID' if self.result.valid else 'INVALID'}"
        )
