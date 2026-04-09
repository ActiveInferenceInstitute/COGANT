## Contingencies

### If parser for language X is complex

**Option 1**: Use tree-sitter (reduces effort by 50%)  
**Option 2**: Delay language support to next release  
**Option 3**: Community contribution (document API)

### If performance targets unmet

**Optimization**: Profile and optimize bottleneck  
**Fallback**: Parallelize processing or add caching  
**Last resort**: Relax targets, document limitations

### If resources constrained

**Priority 1**: Core Rust library (0.1.0)  
**Priority 2**: Python API (0.2.0)  
**Priority 3**: Documentation (continuous)  
**Defer**: Advanced features, ecosystem

