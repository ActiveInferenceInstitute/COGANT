# Held-out roundtrip pilot (out-of-sample)

> Exploratory evidence, generated 2026-06-09. **Not** a manuscript claim and not
> injected into any `{{TOKEN}}`: manuscript numbers must come from a registered
> generator (see the project Claim Policy). This directory records a pilot run
> on repositories the translation rules were **not** authored against, to begin
> answering the external-validity caveat in `@sec:08-05-threats-to-validity`.

## What this is

The shipped benchmark fixtures are in-sample: the 22 translation rules and
keyword vocabularies were written with them visible, so their scores *upper-bound*
out-of-sample performance. This pilot runs the same `cogant roundtrip`
(forward → reverse → forward) on three never-tuned external packages and records
the native metrics, to see whether the measures behave out-of-sample as the
manuscript predicts.

## Targets (never-tuned)

| Repo | Ref | Target package |
|------|-----|----------------|
| `tqdm/tqdm` | v4.66.5 | `tqdm/` |
| `dateutil/dateutil` | 2.9.0.post0 | `src/dateutil/` |
| `yaml/pyyaml` | 6.0.2 | `lib/yaml/` |

`requests` is intentionally excluded — a reduction of it (`requests_lib`) is a
shipped fixture, so it is not held out.

## Results

| Target | `role_preservation_score` | `role_preserved` | `structurally_isomorphic` | `matrix_score` | `structural_score` | `generated_code_ok` |
|--------|:--:|:--:|:--:|:--:|:--:|:--:|
| tqdm | 1.0 | yes | **no** | 0.601 | 0.622 | yes |
| dateutil | 1.0 | yes | **no** | 0.658 | 0.583 | yes |
| pyyaml | 1.0 | yes | **no** | 0.600 | 0.642 | yes |

Raw per-target summaries: `rt_tqdm.json`, `rt_dateutil.json`, `rt_pyyaml.json`.

## Honest reading (what this does and does NOT show)

- **It does show robustness:** the pipeline runs end-to-end on three never-tuned
  external repositories, emits a structurally valid bundle, and the reverse
  synthesizer produces code that compiles (`generated_code_ok = yes`) every time.
- **It does NOT show "COGANT generalizes" in any strong sense.** The
  `role_preservation_score` saturates at **1.0** out-of-sample exactly as it does
  in-sample — because role preservation is a coarse symmetric multiset-overlap
  measure that the rule-derived reverse→forward cycle largely preserves by
  construction. A saturating 1.0 is therefore weak evidence, consistent with the
  manuscript's own framing that the score upper-bounds rather than estimates.
- **The harder bar fails out-of-sample too.** `structurally_isomorphic = no` for
  all three (matrix/structural scores ≈ 0.6), mirroring the in-sample
  result that strict isomorphism is confined to the deliberately minimal
  `roundtrip_strict_minimal` fixture. The
  out-of-sample behavior is consistent with the in-sample story, which is the
  most this pilot can honestly support.

**Net:** this is a robustness probe, not an accuracy result. A real
external-validity study still needs human-labeled role ground truth on these
repos (to measure false negatives, false positives, and semantic-role accuracy
against truth rather than roundtrip self-consistency) before any generalization
claim enters the manuscript.

## Reproduce

```bash
mkdir -p /tmp/cogant_heldout && cd /tmp/cogant_heldout
git clone --depth 1 --branch v4.66.5     https://github.com/tqdm/tqdm.git tqdm
git clone --depth 1 --branch 2.9.0.post0 https://github.com/dateutil/dateutil.git dateutil
git clone --depth 1 --branch 6.0.2       https://github.com/yaml/pyyaml.git yaml
cd ~/Documents/GitHub/projects/working/cogant
uv run --directory cogant cogant roundtrip /tmp/cogant_heldout/tqdm/tqdm --json
uv run --directory cogant cogant roundtrip /tmp/cogant_heldout/dateutil/src/dateutil --json
uv run --directory cogant cogant roundtrip /tmp/cogant_heldout/yaml/lib/yaml --json
```
