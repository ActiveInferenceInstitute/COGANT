## Parse Python setup.py
metadata, deps = parser.parse_setup_py(Path("setup.py"))
print(f"Project: {metadata.get('name')}")
for dep in deps:
    print(f"  {dep.name} ({dep.version or 'any'}) - dev={dep.is_dev}")

