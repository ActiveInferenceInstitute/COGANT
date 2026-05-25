# Agents - app_pkg

## Scope

Application package in the multi-package workspace fixture. It should remain a
thin consumer of `core_pkg` so cross-package dependency edges stay obvious.

## Verification

From the fixture root, `packages.app_pkg.run([1, 2, 3])` should be importable
without external dependencies.
