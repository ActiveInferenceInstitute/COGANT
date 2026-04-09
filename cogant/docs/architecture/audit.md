## Audit
history = manager.get_review_history()
```

---

### Complete Example: End-to-End Translation

```python
from cogant.normalize.identities import IdentityResolver
from cogant.normalize.canonical import CanonicalNormalizer, LanguageFact
from cogant.graph.builder import ProgramGraphBuilder
from cogant.graph.queries import GraphQuery
from cogant.graph.merge import GraphMerger
from cogant.translate.engine import TranslationEngine
from cogant.translate.rules import *
from cogant.translate.confidence import ConfidenceModel
from cogant.translate.review import ReviewManager

