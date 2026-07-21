import sys
from pathlib import Path

# Allow production modules to be imported the same way their entrypoints do.
ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("ingest", "analytics", "qa", "dashboard"):
    _dir = str(ROOT / _pkg)
    if _dir not in sys.path:
        sys.path.insert(0, _dir)
