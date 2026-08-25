from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from core.db import get_db
from services.audit_service import record as audit
from services.auth_service import AuthenticationError, current_actor
from services.authorization_service import require
from services.inventory_service import InventoryError, receive_items, reserve_items
from services.sale_delete_service import SaleDeleteError, delete_sale
from services.sale_service import SaleError, create_sale
from services.sale_completion_service import deliver_sale_invoice

sales_api = Blueprint("sales_api", __name__, url_prefix="/api/v2/sales")


def _actor(permission: str):
    actor = current_actor()
    require(actor, permission)
    return actor


def _clean(v):
    return "" if v is None else str(v).strip()


def _normalize_items(conn, items):
    if items is None:
        return None
    if not items:
        raise SaleError("La venta debe contener al menos un producto")

    merged = {}
    for item in items:
        ref = _clean(item.get("referencia"))
        try:
            qty = int(item.get("cantidad", 0))
        except (TypeError, ValueError) as exc:
            raise SaleError("La cantidad debe ser un entero") from exc
        if not ref:
            raise SaleError("Cada producto debe tener referencia")
        if qty <= 0:
            raise SaleError("La cantidad debe ser mayor que cero")
        merged[ref] = merged.get(ref, 0) + qty

    normalized = []
    for ref, qty in merged.items():
        product = conn.execute(
            "SELECT id, referencia, nombre, precio_compra, precio_venta FROM productos WHERE referencia=? LIMIT 1",
            (ref,),
        ).fetchone()
        if not product:
            raise SaleError(f"Producto no encontrado: {ref}")
        normalized.append({
            "producto_id": int(product["id"]),
            "referencia": product["referencia"],
            "nombre": product["nombre"],
            "cantidad": qty,
            "precio_compra": float(product["precio_compra"] or 0),
            "precio_venta": float(product["precio_venta"] or 0),
        })
    return normalized


def _aggregate(items):
    out = {}
    for item in items or []:
        out[item["referencia"]] = out.get(item["referencia"], 0) + int(item["cantidad"])
    return out


def _payment_state(total, paid, requested_state):
    total = float(total or 0)
    paid = max(float(paid or 0), 0)
    requested = _clean(requested_state)

    if requested == "Pagado":
        paid = total
        state = "Pagado"
        payment_state = "Pagado"
    elif requested == "Cancelado":
        state = "Cancelado"
        payment_state = "Cancelado"
    elif paid >= total and total > 0:
        paid = total
        state = "Pagado"
        payment_state = "Pagado"
    elif paid > 0:
        state = "Pendiente"
        payment_state = "Abonado"
    else:
        state = "Pendiente"
        payment_state = "Pendiente"

    return state, payment_state, paid, max(total - paid, 0)


def _detail(conn, sale_id: int):
    sale = conn.execute(
        "SELECT * FROM ventas WHERE id=? LIMIT 1",
        (sale_id,),
    ).fetchone()
    if not sale:
        return None

    items = conn.execute(
        "SELECT * FROM venta_items WHERE venta_id=? ORDER BY id",
        (sale_id,),
    ).fetchall()
    payments = conn.execute(
        """
        SELECT id, venta_id, monto, forma_pago, fecha, usuario_id, nota
        FROM venta_abonos
        WHERE venta_id=?
        ORDER BY fecha ASC, id ASC
        """,
        (sale_id,),
    ).fetchall()
    return {
        "venta": dict(sale),
        "items": [dict(x) for x in items],
        "abonos": [dict(x) for x in payments],
    }


@sales_api.get("")
def list_sales():
    try:
        _actor("read_sale")
        q = _clean(request.args.get("q"))
        conn = get_db()
        try:
            rows = conn.execute(
                """
                SELECT
                    v.*,
                    COALESCE((SELECT COUNT(*) FROM venta_abonos a WHERE a.venta_id=v.id),0) AS abonos_count
                FROM ventas v
                WHERE (?='' OR LOWER(v.numero_factura) LIKE LOWER(?) OR LOWER(COALESCE(v.cliente_nombre,'')) LIKE LOWER(?) OR LOWER(COALESCE(v.cliente_telefono,'')) LIKE LOWER(?))
                ORDER BY v.id DESC
                LIMIT 200
                """,
                (q, f"%{q}%", f"%{q}%", f"%{q}%"),
            ).fetchall()
            return jsonify({"ok": True, "results": [dict(r) for r in rows]})
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)[:500]}), 400


