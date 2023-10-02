# Despliegue de IRIS

## Pods/servicios recomendados

Se recomienda desplegar IRIS2 en una serie de servicios independientes:

- PostgreSQL
- Redis
- Minio
- Backend
- Celery
  - Celery beat
  - Cola alta prioridad
  - Cola baja prioridad

## Health checks

### Backend

Liveliness:
```bash
exec curl -f localhost:8080/health/ || exit 1
```

Readiness:
```bash
exec python manage.py showmigrations | grep -c "\[ \]" -m 1 | grep -q 0 || exit 1
```

### Celery

Liveliness:
```bash
 exec celery inspect -t ${CELERY_INSPECT_TIMEOUT} ping -A main.celery || exit 1
```

### Celery-beat

Liveliness:
```bash
exec test `ps aux | grep beat | grep -v grep | wc -l` -gt 0 || exit 1
```

## Test de estrés

En el proyecto encontrarás ficheros JMX para realizar las pruebas de estrés y dimensionar la capacidad de cada uno
de los componentes de la arquitectura de IRIS para tu caso de uso.
