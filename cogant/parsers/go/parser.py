"""Go parser plugin using regex."""

import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field

# Add py directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "py"))

from cogant.plugins.base import LanguagePlugin, PluginMetadata


@dataclass
class ParseResult:
    """Result from parsing a file."""

    file_path: Path
    package: Optional[str] = None
    imports: List[Dict[str, Any]] = field(default_factory=list)
    functions: List[Dict[str, Any]] = field(default_factory=list)
    structs: List[Dict[str, Any]] = field(default_factory=list)
    interfaces: List[Dict[str, Any]] = field(default_factory=list)
    methods: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class GoLanguageParser(LanguagePlugin):
    """Parser for Go source files."""

    def __init__(self):
        """Initialize Go parser."""
        metadata = PluginMetadata(
            name="go",
            version="0.1.0",
            author="COGANT",
            description="Regex-based parser for Go code structure"
        )
        super().__init__(metadata)
        self.supported_languages = {"go"}
        self.supported_extensions = {".go"}

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize parser with configuration."""
        pass

    def shutdown(self) -> None:
        """Shutdown parser gracefully."""
        pass

    def parse(self, source_code: str) -> Dict[str, Any]:
        """Parse Go source code and return AST.

        Args:
            source_code: Source code as string.

        Returns:
            Dictionary representation of AST.
        """
        result = self._parse_source(source_code)
        return {
            "package": result.package,
            "imports": result.imports,
            "functions": result.functions,
            "structs": result.structs,
            "interfaces": result.interfaces,
            "methods": result.methods,
            "errors": result.errors,
        }

    def extract_symbols(self, ast: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract symbols from AST.

        Args:
            ast: AST dictionary from parse().

        Returns:
            List of symbol dictionaries.
        """
        symbols = []

        for struct in ast.get("structs", []):
            symbols.append({
                "type": "struct",
                "name": struct["name"],
                "line": struct.get("line"),
            })

        for iface in ast.get("interfaces", []):
            symbols.append({
                "type": "interface",
                "name": iface["name"],
                "line": iface.get("line"),
            })

        for func in ast.get("functions", []):
            symbols.append({
                "type": "function",
                "name": func["name"],
                "line": func.get("line"),
            })

        for method in ast.get("methods", []):
            symbols.append({
                "type": "method",
                "name": method["name"],
                "receiver": method.get("receiver"),
                "line": method.get("line"),
            })

        return symbols

    def extract_types(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """Extract type information from AST.

        Args:
            ast: AST dictionary from parse().

        Returns:
            Type information dictionary.
        """
        types = {
            "structs": [],
            "interfaces": [],
            "functions": [],
            "methods": []
        }

        for struct in ast.get("structs", []):
            types["structs"].append({
                "name": struct["name"],
                "fields": struct.get("fields", [])
            })

        for iface in ast.get("interfaces", []):
            types["interfaces"].append({
                "name": iface["name"],
                "methods": iface.get("methods", [])
            })

        for func in ast.get("functions", []):
            types["functions"].append({
                "name": func["name"],
                "params": func.get("params", []),
                "return_type": func.get("return_type")
            })

        for method in ast.get("methods", []):
            types["methods"].append({
                "name": method["name"],
                "receiver": method.get("receiver"),
                "params": method.get("params", []),
                "return_type": method.get("return_type")
            })

        return types

    def resolve_imports(self, ast: Dict[str, Any]) -> List[str]:
        """Resolve import dependencies from AST.

        Args:
            ast: AST dictionary from parse().

        Returns:
            List of module paths imported.
        """
        imports = []
        for imp in ast.get("imports", []):
            path = imp.get("path")
            if path and path not in imports:
                imports.append(path)
        return imports

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a Go file and extract structure.

        Args:
            file_path: Path to Go file.

        Returns:
            ParseResult with extracted information.
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
        except Exception as e:
            return ParseResult(
                file_path=file_path,
                errors=[f"Failed to read file: {e}"]
            )

        result = self._parse_source(source)
        result.file_path = file_path
        return result

    def get_node_kinds(self) -> Set[str]:
        """Get supported node kinds.

        Returns:
            Set of supported NodeKind values.
        """
        return {
            "Package",
            "Import",
            "FuncDecl",
            "MethodDecl",
            "TypeDecl",
            "StructType",
            "InterfaceType",
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
            # Extract package
            result.package = self._extract_package(source)

            # Extract imports
            result.imports = self._extract_imports(source)

            # Extract structs
            result.structs = self._extract_structs(source)

            # Extract interfaces
            result.interfaces = self._extract_interfaces(source)

            # Extract functions
            result.functions = self._extract_functions(source)

            # Extract methods
            result.methods = self._extract_methods(source)

        except Exception as e:
            result.errors.append(f"Parse error: {e}")

        return result

    def _extract_package(self, source: str) -> Optional[str]:
        """Extract package declaration.

        Args:
            source: Source code string.

        Returns:
            Package name or None.
        """
        pattern = r'package\s+(\w+)'
        match = re.search(pattern, source)
        if match:
            return match.group(1)
        return None

    def _extract_imports(self, source: str) -> List[Dict[str, Any]]:
        """Extract import statements.

        Args:
            source: Source code string.

        Returns:
            List of import dictionaries.
        """
        imports = []

        # Pattern: import (...) blocks
        import_block_pattern = r'import\s*\((.*?)\)'
        for block_match in re.finditer(import_block_pattern, source, re.DOTALL):
            block_content = block_match.group(1)
            # Extract individual imports from the block
            for line in block_content.split('\n'):
                line = line.strip()
                if not line or line.startswith('//'):
                    continue
                # Match "path" or alias "path"
                import_match = re.match(r'(?:(\w+)\s+)?"([^"]+)"', line)
                if import_match:
                    imports.append({
                        "path": import_match.group(2),
                        "alias": import_match.group(1),
                        "line": source[:block_match.start()].count('\n') + 1,
                    })

        # Pattern: import "path/to/package" (single line)
        pattern1 = r'import\s+"([^"]+)"'
        for match in re.finditer(pattern1, source):
            # Skip if it's already matched in block
            if not any(imp["path"] == match.group(1) for imp in imports):
                imports.append({
                    "path": match.group(1),
                    "alias": None,
                    "line": source[:match.start()].count('\n') + 1,
                })

        # Pattern: import alias "path/to/package"
        pattern2 = r'import\s+(\w+)\s+"([^"]+)"'
        for match in re.finditer(pattern2, source):
            # Skip if it's already matched
            if not any(imp["path"] == match.group(2) for imp in imports):
                imports.append({
                    "path": match.group(2),
                    "alias": match.group(1),
                    "line": source[:match.start()].count('\n') + 1,
                })

        return imports

    def _extract_structs(self, source: str) -> List[Dict[str, Any]]:
        """Extract struct type definitions.

        Args:
            source: Source code string.

        Returns:
            List of struct dictionaries.
        """
        structs = []

        # Pattern: type StructName struct { ... }
        pattern = r'type\s+(\w+)\s+struct'

        for match in re.finditer(pattern, source):
            name = match.group(1)

            # Try to extract fields from the struct body
            struct_start = match.end()
            fields = []

            # Look for the struct body
            brace_match = re.search(r'\{', source[struct_start:])
            if brace_match:
                body_start = struct_start + brace_match.start() + 1
                brace_count = 1
                body_end = body_start

                for i, char in enumerate(source[body_start:]):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            body_end = body_start + i
                            break

                body = source[body_start:body_end]

                # Extract field names and types
                for field_match in re.finditer(r'(\w+)\s+([^\n;]+)', body):
                    fields.append({
                        "name": field_match.group(1),
                        "type": field_match.group(2).strip()
                    })

            structs.append({
                "name": name,
                "fields": fields,
                "line": source[:match.start()].count('\n') + 1,
            })

        return structs

    def _extract_interfaces(self, source: str) -> List[Dict[str, Any]]:
        """Extract interface type definitions.

        Args:
            source: Source code string.

        Returns:
            List of interface dictionaries.
        """
        interfaces = []

        # Pattern: type InterfaceName interface { ... }
        pattern = r'type\s+(\w+)\s+interface'

        for match in re.finditer(pattern, source):
            name = match.group(1)

            # Try to extract methods from the interface body
            methods = []

            interfaces.append({
                "name": name,
                "methods": methods,
                "line": source[:match.start()].count('\n') + 1,
            })

        return interfaces

    def _extract_functions(self, source: str) -> List[Dict[str, Any]]:
        """Extract function declarations (not methods).

        Args:
            source: Source code string.

        Returns:
            List of function dictionaries.
        """
        functions = []

        # Pattern: func name(params) return_type
        # Negative lookbehind to exclude methods: func (receiver) name(params)
        pattern = r'func\s+(?!\()\s*(\w+)\s*\(([^)]*)\)(?:\s+([^{]+))?'

        for match in re.finditer(pattern, source):
            name = match.group(1)
            params_str = match.group(2) if match.group(2) else ""
            return_type = match.group(3).strip() if match.group(3) else None

            params = [p.strip() for p in params_str.split(',')] if params_str else []

            functions.append({
                "name": name,
                "params": params,
                "return_type": return_type,
                "line": source[:match.start()].count('\n') + 1,
            })

        return functions

    def _extract_methods(self, source: str) -> List[Dict[str, Any]]:
        """Extract method definitions.

        Args:
            source: Source code string.

        Returns:
            List of method dictionaries.
        """
        methods = []

        # Pattern: func (receiver Type) name(params) return_type
        pattern = r'func\s+\(([^)]+)\)\s+(\w+)\s*\(([^)]*)\)(?:\s+([^{]+))?'

        for match in re.finditer(pattern, source):
            receiver = match.group(1).strip()
            name = match.group(2)
            params_str = match.group(3) if match.group(3) else ""
            return_type = match.group(4).strip() if match.group(4) else None

            params = [p.strip() for p in params_str.split(',')] if params_str else []

            methods.append({
                "name": name,
                "receiver": receiver,
                "params": params,
                "return_type": return_type,
                "line": source[:match.start()].count('\n') + 1,
            })

        return methods
