# calculator_js — JavaScript twin of the Python calculator example

This module is the JavaScript counterpart of
`examples/control_positive/calculator/calculator.py`. Both files expose
the same `Calculator` class with identical method names and semantics so
the cross-language differential tests in
`tests/integration/test_cross_lang_differential.py` can confirm that
COGANT produces comparable mappings regardless of source language.

## Equivalence contract

| Element                  | Python                     | JavaScript                 | Expected role          |
| ------------------------ | -------------------------- | -------------------------- | ---------------------- |
| `display`                | `self.display`             | `this.display`             | HIDDEN_STATE           |
| `accumulator`            | `self.accumulator`         | `this.accumulator`         | HIDDEN_STATE           |
| `operation`              | `self.operation`           | `this.operation`           | HIDDEN_STATE           |
| `history`                | `self.history`             | `this.history`             | HIDDEN_STATE           |
| `new_input`              | `self.new_input`           | `this.new_input`           | HIDDEN_STATE           |
| `input_digit`            | method                     | method                     | ACTION                 |
| `input_operation`        | method                     | method                     | ACTION                 |
| `equals`                 | method                     | method                     | ACTION                 |
| `clear`                  | method                     | method                     | ACTION                 |
| `_execute_operation`     | private method             | private method             | HIDDEN_STATE transition|
| `get_display`            | method                     | method                     | OBSERVATION            |
| `get_history`            | method                     | method                     | OBSERVATION            |
| `assert_display`         | method                     | method                     | PREFERENCE             |
| `assert_history_length`  | method                     | method                     | PREFERENCE             |

## Invariants tested

1. **Name overlap** — ≥60% of normalized method/variable names must be
   shared between the two graphs.
2. **Role coverage** — both graphs must produce at least one
   `HIDDEN_STATE`, `OBSERVATION`, and `ACTION` mapping.
3. **Pattern stability** — a pure getter (`get_x`) must be classified
   as `OBSERVATION` in both languages.

The JS file is intentionally dependency-free and uses only
`module.exports` so the tree-sitter JavaScript parser can walk it
without a toolchain.
