import re
import os
import shutil

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

def to_filename(header):
    # remove ## and strip
    clean = re.sub(r'^#+\s*', '', header).strip()
    # slugify
    clean = re.sub(r'[^a-zA-Z0-9\s-]', '', clean).strip()
    clean = re.sub(r'[\s\-]+', '_', clean).lower()
    return clean + ".md"

def split_file(filepath, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    with open(filepath, "r") as f:
        lines = f.readlines()
        
    sections = []
    current_section = {"header": "index", "lines": []}
    
    for line in lines:
        if line.startswith("## "):
            sections.append(current_section)
            current_section = {"header": line.strip(), "lines": [line]}
        else:
            current_section["lines"].append(line)
    
    sections.append(current_section)
    
    # write sections
    index_lines = []
    for sec in sections:
        header = sec["header"]
        lines = sec["lines"]
        if not lines or all(not l.strip() for l in lines): continue
        
        filename = to_filename(header)
        
        # fix the preamble section
        if header == "index":
            filename = "overview.md"
            header = "Overview"
        
        index_lines.append(f"- [{header}]({filename})")
        with open(os.path.join(out_dir, filename), "w") as f:
            f.writelines(lines)
            
    # write README.md
    with open(os.path.join(out_dir, "README.md"), "w") as f:
        f.write(f"# {os.path.basename(out_dir).title()} Index\n\n")
        f.write("\n".join(index_lines) + "\n")
        
    print(f"Processed {filepath} into {out_dir}")

for file_node, folder in FILE_TO_FOLDER.items():
    filepath = os.path.join(DOCS_DIR, file_node)
    if os.path.exists(filepath):
        out_dir = os.path.join(DOCS_DIR, folder)
        split_file(filepath, out_dir)
        os.remove(filepath)
        print(f"Removed original {filepath}")

