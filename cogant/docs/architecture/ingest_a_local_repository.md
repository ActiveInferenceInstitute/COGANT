## Ingest a local repository
ingester = RepoIngester()
snapshot = ingester.ingest_local(Path("/path/to/repo"))

print(f"Repository: {snapshot.metadata.name}")
print(f"Files: {len(snapshot.files)}")
print(f"Dependencies: {len(snapshot.dependencies)}")
print(f"Language: {snapshot.metadata.language}")

