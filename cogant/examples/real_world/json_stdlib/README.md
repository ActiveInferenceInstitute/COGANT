# json_stdlib — CPython Lib/json snapshot

A pristine snapshot of CPython's standard-library `json` package
(`__init__.py`, `decoder.py`, `encoder.py`, `scanner.py`), included as an
integration fixture for the COGANT pipeline.

## Why this fixture

Unlike the hand-written control-positive examples, this code was NOT
authored for COGANT. It is real, battle-tested Python used by every
CPython install in the world — that makes it a useful proxy for "can
the pipeline survive on code written by someone who has never heard of
GNNs or active inference?"

## Patterns exercised

- Classic class-based API (`JSONDecoder`, `JSONEncoder`, `JSONDecodeError`).
- Module-level convenience functions (`loads`, `dumps`, `load`, `dump`)
  that wrap the class instances.
- C-accelerator fallback pattern (`from _json import ...` guarded by
  `try/except ImportError`).
- Extensive use of regex-driven scanners with `re.compile` at
  module-import time.
- Recursive descent parsing via closures and nested functions.
- `__all__` explicit public API surface.

## Provenance

Copied verbatim from CPython 3.11.13 (`Lib/json/`). Licensed under the
PSF license (see CPython distribution). The `tool.py` module, which is
an entry-point script with no class/function shape of interest, is
deliberately omitted so that the fixture focuses on library code rather
than on CLI glue.
