# viz.dashboard

HTML dashboard generator and static assets. See [AGENTS.md](AGENTS.md), [../AGENTS.md](../AGENTS.md).

The inference panel reads `inference_trace.json` from the run's data directory
or flat output layout through the canonical source-digest and replay validator.
An absent trace produces an empty panel; a present corrupt or stale trace raises
an error. `inference.py` renders the admitted records, units, source identities,
and model-rollout limitations. The constructor does not accept arbitrary trace
payloads.
