## Compliance

### Standards

- **OWASP Top 10**: Mitigations documented per item
- **CWE**: Avoided common weaknesses (injection, auth, crypto)
- **NIST**: Aligns with information security framework

### Deployment Security

When deploying COGANT in CI/CD:

1. **Run as non-root**: Limit privilege
2. **Limit file access**: Restrict to project directories
3. **Network isolation**: No external network by default
4. **Secret handling**: Use CI/CD secret manager, not env vars
5. **Audit logging**: Enable for compliance
6. **Least privilege**: Only grant needed permissions

### Example: GitHub Actions

```yaml
jobs:
  cogant-analysis:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - uses: actions/checkout@v3

      - name: Run COGANT
        run: |
          cogant translate ./src \
            --config cogant.yaml \
            --output output/
      # COGANT emits JSON bundles by default; upload-sarif expects SARIF. Add a conversion step
      # or use a different security integration before uploading.
      # - name: Upload SARIF
      #   uses: github/codeql-action/upload-sarif@v2
      #   with:
      #     sarif_file: results.sarif
```
