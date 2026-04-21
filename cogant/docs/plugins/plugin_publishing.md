## Plugin Publishing

To share your plugin:

1. Create a Python package
2. Implement plugin interface
3. Include README with configuration example
4. Add test suite
5. Publish to PyPI (optional)

Example structure:

```
my-cogant-plugin/
├── cogant_my_plugin/
│   ├── __init__.py
│   ├── parser.py
│   ├── rules.py
│   └── tests/
│       ├── test_parser.py
│       └── test_rules.py
├── README.md
├── setup.py
└── examples/
    └── cogant.yaml
```
