from cogant.ingest import RepoIngester

ingester = RepoIngester()
snapshot = ingester.ingest_git_remote(
    "https://github.com/user/repo.git",
    branch="main",
    cleanup=False  # Keep cloned repo
)
