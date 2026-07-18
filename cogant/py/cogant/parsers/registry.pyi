from dataclasses import dataclass

from cogant.plugins.base import LanguagePlugin

class LanguageParserUnavailable(ImportError, RuntimeError):
    language: str
    reason: str
    def __init__(self, language: str, reason: str) -> None: ...

@dataclass(frozen=True)
class ParserCapability:
    language: str
    extensions: tuple[str, ...]
    implementation: str
    optional_dependency: str | None = None
    fallback_implementation: str | None = None

def parser_capabilities() -> dict[str, ParserCapability]: ...
def parser_capability_report() -> dict[str, dict[str, object]]: ...
def supported_languages() -> tuple[str, ...]: ...
def get_parser(language: str) -> LanguagePlugin: ...
def get_parser_for_extension(extension: str) -> LanguagePlugin: ...

__all__: list[str]
