## Review process (interactive)
for mapping in reviewer.get_unreviewed_mappings():
    if should_accept(mapping):
        reviewer.accept_mapping(mapping.id, "human_reviewer")
    elif should_split(mapping):
        reviewer.split_mapping(mapping.id, "human_reviewer", split_defs)
    else:
        reviewer.reject_mapping(mapping.id, "human_reviewer", reason)

