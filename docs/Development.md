# Entorno de desarrollo

Dependencias
------------

* Git.
* Python 3.7.4 and  `pipenv <http://pipenv.readthedocs.io/en/latest/#install-pipenv-today>`__.
* Node LTS with `nvm <https://github.com/creationix/nvm>`__
* `Yarn <https://yarnpkg.com/en/docs/install>`__
* `Editorconfig <http://editorconfig.org/#download>`__ for development.


Instalación y puesta en marcha
------------------------------

1.  Clonar proyecto :

        mkdir ~/workspace/iris
        cd iris/
        git clone git@github.com:AjuntamentdeBarcelona/iris.git

2. Instalar librerias de sistema:

       xargs -rxa system-requirements.txt -- sudo apt-get install --

3.  Preparar virtualenv Python :

        pipenv install --dev
        pipenv shell
        # Pulsa Ctrl-D para salir del virtualenv.

4.  Crear configuración local :

        cd src
        cp app.ini.template app.ini
        # Revisar y modificar app.ini, al menos la sección de base de datos.

5.  Crear base de datos :

        python manage.py migrate
        # Opcionalmente, crear super usuario solo la primera vez
        python manage.py createsuperuser

6.  Arancar servidor de desarrollo y tests :

        python manage.py runserver
        pytest


Funcionalidad
=============

La mayoría de la funcionalidad se puede deducir leyendo el *app.ini* y
el *settings.py*. A continuación se explica las partes más importantes.

Pipfile
-------

