import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# PythonAnywhere debe cargar primero la configuración privada.
load_dotenv(BACKEND_ROOT / ".env", override=True)

# V2 es ahora la aplicación principal.
# Solo se permite volver a legacy de forma explícita:
# LUMEON_APP_MODE=legacy
mode = os.getenv("LUMEON_APP_MODE", "v2").strip().lower()

if mode == "legacy":
    from app import app as application
else:
    from app_v2 import app as application
