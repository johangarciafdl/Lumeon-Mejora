from __future__ import annotations

import re
import sqlite3


class CustomerError(ValueError):
    pass


EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def normalize_customer(data: dict) -> dict:
    name = str(data.get("nombre", "")).strip()
    if not name:
        raise CustomerError("El nombre del cliente es obligatorio")
    email = str(data.get("email", "")).strip().lower()
    if email and not EMAIL_RE.fullmatch(email):
        raise CustomerError("El email del cliente no es válido")
    return {
        "nombre": name,
        "documento": str(data.get("documento", "")).strip(),
        "telefono": str(data.get("telefono", "")).strip(),
        "direccion": str(data.get("direccion", "")).strip(),
        "email": email,
        "ciudad": str(data.get("ciudad", "")).strip(),
    }


def create_customer(conn: sqlite3.Connection, data: dict) -> int:
    customer = normalize_customer(data)
    cursor = conn.execute(
        """INSERT INTO clientes (nombre,documento,telefono,direccion,email,ciudad)
        VALUES (?,?,?,?,?,?)""",
        tuple(customer.values()),
    )
    return int(cursor.lastrowid)
