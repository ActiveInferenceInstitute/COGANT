# 02 Observer

A single observation modality with an `observe()` method. The observer reads
from an external data source without mutating internal state. COGANT should
map the `observe` method to OBSERVATION via the ObservationRule keyword match
on "get"/"read" patterns and the read-only edge structure.
