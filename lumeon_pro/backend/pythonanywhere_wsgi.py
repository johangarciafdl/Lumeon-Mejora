import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_ROOT = os.path.join(PROJECT_ROOT, "backend")
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

# Keep the legacy application as the safe default until endpoint parity is
# complete. PythonAnywhere can switch to the modular stack with
# LUMEON_APP_MODE=v2 without changing source code.
if os.getenv("LUMEON_APP_MODE", "legacy").strip().lower() == "v2":
    from app_v2 import app as application
else:
    from app import app as application
