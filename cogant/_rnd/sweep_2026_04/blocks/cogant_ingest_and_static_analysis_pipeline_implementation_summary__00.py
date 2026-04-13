from cogant.ingest import RepoIngester

ingester = RepoIngester()
snapshot = ingester.ingest_local("/path/to/repo")

print(f"Repository: {snapshot.metadata.name}")
print(f"Files: {len(snapshot.files)}")
print(f"Language: {snapshot.metadata.language}")
print(f"Dependencies: {len(snapshot.dependencies)}")
