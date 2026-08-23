from __future__ import annotations

from getpass import getpass
import sys

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from core.db import get_db

ENV = "/home/lumeon/lumeon-mejora/lumeon_pro/backend/.env"
USERNAME = "AdminMichelle"
EMAIL = "michelle@lumeon.local"
NAME = "Michelle"


def main() -> int:
    load_dotenv(ENV, override=True)

    password = getpass("Contraseña para AdminMichelle: ")
    confirm = getpass("Repite la contraseña: ")

    if not password:
        print("ERROR: la contraseña no puede estar vacía")
        return 1
    if password != confirm:
        print("ERROR: las contraseñas no coinciden")
        return 1
    if len(password) < 8:
        print("ERROR: usa al menos 8 caracteres")
        return 1

    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id FROM usuarios WHERE username=?",
            (USERNAME,),
        ).fetchone()
        if existing:
            print("ERROR: AdminMichelle ya existe")
            return 2

        row = conn.execute(
            """INSERT INTO usuarios
               (username, password, email, nombre, rol, activo)
               VALUES (?, ?, ?, ?, 'admin', TRUE)
               RETURNING id, username, email, nombre, rol, activo""",
            (
                USERNAME,
                generate_password_hash(password),
                EMAIL,
                NAME,
            ),
        ).fetchone()
        conn.commit()

        print("ADMINMICHELLE CREADO")
        print(dict(row))
        return 0
    except Exception as exc:
        conn.rollback()
        print("ERROR:", type(exc).__name__, str(exc))
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
