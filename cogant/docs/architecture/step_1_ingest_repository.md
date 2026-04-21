## Step 1: Ingest repository
ingester = RepoIngester()
snapshot = ingester.ingest_local(Path("/path/to/repo"))

print(f"Repository: {snapshot.metadata.name}")
print(f"Language: {snapshot.metadata.language}")
print(f"Files: {len(snapshot.files)}")
print(f"Dependencies: {len(snapshot.dependencies)}")
