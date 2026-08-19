from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "lumeon_pro/backend/services/ai_orchestrator.py"

text = AI.read_text(encoding="utf-8")

import_line = "from services.invoice_delivery_service import deliver_invoice\n"
new_import = import_line + "from services.gemini_planner import plan_with_gemini\n"
if "from services.gemini_planner import plan_with_gemini" not in text:
    if import_line not in text:
        raise SystemExit("No encontré el import de invoice_delivery_service")
    text = text.replace(import_line, new_import, 1)

marker = '''    deterministic = _local_command_plan(text)\n    if deterministic:\n        return deterministic\n\n'''
insert = '''    deterministic = _local_command_plan(text)\n    if deterministic:\n        return deterministic\n\n    gemini = plan_with_gemini(text, db_context)\n    if gemini and str(gemini.get("action") or "unknown") != "unknown":\n        return gemini\n\n'''
if marker not in text:
    raise SystemExit("No encontré el bloque de plan()")
text = text.replace(marker, insert, 1)

AI.write_text(text, encoding="utf-8")
print("GEMINI PLANNER ENABLED")
print("No database was touched.")
