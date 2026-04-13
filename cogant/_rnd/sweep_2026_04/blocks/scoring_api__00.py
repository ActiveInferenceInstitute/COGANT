from cogant.scoring import DriftAnalyzer
import json

# Load two bundles
with open("bundle_v1.json") as f:
    data1 = json.load(f)

with open("bundle_v2.json") as f:
    data2 = json.load(f)

# Analyze drift
analyzer = DriftAnalyzer()
score = analyzer.analyze(data1, data2)

# Get scores
print(f"Overall drift: {score.total_score:.2%}")
print(f"Architectural: {score.architectural_score:.2%}")
print(f"Semantic churn: {score.semantic_churn_score:.2%}")

# Get detailed report
print(analyzer.report(score))
