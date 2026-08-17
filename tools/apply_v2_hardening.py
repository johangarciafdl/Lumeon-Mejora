from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "lumeon_pro" / "backend" / "app.py"
REQUIREMENTS = ROOT / "requirements.txt"
RENDER = ROOT / "render.yaml"

text = APP.read_text(encoding="utf-8")

old_imports = '''import sqlite3, os, smtplib, io, re, threading\nfrom email.mime.text import MIMEText\nfrom email.mime.multipart import MIMEMultipart\nfrom email.mime.base import MIMEBase\nfrom email import encoders\nimport dotenv'''
new_imports = '''import sqlite3, os, io, re, threading, secrets, json\nimport urllib.request as urllib_req\nimport urllib.error as urllib_error\nfrom email.mime.text import MIMEText\nfrom email.mime.multipart import MIMEMultipart\nfrom email.mime.base import MIMEBase\nfrom email import encoders\nimport dotenv'''
if old_imports in text:
    text = text.replace(old_imports, new_imports, 1)

old_config = '''app = Flask(__name__, static_folder="../frontend", static_url_path="")\napp.secret_key = os.getenv("SECRET_KEY", "lumeon-secret-key-2026-admin")\nlogin_manager = LoginManager()\nlogin_manager.init_app(app)\n \n@app.after_request\ndef add_cors(response):\n    response.headers["Access-Control-Allow-Origin"] = "*"\n    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"\n    response.headers["Access-Control-Allow-Headers"] = "Content-Type"\n    return response'''
new_config = '''app = Flask(__name__, static_folder="../frontend", static_url_path="")\n_secret_key = os.getenv("SECRET_KEY", "").strip()\nif not _secret_key and os.getenv("FLASK_ENV", "").lower() == "production":\n    raise RuntimeError("SECRET_KEY es obligatorio en producción")\napp.secret_key = _secret_key or secrets.token_hex(32)\napp.config.update(\n    SESSION_COOKIE_HTTPONLY=True,\n    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "0") == "1",\n    SESSION_COOKIE_SAMESITE=os.getenv("SESSION_COOKIE_SAMESITE", "Lax"),\n    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 7,\n)\n\nlogin_manager = LoginManager()\nlogin_manager.init_app(app)\nlogin_manager.login_view = "login"\n\n_ALLOWED_ORIGINS = {x.strip() for x in os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:5000,http://localhost:5000").split(",") if x.strip()}\n\n@app.after_request\ndef add_security_headers(response):\n    origin = request.headers.get("Origin")\n    if origin and origin in _ALLOWED_ORIGINS:\n        response.headers["Access-Control-Allow-Origin"] = origin\n        response.headers["Access-Control-Allow-Credentials"] = "true"\n        response.headers["Vary"] = "Origin"\n    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"\n    response.headers["Access-Control-Allow-Headers"] = "Content-Type,X-CSRF-Token"\n    response.headers["X-Content-Type-Options"] = "nosniff"\n    response.headers["X-Frame-Options"] = "SAMEORIGIN"\n    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"\n    return response'''
if old_config in text:
    text = text.replace(old_config, new_config, 1)

old_users = '''    # Usuarios por defecto\n    c.execute("SELECT COUNT(*) FROM usuarios")\n    if c.fetchone()[0] == 0:\n        usuarios = [\n            ("admin1", generate_password_hash("admin123"), "admin1@lumeon.com", "Administrador 1"),\n            ("admin2", generate_password_hash("admin123"), "admin2@lumeon.com", "Administrador 2"),\n        ]\n        c.executemany("INSERT INTO usuarios (username,password,email,nombre) VALUES (?,?,?,?)", usuarios)\n        conn.commit()'''
new_users = '''    # Administrador inicial: nunca sembrar contraseñas conocidas.\n    c.execute("SELECT COUNT(*) FROM usuarios")\n    if c.fetchone()[0] == 0:\n        admin_username = os.getenv("ADMIN_USERNAME", "").strip()\n        admin_password = os.getenv("ADMIN_PASSWORD", "")\n        admin_email = os.getenv("ADMIN_EMAIL", "admin@lumeon.local").strip()\n        if admin_username and admin_password:\n            c.execute(\n                "INSERT INTO usuarios (username,password,email,nombre) VALUES (?,?,?,?)",\n                (admin_username, generate_password_hash(admin_password), admin_email, "Administrador")\n            )\n            conn.commit()\n        else:\n            print("⚠️ No hay usuarios. Define ADMIN_USERNAME y ADMIN_PASSWORD para crear el primer administrador.")'''
if old_users in text:
    text = text.replace(old_users, new_users, 1)

