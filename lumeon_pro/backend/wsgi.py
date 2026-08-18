"""WSGI entrypoint for the Lumeon Pro v2 deployment."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app_v2 import app  # noqa: E402

application = app
