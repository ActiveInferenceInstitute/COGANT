from pathlib import Path
from typing import Any

parsers_root: Any

class LanguageDetector:
    EXTENSION_MAP: Any
    PARSER_CLASSES: Any
    @staticmethod
    def detect_language(file_path: Path) -> str | None: ...
    @staticmethod
    def detect_repo_languages(repo_path: Path) -> dict[str, int]: ...
    @classmethod
    def get_parser(cls, language: str) -> Any: ...
    @classmethod
    def get_supported_languages(cls) -> list[str]: ...

def get_parser_for_extension(ext: str) -> Any: ...