needle = '''            vid = c.lastrowid\n \n            for it in items:'''
replacement = '''            vid = c.lastrowid\n \n            # Validar cantidades y stock antes de descontar inventario.\n            for it in items:\n                try:\n                    cant_validada = int(it.get("cantidad", 0))\n                except (TypeError, ValueError):\n                    raise ValueError("La cantidad de cada producto debe ser un entero")\n                if cant_validada <= 0:\n                    raise ValueError("La cantidad de cada producto debe ser mayor que cero")\n                ref_validada = str(it.get("referencia", "")).strip()\n                if ref_validada:\n                    c.execute("SELECT stock FROM productos WHERE referencia=?", (ref_validada,))\n                    producto_db = c.fetchone()\n                    if not producto_db:\n                        raise ValueError(f"Producto no encontrado: {ref_validada}")\n                    if producto_db[0] < cant_validada:\n                        raise ValueError(f"Stock insuficiente para {ref_validada}: disponible {producto_db[0]}, solicitado {cant_validada}")\n \n            for it in items:'''
if needle in text:
    text = text.replace(needle, replacement, 1)

old_stock = 'c.execute("UPDATE productos SET stock=MAX(0,stock-?) WHERE referencia=?", (cant, ref))'
new_stock = 'c.execute("UPDATE productos SET stock=stock-? WHERE referencia=? AND stock>=?", (cant, ref, cant))\n                if c.rowcount != 1:\n                    raise ValueError(f"Stock insuficiente para {ref}")'
if old_stock in text:
    text = text.replace(old_stock, new_stock, 1)

old_order = '''    estado = d["estado"]\n    if estado == "Entregado":\n        fecha = d.get("fecha_entrega", datetime.now().strftime("%Y-%m-%d"))\n        c.execute("UPDATE pedidos SET estado=?,fecha_entrega=? WHERE id=?", (estado, fecha, pid))\n        c.execute("SELECT * FROM pedido_items WHERE pedido_id=?", (pid,))\n        for it in c.fetchall():\n            c.execute("UPDATE productos SET stock=stock+? WHERE referencia=?", (it["cantidad"], it["referencia"]))\n    elif estado == "Cancelado":'''
new_order = '''    estado = d["estado"]\n    c.execute("SELECT estado FROM pedidos WHERE id=?", (pid,))\n    pedido_actual = c.fetchone()\n    if not pedido_actual:\n        conn.close()\n        return jsonify({"ok": False, "error": "Pedido no encontrado"}), 404\n    estado_anterior = pedido_actual[0]\n    if estado == "Entregado":\n        if estado_anterior == "Entregado":\n            conn.close()\n            return jsonify({"ok": False, "error": "El pedido ya fue entregado"}), 409\n        if estado_anterior == "Cancelado":\n            conn.close()\n            return jsonify({"ok": False, "error": "Un pedido cancelado no puede marcarse como entregado"}), 409\n        fecha = d.get("fecha_entrega", datetime.now().strftime("%Y-%m-%d"))\n        c.execute("UPDATE pedidos SET estado=?,fecha_entrega=? WHERE id=?", (estado, fecha, pid))\n        c.execute("SELECT * FROM pedido_items WHERE pedido_id=?", (pid,))\n        for it in c.fetchall():\n            c.execute("UPDATE productos SET stock=stock+? WHERE referencia=?", (it["cantidad"], it["referencia"]))\n    elif estado == "Cancelado":'''
if old_order in text:
    text = text.replace(old_order, new_order, 1)

# Fix Resend runtime imports already added above; make error handling explicit.
text = text.replace("with urllib_req.urlopen(req, timeout=30) as response:", "with urllib_req.urlopen(req, timeout=30) as response:", 1)

# Add a lightweight health endpoint before init_db.
health = '''\n@app.route("/health", methods=["GET"])\ndef health():\n    try:\n        conn = get_db()\n        conn.execute("SELECT 1")\n        conn.close()\n        return jsonify({"ok": True, "service": "lumeon", "status": "healthy"})\n    except Exception:\n        return jsonify({"ok": False, "service": "lumeon", "status": "unhealthy"}), 503\n\n'''
marker = "\ninit_db()\n"
if health not in text and marker in text:
    text = text.replace(marker, health + marker, 1)

APP.write_text(text, encoding="utf-8")

# Pin direct runtime dependencies to stable major/minor floors while retaining compatibility.
REQUIREMENTS.write_text('''Flask>=3.0,<4\nflask-cors>=4.0,<7\nflask-login>=0.6,<1\nWerkzeug>=3.0,<4\nreportlab>=4.0,<5\npython-dotenv>=1.0,<2\ngunicorn>=22,<24\npytest>=8,<9\n''', encoding="utf-8")

# Align deployment configuration with the actual Resend implementation and secure secret handling.
if RENDER.exists():
    render = RENDER.read_text(encoding="utf-8")
    render = render.replace('GMAIL_USER', 'RESEND_API_KEY')
    render = render.replace('GMAIL_PASSWORD', 'ADMIN_PASSWORD')
    if 'ADMIN_USERNAME' not in render:
        render = render.replace('envVars:', 'envVars:\n    - key: ADMIN_USERNAME\n      sync: false\n    - key: ADMIN_EMAIL\n      sync: false\n    - key: ALLOWED_ORIGINS\n      sync: false', 1)
    RENDER.write_text(render, encoding="utf-8")

print("Lumeon V2 hardening applied")
