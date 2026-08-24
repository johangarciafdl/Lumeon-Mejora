from __future__ import annotations

from datetime import datetime

from flask import Blueprint, jsonify, request, session

from core.db import get_db
from services.auth_service import AuthenticationError, current_actor
from services.authorization_service import require
from services.customer_service import create_customer, search_customers
from services.product_service import create_product, search_products
from services.sale_service import SaleError, create_sale
from services.audit_service import record as audit
from services.sale_delete_service import SaleDeleteError, delete_sale
from services.return_service import ReturnError, return_sale
from services.sale_completion_service import deliver_sale_invoice

legacy_compat_api = Blueprint("legacy_compat_api", __name__, url_prefix="/api")


def actor(permission: str | None = None):
    a = current_actor()
    if permission:
        require(a, permission)
    return a


@legacy_compat_api.get("/current-user")
def current_user_compat():
    try:
        a = current_actor()
        return jsonify({
            "ok": True,
            "user": {
                "id": a.id,
                "username": "AdminJohan",
                "role": a.role,
            },
        })
    except AuthenticationError:
        return jsonify({"ok": False, "user": None}), 401


@legacy_compat_api.post("/logout")
def logout_compat():
    session.clear()
    return jsonify({"ok": True})


@legacy_compat_api.get("/dashboard")
def dashboard():
    try:
        actor("read_sale")
        conn = get_db()
        try:
            today = datetime.now().date().isoformat()
            month = datetime.now().strftime("%Y-%m")
            year = datetime.now().strftime("%Y")

            ventas_hoy = conn.execute(
                "SELECT COALESCE(SUM(total),0) FROM ventas WHERE substr(fecha,1,10)=?",
                (today,),
            ).fetchone()[0]

            ventas_mes = conn.execute(
                "SELECT COALESCE(SUM(total),0) FROM ventas WHERE substr(fecha,1,7)=?",
                (month,),
            ).fetchone()[0]

            ganancia_mes = conn.execute(
                "SELECT COALESCE(SUM(ganancia),0) FROM ventas WHERE substr(fecha,1,7)=?",
                (month,),
            ).fetchone()[0]

            pendientes = conn.execute(
                "SELECT COUNT(*) FROM ventas WHERE estado='Pendiente'"
            ).fetchone()[0]

            pagadas = conn.execute(
                "SELECT COUNT(*) FROM ventas WHERE estado='Pagado'"
            ).fetchone()[0]

            sin_stock = conn.execute(
                "SELECT COUNT(*) FROM productos WHERE stock<=0"
            ).fetchone()[0]

            stock_bajo = conn.execute(
                "SELECT COUNT(*) FROM productos WHERE stock>0 AND stock<=stock_minimo"
            ).fetchone()[0]

            total_clientes = conn.execute(
                "SELECT COUNT(*) FROM clientes"
            ).fetchone()[0]

            total_productos = conn.execute(
                "SELECT COUNT(*) FROM productos"
            ).fetchone()[0]

            alertas = conn.execute("""
                SELECT nombre, referencia, stock
                FROM productos
                WHERE stock<=stock_minimo
                ORDER BY stock ASC, nombre
                LIMIT 20
            """).fetchall()

            recientes = conn.execute("""
                SELECT numero_factura, cliente_nombre, total, estado, fecha
                FROM ventas
                ORDER BY id DESC
                LIMIT 10
            """).fetchall()

            ventas_por_mes = conn.execute("""
                SELECT substr(fecha,6,2) AS mes, COALESCE(SUM(total),0) AS total
                FROM ventas
                WHERE substr(fecha,1,4)=?
                GROUP BY substr(fecha,6,2)
                ORDER BY mes
            """, (year,)).fetchall()

            return jsonify({
                "ok": True,
                "ventas_hoy": float(ventas_hoy or 0),
                "ventas_mes": float(ventas_mes or 0),
                "ganancia_mes": float(ganancia_mes or 0),
                "pendientes": int(pendientes or 0),
                "pagadas": int(pagadas or 0),
                "sin_stock": int(sin_stock or 0),
                "stock_bajo": int(stock_bajo or 0),
                "total_clientes": int(total_clientes or 0),
                "total_productos": int(total_productos or 0),
                "alertas_stock": [dict(r) for r in alertas],
                "ultimas_ventas": [dict(r) for r in recientes],
                "ventas_por_mes": [dict(r) for r in ventas_por_mes],
            })
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403


