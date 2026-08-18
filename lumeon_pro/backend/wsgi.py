"""WSGI entrypoint for the Lumeon Pro v2 deployment."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# PythonAnywhere workers need the production environment loaded before app_v2
# imports settings. The real .env file is ignored by Git and must stay private.
load_dotenv(BACKEND_DIR / ".env")

from app_v2 import app  # noqa: E402

application = app
