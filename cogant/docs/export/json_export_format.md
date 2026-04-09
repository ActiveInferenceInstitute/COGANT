## JSON Export Format

### Structure

```json
{
  "title": "MyProject",
  "statistics": {
    "nodes": 320,
    "edges": 1250,
    "node_kinds": {
      "FUNCTION": 89,
      "VARIABLE": 145,
      ...
    },
    "edge_kinds": {
      "CALLS": 450,
      "USES": 380,
      ...
    }
  },
  "nodes": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "short_id": "fn_process",
      "name": "process",
      "kind": "FUNCTION",
      "role": "FUNCTION_DEF",
      "type_name": "Callable[[list], dict]",
      "confidence": 0.98,
      "attributes": {...},
      "documentation": "..."
    },
    ...
  ],
  "edges": [
    {
      "source": "550e8400-...",
      "target": "550e8401-...",
      "kind": "CALLS",
      "confidence": 0.95,
      "label": "direct_call",
      "attributes": {...}
    },
    ...
  ]
}
```

### Node Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Unique identifier |
| short_id | string | Yes | Human-readable ID |
| name | string | Yes | Entity name |
| kind | string | Yes | NodeKind enum |
| role | string | Yes | SemanticRole enum |
| type_name | string | No | Type annotation |
| confidence | float | Yes | 0.0-1.0 certainty |
| attributes | object | No | Additional properties |
| documentation | string | No | Docstring/comment |

### Edge Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| source | UUID | Yes | Source node ID |
| target | UUID | Yes | Target node ID |
| kind | string | Yes | EdgeKind enum |
| confidence | float | Yes | 0.0-1.0 certainty |
| label | string | No | Semantic label |
| attributes | object | No | Additional properties |

