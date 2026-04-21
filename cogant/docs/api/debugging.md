## Debugging

Enable verbose logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)

# Now all DEBUG messages will be printed
```

The package uses module loggers (e.g. `cogant.api.session`). There is no `COGANT_LOGLEVEL` environment variable in the codebase; configure the root logger or specific loggers as needed.
