# Recipe 17: Benchmarking COGANT Performance

**Goal:** Measure pipeline wall-clock performance across several runs.
**Time:** ~5 minutes.

## Prerequisites

- COGANT installed
- A Python or JS/TS project directory

## Steps

### 1. Run the benchmark

```bash
cogant benchmark ./my-project --iterations 5
```

COGANT runs the pipeline 5 times (skipping `export` and `validate`
stages to focus on the translation core) and reports statistics.

### 2. Benchmark static analysis only

```bash
cogant benchmark ./my-project --iterations 5 --no-dynamic
```

The `--no-dynamic` flag skips coverage and trace analysis, measuring
pure static-analysis throughput.

### 3. Compare before and after a change

```bash
# Baseline
cogant benchmark ./my-project -n 3 --no-dynamic > baseline.txt 2>&1

# Make changes, then re-benchmark
cogant benchmark ./my-project -n 3 --no-dynamic > after.txt 2>&1

diff baseline.txt after.txt
```

### 4. Estimate time for a new project

The `init` command provides a rough estimate:

```bash
cogant init ./new-project --check
```

This counts source files and estimates translate time at approximately
50 ms per file.

## Expected output

```
Benchmarking ./my-project (5 runs)

Run 1/5... 2.34s
Run 2/5... 2.21s
Run 3/5... 2.28s
Run 4/5... 2.19s
Run 5/5... 2.25s

Statistics
┌─────────┬────────┐
│ Metric  │ Time   │
├─────────┼────────┤
│ Average │ 2.25s  │
│ Min     │ 2.19s  │
│ Max     │ 2.34s  │
└─────────┴────────┘
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| High variance between runs | Close background processes; use `--no-dynamic` for consistent results |
| Unexpectedly slow | Check file count with `cogant scan`; large repos take longer |
| First run is much slower | JIT/import warmup; discard the first iteration or add 1 extra |