@sales_api.get("/<int:sale_id>")
def get_sale(sale_id: int):
    try:
        _actor("read_sale")
        conn = get_db()
        try:
            detail = _detail(conn, sale_id)
            if not detail:
                return jsonify({"ok": False, "error": "Venta no encontrada"}), 404
            return jsonify({"ok": True, **detail})
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403


@sales_api.post("")
def create_sale_v2():
    try:
        actor = _actor("create_sale")
        data = request.get_json(silent=True) or {}
        initial_payment = float(data.pop("initial_payment", 0) or 0)
        if initial_payment < 0:
            return jsonify({"ok": False, "error": "El abono inicial no puede ser negativo"}), 400

        conn = get_db()
        try:
            sale_id = create_sale(conn, data=data, user_id=int(actor.id))
            sale = conn.execute("SELECT total FROM ventas WHERE id=?", (sale_id,)).fetchone()
            total = float(sale["total"] or 0)
            if initial_payment > total:
                raise SaleError("El abono inicial no puede superar el total de la venta")

            if initial_payment > 0:
                conn.execute(
                    """
                    INSERT INTO venta_abonos (venta_id, monto, forma_pago, fecha, usuario_id, nota)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sale_id,
                        initial_payment,
                        _clean(data.get("forma_pago")) or "Abono",
                        datetime.now(timezone.utc),
                        int(actor.id),
                        "Abono inicial",
                    ),
                )
                state, pstate, paid, balance = _payment_state(total, initial_payment, "Pendiente")
                conn.execute(
                    "UPDATE ventas SET total_abonado=?, saldo_pendiente=?, estado=?, estado_pago=? WHERE id=?",
                    (paid, balance, state, pstate, sale_id),
                )
                audit(
                    conn,
                    actor_id=int(actor.id),
                    action="sale.payment",
                    entity="venta",
                    entity_id=sale_id,
                    details={"monto": initial_payment, "tipo": "initial"},
                )
            conn.commit()
            whatsapp = deliver_sale_invoice(conn, sale_id)
            conn.commit()
            detail = _detail(conn, sale_id)
            return jsonify({"ok": True, "id": sale_id, "whatsapp": whatsapp, **detail}), 201
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except (SaleError, InventoryError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)[:500]}), 400


@sales_api.put("/<int:sale_id>")
def update_sale(sale_id: int):
    try:
        actor = _actor("update_sale")
        data = request.get_json(silent=True) or {}
        conn = get_db()
        try:
            sale = conn.execute("SELECT * FROM ventas WHERE id=? LIMIT 1", (sale_id,)).fetchone()
            if not sale:
                return jsonify({"ok": False, "error": "Venta no encontrada"}), 404

            old_items = conn.execute(
                "SELECT referencia, cantidad, producto_id FROM venta_items WHERE venta_id=? ORDER BY id",
                (sale_id,),
            ).fetchall()
            old_map = {str(x["referencia"]): int(x["cantidad"]) for x in old_items if x["referencia"]}

            new_items = _normalize_items(conn, data.get("items")) if "items" in data else None

            if new_items is not None:
                new_map = _aggregate(new_items)
                delta = {}
                for ref in set(old_map) | set(new_map):
                    d = new_map.get(ref, 0) - old_map.get(ref, 0)
                    if d:
                        delta[ref] = d

                reserve = [{"referencia": ref, "cantidad": d} for ref, d in delta.items() if d > 0]
                release = [{"referencia": ref, "cantidad": -d} for ref, d in delta.items() if d < 0]

                if reserve:
                    reserve_items(conn, reserve)
                if release:
                    receive_items(conn, release)

                conn.execute("DELETE FROM venta_items WHERE venta_id=?", (sale_id,))

                subtotal = 0.0
                profit = 0.0
                for item in new_items:
                    line_total = item["cantidad"] * item["precio_venta"]
                    line_profit = item["cantidad"] * (item["precio_venta"] - item["precio_compra"])
                    subtotal += line_total
                    profit += line_profit
                    conn.execute(
                        """
                        INSERT INTO venta_items
                        (venta_id, producto_id, referencia, nombre, cantidad, precio_compra, precio_venta, subtotal, ganancia)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sale_id,
                            item["producto_id"],
                            item["referencia"],
                            item["nombre"],
                            item["cantidad"],
                            item["precio_compra"],
                            item["precio_venta"],
                            line_total,
                            line_profit,
                        ),
                    )
            else:
                subtotal = float(sale["subtotal"] or sale["total"] or 0)
                profit = float(sale["ganancia"] or 0)

            total = subtotal
            paid_before = float(sale["total_abonado"] or 0)
            requested_state = data.get("estado", sale["estado"])
            state, pstate, paid, balance = _payment_state(total, paid_before, requested_state)

            if _clean(data.get("forma_pago")) == "Abono" and paid == 0 and data.get("initial_payment"):
                initial = float(data.get("initial_payment") or 0)
                if initial > total:
                    raise SaleError("El abono inicial no puede superar el total")
                conn.execute(
                    "INSERT INTO venta_abonos (venta_id, monto, forma_pago, fecha, usuario_id, nota) VALUES (?, ?, ?, ?, ?, ?)",
                    (sale_id, initial, "Abono", datetime.now(timezone.utc), int(actor.id), "Abono de edición"),
                )
                state, pstate, paid, balance = _payment_state(total, initial, "Pendiente")

            fields = {
                "numero_factura": data.get("numero_factura", sale["numero_factura"]),
                "cliente_id": data.get("cliente_id", sale["cliente_id"]),
                "cliente_nombre": data.get("cliente_nombre", sale["cliente_nombre"]),
                "cliente_email": data.get("cliente_email", sale["cliente_email"]),
                "cliente_telefono": data.get("cliente_telefono", sale["cliente_telefono"]),
                "fecha": data.get("fecha", sale["fecha"]),
                "forma_pago": data.get("forma_pago", sale["forma_pago"]),
                "estado": state,
                "estado_pago": pstate,
                "total_abonado": paid,
                "saldo_pendiente": balance,
                "notas": data.get("notas", sale["notas"]),
                "ciclo": data.get("ciclo", sale["ciclo"]),
                "fecha_inicio_ciclo": data.get("fecha_inicio_ciclo", sale["fecha_inicio_ciclo"]),
                "fecha_fin_ciclo": data.get("fecha_fin_ciclo", sale["fecha_fin_ciclo"]),
            }

            conn.execute(
                """
                UPDATE ventas SET
                    numero_factura=?, cliente_id=?, cliente_nombre=?, cliente_email=?, cliente_telefono=?,
                    fecha=?, forma_pago=?, subtotal=?, total=?, ganancia=?, estado=?, estado_pago=?,
                    total_abonado=?, saldo_pendiente=?, notas=?, ciclo=?, fecha_inicio_ciclo=?, fecha_fin_ciclo=?
                WHERE id=?
                """,
                (
                    fields["numero_factura"], fields["cliente_id"], fields["cliente_nombre"], fields["cliente_email"],
                    fields["cliente_telefono"], fields["fecha"], fields["forma_pago"], subtotal, total, profit,
                    fields["estado"], fields["estado_pago"], fields["total_abonado"], fields["saldo_pendiente"],
                    fields["notas"], fields["ciclo"], fields["fecha_inicio_ciclo"], fields["fecha_fin_ciclo"], sale_id,
                ),
            )

            audit(
                conn,
                actor_id=int(actor.id),
                action="sale.updated",
                entity="venta",
                entity_id=sale_id,
                details={
                    "items_changed": new_items is not None,
                    "total": total,
                    "estado": fields["estado"],
                    "estado_pago": fields["estado_pago"],
                    "saldo_pendiente": fields["saldo_pendiente"],
                },
            )
            conn.commit()
            return jsonify({"ok": True, **_detail(conn, sale_id)})
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except (SaleError, InventoryError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)[:500]}), 400


