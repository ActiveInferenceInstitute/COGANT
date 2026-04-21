## Data Flow

### Pipeline Execution

```
┌─ 1. Ingest ─────────────────────────────┐
│ Input: Directory                         │
│ Output: File manifest                    │
│                                          │
│ ├─ Load target codebase                  │
│ ├─ Enumerate files                       │
│ ├─ Detect languages                      │
│ └─ Load configuration                    │
└──┬──────────────────────────────────────┘
   │
   ▼
┌─ 2. Static ─────────────────────────────┐
│ Input: File manifest + source files      │
│ Output: AST + types + symbols per file   │
│                                          │
│ ├─ Extract AST per language              │
│ ├─ Extract types and symbols             │
│ ├─ Resolve imports                       │
│ ├─ Build call graph                      │
│ └─ Compute data flow                     │
└──┬──────────────────────────────────────┘
   │
   ▼
┌─ 3. Normalize ──────────────────────────┐
│ Input: Per-file static analysis          │
│ Output: Canonical entities               │
│                                          │
│ ├─ Normalize cross-language names        │
│ ├─ Resolve identities                    │
│ ├─ De-duplicate entities                 │
│ └─ Merge type information                │
└──┬──────────────────────────────────────┘
   │
   ▼ (Via FFI)
┌─ 4. Graph ──────────────────────────────┐
│ Input: Canonical entities                │
│ Output: Program Graph IR                 │
│                                          │
│ ├─ Create nodes                          │
│ ├─ Add edges                             │
│ ├─ Assign confidence                     │
│ ├─ Track provenance                      │
│ └─ Compute statistics                    │
└──┬──────────────────────────────────────┘
   │
   ▼
┌─ 5. Dynamic (optional, skip_on_error) ──┐
│ Input: Program Graph IR + traces         │
│ Output: Enriched Program Graph IR        │
│                                          │
│ ├─ Load runtime coverage data            │
│ ├─ Load execution traces                 │
│ ├─ Enrich graph with runtime info        │
│ └─ Update edge confidence                │
└──┬──────────────────────────────────────┘
   │
   ▼ (Via FFI)
┌─ 6. Translate ──────────────────────────┐
│ Input: Program Graph IR                  │
│ Output: Translated graph + roles         │
│                                          │
│ ├─ Load rules                            │
│ ├─ Apply via fixpoint iteration          │
│ ├─ Resolve conflicts                     │
│ ├─ Assign semantic roles                 │
│ └─ Update confidence                     │
└──┬──────────────────────────────────────┘
   │
   ▼
┌─ 7. Statespace ─────────────────────────┐
│ Input: Translated graph                  │
│ Output: State Space Model                │
│                                          │
│ ├─ Identify variables                    │
│ ├─ Extract actions                       │
│ ├─ Infer transitions                     │
│ └─ Collect observations                  │
└──┬──────────────────────────────────────┘
   │
   ▼
┌─ 8. Process ────────────────────────────┐
│ Input: State Space Model + graph         │
│ Output: Process Model                    │
│                                          │
│ ├─ Extract stages                        │
│ ├─ Identify connections                  │
│ ├─ Detect patterns                       │
│ └─ Build timeline                        │
└──┬──────────────────────────────────────┘
   │
   ▼ (Via FFI)
┌─ 9. Export ──────────────────────────────┐
│ Input: All IRs + models                  │
│ Output: Artifact bundles                 │
│                                          │
│ ├─ Export JSON                            │
│ ├─ Export GraphML                         │
│ ├─ Export Parquet                         │
│ ├─ Export HTML + Mermaid                  │
│ └─ Generate manifest                     │
└──┬──────────────────────────────────────┘
   │
   ▼
┌─ 10. Validate ──────────────────────────┐
│ Input: All IRs + exported artifacts      │
│ Output: Validation IR                    │
│                                          │
│ ├─ Run integrity checks                  │
│ ├─ Validate schemas                      │
│ ├─ Check provenance                      │
│ ├─ Analyze confidence distribution       │
│ └─ Generate report                       │
└──────────────────────────────────────────┘
```
