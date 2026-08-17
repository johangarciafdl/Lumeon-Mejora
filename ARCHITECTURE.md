# Lumeon V2 — arquitectura

## Objetivo

Evolucionar el MVP actual sin romper la aplicación existente. `app.py` se mantiene como compatibilidad durante la migración; la nueva lógica de negocio vive en módulos independientes.

## Capas

```text
HTTP / Flask routes
        |
        v
Services (reglas de negocio)
        |
        v
Core (configuración, DB, seguridad, errores)
        |
        v
SQLite / PostgreSQL
```

### `core/`
Infraestructura transversal. No debe contener reglas de negocio.

### `services/`
Casos de uso: ventas, inventario, pedidos, clientes, emails. Los servicios reciben conexiones/datos y no dependen de HTML.

### `routes/` (siguiente etapa)
Endpoints HTTP delgados. Validan entrada, autentican y delegan en servicios.

### `models/` (siguiente etapa)
Representaciones de dominio y acceso a datos cuando la migración de SQLite a PostgreSQL esté lista.

## Reglas de diseño

1. Una operación de negocio importante debe ser atómica.
2. El inventario nunca puede quedar negativo.
3. Las transiciones de pedidos son explícitas.
4. El email no forma parte de la transacción de venta.
5. Los secretos solo vienen de variables de entorno.
6. Ninguna ruta debe contener consultas SQL complejas + reglas de negocio completas.
7. Los servicios deben poder probarse sin levantar Flask.
8. Los errores públicos no exponen stack traces ni secretos.
9. PostgreSQL será el destino de producción; SQLite seguirá disponible para desarrollo.

## Migración incremental

```text
legacy app.py
    |
    +--> core
    +--> services
    +--> routes
    +--> tests
          |
          v
     app.py delgado
```

No se cambia el entrypoint de producción hasta que la cobertura funcional de la nueva capa sea suficiente.
