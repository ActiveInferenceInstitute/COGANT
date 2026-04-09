## ReviewAPI

The `ReviewAPI` provides interactive curation and review functionality.

### Loading a Bundle

```python
from cogant import ReviewAPI

review = ReviewAPI()
review.load_bundle("bundle.json")
```

### Reviewing Mappings

```python
# Get review summary
summary = review.get_review_summary()
# Returns: {
#   "total": 100,
#   "pending": 85,
#   "accepted": 10,
#   "rejected": 5,
#   "edited": 0
# }

# Get pending mappings
pending = review.get_pending_mappings()
for mapping in pending:
    print(f"{mapping.source} → {mapping.target}")
```

### Accepting/Rejecting Mappings

```python
# Accept a mapping
review.accept_mapping("mapping_123", notes="Looks correct")

# Reject a mapping
review.reject_mapping("mapping_456", reason="Incorrect mapping")

# Edit a mapping
review.edit_mapping("mapping_789", target="new_target", confidence=0.95)
```

### Saving Curated Results

```python
# Save curated bundle with review decisions
review.save_curated_bundle("curated_bundle.json")
```

