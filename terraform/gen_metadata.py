import os
import json

docs_dir = "../data_package/knowledge_base"
files = [f for f in os.listdir(docs_dir) if f.endswith(".md")]

for f in files:
    metadata = {"status": "current"}
    if "archived" in f or "v1" in f:
        metadata["status"] = "archived"
    if "2025" in f:
        metadata["year"] = 2025
    elif "2026" in f:
        metadata["year"] = 2026
        
    with open(os.path.join(docs_dir, f + ".metadata.json"), "w") as jf:
        json.dump({"metadataAttributes": metadata}, jf)

print(f"Generated metadata for {len(files)} files.")