@legacy_compat_api.get("/productos")
def productos():
    try:
        actor("read_product")
        q = (request.args.get("q") or "").strip()
        conn = get_db()
        try:
            return jsonify(search_products(conn, q))
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403


@legacy_compat_api.get("/productos/buscar/<ref>")
def buscar_producto(ref: str):
    try:
        actor("read_product")
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT * FROM productos WHERE referencia=?",
                (ref.strip(),),
            ).fetchone()
            return jsonify(dict(row) if row else {})
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403


@legacy_compat_api.post("/productos")
def crear_producto():
    try:
        actor("create_product")
        conn = get_db()
        try:
            product_id = create_product(conn, request.get_json(silent=True) or {})
            conn.commit()
            return jsonify({"ok": True, "id": product_id}), 201
        finally:
            conn.close()
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@legacy_compat_api.get("/clientes")
def clientes():
    try:
        actor("read_customer")
        q = (request.args.get("q") or "").strip()
        conn = get_db()
        try:
            return jsonify(search_customers(conn, q, 100))
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403


@legacy_compat_api.post("/clientes")
def crear_cliente():
    try:
        actor("create_customer")
        conn = get_db()
        try:
            customer_id = create_customer(conn, request.get_json(silent=True) or {})
            conn.commit()
            return jsonify({
                "ok": True,
                "id": customer_id,
            }), 201
        finally:
            conn.close()
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@legacy_compat_api.get("/ventas")
def ventas():
    try:
        actor("read_sale")
        q = (request.args.get("q") or "").strip()
        estado = (request.args.get("estado") or "").strip()
        conn = get_db()
        try:
            rows = conn.execute("""
                SELECT *
                FROM ventas
                WHERE (?='' OR numero_factura LIKE ? OR cliente_nombre LIKE ?)
                  AND (?='' OR estado=?)
                ORDER BY id DESC
                LIMIT 200
            """, (
                q, f"%{q}%", f"%{q}%",
                estado, estado,
            )).fetchall()
            return jsonify([dict(r) for r in rows])
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403


@legacy_compat_api.post("/ventas")
def crear_venta():
    try:
        a = actor("create_sale")
        conn = get_db()
        try:
            data = request.get_json(silent=True) or {}
            sale_id = create_sale(conn, data=data, user_id=int(a.id))
            conn.commit()
            whatsapp = deliver_sale_invoice(conn, sale_id)
            conn.commit()
            return jsonify({"ok": True, "id": sale_id, "whatsapp": whatsapp}), 201
        finally:
            conn.close()
    except SaleError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403






# LUMEON SALES MANAGEMENT V2

