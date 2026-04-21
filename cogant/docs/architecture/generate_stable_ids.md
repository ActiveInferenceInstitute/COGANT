## Generate stable IDs
module_id = resolver.get_id(
    entity_type="module",
    repo_uri="https://github.com/example/repo",
    path="src/mymodule.py",
    qualified_name="myapp.core"
)
