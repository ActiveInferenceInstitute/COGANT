from cogant.static import SymbolExtractor
from pathlib import Path

extractor = SymbolExtractor(repo_root=Path("."))
table = extractor.extract_from_file(Path("example.py"))

for symbol in table.symbols:
    print(f"{symbol.qualified_name} ({symbol.kind})")
    print(f"  ID: {symbol.id}")
    print(f"  Lines: {symbol.line_start}-{symbol.line_end}")