def _ensure_sale_payments_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS venta_abonos (
            id INTEGER,
            venta_id INTEGER NOT NULL,
            monto NUMERIC(12,2) NOT NULL,
            forma_pago TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            usuario_id INTEGER,
            nota TEXT
        )
    """)


def _sale_payment_state(total, total_abonado, requested_state):
    total = float(total or 0)
    total_abonado = float(total_abonado or 0)

    saldo = max(total - total_abonado, 0)

    requested = str(requested_state or "").strip()

    if requested == "Pagado":
        total_abonado = total
        saldo = 0
        estado = "Pagado"
        estado_pago = "Pagado"

    elif requested == "Cancelado":
        estado = "Cancelado"
        estado_pago = "Cancelado"

    elif saldo <= 0:
        estado = "Pagado"
        estado_pago = "Pagado"

    elif total_abonado > 0:
        estado = "Pendiente"
        estado_pago = "Abonado"

    else:
        estado = "Pendiente"
        estado_pago = "Pendiente"

    return (
        estado,
        estado_pago,
        total_abonado,
        saldo,
    )


@legacy_compat_api.put("/ventas/<int:sale_id>")
def actualizar_venta(sale_id: int):
    try:
        a = actor("update_sale")
        data = request.get_json(silent=True) or {}

        conn = get_db()

        try:
            sale = conn.execute(
                "SELECT * FROM ventas WHERE id=? LIMIT 1",
                (sale_id,),
            ).fetchone()

            if not sale:
                return jsonify({
                    "ok": False,
                    "error": "Venta no encontrada",
                }), 404

            allowed = {
                "cliente_id",
                "cliente_nombre",
                "cliente_email",
                "cliente_telefono",
                "fecha",
                "forma_pago",
                "estado",
                "notas",
                "ciclo",
                "fecha_inicio_ciclo",
                "fecha_fin_ciclo",
            }

            updates = {
                key: data[key]
                for key in allowed
                if key in data
            }

            if not updates:
                return jsonify({
                    "ok": False,
                    "error": "No hay cambios para guardar",
                }), 400

            estado_requested = updates.get(
                "estado",
                sale["estado"],
            )

            total_abonado = float(
                sale["total_abonado"] or 0
            )

            (
                estado,
                estado_pago,
                total_abonado,
                saldo_pendiente,
            ) = _sale_payment_state(
                sale["total"],
                total_abonado,
                estado_requested,
            )

            conn.execute(
                """
                UPDATE ventas
                SET
                    cliente_id=?,
                    cliente_nombre=?,
                    cliente_email=?,
                    cliente_telefono=?,
                    fecha=?,
                    forma_pago=?,
                    estado=?,
                    estado_pago=?,
                    total_abonado=?,
                    saldo_pendiente=?,
                    notas=?,
                    ciclo=?,
                    fecha_inicio_ciclo=?,
                    fecha_fin_ciclo=?,
                    num_ediciones=COALESCE(num_ediciones,0)+1
                WHERE id=?
                """,
                (
                    updates.get(
                        "cliente_id",
                        sale["cliente_id"],
                    ),
                    updates.get(
                        "cliente_nombre",
                        sale["cliente_nombre"],
                    ),
                    updates.get(
                        "cliente_email",
                        sale["cliente_email"],
                    ),
                    updates.get(
                        "cliente_telefono",
                        sale["cliente_telefono"],
                    ),
                    updates.get(
                        "fecha",
                        sale["fecha"],
                    ),
                    updates.get(
                        "forma_pago",
                        sale["forma_pago"],
                    ),
                    estado,
                    estado_pago,
                    total_abonado,
                    saldo_pendiente,
                    updates.get(
                        "notas",
                        sale["notas"],
                    ),
                    updates.get(
                        "ciclo",
                        sale["ciclo"],
                    ),
                    updates.get(
                        "fecha_inicio_ciclo",
                        sale["fecha_inicio_ciclo"],
                    ),
                    updates.get(
                        "fecha_fin_ciclo",
                        sale["fecha_fin_ciclo"],
                    ),
                    sale_id,
                ),
            )

            audit(
                conn,
                actor_id=int(a.id),
                action="sale.updated",
                entity="venta",
                entity_id=sale_id,
                details={
                    "fields": sorted(updates.keys()),
                    "estado": estado,
                    "estado_pago": estado_pago,
                    "ciclo": updates.get(
                        "ciclo",
                        sale["ciclo"],
                    ),
                    "fecha": updates.get(
                        "fecha",
                        sale["fecha"],
                    ),
                },
            )

            conn.commit()

            return jsonify({
                "ok": True,
                "id": sale_id,
                "estado": estado,
                "estado_pago": estado_pago,
                "total_abonado": total_abonado,
                "saldo_pendiente": saldo_pendiente,
            })

        finally:
            conn.close()

    except (AuthenticationError, PermissionError) as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
        }), 403

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)[:500],
        }), 400


@legacy_compat_api.patch("/ventas/<int:sale_id>/estado")
def cambiar_estado_venta(sale_id: int):
    try:
        a = actor("update_sale")
        data = request.get_json(silent=True) or {}

        estado_requested = str(
            data.get("estado") or ""
        ).strip()

        if estado_requested not in {
            "Pendiente",
            "Pagado",
            "Cancelado",
        }:
            return jsonify({
                "ok": False,
                "error": "Estado inválido",
            }), 400

        conn = get_db()

        try:
            sale = conn.execute(
                "SELECT * FROM ventas WHERE id=? LIMIT 1",
                (sale_id,),
            ).fetchone()

            if not sale:
                return jsonify({
                    "ok": False,
                    "error": "Venta no encontrada",
                }), 404

            previous_paid = float(
                sale["total_abonado"] or 0
            )

            remaining = max(
                float(sale["total"] or 0) - previous_paid,
                0,
            )

            # Al marcar Pagado, si había saldo pendiente,
            # registramos automáticamente ese pago final.
            if (
                estado_requested == "Pagado"
                and remaining > 0
            ):
                _ensure_sale_payments_table(conn)

                max_id = conn.execute(
                    "SELECT COALESCE(MAX(id),0)+1 FROM venta_abonos"
                ).fetchone()[0]

                conn.execute(
                    """
                    INSERT INTO venta_abonos
                        (id, venta_id, monto, forma_pago,
                         usuario_id, nota)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(max_id),
                        sale_id,
                        remaining,
                        sale["forma_pago"],
                        int(a.id),
                        "Pago total manual",
                    ),
                )

                previous_paid += remaining

            (
                estado,
                estado_pago,
                total_abonado,
                saldo_pendiente,
            ) = _sale_payment_state(
                sale["total"],
                previous_paid,
                estado_requested,
            )

            conn.execute(
                """
                UPDATE ventas
                SET
                    estado=?,
                    estado_pago=?,
                    total_abonado=?,
                    saldo_pendiente=?,
                    num_ediciones=COALESCE(num_ediciones,0)+1
                WHERE id=?
                """,
                (
                    estado,
                    estado_pago,
                    total_abonado,
                    saldo_pendiente,
                    sale_id,
                ),
            )

            audit(
                conn,
                actor_id=int(a.id),
                action="sale.status_changed",
                entity="venta",
                entity_id=sale_id,
                details={
                    "estado": estado,
                    "estado_pago": estado_pago,
                    "total_abonado": total_abonado,
                    "saldo_pendiente": saldo_pendiente,
                },
            )

            conn.commit()

            return jsonify({
                "ok": True,
                "id": sale_id,
                "estado": estado,
                "estado_pago": estado_pago,
                "total_abonado": total_abonado,
                "saldo_pendiente": saldo_pendiente,
            })

        finally:
            conn.close()

    except (AuthenticationError, PermissionError) as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
        }), 403

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)[:500],
        }), 400


