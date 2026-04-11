# Wave 19 — Internal Doc Link Validation

**Agent:** `validate-all-links-agent`
**Date:** 2026-04-10
**Scope:** All Markdown files under `docs/` (excluding `manuscript/` per binding rules).
**Tooling:** Existing `docs/verify_doc_links.py` plus an independent secondary sweep.

## Result

**Status:** PASS — zero dead internal links detected. No file edits required.

| Metric | Value |
| --- | --- |
| Markdown files scanned | 388 |
| Inline internal links checked | 740 |
| Reference-style internal links checked | 0 |
| Dead links | 0 |
| Files edited | 0 |
| Stub files created | 0 |

## Method

1. **Existing verifier (`docs/verify_doc_links.py`)**
   - Walks `docs/**/*.md` (excluding `__pycache__`).
   - Parses `[text](target)` inline links via `_LINK_RE = r"\[[^\]]*\]\(([^)]+)\)"`.
   - Skips fragments-only (`#...`), `mailto:`, `tel:`, and absolute URLs (`http://`, `https://`).
   - Strips angle-bracket wrapping (`<path>`) and trailing fragments (`path#anchor`).
   - Resolves the link relative to the containing file's directory and confirms the target is a file or directory under the package root.
   - **Run:** `uv run python docs/verify_doc_links.py`
   - **Exit code:** `0`
   - **Output:** empty.

2. **Independent secondary sweep (inline matcher)**
   - Same regex semantics as the verifier, re-implemented inline to cross-check.
   - **Files scanned:** 388
   - **Internal links checked:** 740
   - **Dead links:** 0

3. **Reference-style link sweep (`[label]: target`)**
   - Regex: `^\s*\[[^\]]+\]:\s*(\S+)` (multiline).
   - **Reference links checked:** 0 (none used in `docs/`).
   - **Dead reference links:** 0

## Coverage Notes

- `manuscript/` is intentionally untouched per Wave 19 binding rules.
- The verifier resolves both file *and* directory targets, so links pointing at directory READMEs or sub-trees are accepted.
- Anchor fragments (`#section`) are not resolved against actual headings — only the file portion is checked. No anchor-level dead links are reported because anchor validation is out of scope of the existing verifier and was not requested in this wave.
- `__pycache__` directories under `docs/` are skipped (matches verifier behavior).

## Conclusion

The `docs/` tree is internally link-clean as of 2026-04-10. The existing `docs/verify_doc_links.py` (and the secondary sweep) both report zero broken internal Markdown links across 388 files and 740 inline links. No fixes, stubs, or rewrites were required, and no files were modified.

Recommended follow-up (out of scope for this wave): wire `docs/verify_doc_links.py` into CI as a pre-merge gate so link rot is caught at PR time.
