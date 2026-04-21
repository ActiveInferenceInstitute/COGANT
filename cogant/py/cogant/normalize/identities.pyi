from dataclasses import dataclass

@dataclass
class IdentityRecord:
    id: str
    entity_type: str
    repo_uri: str
    path: str | None
    qualified_name: str | None
    hash_inputs: str

class IdentityResolver:
    def __init__(self) -> None: ...
    def generate_id(
        self,
        entity_type: str,
        repo_uri: str,
        path: str | None = None,
        qualified_name: str | None = None,
    ) -> str: ...
    def get_id(
        self,
        entity_type: str,
        repo_uri: str,
        path: str | None = None,
        qualified_name: str | None = None,
    ) -> str: ...
    def lookup_id(
        self,
        entity_type: str,
        repo_uri: str,
        path: str | None = None,
        qualified_name: str | None = None,
    ) -> str | None: ...
    def get_record(self, identity_id: str) -> IdentityRecord | None: ...
    def deduplicate_ids(self, identity_ids: list[str]) -> list[str]: ...
    def generate_edge_id(self, source_id: str, target_id: str, edge_kind: str) -> str: ...
    def get_statistics(self) -> dict[str, int]: ...
    def clear_cache(self) -> None: ...
