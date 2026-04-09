## 5. Review
reviewer = ReviewManager()
for mapping in mappings:
    reviewer.add_mapping(mapping)
    if should_accept(mapping):
        reviewer.accept_mapping(mapping.id, "human")

