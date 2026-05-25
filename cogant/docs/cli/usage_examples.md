## Usage Examples

### Complete Workflow

```bash
# 1. Initialize project
cogant init analysis_project

# 2. Scan repository
cogant scan ./source_code

# 3. Run analysis
cogant translate ./source_code \
  --output analysis_output/ \
  --skip ingest

# 4. Validate results
cogant validate analysis_output/bundle.json

# 5. Generate review figures and the artifact-first dashboard
cogant viz analysis_output/

# 6. Generate site
cogant render analysis_output/bundle.json \
  --output analysis_output/site/

# 7. Open in browser
open analysis_output/site/index.html
```

For a complete forward -> reverse -> forward evidence loop:

```bash
cogant translate examples/control_positive/calculator \
  --layout-output \
  --output output/calculator

cogant roundtrip examples/control_positive/calculator \
  --output output/calculator/roundtrip \
  --keep-tmp

cogant viz output/calculator
```

The roundtrip command writes `roundtrip/metrics.json` plus
`roundtrip/rule_evidence_trace.json`; the viz command turns those into the
inspection dashboard, graphical abstract, roundtrip diff, rule trace,
confidence calibration, and deterministic inference trace figures.

### Skip Specific Stages

```bash
# Skip dynamic analysis and process model extraction
cogant translate ./repo --skip dynamic,process --output output/
```

### Compare Two Versions

```bash
# Analyze version 1
cogant translate ./repo_v1 --output output/v1/

# Analyze version 2
cogant translate ./repo_v2 --output output/v2/

# Compare
cogant diff output/v1/bundle.json output/v2/bundle.json
```

### Benchmark Configuration

```bash
# Run 10 benchmarks to test stability
cogant benchmark ./repo --iterations 10
```
