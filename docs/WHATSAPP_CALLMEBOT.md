# WhatsApp con CallMeBot

Lumeon usa CallMeBot como proveedor intercambiable para mensajes de WhatsApp.

## Configuración

Nunca guardar la API key en Git.

Variables de entorno:

```env
CALLMEBOT_ENABLED=1
CALLMEBOT_DEFAULT_PHONE=+573045201946
CALLMEBOT_API_KEY=***
```

El número predeterminado es configurable y solo sirve como destino de prueba/configuración. Los números de clientes se normalizan a formato internacional de Colombia (`+57XXXXXXXXXX`).

## Facturas

CallMeBot se usa para el mensaje y el enlace seguro a la factura. El PDF se genera y conserva dentro del sistema; no se asume que el proveedor gratuito pueda transportar adjuntos PDF.

## Seguridad

- No registrar API keys en logs.
- No poner credenciales en `app.py`.
- No incluir credenciales en commits.
- Si una clave se expone, revocarla y crear otra.

## Sustitución del proveedor

El código depende de `WhatsAppProvider`, no de CallMeBot directamente. Si el proveedor cambia sus condiciones, se puede implementar otro adaptador sin cambiar ventas, clientes o facturación.
