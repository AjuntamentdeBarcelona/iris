# IRIS Community

IRIS es una aplicación creada por el Ajuntament de Barcelona para la comunicación y gestión entre la ciudadanía y las
instituciones. Con IRIS, los diferentes  actores sociales pueden comunicar sus sugerencias, peticiones, quejas o
incidencias de forma que toda la gestión queda registrada, clasificada en función de su naturaleza y derivada
automáticamente al personal responsable de tratarla.

Las peticiones (fichas) se organizan y asignan en función de un árbol de temáticas que definen las tareas que la
institución puede desarrollar en el ámbito de sus competencias. IRIS permite configurar cada temática para personalizar
el flujo necesario para resolver la tarea y dar una respuesta satisfactoria al solicitante: desde los pasos que se
deben dar hasta la persona que debería resolverla.

Además del árbol de temáticas para clasificar las peticiones, la aplicación incorpora un sistema de grupos de trabajo
que marca la estructura organizativa de la institución y garantiza que la ficha solo sea vista por quién va a
resolver la solicitud. Cada grupo y cada usuario tienen unos permisos asociados para gestionar quién y qué puede hacer
cada acción.

El árbol de tareas y la jerarquía de grupos están relacionados para hacer posible la derivación, es decir, la asignación
automática de la tarea a medida que avanza de estado.
Con cada temática se configura qué grupo resolverá las tareas asociadas en base criterios de asignación
directa o territorial. La derivación territorial permite asignar tareas por distrito o basado en áreas definidas en la
base de datos geoespacial.

### IRIS y IRIS2

> IRIS tiene mucha historia, este es IRIS2, reimplementación de la primera versión que estuvo funciona con éxito durante años.
Algunas decisiones de diseño y limitaciones están basadas en facilitar la migración de IRIS1 a IRIS2, reducir el riesgo
y facilitar la transición.

## ¿Cómo empezar?

### Demostración y pruebas

Para hacer realizar una demostración de IRIS y probar sus funcionalidades, hay dos opciones:
- [Que tu departamento de IT prepare una demo en su PC local](./docs/Demo.md).
- Contactar con un proveedor de IRIS.

Ahora mismo no podemos ofrecer un entorno de pruebas siempre disponible.

### Configuración y despliegue

Para desplegar IRIS en tu entorno, puedes seguir [la guía y recomendaciones de despliegue](./docs/Despliegue.md).

Una vez desplegado puedes seguir las [intrucciones de configuración](./docs/Configuración.md) para personalizar IRIS y ponerlo en marcha.

### Desarrollo y diseño técnico

IRIS ofrece múltiples opciones de configuración para adaptarse a tus casos de uso, si no fueran suficiente, su diseño
permite que puedas añadir paquetes y extensiones. Aquí encontrarás las
[instrucciones para lanzar el proyecto en local](./docs/Development.md) con docker-compose o con un entorno virtual
de python.

Para empezar a desarrollar es recomendable conocer la [arquitectura de IRIS](./docs/Arquitectura.md) y las
documentaciones de cada componente. Por ejemplo, la [documentación del backend](./documentation.md).

Para hacer contribuciones a la versión community puedes seguir la [guía y normas de contribución.](./CONTRIBUTING.md)


