## Plugin Configuration

Register plugins in `cogant.yaml`:

```yaml
plugins:
  parsers:
    - path: "plugins/my_parser.py"
      class_name: "MyLanguageParser"
      enabled: true
      config:
        strict_mode: true
  
  rules:
    - path: "plugins/my_rules.py"
      class_name: "MyTranslationRule"
      enabled: true
      priority: 100  # Higher = runs later
  
  validators:
    - path: "plugins/my_validator.py"
      class_name: "MyValidator"
      enabled: true
      config:
        max_complexity: 15
  
  exporters:
    - path: "plugins/my_exporter.py"
      class_name: "MyExporter"
      enabled: true
```

