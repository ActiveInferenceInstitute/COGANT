from cogant.dynamic import CoverageIngester

ingester = CoverageIngester()

# Parse Cobertura XML
coverage = ingester.ingest_coverage_xml("coverage.xml")

# Or parse coverage.py
coverage = ingester.ingest_coverage_py(".coverage")

# Get summary
summary = ingester.get_coverage_summary()

# Map to source spans
spans = ingester.map_coverage_to_spans()
