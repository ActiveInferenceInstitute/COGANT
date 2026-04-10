# Recipe 5: Running COGANT on a Monorepo

**Goal:** Translate multiple packages inside a single monorepo.
**Time:** ~10 minutes.

## Prerequisites

- COGANT installed
- A monorepo with several Python or JS/TS packages

## Steps

### 1. Identify the packages

```bash
ls -d ./monorepo/packages/*/
```

Assume the layout is:

```
monorepo/
  packages/
    auth/
    billing/
    gateway/
```

### 2. Initialize each package

```bash
for pkg in ./monorepo/packages/*/; do
  cogant init "$pkg" --quiet
done
```

### 3. Translate each package independently

```bash
for pkg in ./monorepo/packages/*/; do
  name=$(basename "$pkg")
  echo "--- Translating $name ---"
  cogant translate "$pkg" --output "./output/$name"
done
```

Each package gets its own output directory with a separate `bundle.json`.

### 4. Validate all outputs

```bash
for dir in ./output/*/; do
  echo "--- Validating $(basename "$dir") ---"
  cogant validate "$dir"
done
```

### 5. Compare packages pairwise (optional)

```bash
cogant diff ./output/auth ./output/billing
```

## Expected output

Each package produces a pipeline summary table and a `bundle.json`.
The diff command shows structural differences between packages,
which is useful for detecting shared patterns or drift across services.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Some packages fail with 0 files | Ensure each directory contains source files; check `.cogant/config.json` target path |
| Shared code not resolved | COGANT scans each directory independently; shared libraries need their own scan |
| Output directories collide | Use `--output "./output/$(basename $pkg)"` to namespace by package |
