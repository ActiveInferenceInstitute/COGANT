from cogant.markov.blanket import partition_by_seeds, BlanketRole
from cogant.markov.extractor import MarkovBlanketExtractor

# Extract automatically -- picks the module with best cohesion
extractor = MarkovBlanketExtractor(graph)
blanket = extractor.extract(strategy="auto")

# Inspect the partition
for node_id, role in blanket.roles.items():
    node = graph.get_node(node_id)
    print(f"{node.name}: {role.value}")
    # Output:
    # Calculator: internal
    # get_display: sensory
    # _execute_operation: active
    # __main__: external
