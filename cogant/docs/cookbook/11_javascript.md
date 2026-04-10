# Recipe 11: Scanning JavaScript/TypeScript Projects

**Goal:** Translate a JS/TS project into a GNN state-space model.
**Time:** ~5 minutes.

## Prerequisites

- COGANT installed
- A JavaScript or TypeScript project directory

## Steps

### 1. Check supported file types

COGANT parses these extensions:
`.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx`

Verify your project has recognized files:

```bash
cogant scan ./my-js-project
```

The summary table shows the file count under "Files (ingest)".

### 2. Translate the project

```bash
cogant translate ./my-js-project --output ./js-output --no-dynamic
```

The `--no-dynamic` flag skips coverage/trace analysis, which currently
requires Python-style `.coverage` databases. JS projects should use
this flag unless you have a Cobertura `coverage.xml`.

### 3. Provide JS coverage data (optional)

If you have a Cobertura XML from Istanbul/nyc:

```bash
cogant translate ./my-js-project \
  --output ./js-output \
  --coverage ./my-js-project/coverage/cobertura-coverage.xml
```

### 4. Inspect the results

```bash
cogant validate ./js-output
```

### 5. Mixed Python + JS monorepo

For a monorepo with both languages, scan the root:

```bash
cogant translate ./monorepo --output ./mono-output --no-dynamic
```

COGANT detects both Python and JS/TS files in a single pass.

## Expected output

```
Scanning ./my-js-project
┌──────────────────────┬──────────┐
│ Property             │ Value    │
├──────────────────────┼──────────┤
│ Target               │ ./my-j…  │
│ Type                 │ mixed    │
│ Files (ingest)       │ 87       │
│ Python modules parsed│ 0        │
│ Symbol summary       │ 87       │
└──────────────────────┴──────────┘
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| 0 files ingested | Check file extensions match the supported set above |
| `node_modules` included | COGANT should ignore `node_modules` by default; check `.cogant/config.json` |
| Low symbol count | Complex TS generics may not fully parse; file an issue with a minimal repro |
