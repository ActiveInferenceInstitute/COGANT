## API Change Policy

- **Major version changes**: May break API after release-note disclosure.
- **Minor version changes**: Add features or tighten validation without silent artifact rewrites.
- **Patch version changes**: Fix defects and documentation inconsistencies.
- **Removal record**: Removed interfaces are documented in the changelog for the release that removes them.
- **Current artifact contract**: Readers validate current schemas and reject unsupported headers rather than auto-upgrading them.
