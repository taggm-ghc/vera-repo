# STUB. The M3 instance's original conftest (FakeLLM(**{"m3.x": ...}), domains()) was accidentally
# overwritten by the M4/M5 instance and must be restored by the M3 owner. M4/M5 tests use
# tests/m45_support.py and do not depend on this file.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
