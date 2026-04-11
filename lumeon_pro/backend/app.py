from flask import Flask, jsonify, request, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from datetime import datetime
import sqlite3, os, smtplib, io
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import dotenv

dotenv.load_dotenv()

app = Flask(__name__, static_folder="../frontend", static_url_path="")
app.secret_key = os.getenv("SECRET_KEY", "lumeon-secret-key-2026-admin")
login_manager = LoginManager()
login_manager.init_app(app)

@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

@app.route("/api/options/<path:p>", methods=["OPTIONS"])
def handle_options(p): 
    return "", 200

DB = os.path.join(os.path.dirname(__file__), "database.db")

# ═════════════════════════════════════════════════════════════════════════
# USER MODEL & AUTH
# ═════════════════════════════════════════════════════════════════════════
class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id,username,email FROM usuarios WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return User(user[0], user[1], user[2])
    return None

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Crear todas las tablas
    c.executescript("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT NOT NULL,
        nombre TEXT,
        rol TEXT DEFAULT 'admin',
        activo INTEGER DEFAULT 1,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        referencia TEXT UNIQUE NOT NULL,
        descripcion TEXT,
        categoria TEXT DEFAULT 'General',
        precio_compra REAL DEFAULT 0,
        precio_venta REAL DEFAULT 0,
        stock INTEGER DEFAULT 0,
        stock_minimo INTEGER DEFAULT 5,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        documento TEXT,
        telefono TEXT,
        direccion TEXT,
        email TEXT,
        ciudad TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_factura TEXT UNIQUE NOT NULL,
        cliente_id INTEGER,
        cliente_nombre TEXT,
        cliente_email TEXT,
        cliente_telefono TEXT,
        fecha TEXT DEFAULT CURRENT_TIMESTAMP,
        forma_pago TEXT DEFAULT 'Contado',
        subtotal REAL DEFAULT 0,
        total REAL DEFAULT 0,
        ganancia REAL DEFAULT 0,
        estado TEXT DEFAULT 'Pendiente',
        notas TEXT,
        pdf_enviado INTEGER DEFAULT 0,
        usuario_id INTEGER,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id),
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    );
    CREATE TABLE IF NOT EXISTS venta_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venta_id INTEGER NOT NULL,
        producto_id INTEGER,
        referencia TEXT,
        nombre TEXT,
        cantidad INTEGER DEFAULT 1,
        precio_compra REAL DEFAULT 0,
        precio_venta REAL DEFAULT 0,
        subtotal REAL DEFAULT 0,
        ganancia REAL DEFAULT 0,
        FOREIGN KEY (venta_id) REFERENCES ventas(id)
    );
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_pedido TEXT UNIQUE NOT NULL,
        proveedor TEXT DEFAULT 'Natura',
        venta_id INTEGER,
        fecha_pedido TEXT,
        fecha_entrega TEXT,
        fecha_cancelacion TEXT,
        total REAL DEFAULT 0,
        estado TEXT DEFAULT 'Pendiente',
        notas TEXT,
        ciclo TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (venta_id) REFERENCES ventas(id)
    );
    CREATE TABLE IF NOT EXISTS pedido_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER NOT NULL,
        referencia TEXT,
        nombre TEXT,
        cantidad INTEGER DEFAULT 1,
        precio_compra REAL DEFAULT 0,
        subtotal REAL DEFAULT 0,
        FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
    );
    CREATE TABLE IF NOT EXISTS devoluciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venta_id INTEGER,
        numero_factura TEXT,
        cliente_nombre TEXT,
        referencia TEXT,
        nombre TEXT,
        cantidad INTEGER DEFAULT 1,
        motivo TEXT,
        fecha TEXT DEFAULT CURRENT_TIMESTAMP,
        estado TEXT DEFAULT 'Procesada'
    );
    """)
    conn.commit()
    
    # Verificar y agregar columnas faltantes en tabla ventas
    c.execute("PRAGMA table_info(ventas)")
    columns = {col[1] for col in c.fetchall()}
    
    try:
        if 'cliente_email' not in columns:
            c.execute("ALTER TABLE ventas ADD COLUMN cliente_email TEXT")
            print("Agregada columna cliente_email")
    except Exception as e:
        print(f"cliente_email ya existe: {e}")
    
    try:
        if 'cliente_telefono' not in columns:
            c.execute("ALTER TABLE ventas ADD COLUMN cliente_telefono TEXT")
            print("Agregada columna cliente_telefono")
    except Exception as e:
        print(f"cliente_telefono ya existe: {e}")
    
    conn.commit()
    
    # Crear 2 usuarios admin por defecto
    c.execute("SELECT COUNT(*) FROM usuarios")
    if c.fetchone()[0] == 0:
        usuarios = [
            ("admin1", generate_password_hash("admin123"), "admin1@lumeon.com", "Administrador 1"),
            ("admin2", generate_password_hash("admin123"), "admin2@lumeon.com", "Administrador 2"),
        ]
        c.executemany("INSERT INTO usuarios (username,password,email,nombre) VALUES (?,?,?,?)", usuarios)
        conn.commit()
    
    # Cargar productos iniciales si no existen
    c.execute("SELECT COUNT(*) FROM productos")
    if c.fetchone()[0] == 0:
        productos = [
            ("PULPA HIDRATANTE MANOS 75G","70983","Ultra Hidratación 75g","Cremas",15000,44460,0,5),
            ("PULPA EXFOLIANTE MANOS Y PIES 60G","70981","Ultra Hidratación 60g","Cremas",15000,44460,0,5),
            ("PULPA HIDRATANTE PIES 75G","69817","Ultra Hidratación 75g","Cremas",15000,44460,0,5),
            ("PULPA HIDRATANTE MANOS 40G","95133","Ultra Hidratación 40g","Cremas",8000,21060,0,3),
            ("PULPA HIDRATANTE CORPORAL 400ML","203381","Ultra Hidratación","Cremas",24000,65340,0,5),
            ("ACEITE TRIFÁSICO CORPORAL 200ML","174338","Ultra Hidratación","Cremas",25000,66150,0,5),
            ("CONCENTRADO CORPORAL 30ML","150220","Ultra Hidratación","Cremas",28000,74070,0,3),
            ("MANTECA NUTRITIVA CORPORAL 200G","69820","Ultra Hidratación","Cremas",24000,65340,0,5),
            ("PESTAÑINA LAVABLE MULTI HD 9G","174921","Ojos","Maquillaje",19000,48510,0,5),
            ("PINCEL PRO BASE LÍQUIDA","55104","Rostro","Maquillaje",28000,72810,0,3),
            ("PRIMER FACIAL FPS 40 30ML","118797","Rostro","Maquillaje",29000,74610,0,3),
            ("GLOSS LABIAL VOLUMEN 5ML","164824","Boca","Maquillaje",19500,50310,0,5),
            ("EDP MASC HOMEM ELO 100ML","135068","Amaderado aromático","Perfumes",38000,97560,0,3),
            ("EDP MASC HOMEM COR.AGIO 100ML","186","Amaderado ambarado","Perfumes",46000,117720,0,3),
            ("EDT MASC HOMEM CLÁSICO 100ML","57351","Amaderado aromático","Perfumes",36000,91530,0,3),
            ("EDT MASC KAIAK URBE 100ML","111172","Aromático especiado","Perfumes",32000,81990,0,3),
            ("KAIAK SONAR MASC 100ML","156226","Aromático amaderado","Perfumes",53000,136710,0,3),
            ("EDP FEM ILÍA CLÁSICO 50ML","44171","Floral dulce","Perfumes",33000,84690,0,3),
            ("EDT FEM LUNA ROSÉ 75ML","116585","Chipre floral","Perfumes",56000,143910,0,3),
            ("BOLSA PEQUEÑA","218168","Empaque","Accesorios",500,1350,0,10),
            ("BOLSA MEDIANA","218169","Empaque","Accesorios",700,1800,0,10),
            ("CAJA VIVARA","154851","Empaque","Accesorios",3000,8100,0,5),
        ]
        c.executemany("INSERT INTO productos (nombre,referencia,descripcion,categoria,precio_compra,precio_venta,stock,stock_minimo) VALUES (?,?,?,?,?,?,?,?)", productos)
        conn.commit()
    conn.close()


# ═════════════════════════════════════════════════════════════════════════
# FUNCIONES DE EMAIL Y PDF
# ═════════════════════════════════════════════════════════════════════════

def enviar_factura_email(email_cliente, nombre_cliente, numero_factura, pdf_buffer):
    """Envía el recibo profesional por email al cliente"""
    try:
        gmail_user = os.getenv("GMAIL_USER", "").strip()
        gmail_pass = os.getenv("GMAIL_PASSWORD", "").strip()

        if not gmail_pass or not gmail_user or gmail_user == "tu_email@gmail.com":
            print(f"⚠️  Email no configurado. Recibo sería enviado a: {email_cliente}")
            return False

        # Validar formato de email
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{{2,}}$', email_cliente):
            print(f"❌ Email del cliente inválido: {email_cliente}")
            return False

        print(f"📧 Enviando recibo a: {email_cliente}")

        msg = MIMEMultipart('alternative')
        msg['From'] = f"{os.getenv('GMAIL_FROM_NAME', 'LUMEON')} <{gmail_user}>"
        msg['To'] = email_cliente
        msg['Subject'] = f"Tu Recibo LUMEON #{numero_factura} ✓"
        
        # HTML mejorado y profesional
        body_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background-color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #7C3AED 0%, #a78bfa 100%); color: white; padding: 30px 20px; text-align: center; }}
        .header h1 {{ font-size: 28px; margin-bottom: 5px; font-weight: 600; }}
        .header p {{ font-size: 14px; opacity: 0.95; letter-spacing: 0.5px; }}
        .content {{ padding: 30px 20px; }}
        .greeting {{ background-color: #f8f8f8; padding: 20px; border-radius: 6px; margin-bottom: 25px; border-left: 4px solid #7C3AED; }}
        .greeting h2 {{ color: #333; font-size: 18px; margin-bottom: 10px; }}
        .greeting p {{ color: #666; font-size: 14px; line-height: 1.6; }}
        .invoice-section {{ margin-bottom: 25px; }}
        .invoice-section h3 {{ color: #7C3AED; font-size: 14px; font-weight: 600; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px; }}
        .invoice-detail {{ background-color: #f8f8f8; padding: 15px; border-radius: 6px; margin-bottom: 10px; display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
        .detail-item {{ }}
        .detail-label {{ font-size: 12px; color: #999; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; }}
        .detail-value {{ font-size: 16px; color: #333; font-weight: 600; margin-top: 3px; }}
        .products-section {{ margin: 25px 0; }}
        .product-row {{ display: grid; grid-template-columns: 1fr 3fr 1fr 1fr; gap: 10px; padding: 10px 0; border-bottom: 1px solid #e0e0e0; font-size: 13px; }}
        .product-row:first-child {{ font-weight: 600; color: #7C3AED; border-bottom: 2px solid #7C3AED; padding-bottom: 8px; }}
        .product-qty, .product-price {{ color: #333; text-align: right; }}
        .summary {{ background-color: #f8f8f8; padding: 20px; border-radius: 6px; margin: 20px 0; }}
        .summary-row {{ display: grid; grid-template-columns: 1fr auto; gap: 20px; padding: 8px 0; font-size: 14px; }}
        .summary-row.total {{ border-top: 2px solid #7C3AED; padding-top: 12px; font-weight: 600; color: #7C3AED; font-size: 16px; }}
        .thanks {{ background: linear-gradient(135deg, rgba(124, 58, 237, 0.1) 0%, rgba(167, 139, 250, 0.1) 100%); padding: 25px; border-radius: 6px; text-align: center; margin: 25px 0; border-left: 4px solid #7C3AED; }}
        .thanks h2 {{ color: #7C3AED; font-size: 18px; margin-bottom: 8px; }}
        .thanks p {{ color: #666; font-size: 13px; line-height: 1.7; }}
        .footer {{ background-color: #f0f0f0; padding: 20px; text-align: center; font-size: 12px; color: #999; border-top: 1px solid #e0e0e0; }}
        .footer p {{ margin: 3px 0; }}
        .highlight {{ color: #7C3AED; font-weight: 600; }}
        .cta-button {{ display: inline-block; background: linear-gradient(135deg, #7C3AED 0%, #a78bfa 100%); color: white; padding: 12px 30px; border-radius: 6px; text-decoration: none; font-size: 14px; font-weight: 600; margin-top: 15px; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- HEADER -->
        <div class="header">
            <h1>✨ LUMEON</h1>
            <p>Cuidamos tu luz natural</p>
        </div>
        
        <!-- CONTENT -->
        <div class="content">
            <!-- SALUDO -->
            <div class="greeting">
                <h2>¡Hola {nombre_cliente.title()}!</h2>
                <p>Tu compra ha sido procesada exitosamente. Aquí está el detalle de tu recibo.</p>
            </div>
            
            <!-- INFORMACIÓN DEL RECIBO -->
            <div class="invoice-section">
                <h3>Información del Recibo</h3>
                <div class="invoice-detail">
                    <div class="detail-item">
                        <div class="detail-label">Número de Factura</div>
                        <div class="detail-value"><span class="highlight">#{numero_factura}</span></div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Estado</div>
                        <div class="detail-value">✓ Completado</div>
                    </div>
                </div>
            </div>
            
            <!-- MENSAJE DE AGRADECIMIENTO -->
            <div class="thanks">
                <h2>¡Gracias por tu confianza!</h2>
                <p>En LUMEON nos complace contar con clientes como tú. Tu satisfacción es nuestro mayor enfoque. Si tienes alguna pregunta o necesitas soporte, estamos aquí para ayudarte.</p>
            </div>
            
            <!-- PIE DE PÁGINA -->
            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0;">
                <p style="color: #999; font-size: 12px; margin-bottom: 10px;">Adjunto encontrarás tu recibo completo en PDF</p>
                <p style="color: #7C3AED; font-weight: 600; font-size: 13px;">LUMEON PRO</p>
                <p style="color: #999; font-size: 11px;">Sistema de Gestión - Natura & Avon</p>
            </div>
        </div>
        
        <!-- FOOTER -->
        <div class="footer">
            <p><strong>LUMEON PRO</strong> | Distribuidora Autorizada</p>
            <p>Cuidamos tu luz natural • admin@lumeon.com</p>
            <p style="margin-top: 10px; border-top: 1px solid #d0d0d0; padding-top: 10px;">Este es un correo automático, por favor no responder directamente.</p>
        </div>
    </div>
</body>
</html>"""
        
        # Adjuntar HTML
        msg.attach(MIMEText(body_html, 'html'))
        
        # Adjuntar PDF
        pdf_buffer.seek(0)
        attachment = MIMEBase('application', 'octet-stream')
        attachment.set_payload(pdf_buffer.read())
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', 'attachment', filename=f"Recibo_LUMEON_{numero_factura}.pdf")
        msg.attach(attachment)
        
        # Enviar por SMTP
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(gmail_user, gmail_pass)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Recibo enviado exitosamente a: {email_cliente}")
        return True
    except Exception as e:
        print(f"❌ Error al enviar email: {e}")
        return False

