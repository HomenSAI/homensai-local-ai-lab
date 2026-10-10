"""Shared helpers: import the project's scripts and the console from a plain `python -m unittest discover -s tests`."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "console", ROOT / "scripts"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))
