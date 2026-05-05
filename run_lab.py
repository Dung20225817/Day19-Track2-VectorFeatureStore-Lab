#!/usr/bin/env python
"""
Day 19 Lab Auto-Execute Script
Runs all 4 notebooks and generates benchmark results.
Run this once pip install completes.
"""
import sys
import subprocess
import time
from pathlib import Path

def run_command(cmd, description, cwd=None):
    """Run a shell command and report status."""
    print(f"\n{'='*70}")
    print(f"  {description}")
    print(f"{'='*70}")
    print(f"  Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or Path.cwd(),
            capture_output=False,
            text=True,
            timeout=600,  # 10 min timeout per command
        )
        if result.returncode == 0:
            print(f"  ✅ SUCCESS")
            return True
        else:
            print(f"  ❌ FAILED (exit code: {result.returncode})")
            return False
    except subprocess.TimeoutExpired:
        print(f"  ❌ TIMEOUT (10 minutes)")
        return False
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False


def main():
    root = Path(__file__).parent
    venv_python = root / ".venv" / "Scripts" / "python.exe"
    
    print("\n" + "="*70)
    print("  Day 19 Lab — Auto-Execute (Lite Path)")
    print("="*70)
    
    steps = [
        {
            "cmd": [str(venv_python), "scripts/seed_corpus.py"],
            "desc": "[1/6] Seed corpus (generate 1000 docs + golden queries)",
            "cwd": root,
        },
        {
            "cmd": [str(root / ".venv" / "Scripts" / "jupytext.exe"), "--to", "notebook", "--update", "notebooks/*.py"],
            "desc": "[2/6] Convert .py notebooks to .ipynb",
            "cwd": root,
        },
        {
            "cmd": [str(venv_python), "-m", "pytest", "app/", "scripts/", "-q"],
            "desc": "[3/6] Run tests",
            "cwd": root,
        },
        {
            "cmd": [str(venv_python), "scripts/benchmark.py"],
            "desc": "[4/6] Benchmark search (keyword/semantic/hybrid + P50/P95/P99)",
            "cwd": root,
        },
        {
            "cmd": [str(venv_python), "-m", "feast.cli", "apply"],
            "desc": "[5/6] Feast apply (register 3 feature views)",
            "cwd": root / "app" / "feast_repo",
        },
    ]
    
    passed = 0
    failed = 0
    
    for i, step in enumerate(steps, 1):
        if run_command(step["cmd"], step["desc"], step.get("cwd")):
            passed += 1
        else:
            failed += 1
            print(f"  ⚠️  Continuing anyway...")
    
    print("\n" + "="*70)
    print(f"  SUMMARY: {passed} passed, {failed} failed")
    print("="*70)
    print("\n  📊 Next: Open Jupyter Lab to see notebook outputs")
    print(f"     .venv\\Scripts\\jupyter lab --notebook-dir=notebooks")
    print("\n  📋 Rubric checklist: See IMPLEMENTATION_GUIDE.md")
    print("="*70 + "\n")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
