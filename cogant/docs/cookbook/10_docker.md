# Recipe 10: Running COGANT in Docker

**Goal:** Run COGANT inside a container for reproducible, isolated builds.
**Time:** ~10 minutes.

## Prerequisites

- Docker installed and running

## Steps

### 1. Create a Dockerfile

```dockerfile
FROM python:3.11-slim

RUN pip install --no-cache-dir cogant

# For PNG export support, install viz extras and system deps
# RUN pip install --no-cache-dir "cogant[viz]" && \
#     apt-get update && apt-get install -y graphviz && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

ENTRYPOINT ["cogant"]
CMD ["--help"]
```

### 2. Build the image

```bash
docker build -t cogant:latest .
```

### 3. Run a scan

Mount your project as a volume:

```bash
docker run --rm -v "$(pwd)/my-project:/workspace/repo:ro" \
  cogant:latest scan /workspace/repo
```

### 4. Run the full pipeline

```bash
docker run --rm \
  -v "$(pwd)/my-project:/workspace/repo:ro" \
  -v "$(pwd)/output:/workspace/output" \
  cogant:latest translate /workspace/repo --output /workspace/output --no-dynamic
```

The output is written to `./output/` on the host.

### 5. Validate the output

```bash
docker run --rm \
  -v "$(pwd)/output:/workspace/output:ro" \
  cogant:latest validate /workspace/output
```

### 6. Run doctor inside the container

```bash
docker run --rm cogant:latest doctor
```

## Expected output

```
COGANT Pipeline
Translating /workspace/repo to GNN...
...
 Translation complete
Output: /workspace/output
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Permission denied on output | Ensure the output volume is writable: remove `:ro` from the output mount |
| Missing graphviz for PNG | Uncomment the `apt-get install graphviz` line in the Dockerfile |
| Slow first run | The image caches pip packages; subsequent builds are fast |
| Dynamic analysis fails | Mount coverage databases alongside the repo, or use `--no-dynamic` |
