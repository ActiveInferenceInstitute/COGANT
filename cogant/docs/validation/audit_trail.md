## Audit Trail

Validation creates immutable audit log:

```json
{
  "audit_log": [
    {
      "timestamp": "2024-10-01T12:00:00Z",
      "stage": "discovery",
      "status": "SUCCESS",
      "duration_seconds": 1.2,
      "output_size_bytes": 45000
    },
    {
      "timestamp": "2024-10-01T12:00:01Z",
      "stage": "parsing",
      "status": "SUCCESS",
      "duration_seconds": 30.5,
      "files_processed": 42,
      "errors": 0
    },
    {
      "timestamp": "2024-10-01T12:00:32Z",
      "stage": "graph",
      "status": "SUCCESS",
      "duration_seconds": 2.1,
      "nodes_created": 320,
      "edges_created": 1250
    }
  ]
}
```

---

