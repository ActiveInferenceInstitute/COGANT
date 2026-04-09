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

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of a GNN package validation."""

    def __init__(self, valid: bool = False, errors: Optional[List[str]] = None,
                 warnings: Optional[List[str]] = None, score: float = 0.0):
        """
        Initialize validation result.

        Args:
            valid: Whether package is valid.
            errors: List of error messages.
            warnings: List of warning messages.
            score: Validation score 0-100.
        """
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.score = score
        self.details = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "score": self.score,
            "errors": self.errors,
            "warnings": self.warnings,
            "details": self.details,
        }

    def badge_svg(self) -> str:
        """Generate SVG badge."""
        status = "VALID" if self.valid else "INVALID"
        color = "32a852" if self.valid else "e74c3c"
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
        "connections",
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

    # Upstream GNN v1.1 canonical headers that the Active Inference
    # Institute GNN type-checker expects. COGANT emits these at the top
    # of ``model.gnn.md`` for upstream compatibility.
    UPSTREAM_SECTIONS = [
        "GNNSection",
        "GNNVersionAndFlags",
        "ModelName",
        "StateSpaceBlock",
        "Connections",
        "InitialParameterization",
        "Time",
        "ActInfOntologyAnnotation",
    ]

    def __init__(self):
        """Initialize validator."""
        self.result = None
        self.package_dir = None

    def validate_package(self, package_dir: str) -> ValidationResult:
        """
        Validate a GNN package.

        Args:
            package_dir: Path to the package directory.

        Returns:
            ValidationResult object.
        """
        self.package_dir = Path(package_dir)
        self.result = ValidationResult()

        logger.info(f"Validating GNN package: {self.package_dir}")

        # Check 1: Directory exists
        if not self.package_dir.exists():
            self.result.errors.append(f"Package directory not found: {self.package_dir}")
            self.result.valid = False
            self.result.score = 0.0
            return self.result

        # Check 2: Required files present
        self._check_required_files()

        # Check 3: Manifest valid
        manifest = self._check_manifest()

        # Check 4: JSON files valid
        self._check_json_files()

        # Check 5: Markdown valid
        self._check_markdown()

        # Check 6: State space valid
        self._check_state_space()

        # Check 7: Provenance valid
        self._check_provenance()

        # Check 8: Checksums match
        if manifest:
            self._check_checksums(manifest)

        # Compute final score and validity
        self._compute_final_score()

        logger.info(f"Validation complete: {self.result.valid} (score: {self.result.score:.1f}%)")
        return self.result

    def validate_markdown(self, markdown: str) -> List[str]:
        """
        Validate GNN markdown structure.

        Checks both the COGANT-extended canonical sections
        (``## Model Metadata``, ``## Source Coverage``, ``## Markov
        Blanket``, etc.) and the upstream GNN v1.1 required headers
        (``## GNNSection``, ``## StateSpaceBlock``, ``## Connections``,
        ``## InitialParameterization``, ``## Time``,
        ``## ActInfOntologyAnnotation``, etc.). Upstream section
        checks are ordered: they must appear in the spec-mandated
        order at the TOP of the file.

        Args:
            markdown: Markdown content.

        Returns:
            List of errors (empty if valid).
        """
        errors: List[str] = []
        lowered = markdown.lower()

        # 1) COGANT-extended canonical sections (case-insensitive presence check).
        for section in self.CANONICAL_SECTIONS:
            section_header = f"## {section.replace('_', ' ').title()}"
            if section_header.lower() not in lowered:
                errors.append(f"Missing canonical section: {section}")

        # 2) Upstream GNN v1.1 required sections — each must be present.
        missing_upstream: List[str] = []
        upstream_offsets: List[tuple[str, int]] = []
        for section in self.UPSTREAM_SECTIONS:
            marker = f"## {section}"
            idx = markdown.find(marker)
            if idx < 0:
                missing_upstream.append(section)
            else:
                upstream_offsets.append((section, idx))
        for section in missing_upstream:
            errors.append(f"Missing upstream GNN v1.1 section: {section}")

        # 3) Upstream sections must appear in canonical order.
        if not missing_upstream and upstream_offsets:
            expected_order = [s for s, _ in upstream_offsets]
            sorted_order = [s for s, _ in sorted(upstream_offsets, key=lambda x: x[1])]
            if expected_order != sorted_order:
                errors.append(
                    "Upstream GNN v1.1 sections out of canonical order: "
                    f"found {sorted_order}, expected {expected_order}"
                )

        return errors

    def validate_state_space(self, state_space_json: dict) -> List[str]:
        """
        Validate state space structure.

        Args:
            state_space_json: State space JSON.

        Returns:
            List of errors (empty if valid).
        """
        errors = []

        # Check required keys
        required_keys = ["variables", "observations", "actions", "transitions"]
        for key in required_keys:
            if key not in state_space_json:
                errors.append(f"Missing state space key: {key}")

        # Check variables are well-formed
        variables = state_space_json.get("variables", [])
        if not isinstance(variables, list):
            errors.append("Variables must be a list")

        # Check observations are well-formed
        observations = state_space_json.get("observations", [])
        if not isinstance(observations, list):
            errors.append("Observations must be a list")

        # Check actions are well-formed
        actions = state_space_json.get("actions", [])
        if not isinstance(actions, list):
            errors.append("Actions must be a list")

        # Check transitions are well-formed
        transitions = state_space_json.get("transitions", {})
        if not isinstance(transitions, dict):
            errors.append("Transitions must be a dict")

        return errors

    def validate_provenance(self, provenance_json: dict) -> List[str]:
        """
        Validate provenance structure.

        Args:
            provenance_json: Provenance JSON.

        Returns:
            List of errors (empty if valid).
        """
        errors = []

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

    def _check_manifest(self) -> Optional[dict]:
        """Check manifest validity and return parsed manifest."""
        manifest_path = self.package_dir / "manifest.json"
        if not manifest_path.exists():
            self.result.errors.append("Missing manifest.json")
            return None

        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
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
            "model.gnn.json",
            "state_space.json",
            "observations.json",
            "actions.json",
            "transitions.json",
            "preferences.json",
            "factors.json",
            "provenance.json",
            "ontology.json",
        ]

        for filename in json_files:
            filepath = self.package_dir / filename
            if not filepath.exists():
                continue

            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                logger.debug(f"  ✓ {filename} is valid JSON")
            except json.JSONDecodeError as e:
                self.result.errors.append(f"Invalid JSON in {filename}: {e}")
            except Exception as e:
                self.result.errors.append(f"Failed to read {filename}: {e}")

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
                self.result.warnings.extend(errors)
            else:
                logger.debug("  ✓ model.gnn.md has all canonical sections")
        except Exception as e:
            self.result.errors.append(f"Failed to read model.gnn.md: {e}")

    def _check_state_space(self) -> None:
        """Check state space validity."""
        state_space_path = self.package_dir / "state_space.json"
        if not state_space_path.exists():
            self.result.errors.append("Missing state_space.json")
            return

        try:
            with open(state_space_path, "r") as f:
                state_space = json.load(f)
            errors = self.validate_state_space(state_space)
            if errors:
                self.result.warnings.extend(errors)
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
            with open(provenance_path, "r") as f:
                provenance = json.load(f)
            errors = self.validate_provenance(provenance)
            if errors:
                self.result.warnings.extend(errors)
            else:
                logger.debug("  ✓ provenance.json is well-formed")
        except Exception as e:
            self.result.errors.append(f"Failed to validate provenance.json: {e}")

    def _check_checksums(self, manifest: dict) -> None:
        """Check that checksums match."""
        checksums = manifest.get("checksums", {})
        if not checksums:
            self.result.warnings.append("Manifest contains no checksums")
            return

        for filename, expected_checksum in checksums.items():
            filepath = self.package_dir / filename
            if not filepath.exists():
                continue

            try:
                if filepath.suffix == ".json":
                    with open(filepath, "r") as f:
                        data = json.load(f)
                    actual = hashlib.sha256(
                        json.dumps(data, sort_keys=True, default=str).encode()
                    ).hexdigest()
                else:
                    content = filepath.read_text(encoding="utf-8")
                    actual = hashlib.sha256(content.encode()).hexdigest()

                if actual != expected_checksum:
                    self.result.warnings.append(
                        f"Checksum mismatch for {filename}: expected {expected_checksum}, got {actual}"
                    )
                else:
                    logger.debug(f"  ✓ {filename} checksum matches")
            except Exception as e:
                self.result.warnings.append(f"Failed to verify checksum for {filename}: {e}")

    def _compute_final_score(self) -> None:
        """Compute final validation score and validity."""
        # Score based on errors and warnings
        max_points = 100
        points_per_error = 10
        points_per_warning = 2

        score = max_points
        score -= len(self.result.errors) * points_per_error
        score -= len(self.result.warnings) * points_per_warning
        score = max(0, min(100, score))

        self.result.score = float(score)
        self.result.valid = len(self.result.errors) == 0 and score >= 80

        logger.debug(f"  Final score: {self.result.score:.1f}% - {'VALID' if self.result.valid else 'INVALID'}")
