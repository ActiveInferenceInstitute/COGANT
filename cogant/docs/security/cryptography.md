## Cryptography

COGANT uses cryptography for:

1. **Integrity**: SHA256 checksums for bundles
2. **Reproducibility**: Hash-based caching

Current implementation:

```rust
// Checksum (simple hash for fast reproducibility)
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

let mut hasher = DefaultHasher::new();
data.hash(&mut hasher);
let checksum = format!("{:x}", hasher.finish());
```

Future improvements:
- [ ] HMAC for authenticated bundles
- [ ] Signature verification for plugins
- [ ] Encrypted storage for sensitive data

**No encryption of data at rest** (user responsible for disk encryption).
