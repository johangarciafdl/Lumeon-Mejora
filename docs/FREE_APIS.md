# Política de APIs gratuitas

Lumeon Mejora no debe introducir una dependencia que obligue a pagar para conservar las funciones básicas del sistema.

## Regla

Antes de integrar cualquier API externa se debe comprobar su modelo de uso y documentar límites, credenciales y alternativa local.

## WhatsApp

El adaptador actual usa CallMeBot porque es el proveedor que se estaba integrando en Lumeon. El código está aislado detrás de `WhatsAppProvider`, por lo que cambiar de proveedor no obliga a modificar ventas ni facturación.

**Importante:** que un servicio sea gratuito actualmente no significa que exista una garantía contractual de gratuidad permanente. Lumeon no debe tratar ningún proveedor externo como garantía de negocio. Por eso las facturas siempre se generan localmente y el fallo de WhatsApp nunca debe impedir registrar una venta.

## Regla de fallback

- PDF/factura: local y siempre disponible.
- Base de datos: local primero.
- Email/WhatsApp: canales de entrega desacoplados.
- Si un proveedor externo falla, registrar el fallo y permitir reintentar.

## Prohibido

- API de pago como dependencia obligatoria del checkout.
- Enviar secretos al frontend.
- Acoplar SQL al bot.
- Hacer que una caída de WhatsApp revierta una venta ya registrada.
