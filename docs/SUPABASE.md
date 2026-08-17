# Supabase / PostgreSQL

Lumeon Mejora usa Supabase como base de datos PostgreSQL en entornos desplegados. El backend no depende de la API de Supabase para las operaciones de negocio: usa la conexión PostgreSQL mediante `DATABASE_URL` y `psycopg`.

## Por qué

- Evita acoplar la lógica de negocio a un SDK externo.
- Mantiene el acceso SQL transaccional.
- Permite migrar de proveedor PostgreSQL sin reescribir los servicios.
- No requiere una API de pago.

## Configuración

Define `DATABASE_URL` como secreto del entorno. Nunca la pongas en Git.

En local, si `DATABASE_URL` está vacío, la capa nueva puede usar SQLite como fallback para desarrollo/tests. La aplicación legacy conserva su conexión propia hasta completar la migración.

## Reglas

1. No crear tablas automáticamente desde la aplicación en producción.
2. Los cambios de esquema deben ser migraciones SQL revisables.
3. Las escrituras de inventario/ventas deben ejecutarse dentro de transacciones.
4. Los IDs nuevos se obtienen mediante `INSERT ... RETURNING id` para PostgreSQL.
5. No almacenar `service_role` keys en frontend.
6. No registrar `DATABASE_URL` en logs.

## Próxima migración

La siguiente fase debe conectar los servicios restantes al esquema real de Supabase y añadir migraciones versionadas para `message_deliveries`, sesiones del asistente y auditoría, verificando primero las tablas existentes para no alterar datos actuales.
