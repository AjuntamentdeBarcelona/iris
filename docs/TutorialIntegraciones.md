# Tutorial sobre importación de integraciones en IRIS

Como ya habrás visto en el documento de [Configuración](./docs/Configuración.md) algunas de las variables de configuración se han marcado con <b>(*)</b>. Esto significa que el valor de estas apunta a un módulo, función o clase de Python. Por defecto dichas variables apuntan a módulos, funciones o clases ya definidas en IRIS. Así pues, si se quiere modificar el comportamiento, en estos casos las variables deben apuntar al lugar dónde se encuentren las integraciones correspondientes.

Los módulos, funciones o clases que se introduzcan pueden provenir de módulos propios o módulos de terceros. Si se trata de un módulo propio, primero se debe incluir el módulo en la carpeta [src](./src/) del proyecto. En cambio, si el módulo proviene de una librería de terceros, esta se debe instalar en el proyecto (dependiendo de como se levante, habrá que actualizar el [Pipfile](./Pifile) o los archivos en [requirements](./requirements/))

### Importación de módulos

Siguiendo lo explicado en el párrafo anterior, para que la variable apunte al módulo deseado en app.ini:

```
# app.ini

[Módulo propio]
NOMBRE_VARIABLE          = nombre_modulo

[Módulo de terceros]
NOMBRE_VARIABLE          = nombre_librería.nombre_modulo
```

Esta sintaxis admite submódulos siempre que se acceda a ellos con puntos ".":

```
# app.ini

[Módulo propio]
NOMBRE_VARIABLE          = nombre_modulo.nombre_submodulo

[Módulo de terceros]
NOMBRE_VARIABLE          = nombre_librería.nombre_modulo.nombre_submodulo
```

### Importación de funciones y clases

En el caso de funciones y clases la sintaxis sigue el mismo patrón. La única diferencia es que por convenio las clases se definen en CamelCase y las funciones en snake_case. Todo dependerá de como estén definidas en origen las integraciones en cuestión. Así pues, en app.ini:

```
# app.ini

[Función propia]
NOMBRE_VARIABLE          = nombre_modulo.nombre_funcion

[Función de terceros]
NOMBRE_VARIABLE          = nombre_librería.nombre_modulo.nombre_funcion

[Clase propia]
NOMBRE_VARIABLE          = nombre_modulo.NombreClase

[Función de terceros]
NOMBRE_VARIABLE          = nombre_librería.nombre_modulo.NombreClase
```

Con esto claro se pueden personalizar todas las variables de configuración con <b>(*)</b> que se desee. Recordamos que cabe respetar la estructura de los módulos, funciones o clases que vienen por defecto en IRIS para que la implementación de integraciones personalizadas sea adecuada.