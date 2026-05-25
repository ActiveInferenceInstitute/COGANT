# Agents — tests/unit

## Owner
Infra Lead (with subsystem owners responsible for their tests)

## Responsibilities
- Unit test design and maintenance
- Test fixture creation
- Isolated module testing
- Coverage metrics per module

## Coordination
- Each module owner maintains unit tests for their code
- Infra Lead provides testing utilities and CI coordination
- Tests must pass before merge
- File names should describe the subsystem and behavior under test, not the campaign that created them. Avoid generated-era campaign numbers, dated batch tags, and opaque coverage-only suffixes.

## Files
- test_*.py files for each module
- fixtures/ — Test data and mock objects
