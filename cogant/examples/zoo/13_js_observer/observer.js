// Zoo/13 — JavaScript Observer fixture.
//
// A tiny JavaScript analogue of zoo/02_observer (Python). The class
// maintains a hidden-state belief distribution, collects observations,
// and exposes a read-only getter plus a cheap invariant check.
//
// Expected COGANT classification (same roles as the Python twin):
//   - constructor        -> HIDDEN_STATE scaffold (initialises belief)
//   - update(obs)        -> mutates internal state, ACTION / POLICY-ish
//   - getState()         -> OBSERVATION (pure getter, "get" prefix)
//   - checkValid()       -> CONSTRAINT (returns a boolean invariant)
//
// Kept deliberately minimal so the cross-language roundtrip claim is
// about structural semantics, not surface features of the language.

class Observer {
  constructor(n_states) {
    this.state = new Array(n_states).fill(1 / n_states);
    this.observations = [];
  }

  update(obs) {
    this.observations.push(obs);
  }

  getState() {
    return this.state;
  }

  checkValid() {
    return this.state.every((s) => s >= 0);
  }
}

module.exports = { Observer };
