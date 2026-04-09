"""COGANT ingest pipeline: repository source reading and manifest parsing.

Provides tools to clone/read repositories, detect languages, parse manifests,
enumerate files, and extract commit metadata.
"""

from cogant.ingest.repo import RepoIngester, RepoSnapshot, RepoMetadata
from cogant.ingest.manifest import ManifestParser, Dependency
from cogant.ingest.files import FileEnumerator, FileInfo

__all__ = [
    "RepoIngester",
    "RepoSnapshot",
    "RepoMetadata",
    "ManifestParser",
    "Dependency",
    "FileEnumerator",
    "FileInfo",
]
