# Recipe 3: Explaining Why a Node Got Its Role

**Goal:** Understand why COGANT assigned a specific Active Inference role to a node.
**Time:** ~3 minutes.

## Prerequisites

- COGANT installed
- A Python project with at least a few modules

## Steps

### 1. Scan first to discover node names

```bash
cogant scan ./my-project --format json | jq '.modules[].name'
```

Pick a module or symbol name from the output.

### 2. Explain the node

```bash
cogant explain ./my-project UserService
```

COGANT runs the static pipeline (ingest through translate), resolves
`UserService` to a concrete node, and queries every translation rule
for whether it fired.

### 3. Get JSON output for scripting

```bash
cogant explain ./my-project UserService --format json
```

The JSON includes `rules_fired`, `semantic_kind`, `markov_blanket_role`,
and `edges` for each rule that considered the node.

## Expected output

```
Explaining node: UserService

Rule                  Status     Kind           Role
────────────────────────────────────────────────────
class_with_state      FIRED      hidden_state   mu
method_calls_extern   considered observation    --
imports_io_module     FIRED      sensory        eta

Markov blanket role: mu (internal state)
Confidence: 0.87
```

### 4. Explain with a substring match

You do not need the full node name. A substring works:

```bash
cogant explain ./my-project "User"
```

COGANT resolves the closest matching node.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Node not found` (exit code 2) | Check spelling; use `cogant scan --format json` to list nodes |
| `Pipeline error` (exit code 1) | Ensure the repo path is correct and contains source files |
| Multiple matches | Provide a more specific substring to disambiguate |