def generar_factura_pdf(venta_id):
    """Genera un PDF profesional del recibo con logo, saludo y gracias"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM ventas WHERE id=?", (venta_id,))
        venta = dict(c.fetchone())
        c.execute("SELECT * FROM venta_items WHERE venta_id=?", (venta_id,))
        items = [dict(row) for row in c.fetchall()]
        conn.close()
        
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, topMargin=20, bottomMargin=30, leftMargin=25, rightMargin=25)
        elements = []
        
        styles = getSampleStyleSheet()
        
        # Estilos personalizados
        subheader_style = ParagraphStyle('Subheader', parent=styles['Normal'], 
            fontSize=11, textColor=colors.HexColor('#666666'), spaceAfter=10, alignment=1)
        section_style = ParagraphStyle('Section', parent=styles['Heading2'], 
            fontSize=12, textColor=colors.HexColor('#7C3AED'), spaceAfter=6, fontName='Helvetica-Bold')
        greeting_style = ParagraphStyle('Greeting', parent=styles['Normal'], 
            fontSize=11, textColor=colors.HexColor('#333333'), spaceAfter=6, leading=16)
        thanks_style = ParagraphStyle('Thanks', parent=styles['Normal'], 
            fontSize=12, textColor=colors.HexColor('#7C3AED'), spaceAfter=3, alignment=1, fontName='Helvetica-Bold')
        footer_style = ParagraphStyle('Footer', parent=styles['Normal'], 
            fontSize=8, textColor=colors.HexColor('#999999'), alignment=1, spaceAfter=2)
        
        # HEADER - Logo y branding
        header_data = [['LUMEON', '']]
        header_table = Table(header_data, colWidths=[300, 100])
        header_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (0, 0), 28),
            ('TEXTCOLOR', (0, 0), (0, 0), colors.HexColor('#7C3AED')),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBELOW', (0, 0), (-1, -1), 2, colors.HexColor('#7C3AED')),
        ]))
        elements.append(header_table)
        elements.append(Paragraph("Cuidamos tu luz natural", subheader_style))
        elements.append(Spacer(1, 8))
        
        # SALUDO PERSONALIZADO
        cliente_nombre = venta['cliente_nombre'] or 'Estimado cliente'
        elements.append(Paragraph(f"Hola {cliente_nombre.title()},", greeting_style))
        elements.append(Paragraph("Te agradecemos sinceramente tu compra. Aquí está el detalle de tu recibo.", greeting_style))
        elements.append(Spacer(1, 12))
        
        # INFORMACIÓN DEL RECIBO
        fecha_formateada = venta['fecha'].split('T')[0] if 'T' in venta['fecha'] else venta['fecha']
        info_data = [
            ['Número de Factura:', venta['numero_factura'], 'Fecha:', fecha_formateada],
            ['Estado:', venta['estado'], 'Forma de Pago:', venta['forma_pago']],
        ]
        if venta['cliente_email'] or venta['cliente_telefono']:
            contacto = []
            if venta['cliente_email']: contacto.append(venta['cliente_email'])
            if venta['cliente_telefono']: contacto.append(venta['cliente_telefono'])
            info_data.append(['Contacto:', ' - '.join(contacto), '', ''])
        
        info_table = Table(info_data, colWidths=[100, 140, 100, 140])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#7C3AED')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F8F8')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E0')),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 12))
        
        # DETALLES DE PRODUCTOS
        elements.append(Paragraph("Detalle de tu Compra", section_style))
        elements.append(Spacer(1, 6))
        
        product_data = [['REF', 'Producto', 'Cant', 'Precio Unit', 'Subtotal']]
        for item in items:
            product_data.append([
                str(item['referencia']),
                item['nombre'][:40],
                str(item['cantidad']),
                f"${item['precio_venta']:,.0f}",
                f"${item['subtotal']:,.0f}"
            ])
        
        product_table = Table(product_data, colWidths=[50, 180, 45, 70, 70])
        product_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7C3AED')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFFFFF')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#333333')),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F8F8')]),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(product_table)
        elements.append(Spacer(1, 12))
        
        # RESUMEN
        elements.append(Paragraph("Resumen", section_style))
        summary_data = [
            ['Subtotal:', f"${venta['total']:,.0f}"],
            ['Ganancia Estimada:', f"${venta['ganancia']:,.0f}"],
            ['TOTAL:', f"${venta['total']:,.0f}"]
        ]
        
        summary_table = Table(summary_data, colWidths=[300, 80])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, 1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (0, 1), 10),
            ('BACKGROUND', (0, 0), (1, 1), colors.HexColor('#F8F8F8')),
            ('FONTNAME', (0, 2), (1, 2), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 2), (1, 2), 11),
            ('BACKGROUND', (0, 2), (1, 2), colors.HexColor('#7C3AED')),
            ('TEXTCOLOR', (0, 2), (1, 2), colors.white),
            ('TOPPADDING', (0, 0), (1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (1, -1), 6),
            ('LINEABOVE', (0, 2), (1, 2), 2, colors.HexColor('#7C3AED')),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 20))
        
        # MENSAJE DE GRACIAS
        elements.append(Paragraph("¡Gracias por elegir LUMEON!", thanks_style))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(
            "Nos complace contar con tu confianza. Tu satisfacción es nuestro compromiso.<br/>"
            "Si tienes alguna duda o necesitas ayuda, no dudes en contactarnos.",
            greeting_style
        ))
        elements.append(Spacer(1, 15))
        
        # FOOTER
        elements.append(Paragraph("─" * 70, footer_style))
        elements.append(Paragraph("LUMEON PRO - Sistema de Gestión Natura & Avon", footer_style))
        elements.append(Paragraph("Cuidamos tu luz natural | Distribuidora Autorizada", footer_style))
        
        doc.build(elements)
        pdf_buffer.seek(0)
        return pdf_buffer
    except Exception as e:
        print(f"❌ Error al generar PDF: {e}")
        return None

# ═════════════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username, password = data.get("username", "").strip(), data.get("password", "").strip()
    if not username or not password:
        return jsonify({"ok": False, "error": "Usuario y contraseña requeridos"}), 400
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, username, email, password FROM usuarios WHERE username=? AND activo=1", (username,))
    user_data = c.fetchone()
    conn.close()
    if not user_data or not check_password_hash(user_data[3], password):
        return jsonify({"ok": False, "error": "Usuario o contraseña incorrectos"}), 401
    user = User(user_data[0], user_data[1], user_data[2])
    login_user(user, remember=True)
    return jsonify({"ok": True, "username": username, "email": user_data[2]})

@app.route("/api/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"ok": True})

@app.route("/api/current-user")
def get_current_user():
    if current_user.is_authenticated:
        return jsonify({"ok": True, "user": {"id": current_user.id, "username": current_user.username, "email": current_user.email}})
    return jsonify({"ok": False, "user": None})

@app.route("/")
def index():
    return send_from_directory("../frontend", "index.html")

# ═════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═════════════════════════════════════════════════════════════════════════

@app.route("/api/dashboard")
@login_required
def dashboard():
    conn = get_db()
    c = conn.cursor()
    hoy = datetime.now().strftime("%Y-%m-%d")
    mes = datetime.now().strftime("%Y-%m")
    año = datetime.now().year
    
    c.execute("SELECT COALESCE(SUM(total),0) FROM ventas WHERE fecha LIKE ?", (f"{hoy}%",))
    ventas_hoy = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(total),0) FROM ventas WHERE fecha LIKE ?", (f"{mes}%",))
    ventas_mes = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(ganancia),0) FROM ventas WHERE fecha LIKE ?", (f"{mes}%",))
    ganancia_mes = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM ventas WHERE estado='Pendiente'")
    pendientes = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM ventas WHERE estado='Pagado'")
    pagadas = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM productos WHERE stock=0")
    sin_stock = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM productos WHERE stock>0 AND stock<=stock_minimo")
    stock_bajo = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM clientes")
    total_clientes = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM productos")
    total_productos = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM pedidos WHERE estado='Pendiente'")
    pedidos_pend = c.fetchone()[0]
    c.execute("SELECT numero_factura,cliente_nombre,total,estado,fecha FROM ventas ORDER BY id DESC LIMIT 8")
    ultimas = [dict(r) for r in c.fetchall()]
    c.execute("SELECT nombre,referencia,stock,stock_minimo FROM productos WHERE stock<=stock_minimo ORDER BY stock ASC LIMIT 8")
    alertas = [dict(r) for r in c.fetchall()]
    c.execute("SELECT strftime('%m',fecha) mes,SUM(total) total,SUM(ganancia) ganancia FROM ventas WHERE fecha LIKE ? GROUP BY mes ORDER BY mes", (f"{año}%",))
    por_mes = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify({"ventas_hoy":ventas_hoy,"ventas_mes":ventas_mes,"ganancia_mes":ganancia_mes,"pendientes":pendientes,"pagadas":pagadas,"sin_stock":sin_stock,"stock_bajo":stock_bajo,"total_clientes":total_clientes,"total_productos":total_productos,"pedidos_pend":pedidos_pend,"ultimas_ventas":ultimas,"alertas_stock":alertas,"ventas_por_mes":por_mes})

# ═════════════════════════════════════════════════════════════════════════
# PRODUCTOS
# ═════════════════════════════════════════════════════════════════════════

@app.route("/api/productos", methods=["GET"])
@login_required
def get_productos():
    conn = get_db()
    c = conn.cursor()
    q = request.args.get("q","")
    cat = request.args.get("categoria","")
    sql = "SELECT * FROM productos WHERE 1=1"
    params = []
    if q:
        sql += " AND (nombre LIKE ? OR referencia LIKE ?)"
        params += [f"%{q}%",f"%{q}%"]
    if cat:
        sql += " AND categoria=?"
        params.append(cat)
    sql += " ORDER BY categoria,nombre"
    c.execute(sql,params)
    r = [dict(x) for x in c.fetchall()]
    conn.close()
    return jsonify(r)

@app.route("/api/productos", methods=["POST"])
@login_required
def create_producto():
    d = request.json
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO productos (nombre,referencia,descripcion,categoria,precio_compra,precio_venta,stock,stock_minimo) VALUES (?,?,?,?,?,?,?,?)",
                  (d["nombre"],d["referencia"],d.get("descripcion",""),d.get("categoria","General"),d.get("precio_compra",0),d.get("precio_venta",0),d.get("stock",0),d.get("stock_minimo",5)))
        conn.commit()
        return jsonify({"ok":True,"id":c.lastrowid})
    except sqlite3.IntegrityError:
        return jsonify({"ok":False,"error":"Referencia ya existe"}),400
    finally:
        conn.close()

@app.route("/api/productos/<int:pid>", methods=["PUT"])
@login_required
def update_producto(pid):
    d = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE productos SET nombre=?,referencia=?,descripcion=?,categoria=?,precio_compra=?,precio_venta=?,stock=?,stock_minimo=? WHERE id=?",
              (d["nombre"],d["referencia"],d.get("descripcion",""),d.get("categoria","General"),d.get("precio_compra",0),d.get("precio_venta",0),d.get("stock",0),d.get("stock_minimo",5),pid))
    conn.commit()
    conn.close()
    return jsonify({"ok":True})

@app.route("/api/productos/<int:pid>", methods=["DELETE"])
@login_required
def delete_producto(pid):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM productos WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return jsonify({"ok":True})

@app.route("/api/productos/buscar/<ref>")
@login_required
def buscar_ref(ref):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM productos WHERE referencia=?", (ref,))
    p = c.fetchone()
    conn.close()
    return jsonify(dict(p) if p else {})

# ═════════════════════════════════════════════════════════════════════════
# CLIENTES
# ═════════════════════════════════════════════════════════════════════════

@app.route("/api/clientes", methods=["GET"])
@login_required
def get_clientes():
    conn = get_db()
    c = conn.cursor()
    q = request.args.get("q","")
    sql = "SELECT * FROM clientes WHERE 1=1"
    params = []
    if q:
        sql += " AND (nombre LIKE ? OR documento LIKE ? OR telefono LIKE ?)"
        params += [f"%{q}%"]*3
    sql += " ORDER BY nombre"
    c.execute(sql,params)
    r = [dict(x) for x in c.fetchall()]
    conn.close()
    return jsonify(r)

@app.route("/api/clientes", methods=["POST"])
@login_required
def create_cliente():
    d = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO clientes (nombre,documento,telefono,direccion,email,ciudad) VALUES (?,?,?,?,?,?)",
              (d["nombre"],d.get("documento",""),d.get("telefono",""),d.get("direccion",""),d.get("email",""),d.get("ciudad","")))
    conn.commit()
    r = {"ok":True,"id":c.lastrowid,"nombre":d["nombre"]}
    conn.close()
    return jsonify(r)

@app.route("/api/clientes/<int:cid>", methods=["PUT"])
@login_required
def update_cliente(cid):
    d = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE clientes SET nombre=?,documento=?,telefono=?,direccion=?,email=?,ciudad=? WHERE id=?",
              (d["nombre"],d.get("documento",""),d.get("telefono",""),d.get("direccion",""),d.get("email",""),d.get("ciudad",""),cid))
    conn.commit()
    conn.close()
    return jsonify({"ok":True})

# ═════════════════════════════════════════════════════════════════════════
# VENTAS (CON AUTO-PEDIDO Y EMAIL)
# ═════════════════════════════════════════════════════════════════════════

@app.route("/api/ventas", methods=["GET"])
@login_required
def get_ventas():
    conn = get_db()
    c = conn.cursor()
    q = request.args.get("q","")
    estado = request.args.get("estado","")
    sql = "SELECT * FROM ventas WHERE 1=1"
    params = []
    if q:
        sql += " AND (numero_factura LIKE ? OR cliente_nombre LIKE ?)"
        params += [f"%{q}%"]*2
    if estado:
        sql += " AND estado=?"
        params.append(estado)
    sql += " ORDER BY id DESC LIMIT 200"
    c.execute(sql,params)
    r = [dict(x) for x in c.fetchall()]
    conn.close()
    return jsonify(r)

@app.route("/api/ventas", methods=["POST"])
@login_required
def create_venta():
    try:
        d = request.json
        items = d.get("items",[])
        if not items:
            return jsonify({"ok":False,"error":"Sin productos"}),400
        
        conn = get_db()
        c = conn.cursor()
        try:
            sub = sum(it["cantidad"]*it["precio_venta"] for it in items)
            gan = sum(it["cantidad"]*(it["precio_venta"]-it.get("precio_compra",0)) for it in items)
            
            c.execute("INSERT INTO ventas (numero_factura,cliente_id,cliente_nombre,cliente_email,cliente_telefono,fecha,forma_pago,subtotal,total,ganancia,estado,notas,usuario_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (d["numero_factura"],d.get("cliente_id"),d.get("cliente_nombre",""),d.get("cliente_email",""),d.get("cliente_telefono",""),d.get("fecha",datetime.now().isoformat()),d.get("forma_pago","Contado"),sub,sub,gan,d.get("estado","Pendiente"),d.get("notas",""),current_user.id))
            vid = c.lastrowid
            
            for it in items:
                ref = it.get("referencia","")
                cant = it["cantidad"]
                pv = it["precio_venta"]
                pc = it.get("precio_compra",0)
                nom = it.get("nombre","")
                c.execute("INSERT INTO venta_items (venta_id,producto_id,referencia,nombre,cantidad,precio_compra,precio_venta,subtotal,ganancia) VALUES (?,?,?,?,?,?,?,?,?)",
                          (vid,it.get("producto_id"),ref,nom,cant,pc,pv,cant*pv,cant*(pv-pc)))
                if ref:
                    c.execute("UPDATE productos SET stock=MAX(0,stock-?) WHERE referencia=?", (cant,ref))
            
            # AUTO-CREAR PEDIDO
            try:
                c.execute("SELECT MAX(CAST(SUBSTR(numero_pedido, 5) AS INTEGER)) FROM pedidos")
                last_ped = c.fetchone()[0] or 0
                numero_pedido = f"PED-{last_ped + 1:04d}"
                total_pedido = sum(it["cantidad"]*it.get("precio_compra",0) for it in items)
                c.execute("INSERT INTO pedidos (numero_pedido,proveedor,venta_id,fecha_pedido,total,estado,notas,ciclo) VALUES (?,?,?,?,?,?,?,?)",
                          (numero_pedido,"Natura",vid,datetime.now().strftime("%Y-%m-%d"),total_pedido,"Pendiente",f"Auto-generado desde Venta #{d['numero_factura']}","Ciclo Actual"))
                pid = c.lastrowid
                for it in items:
                    cant = it["cantidad"]
                    pc = it.get("precio_compra",0)
                    ref = it.get("referencia","")
                    nom = it.get("nombre","")
                    c.execute("INSERT INTO pedido_items (pedido_id,referencia,nombre,cantidad,precio_compra,subtotal) VALUES (?,?,?,?,?,?)",
                              (pid,ref,nom,cant,pc,cant*pc))
                print(f"✅ Auto-pedido creado: {numero_pedido}")
            except Exception as e:
                print(f"⚠️  Error auto-pedido: {e}")
            
            conn.commit()
            
            # GENERAR Y ENVIAR RECIBO PDF POR EMAIL
            email_enviado = False
            try:
                nombre_cliente = d.get("cliente_nombre", "Cliente")
                email_cliente = d.get("cliente_email", "").strip()
                numero_factura = d["numero_factura"]
                
                if email_cliente:
                    print(f"📧 Generando recibo para: {email_cliente}")
                    pdf_buffer = generar_factura_pdf(vid)
                    
                    if pdf_buffer:
                        if enviar_factura_email(email_cliente, nombre_cliente, numero_factura, pdf_buffer):
                            c.execute("UPDATE ventas SET pdf_enviado=1 WHERE id=?", (vid,))
                            conn.commit()
                            email_enviado = True
                            print(f"✅ Recibo enviado exitosamente")
                        else:
                            print(f"⚠️  No se pudo enviar recibo (email no configurado)")
                    else:
                        print(f"❌ Error generando PDF del recibo")
                else:
                    print(f"⚠️  No hay email del cliente para enviar recibo")
                    
            except Exception as e:
                print(f"❌ Error al generar/enviar recibo: {e}")
            
            venta_info = {
                "ok": True,
                "id": vid,
                "numero_factura": d["numero_factura"],
                "email_enviado": email_enviado,
                "mensaje": "Venta registrada exitosamente" + (" y recibo enviado por email" if email_enviado else "")
            }
            
            return jsonify(venta_info), 201
            
        except sqlite3.IntegrityError as e:
            conn.rollback()
            return jsonify({"ok":False,"error":f"Error de integridad: {str(e)}"}),400
        finally:
            conn.close()
    except Exception as e:
        print(f"❌ Error en create_venta: {e}")
        return jsonify({"ok":False,"error":f"Error del servidor: {str(e)}"}),500


@app.route("/api/ventas/<int:vid>", methods=["GET"])
@login_required
def get_venta(vid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM ventas WHERE id=?", (vid,))
    v = dict(c.fetchone())
    c.execute("SELECT * FROM venta_items WHERE venta_id=?", (vid,))
    v["items"] = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(v)

@app.route("/api/ventas/<int:vid>/estado", methods=["PATCH"])
@login_required
def update_venta_estado(vid):
    d = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE ventas SET estado=? WHERE id=?", (d["estado"],vid))
    conn.commit()
    conn.close()
    return jsonify({"ok":True})

# ═════════════════════════════════════════════════════════════════════════
# PEDIDOS
# ═════════════════════════════════════════════════════════════════════════

@app.route("/api/pedidos", methods=["GET"])
@login_required
def get_pedidos():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM pedidos ORDER BY id DESC LIMIT 100")
    r = [dict(x) for x in c.fetchall()]
    conn.close()
    return jsonify(r)

@app.route("/api/pedidos", methods=["POST"])
@login_required
def create_pedido():
    d = request.json
    items = d.get("items",[])
    conn = get_db()
    c = conn.cursor()
    try:
        total = sum(it["cantidad"]*it.get("precio_compra",0) for it in items)
        c.execute("INSERT INTO pedidos (numero_pedido,proveedor,fecha_pedido,fecha_entrega,fecha_cancelacion,total,estado,notas,ciclo) VALUES (?,?,?,?,?,?,?,?,?)",
                  (d["numero_pedido"],d.get("proveedor","Natura"),d.get("fecha_pedido"),d.get("fecha_entrega"),d.get("fecha_cancelacion"),total,d.get("estado","Pendiente"),d.get("notas",""),d.get("ciclo","")))
        pid = c.lastrowid
        for it in items:
            pc = it.get("precio_compra",0)
            cant = it["cantidad"]
            c.execute("INSERT INTO pedido_items (pedido_id,referencia,nombre,cantidad,precio_compra,subtotal) VALUES (?,?,?,?,?,?)",
                      (pid,it.get("referencia",""),it.get("nombre",""),cant,pc,cant*pc))
        conn.commit()
        return jsonify({"ok":True,"id":pid})
    except sqlite3.IntegrityError as e:
        return jsonify({"ok":False,"error":str(e)}),400
    finally:
        conn.close()

@app.route("/api/pedidos/<int:pid>/estado", methods=["PATCH"])
@login_required
def update_pedido_estado(pid):
    d = request.json
    conn = get_db()
    c = conn.cursor()
    estado = d["estado"]
    if estado == "Entregado":
        fecha = d.get("fecha_entrega", datetime.now().strftime("%Y-%m-%d"))
        c.execute("UPDATE pedidos SET estado=?,fecha_entrega=? WHERE id=?", (estado,fecha,pid))
        c.execute("SELECT * FROM pedido_items WHERE pedido_id=?", (pid,))
        for it in c.fetchall():
            c.execute("UPDATE productos SET stock=stock+? WHERE referencia=?", (it["cantidad"],it["referencia"]))
    elif estado == "Cancelado":
        c.execute("UPDATE pedidos SET estado=?,fecha_cancelacion=? WHERE id=?", (estado,datetime.now().strftime("%Y-%m-%d"),pid))
    else:
        c.execute("UPDATE pedidos SET estado=? WHERE id=?", (estado,pid))
    conn.commit()
    conn.close()
    return jsonify({"ok":True})

# ═════════════════════════════════════════════════════════════════════════
# DEVOLUCIONES
# ═════════════════════════════════════════════════════════════════════════

@app.route("/api/devoluciones", methods=["GET"])
@login_required
def get_devoluciones():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM devoluciones ORDER BY id DESC LIMIT 100")
    r = [dict(x) for x in c.fetchall()]
    conn.close()
    return jsonify(r)

@app.route("/api/devoluciones", methods=["POST"])
@login_required
def create_devolucion():
    d = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO devoluciones (venta_id,numero_factura,cliente_nombre,referencia,nombre,cantidad,motivo,estado) VALUES (?,?,?,?,?,?,?,?)",
              (d.get("venta_id"),d.get("numero_factura",""),d.get("cliente_nombre",""),d.get("referencia",""),d.get("nombre",""),d.get("cantidad",1),d.get("motivo",""),d.get("estado","Procesada")))
    if d.get("referencia"):
        c.execute("UPDATE productos SET stock=stock+? WHERE referencia=?", (d.get("cantidad",1),d["referencia"]))
    conn.commit()
    r = {"ok":True,"id":c.lastrowid}
    conn.close()
    return jsonify(r)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