@legacy_compat_api.get("/ventas/<int:sale_id>/abonos")
def listar_abonos(sale_id: int):
    try:
        actor("read_sale")

        conn = get_db()

        try:
            _ensure_sale_payments_table(conn)

            rows = conn.execute(
                """
                SELECT
                    id,
                    venta_id,
                    monto,
                    forma_pago,
                    fecha,
                    usuario_id,
                    nota
                FROM venta_abonos
                WHERE venta_id=?
                ORDER BY fecha ASC, id ASC
                """,
                (sale_id,),
            ).fetchall()

            total = conn.execute(
                """
                SELECT
                    total,
                    total_abonado,
                    saldo_pendiente,
                    estado,
                    estado_pago
                FROM ventas
                WHERE id=?
                """,
                (sale_id,),
            ).fetchone()

            if not total:
                return jsonify({
                    "ok": False,
                    "error": "Venta no encontrada",
                }), 404

            return jsonify({
                "ok": True,
                "results": [dict(r) for r in rows],
                "total": float(total["total"] or 0),
                "total_abonado": float(
                    total["total_abonado"] or 0
                ),
                "saldo_pendiente": float(
                    total["saldo_pendiente"] or 0
                ),
                "estado": total["estado"],
                "estado_pago": total["estado_pago"],
            })

        finally:
            conn.close()

    except (AuthenticationError, PermissionError) as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
        }), 403

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)[:500],
        }), 400


