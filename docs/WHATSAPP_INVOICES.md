# Facturas por WhatsApp

## Flujo

1. La venta se confirma dentro de una transacción.
2. Se genera el PDF localmente.
3. Se registra la entrega como `PENDING`.
4. El proveedor WhatsApp intenta enviar el aviso.
5. Se registra `SENT` o `FAILED`, el error y el identificador del proveedor.

## CallMeBot

La configuración se realiza únicamente mediante variables de entorno:

- `CALLMEBOT_ENABLED=1`
- `CALLMEBOT_PHONE=+57...`
- `CALLMEBOT_API_KEY=...`

Nunca guardar la API key en Git.

## PDF

El proveedor gratuito de CallMeBot se utiliza para el mensaje de WhatsApp. La aplicación no debe asumir que puede adjuntar un PDF directamente. El mensaje puede incluir una URL segura al documento cuando exista un mecanismo de almacenamiento/descarga apropiado.

## Resiliencia

Un fallo de WhatsApp no debe deshacer una venta. La comunicación es una tarea posterior a la transacción comercial y debe poder reintentarse.
