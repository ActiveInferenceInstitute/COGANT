"""Comprehensive tests for symbol extraction."""

import pytest
from pathlib import Path

from cogant.static.symbols import SymbolExtractor


class TestSymbolExtractor:
    """Tests for SymbolExtractor functionality."""

    def test_extractor_creation(self):
        """Test creating a symbol extractor instance."""
        extractor = SymbolExtractor()
        assert extractor is not None

    def test_extract_from_simple_code(self, sample_python_code: str, temp_dir: Path):
        """Test extracting symbols from simple code."""
        # Create temp file
        file_path = temp_dir / "test.py"
        file_path.write_text(sample_python_code)

        extractor = SymbolExtractor()
        symbol_table = extractor.extract_from_file(file_path)

        assert symbol_table is not None
        assert len(symbol_table.symbols) > 0

    def test_extract_classes(self, temp_dir: Path):
        """Test extracting classes."""
        code = '''
class User:
    """User class."""
    pass

class Database:
    """Database class."""
    pass

class Connection:
    """Connection class."""
    pass
'''
        file_path = temp_dir / "classes.py"
        file_path.write_text(code)

        extractor = SymbolExtractor()
        symbol_table = extractor.extract_from_file(file_path)

        # Should extract class symbols
        assert symbol_table is not None
        classes = [s for s in symbol_table.symbols if s.kind == "class"]
        assert len(classes) >= 3

    def test_extract_functions(self, temp_dir: Path):
        """Test extracting functions."""
        code = '''
def hello():
    """Say hello."""
    pass

def goodbye():
    """Say goodbye."""
    pass

async def fetch_data():
    """Fetch data."""
    pass
'''
        file_path = temp_dir / "functions.py"
        file_path.write_text(code)

        extractor = SymbolExtractor()
        symbol_table = extractor.extract_from_file(file_path)

        assert symbol_table is not None
        functions = [s for s in symbol_table.symbols if s.kind == "function"]
        assert len(functions) >= 3

    def test_extract_qualified_names(self, sample_python_code: str, temp_dir: Path):
        """Test extracting qualified names for nested symbols."""
        file_path = temp_dir / "qualified.py"
        file_path.write_text(sample_python_code)

        extractor = SymbolExtractor()
        symbol_table = extractor.extract_from_file(file_path)

        # Should have qualified names for methods
        assert symbol_table is not None
        methods = [s for s in symbol_table.symbols if s.kind == "method"]
        assert len(methods) > 0
        # Methods should have qualified names with class prefix
        for method in methods:
            assert "." in method.qualified_name

    def test_extract_symbol_types(self, temp_dir: Path):
        """Test extracting various symbol types."""
        code = '''
class MyClass:
    """A class."""
    class_var = 10

    def __init__(self):
        self.instance_var = 20

    def method(self):
        """A method."""
        pass

    @property
    def prop(self):
        """A property."""
        return 42

    @staticmethod
    def static():
        """Static method."""
        pass

    @classmethod
    def cls_method(cls):
        """Class method."""
        pass

def module_func():
    """Module function."""
    pass
'''
        file_path = temp_dir / "types.py"
        file_path.write_text(code)

        extractor = SymbolExtractor()
        symbol_table = extractor.extract_from_file(file_path)

        assert symbol_table is not None
        # Should have class, methods, and function
        class_symbols = [s for s in symbol_table.symbols if s.kind == "class"]
        method_symbols = [s for s in symbol_table.symbols if s.kind == "method"]
        function_symbols = [s for s in symbol_table.symbols if s.kind == "function"]
        assert len(class_symbols) >= 1
        assert len(method_symbols) >= 4
        assert len(function_symbols) >= 1

    def test_extract_scopes(self, temp_dir: Path):
        """Test extracting symbol scopes."""
        code = '''
PUBLIC_VAR = 10
_PRIVATE_VAR = 20

class MyClass:
    class_var = 30
    _private_var = 40

    def method(self):
        local_var = 50
        self._private = 60
        return local_var

def function():
    func_var = 70
    return func_var
'''
        file_path = temp_dir / "scopes.py"
        file_path.write_text(code)

        extractor = SymbolExtractor()
        symbol_table = extractor.extract_from_file(file_path)

        assert symbol_table is not None
        # Should have module-scope variables
        variables = [s for s in symbol_table.symbols if s.kind == "variable"]
        assert len(variables) > 0

    def test_extract_with_decorators(self, temp_dir: Path):
        """Test extracting decorated symbols."""
        code = '''
@decorator
def decorated_func():
    pass

@decorator1
@decorator2
class DecoratedClass:
    @property
    def prop(self):
        pass

    @staticmethod
    def static():
        pass
'''
        file_path = temp_dir / "decorators.py"
        file_path.write_text(code)

        extractor = SymbolExtractor()
        symbol_table = extractor.extract_from_file(file_path)

        assert symbol_table is not None
        # Should extract decorated symbols
        assert len(symbol_table.symbols) > 0
        # Check that decorators are captured
        decorated = [s for s in symbol_table.symbols if len(s.decorators) > 0]
        assert len(decorated) > 0

    def test_extract_with_annotations(self, temp_dir: Path):
        """Test extracting symbols with type annotations."""
        code = '''
def typed_func(x: int, y: str) -> bool:
    """Typed function."""
    return True

class TypedClass:
    value: int
    name: str = "default"
    items: list[str]

    def typed_method(self, a: float) -> float:
        return a * 2
'''
        file_path = temp_dir / "typed.py"
        file_path.write_text(code)

        extractor = SymbolExtractor()
        symbol_table = extractor.extract_from_file(file_path)

        assert symbol_table is not None
        # Should extract typed symbols
        assert len(symbol_table.symbols) > 0

    def test_extract_from_tmp_repo(self, tmp_repo: Path):
        """Test extracting from sample repository."""
        main_file = tmp_repo / "main.py"
        assert main_file.exists()

        extractor = SymbolExtractor()
        symbol_table = extractor.extract_from_file(main_file)

        assert symbol_table is not None
        assert len(symbol_table.symbols) > 0

    def test_extract_multiple_files(self, tmp_repo: Path):
        """Test extracting from multiple files."""
        extractor = SymbolExtractor()

        # Extract from main.py
        main_table = extractor.extract_from_file(tmp_repo / "main.py")
        assert main_table is not None
        assert len(main_table.symbols) > 0

        # Extract from utils.py
        utils_table = extractor.extract_from_file(tmp_repo / "utils.py")
        assert utils_table is not None
        assert len(utils_table.symbols) > 0

    def test_symbol_has_metadata(self, temp_dir: Path):
        """Test extracted symbols have metadata."""
        code = '''
def my_function(x: int) -> str:
    """My function."""
    return str(x)
'''
        file_path = temp_dir / "metadata.py"
        file_path.write_text(code)

        extractor = SymbolExtractor()
        symbol_table = extractor.extract_from_file(file_path)

        assert symbol_table is not None
        # Symbols should have location info and metadata
        assert len(symbol_table.symbols) > 0
        for symbol in symbol_table.symbols:
            assert symbol.line_start > 0
            assert symbol.file_path is not None

    def test_extract_from_source_string(self, temp_dir: Path):
        """Test extracting symbols from source code string."""
        code = '''
def test_func():
    pass

class TestClass:
    def test_method(self):
        pass
'''
        file_path = temp_dir / "source.py"

        extractor = SymbolExtractor()
        symbol_table = extractor.extract_from_source(code, file_path)

        assert symbol_table is not None
        assert len(symbol_table.symbols) > 0
