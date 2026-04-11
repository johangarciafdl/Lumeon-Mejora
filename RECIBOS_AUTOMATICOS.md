# Sistema de Recibos Automatizados

## Automatización Activada

El sistema ahora genera y envía **recibos profesionales en PDF** automáticamente cuando se registra una venta.

---

## Características de los Recibos

✅ **Diseño Profesional**

- Header con branding LUMEON (púrpura/azul)
- Logo y texto "Cuidamos tu luz natural"

✅ **Contenido Personalizado**

- Saludo personalizado al cliente ("¡Hola [nombre]!")
- Número de factura único
- Fecha y hora de la compra
- Estado de la venta

✅ **Detalles de Compra**

- Lista completa de productos
- Referencia, cantidad, precio unitario
- Subtotal por producto

✅ **Resumen Financiero**

- Subtotal de venta
- Ganancia estimada
- Total a pagar (destacado en color púrpura)

✅ **Mensaje de Gracias**

- "¡Gracias por tu confianza en LUMEON!"
- Mensaje de compromiso de calidad
- Llamado a acción para soporte

---

## Configuración de Email

### Opción 1: Usar Gmail (Recomendado)

1. **Abre el archivo `.env`** en la carpeta `backend/`:

```env
GMAIL_USER=tu_email@gmail.com
GMAIL_PASSWORD=tu_contrasena_de_15_caracteres
```

1. **Genera una contraseña de aplicación en Google:**

   - Ve a [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   - Selecciona "Mail" y "Windows Computer"
   - Google generará una contraseña de 16 caracteres
   - Cópiala en el `.env` (sin espacios)

2. **Ejemplo correcto:**

```env
GMAIL_USER=mitienda@gmail.com
GMAIL_PASSWORD=abcd1234efgh5678
```

### Opción 2: Sin Configuración (DESARROLLO)

Si no configuras Gmail, el sistema:

- ✅ Registra la venta normalmente
- ✅ Genera el PDF del recibo
- ✅ Muestra en consola: "⚠️ Email no configurado. Recibo sería enviado a: <cliente@ejemplo.com>"
- ❌ No envía el email automáticamente

---

## Flujo de Envío Automático

Cuando registras una venta:

```text
1. Completas el formulario de venta
   ↓
2. Haces clic en "💾 REGISTRAR VENTA"
   ↓
3. El sistema:
   ✅ Guarda la venta en la BD
   ✅ Crea el auto-pedido (PED-0001, etc)
   ✅ Genera PDF profesional
   ✅ Envía email si está configurado
   ↓
4. Aparece: "Venta registrada exitosamente y recibo enviado por email"
   ↓
5. Cliente recibe email con:
   - HTML bonito en su bandeja
   - PDF adjunto: "Recibo_LUMEON_FAC-0123.pdf"
```

---

## Ejemplo de Email Recibido

**Asunto:** `Tu Recibo LUMEON #FAC-0123 ✓`

**Contenido:**

- Header con branding LUMEON
- "¡Hola María!"
- Número de factura, estado, fecha
- Detalles de productos comprados
- Total a pagar: $15,400
- "¡Gracias por tu confianza en LUMEON!"
- PDF adjunto: Recibo_LUMEON_FAC-0123.pdf

---

## Monitoreo del Sistema

### En la Consola del Servidor

Verás mensajes como:

```text
📧 Generando recibo para: cliente@ejemplo.com
✅ Recibo enviado exitosamente a: cliente@ejemplo.com
⚠️ Email no configurado. Recibo sería enviado a: cliente@ejemplo.com
❌ Error al generar/enviar recibo: [error details]
```

### En la Base de Datos

Cada venta tiene un campo `pdf_enviado`:

- `1` = Email enviado ✅
- `0` = Email no enviado (no configurado o error)

---

## Costumización del Recibo

### Cambiar Colores

En [app.py](lumeon_pro/backend/app.py), función `generar_factura_pdf()`:

```python
# Color púrpura actual:
colors.HexColor('#7C3AED')

# Cambia por tu color:
colors.HexColor('#FF6B9D')  # Rosa
colors.HexColor('#00D4FF')  # Cian
colors.HexColor('#FFB800')  # Oro
```

### Cambiar Mensaje de Gracias

Busca en `enviar_factura_email()` la sección:

```html
<h2>¡Gracias por tu confianza!</h2>
<p>En LUMEON nos complace contar con clientes como tú...</p>
```

Personaliza el mensaje como desees.

### Agregar Logo en PDF

Para incluir el logo de LUMEON en el PDF:

1. Guarda la imagen en: `backend/static/logo.png` (200px ancho)
2. En `generar_factura_pdf()`, agrega después del header:

```python
from reportlab.platypus import Image
logo = Image('backend/static/logo.png', width=100, height=100)
elements.insert(0, logo)
```

---

## Prueba Rápida

1. **Accede a:** [http://127.0.0.1:5000](http://127.0.0.1:5000)
2. **Login:** admin1 / admin123
3. **Registra una venta:**
   - Cliente: "Test Cliente"
   - Email: <tu_email@gmail.com>
   - Producto: cualquiera
   - Haz clic: "💾 REGISTRAR VENTA"

4. **Verifica:**
   - Terminal: búsca "✅ Recibo enviado"
   - Email: revisa tu bandeja (o spam)
   - PDF: descarga el adjunto

---

## Troubleshooting

### Error: 'ascii' codec can't encode

**Causa:** Caracteres especiales (ñ, ü, etc) en el nombre del cliente
**Solución:** Ya está fijado en la última versión ✅

### Email no configurado

**Causa:** `.env` no tiene `GMAIL_USER` o `GMAIL_PASSWORD`
**Solución:** Completa el archivo `.env` con tus credenciales

### Email no llega

**Verificar:**

1. ¿Gmail está configurado? (`echo $GMAIL_USER` en terminal)
2. ¿Cliente ingresó email? (formulario de venta)
3. ¿Revisar spam/promociones en Gmail?
4. Credenciales correctas? (no acepta contraseña normal, solo Contraseña de Aplicación)

### PDF no se genera

**Causa:** Falta ReportLab
**Solución:** `pip install reportlab==4.4.10`

---

## Estadísticas de Envíos

Próximamente agregaremos:

- Dashboard con recibos enviados hoy
- Reporte de intentos fallidos
- Reenvío manual de recibos

---

## Próximas Mejoras

**En desarrollo:**

- Recibos en WhatsApp
- Recibos en SMS
- Plantillas personalizables
- Logo dinámico en PDF
- Descuentos y promociones en recibo

---

## Soporte

Si tienes problemas:

1. Verifica mensajes en la consola del servidor
2. Revisa el archivo `.env`
3. Prueba con un email de prueba primero

**¡Tu sistema de recibos está listo!**
