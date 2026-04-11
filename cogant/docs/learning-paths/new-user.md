# New User — Learning Path

You are new to COGANT and want to understand what it is, install it, run your
first analysis, and know where to look when something is unclear. This path is
the shortest route from "never heard of it" to "scanned my first repository
and read the resulting GNN".

Estimated reading time: ~45 minutes. Estimated hands-on time: ~30 minutes.

## Steps

1. **[Home — What is COGANT?](../index.md)** — One-page tour of the project,
   what problem it solves (translating source code into Active Inference
   generative models), and where the docs live. Read this first to set
   expectations.

2. **[What is a GNN?](../concepts/gnn.md)** — Conceptual primer on the
   Generalized Notation Notation format COGANT emits. You don't need to write
   GNN by hand, but you should know what the output *means* before you generate
   any.

3. **[Installation](../getting-started/installation.md)** — Install the package
   (uv-managed, Python 3.11+). Verify with `cogant --version`. Roughly five
   minutes if your environment is already set up.

4. **[Quick Start Tutorial](../tutorials/01_quickstart.md)** — Your first
   end-to-end run on a tiny example repository. By the end of this tutorial
   you will have produced a GNN file, an HTML report, and a JSON dump.

5. **[Small Repo Walkthrough](../tutorials/02_small_repo_walkthrough.md)** —
   Apply the same workflow to a real (but small) project. This is where the
   abstract concepts from step 2 become concrete: you will see how a real
   codebase becomes a state-space model.

6. **[FAQ](../faq.md)** — When you get stuck, check here first. Common issues,
   "why is X happening?", and pointers into the deeper docs.

## Where to go next

- If you want to **call COGANT from Python code** rather than the CLI, follow
  the [API Consumer](api-consumer.md) path.
- If you want to **understand the active-inference theory** behind the
  translation, follow the [Theory Reader](theory-reader.md) path.
- If you want to **extend COGANT with new languages or rules**, follow the
  [Plugin Author](plugin-author.md) path.
