import sys
from pathlib import Path

# Allow `from ingest.transform import ...` when running pytest from repo root
ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("ingest", "analytics", "qa"):
    _dir = str(ROOT / _pkg)
    if _dir not in sys.path:
        sys.path.insert(0, _dir)
