import os
import re

def generate_directory_structure():
    root_dir = "C:/Users/blpun/Desktop/SafeShe"
    out_file = os.path.join(root_dir, "docs", "2. DIRECTORY_STRUCTURE.md")
    
    ignore_dirs = {'.git', 'node_modules', '.venv', '.vscode', '__pycache__', 'build', 'dist', 'docs', 'tests', 'scratch'}
    
    with open(out_file, "w", encoding="utf-8") as out:
        out.write("# Directory Structure\n\n")
        
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
            
            # Skip root if it's not app or frontend/src and not root itself
            rel_path = os.path.relpath(root, root_dir)
            
            out.write(f"## Folder: `{rel_path}`\n")
            out.write("- **Purpose**: \n")
            out.write(f"- **Contains**: {len(files)} files\n\n")
            
            for file in files:
                if file.endswith(('.pyc', '.zip', '.md', '.log', '.txt')):
                    continue
                if file.startswith('.'):
                    continue
                    
                file_path = os.path.join(root, file)
                rel_file = os.path.relpath(file_path, root_dir)
                size = os.path.getsize(file_path)
                ext = os.path.splitext(file)[1]
                lang = ext[1:] if ext else "Unknown"
                
                imports = []
                exports = []
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        for line in lines:
                            if line.strip().startswith(("import ", "from ")):
                                imports.append(line.strip())
                            if line.strip().startswith("export "):
                                exports.append(line.strip())
                except:
                    pass
                
                out.write(f"### File: `{rel_file}`\n")
                out.write(f"- **Purpose**: \n")
                out.write(f"- **Size**: {size} bytes\n")
                out.write(f"- **Language**: {lang}\n")
                if imports:
                    out.write(f"- **Imports**: {len(imports)} statements\n")
                if exports:
                    out.write(f"- **Exports**: {len(exports)} statements\n")
                out.write("\n")

def trigger_doc_gen():
    import threading
    t = threading.Thread(target=generate_directory_structure)
    t.start()
