# 13 JS Observer

JavaScript twin of `zoo/02_observer`. An `Observer` class maintains a
uniform hidden-state belief, accumulates observations, exposes a
read-only `getState()` getter, and offers a boolean `checkValid()`
invariant. The fixture exists to prove that the COGANT forward
pipeline, reverse synthesis, and Active Inference runtime all work on
a non-Python language via the tree-sitter backed JS plugin.

See `docs/evaluation/CROSS_LANG_ROUNDTRIP.md` for the cross-language empirical
claim and measured results.