@sales_api.patch("/<int:sale_id>/status")
def update_status(sale_id: int):
    try:
        actor = _actor("update_sale")
        data = request.get_json(silent=True) or {}
        requested = _clean(data.get("estado"))
        if requested not in {"Pendiente", "Pagado", "Cancelado"}:
            return jsonify({"ok": False, "error": "Estado inválido"}), 400
        conn = get_db()
        try:
            sale = conn.execute("SELECT * FROM ventas WHERE id=? LIMIT 1", (sale_id,)).fetchone()
            if not sale:
                return jsonify({"ok": False, "error": "Venta no encontrada"}), 404
            total = float(sale["total"] or 0)
            paid_before = float(sale["total_abonado"] or 0)
            remaining_before = max(total - paid_before, 0)

            state, pstate, paid, balance = _payment_state(
                total,
                paid_before,
                requested,
            )

            if requested == "Pagado" and remaining_before > 0:
                conn.execute(
                    "INSERT INTO venta_abonos (venta_id, monto, forma_pago, fecha, usuario_id, nota) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        sale_id,
                        remaining_before,
                        sale["forma_pago"] or "Contado",
                        datetime.now(timezone.utc),
                        int(actor.id),
                        "Pago total",
                    ),
                )
            conn.execute(
                "UPDATE ventas SET estado=?, estado_pago=?, total_abonado=?, saldo_pendiente=? WHERE id=?",
                (state, pstate, paid, balance, sale_id),
            )
            audit(conn, actor_id=int(actor.id), action="sale.status_changed", entity="venta", entity_id=sale_id,
                  details={"estado": state, "estado_pago": pstate, "total_abonado": paid, "saldo_pendiente": balance})
            conn.commit()
            return jsonify({"ok": True, **_detail(conn, sale_id)})
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)[:500]}), 400


