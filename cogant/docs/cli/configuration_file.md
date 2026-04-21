## Configuration File

Create `.cogant/config.json` in your project:

```json
{
  "version": "0.1.0",
  "name": "my_analysis",
  "target": ".",
  "output_dir": "output",
  "stages": [
    "ingest",
    "static",
    "normalize",
    "graph",
    "translate",
    "statespace",
    "process",
    "export",
    "validate"
  ]
}
```
