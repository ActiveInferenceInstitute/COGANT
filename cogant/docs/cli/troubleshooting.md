## Troubleshooting

### ModuleNotFoundError: No module named 'typer'

Install dependencies:
```bash
pip install -r py/requirements.txt
```

### Permission denied when writing output

Ensure output directory is writable:
```bash
chmod 755 output/
```

### Analysis takes too long

Skip unnecessary stages:
```bash
cogant translate ./repo --skip validate
```

Or use benchmarking to identify bottlenecks:
```bash
cogant benchmark ./repo --iterations 1
```
