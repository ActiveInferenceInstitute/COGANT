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

# 5. Generate site
cogant render analysis_output/bundle.json \
  --output analysis_output/site/

# 6. Open in browser
open analysis_output/site/index.html
```

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
