# Recipe 1: How to Scan Your First Python Project

**Goal:** Run `cogant scan` on a local Python repository and read the summary table.
**Time:** ~2 minutes.

## Prerequisites

- COGANT installed (`pip install cogant`)
- A Python project directory on disk

## Steps

### 1. Verify the environment

```bash
cogant doctor
```

All checks should pass. If any fail, install the missing dependency
listed in the diagnostic output.

### 2. Initialize COGANT in the project (optional)

```bash
cogant init ./my-project --check
```

This creates a `.cogant/config.json` scaffold and optionally runs
environment diagnostics. Safe to skip if you only want a quick scan.

### 3. Scan the project

```bash
cogant scan ./my-project
```

COGANT runs static-analysis extractors (AST parsing, type inference,
symbol tables) and prints a Rich table:

## Expected output

```
Scanning ./my-project
┌──────────────────────┬──────────┐
│ Property             │ Value    │
├──────────────────────┼──────────┤
│ Target               │ ./my-p…  │
│ Type                 │ python   │
│ Files (ingest)       │ 42       │
│ Python modules parsed│ 38       │
│ Symbol summary       │ 38       │
└──────────────────────┴──────────┘
```

### 4. Get JSON instead of a table

```bash
cogant scan ./my-project --format json
```

This prints the raw analysis result as JSON, useful for piping into
`jq` or other tools.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Error: Repository not found` | Check the path exists and is a directory |
| `Files (ingest): 0` | Ensure the directory contains `.py`, `.js`, or `.ts` files |
| `Permission denied` | Check file read permissions on the repo |