@legacy_compat_api.post("/ventas/<int:sale_id>/abonos")
def registrar_abono(sale_id: int):
    try:
        a = actor("record_payment")
        data = request.get_json(silent=True) or {}

        try:
            monto = float(
                data.get("monto")
                if data.get("monto") is not None
                else data.get("amount")
            )
        except (TypeError, ValueError):
            return jsonify({
                "ok": False,
                "error": "Monto de abono inválido",
            }), 400

        if monto <= 0:
            return jsonify({
                "ok": False,
                "error": "El abono debe ser mayor que cero",
            }), 400

        conn = get_db()

        try:
            _ensure_sale_payments_table(conn)

            sale = conn.execute(
                "SELECT * FROM ventas WHERE id=? LIMIT 1",
                (sale_id,),
            ).fetchone()

            if not sale:
                return jsonify({
                    "ok": False,
                    "error": "Venta no encontrada",
                }), 404

            total = float(sale["total"] or 0)
            anterior = float(
                sale["total_abonado"] or 0
            )
            saldo_anterior = max(
                total - anterior,
                0,
            )

            if saldo_anterior <= 0:
                return jsonify({
                    "ok": False,
                    "error": "La venta ya está totalmente pagada",
                }), 400

            if monto > saldo_anterior:
                return jsonify({
                    "ok": False,
                    "error": (
                        "El abono no puede superar el saldo "
                        f"pendiente de {saldo_anterior:.2f}"
                    ),
                }), 400

            max_id = conn.execute(
                "SELECT COALESCE(MAX(id),0)+1 FROM venta_abonos"
            ).fetchone()[0]

            forma_pago = str(
                data.get("forma_pago")
                or sale["forma_pago"]
                or "Contado"
            ).strip()

            nota = str(
                data.get("nota")
                or ""
            ).strip()

            conn.execute(
                """
                INSERT INTO venta_abonos
                    (id, venta_id, monto, forma_pago,
                     usuario_id, nota)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    int(max_id),
                    sale_id,
                    monto,
                    forma_pago,
                    int(a.id),
                    nota,
                ),
            )

            nuevo_abonado = anterior + monto
            nuevo_saldo = max(
                total - nuevo_abonado,
                0,
            )

            if nuevo_saldo <= 0:
                nuevo_estado = "Pagado"
                nuevo_estado_pago = "Pagado"
            else:
                nuevo_estado = "Pendiente"
                nuevo_estado_pago = "Abonado"

            conn.execute(
                """
                UPDATE ventas
                SET
                    total_abonado=?,
                    saldo_pendiente=?,
                    estado_pago=?,
                    estado=?,
                    forma_pago=?
                WHERE id=?
                """,
                (
                    nuevo_abonado,
                    nuevo_saldo,
                    nuevo_estado_pago,
                    nuevo_estado,
                    forma_pago,
                    sale_id,
                ),
            )

            audit(
                conn,
                actor_id=int(a.id),
                action="sale.payment",
                entity="venta",
                entity_id=sale_id,
                details={
                    "monto": monto,
                    "total_abonado_anterior": anterior,
                    "total_abonado_nuevo": nuevo_abonado,
                    "saldo_anterior": saldo_anterior,
                    "saldo_nuevo": nuevo_saldo,
                    "forma_pago": forma_pago,
                },
            )

            conn.commit()

            return jsonify({
                "ok": True,
                "id": sale_id,
                "monto": monto,
                "total_abonado": nuevo_abonado,
                "saldo_pendiente": nuevo_saldo,
                "estado_pago": nuevo_estado_pago,
                "estado": nuevo_estado,
            }), 201

        finally:
            conn.close()

    except (AuthenticationError, PermissionError) as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
        }), 403

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)[:500],
        }), 400


@legacy_compat_api.get("/ventas/<int:sale_id>")
def venta(sale_id: int):
    try:
        actor("read_sale")
        conn = get_db()
        try:
            sale = conn.execute(
                "SELECT * FROM ventas WHERE id=?",
                (sale_id,),
            ).fetchone()
            if not sale:
                return jsonify({"ok": False, "error": "Venta no encontrada"}), 404
            items = conn.execute(
                "SELECT * FROM venta_items WHERE venta_id=? ORDER BY id",
                (sale_id,),
            ).fetchall()
            data = dict(sale)
            data["items"] = [dict(r) for r in items]
            return jsonify(data)
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403


@legacy_compat_api.get("/ciclos")
def ciclos():
    try:
        actor("read_sale")
        conn = get_db()
        try:
            rows = conn.execute("""
                SELECT DISTINCT ciclo
                FROM ventas
                WHERE TRIM(COALESCE(ciclo,'')) <> ''
                ORDER BY ciclo
            """).fetchall()
            return jsonify([r[0] for r in rows])
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403


@legacy_compat_api.get("/ciclos/<ciclo>/resumen")
def ciclo_resumen(ciclo: str):
    try:
        actor("read_sale")
        conn = get_db()
        try:
            ventas_rows = conn.execute("""
                SELECT id, numero_factura, cliente_nombre, total, ganancia,
                       estado, fecha, ciclo, fecha_inicio_ciclo, fecha_fin_ciclo
                FROM ventas
                WHERE ciclo=?
                ORDER BY id DESC
            """, (ciclo,)).fetchall()

            if not ventas_rows:
                return jsonify({
                    "ciclo": ciclo,
                    "num_ventas": 0,
                    "total": 0,
                    "ganancia": 0,
                    "fecha_inicio": None,
                    "fecha_fin": None,
                    "productos": [],
                    "compradores": {},
                    "ventas": [],
                })

            sale_ids = [int(r["id"]) for r in ventas_rows]
            placeholders = ",".join("?" * len(sale_ids))

            items = conn.execute(f"""
                SELECT vi.referencia, vi.nombre, vi.cantidad,
                       vi.subtotal, vi.ganancia, vi.venta_id
                FROM venta_items vi
                WHERE vi.venta_id IN ({placeholders})
            """, sale_ids).fetchall()

            productos_map = {}
            compradores = {}

            sales_dict = [dict(r) for r in ventas_rows]

            for item in items:
                ref = item["referencia"] or ""
                key = ref or item["nombre"] or ""
                bucket = productos_map.setdefault(key, {
                    "referencia": ref,
                    "nombre": item["nombre"] or "",
                    "total_cant": 0,
                    "total_venta": 0,
                    "total_gan": 0,
                })
                bucket["total_cant"] += int(item["cantidad"] or 0)
                bucket["total_venta"] += float(item["subtotal"] or 0)
                bucket["total_gan"] += float(item["ganancia"] or 0)

            for sale in sales_dict:
                buyer = sale["cliente_nombre"] or "Sin cliente"
                entry = compradores.setdefault(
                    buyer,
                    {"items": [], "total": 0},
                )
                sale_items = [dict(i) for i in items if i["venta_id"] == sale["id"]]
                for item in sale_items:
                    entry["items"].append(item)
                    entry["total"] += float(item["subtotal"] or 0)

            starts = [r["fecha_inicio_ciclo"] for r in ventas_rows if r["fecha_inicio_ciclo"]]
            ends = [r["fecha_fin_ciclo"] for r in ventas_rows if r["fecha_fin_ciclo"]]

            return jsonify({
                "ciclo": ciclo,
                "num_ventas": len(sales_dict),
                "total": sum(float(r["total"] or 0) for r in ventas_rows),
                "ganancia": sum(float(r["ganancia"] or 0) for r in ventas_rows),
                "fecha_inicio": min(starts) if starts else None,
                "fecha_fin": max(ends) if ends else None,
                "productos": list(productos_map.values()),
                "compradores": compradores,
                "ventas": sales_dict,
            })
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403


@legacy_compat_api.get("/devoluciones")
def devoluciones():
    try:
        actor("read_sale")
        conn = get_db()
        try:
            rows = conn.execute("""
                SELECT vd.id,
                       vd.venta_id,
                       v.numero_factura,
                       v.cliente_nombre,
                       vd.motivo,
                       vd.created_at AS fecha,
                       vd.motivo AS estado
                FROM venta_devoluciones vd
                JOIN ventas v ON v.id = vd.venta_id
                ORDER BY vd.id DESC
            """).fetchall()
            result = []
            for row in rows:
                base = dict(row)
                items = conn.execute("""
                    SELECT referencia, cantidad
                    FROM venta_devolucion_items
                    WHERE devolucion_id=?
                    ORDER BY id
                """, (row["id"],)).fetchall()
                if items:
                    for item in items:
                        result.append({
                            **base,
                            "referencia": item["referencia"],
                            "nombre": item["referencia"],
                            "cantidad": item["cantidad"],
                        })
                else:
                    result.append(base)
            return jsonify(result)
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
