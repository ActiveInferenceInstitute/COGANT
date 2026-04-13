# py/cogant/plugins/base.py  (excerpt)

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, List

from cogant.schemas.core import Node, Edge


class LanguagePlugin(ABC):
    """A language-specific parser plugin.

    Plugins are stateless. The registry instantiates each plugin once and
    dispatches files to it by extension + shebang match.
    """

    name: str
    extensions: tuple[str, ...]
    shebang_patterns: tuple[str, ...] = ()

    @abstractmethod
    def parse_file(self, path: Path) -> "ParseResult":
        """Parse a single source file into nodes and edges."""

    @abstractmethod
    def parse_source(self, source: str, filename: str) -> "ParseResult":
        """Parse in-memory source without touching the filesystem."""
