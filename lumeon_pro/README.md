# LUMEON PRO v2.2 ENTERPRISE

## Sistema de Gestión Inteligente — Natura & Avon

### 🆕 NUEVAS FUNCIONALIDADES (v2.2 - Recibos Profesionales)

- ✅ **Recibos PDF profesionales** con diseño hermoso
- ✅ **Emails automáticos** con HTML personalizado
- ✅ **Saludo personalizado** al cliente
- ✅ **Mensaje de gracias** con branding LUMEON
- ✅ **Detalles completos** de productos y montos
- ✅ **Autenticación segura** para 2 administradores
- ✅ **Auto-generación de pedidos** al registrar ventas
- ✅ **Descuento automático de inventario**
- ✅ **Sistema privado** - Solo acceso para admins

---

## 🚀 INSTALACIÓN RÁPIDA

### 1. Instalar dependencias

```bash
cd lumeon_pro
pip install -r requirements.txt
```

### 2. Configurar email (IMPORTANTE para recibos)

Edita `.env`:

```env
GMAIL_USER=tu_email@gmail.com
GMAIL_PASSWORD=tu_contraseña_app_google
```

> 📖 Ver guía completa: `CONFIGURAR_GMAIL.md`

### 3. Iniciar el servidor

```bash
python backend\app.py
```

### 4. Abrir en navegador

```bash
http://127.0.0.1:5000
```

---

## 🔐 LOGIN

| Usuario | Clave |
| --- | --- |
| admin1 | admin123 |
| admin2 | admin123 |

---

## ✨ FUNCIONALIDADES

### 📧 Recibos Automáticos (NUEVO)

**Cuando registras una venta:**
1. ✅ Se guarda en la BD
2. ✅ Se crea auto-pedido
3. ✅ Se genera PDF profesional
4. ✅ Se envía email automático al cliente

**Recibo incluye:**
- 🎨 Diseño profesional con branding LUMEON
- 👋 Saludo personalizado ("¡Hola María!")
- 📋 Número de factura, fecha, estado
- 📦 Detalle de productos comprados
- 💰 Subtotal, ganancia estimada, total
- 🙏 Mensaje de gracias con compromiso de calidad
- 📎 PDF adjunto descargable

Ver ejemplo: `EJEMPLO_RECIBO_VISUAL.html`

### 🔐 Autenticación

- Login para 2 administradores
- Sesiones seguras con Flask-Login
- Logout desde cualquier pantalla

### 📊 Dashboard

- KPIs en tiempo real: ventas del día/mes, ganancia
- Alertas automáticas de stock bajo
- Gráfico de ventas por mes
- Últimas ventas y productos con bajo stock

### 📦 Inventario

- 22 productos Natura precargados
- Precio compra, venta, margen $ y %
- Stock con alertas automáticas
- Búsqueda y filtro por categoría

### 🧾 Facturas/Ventas

- Registro completo con datos del cliente
- Búsqueda dinámica de productos
- Descuento automático de inventario
- **PDF automático** de factura (profesional)
- **Email automático** al cliente
- Control de estado: Pendiente/Pagado/Cancelado

### 👥 Clientes

- Base de datos con teléfono, correo, dirección
- Búsqueda por nombre, documento, teléfono
- Historial de compras asociado

### 📬 Pedidos a Distribuidora

- **Auto-generación automática** desde ventas
- Registro manual también disponible
- Control por ciclo/campaña
- Estados: Pendiente/En camino/Entregado/Cancelado
- Al marcar como "Entregado", **stock se actualiza automáticamente**

### ↺ Devoluciones

- Registro con motivo
- Stock se devuelve automáticamente
- Historial completo

### 📄 Reportes

- Exportación de facturas PDF
- Próximamente: Excel con análisis

---

## 🔄 FLUJO DE OPERACIÓN

- Fechas: pedido, entrega, cancelación
- Al marcar "Entregado" → suma el stock automáticamente

### Devoluciones

- Registro de devoluciones
- Al procesar → devuelve el stock automáticamente

---

## ESTRUCTURA

```bash
LUMEON_PRO/
├── backend/
│   ├── app.py          # API Flask (lógica del negocio)
│   └── database.db     # SQLite (se crea automáticamente)
├── frontend/
│   └── index.html      # UI completa (HTML + CSS + JS)
└── requirements.txt
```
