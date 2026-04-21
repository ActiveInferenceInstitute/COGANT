## Privacy Protections

### Anonymization

Optional mode to strip personally identifiable information:

```yaml
# cogant.yaml
privacy:
  anonymize: true
  anonymize_names: true      # fn_001, fn_002, ...
  anonymize_paths: true      # /dev/null/...
  strip_documentation: true
  strip_comments: true
  hash_type_names: true
```

### Data Minimization

COGANT stores only semantic information:
- No file contents
- No comments (unless needed for roles)
- No documentation (optional)
- No numeric values except locations
- No external references (unless for dependencies)

### Audit Trail

Optional audit logging:

```yaml
security:
  audit_log: true
  audit_log_file: "audit.log"
  log_config: true
  log_file_access: true
  log_rule_applications: true
```

Logged events:
- File discovery and processing
- Parse errors and warnings
- Rule application decisions
- Export operations
- Time, duration, file paths
