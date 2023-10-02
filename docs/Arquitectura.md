# Arquitectura de IRIS2

El stack de IRIS está compuesto por los siguientes elementos:

- PostgreSQL como base de datos relacional.
- Redis para caché y almacenamiento de las tareas asíncronas.
- Minio como almacén de archivos.
- Backend (API e interfaz administrativa para desarrolladores). Implementado en Django.
- Celery como sistema de colas.
- Frontal implementado como una Single Page Applicantion (SPA) con Vue y Nuxt.

Opcionalmente, se puede implementar un portal público para que los ciudadanos puedan enviar sus fichas.

> Algunos elementos de IRIS2 están heredados de IRIS y no han sido modificados para facilitar la migración y
> evitar errores derivados del cambio.

## PostgreSQL

De PostgreSQL se utilizan tres extensiones para lógica específica de IRIS:
- Unaccent
- Full text search
- GIS: si se usa un backend de geolicalización diferente se puede evitar esta dependencia.

Por tanto, para cambiar de base de datos se deberían evitar estas dependencias. Esta versión de IRIS es dependiente
completamente de Postgres.

## Minio

En la configuración se usa minio como almacén de archivos, pero se puede configurar en modo proxy por si se prefiriese
utilizar el servicio de un proveedor de cloud.

## Backend y colas en segunda plano (API Django + Django Rest Framework + Celery)

La [documentación del backend](../documentation.md) entra en más detalle de cada una de estas partes, dando más contexto sobre la implementación
y ejemplos directos.

## Frontend Vue

Puedes encontrar la documentación del frontend Vue en el repositorio de esa parte de la aplicación.
