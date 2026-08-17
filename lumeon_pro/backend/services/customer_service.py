from __future__ import annotations

import re


class CustomerError(ValueError):
    pass


EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def normalize_customer(data: dict) -> dict:
    name = " ".join(str(data.get("nombre", "")).strip().split())
    if len(name) < 2 or len(name) > 120:
        raise CustomerError("El nombre del cliente no es válido")
    email = str(data.get("email", "")).strip().lower()
    if email and not EMAIL_RE.fullmatch(email):
        raise CustomerError("El email del cliente no es válido")
    return {
        "nombre": name,
        "documento": str(data.get("documento", "")).strip()[:50],
        "telefono": str(data.get("telefono", "")).strip()[:30],
        "direccion": str(data.get("direccion", "")).strip()[:180],
        "email": email,
        "ciudad": str(data.get("ciudad", "")).strip()[:100],
    }


def search_customers(conn, term: str, limit: int = 20) -> list[dict]:
    term = str(term or "").strip()
    if not term:
        return []
    limit = max(1, min(int(limit), 100))
    like = f"%{term}%"
    rows = conn.execute(
        "SELECT id,nombre,documento,telefono,direccion,email,ciudad FROM clientes "
        "WHERE nombre ILIKE ? OR documento ILIKE ? OR telefono ILIKE ? OR email ILIKE ? "
        "ORDER BY nombre LIMIT ?",
        (like, like, like, like, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def create_customer(conn, data: dict) -> int:
    customer = normalize_customer(data)
    document = customer["documento"]
    if document:
        existing = conn.execute("SELECT id FROM clientes WHERE documento=?", (document,)).fetchone()
        if existing:
            raise CustomerError("Ya existe un cliente con ese documento")
    row = conn.execute(
        """INSERT INTO clientes (nombre,documento,telefono,direccion,email,ciudad)
        VALUES (?,?,?,?,?,?) RETURNING id""",
        tuple(customer.values()),
    ).fetchone()
    return int(row["id"])
