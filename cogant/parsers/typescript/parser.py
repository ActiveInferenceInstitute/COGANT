"""TypeScript/JavaScript parser plugin using regex."""

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
    classes: List[Dict[str, Any]] = field(default_factory=list)
    functions: List[Dict[str, Any]] = field(default_factory=list)
    imports: List[Dict[str, Any]] = field(default_factory=list)
    interfaces: List[Dict[str, Any]] = field(default_factory=list)
    exports: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class TypeScriptLanguageParser(LanguagePlugin):
    """Parser for TypeScript and JavaScript source files."""

    def __init__(self):
        """Initialize TypeScript parser."""
        metadata = PluginMetadata(
            name="typescript",
            version="0.1.0",
            author="COGANT",
            description="Regex-based parser for TypeScript/JavaScript code structure"
        )
        super().__init__(metadata)
        self.supported_languages = {"typescript", "javascript"}
        self.supported_extensions = {".ts", ".tsx", ".js", ".jsx"}

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize parser with configuration."""
        pass

    def shutdown(self) -> None:
        """Shutdown parser gracefully."""
        pass

    def parse(self, source_code: str) -> Dict[str, Any]:
        """Parse TypeScript/JavaScript source code and return AST.

        Args:
            source_code: Source code as string.

        Returns:
            Dictionary representation of AST.
        """
        result = self._parse_source(source_code)
        return {
            "classes": result.classes,
            "functions": result.functions,
            "imports": result.imports,
            "interfaces": result.interfaces,
            "exports": result.exports,
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

        for cls in ast.get("classes", []):
            symbols.append({
                "type": "class",
                "name": cls["name"],
                "line": cls.get("line"),
            })

        for func in ast.get("functions", []):
            symbols.append({
                "type": "function",
                "name": func["name"],
                "line": func.get("line"),
            })

        for iface in ast.get("interfaces", []):
            symbols.append({
                "type": "interface",
                "name": iface["name"],
                "line": iface.get("line"),
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
            "classes": [],
            "functions": [],
            "interfaces": []
        }

        for cls in ast.get("classes", []):
            types["classes"].append({
                "name": cls["name"],
                "extends": cls.get("extends"),
                "implements": cls.get("implements", [])
            })

        for func in ast.get("functions", []):
            types["functions"].append({
                "name": func["name"],
                "return_type": func.get("return_type"),
                "params": func.get("params", [])
            })

        for iface in ast.get("interfaces", []):
            types["interfaces"].append({
                "name": iface["name"],
                "extends": iface.get("extends", [])
            })

        return types

    def resolve_imports(self, ast: Dict[str, Any]) -> List[str]:
        """Resolve import dependencies from AST.

        Args:
            ast: AST dictionary from parse().

        Returns:
            List of module names imported.
        """
        imports = []
        for imp in ast.get("imports", []):
            module = imp.get("module")
            if module and module not in imports:
                imports.append(module)
        return imports

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a TypeScript/JavaScript file and extract structure.

        Args:
            file_path: Path to file.

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
            "ClassDeclaration",
            "InterfaceDeclaration",
            "FunctionDeclaration",
            "ImportDeclaration",
            "ExportDeclaration",
            "MethodDeclaration",
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
            # Extract imports
            result.imports = self._extract_imports(source)

            # Extract classes
            result.classes = self._extract_classes(source)

            # Extract interfaces
            result.interfaces = self._extract_interfaces(source)

            # Extract functions (non-method functions)
            result.functions = self._extract_functions(source)

            # Extract exports
            result.exports = self._extract_exports(source)

        except Exception as e:
            result.errors.append(f"Parse error: {e}")

        return result

    def _extract_imports(self, source: str) -> List[Dict[str, Any]]:
        """Extract import statements.

        Args:
            source: Source code string.

        Returns:
            List of import dictionaries.
        """
        imports = []
        line_num = 0

        # Pattern: import { x, y } from "module"
        pattern1 = r'import\s+{([^}]+)}\s+from\s+["\']([^"\']+)["\']'
        for match in re.finditer(pattern1, source):
            imports.append({
                "type": "named",
                "module": match.group(2),
                "names": [n.strip() for n in match.group(1).split(",")],
                "line": source[:match.start()].count('\n') + 1,
            })

        # Pattern: import x from "module"
        pattern2 = r'import\s+(\w+)\s+from\s+["\']([^"\']+)["\']'
        for match in re.finditer(pattern2, source):
            imports.append({
                "type": "default",
                "module": match.group(2),
                "name": match.group(1),
                "line": source[:match.start()].count('\n') + 1,
            })

        # Pattern: import * as x from "module"
        pattern3 = r'import\s+\*\s+as\s+(\w+)\s+from\s+["\']([^"\']+)["\']'
        for match in re.finditer(pattern3, source):
            imports.append({
                "type": "namespace",
                "module": match.group(2),
                "name": match.group(1),
                "line": source[:match.start()].count('\n') + 1,
            })

        return imports

    def _extract_classes(self, source: str) -> List[Dict[str, Any]]:
        """Extract class declarations.

        Args:
            source: Source code string.

        Returns:
            List of class dictionaries.
        """
        classes = []

        # Pattern: class ClassName extends Base implements Interface
        pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^{]+))?'

        for match in re.finditer(pattern, source):
            class_name = match.group(1)
            extends = match.group(2) if match.group(2) else None
            implements = [x.strip() for x in match.group(3).split(',')] if match.group(3) else []

            classes.append({
                "name": class_name,
                "extends": extends,
                "implements": implements,
                "line": source[:match.start()].count('\n') + 1,
            })

        return classes

    def _extract_interfaces(self, source: str) -> List[Dict[str, Any]]:
        """Extract interface declarations.

        Args:
            source: Source code string.

        Returns:
            List of interface dictionaries.
        """
        interfaces = []

        # Pattern: interface InterfaceName extends Base
        pattern = r'interface\s+(\w+)(?:\s+extends\s+([^{]+))?'

        for match in re.finditer(pattern, source):
            name = match.group(1)
            extends = [x.strip() for x in match.group(2).split(',')] if match.group(2) else []

            interfaces.append({
                "name": name,
                "extends": extends,
                "line": source[:match.start()].count('\n') + 1,
            })

        return interfaces

    def _extract_functions(self, source: str) -> List[Dict[str, Any]]:
        """Extract function declarations.

        Args:
            source: Source code string.

        Returns:
            List of function dictionaries.
        """
        functions = []

        # Pattern: function name(params): return_type
        pattern = r'(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)(?:\s*:\s*([^{]+))?'

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

    def _extract_exports(self, source: str) -> List[Dict[str, Any]]:
        """Extract export statements.

        Args:
            source: Source code string.

        Returns:
            List of export dictionaries.
        """
        exports = []

        # Pattern: export class/interface/function/const name
        pattern = r'export\s+(?:default\s+)?(?:(class|interface|function|const)\s+(\w+))'

        for match in re.finditer(pattern, source):
            export_type = match.group(1)
            name = match.group(2)

            exports.append({
                "type": export_type,
                "name": name,
                "line": source[:match.start()].count('\n') + 1,
            })

        return exports
