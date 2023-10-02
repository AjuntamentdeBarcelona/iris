# Configuración de IRIS2 Community

## Backend

IRIS ofrece opciones de configuración a diferentes niveles:
- Variables de entorno (env)
- Parámetros de configuración globales (DB)
- A nivel de objetos de negocio como las temáticas (DB)

En esta sección cubriremos los parámetros de configuración a partir del entorno.

> En desarrollo, para definir las variables de entorno en desarrollo, podéis indicar su valor en el archivo app.ini antes de arrancar el backend.
Cualquier modificación de dicho archivo con el backend levantado no se verá reflejada, sino que tendrás que reiniciar el servidor.

Por ejemplo, la variable `PUBLIC_API_ACTIVE` permite indicar si la API pública está activada (si está activada entonces los endpoints correspondientes de esa API serán acesibles). Por defecto esta variable toma el valor `False` por lo que si queremos activarla debemos especificarlo:

```
# app.ini

PUBLIC_API_ACTIVE           = True
```

El procedimiento es el mismo para otras variables.
En caso que el valor sea una cadena de caracteres no se debe escribir con comillas (\',\"), hay que introducirlo como texto plano.
Para configurar estas integraciones puedes leer el [artículo para dar implementación a las integraciones](./TutorialIntegraciones.md).

A continuación detallamos las variables que se pueden configurar y, cuando sea necesario, una explicación de las mismas. En la descripción de algunas incluímos un asterisco (<b>*</b>) para indicar que se trata de una integración que puede importarse con un módulo o clase personalizado. Por defecto IRIS proporciona estos módulos y clases pero si se desea se pueden cambiar. Para ver el funcionamiento de este tipo de variables recomendamos leer el [documento sobre importación de integraciones](./docs/TutorialIntegraciones.md).

### Minio

Minio es la opción para almacenar ficheros de esta aplicación. Aún así, puedes trabajar con cualquiera de los backends de almacenamiento de ficheros de django.

Las variables de configuración de minio que debes fijar son las siguientes:

```
MINIO_HOST = localhost
MINIO_PORT = 9000
MINIO_SECRET_FILE = False
MINIO_SECURE = true
MINIO_BUCKET = iris2-community
MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = true
MINIO_ACCESS_KEY = AKIAIOSFODNN7EXAMPLE
MINIO_SECRET_KEY = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

### Idioma

Actualmente la configuración de idioma en el Backend se lleva a cabo mediante las variables LANGUAGE_CODE y LANGUAGES.
Estas variables se tienen que configurar directamente en [`main.settings`](./src/main/settings.py). Por defecto los valores son:

```python
# settings.py

LANGUAGE_CODE = "es"
LANGUAGES = (
    ("es", gettext_lazy("Spanish")),
    ("gl", gettext_lazy("Galician")),
    ("en", gettext_lazy("English")),
)
```

Estas variables se encargan de seleccionar los idiomas en los que se muestran los datos en el Backend, ya sea creando URLs específicas según el idioma o configurando las respuestas.

Para las fichas y la API pública, en [`main.utils`](./src/main/utils.py) encontramos la variable LANGUAGES (diferente a la de configuración):

```python
# utils.py

SPANISH = "es"
ENGLISH = "en"
GALICIAN = "gl"

LANGUAGES = (
    (SPANISH, _("Spanish")),
    (ENGLISH, _("English")),
    (GALICIAN, _("Galician")),
)
```

> Esta duplicidad de configuración será corregida en próximas versiones.

### CORS

Cuando la SPA del backoffice, o cualquier otro cliente que funcionen sobre web, esté desplegado en un dominio diferente
al backend se deberá añadir al whitelist del CORS.

- CORS_ORIGIN_WHITELIST: lista de dominios a los que se quiere permitir el acceso a los servicios de IRIS.

### Celery

> IRIS ya viene con una configuración recomendada para las tareas periódicas, pero a nivel de operativa es importante
> conocer que tareas se ejecutan y la frecuencia. También por si es necesario añadir tareas personalizadas o custom.

Variable que apunta a la función que gestiona las tareas periódicas que ejecutará Celery a través de beat.
Debe devolver un diccionario al estilo de la variable [app.conf.beat_schedule](https://docs.celeryproject.org/en/stable/userguide/periodic-tasks.html#crontab-schedules):

El valor por defecto lo encontrarás en main.schedules.scheduled_tasks.

- SCHEDULE_BACKEND (<b>*</b>)

### Grupos

IRIS gestiona los permisos de usuario en parte con el modelo `Group`.
Cada grupo se tiene una matrícula que sirve para identificar la posición en un árbol de jerarquía.
Estas variables están relacionadas con la configuración de dicho modelo.

- DEFAULT_ADMIN: matrícula del administrador por defecto, se crear al lanzar los data checks. Si no se configura no se crea usuario por defecto.
- DEFAULT_ADMIN_PASSWORD: contraseña del administrador por defecto, se crear al lanzar los data checks.

Variables para crear los usuarios, grupos y perfiles por defecto.

- SET_DEFAULT_ADMIN_BACKEND: apunta a la función que establece el administrador por defecto. Debe admitir un `sender` y unos `**kwargs` como parámetros. En esta función se deben crear si no lo están el usuario administrador, el grupo coordinador (`Group`), el grupo de usuario (`UserGroup`) y el grupo que relaciona los dos anteriores (`GroupsUserGroup`). (<b>*</b>)
- SET_AMBIT_COORDINATORS_BACKEND: apunta a la función que establece los coordinadores y los asigna a los grupos correspondientes. También se encarga de gestionar los perfiles de administrador y sus grupos. Debe admitir un `sender` y unos `**kwargs` como parámetros. (<b>*</b>)
- SET_GROUP_PLATES_BACKEND = backend para establecer las matrículas de los grupos. Debe admitir un `sender` y unos `**kwargs` como parámetros. (<b>*</b>)

Otras variables:

- MAX_FILE_SIZE_GROUP_ICON: tamaño máximo de icono de grupo.

Variables legacy que desaparecerán:

- INTERNAL_GROUPS_SYSTEM: si es `True` se fijan los grupos en IRIS2, si es `False` se cargan desde Control User.
- IRIS_CTRLUSER_APPNAME: nombre de la app en Control User.

# GEO

IRIS permite seleccionar en el mapa la ubicación para las fichas. La funcionalidad y la asignación de estos datos depende del mapa usado, por lo que se deben especificar valores como la [zona UTM](https://en.wikipedia.org/wiki/Universal_Transverse_Mercator_coordinate_system) o el [SRID](https://gis.stackexchange.com/questions/131363/choosing-srid-and-what-is-its-meaning).

- GEO_UTM_ZONE: código de la zona UTM para la configuración del servicio de distribución geográfica. Debe ser un entero.
- GEO_SRID: identificador de referencia espacial para la configuración del servicio de distribución geográfica. Debe ser un entero.
- GEOCODER_SERVICES_CLASS: apunta a la clase de los servicios de geocodificación. (<b>*</b>)
- GEOCODER_CLASS: apunta a la clase de geocodificación. Debe tener una serie de métodos específicos para gestionar la información geográfica (ver la clase [`GisGeocoder`](./src/geo/geocode.py) y su clase padre [`BaseGeocoder`](./src/record_cards/record_actions/geocode.py) para ver qué métodos se deben implementar). (<b>*</b>)

Al seleccionar ubicaciones en el mapa interactivo, se lanzan peticiones a la API de [Nominatim](https://nominatim.org/) para buscar lugares en Open Street Map ([OSM](https://www.openstreetmap.org/)). En IRIS tenemos una serie de variables opcionales que permiten afinar la búsqueda.

- POSTAL_CODE: código postal. Se puede introducir un número de 1 a 5 dígitos. En caso de tener menos de 5 dígitos se consideran todos los códigos postales rellenando los dígitos restantes. Ejemplo: POSTAL_CODE = 071 sirve para indicar los códigos postales de la forma 071XX.
- CITY: ciudad.
- COUNTY: provincia.
- STATE: comunidad autónoma.
- COUNTRY: país.

Una vez obtenidos los datos de Nominatim, necesitamos tratarlos para que se adapten a los de IRIS. Para ello necesitamos una lista de los tipos de vía que se deben clasificar (preferiblemente la lista debería depender del idioma de la aplicación). Además, Nominatim proporciona un [tipo de vía](https://nominatim.org/release-docs/develop/api/Output/#addressdetails) que en la mayoría de casos no nos sirve.

- STREET_TYPE_TRANSLATION_LANGUAGE_CODE: debe contener el código del idioma mediante el que se quiere configurar el tipo de vía en mayúsculas.
- STREET_TYPE_MAP_GENERATOR: apunta a una función que genera una lista de los tipos de vía. Debe admitir un único parámetro que usará el código del idioma de la variable anterior. (<b>*</b>)
- IGNORED_KEYS_LIST_GENERATOR: apunta a una función que devuelve un listado de tipos de vía a ignorar al recibir datos de Nominatim. (<b>*</b>)

 # Tareas de integración

Como hemos comentado al inicio del documento, hay algunas integraciones que vienen por defecto en IRIS pero que se pueden modificar. Algunas las hemos ido comentando pero nos quedan las relacionadas con las respuestas y su generación.

- LETTER_RESPONSE_ENABLED: si es `True` habilita el envío de cartas como respuesta, si es `False` lo deshabilita.
- PDF_BACKEND: apunta a una función para crear PDFs para las respuestas. Debe admitir como parámetro el id de una ficha y opcionalmente el parámetro `file_name` con el nombre del archivo a generar. Esta función tiene que guardar un archivo PDF a partir de un template relacionado con la ficha correspondiente (ver el funcionamiento de [`create_pdf`](./src/integrations/services/pdf/hooks.py) para entender la implementación). (<b>*</b>)

Variables relacionadas con el envío de SMS. En las tareas de integración, celery gestiona en la cola de alta prioridad el envío de SMS.

- SMS_BACKEND: apunta a una función para gestionar el envío de mensajes vía SMS. Debe admitir como parámetro el id de una ficha y opcionalmente los parámetros `send_real_sms`, `buroSMS`, `application`, `destination`,`user`. Debe devolver los datos al hacer POST a la API de SMS correspondiente. (<b>*</b>)
- SMS_BACKEND_PENDENTS: apunta a una función que envía los SMS con la función configurada en la variable anterior para enviar los SMS con <em>delay</em>. (<b>*</b>)

### Data checks

Los <em>data checks</em> comprueban que los datos necesarios para el funcionamiento de IRIS están en la base de datos. Si hay datos que faltan se crean al lanzar los <em>data checks</em>.

- EXECUTE_DATA_CHEKS: si es `True` se fuerza la ejecución de los data checks al levantar el servidor.

Estas dos configuraciones tienen que estar siempre a la par ya que en caso contrario el funcionamiento puede no ser el deseado.

### Mario

Mario es un servicio proporcionado por [APSL](https://apsl.net) en base al texto de la petición de un ciudadano, sugiere una temática.
Este servicio funciona concretamente con las temáticas del Ajuntament de Barcelona, pero se puede adaptar para otros.

- URL_PA_MARIO: variable que indica la URL de la API pública en la que se trata el servicio de búsqueda Mario. Si se configura, el sistema interpreta que Mario está habilitado y la funcionalidad de este se aplicará. En caso contrario se realizará la búsqueda se realizará por palabras clave.

### Twitter:

IRIS permite un flujo concreto para gestionar peticiones de twitter. Sencillamente se basa en crear una ficha con el
texto de un tweet, registrar el usuario que envió el mensaje y elegir la temática. Una vez seleccionada la persona recibirá
un mensaje directo sugiriendole que cree la ficha en IRIS con una URL a la temática concreta.

- URL_PA_TWITTER: variable que indica la URL de la API pública en la que se trata Twitter. Si se configura, el sistema interpreta que Twitter está habilitado y la funcionalidad que proporcionan el resto de variables en esta subsección se tendrán en cuenta.

Seguido encontramos variables para poder acceder a la API de Twitter. Para saber qué valores deben tener, recomendamos ver la [guía para acceder a la API de Twitter](https://developer.twitter.com/en/docs/twitter-api/getting-started/getting-access-to-the-twitter-api):

- TWITTER_ACCESS_TOKEN
- TWITTER_TOKEN_SECRET
- TWITTER_CONSUMER_KEY
- TWITTER_CONSUMER_SECRET

- TWITTER_BACKEND: apunta a la función que gestiona el envío de mensajes directos vía Twitter.
Debe aceptar como parámetros el destinatario `username` (nombre de usuario de Twitter sin @) y el mensaje `text`.
Debe devolver los datos al hacer POST a la API de Twitter [enviando un mensaje privado](https://developer.twitter.com/en/docs/twitter-api/v1/direct-messages/sending-and-receiving/api-reference/new-event). (<b>*</b>)


### SFTP

Variables relacionadas con el protocolo de transferencia de archivos (SFTP). En las tareas de integración, celery gestiona en la cola de baja prioridad la validación de <em>batch files</em> con los datos del trimestre en cuestión. En ese punto si se quieren transferir archivos a una máquina remota hay que configurar el SFTP:

- SFTP_HOSTNAME: Nombre del Host de la máquina remota o su IP.
- SFTP_USERNAME: Nombre de usuario en la máquina remota.
- SFTP_PASSWORD: Contraseña en la máquina remota.
- SFTP_PATH: Directorio de trabajo en al que se moverán los archivos.

### Paquetes externos:

- [DRF_CHUNKED_UPLOAD_*](https://github.com/jkeifer/drf-chunked-upload#settings)
- [CACHALOT_*](https://django-cachalot.readthedocs.io/en/latest/quickstart.html#settings): ***NO TOCAR CONFIGUACIÓN SI NO SE CONOCE SU FUNCIONAMIENTO, AFECTA AL RENDIMIENTO DE LA APLICACIÓN.**
- [MAILER_*](https://django-yubin.readthedocs.io/en/latest/settings.html): implementado con Django Yubin.
