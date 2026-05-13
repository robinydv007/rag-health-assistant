import sys
from pathlib import Path

_svc = str(Path(__file__).parent.parent)
if _svc not in sys.path:
    sys.path.insert(0, _svc)
