from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "lumeon_pro/backend/services/ai_orchestrator.py"

text = AI.read_text(encoding="utf-8")

old = '''def _product(conn, ref):
    ref = str(ref or "").strip()
    return conn.execute(
        "SELECT * FROM productos WHERE referencia=? OR CAST(id AS TEXT)=? LIMIT 1",
        (ref, ref),
    ).fetchone() if ref else None
'''

new = '''def _product(conn, ref):
    """Resolve a product by reference, numeric id, exact name, or name fragment.

    The assistant may identify a product using natural language. Never trust
    model-provided price/stock; only use the returned database row.
    """
    ref = " ".join(str(ref or "").strip().split())
    if not ref:
        return None

    row = conn.execute(
        "SELECT * FROM productos WHERE referencia=? OR CAST(id AS TEXT)=? LIMIT 1",
        (ref, ref),
    ).fetchone()
    if row:
        return row

    row = conn.execute(
        "SELECT * FROM productos WHERE LOWER(TRIM(nombre))=LOWER(TRIM(?)) LIMIT 1",
        (ref,),
    ).fetchone()
    if row:
        return row

    # Natural-language names can include extra words. Keep resolution
    # deterministic: prefer a unique partial-name match and reject ambiguity.
    rows = conn.execute(
        "SELECT * FROM productos WHERE LOWER(nombre) LIKE LOWER(?) ORDER BY id",
        (f"%{ref}%",),
    ).fetchall()
    if len(rows) == 1:
        return rows[0]
    return None
'''

if old not in text:
    raise SystemExit("No encontre la funcion _product esperada")

text = text.replace(old, new, 1)
AI.write_text(text, encoding="utf-8")
print("AI PRODUCT RESOLUTION FIXED")
print("Natural-language product names now resolve to the real database product.")
print("Reference/id matching remains first priority.")
print("No database was touched.")
