from __future__ import annotations

import re


def parse_fields(text: str) -> dict[str, str]:
    """Parse simple `clave=valor` or `clave: valor` pairs without an LLM."""
    fields: dict[str, str] = {}
    for match in re.finditer(r"([a-zA-Z_áéíóúñ]+)\s*[:=]\s*([^,;|]+)", text):
        key = match.group(1).strip().lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
        fields[key] = match.group(2).strip()
    return fields


def parse_create_customer(text: str) -> dict:
    fields = parse_fields(text)
    if "nombre" not in fields:
        raw = re.sub(r"^registrar\s+cliente\s*", "", text, flags=re.I).strip()
        if raw and not re.search(r"\b(telefono|email|correo|documento|direccion)\s*[:=]", raw, re.I):
            fields["nombre"] = raw
    if "correo" in fields and "email" not in fields:
        fields["email"] = fields.pop("correo")
    return fields


def parse_create_product(text: str) -> dict:
    fields = parse_fields(text)
    return fields
