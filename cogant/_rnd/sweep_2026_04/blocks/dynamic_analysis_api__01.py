from cogant.dynamic import TraceIngester

ingester = TraceIngester()

# Parse Chrome DevTools trace
traces = ingester.ingest_chrome_trace("trace.json")

# Extract call sequences
sequences = ingester.extract_call_sequences()

# Extract call graph
call_graph = ingester.extract_call_graph()

# Extract timing
timing = ingester.extract_timing()

# Get hot paths
hot_paths = ingester.extract_hot_paths(count=10)
