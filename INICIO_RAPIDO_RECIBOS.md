# Inicio Rápido - Sistema de Recibos Automáticos

## En 5 minutos tendrás recibos enviándose por email

---

## PASO 1: Activar Gmail (2 minutos)

### 1.1 - Abre el archivo .env

```text
lumeon_pro/backend/.env
```

### 1.2 - Obtén contraseña de Google

- Ve a: [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
- Selecciona: **Correo** + **Windows Computer**
- Haz clic: Generar
- Copia la contraseña de 16 caracteres

### 1.3 - Llena el .env

```env
GMAIL_USER=tu_email@gmail.com
GMAIL_PASSWORD=xyzw9876lmno1234
```

✅ **Guardado**

---

## PASO 2: Reinicia el Servidor (1 minuto)

```bash
# En terminal, detén el servidor:
Ctrl+C

# Vuelve a iniciar:
python lumeon_pro\backend\app.py
```

Deberías ver:

```text
 * Running on http://127.0.0.1:5000
```

✅ **Servidor listo**

---

## PASO 3: Registra una Venta de Prueba (2 minutos)

1. Abre: [http://127.0.0.1:5000](http://127.0.0.1:5000)
2. Login: `admin1` / `admin123`
3. Haz clic: **"+ NUEVA VENTA"**
4. Rellena:

```text
Factura: FAC-0001
Cliente: Tu Nombre
Email: TU_EMAIL@gmail.com ← IMPORTANTE
Teléfono: +57 301 234 5678
Producto: Agrega uno
Cantidad: 1
```

1. Haz clic: **"💾 REGISTRAR VENTA"**

### Resultado esperado

```text
✅ Venta registrada exitosamente y recibo enviado por email
```

---

## PASO 4: Verifica tu Email (1 minuto)

1. 📧 Abre tu email
2. 🔍 Busca: `Tu Recibo LUMEON #FAC-0001`
3. 📎 Descarga el PDF adjunto
4. ✅ ¡Listo! Eso es lo que reciben tus clientes

---

## En caso de problemas

### Email no configurado

- Verifica que `.env` esté en `backend/` (no otra carpeta)
- Reinicia el servidor
- Verifica que el `.env` sin extensión `.txt`

### Email no llega

- Revisa carpeta **Spam/Correo no deseado**
- Espera 1-2 minutos (a veces tarda)
- Prueba con otro email

### Error al enviar email

- Verifica contraseña (debe ser de app, no tu clave normal)
- Regenera contraseña en Google
- Habilita autenticación en 2 pasos si no la tienes

---

## Documentación Completa

| Documento | Tema |
| --- | --- |
| `CONFIGURAR_GMAIL.md` | Guía detallada Gmail |
| `RECIBOS_AUTOMATICOS.md` | Características del recibo |
| `EJEMPLO_RECIBO_VISUAL.html` | Vista previa |
| `IMPLEMENTACION_COMPLETADA.md` | Resumen técnico |

---

## Qué sucede automáticamente

```text
Cuando registras venta:

1. Se guarda en BD
2. Se crea auto-pedido (PED-0001)
3. Se genera PDF profesional ← NUEVO
4. Se envía email al cliente ← NUEVO
5. Se registra estado de envío

TODO SIN INTERVENCIÓN MANUAL
```

---

## Próximos Pasos

### Personalizar el Recibo

- Cambiar colores
- Agregar tu logo
- Editar mensajes

Ver: `RECIBOS_AUTOMATICOS.md` → "Sección CUSTOMIZACIÓN"

### Añadir Más Usuarios

- Editar BD con admin2/admin123
- Crear nuevos usuarios en tabla `usuarios`

### Integrar Otros Canales

- WhatsApp (próximamente)
- SMS (próximamente)

---

## Ya está todo listo

Tu sistema ahora:

- ✅ Genera recibos automáticamente
- ✅ Envía emails profesionales
- ✅ Personaliza cada recibo
- ✅ Mantiene registro de envíos
- ✅ Maneja errores inteligentemente

**Tus clientes recibirán recibos hermosos sin que hagas nada adicional.**

---

## Ayuda

Si tienes dudas:

1. Lee el documento relevante (ver tabla arriba)
2. Revisa la consola del servidor para mensajes de error
3. Verifica archivos `.env` y estructura de carpetas

¡Éxito con tus recibos! 🎉
