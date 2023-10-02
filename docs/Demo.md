# Demo

Para lanzar la demo en tu entorno local necesitarás tener instalado docker y docker-compose.

> Estas instrucciones están adaptadas para un entorno linux, pero con docker y docker-compose se pueden lanzar en
> en entonos mac y windows.

## Descarga el código de los componentes

Descarga el código del backend y del frontend dentro de un mismo directorio.

## Configuración

### Backend

Dentro de la carpeta src, existe el fichero app.ini.template, cópialo con nombre app.ini.

```bash
cp iris2-backoffice/src/app.ini.template iris2-backoffice/src/app.ini
```

### Frontend

Copia el fichero dev-config.template.json al directorio src/static:

```bash
cp iris2-spa/dev-config.template.json iris2-spa/src/static/config.json
```

# Lanzar el entorno

Primero lanzaremos el backend:

```bash
cd iris-backoffice
docker-compose up devel
```

Si todo ha ido bien, podrás entrar en http://localhost:8000/services/iris/admin/ y hacer login con el usuario ADMIN,
creado por defecto con password 1234 (salvo que hayas configurado otra cosa en el app.ini)

Una vez en marcha ya podemos iniciar el front, ya que trabaja de forma separada.

```bash
cd ../iris2-spa
docker-compose up -d nginx
```

Si se ha inicializado correctamente, podrás acceder a la aplicación en http://127.0.0.1:3000/backoffice/dashboard/.

Aquí podrás empezar a probar las funcionalidades de IRIS.

## Datos de demo

El docker-compose de IRIS Community viene preparado para cargar una base de datos de demo lista para funcionar.
El sistema auto-identificará a cualquier usuario como administrador, ya que para la demo se ha eliminado la necesidad
de configurar el sistema de autenticación.

## Próximos pasos

Una vez que el entorno está en marcha, puedes seguir las [intrucciones de configuración](./docs/Configuración.md) para
personalizar IRIS a tu caso de uso.
