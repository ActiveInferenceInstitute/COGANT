## Scoring API

### Drift Analysis

```python
# doctest: +SKIP  # example requires runtime context or external resources
from cogant.scoring import DriftAnalyzer
import json

# Load two bundles
with open("bundle_v1.json") as f:
    data1 = json.load(f)

with open("bundle_v2.json") as f:
    data2 = json.load(f)

# Analyze drift — the analyzer is constructed with both bundles
analyzer = DriftAnalyzer(data1, data2)
score = analyzer.analyze(data1, data2)

# Get scores
print(f"Overall drift: {score.total_score:.2%}")
print(f"Architectural: {score.architectural_score:.2%}")
print(f"Semantic churn: {score.semantic_churn_score:.2%}")

# Get detailed report
print(analyzer.report(score))
```
