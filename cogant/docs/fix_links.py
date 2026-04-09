import os
import re

DOCS_DIR = "/Users/4d/Documents/GitHub/template/projects_in_progress/cogant/cogant/docs"

FILE_TO_FOLDER = {
    "API_GUIDE.md": "api",
    "ARCHITECTURE.md": "architecture",
    "CLI_GUIDE.md": "cli",
    "GNN_EXPORT.md": "export",
    "PLUGIN_API.md": "plugins",
    "ROADMAP.md": "roadmap",
    "SECURITY.md": "security",
    "SPEC.md": "reference",
    "TRANSLATION_RULES.md": "rules",
    "VALIDATION.md": "validation"
}

def update_links(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    original_content = content
    
    # We are inside a subdirectory, e.g. `docs/api/file.md`.
    # A link to `API_GUIDE.md` or `./API_GUIDE.md` should become `../api/README.md`.
    # A link to `#some-header` inside the SAME old monolith might now be broken because the monolith is split.
    # For now, let's fix inter-monolith links.
    for old_file, new_folder in FILE_TO_FOLDER.items():
        # Match `(API_GUIDE.md)` or `(./API_GUIDE.md)` or `(API_GUIDE.md#anchor)`
        pattern = r'\(\.?/?' + re.escape(old_file) + r'(#[^\)]*)?\)'
        
        # Replacement is `../new_folder/README.md`
        # Because we're in `docs_dir/some_folder/file.md`, relative to `docs_dir/new_folder/README.md` is `../new_folder/README.md`
        replacement = r'(../' + new_folder + r'/README.md)'
        
        content = re.sub(pattern, replacement, content)

    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False

# Generate AGENTS.md and fix links
for folder in FILE_TO_FOLDER.values():
    folder_path = os.path.join(DOCS_DIR, folder)
    if not os.path.isdir(folder_path):
        continue
        
    agents_path = os.path.join(folder_path, "AGENTS.md")
    if not os.path.exists(agents_path):
        with open(agents_path, 'w') as f:
            f.write(f"# AGENTS.md — {folder.title()} Module\n\n")
            f.write(f"This directory houses the deeply modularized documentation for the **{folder.title()}** aspects of the COGANT translation engine.\n\n")
            f.write("## Maintenance Rules\n\n")
            f.write("*   **Granularity**: Keep articles focused. Do not reintroduce monolithic, multi-context files.\n")
            f.write("*   **Cross-Linking**: When referencing other modules, link to their respective `../module_name/README.md` indexes.\n")
    
    for filename in os.listdir(folder_path):
        if filename.endswith(".md"):
            filepath = os.path.join(folder_path, filename)
            updated = update_links(filepath)
            if updated:
                print(f"Fixed links in {filepath}")

# Let's also fix links in the root README/AGENTS.md of docs
for r_file in ["README.md", "AGENTS.md"]:
    fp = os.path.join(DOCS_DIR, r_file)
    if os.path.exists(fp):
        # same logic, but we are at the root level docs/
        # so relative is just `./new_folder/README.md`
        with open(fp, 'r') as f:
            content = f.read()
        
        orig = content
        for old_file, new_folder in FILE_TO_FOLDER.items():
            pattern = r'\(\.?/?' + re.escape(old_file) + r'(#[^\)]*)?\)'
            replacement = r'(' + new_folder + r'/README.md)'
            content = re.sub(pattern, replacement, content)
            
        if content != orig:
            with open(fp, 'w') as f:
                f.write(content)
            print(f"Fixed links in {fp}")

