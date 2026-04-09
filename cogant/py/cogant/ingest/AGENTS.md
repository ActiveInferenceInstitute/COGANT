# Agents — py/cogant/ingest

## Owner
Source Ingestion

## Responsibilities
RepoIngester drives repository ingestion: cloning or reading local repositories, enumerating source files, detecting languages, and extracting dependencies. FileEnumerator handles .gitignore parsing, test file detection, and file filtering. ManifestParser handles multiple manifest formats (setup.py, pyproject.toml, requirements.txt, package.json, Cargo.toml). LanguageDetector identifies programming languages by extension and lazy-loads language-specific parsers.

## Coordination
Output: RepoSnapshot with files, dependencies, and metadata. Flows to static (parsers) and dynamic (coverage/traces) pipelines. Configuration from config/defaults.py. No downstream modification; ingest is read-only.

## How to Extend
Add new manifest format: extend ManifestParser with parse_<format> method returning (metadata dict, dependencies list). Add new language: extend LANGUAGE_EXTENSIONS in files.py and LanguageDetector.EXTENSION_MAP, then implement corresponding parser in parsers/. Add new ignore pattern: extend IGNORE_PATTERNS or .gitignore respect.
