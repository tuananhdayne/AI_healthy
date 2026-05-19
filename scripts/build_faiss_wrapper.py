"""Wrapper to run the root `build_faiss.py` from `scripts/` folder.

This file simply imports and runs the existing script to keep root tidy.
"""
from pathlib import Path
import runpy


HERE = Path(__file__).resolve().parent.parent
SCRIPT = HERE / "build_faiss.py"

if __name__ == "__main__":
    if SCRIPT.exists():
        runpy.run_path(str(SCRIPT), run_name="__main__")
    else:
        print("build_faiss.py not found at project root")
