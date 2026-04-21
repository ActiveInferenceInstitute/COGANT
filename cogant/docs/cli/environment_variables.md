## Environment variables

The CLI configures Python `logging` with `INFO` by default in [`main.py`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/cli/main.py). For ad hoc debugging in your own scripts, use:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

There is no separate `COGANT_*` log-level environment variable wired in the library today; set the standard library root logger or configure handlers in application code.
