# requests_lib — requests-style HTTP library fixture

A hand-written snapshot of the architectural shape of the venerable
``requests`` library. No network sockets are opened; the transport
adapters are backed by an in-memory route table so the fixture stays
hermetic.

## Files

- `models.py` — ``Request`` / ``PreparedRequest`` / ``Response``
  dataclasses, a case-insensitive header dict, and the exception
  hierarchy (``RequestException`` -> ``HTTPError`` / ``ConnectionError``
  / ``Timeout``).
- `adapters.py` — ``BaseAdapter`` interface, ``HTTPAdapter`` with a
  connection pool shape, ``MockAdapter`` for tests, and a ``MountTable``
  that performs longest-prefix resolution of URL prefixes to adapters.
- `auth.py` — ``AuthBase`` hierarchy with ``NoAuth`` / ``BasicAuth`` /
  ``BearerAuth`` / ``HMACAuth`` / ``RotatingTokenAuth`` and a
  ``build_auth`` factory.
- `sessions.py` — ``Session`` class with cookies, headers, adapters,
  response hooks, and a ``request()`` pipeline
  (prepare -> auth -> hooks -> send).
- `utils.py` — URL parsing, ``STATUS_CODES`` table, and
  ``is_success`` / ``is_redirect`` / ``is_client_error`` helpers.

## Why a stub instead of vendoring requests?

``requests`` drags in ``urllib3``, ``chardet``, ``idna`` and ``certifi``
as runtime dependencies. Vendoring all of that would be noisy and
brittle — this stub keeps the pipeline focused on architectural
patterns (polymorphic adapters, stateful session, response hooks,
auth callables) rather than transport minutiae.
