# 🌟 LUMEON PRO - Sistema de Gestión Integral

Sistema profesional de gestión de ventas, pedidos y envío automático de recibos por email

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.13-green)
![Flask](https://img.shields.io/badge/flask-3.1.3-red)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Características Principales

### 📧 Sistema de Correos Automáticos ⭐ **NUEVO**

- ✅ Genera recibos profesionales en **PDF** automáticamente
- ✅ Envía por email al cliente al registrar venta
- ✅ Diseño responsivo y personalizado
- ✅ Integración con **Gmail SMTP**
- ✅ HTML mejorado con estilos CSS
- ✅ Adjunta PDF al correo electrónico

### 💼 Gestión de Ventas

- Registro de clientes, productos y ventas
- Auto-generación de pedidos
- Cálculo automático de ganancias
- Control de inventario

### 📦 Gestión de Pedidos

- Auto-pedidos desde ventas
- Seguimiento desde Pendiente → Entregado
- Actualización automático de stock
- Reportes de pedidos

### 📊 Base de Datos

- SQLite3 con 8 tablas
- Migrations automáticas
- Registro completo de operaciones

### 🔐 Autenticación

- Login seguro con contraseñas hasheadas
- 2 usuarios admin por defecto
- Control de acceso por roles

---

## 🚀 Inicio Rápido

### Requisitos

- Python 3.13+
- pip (gestor de paquetes)
- Git

### Instalación (5 minutos)

### 1. Clonar Repositorio

```bash
git clone https://github.com/tu_usuario/lumeon-pro.git
cd lumeon-pro
```

### 2. Crear Entorno Virtual

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Gmail (Opcional pero Recomendado)

```bash
cd lumeon_pro
cp .env.example .env
# Edita .env con tus credenciales de Gmail
```

### 5. Ejecutar Servidor

```bash
# Opción A: Script automático
start_server.bat

# Opción B: Manual
python backend/app.py
```

### 6. Acceder al Sistema

- URL: [http://127.0.0.1:5000](http://127.0.0.1:5000)
- Login: `admin1` / `admin123`
- Usuario: `admin2` / `admin123`

---

## 📧 Configurar Correos Automáticos

### Paso 1: Configurar Gmail App Password

1. Ve a: [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Selecciona: "Mail" y "Windows Computer"
3. Copia la contraseña de 16 caracteres

### Paso 2: Actualizar .env

```env
GMAIL_USER=tu_email@gmail.com
GMAIL_PASSWORD=abcd1234efgh5678
GMAIL_FROM_NAME=LUMEON
```

### Paso 3: Probar Sistema

```bash
python test_email_system.py
```

---

## 📁 Estructura del Proyecto

```text
lumeon-pro/
├── lumeon_pro/
│   ├── backend/
│   │   ├── app.py                    # 🔥 Backend principal (812 líneas)
│   │   ├── database.db               # Base de datos SQLite
│   │   └── static/                   # Archivos estáticos
│   ├── frontend/
│   │   ├── index.html                # Interfaz web
│   │   └── styles/
│   ├── .env.example                  # Plantilla de configuración
│   ├── start_server.bat              # Script para iniciar servidor
│   ├── test_email_system.py          # Script de pruebas
│   └── requirements.txt              # Dependencias Python
├── CONFIGURAR_GMAIL.md               # Guía Gmail
├── RECIBOS_AUTOMATICOS.md            # Detalles del sistema
├── IMPLEMENTACION_COMPLETADA.md      # Resumen técnico
├── INICIO_RAPIDO_RECIBOS.md          # Quick start
├── EJEMPLO_RECIBO_VISUAL.html        # Vista previa
└── README.md                         # Este archivo
```

---

## 🛠️ Stack Tecnológico

### Backend

- **Flask 3.1.3** - Framework web
- **Flask-Login 0.6.3** - Autenticación
- **ReportLab 4.4.10** - Generación de PDF
- **SQLite3** - Base de datos
- **python-dotenv** - Variables de entorno
- **smtplib** - Envío de emails

### Frontend

- HTML5 / CSS3
- JavaScript vanilla
- Responsive design

### DevOps

- Python 3.13
- Git / GitHub
- Virtual Environment

---

## 📊 Funcionalidades por Endpoints

### Autenticación

- `POST /api/login` - Login de usuario
- `GET /api/logout` - Cerrar sesión

### Ventas 💼

- `POST /api/ventas` - **Crear venta + Generar PDF + Enviar Email**
- `GET /api/ventas` - Listar ventas
- `GET /api/ventas/<id>` - Detalle venta

### Productos

- `POST /api/productos` - Crear producto
- `GET /api/productos` - Listar productos
- `DELETE /api/productos/<id>` - Eliminar producto

### Clientes

- `POST /api/clientes` - Crear cliente
- `GET /api/clientes` - Listar clientes

### Pedidos

- `POST /api/pedidos` - Crear pedido
- `GET /api/pedidos` - Listar pedidos
- `PATCH /api/pedidos/<id>` - Actualizar estado

### Devoluciones

- `POST /api/devoluciones` - Registrar devolución
- `GET /api/devoluciones` - Listar devoluciones

---

## 🧪 Pruebas

### Ejecutar Suite de Pruebas

```bash
cd lumeon_pro
python test_email_system.py
```

### Verificar Dependencias

```bash
python -c "from flask import Flask; from reportlab.lib import colors; print('✅ Todas las dependencias OK')"
```

---

## 📋 Base de Datos

### Tablas

1. **usuarios** - Cuentas de acceso
2. **clientes** - Información de clientes
3. **productos** - Catálogo de productos
4. **ventas** - Registro de ventas
5. **venta_items** - Detalles por venta
6. **pedidos** - Órdenes a proveedores
7. **pedido_items** - Detalles por pedido
8. **devoluciones** - Registro de devoluciones

### Columnas Clave

- `cliente_email` - Para envío automático de recibos
- `cliente_telefono` - Dato de contacto
- `pdf_enviado` - Seguimiento de envíos
- `ganancia` - Cálculo automático

---

## 🔒 Seguridad

- ✅ Contraseñas hasheadas con Werkzeug
- ✅ Autenticación con Flask-Login
- ✅ Variables sensibles en `.env`
- ✓ CORS configurado correctamente
- ✓ `.env` en .gitignore

---

## 🐛 Troubleshooting

### "⚠️ Email no configurado"

**Solución:** Verifica que `GMAIL_USER` y `GMAIL_PASSWORD` están en `.env`

### "❌ Error al generar PDF"

**Solución:** `pip install reportlab==4.4.10`

### "No se conecta al servidor"

**Solución:** Ejecuta: `python lumeon_pro/backend/app.py`

### Email no llega

1. Verifica spam/correo no deseado
2. Revisa credenciales en `.env`
3. Habilita autenticación en 2 pasos en Gmail
4. Usa contraseña de aplicación (no la contraseña normal)

---

## 📝 Cambios Recientes

### v1.0.0 (10 Abril 2026) 🎉

- ✨ Sistema completo de correos automáticos
- ✨ Generación de PDF con ReportLab
- ✨ Templates HTML responsivos
- ✨ Integración Gmail SMTP
- ✨ Auto-pedidos desde ventas
- ✨ Validación de emails
- ✨ Scripts de prueba automatizadas
- ✨ Documentación completa

---

## 🤝 Contribuir

1. Fork el repositorio
2. Crea una rama: `git checkout -b feature/nueva-caracteristica`
3. Commit cambios: `git commit -m "Add nueva-caracteristica"`
4. Push: `git push origin feature/nueva-caracteristica`
5. Abre un Pull Request

---

## 📄 Licencia

MIT License - Libre para uso personal y comercial

---

## 👤 Autor

### LUMEON PRO Team

- Sistema de Gestión para Natura & Avon
- Desarrollado con ❤️ en 2026

---

## 🔗 Enlaces Importantes

- 📧 Configurar Gmail: [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
- 📖 Documentación Flask: [https://flask.palletsprojects.com/](https://flask.palletsprojects.com/)

- 📚 ReportLab: [https://www.reportlab.com/](https://www.reportlab.com/)
- 🐍 Python: [https://www.python.org/](https://www.python.org/)

---

## 📮 Contacto / Soporte

Para soporte técnico o reportar bugs, abre un issue en GitHub.

**¡Gracias por usar LUMEON PRO!** 🌟
