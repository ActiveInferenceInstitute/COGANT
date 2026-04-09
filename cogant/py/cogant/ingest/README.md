# Ingest — Repository Source Reading and File Enumeration

The ingest module provides tools to read and analyze repositories from local or remote sources, detect programming languages, extract dependency manifests, and enumerate source files with metadata.

## Module Overview

RepoIngester is the primary entry point. It ingests repositories (local paths or remote Git URLs), enumerates source files with language detection, and extracts dependencies from manifest files. RepoSnapshot encapsulates the complete result with metadata, file list, and dependencies.

File enumeration respects .gitignore patterns, filters out build artifacts and common ignore patterns (node_modules, venv, __pycache__, etc.), and optionally computes SHA256 checksums for integrity tracking. FileInfo records path, relative path, detected language, file size, test status, and optional checksum.

Language detection uses file extensions to identify programming languages (Python, JavaScript, TypeScript, Rust, Go, Java, C/C++, C#, Ruby, PHP). LanguageDetector provides both single-file and repository-wide language detection, with lazy-loading of language-specific parsers.

ManifestParser extracts dependencies from multiple manifest file formats: Python (setup.py, pyproject.toml, requirements.txt), Node.js (package.json), and Rust (Cargo.toml). Each manifest is parsed to extract project metadata and dependencies (including dev vs. production, local vs. third-party).

RepoMetadata records repository-level information: name, URL/path, commit hash, commit message, author, timestamp, primary language, and description. These are extracted from git history when available.

## API Reference

RepoIngester class with methods:
- ingest_local(repo_path, include_test_files=True, compute_checksums=False) — Ingest a local repository and return RepoSnapshot
- ingest_git_remote(url, branch=None, include_test_files=True, compute_checksums=False, cleanup=True) — Clone and ingest a remote Git repository

FileEnumerator class with methods:
- enumerate(include_test_files=True, compute_checksums=False) — List all source files with metadata

ManifestParser class with methods:
- parse(path) — Auto-detect manifest type and parse (returns dict, list of Dependency)
- parse_setup_py(path), parse_pyproject_toml(path), parse_requirements_txt(path), parse_package_json(path), parse_cargo_toml(path) — Language-specific parsers

LanguageDetector class with static methods:
- detect_language(file_path) — Detect language from file extension
- detect_repo_languages(repo_path) — Return dict of language → count
- get_parser(language) — Lazy-load and return language-specific parser instance
- get_supported_languages() — List of supported languages

Data classes:
- RepoSnapshot(metadata, files, dependencies, root_path) — Complete repository snapshot
- RepoMetadata(name, url, commit_hash, commit_message, timestamp, author, language, description) — Repository-level metadata
- FileInfo(path, relative_path, language, size_bytes, is_test, checksum) — Single source file metadata
- Dependency(name, version, is_dev, is_local) — Package dependency record
