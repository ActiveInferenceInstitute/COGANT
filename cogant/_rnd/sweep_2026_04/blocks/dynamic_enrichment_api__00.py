from cogant.dynamic import enrich_graph, CoverageIngester, TraceIngester
from cogant.schemas.graph import ProgramGraph

# Load or build a program graph
graph: ProgramGraph = session.build_graph()

# Enrich with coverage and/or trace data
summary = enrich_graph(
    graph,
    coverage_path="coverage.xml",
    trace_path="trace.json",
)
# summary contains counts of enriched nodes and inserted edges
print(f"Enriched {summary['nodes_enriched']} nodes, added {summary['edges_added']} dynamic edges")
