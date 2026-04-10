# COGANT Example Zoo

Twelve minimal Python repos, each exercising a specific Active Inference / GNN
pattern that the COGANT forward pipeline can detect. Run any repo with
`cogant scan examples/zoo/<name>` to verify non-zero semantic mappings.

| # | Repo | Primary GNN Pattern | Expected Mappings |
|---|------|---------------------|-------------------|
| 01 | `01_simple_state` | Hidden state with update method | HIDDEN_STATE, ACTION |
| 02 | `02_observer` | Observation modality via `observe()` | OBSERVATION |
| 03 | `03_actor` | Action type via `act()` | ACTION |
| 04 | `04_pomdp_minimal` | State + obs + act loop | HIDDEN_STATE, OBSERVATION, ACTION |
| 05 | `05_multi_factor` | Two hidden-state factors | HIDDEN_STATE x2 |
| 06 | `06_hierarchical` | Parent/child state hierarchy | HIDDEN_STATE (nested) |
| 07 | `07_event_driven` | Event bus with handlers | OBSERVATION, ACTION, POLICY |
| 08 | `08_preferences` | Explicit preference/utility | CONSTRAINT |
| 09 | `09_policy` | `select_action` / `select_policy` | POLICY, ACTION |
| 10 | `10_constraint` | Validation and constraint checks | CONSTRAINT |
| 11 | `11_sensor_fusion` | Two observation modalities merged | OBSERVATION x2, ACTION |
| 12 | `12_full_pomdp` | Complete POMDP with all roles | HIDDEN_STATE, OBSERVATION, ACTION, POLICY, CONSTRAINT |

## Design Principles

Each repo is a standalone Python package with no external dependencies beyond
the standard library. The code is written to trigger specific COGANT translation
rules (see `py/cogant/translate/rules/`) through naming conventions, attribute
patterns, and method signatures.

## Usage

```bash
# Scan a single repo
cogant scan examples/zoo/01_simple_state

# Scan all repos
for d in examples/zoo/*/; do cogant scan "$d"; done
```
