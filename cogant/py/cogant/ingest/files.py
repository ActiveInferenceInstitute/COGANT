"""File enumeration and filtering for repository ingest."""

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = ["FileInfo", "FileEnumerator", "LANGUAGE_EXTENSIONS", "TEST_PATTERNS", "IGNORE_PATTERNS"]


LANGUAGE_EXTENSIONS = {
    "python": {".py", ".pyx", ".pyi"},
    "javascript": {".js", ".jsx", ".mjs", ".cjs"},
    "typescript": {".ts", ".tsx"},
    "rust": {".rs"},
    "go": {".go"},
    "java": {".java"},
    "cpp": {".cpp", ".cc", ".cxx", ".h", ".hpp", ".c"},
    "csharp": {".cs"},
    "ruby": {".rb"},
    "php": {".php"},
}

TEST_PATTERNS = {
    "test_",
    "_test.py",
    "_spec.py",
    "tests/",
    "test/",
    "__tests__/",
    "spec/",
}

IGNORE_PATTERNS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "target",
    "dist",
    "build",
    ".egg-info",
    ".pytest_cache",
    ".tox",
    ".mypy_cache",
    ".idea",
    ".vscode",
    ".DS_Store",
    "*.egg",
    "*.whl",
}


@dataclass
class FileInfo:
    """Information about a source file."""

    path: Path
    """Absolute path to file."""

    relative_path: str
    """Path relative to repository root."""

    language: str | None
    """Detected programming language."""

    size_bytes: int
    """File size in bytes."""

    is_test: bool = False
    """Whether file is a test file."""

    checksum: str | None = None
    """SHA256 checksum of file contents."""


class FileEnumerator:
    """Enumerate files in a repository with language detection and filtering."""

    def __init__(self, repo_root: Path, respect_gitignore: bool = True):
        """Initialize file enumerator.

        Args:
            repo_root: Root path of repository.
            respect_gitignore: If True, skip files matching .gitignore patterns.
        """
        self.repo_root = Path(repo_root).resolve()
        self.respect_gitignore = respect_gitignore
        self._gitignore_patterns: set[str] | None = None

    def _load_gitignore(self) -> set[str]:
        """Load .gitignore patterns from repository.

        Returns:
            Set of gitignore patterns.
        """
        if self._gitignore_patterns is not None:
            return self._gitignore_patterns

        patterns = set()
        gitignore_path = self.repo_root / ".gitignore"

        if gitignore_path.exists():
            try:
                with open(gitignore_path) as f:
                    for line in f:
                        line = line.strip()
                        # Skip comments and empty lines
                        if line and not line.startswith("#"):
                            patterns.add(line)
            except Exception as e:
                logger.warning(f"Failed to load .gitignore: {e}")

        self._gitignore_patterns = patterns
        return patterns

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored based on patterns.

        Args:
            path: Path to check.

        Returns:
            True if path should be ignored.
        """
        # Always ignore certain patterns
        for ignore_pattern in IGNORE_PATTERNS:
            if ignore_pattern in path.parts or path.name.endswith(ignore_pattern):
                return True

        # Check .gitignore patterns
        if self.respect_gitignore:
            gitignore_patterns = self._load_gitignore()
            relative = path.relative_to(self.repo_root)

            for pattern in gitignore_patterns:
                # Simple wildcard matching
                if "*" in pattern:
                    if pattern.startswith("*"):
                        suffix = pattern[1:]
                        if str(relative).endswith(suffix):
                            return True
                    elif pattern.endswith("*"):
                        prefix = pattern[:-1]
                        if str(relative).startswith(prefix):
                            return True
                else:
                    if pattern in relative.parts or str(relative) == pattern:
                        return True

        return False

    def _detect_language(self, path: Path) -> str | None:
        """Detect programming language from file extension.

        Args:
            path: File path.

        Returns:
            Language name or None if not recognized.
        """
        suffix = path.suffix.lower()

        for lang, extensions in LANGUAGE_EXTENSIONS.items():
            if suffix in extensions:
                return lang

        return None

    def _is_test_file(self, relative_path: str) -> bool:
        """Check if file is likely a test file.

        Args:
            relative_path: Relative path to file.

        Returns:
            True if file appears to be a test.
        """
        for pattern in TEST_PATTERNS:
            if pattern in relative_path:
                return True
        return False

    def _compute_checksum(self, path: Path) -> str:
        """Compute SHA256 checksum of file.

        Args:
            path: File path.

        Returns:
            Hex-encoded SHA256 hash.
        """
        try:
            sha256_hash = hashlib.sha256()
            with open(path, "rb") as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to compute checksum for {path}: {e}")
            return ""

    def enumerate(
        self, include_test_files: bool = True, compute_checksums: bool = False
    ) -> list[FileInfo]:
        """Enumerate all source files in repository.

        Args:
            include_test_files: Include test files in results.
            compute_checksums: Compute SHA256 checksums for each file.

        Returns:
            List of FileInfo for source files.
        """
        files: list[FileInfo] = []

        try:
            for path in self.repo_root.rglob("*"):
                if not path.is_file():
                    continue

                if self._should_ignore(path):
                    continue

                # Detect language
                language = self._detect_language(path)
                if language is None:
                    continue

                # Check if test file
                try:
                    relative_path = path.relative_to(self.repo_root)
                except ValueError:
                    continue

                is_test = self._is_test_file(str(relative_path))
                if is_test and not include_test_files:
                    continue

                # Get file size
                try:
                    size_bytes = path.stat().st_size
                except OSError:
                    logger.warning(f"Could not stat file: {path}")
                    continue

                # Compute checksum if requested
                checksum = None
                if compute_checksums:
                    checksum = self._compute_checksum(path)

                file_info = FileInfo(
                    path=path,
                    relative_path=str(relative_path),
                    language=language,
                    size_bytes=size_bytes,
                    is_test=is_test,
                    checksum=checksum,
                )
                files.append(file_info)

        except Exception as e:
            logger.error(f"Error enumerating files in {self.repo_root}: {e}")

        return files
