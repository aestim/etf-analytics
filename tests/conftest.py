import sys
from pathlib import Path

# Allow `from ingest.transform import ...` when running pytest from repo root
ROOT = Path(__file__).resolve().parents[1]
INGEST = ROOT / "ingest"
if str(INGEST) not in sys.path:
    sys.path.insert(0, str(INGEST))
