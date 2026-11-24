"""SAKHISAHAY Backend Application Package."""

import sys
from pathlib import Path

# Ensure the parent directory containing 'backend' is in sys.path
_parent_dir = str(Path(__file__).resolve().parent.parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

__version__ = "1.0.0"
