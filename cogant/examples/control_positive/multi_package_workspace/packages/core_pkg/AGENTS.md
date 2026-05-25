# Agents - core_pkg

## Scope

Core package in the multi-package workspace fixture. Keep it independent from
`app_pkg` so dependency direction remains one-way.

## Verification

`score([1, 2, 3])` should return the sum of squares and require no optional dependencies.
