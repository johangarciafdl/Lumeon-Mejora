# 🌙 LUMEON PRO - Guía de Inicio Rápido

## ✅ Instalación Completada

Tu sistema **LUMEON PRO** está configurado con:

- ✅ **Autenticación** para 2 admins
- ✅ **Generación automática de PDFs** de facturas
- ✅ **Envío de facturas por email** (configurable)
- ✅ **Auto-generación de pedidos** cuando se registra una venta
- ✅ **Descuento automático** de inventario
- ✅ **Sistema privado** solo para administradores

---

## 🚀 Para Iniciar el Sistema

### 1. Abre una terminal en la carpeta del proyecto

```bash
cd c:\Users\johan\Downloads\LUMEON_PRO_SOFTWARE\lumeon_pro
```

### 2. Activa el entorno virtual

```bash
.\.venv\Scripts\Activate.ps1
```

### 3. Ejecuta la aplicación

```bash
python backend\app.py
```

Verás algo como:

```bash
 * Running on http://127.0.0.1:5000
### 4. Abre en el navegador

```bash
http://127.0.0.1:5000
```

---

## 🔐 Credenciales de Acceso

| Usuario | Contraseña |
| --- | --- |
| `admin1` | `admin123` |
| `admin2` | `admin123` |

⚠️ **IMPORTANTE**: Cambia estas contraseñas después del primer login.

---

## 📧 Configurar Envío de Facturas por Email

Para que las facturas se envíen automáticamente:

### 1. Obtén tu contraseña de Google

1. Ve a [Google App Passwords](https://myaccount.google.com/apppasswords)
2. Selecciona **Mail** → **Windows Computer**
3. Google te generará una contraseña de 16 caracteres
4. Cópiala

### 2. Edita el archivo `.env`

```env
GMAIL_USER=tu_email@gmail.com
GMAIL_PASSWORD=tu_contraseña_de_16_caracteres
```

### 3. Reinicia la aplicación

Listo. Ahora cuando registres una venta, la factura se enviará automáticamente al email del cliente.

---

## 🎯 Flujo de Operación

### Registrar una venta

1. Ve a **Ventas** → **+ Nueva Venta**
2. **Selecciona o crea un cliente** (nombre, teléfono, email)
3. **Busca productos por referencia** y agrega cantidades
4. **Confirma** y se ejecutará automáticamente:
   - ✅ Factura PDF generada
   - ✅ Email enviado al cliente
   - ✅ Inventario descontado
   - ✅ Pedido generado en el apartado de Pedidos

### Recibir pedidos

1. Los pedidos se generan automáticamente desde las ventas
2. Cuando la distribuidora entregue, ve a **Pedidos** → **✓ Entregado**
3. El stock se actualizará automáticamente

### Gestionar devoluciones

1. Ve a **Devoluciones** → **+ Devolución**
2. Busca la referencia del producto
3. El stock se devuelve automáticamente

---

## 📊 Dashboard - Métricas Principales

El dashboard muestra en tiempo real:

- 📈 Ventas de hoy y del mes
- 💰 Ganancia estimada
- 🧾 Facturas pendientes y pagadas
- 📦 Stock disponible y alertas
- 👥 Total de clientes y productos
- 🚚 Pedidos pendientes

---

## 🗄️ Estructura del Proyecto

```bash
lumeon_pro/
├── backend/
│   ├── app.py              # API Flask con autenticación
│   └── database.db         # BD SQLite (se crea automáticamente)
├── frontend/
│   └── index.html          # Interfaz web
├── requirements.txt        # Dependencias Python
├── .env                    # Configuración (editable)
└── README.md              # Documentación
```

---

## 🔧 Tecnologías

- **Backend**: Python Flask + Flask-Login
- **Base de Datos**: SQLite3
- **Frontend**: HTML5 + CSS3 + JavaScript puro
- **Reportes**: ReportLab (PDFs)
- **Email**: SMTP (Gmail)

---

## ⚡ Comandos Útiles

| Comando | Qué hace |
| --- | --- |
| `python backend\app.py` | Inicia el servidor |
| `pip install -r requirements.txt` | Instala dependencias |
| `del backend\database.db` | Borra la DB (recarga datos) |

---

## 🆘 Troubleshooting

### No puede conectarse al servidor

- Verifica que `http://127.0.0.1:5000` esté en el navegador
- Restaura el terminal y ejecuta `python backend\app.py` nuevamente

### Error de Email

- Verifica que `GMAIL_PASSWORD` sea una **contraseña de aplicación** (16 caracteres)
- No uses tu contraseña de Gmail normal

### Login no funciona

- Limpia cookies del navegador (Ctrl+Shift+Delete)
- Intenta en modo incógnita

### Stock no se actualiza

- Recarga la página (F5)
- Verifica que hayas presionado "Registrar Venta"

---

## 📱 Usando en Móvil (Red Local)

1. Abre Command Prompt
2. Ejecuta: `ipconfig`
3. Busca tu IP local (ej: `192.168.1.100`)
4. En móvil, abre: `http://192.168.1.100:5000`

---

## 🎓 Próximas Mejoras

- Dashboard gráficos interactivos
- Reportes exportables a Excel
- Notificaciones por WhatsApp
- App móvil nativa
- Integración con APIs de Natura/Avon

---

## 📞 Soporte

Si tienes problemas:

1. Revisa los logs en la terminal
2. Borra `database.db` y reinicia para resetear todo
3. Verifica el archivo `.env`

---

**¡Tu sistema LUMEON PRO está 100% operativo!** 🚀

Hecho con ❤️ para tu emprendimiento.
