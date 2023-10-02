# IRIS2 - Backoffice

## Índice

[Encontrarás las instrucciones de instalación en el Readme del proyecto](README.md)

1. [Estructura del proyecto](#1-estructura-del-proyecto)
    1. [Aplicaciones core](#aplicaciones-core)
        1. [Gráfico aplicaciones core](#gráfico-aplicaciones-core)
    1. [Aplicaciones extra funcionalidades](#aplicaciones-extra-funcionalidades)
    1. [Abstracción de las integraciones](#abstracción-de-las-integraciones)
    1. [Estrategia de testing](#estrategia-de-testing)
    1. [Paquete main](#paquete-main)
1. [Base de datos](#2-base-de-datos)
    1. [Modelo base datos](#modelo-base-datos)
1. [APIS](#3-apis)
    1. [API Privada](#api-privada)
    2. [API Pública](#api-pública)
    3. [API Pública Autentificada](#api-pública-autentificada)
    4. [API Proxy XML](#api-proxy-xml)
1. [Puntos más relevantes en la implementación](#4-puntos-más-relevantes-en-la-implementación)
    1. [Rest-framework](#rest-framework)
    1. [Open-API](#generar-open-api)
    1. [Celery](#celery)
    1. [Safe-delete](#safe-delete)
    1. [Cachalot](#cachalot)
    1. [Postmigración](#postmigración)
    1. [Permisos](#Permisos)
    1. [Traducciones](#Traducciones)
    1. [Árbol de temáticas](#árbol-de-temáticas)
    1. [Árbol de grupos y concepto de ámbito](#árbol-de-grupos-y-concepto-de-ámbito)
    1. [Multifichas](#multificha)
    1. [Fichas similares y unifichas](#fichas-similares-y-unifichas)
    1. [Máquina de estados: procesos y estados](#máquina-de-estados-procesos-y-estados)
    1. [Acciones ficha](#acciones-de-la-ficha)
        1. [Procesos](#procesos)
    1. [Derivación fichas](#derivación-fichas)
    1. [Reasignaciones](#reassignations)
    1. [Cambio de temática](#cambio-de-temática)
    1. [Tramitación externa](#tramitación-externa)
    1. [Búsqueda de solicitantes](#búsqueda-de-solicitantes)
    1. [Templates de respuesta y variables](#templates-de-respuesta-y-variables)
    1. [Subidas de ficheros](#subida-de-ficheros)
    1. [Anonimizar solicitantes](#anonimizacin-de-solicitantes)
    1. [Conversaciones](#comunicaciones)
    1. [Geocoding](#geocoding)
1. [Relación con otros sistemas](#5-relación-con-otros-sistemas)
    1. [Autenticación OAM y APIM](#backend-de-autenticación)
    1. [Minio](#minio)
1. [Operativa](#6-operativa)
    1. [Lanzar tests](#lanzar-tests)
    1. [Configuración](#configuración)
    1. [Despliegue](#despliegue)
    1. [Otros comandos](#commands)


## 1. Estructura del proyecto

El proyecto de IRIS2 consiste en la actualización de la aplicación IRIS1, utilizada por el Ajuntament
de Barcelona para gestionar las tareas e incidencias del dia a dia en el Ajuntament. A continuación, las tareas
se conoceran como fichas. La funcionalidad principal de IRIS2 es la creación de fichas y el seguimiento de todo
su ciclo de vida mientras los trabajadores del Ajuntament la resuelven.

El backoffice de IRIS2 consiste en una SPA que se conecta a través de un
[API REST](https://rockcontent.com/es/blog/api-rest/) al core de la aplicación.
El core de la aplicación está programado utilizando el framework web [Django](https://www.djangoproject.com/).

Siguiendo los patrones de Django, el proyecto esta separado en diferentes django apps, que se pueden separar en dos
grandes grupos: aplicaciones core de negocio y aplicaciones que proveen funcionalidades para las aplicaciones de negocio.


### Aplicaciones core

Las aplicaciones core del proyecto son:
1. [iris_masters](./src/iris_masters): contiene los maestros de la aplicación, que se utilizan para configurar
el resto de entidades. Algunos ejemplos son: RecordType, RecordState, InputChannel, Reason, Announcement o Parameter.
2. [themes](./src/themes): contiene toda la funcionalidad relacionada con las temáticas, sus elementos y areas. Las
temáticas se utilizan para configurar las fichas y marcan el proceso que seguirán dentro de la aplicación.
3. [profiles](./src/profiles): contiene el modelado de los grupos, perfiles y permisos de los usuarios que utilizan
IRIS2. A partir de los grupos que tenga un usuario asignados podrá realizar un determinado conjunto de acciones en
la aplicación.
4. [record_cards](./src/record_cards): contiene el modelo de fichas y otros modelos para configurarlas, como las
ubicaciones o los solicitantes. Esta aplicación también dispone de todas las funcionalidades de las fichas, desde su
creación hasta la respuesta y cierre de estas.
5. [ariadna](./src/ariadna): contiene los registros de las peticiones de Ariadna que llegan a IRIS2.
6. [communications](./src/communications): aplicación que gestiona las conversaciones que se realizan en las fichas por
 los diferentes implicados, tanto las conversaciones internas como las externas, que serán respondidas a través del
 API pública.
7. [features](./src/features): sirve para gestionar las caracteríticas que se utilizan para configurar las temáticas y
las fichas.
8. [iris_templates](./src/iris_templates): incluye la gestión de las plantillas utilizadas para responder las fichas
por email, carta o sms.
9. [integrations](./src/integrations): aplicación que gestiona la relación de IRIS2 con otras aplicaciones o servicios
del Ajuntament.
10. [protocols](./src/protocols): aplicación que gestiona los protocolos a seguir al dar de alta una ficha en el
backoffice.
11. [public_api](./src/public_api): aplicación con un API REST para la web de ATE que permite consultar teḿaticas, dar
de alta fichas en IRIS2, consultar y reclamar fichas, responder comunicaciones, consultar las fichas del SSI y
otras funcionalidades.
12. [public_external_processing](./src/public_external_processing): aplicación con un API REST para la devolución de
fichas procesadas externamente.
13. [quioscs](./src/quioscs): integración para el servicio de QUIOSC que permite consultar temáticas y dar fichas de
alta en IRIS2.
14. [reports](./src/reports): aplicación para generar informes de fichas, temáticas o operadores
15. [support_info](./src/support_info): aplicación de soporte para el uso de IRIS2 o informaciones del Ajuntament a
sus empleados. Permite subir contenido de diferentes tipos.
16. [surveys](./src/surveys): aplicación para envio de encuestas y registro de sus respuestas que se rellenan desde la ATE.
17. [xml_proxy](./src/xml_proxy): integración para el servicio de XML que permite consultar temáticas, dar fichas de
alta en IRIS2 y reclamarlas.

#### Gráfico aplicaciones core

[![](https://mermaid.ink/img/eyJjb2RlIjoiZ3JhcGggVERcbiAgICBBW2lyaXNfbWFzdGVyc10gLS0-fGNvbmZpZ3wgQih0aGVtZXMpXG4gICAgQVtpcmlzX21hc3RlcnNdIC0tPnxjb25maWd8IEMocmVjb3JkX2NhcmRzKVxuICAgIEJbdGhlbWVzXSAtLT58Y29uZmlnfCBDKHJlY29yZF9jYXJkcylcbiAgICBEW2FyaWFkbmFdIC0tPnxjb25maWd8IEMocmVjb3JkX2NhcmRzKVxuICAgIEMocmVjb3JkX2NhcmRzKSAtLT4gfGNhbi1oYXZlfCBFW2NvbW11bmljYXRpb25zXVxuICAgIEYoZmVhdHVyZXMpIC0tPnxjb25maWd8IEMocmVjb3JkX2NhcmRzKVxuICAgIEYoZmVhdHVyZXMpIC0tPnxjb25maWd8IEJbdGhlbWVzXVxuICAgIEcoaXJpc190ZW1wbGF0ZXMpLS0-fGNvbmZpZ3wgQyhyZWNvcmRfY2FyZHMpXG4gICAgSShwcm90b2NvbHMpIC0tPiB8Y29uZmlnfCBDKHJlY29yZF9jYXJkcylcbiAgICBKKHB1YmxpY19hcGkpIC0tPiB8Y3JlYXRlL3JlYWQvY2xhaW18IEMocmVjb3JkX2NhcmRzKVxuICAgIEsocHVibGljX2V4dGVybmFsX3Byb2Nlc3NpbmcpIC0tPiB8cmV0dXJuL2NhbmNlbC9jbG9zZXwgQyhyZWNvcmRfY2FyZHMpXG4gICAgTChxdWlvc2NzKSAtLT4gfGNyZWF0ZS9jbGFpbXwgQyhyZWNvcmRfY2FyZHMpXG4gICAgQyhyZWNvcmRfY2FyZHMpIC0tPiB8Z2VuZXJhdGV8IE0ocmVwb3J0cylcbiAgICBCKHRoZW1lcykgLS0-IHxnZW5lcmF0ZXwgTShyZXBvcnRzKVxuICAgIFEocHJvZmlsZXMpIC0tPiB8Z2VuZXJhdGV8IE0ocmVwb3J0cylcbiAgICBOKHN1cHBvcnRfaW5mbylcbiAgICBPKHN1cnZleXMpXG4gICAgUCh4bWxfcHJveHkpIC0tPiB8Y3JlYXRlL3JlYWQvY2xhaW18IEMocmVjb3JkX2NhcmRzKVxuICAgIEFbaXJpc19tYXN0ZXJzXSAtLT4gSChpbnRlZ3JhdGlvbnMpXG4gICAgQih0aGVtZXMpIC0tPiBIKGludGVncmF0aW9ucylcbiAgICBDKHJlY29yZF9jYXJkcykgLS0-IEgoaW50ZWdyYXRpb25zKVxuICAgIFEocHJvZmlsZXMpIC0tPiB8Y29uZmlnfCBCKHRoZW1lcylcbiAgICBDKHJlY29yZF9jYXJkcykgLS0-IHxhc3NpZ25lZCB0b3wgUShwcm9maWxlcylcblxuICAgIFxuICAgIFxuICAgIFxuICAgIFxuICAgICIsIm1lcm1haWQiOnsidGhlbWUiOiJkZWZhdWx0IiwidGhlbWVWYXJpYWJsZXMiOnsiYmFja2dyb3VuZCI6IndoaXRlIiwicHJpbWFyeUNvbG9yIjoiI0VDRUNGRiIsInNlY29uZGFyeUNvbG9yIjoiI2ZmZmZkZSIsInRlcnRpYXJ5Q29sb3IiOiJoc2woODAsIDEwMCUsIDk2LjI3NDUwOTgwMzklKSIsInByaW1hcnlCb3JkZXJDb2xvciI6ImhzbCgyNDAsIDYwJSwgODYuMjc0NTA5ODAzOSUpIiwic2Vjb25kYXJ5Qm9yZGVyQ29sb3IiOiJoc2woNjAsIDYwJSwgODMuNTI5NDExNzY0NyUpIiwidGVydGlhcnlCb3JkZXJDb2xvciI6ImhzbCg4MCwgNjAlLCA4Ni4yNzQ1MDk4MDM5JSkiLCJwcmltYXJ5VGV4dENvbG9yIjoiIzEzMTMwMCIsInNlY29uZGFyeVRleHRDb2xvciI6IiMwMDAwMjEiLCJ0ZXJ0aWFyeVRleHRDb2xvciI6InJnYig5LjUwMDAwMDAwMDEsIDkuNTAwMDAwMDAwMSwgOS41MDAwMDAwMDAxKSIsImxpbmVDb2xvciI6IiMzMzMzMzMiLCJ0ZXh0Q29sb3IiOiIjMzMzIiwibWFpbkJrZyI6IiNFQ0VDRkYiLCJzZWNvbmRCa2ciOiIjZmZmZmRlIiwiYm9yZGVyMSI6IiM5MzcwREIiLCJib3JkZXIyIjoiI2FhYWEzMyIsImFycm93aGVhZENvbG9yIjoiIzMzMzMzMyIsImZvbnRGYW1pbHkiOiJcInRyZWJ1Y2hldCBtc1wiLCB2ZXJkYW5hLCBhcmlhbCIsImZvbnRTaXplIjoiMTZweCIsImxhYmVsQmFja2dyb3VuZCI6IiNlOGU4ZTgiLCJub2RlQmtnIjoiI0VDRUNGRiIsIm5vZGVCb3JkZXIiOiIjOTM3MERCIiwiY2x1c3RlckJrZyI6IiNmZmZmZGUiLCJjbHVzdGVyQm9yZGVyIjoiI2FhYWEzMyIsImRlZmF1bHRMaW5rQ29sb3IiOiIjMzMzMzMzIiwidGl0bGVDb2xvciI6IiMzMzMiLCJlZGdlTGFiZWxCYWNrZ3JvdW5kIjoiI2U4ZThlOCIsImFjdG9yQm9yZGVyIjoiaHNsKDI1OS42MjYxNjgyMjQzLCA1OS43NzY1MzYzMTI4JSwgODcuOTAxOTYwNzg0MyUpIiwiYWN0b3JCa2ciOiIjRUNFQ0ZGIiwiYWN0b3JUZXh0Q29sb3IiOiJibGFjayIsImFjdG9yTGluZUNvbG9yIjoiZ3JleSIsInNpZ25hbENvbG9yIjoiIzMzMyIsInNpZ25hbFRleHRDb2xvciI6IiMzMzMiLCJsYWJlbEJveEJrZ0NvbG9yIjoiI0VDRUNGRiIsImxhYmVsQm94Qm9yZGVyQ29sb3IiOiJoc2woMjU5LjYyNjE2ODIyNDMsIDU5Ljc3NjUzNjMxMjglLCA4Ny45MDE5NjA3ODQzJSkiLCJsYWJlbFRleHRDb2xvciI6ImJsYWNrIiwibG9vcFRleHRDb2xvciI6ImJsYWNrIiwibm90ZUJvcmRlckNvbG9yIjoiI2FhYWEzMyIsIm5vdGVCa2dDb2xvciI6IiNmZmY1YWQiLCJub3RlVGV4dENvbG9yIjoiYmxhY2siLCJhY3RpdmF0aW9uQm9yZGVyQ29sb3IiOiIjNjY2IiwiYWN0aXZhdGlvbkJrZ0NvbG9yIjoiI2Y0ZjRmNCIsInNlcXVlbmNlTnVtYmVyQ29sb3IiOiJ3aGl0ZSIsInNlY3Rpb25Ca2dDb2xvciI6InJnYmEoMTAyLCAxMDIsIDI1NSwgMC40OSkiLCJhbHRTZWN0aW9uQmtnQ29sb3IiOiJ3aGl0ZSIsInNlY3Rpb25Ca2dDb2xvcjIiOiIjZmZmNDAwIiwidGFza0JvcmRlckNvbG9yIjoiIzUzNGZiYyIsInRhc2tCa2dDb2xvciI6IiM4YTkwZGQiLCJ0YXNrVGV4dExpZ2h0Q29sb3IiOiJ3aGl0ZSIsInRhc2tUZXh0Q29sb3IiOiJ3aGl0ZSIsInRhc2tUZXh0RGFya0NvbG9yIjoiYmxhY2siLCJ0YXNrVGV4dE91dHNpZGVDb2xvciI6ImJsYWNrIiwidGFza1RleHRDbGlja2FibGVDb2xvciI6IiMwMDMxNjMiLCJhY3RpdmVUYXNrQm9yZGVyQ29sb3IiOiIjNTM0ZmJjIiwiYWN0aXZlVGFza0JrZ0NvbG9yIjoiI2JmYzdmZiIsImdyaWRDb2xvciI6ImxpZ2h0Z3JleSIsImRvbmVUYXNrQmtnQ29sb3IiOiJsaWdodGdyZXkiLCJkb25lVGFza0JvcmRlckNvbG9yIjoiZ3JleSIsImNyaXRCb3JkZXJDb2xvciI6IiNmZjg4ODgiLCJjcml0QmtnQ29sb3IiOiJyZWQiLCJ0b2RheUxpbmVDb2xvciI6InJlZCIsImxhYmVsQ29sb3IiOiJibGFjayIsImVycm9yQmtnQ29sb3IiOiIjNTUyMjIyIiwiZXJyb3JUZXh0Q29sb3IiOiIjNTUyMjIyIiwiY2xhc3NUZXh0IjoiIzEzMTMwMCIsImZpbGxUeXBlMCI6IiNFQ0VDRkYiLCJmaWxsVHlwZTEiOiIjZmZmZmRlIiwiZmlsbFR5cGUyIjoiaHNsKDMwNCwgMTAwJSwgOTYuMjc0NTA5ODAzOSUpIiwiZmlsbFR5cGUzIjoiaHNsKDEyNCwgMTAwJSwgOTMuNTI5NDExNzY0NyUpIiwiZmlsbFR5cGU0IjoiaHNsKDE3NiwgMTAwJSwgOTYuMjc0NTA5ODAzOSUpIiwiZmlsbFR5cGU1IjoiaHNsKC00LCAxMDAlLCA5My41Mjk0MTE3NjQ3JSkiLCJmaWxsVHlwZTYiOiJoc2woOCwgMTAwJSwgOTYuMjc0NTA5ODAzOSUpIiwiZmlsbFR5cGU3IjoiaHNsKDE4OCwgMTAwJSwgOTMuNTI5NDExNzY0NyUpIn19LCJ1cGRhdGVFZGl0b3IiOmZhbHNlfQ)](https://mermaid-js.github.io/mermaid-live-editor/#/edit/eyJjb2RlIjoiZ3JhcGggVERcbiAgICBBW2lyaXNfbWFzdGVyc10gLS0-fGNvbmZpZ3wgQih0aGVtZXMpXG4gICAgQVtpcmlzX21hc3RlcnNdIC0tPnxjb25maWd8IEMocmVjb3JkX2NhcmRzKVxuICAgIEJbdGhlbWVzXSAtLT58Y29uZmlnfCBDKHJlY29yZF9jYXJkcylcbiAgICBEW2FyaWFkbmFdIC0tPnxjb25maWd8IEMocmVjb3JkX2NhcmRzKVxuICAgIEMocmVjb3JkX2NhcmRzKSAtLT4gfGNhbi1oYXZlfCBFW2NvbW11bmljYXRpb25zXVxuICAgIEYoZmVhdHVyZXMpIC0tPnxjb25maWd8IEMocmVjb3JkX2NhcmRzKVxuICAgIEYoZmVhdHVyZXMpIC0tPnxjb25maWd8IEJbdGhlbWVzXVxuICAgIEcoaXJpc190ZW1wbGF0ZXMpLS0-fGNvbmZpZ3wgQyhyZWNvcmRfY2FyZHMpXG4gICAgSShwcm90b2NvbHMpIC0tPiB8Y29uZmlnfCBDKHJlY29yZF9jYXJkcylcbiAgICBKKHB1YmxpY19hcGkpIC0tPiB8Y3JlYXRlL3JlYWQvY2xhaW18IEMocmVjb3JkX2NhcmRzKVxuICAgIEsocHVibGljX2V4dGVybmFsX3Byb2Nlc3NpbmcpIC0tPiB8cmV0dXJuL2NhbmNlbC9jbG9zZXwgQyhyZWNvcmRfY2FyZHMpXG4gICAgTChxdWlvc2NzKSAtLT4gfGNyZWF0ZS9jbGFpbXwgQyhyZWNvcmRfY2FyZHMpXG4gICAgQyhyZWNvcmRfY2FyZHMpIC0tPiB8Z2VuZXJhdGV8IE0ocmVwb3J0cylcbiAgICBCKHRoZW1lcykgLS0-IHxnZW5lcmF0ZXwgTShyZXBvcnRzKVxuICAgIFEocHJvZmlsZXMpIC0tPiB8Z2VuZXJhdGV8IE0ocmVwb3J0cylcbiAgICBOKHN1cHBvcnRfaW5mbylcbiAgICBPKHN1cnZleXMpXG4gICAgUCh4bWxfcHJveHkpIC0tPiB8Y3JlYXRlL3JlYWQvY2xhaW18IEMocmVjb3JkX2NhcmRzKVxuICAgIEFbaXJpc19tYXN0ZXJzXSAtLT4gSChpbnRlZ3JhdGlvbnMpXG4gICAgQih0aGVtZXMpIC0tPiBIKGludGVncmF0aW9ucylcbiAgICBDKHJlY29yZF9jYXJkcykgLS0-IEgoaW50ZWdyYXRpb25zKVxuICAgIFEocHJvZmlsZXMpIC0tPiB8Y29uZmlnfCBCKHRoZW1lcylcbiAgICBDKHJlY29yZF9jYXJkcykgLS0-IHxhc3NpZ25lZCB0b3wgUShwcm9maWxlcylcblxuICAgIFxuICAgIFxuICAgIFxuICAgIFxuICAgICIsIm1lcm1haWQiOnsidGhlbWUiOiJkZWZhdWx0IiwidGhlbWVWYXJpYWJsZXMiOnsiYmFja2dyb3VuZCI6IndoaXRlIiwicHJpbWFyeUNvbG9yIjoiI0VDRUNGRiIsInNlY29uZGFyeUNvbG9yIjoiI2ZmZmZkZSIsInRlcnRpYXJ5Q29sb3IiOiJoc2woODAsIDEwMCUsIDk2LjI3NDUwOTgwMzklKSIsInByaW1hcnlCb3JkZXJDb2xvciI6ImhzbCgyNDAsIDYwJSwgODYuMjc0NTA5ODAzOSUpIiwic2Vjb25kYXJ5Qm9yZGVyQ29sb3IiOiJoc2woNjAsIDYwJSwgODMuNTI5NDExNzY0NyUpIiwidGVydGlhcnlCb3JkZXJDb2xvciI6ImhzbCg4MCwgNjAlLCA4Ni4yNzQ1MDk4MDM5JSkiLCJwcmltYXJ5VGV4dENvbG9yIjoiIzEzMTMwMCIsInNlY29uZGFyeVRleHRDb2xvciI6IiMwMDAwMjEiLCJ0ZXJ0aWFyeVRleHRDb2xvciI6InJnYig5LjUwMDAwMDAwMDEsIDkuNTAwMDAwMDAwMSwgOS41MDAwMDAwMDAxKSIsImxpbmVDb2xvciI6IiMzMzMzMzMiLCJ0ZXh0Q29sb3IiOiIjMzMzIiwibWFpbkJrZyI6IiNFQ0VDRkYiLCJzZWNvbmRCa2ciOiIjZmZmZmRlIiwiYm9yZGVyMSI6IiM5MzcwREIiLCJib3JkZXIyIjoiI2FhYWEzMyIsImFycm93aGVhZENvbG9yIjoiIzMzMzMzMyIsImZvbnRGYW1pbHkiOiJcInRyZWJ1Y2hldCBtc1wiLCB2ZXJkYW5hLCBhcmlhbCIsImZvbnRTaXplIjoiMTZweCIsImxhYmVsQmFja2dyb3VuZCI6IiNlOGU4ZTgiLCJub2RlQmtnIjoiI0VDRUNGRiIsIm5vZGVCb3JkZXIiOiIjOTM3MERCIiwiY2x1c3RlckJrZyI6IiNmZmZmZGUiLCJjbHVzdGVyQm9yZGVyIjoiI2FhYWEzMyIsImRlZmF1bHRMaW5rQ29sb3IiOiIjMzMzMzMzIiwidGl0bGVDb2xvciI6IiMzMzMiLCJlZGdlTGFiZWxCYWNrZ3JvdW5kIjoiI2U4ZThlOCIsImFjdG9yQm9yZGVyIjoiaHNsKDI1OS42MjYxNjgyMjQzLCA1OS43NzY1MzYzMTI4JSwgODcuOTAxOTYwNzg0MyUpIiwiYWN0b3JCa2ciOiIjRUNFQ0ZGIiwiYWN0b3JUZXh0Q29sb3IiOiJibGFjayIsImFjdG9yTGluZUNvbG9yIjoiZ3JleSIsInNpZ25hbENvbG9yIjoiIzMzMyIsInNpZ25hbFRleHRDb2xvciI6IiMzMzMiLCJsYWJlbEJveEJrZ0NvbG9yIjoiI0VDRUNGRiIsImxhYmVsQm94Qm9yZGVyQ29sb3IiOiJoc2woMjU5LjYyNjE2ODIyNDMsIDU5Ljc3NjUzNjMxMjglLCA4Ny45MDE5NjA3ODQzJSkiLCJsYWJlbFRleHRDb2xvciI6ImJsYWNrIiwibG9vcFRleHRDb2xvciI6ImJsYWNrIiwibm90ZUJvcmRlckNvbG9yIjoiI2FhYWEzMyIsIm5vdGVCa2dDb2xvciI6IiNmZmY1YWQiLCJub3RlVGV4dENvbG9yIjoiYmxhY2siLCJhY3RpdmF0aW9uQm9yZGVyQ29sb3IiOiIjNjY2IiwiYWN0aXZhdGlvbkJrZ0NvbG9yIjoiI2Y0ZjRmNCIsInNlcXVlbmNlTnVtYmVyQ29sb3IiOiJ3aGl0ZSIsInNlY3Rpb25Ca2dDb2xvciI6InJnYmEoMTAyLCAxMDIsIDI1NSwgMC40OSkiLCJhbHRTZWN0aW9uQmtnQ29sb3IiOiJ3aGl0ZSIsInNlY3Rpb25Ca2dDb2xvcjIiOiIjZmZmNDAwIiwidGFza0JvcmRlckNvbG9yIjoiIzUzNGZiYyIsInRhc2tCa2dDb2xvciI6IiM4YTkwZGQiLCJ0YXNrVGV4dExpZ2h0Q29sb3IiOiJ3aGl0ZSIsInRhc2tUZXh0Q29sb3IiOiJ3aGl0ZSIsInRhc2tUZXh0RGFya0NvbG9yIjoiYmxhY2siLCJ0YXNrVGV4dE91dHNpZGVDb2xvciI6ImJsYWNrIiwidGFza1RleHRDbGlja2FibGVDb2xvciI6IiMwMDMxNjMiLCJhY3RpdmVUYXNrQm9yZGVyQ29sb3IiOiIjNTM0ZmJjIiwiYWN0aXZlVGFza0JrZ0NvbG9yIjoiI2JmYzdmZiIsImdyaWRDb2xvciI6ImxpZ2h0Z3JleSIsImRvbmVUYXNrQmtnQ29sb3IiOiJsaWdodGdyZXkiLCJkb25lVGFza0JvcmRlckNvbG9yIjoiZ3JleSIsImNyaXRCb3JkZXJDb2xvciI6IiNmZjg4ODgiLCJjcml0QmtnQ29sb3IiOiJyZWQiLCJ0b2RheUxpbmVDb2xvciI6InJlZCIsImxhYmVsQ29sb3IiOiJibGFjayIsImVycm9yQmtnQ29sb3IiOiIjNTUyMjIyIiwiZXJyb3JUZXh0Q29sb3IiOiIjNTUyMjIyIiwiY2xhc3NUZXh0IjoiIzEzMTMwMCIsImZpbGxUeXBlMCI6IiNFQ0VDRkYiLCJmaWxsVHlwZTEiOiIjZmZmZmRlIiwiZmlsbFR5cGUyIjoiaHNsKDMwNCwgMTAwJSwgOTYuMjc0NTA5ODAzOSUpIiwiZmlsbFR5cGUzIjoiaHNsKDEyNCwgMTAwJSwgOTMuNTI5NDExNzY0NyUpIiwiZmlsbFR5cGU0IjoiaHNsKDE3NiwgMTAwJSwgOTYuMjc0NTA5ODAzOSUpIiwiZmlsbFR5cGU1IjoiaHNsKC00LCAxMDAlLCA5My41Mjk0MTE3NjQ3JSkiLCJmaWxsVHlwZTYiOiJoc2woOCwgMTAwJSwgOTYuMjc0NTA5ODAzOSUpIiwiZmlsbFR5cGU3IjoiaHNsKDE4OCwgMTAwJSwgOTMuNTI5NDExNzY0NyUpIn19LCJ1cGRhdGVFZGl0b3IiOmZhbHNlfQ)

### Aplicaciones extra funcionalidades

Las aplicaciones que proveen de funcionalidad a las aplicaciones core del proyecto son:
1. [custom_safedelete](./src/custom_safedelete): override de la app de django safedelete para ajustar el borrado lógico
a las necesidades de la aplicación.
2. [emails](./src/emails): aplicación que controla el envio de los diferentes mails de la aplicación.
3. [excel_export](./src/excel_export): sobreescritura de la app de django drf_renderer_xlsx para ajustar el renderizado
de los excel a las necesidades de IRIS2. También se incluye la base para las exportaciones excel.
4. [post_migrate](./src/post_migrate): aplicación que proporciona un endpoint para lanzar todas las tareas de
postmigración.

### Abstracción de las integraciones

Las integraciones se han implementado de forma desacoplada al código y se trabajan de forma autónoma. La comunicación entre
los paquetes que implementen IRIS y su API y las integraciones se llevan a cabo a través de señales (eventos Django).

Las señales se van lanzando a medida que se suceden los eventos importantes en la gestión de las fichas y otros modelos.
Algunos son genéricos de django, como la creación, actualización o eliminación, y otros son señales implementadas
para la lógica de negocio. En el paquete [integrations.signals](./src/integrations/signals.py) se puede ver a qué
eventos se suscriben las integraciones.

Las integraciones de entrada son sencillamente APIs implementadas para tal efecto y también se integran en estos flujos.

### Estrategia de testing

Cada paquete python un paquete de tests donde implementar los diferentes tests automáticos que se lanzarán con pytest.

En la estrategia de testing de IRIS2 distinguimos tres tipos de tests:

- Unitarios/Integración: prueban una o varias unidades de código en aislamiento, sin que el resto de partes de la aplicación estén en marcha.
Este tipo de tests puede hacer uso de una base de datos sqlite en memoria, para simplificar la implementación.
- Funcionales: prueban todo el API en su conjunto simulando un ciclo de petición. Para ello, nos apoyamos en la especificación
del OpenAPI, para detectar si las respuestas y algunas estructuras son las esperadas.
- Integraciones externas: prueban la conexión con servicios externos, para no bombardear a los sistemas de destino
solo se deben lanzar en los momentos apropiados.

Para facilitar la implementación, se han desarrollado clases de base de tests que facilitan el trabajo. Por ejemplo,
en el paquete [main.open_api.tests](./src/main/open_api/tests) encontrarás muchas de estas utilidades.

Además de las clases base, se ofrecen métodos, fixtures y mixins para facilitar la creación de datos de prueba.

Por otro lado, se utilizan paquetes útiles como pytest-django para facilitar la simulación del entorno real de la
aplicación cuando realizamos pruebas.

Las pruebas cuando se lanzan utilizan los settings de test, que encontrarás en [main.settings.Test](./src/main/settings.py).

### Paquete main

El paquete main se encarga de gestionar los settings de django y de proveer algunas utilidades genéricas para el resto del proyecto.
La gestión de la configuración se realiza utilizando el paquete [django-kaio](https://pypi.org/project/django-kaio/), que se encarga
de buscar las variables de entorno o de un fichero app.ini.

Las particularidades de como kaio descubre las variables y las configuraciones se detallan en su [documentación](https://django-kaio.readthedocs.io/en/latest/),
de ella se especifica que:

```
0. Class based settings has prevalence.
1. if the .ini file does not exist set the default values
2. searches the .ini file in the current and parent directories
3. managanement script to let us see the current project configuration
4. management script to generate the .ini file with the default values
5. uses django-configurations in order to be able to create class based settings
6. mixins for standard configurations, such as Paths, Filer, Cache, Database…
```

Si queremos añadir una nueva variable de configuración, cuyo valor venga del entorno, es tan sencillo como añadir
un nuevo atributo al settings e intentar recuperar su valor de `opts`:

```python
# fichero main.settings
from kaio import Options, mixins
from configurations import Configuration

opts = Options()

DEFAULT_VALUE = 'DEFAULT'

class Base(mixins.CachesMixin, mixins.DatabasesMixin, mixins.CompressMixin,
           mixins.PathsMixin, mixins.LogsMixin, mixins.EmailMixin,
           mixins.SecurityMixin, mixins.DebugMixin, mixins.WhiteNoiseMixin,
           mixins.StorageMixin, Configuration):
    MY_NEW_SETTING = opts.get('MY_NEW_SETTING_ENV_VAR_NAME', DEFAULT_VALUE)
```

Con esto, kaio se encargará de descubrir las variables y si existe `MY_NEW_SETTING_ENV_VAR_NAME`, devolverá su valor.

En el entorno del IMI hay una particularidad, que es que los secretos se dejan en un vólumen en forma de ficheros.
Esto son los casos de MINIO y la Base de datos. Para ello se implementó el método `get_secret_from_file` dentro de la clase
de settings de IRIS2.

El fichero app.ini nunca se añade al repositorio, para que los secretos de desarrollo local no se difundan a todos los que tengan acceso al mismo.
De esta forma, cada desarrollador tiene su propio app.ini con su configuración y password local.

## 2. Base de datos

Dado que el proyecto de IRIS2 consiste en la actualización de la aplicación IRIS1, uno de los requisitos principales
era migrar los datos de un proyecto a otro. A partir de este requisito, se estableció que se migrarian los datos de la
base de datos oracle de IRIS1 a un postgresql en IRIS2. Además, se tomó la decisión de que el nuevo modelo de datos
debía ser lo más fiel posible al de IRIS1, facilitando así la migración y el uso de los datos en IRIS2.

Por tanto, el grueso del modelado viene dado por la base de datos existente en IRIS1, a la cual se le han hecho las
menos modificaciones posibles. Las modificaciones realizadas tienen que ver con la deprecación de algunos campos o tablas
que hayan perdido el uso en la nueva versión de IRIS o el añadido de nuevas estructuras por las nuevas funcionalidades
introducidas en el proyecto. Por ejemplo, la aplicación de las conversaciones en las fichas es una funcionalidad nueva
en IRIS2, por lo que las tablas no se pueden encontrar en IRIS1.

El modelo relacional de la aplicación es similar al mostrado en el gráfico de las aplicaciones core de IRIS2, dado que
fue uno de los motivos por los que se realizo este diseño.

Siguiendo este diseño, tenemos tres grandes grupos de modelos que se utilizan para configurar las fichas:
1. [masters](./src/iris_masters/models.py):  RecordType, RecordState, Reason, MediaType, CommunicationMedia,
ResponseChannel, InputChannel, Application, Support, Process, District, ResolutionType
2. [features](./src/features/models.py): Feature, ValuesType, Values y Mask
3. [themes](./src/themes/models.py): Area, Element, ElementDetail, Keyword, DerivationDirect, DerivationDistrict,
DerivationPolygon

En la aplicación [profiles](./src/profiles/models.py) podemos encontrar los modelos de los grupos, perfiles y permisos
de los usuarios que utilizan IRIS2: Group, Profile, Permission, UserGroup.

Con la información que proveen todos esos modelos, se gestionan todas las reglas para dar de alta y procesar las fichas
en el sistema de IRIS2 durante todo su ciclo de vida.

En la aplicación [record_cards](./src/record_cards/models.py) podemos encontrar los modelos donde  se registra toda
la información de la ficha, como el solicitante, la ubicación de la misma o como dar la respuesta: RecordCard, Request,
Applicant, Citizen, SocialEntity, Comment, RecordCardResponse, RecordCardChunkedFile.

También podemos encontrar modelos para la gestión de las fichas como: RecordCardAudit, RecordCardBlock,
RecordCardReasignation, Workflow, WorkflowPlan, WorkflowResolution, WorkflowComment.

Del resto de aplicaciones, encontramos [ariadna](./src/ariadna/models.py),
[iris_templates](./src/iris_templates/models.py), [protocols](./src/protocols/models.py),
[communications](./src/communications/models.py), [integrations](./src/integrations/models.py),
[support_info](./src/support_info/models.py) y surveys que contien algunos modelos más simples y que se utilizan a
modo de registro. Aún siendo importantes en las funcionalidades de IRIS2, no pertenecen a la parte más crítica.

#### Modelo base datos

[![](https://mermaid.ink/img/eyJjb2RlIjoiZ3JhcGggVERcbiAgICBBW1JlY29yZENhcmRdXG4gICAgQltSZXF1ZXN0XSAtLT4gQVxuICAgIENbQXBwbGljYW50XSAtLT4gQlxuICAgIERbQ2l0aXplbl0gLS0-IENcbiAgICBFW1NvY2lhbEVudGl0eV0gLS0-IENcbiAgICBGW0NvbW1lbnRdIC0tPiBBXG4gICAgR1tSZWNvcmRDYXJkUmVzcG9uc2VdIC0tPiBBXG4gICAgSFtSZWNvcmRDYXJkQ2h1bmNrZWRGaWxlXSAtLT4gQVxuICAgIEEgLS0-IElbV29ya2Zsb3ddXG4gICAgSSAtLT4gSltXb3JrZmxvd1BsYW5dXG4gICAgSSAtLT4gS1tXb3JrZmxvd1Jlc29sdXRpb25dXG4gICAgSSAtLT4gTFtXb3JrZmxvd0NvbW1lbnRdXG4gICAgTVtHcm91cF0gLS0-IEFcbiAgICBOW1Byb2ZpbGVdIC0tPiBNXG4gICAgT1tQZXJtaXNzaW9uXSAtLT4gTVxuICAgIE0gLS0-IFBbVXNlckdyb3VwXVxuICAgIFFbVXNlcl0gLS0-IFBbVXNlckdyb3VwXVxuICAgIFJbRmVhdHVyZV0gLS0-IEFcbiAgICBTW1ZhbHVlc1R5cGVdIC0tPiBSXG4gICAgVFtWYWx1ZXNdIC0tPiBTXG4gICAgVVtNYXNrXSAtLT4gUlxuICAgIFZbRWxlbWVudERldGFpbF0gLS0-IEFcbiAgICBXW0VsZW1lbnRdIC0tPiBWXG4gICAgWFtBcmVhXSAtLT4gV1xuICAgIFIgLS0-IFZcbiAgICBZW0tleXdvcmRdIC0tPiBWXG4gICAgWltEZXJpdmF0aW9uRGlyZWN0XSAtLT4gVlxuICAgIDFbRGVyaXZhdGlvbkRpc3RyaWN0XSAtLT4gVlxuICAgIDJbRGVyaXZhdGlvblBvbHlnb25dIC0tPiBWXG4gICAgM1tSZWNvcmRUeXBlXSAtLT4gVlxuICAgIDRbUmVjb3JkU3RhdGVdIC0tPiBBXG4gICAgN1tDb21tdW5pY2F0aW9uTWVkaWFdIC0tPiBBXG4gICAgOFtSZXNwb25zZUNoYW5uZWxdIC0tPiBBXG4gICAgOVtJbnB1dENoYW5uZWxdIC0tPiBBXG4gICAgMTBbQXBwbGljYXRpb25dIC0tPiBWXG4gICAgMTFbU3VwcG9ydF0gLS0-IEFcbiAgICAxMltQcm9jZXNzXSAtLT4gVlxuICAgIDEzW0Rpc3RyaWN0XSAtLT4gMTRbVWJpY2F0aW9uXVxuICAgIDEzIC0tPiBBXG4gICAgMTQgLS0-IDFcbiAgICAxNVtSZXNvbHV0aW9uVHlwZV0gLS0-IEtcblxuIiwibWVybWFpZCI6eyJ0aGVtZSI6ImRlZmF1bHQiLCJ0aGVtZVZhcmlhYmxlcyI6eyJiYWNrZ3JvdW5kIjoid2hpdGUiLCJwcmltYXJ5Q29sb3IiOiIjRUNFQ0ZGIiwic2Vjb25kYXJ5Q29sb3IiOiIjZmZmZmRlIiwidGVydGlhcnlDb2xvciI6ImhzbCg4MCwgMTAwJSwgOTYuMjc0NTA5ODAzOSUpIiwicHJpbWFyeUJvcmRlckNvbG9yIjoiaHNsKDI0MCwgNjAlLCA4Ni4yNzQ1MDk4MDM5JSkiLCJzZWNvbmRhcnlCb3JkZXJDb2xvciI6ImhzbCg2MCwgNjAlLCA4My41Mjk0MTE3NjQ3JSkiLCJ0ZXJ0aWFyeUJvcmRlckNvbG9yIjoiaHNsKDgwLCA2MCUsIDg2LjI3NDUwOTgwMzklKSIsInByaW1hcnlUZXh0Q29sb3IiOiIjMTMxMzAwIiwic2Vjb25kYXJ5VGV4dENvbG9yIjoiIzAwMDAyMSIsInRlcnRpYXJ5VGV4dENvbG9yIjoicmdiKDkuNTAwMDAwMDAwMSwgOS41MDAwMDAwMDAxLCA5LjUwMDAwMDAwMDEpIiwibGluZUNvbG9yIjoiIzMzMzMzMyIsInRleHRDb2xvciI6IiMzMzMiLCJtYWluQmtnIjoiI0VDRUNGRiIsInNlY29uZEJrZyI6IiNmZmZmZGUiLCJib3JkZXIxIjoiIzkzNzBEQiIsImJvcmRlcjIiOiIjYWFhYTMzIiwiYXJyb3doZWFkQ29sb3IiOiIjMzMzMzMzIiwiZm9udEZhbWlseSI6IlwidHJlYnVjaGV0IG1zXCIsIHZlcmRhbmEsIGFyaWFsIiwiZm9udFNpemUiOiIxNnB4IiwibGFiZWxCYWNrZ3JvdW5kIjoiI2U4ZThlOCIsIm5vZGVCa2ciOiIjRUNFQ0ZGIiwibm9kZUJvcmRlciI6IiM5MzcwREIiLCJjbHVzdGVyQmtnIjoiI2ZmZmZkZSIsImNsdXN0ZXJCb3JkZXIiOiIjYWFhYTMzIiwiZGVmYXVsdExpbmtDb2xvciI6IiMzMzMzMzMiLCJ0aXRsZUNvbG9yIjoiIzMzMyIsImVkZ2VMYWJlbEJhY2tncm91bmQiOiIjZThlOGU4IiwiYWN0b3JCb3JkZXIiOiJoc2woMjU5LjYyNjE2ODIyNDMsIDU5Ljc3NjUzNjMxMjglLCA4Ny45MDE5NjA3ODQzJSkiLCJhY3RvckJrZyI6IiNFQ0VDRkYiLCJhY3RvclRleHRDb2xvciI6ImJsYWNrIiwiYWN0b3JMaW5lQ29sb3IiOiJncmV5Iiwic2lnbmFsQ29sb3IiOiIjMzMzIiwic2lnbmFsVGV4dENvbG9yIjoiIzMzMyIsImxhYmVsQm94QmtnQ29sb3IiOiIjRUNFQ0ZGIiwibGFiZWxCb3hCb3JkZXJDb2xvciI6ImhzbCgyNTkuNjI2MTY4MjI0MywgNTkuNzc2NTM2MzEyOCUsIDg3LjkwMTk2MDc4NDMlKSIsImxhYmVsVGV4dENvbG9yIjoiYmxhY2siLCJsb29wVGV4dENvbG9yIjoiYmxhY2siLCJub3RlQm9yZGVyQ29sb3IiOiIjYWFhYTMzIiwibm90ZUJrZ0NvbG9yIjoiI2ZmZjVhZCIsIm5vdGVUZXh0Q29sb3IiOiJibGFjayIsImFjdGl2YXRpb25Cb3JkZXJDb2xvciI6IiM2NjYiLCJhY3RpdmF0aW9uQmtnQ29sb3IiOiIjZjRmNGY0Iiwic2VxdWVuY2VOdW1iZXJDb2xvciI6IndoaXRlIiwic2VjdGlvbkJrZ0NvbG9yIjoicmdiYSgxMDIsIDEwMiwgMjU1LCAwLjQ5KSIsImFsdFNlY3Rpb25Ca2dDb2xvciI6IndoaXRlIiwic2VjdGlvbkJrZ0NvbG9yMiI6IiNmZmY0MDAiLCJ0YXNrQm9yZGVyQ29sb3IiOiIjNTM0ZmJjIiwidGFza0JrZ0NvbG9yIjoiIzhhOTBkZCIsInRhc2tUZXh0TGlnaHRDb2xvciI6IndoaXRlIiwidGFza1RleHRDb2xvciI6IndoaXRlIiwidGFza1RleHREYXJrQ29sb3IiOiJibGFjayIsInRhc2tUZXh0T3V0c2lkZUNvbG9yIjoiYmxhY2siLCJ0YXNrVGV4dENsaWNrYWJsZUNvbG9yIjoiIzAwMzE2MyIsImFjdGl2ZVRhc2tCb3JkZXJDb2xvciI6IiM1MzRmYmMiLCJhY3RpdmVUYXNrQmtnQ29sb3IiOiIjYmZjN2ZmIiwiZ3JpZENvbG9yIjoibGlnaHRncmV5IiwiZG9uZVRhc2tCa2dDb2xvciI6ImxpZ2h0Z3JleSIsImRvbmVUYXNrQm9yZGVyQ29sb3IiOiJncmV5IiwiY3JpdEJvcmRlckNvbG9yIjoiI2ZmODg4OCIsImNyaXRCa2dDb2xvciI6InJlZCIsInRvZGF5TGluZUNvbG9yIjoicmVkIiwibGFiZWxDb2xvciI6ImJsYWNrIiwiZXJyb3JCa2dDb2xvciI6IiM1NTIyMjIiLCJlcnJvclRleHRDb2xvciI6IiM1NTIyMjIiLCJjbGFzc1RleHQiOiIjMTMxMzAwIiwiZmlsbFR5cGUwIjoiI0VDRUNGRiIsImZpbGxUeXBlMSI6IiNmZmZmZGUiLCJmaWxsVHlwZTIiOiJoc2woMzA0LCAxMDAlLCA5Ni4yNzQ1MDk4MDM5JSkiLCJmaWxsVHlwZTMiOiJoc2woMTI0LCAxMDAlLCA5My41Mjk0MTE3NjQ3JSkiLCJmaWxsVHlwZTQiOiJoc2woMTc2LCAxMDAlLCA5Ni4yNzQ1MDk4MDM5JSkiLCJmaWxsVHlwZTUiOiJoc2woLTQsIDEwMCUsIDkzLjUyOTQxMTc2NDclKSIsImZpbGxUeXBlNiI6ImhzbCg4LCAxMDAlLCA5Ni4yNzQ1MDk4MDM5JSkiLCJmaWxsVHlwZTciOiJoc2woMTg4LCAxMDAlLCA5My41Mjk0MTE3NjQ3JSkifX0sInVwZGF0ZUVkaXRvciI6ZmFsc2V9)](https://mermaid-js.github.io/mermaid-live-editor/#/edit/eyJjb2RlIjoiZ3JhcGggVERcbiAgICBBW1JlY29yZENhcmRdXG4gICAgQltSZXF1ZXN0XSAtLT4gQVxuICAgIENbQXBwbGljYW50XSAtLT4gQlxuICAgIERbQ2l0aXplbl0gLS0-IENcbiAgICBFW1NvY2lhbEVudGl0eV0gLS0-IENcbiAgICBGW0NvbW1lbnRdIC0tPiBBXG4gICAgR1tSZWNvcmRDYXJkUmVzcG9uc2VdIC0tPiBBXG4gICAgSFtSZWNvcmRDYXJkQ2h1bmNrZWRGaWxlXSAtLT4gQVxuICAgIEEgLS0-IElbV29ya2Zsb3ddXG4gICAgSSAtLT4gSltXb3JrZmxvd1BsYW5dXG4gICAgSSAtLT4gS1tXb3JrZmxvd1Jlc29sdXRpb25dXG4gICAgSSAtLT4gTFtXb3JrZmxvd0NvbW1lbnRdXG4gICAgTVtHcm91cF0gLS0-IEFcbiAgICBOW1Byb2ZpbGVdIC0tPiBNXG4gICAgT1tQZXJtaXNzaW9uXSAtLT4gTVxuICAgIE0gLS0-IFBbVXNlckdyb3VwXVxuICAgIFFbVXNlcl0gLS0-IFBbVXNlckdyb3VwXVxuICAgIFJbRmVhdHVyZV0gLS0-IEFcbiAgICBTW1ZhbHVlc1R5cGVdIC0tPiBSXG4gICAgVFtWYWx1ZXNdIC0tPiBTXG4gICAgVVtNYXNrXSAtLT4gUlxuICAgIFZbRWxlbWVudERldGFpbF0gLS0-IEFcbiAgICBXW0VsZW1lbnRdIC0tPiBWXG4gICAgWFtBcmVhXSAtLT4gV1xuICAgIFIgLS0-IFZcbiAgICBZW0tleXdvcmRdIC0tPiBWXG4gICAgWltEZXJpdmF0aW9uRGlyZWN0XSAtLT4gVlxuICAgIDFbRGVyaXZhdGlvbkRpc3RyaWN0XSAtLT4gVlxuICAgIDJbRGVyaXZhdGlvblBvbHlnb25dIC0tPiBWXG4gICAgM1tSZWNvcmRUeXBlXSAtLT4gVlxuICAgIDRbUmVjb3JkU3RhdGVdIC0tPiBBXG4gICAgN1tDb21tdW5pY2F0aW9uTWVkaWFdIC0tPiBBXG4gICAgOFtSZXNwb25zZUNoYW5uZWxdIC0tPiBBXG4gICAgOVtJbnB1dENoYW5uZWxdIC0tPiBBXG4gICAgMTBbQXBwbGljYXRpb25dIC0tPiBWXG4gICAgMTFbU3VwcG9ydF0gLS0-IEFcbiAgICAxMltQcm9jZXNzXSAtLT4gVlxuICAgIDEzW0Rpc3RyaWN0XSAtLT4gMTRbVWJpY2F0aW9uXVxuICAgIDEzIC0tPiBBXG4gICAgMTQgLS0-IDFcbiAgICAxNVtSZXNvbHV0aW9uVHlwZV0gLS0-IEtcblxuIiwibWVybWFpZCI6eyJ0aGVtZSI6ImRlZmF1bHQiLCJ0aGVtZVZhcmlhYmxlcyI6eyJiYWNrZ3JvdW5kIjoid2hpdGUiLCJwcmltYXJ5Q29sb3IiOiIjRUNFQ0ZGIiwic2Vjb25kYXJ5Q29sb3IiOiIjZmZmZmRlIiwidGVydGlhcnlDb2xvciI6ImhzbCg4MCwgMTAwJSwgOTYuMjc0NTA5ODAzOSUpIiwicHJpbWFyeUJvcmRlckNvbG9yIjoiaHNsKDI0MCwgNjAlLCA4Ni4yNzQ1MDk4MDM5JSkiLCJzZWNvbmRhcnlCb3JkZXJDb2xvciI6ImhzbCg2MCwgNjAlLCA4My41Mjk0MTE3NjQ3JSkiLCJ0ZXJ0aWFyeUJvcmRlckNvbG9yIjoiaHNsKDgwLCA2MCUsIDg2LjI3NDUwOTgwMzklKSIsInByaW1hcnlUZXh0Q29sb3IiOiIjMTMxMzAwIiwic2Vjb25kYXJ5VGV4dENvbG9yIjoiIzAwMDAyMSIsInRlcnRpYXJ5VGV4dENvbG9yIjoicmdiKDkuNTAwMDAwMDAwMSwgOS41MDAwMDAwMDAxLCA5LjUwMDAwMDAwMDEpIiwibGluZUNvbG9yIjoiIzMzMzMzMyIsInRleHRDb2xvciI6IiMzMzMiLCJtYWluQmtnIjoiI0VDRUNGRiIsInNlY29uZEJrZyI6IiNmZmZmZGUiLCJib3JkZXIxIjoiIzkzNzBEQiIsImJvcmRlcjIiOiIjYWFhYTMzIiwiYXJyb3doZWFkQ29sb3IiOiIjMzMzMzMzIiwiZm9udEZhbWlseSI6IlwidHJlYnVjaGV0IG1zXCIsIHZlcmRhbmEsIGFyaWFsIiwiZm9udFNpemUiOiIxNnB4IiwibGFiZWxCYWNrZ3JvdW5kIjoiI2U4ZThlOCIsIm5vZGVCa2ciOiIjRUNFQ0ZGIiwibm9kZUJvcmRlciI6IiM5MzcwREIiLCJjbHVzdGVyQmtnIjoiI2ZmZmZkZSIsImNsdXN0ZXJCb3JkZXIiOiIjYWFhYTMzIiwiZGVmYXVsdExpbmtDb2xvciI6IiMzMzMzMzMiLCJ0aXRsZUNvbG9yIjoiIzMzMyIsImVkZ2VMYWJlbEJhY2tncm91bmQiOiIjZThlOGU4IiwiYWN0b3JCb3JkZXIiOiJoc2woMjU5LjYyNjE2ODIyNDMsIDU5Ljc3NjUzNjMxMjglLCA4Ny45MDE5NjA3ODQzJSkiLCJhY3RvckJrZyI6IiNFQ0VDRkYiLCJhY3RvclRleHRDb2xvciI6ImJsYWNrIiwiYWN0b3JMaW5lQ29sb3IiOiJncmV5Iiwic2lnbmFsQ29sb3IiOiIjMzMzIiwic2lnbmFsVGV4dENvbG9yIjoiIzMzMyIsImxhYmVsQm94QmtnQ29sb3IiOiIjRUNFQ0ZGIiwibGFiZWxCb3hCb3JkZXJDb2xvciI6ImhzbCgyNTkuNjI2MTY4MjI0MywgNTkuNzc2NTM2MzEyOCUsIDg3LjkwMTk2MDc4NDMlKSIsImxhYmVsVGV4dENvbG9yIjoiYmxhY2siLCJsb29wVGV4dENvbG9yIjoiYmxhY2siLCJub3RlQm9yZGVyQ29sb3IiOiIjYWFhYTMzIiwibm90ZUJrZ0NvbG9yIjoiI2ZmZjVhZCIsIm5vdGVUZXh0Q29sb3IiOiJibGFjayIsImFjdGl2YXRpb25Cb3JkZXJDb2xvciI6IiM2NjYiLCJhY3RpdmF0aW9uQmtnQ29sb3IiOiIjZjRmNGY0Iiwic2VxdWVuY2VOdW1iZXJDb2xvciI6IndoaXRlIiwic2VjdGlvbkJrZ0NvbG9yIjoicmdiYSgxMDIsIDEwMiwgMjU1LCAwLjQ5KSIsImFsdFNlY3Rpb25Ca2dDb2xvciI6IndoaXRlIiwic2VjdGlvbkJrZ0NvbG9yMiI6IiNmZmY0MDAiLCJ0YXNrQm9yZGVyQ29sb3IiOiIjNTM0ZmJjIiwidGFza0JrZ0NvbG9yIjoiIzhhOTBkZCIsInRhc2tUZXh0TGlnaHRDb2xvciI6IndoaXRlIiwidGFza1RleHRDb2xvciI6IndoaXRlIiwidGFza1RleHREYXJrQ29sb3IiOiJibGFjayIsInRhc2tUZXh0T3V0c2lkZUNvbG9yIjoiYmxhY2siLCJ0YXNrVGV4dENsaWNrYWJsZUNvbG9yIjoiIzAwMzE2MyIsImFjdGl2ZVRhc2tCb3JkZXJDb2xvciI6IiM1MzRmYmMiLCJhY3RpdmVUYXNrQmtnQ29sb3IiOiIjYmZjN2ZmIiwiZ3JpZENvbG9yIjoibGlnaHRncmV5IiwiZG9uZVRhc2tCa2dDb2xvciI6ImxpZ2h0Z3JleSIsImRvbmVUYXNrQm9yZGVyQ29sb3IiOiJncmV5IiwiY3JpdEJvcmRlckNvbG9yIjoiI2ZmODg4OCIsImNyaXRCa2dDb2xvciI6InJlZCIsInRvZGF5TGluZUNvbG9yIjoicmVkIiwibGFiZWxDb2xvciI6ImJsYWNrIiwiZXJyb3JCa2dDb2xvciI6IiM1NTIyMjIiLCJlcnJvclRleHRDb2xvciI6IiM1NTIyMjIiLCJjbGFzc1RleHQiOiIjMTMxMzAwIiwiZmlsbFR5cGUwIjoiI0VDRUNGRiIsImZpbGxUeXBlMSI6IiNmZmZmZGUiLCJmaWxsVHlwZTIiOiJoc2woMzA0LCAxMDAlLCA5Ni4yNzQ1MDk4MDM5JSkiLCJmaWxsVHlwZTMiOiJoc2woMTI0LCAxMDAlLCA5My41Mjk0MTE3NjQ3JSkiLCJmaWxsVHlwZTQiOiJoc2woMTc2LCAxMDAlLCA5Ni4yNzQ1MDk4MDM5JSkiLCJmaWxsVHlwZTUiOiJoc2woLTQsIDEwMCUsIDkzLjUyOTQxMTc2NDclKSIsImZpbGxUeXBlNiI6ImhzbCg4LCAxMDAlLCA5Ni4yNzQ1MDk4MDM5JSkiLCJmaWxsVHlwZTciOiJoc2woMTg4LCAxMDAlLCA5My41Mjk0MTE3NjQ3JSkifX0sInVwZGF0ZUVkaXRvciI6ZmFsc2V9)

## 3. APIs

Al core de IRIS2 se puede acceder desde diferentes aplicaciones o sistemas, por este motivo se dispone de diferentes
APIs que se adaptan a las diferentes necesidades de conexión de estas aplicaciones o sistemas.


### API Privada

El [API Privada](./src/main/urls_iris_api.py) es el API que utiliza la SPA del backoffice de IRIS para conectarse al
back y poder realizar todas sus funcionalidades. Este API es privada dado que solo se utiliza para este fin y todos
los endpoints requieren autentificación. Para poderse identificar en el sistema es necesario indicar la cabecera
http X-IBM-Client-Id. El acceso a este API solo esta permitido dentro de la red corporativa del Ajuntament.

El API Privada de IRIS la podemos encontrar en el "base path" /services/iris/api/. En ese mismo path se puede consultar
la documentación en formato OpenApi. También se puede consultar el swagger en /services/iris/api/swagger/.

En el API privada de IRIS2 podemos encontrar con los endpoints de los maestros de la aplicación, las temáticas,
las plantillas, los grupos y perfiles, las fichas, los informes, las características, las integraciones,
las comunicaciones, el listado de fichas de SSI, los protocolos, ariadna, quiosc, la información de soporte, la
respuesta de las fichas tramitadas externamente y la postmigración.


### API Pública

EL [API Pública](./src/public_api/urls.py) es el API que utiliza la Web d'Atenció al Ciutadà, que se ha renovado
conjuntamente con IRIS2, y alguna de las integraciones. Como indica su nombre, este API es pública y se permite el
acceso fuera de la red corporativa del Ajuntament sin autentificación.

El API Pública de IRIS la podemos encontrar en el "base path" /services/iris/api-public. En ese mismo path se puede
consultar la documentación en formato OpenApi. También se puede consultar el swagger en /services/iris/api-public/swagger/.

En el API Pública se pueden encontrar los endpoints para proveer la información de la Web ATE desde listados de areas,
elementos, detalles, fichas, distritos, canal de entrada, tipos de solicitantes, parametros de configuración del ATE
hasta operaciones tales como alta de fichas, reclamación de fichas o respuesta a comunicaciones solicitadas desde el
backoffice de IRIS2.


### API Pública Autentificada

El [API Pública Autentificada](./src/public_external_processing/urls.py) es una API que pueden utilizar servicios
externos para devolver, cancelar o cerrar fichas que les haya remitido el Ajuntament. Este API es pública porque se
puede acceder desde fuera de la red corporativa del Ajuntament, siempre de forma autentificada indicando a
cabecera http X-IBM-Client-Id.

El API Pública Autentificada de IRIS la podemos encontrar en el "base path" /services/iris/api-internet. En ese mismo
path se puede consultar la documentación en formato OpenApi. También se puede consultar el swagger en
/services/iris/api-internet/swagger/.


### API Proxy XML

El [API Proxy XML](./src/xml_proxy/urls.py) es una API creada por motivos de retrocompatiblidad con serivicios drupal
o similares que se conectaban a IRIS1. Este API es pública y se permite el acceso fuera de la red corporativa del
Ajuntament sin autentificación.

El API Proxy XML de IRIS la podemos encontrar en el "base path" /services/iris/api-public/xml-proxy En ese mismo path
se puede consultar la documentación en formato OpenApi. También se puede consultar el swagger en
/services/iris/api-public/xml-proxy/swagger/.



## 4. Puntos más relevantes en la implementación

### Rest framework

El API de esta aplicación está implementada utilizando Rest Framework. Las diferentes partes de la aplicación y su
particularidades se han implementado utilizando los conceptos que el framework ofrece: Authentication backends,
serializadores, generic views y viewsets, permission classes, filter backends, django filters, etc.

Como detalle, algunos serializadores están implementados como Serializers normales en lugar de ModelSerializers,
ya que ofrecen un mayor rendimiento. Así mismo, se han aplicado otras estrategias para mejorar la velocidad de
serialización como marcar los campos como readonly cuando se pueda.

### Generar Open API

Para generar los ficheros OpenAPI y sus correspondientes portales Swagger y Redoc, utilizamos el paquete [drf-yasg](https://pypi.org/project/drf-yasg/).

Para automatizar y mejorar la documentación generada, hemos añadido algunos decoradores personalizados que añaden elementos
como las cabeceras de idioma a la especificación o configuraciones especificas del imi. Se pueden encontrar en
[main.open_api](./src/main/open_api)

### Celery

Dado que entre las funcionalidades de IRIS2 podemos encontrar tareas muy pesadas y que necesitan más tiempo para
ejecutarse que lo habitual en una petición http, se ha introducido un sistema de colas utilizando
[Celery](https://github.com/celery/celery). Así, este tipo de tareas se puede ejecutar en segundo plano sin afectar
al uso de la aplicación. Además, como el Celery esta desplegado en varios pods aparte del backoffice el uso de recursos
estas tareas no afecta al rendimiento de la aplicación. Otra ventaja que nos da es la programación de tareas utilizando
[Celery-beat](https://github.com/celery/django-celery-beat).

Para la implementación se ha utilizado

Algunas de las tareas que se realizan con el Celery son:
1. Proceso de borrado de un grupo. [Ver aquí](./src/profiles/tasks.py).
2. Envio de notificaciones cuando una ficha es asignada a un grupo. [Ver aquí](./src/profiles/tasks.py).
3. Registro de las fichas posibles similares de una ficha. [Ver aquí](./src/record_cards/tasks.py).

Algunas tareas que se ejecutan de forma periódica utilizando Celery-beat:
1. Envio de emails
2. Envio de notificaciones de fichas cerca de expirar
3. Generar informes: BI, MIB, DWH, OpenData, etc
4. Calcular el tiempo medio de cierre de las fichas de cada temática

Estas tareas se configuran en el setting `CELERY_BEAT_SCHEDULE` en el fichero [settings](./src/main/settings.py).

### Safe-delete

Dado que uno de los requisitos de la aplicación consiste en guardar un registro de todo lo que se ha hecho con los datos
de IRIS2, los elementos borrados no se pueden eliminar de la base de datos. Por esto se ha implementado una política de
borrado lógico en la mayoría de modelos susceptibles a cambios. Esta política se ha implementado utilizando
[django-safedelete](https://pypi.org/project/django-safedelete/).

Esta librería permite escoger el método de borrado cuando se elimina un objeto, desde enmascararlo a no borrarlo nunca.
Por defecto, un objecto enmascarado se tratará como un objeto borrado, por lo que no se podrá acceder a él. Por este
motivo se sobreescribio la aplicación con custom_safedelete. Para entender el caso, podemos tener una característica
que se utiliza en varias fichas. Si se borra esta característica, no queremos que se borre el valor que tiene asignado
en las fichas, dado que perderiamos información. Por esto, al borrar la característica no la podremos volver a utilizar
al dar de alta una ficha pero si accedemos por su ID para consultar los registros utilizados previamente podremos hacerlo.

### Cachalot

Dado que hay un gran número de consultas a la base de datos que se van a repetir de forma sistemática sobre entidades
que no van a cambiar mucho dada la naturaleza de la aplicación, se decidio implementar un sistema para cachear las
consultas a la base de datos. Esta funcionalidad está implementada utilizando
[django-cachalot](https://django-cachalot.readthedocs.io/en/latest/).

En el fichero la variable `CACHALOT_ONLY_CACHABLE_TABLES` del fichero de [settings](./src/main/settings.py) podemos ver
las tablas que se han añadido al Cachalot. Básicamente se añadieron todas las tablas de configuraciones, desde
los maestros de la aplicación hasta las temáticas pasando por las plantillas, características o protocolos. También
se añadieron las tablas de grupos, perfiles y permisos dado que son unas consultas que se realizan cada vez que un
usuario hace una petición al API.

Es importante destacar que, por defecto, Cachalot cachea todas las consultas que se realizan sobre estas tablas y que
solo invalida las claves en la cache cuando se actualiza un registro en estas tablas. Para no hacer un uso ilimitado de
la cache:
1. se ha configurado un timeout de 8h para que las consultas expiren, ya que por defecto django-cachalot no indica un
tiempo de expiración. Configuración en `CACHALOT_TIMEOUT` en [settings](./src/main/settings.py).
2. se ha implementado un decorador [iris_cachalot](./src/main/cachalot_decorator.py) para sobreescribir el manager de los
modelos que utilizan cachalot y solo cachear las queries más habituales y que contemplen los atributos más generales.
Para poner en contexto, tiene sentido cachear un listado de un maestro pero no tiene sentido cachear cada búsqueda que
se haga sobre ese listado.

```python
def iris_cachalot(manager, extra_fields=None):
    fields = ["pk", "order", "deleted", "enabled", *(extra_fields or [])]

    manager.filter = cacheable_query_decorator(manager.filter, fields)
    manager.get = cacheable_query_decorator(manager.get, fields)

    class CachalotClass(manager._queryset_class):
        pass

    def decorator_factory(method):
        return cacheable_query_decorator(method, fields)

    method_decorator(decorator_factory, name='filter')(CachalotClass)
    method_decorator(decorator_factory, name='get')(CachalotClass)
    manager._queryset_class = CachalotClass
    return manager
```

### Postmigración

Dadas las características de la aplicación, no se puede arrancar con una base de datos vacia ya que hay funcionalidades
que dependen de los datos en las tablas de datos maestros. Por ese motivo, se han creado varios procesos que se han de
ejecutar antes de arrancar el proyecto por primera vez con una base de datos vacia o con una base de datos nueva. Este
segundo caso incluye la ejecución de estos procesos después de cada migración en uno de los entornos donde esta desplegada
la aplicación (int, pre y prod).

Muchos de estos procesos se podrían lanzar después de ejecutar las migraciones de Django, el problema es que ralentizan
mucho el proceso de despliegue de la aplicación. Por este motivo, esta opción está desactivada con el setting
`EXECUTE_DATA_CHEKS` en [settings](./src/main/settings.py)

La alternativa planteada para ejecutar los procesos en los entornos es realizar unas peticiones definidas en el api
para ejecutar estas tareas. De ahi la idea de la aplicación [post_migrate](./src/post_migrate), que lanza la gran
mayoria de las tareas. Aún así, según la migración que se haya realizado puede interesar solo ejecutar algunas de estas
tareas, por lo que se dispone de otros endpoints para tal efecto.

Los endpoints para las tareas de postmigración son:
1. /services/iris/api/post-migrate/
2. /services/iris/api/masters/masters-data-checks/
3. /services/iris/api/profiles/profiles-data-checks/
4. /services/iris/api/profiles/groups/rebuildtree/
5. /services/iris/api/record_cards/set-record-audits/
6. /services/iris/api/theme/tree/cache/

### Permisos

En IRIS2 la gestión de grupos y perfiles ha pasado de ser gestionada en Control User a ser gestionada en IRIS2. La implementación
se encuentra en el paquete `profiles`. En concreto la implementación se controla como un backend de permisos de RestFramework (subclase de `rest_framework.permissions.BasePermission),
implementado en la clase [profiles.permissions.IrisPermission](./src/profiles/permissions.py).

Cada aplicación se encarga de proporcionar los permisos que necesita para funcionar. Estos se pueden encontrar en cada
paquete de core en el fichero permissions.py, donde la propia aplicación se encarga de registrarlos. Por ejemplo,
el paquete de record cards registra un permiso para validar fichas:

```python
def register_permissions():
    PERMISSIONS.register(VALIDATE, {
        "description": "Accions - Validar fitxes",
        "category": CATEGORY,
    })
    # Otros permisos
```

Los permisos se deben registrar en el método ready del AppConfig de la app Django, para asegurar que todos los modelos
han sido cargados y no habrá problemas al importarlos. Siguiendo el ejemplo del paquete de fichas, podemos revisar el
fichero `record_cards.apps.py`:

```python
from django.apps import AppConfig
from django.db.models import CharField

from record_cards.lookups import ILike


class RecordCardsConfig(AppConfig):
    name = 'record_cards'

    def ready(self):
        from .permissions import register_permissions
        register_permissions()
        # Otro código y registro
```

### Traducciones

Dentro del sistema de traducciones encontramos dos tipos:

- Traducción de los strings del sistema: implementado con el sistema de traducciones de django.
- Traducción de los datos del usuario: implementados con el paquete open Source Django Model Translations, que transparemente
se encarga de ajustar los modelos para gestionar los campos que han sido marcados como traducibles.

RestFramework se encarga de procesar la cabecera de la petición para decidir el idioma de la petición y obtener los strings
y el contenido en el idioma adecuado.

### Árbol de temáticas

En el alta de fichas de la SPA hay un buscador de temáticas que parte de la estructura Area - Elemento - Temática.
Para facilitar el renderizado de ese componente, se proporciona el Árbol de temáticas desde el core en el endpoint
/services/iris/api/themes/tree/. Este árbol se genera utilizando la clase [ThemeTreeBuilder](./src/themes/actions/theme_tree.py),
que proporciona toda la información necesaria. Este árbol esta cacheado y solo se recalcula si se crea o se actualiza
un Area, Elemento o Temática. Como se ha indicado en el punto anterior, disponemos de un endpoint para forzar el
recálculo del árbol en caso necesario: /services/iris/api/themes/tree/cache/.

### Árbol de grupos y concepto de ámbito

La distribución de los grupos de trabajo dentro del Ajuntament también tiene estructura de árbol, partiendo desde el
DAIR (grupo principal y admin de IRIS2), pasando a un segundo nivel de coordinadores de ámbito, un tercero de
responsable y tal vez un cuarto nivel de operadores. El árbol se puede obtener en la vista
[GetGroupsTreeView](./src/profiles/views.py) que se encuentra en la url /services/iris/api/profiles/groups/tree/.

El ámbito son los grupos con los que tiene relación un determinado grupo, menos el dair. Es decir, el ámbito de un grupo
son todos sus ancestros  excepto el DAIR y sus descendientes. Por ejemplo, para un responsable su ámbito es el coordinador
 y sus posibles operadores. Para un coordinador, su ámbito son los grupos responsables y los operadores de estos.

### Multificha

La multificha consiste en desglosar una petición ciudadana en más de una ficha, ya que el alcance de la misma es demasiado amplio.
De esta forma, cuando un operador recibe una ficha que afecta a varias temáticas procede a desglosarla en multificha, quedando todas relacionadas.

Los flujos de cada ficha de una multifificha son independientes, pero permiten a los operadores consultar el estado de forma conjunta.

Las fichas que han sido desglosada en multificha desde otra tienen el campo multirecord_form informado, siendo su valor la clave primaria de la ficha original, además
todas tienen el flag is_multirecord a True.

La vista RecordCardMultiRecordsView` implementa la llamada al API para obtener el listado de multifichas asociadas a un ficha.

Para crear multifichas es necesario un permiso.

### Fichas similares y unifichas

IRIS permite unificar varias peticiones ciudadanas, si la temática está configurada para ello, y se cumplen las condiciones
establecidas en la misma:

- Las fichas son de la misma temática.
- Las fichas están dentro de un radio.
- Las fichas se han producido cerca en el tiempo.

Cada vez que se crea una ficha, se revisa sus posibles similares. Este proceso se implementa en la tarea `record_cards.tasks.register_possible_similar_records`.
La tarea a su vez lanza el método set_similar_records del modelo `record_cards.models.RecordCard`. Es en este método donde se implementa
la lógica para revisar si dos fichas son similares. Una vez calculado, se registra en DB.

Cuando el usuario va a validar una ficha, se le ofrece el listado de fichas similares. En caso de que el operador decida unificar
dos fichas similares, la nueva ficha validada se unirá al proceso (record_cards.models.Workflow) para gestionarse una única vez.

Todas las fichas tienen un Workflow que se asigna al validar. Hay estados que son a nivel de ficha y estados que se gestionan desde el workflow.
Por ejemplo, la validación, respuesta o la anulación son propia de la ficha, mientras que la resolución, planificación se realiza a nivel
de Workflow. Básicamente, esto se debe a que hay partes de la tramitación que son propias de la petición y otras que son de la tarea en si.
Si 20 ciudadanos piden arreglar el bache, el bache se arregla una vez pero se responde a los 20 ciudadanos.

La propia implementación del API y las transiciones controlan este flujo, en la próxima sección abordaremos la gestión de estados.

*Todas las unifichas tienen una ficha principal que es la que inició el Workflow, para que después otras se añadiesen.*

### Máquina de estados: procesos y estados

Durante la tramitación de una ficha en IRIS2, esta pasa por diferentes estados que dependen del proceso que ha de seguir
la ficha, que viene determinado por la temática. Por este motivo, se creo una
[máquina de estados](./src/record_cards/record_actions/state_machine.py) que partiendo del proceso de la ficha y el
estado en el que se encuentra determina las transiciones que se pueden realizar para avanzar a los siguientes estados.
La máquina de estados la podemos encontrar en la clase RecordCardStateMachine. Esta clase también incluye métodos para
conocer el paso actual, el paso siguiente esperado o las posibles transiciones.

Tomando de ejemplo el siguiente trozo de la máquina de estados:

```python
    {
        Process.CLOSED_DIRECTLY: {
            RecordState.NO_PROCESSED: self.get_not_tramit_state(),
            RecordState.PENDING_VALIDATE: {
                "initial": True,
                "state": self.pending_validation,
                "get_state_change_method": "change_state",
                "transitions": {
                    RecordState.CLOSED:  self.validate(is_next=True),
                    RecordState.CANCELLED: self.cancel()
                }
            },
            RecordState.CANCELLED: {"state": self.canceled, "get_state_change_method": "change_state"},
            RecordState.CLOSED: {"state": self.closed, "get_state_change_method": "change_state"}
        }
    }
```

Planteando una ficha con proces "CLOSED_DIRECTLY" y en estado "PENDING_VALIDATE", la máquina de estados nos indica que:
1. la ficha se encuentra en el estado inicial
2. para este proceso, las posibles transiciones son anular la ficha o cerrarla
3. el método que utilizará para cambiar de estado

Añadir un nuevo proceso consiste en añadirlo a la definición de la máquina de estados. Se puede seguir el ejemplo de
los ya implementados. Así mismo, añadir nuevos tipos de transiciones se basa en añadir nuevos enpoints que actuen sobre
la ficha y después definirlos dentro de la máquina de estados.

### Acciones de la ficha

Además de cambiar de estado, en una ficha se pueden realizar multitud de acciones. La lógica de que acciones se pueden
llevar a cabo se representa en la classe [RecordActions](./src/record_cards/record_actions/actions.py) y se incluye un
campo en los serializadores de la ficha para que el frontal sepa que acciones puede realizar.

Las acciones que se pueden hacer dependen de varias condiciones:
1. del estado de la ficha
2. de si el grupo puede tramitar o no una ficha. La podrá tramitar si es el responsable de una ficha o un ancestro
de ese grupo
3. de si se esta consultando el detalle de la ficha
4. de si la ficha tiene un solicitante asignado o no
5. de si el usuario es el creador de la ficha
6. de los permisos del grupo del usuario

#### Procesos
De la mano una de las acciones de las fichas, se introduce el concepto de Proceso(Workflow) de las fichas.
Un proceso son un conjunto de fichas relacionadas entre ellas por varios criterios de similitud. Por ejemplo, un proceso
serian varias fichas que se han recibido indicando que hay un semaforo que no funciona. Dado que se trata del mismo caso,
se han de gestionar igual y se dará la respuesta a cada solicitante.

El proceso de una ficha se setea cuando esta se valida. Si al validar se escoge una ficha ya validada, añadimos la ficha
que estamos validando al proceso de la segunda. Si no se indica ninguna, se crea un proceso nuevo.

### Derivación fichas
El proceso de derivación de las fichas es el proceso automático que se encarga se asignar las fichas al grupo que les
corresponden según la configuración de las mismas.

Existen tres tipos de derivaciones:
1. directas: dada una temática y un estado se asigna la ficha a un grupo
2. de polígono: dada una temática, un estado y un código de polígono se asigna la ficha a un grupo
3. de distrito: dado una temática, un estado y un districto se asigna la ficha a un grupo

Para una temática y un estado, el tipo de derivación es excluyente. O bien se configura una derivación directa o bien se
configura una derivación territorial.

Por ese motivo, el [proceso de derivación](./src/record_cards/record_actions/derivations.py) empieza obteniendo que
tipo de derivación se ha de aplicar y a continuación la aplica.

```python
def derivate(record_card, next_state_id, next_district_id):
    """

    :param record_card: Record Card to derivate
    :param next_state_id: RecordState to derivate
    :param next_district_id: District to derivate
    :return: If derivation group exist, derivation group else None
    """
    derivation_class = get_derivation_class(record_card, next_state_id=next_state_id)
    return derivation_class(record_card, next_state_id, next_district_id).get_derivation_group()
```

Si existe una derivación directa, se aplica este tipo de derivación y si no existe, se aplica la derivación territorial.
Dentro de la derivación territorial, se intenta aplicar primero la derivación de polígono. Si no se encuentra grupo para
derivar, se consulta la derivación por distrito.

Si después de comprobar todas las posibles derivaciones no se obtiene un grupo al que asignar la ficha, no se aplica la
derivación y la ficha permanece asignada al mismo grupo. Si no se trata de una derivación inicial en la creación de la
ficha se enviará una notificación de ficha asignada, si el grupo lo tiene configurado.

### Reasignaciones

Los grupos tienen configurado a quién pueden reasignar una ficha cuando está en estado pendiente de validar.

En caso de que la ficha ya esté validada, los grupos solo podrán reasignar la ficha a los de su propio ámbito.

En caso de que la ficha haya sido reclamada más de N ocasiones solo se puede reasignar a su coordinador.

Estos casos se implementan y están documentados en `record_cards.record_actions.reasignations.py`, con la clase
[PossibleReassignations](./src/themes/actions/reasignations.py)

Como es lógico, la operación se lanza desde una llamada al API que utiliza PossibleReassignations y si la derivación
solicitada es válida, procede a realizarla. El uso de PossibleReassignations para la validación y efectuar la reasignación
es responsabilidad de [ecord_cards.serializers.RecordCardReasignationSerializer](./src/record_cards/serializers.py).

### Cambio de temática

En el uso diario de IRIS2 se puede dar el caso que a una ficha se le asigne una temática que no es la más adecuada para
el caso. Por esto existe el proceso de cambio de temática, que se puede realizar siempre que se respeten las siguientes
condiciones:
1. el estado de la ficha tiene que estar entre: PENDING_VALIDATE, EXTERNAL_RETURNED, IN_RESOLUTION y CLOSED.
2. la nueva temática tiene que estar entre las temáticas a las que puede cambiar una ficha el grupo que realiza el proceso.
Las posibles temáticas se definen la clase [PossibleThemeChange](./src/themes/actions/possible_theme_change.py)
3. el grupo que realiza el cambio debe tener el permiso para realizar esta acción.

Al cambiar la temática de una ficha, se marcas las características que tubiera asignadas como ocultas y se registra un
comentario en la trazabilidad de la ficha. Si la nueva temática tiene características, se registran los valores de las
nuevas en la ficha.

Si al cambiar la temática, la ficha se puede autovalidar, se valida la ficha. Sino, se realiza la derivación, si así se
ha indicado.

### Tramitación externa

Algunas temáticas y procesos requieren que las fichas sean enviadas a sistemas externos para realizar su tramitación fuera de IRIS.
A este proceso lo llamamos internamente validación contra sistema externo y a las clases y subclases encargadas de implementarlos ExternalValidators.

Un validador externo debe implementar los métodos abstractos de la clase [ExternalValidator](./src/record_cards/record_actions/external_validators.py) para implementar la integración.

La implementación y registro de los validadores externos está desacoplada del paquete Core, de forma que los diferentes paquetes
que implementen las integraciones deben registrarlos. El proceso para añadir un nuevo ExternalValidator es:

1. Implementar una subclase de ExternalValidator que realice el envío.
1. Registrar la clase.
1. Crear la fila dentro del modelo ExternalValidator que guarda en base datos la lista de validadores para que pueda ser asignado a la temática

```
Además de esto, se ha implementado una tramitación externa genérica, con este flujo es el sistema externo el que se ajusta al payload que enviará IRIS.
```

Las fichas enviadas a tramitación externa pueden ser devueltas, cerradas o canceladas desde el sistema externo.
Los detalles se pueden encontrar en la documentación de las APIs para integradores externos o en el paquete `public_external_processing`.

### Búsqueda de solicitantes

Aunque el MIB sea una integración, al igual que con la tramitación externa tiene un impacto significativo dentro de la usabilidad y el funcionamiento del backoffice.

Para abstraer esta parte y hacer que el sistema sea tolerante a los fallos de conexión al MIB se introduce el concepto de [ApplicantSource](./src/record_cards/applicant_sources/applicant_source.py)

IRIS utiliza la clase [IrisSource](./src/record_cards/applicant_sources/applicant_source.py) para buscar los solicitantes.
Este ApplicantSource realiza dos búsquedas parelelas, una al MIB y otra a la DB local, y luego fusiona los resultados.
En caso de que una de los dos falle (MIB), devuelve los resultados de la otra.

Si los datos del solicitante se actualizan en IRIS, estos se reenvian al MIB que aplicará sus principios de prioridad para decidir que
datos prevalecerán.

### Templates de respuesta y variables

IRIS2 ofrece un completo sistema de templates de respuesta y comunicaciones. Este sistema permite crear una librería de plantilla
entre los diferentes tipos de ficha y canales de respuesta. Cada template se configura para texto largo (email + carta) o sms,
para los idiomas configurados en la aplicación.

Además de los templates configurados por defecto a nivel de tipo de ficha y de respuesta propia en la temática, IRIS2 ofrece un sistema
para que los grupos puedan guardar sus propias plantillas de respuesta que compartirán todos los operadores que pertenezcan a dicho grupo.

A nivel de implementación, los dos conceptos clave a la hora de hablar del sistema de templates son el [renderizador](./src/iris_templates/renderer.py) y los [buscadores de variables](./src/iris_templates/templates_context/vars_finder.py).
Ambos están implementados dentro del paquete iris_templates.

El renderizador de IRIS2 es retrocompatible con IRIS1 y sigue el formato de reemplazar las variables sin ninguna marca,
directamente hay algunos tags que se reemplazan si se encuentran. Por ejemplo:

```
"El seu codi de fitxa és codi_fitxa" se renderiza a "El seu codi de fitxa és 2000ABJ"
```

El renderizador de IRIS1 se implementa en la clase `iris_templates.renderers.Iris1TemplateRenderer`.

Las variables disponibles para el template son responsabilidad de las subclases de VariableFinder. En IRIS2 se implementan dos buscadores:

- ConfigVariableFinder: que busca las variables dentro de las variables de configuración dinámicas de IRIS2
- RecordCardVariableFinder: que busca y mapea las variables a partir de la ficha.

Ambas clases se ayudan de las utilidades que ofrece el paquete VarsFinders para mapear de forma sencilla, por ejemplo,
si queremos añadir una nueva variable test_finder que se sustituya con el código de ficha, es tan sencillo como añadir el mapeo
a la clase RecordCardVariableFinder:

```python
class RecordCardVariableFinder(MapVariableFinder):
    """
    Generates the required vars in order to renders templates associated to a RecordCard.
    """
    variables = {
        # Mi nueva variable
        "test_finder": "normalized_record_id",
        # Otras vars
        "id_fitxa": "id",
        "codi_peticio_ciutada": "normalized_record_id",
        "identificador_fitxa": "id",
        "data_peticio_ciutada": {
            "attr": "created_at",
            "filter": date,
        },
        # Resto de variables
    }
```

Como se puede apreciar en el caso de `"data_peticio_ciutada"`, el sistema de variables permite añadir filtros para formatear
tipos de valores nativos o sencillamente personalizar la representación. En iris_templates.templates_contexts.vars_finders encontraréis
los filtros ya implementados.

Los mapeos además pueden ser anidados, por ejemplo, para añadir datos que provengan del grupo de la ficha. Volviendo al ejemplo
de las fichas que es muy completo:

```python
class ResponsibleGroupVariableFinder(MapVariableFinder):
    variables = {
        "firma_perfil": "signature",
        "firma_grup": "signature",
        "icona_perfil": "icon",
        "icona_grup": "icon",
        "icona_signatura": "icon",
    }

class RecordCardVariableFinder(MapVariableFinder):
    """
    Generates the required vars in order to renders templates associated to a RecordCard.
    """
    variables = {
        # Resto de vars

        # Vars anidadas que se recuperan con otro VariableFinder anidado
        "responsible_group": ResponsibleGroupVariableFinder,

        # Resto de variables
    }
```

En el ejemplo anterior, las variables que se mapean ResponsibleGroupVariableFinder estarán disponibles para el template, además de las propias de la ficha.

### Subida de ficheros

La aplicación está configurada con DRF_CHUNKED_UPLOAD para poder subir ficheros por trozos, pero debido a problemas encontrados
en el desarrollo al hacer la unión de los trozos y subir con MINIO, solo se permiten subidas de un trozo.

Para implementar la subida multiparte se tendría que solventar el problema. Actualmente no es un requisito para IRIS2,
pero en el futuro puede ser interesante, más que la subida por trozos aplicar algoritmos para bajar calidad a las imágenes
para las fichas que vengan del api pública.

Hay tres puntos de subida de ficheros:
- Fichas
- Sección de manuales y soportes
- Iconos de firma del grupo

### Anonimización de solicitantes

Si un solicitante solicita su anonimización se debe seguir un proceso determinado más complejo que sencillamente borrar sus datos al momento.
El flujo consiste en marcar al solicitante como pendiente de anonimización, de forma que cuando se cierren todas sus fichas este pasará a ser anonimizado.

Los pasos de este flujo se implementan en:
- Flag pend_anonymize del modelo record_cards.models.Applicant
- Al cerrar la ficha se lanza la tarea record_cards.tasks.anonymize_applicant
- record_cards.tasks.anonymize_applicant revisa si puede ser anonimizado (todas sus fichas cerradas) y si es así lo anonimiza.

### Comunicaciones

IRIS2 permite la comunicación directa entre los operadores, solicitantes y entes externos. Este flujo denominado comunicación intermedia,
ya existía en versiones previas, pero en IRIS2 se permite de todo el flujo dentro de la aplicación.

El flujo consiste en:

- Un operador envía un mensaje al solicitante de la ficha o a un ente externo.
- El solicitante/externo recibe un email con el mensaje y una URL para response. Al clickar el enlace es dirigido a la ATE a una pantalla donde puede contestar el mensaje.
- Al enviar el mensaje, el back comprueba el hash (código asociado al mensaje que permite responder) y si es correcto registra el mensaje.
- El operador ve un aviso de que han contestado su mensaje.
- El operador puede repetir el flujo para solicitar más información o continuar con la tramitación.

Este flujo se implementa a nivel de API en el paquete communications.

Como nota importante, también existen comunicaciones internas entre grupos de IRIS2, pero todas se producen en el ámbito del backoffice.
A efectos prácticos para el backend, la diferencia entre el flujo externo e interno es la comprobación del hash externo,
ya que las internas sencillamente revisa que los grupos destinatarios los tenga el usuario que desea contestar.

### Geocoding

La geolocalización es un proceso crítico para las fichas, ya que la derivación territorial depende de ello.
Al crear una ficha, además de la información que ya se obtiene del usuario, se lanza un proceso que se encarga
de llamar al servicio de geocod para recibir todos los datos y asociarlos a la ficha. Este proceso es `record_cards.tasks.geocode_record`.

## 5. Relación con otros sistemas

El core del backoffice de IRIS2 se relaciona con otros sistemas de diferentes formas. Principalmente existen dos Single
Page Application (SPA) que se connectan al core a través de un API para nutrirse de información. Estas SPA son:
1. el front de IRIS2: se conecta al core utilizando el API privada y que será utilizada por los trabajadores del Ajuntament.
2. la web Atenció en Linia: se conecta utilizando el API Pública y será utilizada por los ciudadanos o entidades que quieran
relacionarse con el Ajuntament.

Además, existen múltiples aplicaciones que se han integrado con IRIS2 o que IRIS2 se ha integrado con ellas. Por ejemplo,
podemos encontrar las aplicaciones Drupal que utilizaran el API Proxy XML u otras como Ariadna o Quiosc, que utilizan
el API privada dentro de la red corporativa.

Por otra parte, encontramos los sistemas que pertenecen a la infraestructura del Ajuntament. Estos son OAM y el API Manager.
OAM es el servicio de autentificación utilizado en la infraestructura del Ajuntament que añade la información de
autentificación en las cabeceras de las peticiones HTTP. El API Manager es el sistema utilizado por el Ajuntament para
gestionar sus APIs.

### Backend de autenticación

La autenticación con OAM y API Manager está implementada como un backend de autenticación de RestFramework que se puede
encontrar en el paquete `profiles.authentication.OAMAuthentication`. Es esta clase la que se encarga de buscar el usuario
de la petición y otros datos relevantes como su departamento.

### Minio

El Storage con Minio se ha implementado siguiendo lo que dicta Django como un Backed de Storage, apoyado sobre el paquete
Open Source `minio_storage`. Se ha tenido que implementar una subclase debido a las particularidades de la arquitectura:

- El backend tiene visibilidad para leer y escribir directamente dentro de la red del ICP de forma rápida y eficaz.
- Los frontales, que reciben URLs para acceder a los ficheros, deben pasar por el resto de capas de arquitecturas.

Teniendo estos casos en cuenta, el storage implementado se encarga de gestionar que la generación de URLs de acceso,
las cuales serán dadas a los usuarios en el backoffice, ya incluyan el dominio final y no la ruta local que usan los
pods para comunicarse.

Este storage puede encontrarse en [main.storage.imi_minio_storage.IMIMinioMediaStorage](./src/main/storage/imi_minio_storage.py)

### Añadir un hash de Aplicación

Los hashes son un ID no conecutivo que se asignan para permitir a las aplicaciones recuperar sus temáticas y los datos
apropiados. Un hash se crea en 3 pasos:

Añadir la constante al modelo de Application, por ejemplo "MY_HASH":

```
class Application(UserTrack):
    """
    Applications that have been integrated with iris

    IRS_TB_MA_SISTEMA
    """
    objects = iris_cachalot(models.Manager(), extra_fields=["description_hash"])

    IRIS_HASH = "AAAA"
    WEB_HASH = "BBB"
    MOBIL_HASH = "CCCC"
    QUIOSCS_HASH = "EEEEE"
    ATE_HASH = "DDDD"
    WEB_DIRECTO_HASH = "XXXXX"
    CONSULTES_DIRECTO_HASH = "EEEEM"
    ATE_DIRECTO_HASH = "OTRRRR"
    PORTAL_HASH = "THIS"
    MY_HASH = "OTHER HASH"

    MY_NEW_PK = 102
```

Añadir a los [data checks](./src/iris_masters/data_checks/applications.py), así se creará la aplicación y se pondrá el hash:

```
def check_required_applications(sender, **kwargs):
    applications = [
      # OTHER HASHES
      {"id": Application.MY_NEW_PK, "description": "NEW APP", "description_ca": "NEW APP",
       "description_hash": Application.MY_HASH},
      # OTHER HASHES
    ]
```

Desplegar y lanzar los data checks de masters, desde la consola del navegador dentro de IRIS ya logueados con un usuario administrador.
Puesto que este proceso revisará los maestros, es mejor lanzarlo por la tarde cuando haya menos carga:

```javascript
$nuxt.$axios.post('/api/masters/masters-data-checks/?delay=0')
```

## 6. Operativa

En esta sección explicaremos los puntos relacionados con la operativa de la aplicación y los despliegues.

La aplicación ofrece algunos comandos de django o `django management commands`, para facilitar las
tareas más frecuentes.

### Configuración

Estas son las variables especificas de IRIS2 que se pueden configurar, no se detallarán las que sean propias de Django
u otros paquetes, ya que es en su documentación donde se encontrará el detalle más actualizado:

Hashes y seguridad:

- APPLICATION_HASH_SALT: salt para generar los hashes de las aplicaciones u órigenes de las fichas en el api pública.
- MESSAGE_HASH_SALT: salta para generar los hashes de la URL de respuesta de comunicaciones externas.

API Manager / Integraciones

- CLIENT_ID: client id para el consumo de APIs en API Manager
- CLIENT_SECRET: secret de API Manager para el consumo de APIs
- BASE_URL: URL para consumir las integraciones a través del APIManager
- AC_INTEGRATIONS: configuración de conexión de las APIs consumidas.
- AC_HEADERS: Headers para las peticiones de APIM
- IDJ_HEADERS: headers para la integración idj
- EXT_HEADERS: headers para la integración EXT
- URLS_XML_PROXY: URL para lanzar las peticiones del XML proxy (debe apuntar al propio backend)
- CITYOS_SERVER
- CITYOS_TOPIC
- KEYTAB_PATH
- KINIT_USER

SFTP

- SFTP_HOSTNAME
- SFTP_USERNAME
- SFTP_PASSWORD
- SFTP_PATH

Twitter:

- TWITTER_ACCESS_TOKEN
- TWITTER_TOKEN_SECRET
- TWITTER_CONSUMER_KEY
- TWITTER_CONSUMER_SECRET

Configurar nombres de las colas celery

- CELERY_HIGH_QUEUE_NAME
- CELERY_LOW_QUEUE_NAME
- CELERY_CITYOS
- TASKS_SCHEDULE: planificación de tareas periódicas

Data checks:

- EXECUTE_DATA_CHEKS: si es verdades se fuerza la ejecución de los data checks al levantar el servidor.

Minio:

Recuerda que Minio genera una URL para acceder a los medias accesible por el usuario en el navegador, pero que internamente el pod python se comunica directamente con el pod minio dentro de su red.

- [MINIO_*](https://django-minio-storage.readthedocs.io/en/latest/usage/#django-settings-configuration)
- MINIO_STORAGE_IRIS1_MEDIA_BUCKET_NAME: para gestionar la división interna entre ficheros de iris2 y de iris1, que están en buckets diferentes.
- MINIO_STORAGE_MEDIA_URL: url para acceder a los ficheros (URL accesible por los usuarios).
- MINIO_STORAGE_ENDPOINT: endpoint interno para que el pod se comunique con minio.

Secciones de paquetes externos:

- [DRF_CHUNKED_UPLOAD_*](https://github.com/jkeifer/drf-chunked-upload#settings)
- [CACHALOT_*](https://django-cachalot.readthedocs.io/en/latest/quickstart.html#settings): *NO TOCAR CONFIGUACIÓN SI NO SE CONOCE SU FUNCIONAMIENTO, AFECTA AL RENDIMIENTO DE LA APLICACIÓN.*
- [MAILER_*](https://django-yubin.readthedocs.io/en/latest/settings.html): implementado con Django Yubin.

Grupos:

- IRIS_CTRLUSER_APPNAME: nombre de la app en control user.
- INTERNAL_GROUPS_SYSTEM: si es verdadero se fijan los grupos en IRIS2, si es falso se cargan desde Control User.
- DEFAULT_ADMIN: matrícula del administrador por defecto, se crear al lanzar los data checks.
- MAX_FILE_SIZE_GROUP_ICON: tamaño máximo de icono de grupo.
- POLYGON_GEO_BCN: si indica si permite geolocalización por polígono de GeoBcn.

### Lanzar tests

Como se ha comentado, IRIS2 distingue diferentes tipos de test en su estrategia, en esta sección explicaremos como
lanzarlos.

Lanzar test unitarios:

```bash
pytest
```

Lanzar test funcionales de API:

```bash
pytest -k test_api.py
```

Lanzar test de integraciones:

```bash
pytest -m external_integration_test
```

### Despliegue

Además de la parte de construcción, controlada por el pipeline de Python del IMI, la arquitectura del IMI requiere realizar
algunos pasos previos para preparar la subida.

#### Lanzar tests funcionales

Además de lanzar los test unitarios, antes de proceder con la subida deberías lanzar los tests funcionales del API,
que requieren un tiempo de ejecución más largo, pero que se complementan con los unitarios para cubrir el máximo de casos.

```bash
pytest
pytest -k test_api.py
```

Con estos dos comandos, lanzamos primero los unitarios (que se lanzan por defecto) y después los funcionales del API.

#### Fijar versiones de API

Si hemos realizado cambios a publicar, debemos ir al punto donde se declaran y subir la versión. Los ficheros,
donde están declaradas son:

- main.iris_open_api.py
- public_api.iris_open_api.py
- xml_proxy.proxy_open_api.py

Basta con cambiar el número el atributo `default_version`, que debería seguir los principios del [versionado semántico](https://semver.org/):

```python
schema_view = get_schema_view(
    openapi.Info(
        title="IRIS2 API",
        default_version='1.110.2',  # HERE THE VERSION HAS TO BE UPDATED !!!
        description="IRIS2 is a complete tool for managing communications between citizens and institutions. "
                    "It's the main citizen support software for the Ajuntament de Barcelona.",
        terms_of_service="-",
        # OTHER ATTRIBUTES
    ),
    # OTHER ATTRIBUTES
)
```

#### Deploy tasks

Para ello, la aplicación ofrece el comando deploy tasks

Este comando se encarga de generar los ficheros de requirements.txt a partir del pipenv.lock y de descargar los yamls
con la especificación del API. Para funcionar, necesita tener el backend funcionando en local en el puerto 8000, para conectarse
y descargar los yaml.

```
./manage.py deploy_tasks
```

#### Listo

Con esto solo quedaría realizar el push y esperar al final del pipeline.

### Commands

Además de deploy tasks, la aplicación viene con otros comandos que ayudan al desarrollo en local. La lista completa se
puede consultar lanzando el manage.py sin parámetros. Aquí destacamos algunos.

- delete_chunked_files: borrar los trozos de las subidas fallidas.
- rebuild_theme_ambits: recalcula los grupos asociados a las temáticas.
- rebuild_theme_tree_cache: borra la caché del árbol.
- invalidate_cachalot: borra la caché de cachalot.
