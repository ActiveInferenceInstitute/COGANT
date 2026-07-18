"""Installable language parser registry for COGANT.

All parser implementations live below this package.  Importing a parser
therefore works identically from a checkout and from an installed wheel;
callers never need to mutate ``sys.path`` or know the repository layout.
"""

from cogant.parsers.registry import (
    LanguageParserUnavailable,
    ParserCapability,
    get_parser,
    get_parser_for_extension,
    parser_capabilities,
    parser_capability_report,
    supported_languages,
)
from cogant.parsers.tree_sitter_base import (
    ParsedFile,
    ParsedSymbol,
    TreeSitterParser,
    get_tree_sitter_parser,
)

__all__ = [
    "ParsedFile",
    "ParsedSymbol",
    "TreeSitterParser",
    "get_tree_sitter_parser",
    "LanguageParserUnavailable",
    "ParserCapability",
    "get_parser",
    "get_parser_for_extension",
    "parser_capability_report",
    "parser_capabilities",
    "supported_languages",
]
