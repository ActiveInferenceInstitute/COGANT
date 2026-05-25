# Code Quality Scripts

Auxiliary staging-root scripts for broad code-quality passes. These scripts are
not package APIs and should stay thin: they may orchestrate checks or local
refactors, but reusable behavior belongs in `tools/` or the inner package.

## Contents

- [`batch_cogsec_improve.py`](batch_cogsec_improve.py) - batch helper for local security/code-quality improvement runs.