Para gestionar las dependencias de los paquetes de Python se utiliza una
liberia basada en pip llamada
[pipenv](http://docs.pipenv.org/en/latest/).

El listado de dependencias se almacena en unos ficheros llamados
*Pipfile* y *Pifile.lock*. El primero se va generando automaticamente a
medida que vamos añadiendo paquetes al entorno y el segundo se genera a
partir del *Pipfile*. En éste se quedan fijadas las versiones
específicas de cada paquete además se introduce un hash por motivos de
[seguridad](http://docs.pipenv.org/en/latest/advanced.html#pipfile-lock-security-features).

Su funcionamento es similar al *pip*:

-   `pipenv install` instala todas las dependencias que encuentra en el
archivo *Pipfile* y genera el fichero *Pipfile.lock*.

-   `pipenv install --dev` instala todas las dependencias, tanto las de
desarrollo como las generales. Solo usar en entorno de desarrollo.

-   `pipenv install nombre_paquete` instala el paquete y lo registra en
el *Pipfile*. Se recomienda definir una versión especifica ya que asi
quedará registrado tambien en el fichero *Pipfile*.
-   `pipenv install --dev nombre_paquete` instala el paquete y lo
registra en el *Pipfile* como paquete solo para desarrollo. Útil para
instalar paquetes de testing (pytest) y de debug(ipdb,
django-debug-toolbar).

-   `pipenv lock` genera el fichero *Pipfile.lock*.
-   `pipenv shell` entra en el virtualenv. Con Ctrl-D se sale.

Conviene repasar las versiones puestas por si ha salido alguna versión
nueva con correcciones de seguridad. Una herramienta recomendada para
comprobar si los paquetes instalados son seguros es
[safety](https://pyup.io/safety).

Probar estáticos, compress offline y 404 sin DEBUG
--------------------------------------------------

El proyecto incluye el servidor
[WhiteNoise](http://whitenoise.evans.io/) para servir estáticos sin
DEBUG. Para usarlo hay que:

1.  Modificar el app.ini :

        DEBUG = False
        COMPRESS_ENABLED = True
        COMPRESS_OFFLINE = True
        ENABLE_WHITENOISE = True

2.  Generar estáticos offline (importante ejecutarlos en este orden) :

        python manage.py compress
        python manage.py collectstatic

3.  Arrancar el servidor :

        python manage.py runserver

En <http://localhost:8000> se verá la página con los estáticos
comprimidos y en una url que no exista se verá la página de 404 también
con los estáticos comprimidos.

**Es muy importante hacer este paso antes de subir a producción para
comprobar que no falla la generación ni la carga de estáticos offline.**

Tests
-----

El proyecto viene preparado para hacer tests con
[pytest](http://docs.pytest.org/) y
[Splinter](http://splinter.readthedocs.io/). También está configurado
para que pase el [Flake8](http://flake8.pycqa.org/) y falle si no se
cumplen sus reglas básicas.

Toda la configuración de pytest y flake8 está en el archivo
*src/main/setup.cfg*.

El proyecto incluye algunos tests básicos de ejemplo en
*src/main/tests*.

Ejemplos de ejecución:

-   `pytest` lanza todos los tests.
-   `pytest -s` lanza todos los tests y se detendrá si encuentra algún
    punto de ruptura.
-   `pytest -m unit_test` ejecuta solo los tests unitarios.
-   `pytest -m integration_test` ejecuta solo los tests de integración
    (acceso a APIs, BDs...).
-   `pytest -m functional_test` ejecuta solo los tests funcionales
    (abren un navegador).
-   `pytest -m "not functional_test"` ejecuta todos los tests menos los
    funcionales.
-   `pytest --markers` lista todo los markers.

`unit_test`, `integration_test` y `functional_test` son
[markers](http://doc.pytest.org/en/latest/example/markers.html)
definidos en el *setup.cfg* y usados en los tests.

### Base de datos de tests

Por defecto la base de datos para los tests es una sqlite en memoria (la
opción más rápida).

En el app.ini se encuentra comentada la configuración de la base de datos parra los tests:

    TEST_DATABASE_USER      = iris
    TEST_DATABASE_ENGINE    = django.contrib.gis.db.backends.postgis
    TEST_DATABASE_HOST      = localhost
    TEST_DATABASE_NAME      = iris2_test_db
    TEST_DATABASE_PORT      = 5432
    TEST_DATABASE_PASSWORD  = 1234

En caso de no usar sqlite para los tests, en el setup.cfg está
configurado para que se reutilice la BD sin destruirse y sin ejecutar
migraciones (hace autoinspect de modelos para crearla la primera vez).

Si los requisitos de BD de los tests son muy especiales y no basta con
el *app.ini*, al final del *settings.py* está la clase `Test` que
permite sobreescribir la conf de BD para los tests.

### flake8 y flake8-django

Como ya hemos dicho, se utiliza el flake8 para comprobación de reglas de PEP8. Del mismo modo, se ha instalado un plugin
de flake8 llamado [flake8-django](https://github.com/rocioar/flake8-django), el cual se integra perfectamente con pytest.
Si tenemos un modelo con un `CharField` definido así:

```python
class InputChannel(models.Model):
    description = models.CharField(max_length=40, null=True)
```

Nos saltará un aviso:
```
―――――――――――――――――――――――――――――――――――――――――――――――― FLAKE8-check ――――――――――――――――――――――――――――――――――――――――――――――
/home/user/workspace/iris/iris2/src/iris_masters/models.py:105:19: DJ01 null=True not recommended to be used in CharField
```
Si quisiesmos desactivar alguno de los checks, basta modificar el fichero setup.cfg en la sección de flake8:
```ini
[flake8]
ignore = DJ01
```

Emails
------

Django Yubin ya viene configurado de serie. Antes de salir a prod
revisar que las direcciones de envío de emails estén bien configuradas
para evitar problemas de bloqueos de spam.

healtcheck
----------

En health se define los health checks que la aplicación debe hacer para
mostrar sus estado. Esta librería permite obtener la información en
formato json y html y escribir nuestros propios healtchecks
sobreescribiendo las clases de la librería. Estan activados los
healtchecks más básicos de base de datos y caché.

La librería utilizada es *django-health-check*

Uno de los helthchecks básicos instalados es health\_check.cache. Éste
requiere tener un sistema de cache configurado. En el app.ini viene
preconfigurada la cache de redis:

    CACHE_TYPE              = redis
    REDIS_HOST              = localhost
    CACHE_REDIS_DB          = 0
    REDIS_PORT              = 6379
    CACHE_MAX_ENTRIES       = 10000
    CACHE_TIMEOUT           = 3600
    CACHE_PREFIX            = iris2-community

En tal caso hay que tener en cuenta que este helthcheck necesita una
versión 3.x.y de *redis-server*.


Desarrollo con Docker
=====================

Opcionalmente, es posible desarrollar usando [Docker](https://docs.docker.com/get-started/).
El arranque de docker se controla a través de la herramienta [make](https://www.gnu.org/software/make/).
Debemos tener Docker instalado en nuestra máquina y [docker-compose](https://docs.docker.com/compose/install/).

Instalación y puesta en marcha
------------------------------

-   Crear configuración local :

        cd src
        cp app.ini.template app.ini

-   Revisar app.ini.

-   Las variables de entorno que difieren de desarrollo en local a Docker
    están en el fichero *env_devel*.

-   Crear base de datos y superuser :

        cd ..
        make migrate
        make manage c=createsuperuser

-   Arrancar servidor de desarrollo :

        make

Comandos de make
----------------

Los siguientes comandos están disponibles:

-   `make` Construye la imagen Docker, aplica migraciones e inicia el runserver.
-   `make runserver` Inicia el runserver.
-   `make migrate` Aplica las migraciones.
-   `make manage c=<COMANDO>` Ejecuta el comando python manage.py
    \<COMANDO\>

Migraciones
-----------

Si vemos que nuestro proyecto tarda mucho tiempo al ejecutar un `python manage.py migrate` debemos revisar si podemos
realizar una operación de optimización de migraciones mediante el método de
[squash migrations](https://docs.djangoproject.com/en/2.2/topics/migrations/#squashing-migrations). Si por el motivo
que fuese, no podemos hacer esta operación, podemos usar la libreria (en fase experimental)
[django-fast-migrations](https://github.com/APSL/django-fast-migrations) la cual ejecuta las migraciones aplicación a
aplicación, haciendo que se ejecuten más rapido. Tal y como dice la documentación, simplemente tenemos que hacer lo siguiente:

1. Instalar
```
pipenv install django-fast-migrations
```

2. Añadir  ``'django_fast_migrations'`` a ``INSTALLED_APPS`` de `settings.py`.

3. Ejecutar `python manage.py migrate_by_app --execute`