@sales_api.post("/<int:sale_id>/payments")
def add_payment(sale_id: int):
    try:
        actor = _actor("record_payment")
        data = request.get_json(silent=True) or {}
        try:
            amount = float(data.get("monto", 0))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "Monto inválido"}), 400
        if amount <= 0:
            return jsonify({"ok": False, "error": "El abono debe ser mayor que cero"}), 400
        conn = get_db()
        try:
            sale = conn.execute("SELECT * FROM ventas WHERE id=? LIMIT 1", (sale_id,)).fetchone()
            if not sale:
                return jsonify({"ok": False, "error": "Venta no encontrada"}), 404
            total = float(sale["total"] or 0)
            paid = float(sale["total_abonado"] or 0)
            balance = max(total - paid, 0)
            if amount > balance:
                return jsonify({"ok": False, "error": f"El abono no puede superar el saldo pendiente de {balance:.2f}"}), 400
            new_paid = paid + amount
            state, pstate, new_paid, new_balance = _payment_state(total, new_paid, "Pendiente")
            conn.execute(
                "INSERT INTO venta_abonos (venta_id, monto, forma_pago, fecha, usuario_id, nota) VALUES (?, ?, ?, ?, ?, ?)",
                (sale_id, amount, _clean(data.get("forma_pago")) or "Abono", datetime.now(timezone.utc), int(actor.id), _clean(data.get("nota"))),
            )
            conn.execute(
                "UPDATE ventas SET total_abonado=?, saldo_pendiente=?, estado=?, estado_pago=?, forma_pago=? WHERE id=?",
                (new_paid, new_balance, state, pstate, _clean(data.get("forma_pago")) or sale["forma_pago"], sale_id),
            )
            audit(conn, actor_id=int(actor.id), action="sale.payment", entity="venta", entity_id=sale_id,
                  details={"monto": amount, "total_abonado": new_paid, "saldo_pendiente": new_balance})
            conn.commit()
            return jsonify({"ok": True, **_detail(conn, sale_id)})
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)[:500]}), 400


@sales_api.delete("/<int:sale_id>")
def delete_sale_v2(sale_id: int):
    try:
        actor = _actor("delete_sale")
        conn = get_db()
        try:
            result = delete_sale(conn, sale_id=sale_id, user_id=int(actor.id))
            conn.commit()
            return jsonify({"ok": True, **result})
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except SaleDeleteError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)[:500]}), 400
