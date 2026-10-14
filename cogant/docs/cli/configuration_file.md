## Configuration File

`cogant init` creates `.cogant/config.json` in your project. It uses the
canonical `ProjectConfig` sections, so it can be passed straight to
`cogant translate --config .cogant/config.json`:

```json
{
  "schema_version": "1.0",
  "pipeline": {
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
}
```

Values are layered as `defaults < preset < file < environment < CLI`.
Flat legacy keys such as a top-level `output_dir` or `stages` are still
normalized into their sections for one deprecation cycle and emit a
`ConfigMigrationWarning`; unknown keys are rejected.
