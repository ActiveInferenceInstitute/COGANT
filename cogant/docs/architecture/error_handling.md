## Error Handling

### Error Categories

1. **Fatal**: Halt pipeline, require user fix
   - Config file missing
   - Parse error on critical file
   - Schema violation

2. **Error**: Skip component, continue
   - Individual file parse failure
   - Rule application error
   - Format conversion error

3. **Warning**: Log and continue
   - Low confidence detection
   - Partial type info
   - Deprecated usage

4. **Info**: Log only
   - Processing milestones
   - Statistics
   - Optional results

### Error Recovery

- Partial results saved at each stage
- Can resume from last successful stage
- Validation IR tracks completion status
- Error log included in output
