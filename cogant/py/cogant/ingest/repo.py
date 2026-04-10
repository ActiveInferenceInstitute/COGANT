"""Repository ingestion: clone, read, detect language, and extract metadata."""

import logging
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from cogant.ingest.files import FileEnumerator, FileInfo
from cogant.ingest.manifest import Dependency, ManifestParser

logger = logging.getLogger(__name__)


@dataclass
class RepoMetadata:
    """Metadata about a repository."""

    name: str
    """Repository name."""

    url: str
    """Repository URL (git or local path)."""

    commit_hash: str | None = None
    """Current commit hash."""

    commit_message: str | None = None
    """Current commit message."""

    timestamp: datetime | None = None
    """Timestamp of repository snapshot."""

    author: str | None = None
    """Author of current commit."""

    language: str | None = None
    """Primary language detected."""

    description: str | None = None
    """Repository description."""


@dataclass
class RepoSnapshot:
    """Complete snapshot of a repository at ingestion time."""

    metadata: RepoMetadata
    """Repository metadata."""

    files: list[FileInfo]
    """Source files in repository."""

    dependencies: list[Dependency]
    """Package dependencies."""

    root_path: Path
    """Root path of repository."""


class RepoIngester:
    """Ingest and analyze repositories."""

    def __init__(self, work_dir: Path | None = None):
        """Initialize repository ingester.

        Args:
            work_dir: Working directory for cloning repos. Defaults to /tmp/cogant.
        """
        self.work_dir = Path(work_dir or "/tmp/cogant")
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_parser = ManifestParser()

    def ingest_local(
        self,
        repo_path: Path,
        include_test_files: bool = True,
        compute_checksums: bool = False,
    ) -> RepoSnapshot:
        """Ingest a local repository.

        Args:
            repo_path: Path to local repository.
            include_test_files: Include test files in analysis.
            compute_checksums: Compute file checksums.

        Returns:
            RepoSnapshot with all metadata and files.
        """
        repo_path = Path(repo_path).resolve()

        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        if not repo_path.is_dir():
            raise ValueError(f"Repository path is not a directory: {repo_path}")

        # Extract metadata
        metadata = self._extract_metadata(repo_path)

        # Enumerate files
        enumerator = FileEnumerator(repo_path, respect_gitignore=True)
        files = enumerator.enumerate(
            include_test_files=include_test_files,
            compute_checksums=compute_checksums,
        )

        # Detect primary language
        if files:
            lang_counts = {}
            for f in files:
                if f.language:
                    lang_counts[f.language] = lang_counts.get(f.language, 0) + 1
            if lang_counts:
                primary_lang = max(lang_counts, key=lang_counts.get)
                metadata.language = primary_lang

        # Extract dependencies
        dependencies = self._extract_dependencies(repo_path)

        return RepoSnapshot(
            metadata=metadata,
            files=files,
            dependencies=dependencies,
            root_path=repo_path,
        )

    def ingest_git_remote(
        self,
        url: str,
        branch: str | None = None,
        include_test_files: bool = True,
        compute_checksums: bool = False,
        cleanup: bool = True,
    ) -> RepoSnapshot:
        """Clone and ingest a remote Git repository.

        Args:
            url: Git repository URL.
            branch: Branch to clone (defaults to default branch).
            include_test_files: Include test files in analysis.
            compute_checksums: Compute file checksums.
            cleanup: Remove cloned repo after ingestion.

        Returns:
            RepoSnapshot with all metadata and files.
        """
        # Clone repository
        repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
        repo_path = self.work_dir / repo_name

        # Remove if already exists
        if repo_path.exists():
            try:
                shutil.rmtree(repo_path)
            except Exception as e:
                logger.warning(f"Failed to remove existing repo at {repo_path}: {e}")

        try:
            cmd = ["git", "clone"]
            if branch:
                cmd.extend(["--branch", branch])
            cmd.extend([url, str(repo_path)])

            logger.info(f"Cloning repository: {url}")
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"Failed to clone repository: {result.stderr}"
                )

        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Clone operation timed out for {url}") from exc
        except Exception as e:
            raise RuntimeError(f"Failed to clone repository {url}: {e}") from e

        try:
            # Ingest the cloned repository
            snapshot = self.ingest_local(
                repo_path,
                include_test_files=include_test_files,
                compute_checksums=compute_checksums,
            )

            # Update metadata with original URL
            snapshot.metadata.url = url

            return snapshot

        finally:
            if cleanup:
                try:
                    shutil.rmtree(repo_path)
                    logger.info(f"Cleaned up cloned repository at {repo_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup repository: {e}")

    def _extract_metadata(self, repo_path: Path) -> RepoMetadata:
        """Extract git metadata from repository.

        Args:
            repo_path: Path to repository.

        Returns:
            RepoMetadata with extracted information.
        """
        repo_name = repo_path.name
        metadata = RepoMetadata(
            name=repo_name,
            url=str(repo_path),
            timestamp=datetime.now(UTC),
        )

        # Try to extract git information
        try:
            # Get current commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                metadata.commit_hash = result.stdout.strip()

            # Get commit message
            result = subprocess.run(
                ["git", "log", "-1", "--pretty=%B"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                metadata.commit_message = result.stdout.strip()

            # Get author
            result = subprocess.run(
                ["git", "log", "-1", "--pretty=%an"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                metadata.author = result.stdout.strip()

        except Exception as e:
            logger.debug(f"Could not extract git metadata: {e}")

        return metadata

    def _extract_dependencies(self, repo_path: Path) -> list[Dependency]:
        """Extract dependencies from manifest files.

        Args:
            repo_path: Path to repository.

        Returns:
            List of dependencies found in manifests.
        """
        all_deps = []

        # Check Python manifests
        setup_py = repo_path / "setup.py"
        if setup_py.exists():
            _, deps = self.manifest_parser.parse_setup_py(setup_py)
            all_deps.extend(deps)

        pyproject_toml = repo_path / "pyproject.toml"
        if pyproject_toml.exists():
            _, deps = self.manifest_parser.parse_pyproject_toml(pyproject_toml)
            all_deps.extend(deps)

        requirements_txt = repo_path / "requirements.txt"
        if requirements_txt.exists():
            deps = self.manifest_parser.parse_requirements_txt(requirements_txt)
            all_deps.extend(deps)

        # Check Node.js manifests
        package_json = repo_path / "package.json"
        if package_json.exists():
            _, deps = self.manifest_parser.parse_package_json(package_json)
            all_deps.extend(deps)

        # Check Rust manifests
        cargo_toml = repo_path / "Cargo.toml"
        if cargo_toml.exists():
            _, deps = self.manifest_parser.parse_cargo_toml(cargo_toml)
            all_deps.extend(deps)

        # Deduplicate dependencies (keep first occurrence)
        seen = set()
        unique_deps = []
        for dep in all_deps:
            key = (dep.name, dep.version, dep.is_dev)
            if key not in seen:
                seen.add(key)
                unique_deps.append(dep)

        return unique_deps
