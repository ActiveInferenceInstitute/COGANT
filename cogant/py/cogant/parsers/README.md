# parsers (package)

Installable parser registry and language front ends for COGANT. Language-specific
implementations live under [`languages/`](languages/), and callers should select
them through `cogant.parsers` rather than importing implementation paths. See
[`AGENTS.md`](AGENTS.md) and [`languages/README.md`](languages/README.md).
