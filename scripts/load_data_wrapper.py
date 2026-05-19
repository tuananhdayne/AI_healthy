"""Wrapper to run the root `load_data.py` from `scripts/` folder.
"""
from pathlib import Path
import runpy


HERE = Path(__file__).resolve().parent.parent
SCRIPT = HERE / "load_data.py"

if __name__ == "__main__":
    if SCRIPT.exists():
        runpy.run_path(str(SCRIPT), run_name="__main__")
    else:
        print("load_data.py not found at project root")
