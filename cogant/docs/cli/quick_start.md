## Quick Start

```bash
# Initialize a new COGANT project
cogant init my_project

# Scan a repository
cogant scan ./my_repo

# Run the full pipeline (writes output/bundle.json plus stage artifacts)
cogant translate ./my_repo --output output/

# Render interactive site (bundle from translate step)
cogant render output/bundle.json --output output/site/

# Validate results
cogant validate output/bundle.json
```

