from pathlib import Path
from typing import Any

parsers_root: Any

class LanguageDetectionError(RuntimeError): ...

class LanguageDetector:
    EXTENSION_MAP: Any
    @staticmethod
    def detect_language(file_path: Path) -> str | None: ...
    @staticmethod
    def detect_repo_languages(repo_path: Path | str) -> dict[str, int]: ...
    @classmethod
    def get_parser(cls, language: str) -> Any: ...
    @classmethod
    def get_supported_languages(cls) -> list[str]: ...
