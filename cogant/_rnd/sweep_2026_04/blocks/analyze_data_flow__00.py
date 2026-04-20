from cogant.static import SymbolExtractor
from pathlib import Path

source = """
def hello(name: str) -> str:
    return f"Hello, {name}!"

class Greeter:
    def greet(self, name: str) -> str:
        return f"Hi, {name}!"
"""

extractor = SymbolExtractor()
table = extractor.extract_from_source(source, Path("example.py"))
