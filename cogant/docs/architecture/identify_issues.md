## Identify issues
low_conf = model.get_low_confidence_mappings(mappings, threshold=0.6)
conflicts = model.get_conflicted_mappings(mappings)
