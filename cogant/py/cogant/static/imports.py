"""Import resolution and analysis: classify imports and build import graph."""

import hashlib
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cogant.static.parser import PythonASTParser

logger = logging.getLogger(__name__)


@dataclass
class ImportEdge:
    """An import relationship between modules."""

    id: str
    """Unique edge identifier."""

    source_file: Path
    """File containing the import."""

    module_name: str
    """Module being imported."""

    is_relative: bool
    """Whether import is relative."""

    is_stdlib: bool
    """Whether module is from Python standard library."""

    is_third_party: bool
    """Whether module is from third-party package."""

    is_local: bool
    """Whether module is local to repository."""

    resolved_file: Path | None = None
    """Resolved file path if found."""

    resolved_module: str | None = None
    """Resolved module name."""

    line_num: int = 0
    """Line number of import statement."""

    imported_names: list[str] = field(default_factory=list)
    """Specific names imported (for 'from X import Y')."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""


class ImportAnalyzer:
    """Analyze and resolve import statements."""

    def __init__(self, repo_root: Path | None = None):
        """Initialize import analyzer.

        Args:
            repo_root: Root path of repository for local import resolution.
                Absolute imports (``import pkg.mod``) are resolved against
                it only when it is given; relative imports always resolve
                against the importing file.
        """
        self.repo_root = Path(repo_root or "/")
        self._resolve_absolute = repo_root is not None
        self.parser = PythonASTParser()
        self._stdlib_modules = self._load_stdlib_modules()

    def analyze_file(self, file_path: Path) -> list[ImportEdge]:
        """Analyze imports in a Python file.

        Args:
            file_path: Path to Python file.

        Returns:
            List of ImportEdge for all imports found.
        """
        module = self.parser.parse_file(file_path)
        return self._build_import_edges(file_path, module.imports)

    def analyze_source(self, source: str, file_path: Path) -> list[ImportEdge]:
        """Analyze imports in Python source code.

        Args:
            source: Python source code.
            file_path: Path for reference.

        Returns:
            List of ImportEdge for all imports found.
        """
        module = self.parser.parse_string(source, file_path)
        return self._build_import_edges(file_path, module.imports)

    def _build_import_edges(self, file_path: Path, import_defs: Any) -> list[ImportEdge]:
        """Build import edges from import definitions.

        Args:
            file_path: Source file path.
            import_defs: List of ImportDef from parser.

        Returns:
            List of ImportEdge.
        """
        edges = []

        for imp in import_defs:
            # Classify on the top-level package: ``os.path`` is stdlib because
            # ``os`` is. Relative imports are never stdlib.
            top_level = imp.module_name.split(".", 1)[0]
            is_stdlib = not imp.is_relative and top_level in self._stdlib_modules

            # Resolve relative imports, and absolute ones against repo_root,
            # before anything non-stdlib is called third-party.
            resolved_file = None
            if imp.is_relative:
                metadata = imp.metadata if isinstance(imp.metadata, dict) else {}
                resolved_file = self._resolve_local_import(
                    file_path,
                    imp.module_name,
                    True,
                    level=int(metadata.get("level", 1) or 1),
                    names=list(imp.names or []),
                )
            elif not is_stdlib and self._resolve_absolute:
                resolved_file = self._resolve_local_import(file_path, imp.module_name, False)
            is_local = resolved_file is not None
            is_third_party = not is_stdlib and not imp.is_relative and not is_local

            edge = ImportEdge(
                id=self._generate_import_id(file_path, imp.module_name),
                source_file=file_path,
                module_name=imp.module_name,
                is_relative=imp.is_relative,
                is_stdlib=is_stdlib,
                is_third_party=is_third_party,
                is_local=is_local,
                resolved_file=resolved_file,
                line_num=imp.line_num,
                imported_names=imp.names,
            )
            edges.append(edge)

        return edges

    def _resolve_local_import(
        self,
        source_file: Path,
        module_name: str,
        is_relative: bool,
        level: int = 1,
        names: list[str] | None = None,
    ) -> Path | None:
        """Try to resolve a local import to a file.

        Args:
            source_file: File containing the import.
            module_name: Module name to resolve (empty for ``from . import x``).
            is_relative: Whether import is relative.
            level: Number of leading dots of a relative import; each dot
                beyond the first moves up one package directory.
            names: Imported names; for ``from . import x`` a submodule
                ``x`` is preferred over the package itself.

        Returns:
            Resolved file path or None if not found.
        """
        if is_relative:
            base = source_file.parent
            for _ in range(max(level, 1) - 1):
                base = base.parent
            if not module_name:
                # ``from . import x``: x is a submodule or a package attribute.
                for name in names or []:
                    for candidate in (base / f"{name}.py", base / name / "__init__.py"):
                        if candidate.exists():
                            return candidate
                package_init = base / "__init__.py"
                return package_init if package_init.exists() else None
            target = base / module_name.replace(".", "/")
        else:
            # Absolute import
            target = self.repo_root / module_name.replace(".", "/")

        # Try as module (file.py)
        module_file = target.parent / f"{target.name}.py"
        if module_file.exists():
            return module_file

        # Try as package (directory with __init__.py)
        if (target / "__init__.py").exists():
            return target / "__init__.py"

        return None

    @staticmethod
    def _load_stdlib_modules() -> set[str]:
        """Load set of Python standard library module names.

        Returns:
            Set of stdlib module names: the running interpreter's
            ``sys.stdlib_module_names`` plus modules removed from recent
            Python versions that older code may still import.
        """
        # Core standard library modules
        stdlib = {
            "__future__",
            "abc",
            "aifc",
            "argparse",
            "array",
            "ast",
            "asyncio",
            "atexit",
            "audioop",
            "base64",
            "bdb",
            "binascii",
            "binhex",
            "bisect",
            "builtins",
            "bz2",
            "calendar",
            "cgi",
            "cgitb",
            "chunk",
            "cmath",
            "cmd",
            "code",
            "codecs",
            "codeop",
            "collections",
            "colorsys",
            "compileall",
            "concurrent",
            "configparser",
            "contextlib",
            "contextvars",
            "copy",
            "copyreg",
            "cProfile",
            "crypt",
            "csv",
            "ctypes",
            "curses",
            "dataclasses",
            "datetime",
            "dbm",
            "decimal",
            "difflib",
            "dis",
            "distutils",
            "doctest",
            "dummy_thread",
            "email",
            "encodings",
            "enum",
            "errno",
            "faulthandler",
            "fcntl",
            "filecmp",
            "fileinput",
            "fnmatch",
            "fractions",
            "ftplib",
            "functools",
            "gc",
            "getopt",
            "getpass",
            "gettext",
            "glob",
            "graphlib",
            "grp",
            "gzip",
            "hashlib",
            "heapq",
            "hmac",
            "html",
            "http",
            "idlelib",
            "imaplib",
            "imghdr",
            "imp",
            "importlib",
            "inspect",
            "io",
            "ipaddress",
            "itertools",
            "json",
            "keyword",
            "lib2to3",
            "linecache",
            "locale",
            "logging",
            "lzma",
            "mailbox",
            "mailcap",
            "marshal",
            "math",
            "mimetypes",
            "mmap",
            "modulefinder",
            "msilib",
            "msvcrt",
            "multiprocessing",
            "netrc",
            "nis",
            "nntplib",
            "numbers",
            "operator",
            "optparse",
            "os",
            "ossaudiodev",
            "parser",
            "pathlib",
            "pdb",
            "pickle",
            "pickletools",
            "pipes",
            "pkgutil",
            "platform",
            "plistlib",
            "poplib",
            "posix",
            "posixpath",
            "pprint",
            "profile",
            "pstats",
            "pty",
            "pwd",
            "py_compile",
            "pyclbr",
            "pydoc",
            "queue",
            "quopri",
            "random",
            "readline",
            "reprlib",
            "resource",
            "rlcompleter",
            "runpy",
            "sched",
            "secrets",
            "select",
            "selectors",
            "shelve",
            "shlex",
            "shutil",
            "signal",
            "site",
            "smtpd",
            "smtplib",
            "sndhdr",
            "socket",
            "socketserver",
            "spwd",
            "sqlite3",
            "ssl",
            "stat",
            "statistics",
            "string",
            "stringprep",
            "struct",
            "subprocess",
            "sunau",
            "symbol",
            "symtable",
            "sys",
            "sysconfig",
            "syslog",
            "tabnanny",
            "tarfile",
            "telnetlib",
            "tempfile",
            "termios",
            "test",
            "textwrap",
            "threading",
            "time",
            "timeit",
            "tkinter",
            "token",
            "tokenize",
            "tomllib",
            "trace",
            "traceback",
            "tracemalloc",
            "tty",
            "turtle",
            "turtledemo",
            "types",
            "typing",
            "unicodedata",
            "unittest",
            "urllib",
            "uu",
            "uuid",
            "venv",
            "warnings",
            "wave",
            "weakref",
            "webbrowser",
            "winreg",
            "winsound",
            "wsgiref",
            "xdrlib",
            "xml",
            "xmlrpc",
            "zipapp",
            "zipfile",
            "zipimport",
            "zlib",
        }

        return stdlib | set(sys.stdlib_module_names)

    @staticmethod
    def _generate_import_id(file_path: Path, module_name: str) -> str:
        """Generate stable import edge ID.

        Args:
            file_path: Source file path.
            module_name: Module being imported.

        Returns:
            Stable ID (SHA256 hash).
        """
        content = f"{file_path.resolve()}:import:{module_name}"
        hash_obj = hashlib.sha256(content.encode())
        return hash_obj.hexdigest()[:16]
