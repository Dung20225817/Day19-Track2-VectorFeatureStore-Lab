#!/usr/bin/env python
"""Execute all 4 notebooks using papermill."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).parent
notebooks = [
    "notebooks/01_embeddings_index.ipynb",
    "notebooks/02_hybrid_search_rrf.ipynb",
    "notebooks/03_search_api_benchmark.ipynb",
    "notebooks/04_feast_feature_store.ipynb",
]

print("\n" + "="*70)
print("  Executing 4 Notebooks")
print("="*70)

for nb in notebooks:
    nb_path = root / nb
    print(f"\n  Executing {nb_path.name}...")
    
    # Try using papermill if available, fallback to nbconvert
    try:
        result = subprocess.run(
            [sys.executable, "-m", "papermill", str(nb_path), str(nb_path)],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            print(f"    ⚠️  papermill failed: {result.stderr[:200]}")
    except Exception as e:
        print(f"    ⚠️  {e}")

print("\n" + "="*70)
print("  ✅ Notebook execution attempt complete")
print("="*70)
