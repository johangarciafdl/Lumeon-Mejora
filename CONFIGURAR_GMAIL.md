# ⚙️ GUÍA PASO A PASO: Configurar Gmail para Recibos Automáticos

## 📋 Requisitos

- ✅ Una cuenta Gmail activa
- ✅ Acceso a [https://myaccount.google.com](https://myaccount.google.com)
- ✅ El archivo `.env` en tu proyecto

---

## 🚀 PASO 1: Abrir el .env

1. Abre la carpeta: `lumeon_pro\backend\`
2. Busca el archivo `.env`
3. Abre con un editor (Notepad, VS Code, etc)

Deberías ver:

```env
GMAIL_USER=
GMAIL_PASSWORD=
```

---

## 🔐 PASO 2: Habilitar Autenticación en 2 Pasos en Google

1. Ve a: [https://myaccount.google.com/security](https://myaccount.google.com/security)
2. En la izquierda, haz clic en **"Seguridad"**
3. Busca **"Verificación en 2 pasos"**
4. Haz clic en **"Verificación en 2 pasos"**
5. Sigue los pasos para:
   - Elegir método (SMS, app, etc)
   - Confirmar tu identidad

✅ Es necesario habilitarla para generar contraseña de app

---

## 🔑 PASO 3: Generar Contraseña de Aplicación

1. Ve a: [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Deberías ver una pantalla que dice:

```text
Selecciona la aplicación y el dispositivo
```

1. En **"Selecciona la aplicación"**: Elige **"Correo"**
2. En **"Selecciona el dispositivo"**: Elige **"Windows Computer"** (o tu SO)
3. Haz clic en **"Generar"**

4. **Google te mostrará una contraseña de 16 caracteres** como:

```text
abcd 1234 efgh 5678
```

1. **Cópiala** (sin espacios será: `abcd1234efgh5678`)

---

## ✏️ PASO 4: Actualizar el Archivo .env

1. Ve de nuevo al archivo `.env` en `backend/`
2. Reemplaza las líneas vacías:

**ANTES:**

```env
GMAIL_USER=
GMAIL_PASSWORD=
```

**DESPUÉS:**

```env
GMAIL_USER=tu_email@gmail.com
GMAIL_PASSWORD=abcd1234efgh5678
```

**Ejemplo real:**

```env
GMAIL_USER=mitienda@gmail.com
GMAIL_PASSWORD=xyzw9876lmno1234
```

⚠️ **Importante:**

- Sin espacios entre caracteres
- Exactamente como Google te lo generó
- No uses tu contraseña normal de Gmail

1. **Guarda el archivo** (Ctrl+S)

---

## 🔄 PASO 5: Reiniciar el Servidor

1. Ve a la terminal donde corre Flask
2. Presiona **Ctrl+C** para detener
3. Ejecuta de nuevo:

```bash
python lumeon_pro\backend\app.py
```

Deberías ver:

```bash
 * Running on http://127.0.0.1:5000
```

---

## ✅ PASO 6: Prueba

1. Abre: [http://127.0.0.1:5000](http://127.0.0.1:5000)
2. Login: `admin1` / `admin123`
3. Registra una venta con:
   - **Cliente:** "Test Cliente"
   - **Email:** **Tu email real** (para que recibas el email de prueba)
   - **Producto:** Cualquiera
   - **Guardar**

4. En la terminal, deberías ver:

```text
📧 Generando recibo para: tu_email@gmail.com
✅ Recibo enviado exitosamente a: tu_email@gmail.com
```

1. Revisa tu **email** (o carpeta de **Spam**)

---

## 🐛 TROUBLESHOOTING

### Problema: "⚠️ Email no configurado"

**Causa:** El .env no se cargó correctamente

**Soluciones:**

1. Verifica que el archivo `.env` está en `backend/` (no en otra carpeta)
2. Verifica que NO tiene extensión `.env.txt` (debe ser solo `.env`)
3. Reinicia el servidor (Ctrl+C y vuelve a iniciar)
4. Prueba escribiendo en terminal:

```bash
echo %GMAIL_USER%
```

Debería mostrar tu email

---

### Problema: "❌ Error al enviar email: Login failed"

**Causa:** Contraseña incorrecta o no es de aplicación

**Soluciones:**

1. Verifica en `.env` que NO hay espacios
2. Genera una NUEVA contraseña en [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Copia exactamente sin espacios
4. Verifica que primero habilitaste autenticación en 2 pasos

---

### Problema: Email no llega a la bandeja

**Soluciones:**

1. Revisa **Spam/Correo no deseado**
2. Agrega `admin@lumeon.com` a contactos
3. Verifica que el email del cliente es correcto
4. Espera 1-2 minutos (a veces tarda)
5. Prueba con tu propio correo primero

---

### Problema: "❌ Error: SSL: WRONG_VERSION_NUMBER"

**Causa:** Problema con Gmail

**Soluciones:**

1. Verifica que usas puerto 465 (en el código)
2. Regenera la contraseña de aplicación
3. Espera 15 minutos después de habilitarla

---

## 📧 Alternativa: Usar otro proveedor de Email

Si no quieres usar Gmail, puedes usar:

### SendGrid (Recomendado - Gratis para 100 emails/día)

```python
def enviar_factura_email(...):
    # Cambiar SMTP
    server = smtplib.SMTP('smtp.sendgrid.net', 587)
    server.login('apikey', 'SG.tu_api_key_aqui')
```

### Mailgun (Gratis también)

```python
server = smtplib.SMTP('smtp.mailgun.org', 587)
server.login('postmaster@tu_dominio.com', 'contraseña')
```

---

## 🎯 Resumen de lo que se logró

✅ **Sistema automático de recibos:**

- Genera PDF profesional automáticamente
- Envía por email al cliente
- Personalizado con nombre del cliente
- Incluye todos los detalles de la compra
- Diseño hermoso con colores de marca

✅ **Configuración segura:**

- Credenciales en `.env` (no en el código)
- Contraseña de aplicación de Google
- Autenticación en 2 pasos

✅ **Totalmente automatizado:**

- No requiere intervención manual
- Se envía al registrar la venta
- Log detallado en consola

---

## 🚀 ¿Qué sigue?

Una vez configurado Gmail:

1. **Personaliza el recibo:**
   - Cambiar colores
   - Agregar logo
   - Editar mensajes

2. **Integra más canales:**
   - WhatsApp
   - SMS
   - Slack

3. **Crea reportes:**
   - Emails enviados hoy
   - Intentos fallidos
   - Estadísticas

---

## ¿Preguntas? El sistema está listo para producción. 🎉
