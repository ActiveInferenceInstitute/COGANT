## Step 1: Normalize language-specific facts
normalizer = CanonicalNormalizer()
normalized_facts = [
    normalizer.normalize(fact)
    for fact in raw_facts
]
