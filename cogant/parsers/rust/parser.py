"""Rust parser plugin using regex."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from parsers._base import CogantLanguagePlugin  # noqa: E402


@dataclass
class ParseResult:
    """Result from parsing a file."""

    file_path: Path
    structs: list[dict[str, Any]] = field(default_factory=list)
    enums: list[dict[str, Any]] = field(default_factory=list)
    functions: list[dict[str, Any]] = field(default_factory=list)
    traits: list[dict[str, Any]] = field(default_factory=list)
    impls: list[dict[str, Any]] = field(default_factory=list)
    modules: list[dict[str, Any]] = field(default_factory=list)
    uses: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class RustLanguageParser(CogantLanguagePlugin):
    """Parser for Rust source files."""

    PLUGIN_NAME = "rust"
    PLUGIN_DESCRIPTION = "Regex-based parser for Rust code structure"
    SUPPORTED_LANGUAGES = {"rust"}
    SUPPORTED_EXTENSIONS = {".rs"}

    def parse(self, source_code: str) -> dict[str, Any]:
        """Parse Rust source code and return AST.

        Args:
            source_code: Source code as string.

        Returns:
            Dictionary representation of AST.
        """
        result = self._parse_source(source_code)
        return {
            "structs": result.structs,
            "enums": result.enums,
            "functions": result.functions,
            "traits": result.traits,
            "impls": result.impls,
            "modules": result.modules,
            "uses": result.uses,
            "errors": result.errors,
        }

    def extract_symbols(self, ast: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract symbols from AST.

        Args:
            ast: AST dictionary from parse().

        Returns:
            List of symbol dictionaries.
        """
        symbols = []

        for struct in ast.get("structs", []):
            symbols.append(
                {
                    "type": "struct",
                    "name": struct["name"],
                    "line": struct.get("line"),
                }
            )

        for enum in ast.get("enums", []):
            symbols.append(
                {
                    "type": "enum",
                    "name": enum["name"],
                    "line": enum.get("line"),
                }
            )

        for func in ast.get("functions", []):
            symbols.append(
                {
                    "type": "function",
                    "name": func["name"],
                    "line": func.get("line"),
                }
            )

        for trait in ast.get("traits", []):
            symbols.append(
                {
                    "type": "trait",
                    "name": trait["name"],
                    "line": trait.get("line"),
                }
            )

        return symbols

    def extract_types(self, ast: dict[str, Any]) -> dict[str, Any]:
        """Extract type information from AST.

        Args:
            ast: AST dictionary from parse().

        Returns:
            Type information dictionary.
        """
        types = {"structs": [], "enums": [], "functions": [], "traits": []}

        for struct in ast.get("structs", []):
            types["structs"].append({"name": struct["name"], "fields": struct.get("fields", [])})

        for enum in ast.get("enums", []):
            types["enums"].append({"name": enum["name"], "variants": enum.get("variants", [])})

        for func in ast.get("functions", []):
            types["functions"].append(
                {
                    "name": func["name"],
                    "return_type": func.get("return_type"),
                    "params": func.get("params", []),
                }
            )

        for trait in ast.get("traits", []):
            types["traits"].append(
                {
                    "name": trait["name"],
                }
            )

        return types

    def resolve_imports(self, ast: dict[str, Any]) -> list[str]:
        """Resolve import dependencies from AST.

        Args:
            ast: AST dictionary from parse().

        Returns:
            List of module names imported.
        """
        imports = []
        for use in ast.get("uses", []):
            path = use.get("path")
            if path and path not in imports:
                imports.append(path)
        return imports

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a Rust file and extract structure.

        Args:
            file_path: Path to Rust file.

        Returns:
            ParseResult with extracted information.
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
        except Exception as e:
            return ParseResult(file_path=file_path, errors=[f"Failed to read file: {e}"])

        result = self._parse_source(source)
        result.file_path = file_path
        return result

    def get_node_kinds(self) -> set[str]:
        """Get supported node kinds.

        Returns:
            Set of supported NodeKind values.
        """
        return {
            "StructDef",
            "EnumDef",
            "TraitDef",
            "ImplBlock",
            "FnDef",
            "ModDef",
            "UseDeclaration",
        }

    def _parse_source(self, source: str) -> ParseResult:
        """Parse source code and extract structure.

        Args:
            source: Source code as string.

        Returns:
            ParseResult with extracted information.
        """
        result = ParseResult(file_path=Path("<string>"))

        try:
            # Extract use statements
            result.uses = self._extract_uses(source)

            # Extract structs
            result.structs = self._extract_structs(source)

            # Extract enums
            result.enums = self._extract_enums(source)

            # Extract traits
            result.traits = self._extract_traits(source)

            # Extract impl blocks
            result.impls = self._extract_impls(source)

            # Extract functions
            result.functions = self._extract_functions(source)

            # Extract modules
            result.modules = self._extract_modules(source)

        except Exception as e:
            result.errors.append(f"Parse error: {e}")

        return result

    def _extract_uses(self, source: str) -> list[dict[str, Any]]:
        """Extract use statements.

        Args:
            source: Source code string.

        Returns:
            List of use dictionaries.
        """
        uses = []

        # Pattern: use path::to::module
        pattern = r"use\s+([a-zA-Z0-9_:*{}]+)(?:\s+as\s+(\w+))?;"

        for match in re.finditer(pattern, source):
            path = match.group(1)
            alias = match.group(2)

            uses.append(
                {
                    "path": path,
                    "alias": alias,
                    "line": source[: match.start()].count("\n") + 1,
                }
            )

        return uses

    def _extract_structs(self, source: str) -> list[dict[str, Any]]:
        """Extract struct definitions.

        Args:
            source: Source code string.

        Returns:
            List of struct dictionaries.
        """
        structs = []

        # Pattern: struct Name { fields }
        pattern = r"(?:pub\s+)?struct\s+(\w+)(?:\s*<([^>]+)>)?(?:\s*{([^}]*)})?"

        for match in re.finditer(pattern, source):
            name = match.group(1)
            generics = match.group(2) if match.group(2) else None
            fields_str = match.group(3) if match.group(3) else ""

            # Extract fields
            fields = []
            if fields_str:
                for field_match in re.finditer(r"(\w+)\s*:\s*([^,;]+)", fields_str):
                    fields.append(
                        {"name": field_match.group(1), "type": field_match.group(2).strip()}
                    )

            structs.append(
                {
                    "name": name,
                    "generics": generics,
                    "fields": fields,
                    "line": source[: match.start()].count("\n") + 1,
                }
            )

        return structs

    def _extract_enums(self, source: str) -> list[dict[str, Any]]:
        """Extract enum definitions.

        Args:
            source: Source code string.

        Returns:
            List of enum dictionaries.
        """
        enums = []

        # Pattern: enum Name { variants }
        pattern = r"(?:pub\s+)?enum\s+(\w+)(?:\s*<([^>]+)>)?(?:\s*{([^}]*)})?"

        for match in re.finditer(pattern, source):
            name = match.group(1)
            generics = match.group(2) if match.group(2) else None
            variants_str = match.group(3) if match.group(3) else ""

            # Extract variants
            variants = []
            if variants_str:
                for variant_match in re.finditer(
                    r"(\w+)(?:\s*\(([^)]*)\))?(?:\s*{([^}]*)})?", variants_str
                ):
                    variants.append(
                        {
                            "name": variant_match.group(1),
                            "data": variant_match.group(2) or variant_match.group(3),
                        }
                    )

            enums.append(
                {
                    "name": name,
                    "generics": generics,
                    "variants": variants,
                    "line": source[: match.start()].count("\n") + 1,
                }
            )

        return enums

    def _extract_traits(self, source: str) -> list[dict[str, Any]]:
        """Extract trait definitions.

        Args:
            source: Source code string.

        Returns:
            List of trait dictionaries.
        """
        traits = []

        # Pattern: trait Name + optional bounds
        pattern = r"(?:pub\s+)?trait\s+(\w+)(?:\s*:\s*([^{]+))?"

        for match in re.finditer(pattern, source):
            name = match.group(1)
            bounds = match.group(2).strip() if match.group(2) else None

            traits.append(
                {
                    "name": name,
                    "bounds": bounds,
                    "line": source[: match.start()].count("\n") + 1,
                }
            )

        return traits

    def _extract_impls(self, source: str) -> list[dict[str, Any]]:
        """Extract impl blocks.

        Args:
            source: Source code string.

        Returns:
            List of impl dictionaries.
        """
        impls = []

        # Pattern: impl Name or impl Trait for Type
        pattern = r"impl\s+(?:<?([^>}]+)>?\s+for\s+)?(\w+)"

        for match in re.finditer(pattern, source):
            trait_name = match.group(1)
            type_name = match.group(2)

            impls.append(
                {
                    "trait": trait_name,
                    "type": type_name,
                    "line": source[: match.start()].count("\n") + 1,
                }
            )

        return impls

    def _extract_functions(self, source: str) -> list[dict[str, Any]]:
        """Extract function definitions.

        Args:
            source: Source code string.

        Returns:
            List of function dictionaries.
        """
        functions = []

        # Pattern: fn name(params) -> return_type
        pattern = (
            r"(?:pub\s+)?(?:async\s+)?(?:unsafe\s+)?fn\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*([^{]+))?"
        )

        for match in re.finditer(pattern, source):
            name = match.group(1)
            params_str = match.group(2) if match.group(2) else ""
            return_type = match.group(3).strip() if match.group(3) else None

            params = [p.strip() for p in params_str.split(",")] if params_str else []

            functions.append(
                {
                    "name": name,
                    "params": params,
                    "return_type": return_type,
                    "line": source[: match.start()].count("\n") + 1,
                }
            )

        return functions

    def _extract_modules(self, source: str) -> list[dict[str, Any]]:
        """Extract module definitions.

        Args:
            source: Source code string.

        Returns:
            List of module dictionaries.
        """
        modules = []

        # Pattern: mod name or mod name { ... }
        pattern = r"(?:pub\s+)?mod\s+(\w+)"

        for match in re.finditer(pattern, source):
            name = match.group(1)

            modules.append(
                {
                    "name": name,
                    "line": source[: match.start()].count("\n") + 1,
                }
            )

        return modules
