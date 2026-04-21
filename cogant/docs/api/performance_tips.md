## Performance Tips

1. **Skip unnecessary stages**: Use `skip_stages` in `PipelineConfig`
2. **Use dynamic analysis selectively**: Only when you have trace data
3. **Cache intermediate results**: Reuse bundles across analyses
4. **Batch operations**: Process multiple bundles with a single script
5. **Monitor memory**: Large graphs require significant memory
