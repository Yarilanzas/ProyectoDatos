<!--
Sync Impact Report
- Version change: 2.0.0 → 3.0.0 (MAJOR: se elimina una regla de gobernanza del flujo, el punto 12)
- Origen: enmienda acordada por todo el grupo.
- Principios modificados: ninguno (I–XI sin cambios; se conserva el Principio IX: especificación
  confirmada antes que el código y correcciones en confirmaciones separadas).
- Secciones modificadas:
  - Flujo de desarrollo y calidad: se elimina "una rama por capacidad, sin commits directos a main,
    integración por PR" [grupo 12]; se trabaja directamente sobre `main` y cada persona hace
    `git pull` antes de subir cambios. Las reglas que hablaban de "PR" se redactan en términos de
    "cambio" sin alterar su contenido (suite en verde, especificación antes que código, README en el
    mismo cambio, revisión de `Modelo/`, `Persistencia/` y `Bitacora/`). Se conserva intacta la regla
    de contratos compartidos [grupo 13].
  - Governance: las enmiendas ya no se proponen mediante PR, sino como cambio por escrito a este
    archivo con su motivo.
- Secciones añadidas: ninguna
- Secciones eliminadas: ninguna
-->

# Proyecto CRIPTA Constitution

## Core Principles

### I. Estructuras de datos propias (NO NEGOCIABLE)

Las estructuras de datos de los problemas evaluados (agenda de eventos, caché, inventario, historial de
retroceso, bitácora en pantalla, ordenamientos, archivo binario con índice, recorridos de la cripta) MUST
implementarse a mano dentro del proyecto.

- `dict` MUST NOT usarse como índice ni como caché. `set` está sujeto a las mismas condiciones que `dict`.
- MUST NOT usarse implementaciones equivalentes de bibliotecas: `heapq`, `bisect`, `collections`
  (`deque`, `OrderedDict`, `defaultdict`, `Counter`), `networkx` ni ninguna biblioteca de grafos o de
  búsqueda de rutas. Tampoco `sorted()`/`list.sort()` como sustituto de un ordenamiento evaluado.
- Usos auxiliares de `dict`/`set` que no sustituyen a una estructura evaluada (p. ej. parsear JSON o
  argumentos) están permitidos.
- Cada estructura propia MUST documentar la complejidad temporal de sus operaciones principales.

**Razón**: el proyecto es una entrega de Estructuras de Datos II (EIF207, UNA); el valor académico está en
diseñar, implementar y justificar las estructuras, no en delegarlas al lenguaje.

### II. Arquitectura MVC con modelo independiente de la fuente

- `Modelo/` contiene solo reglas del juego y MUST NOT importar red, archivos, consola ni adaptadores.
- `Vista/` solo muestra estado y lee comandos; MUST NOT contener reglas del juego.
- `Controlador/` traduce comandos en acciones del motor y coordina bitácora, guardado y puntajes.
- Los modos `--replay` y `--bench` MUST NOT instanciar la vista.
- Los adaptadores de datos (`API/`, `AlmacenamientoLocalApi/`, `Cache/`, `Gestor/`) MUST ofrecer la misma
  interfaz con red y con `--offline`, de modo que el modelo no sepa de dónde vienen los datos.
- Los datos que cruzan capas MUST viajar como DTOs (`DTOS/`), no como respuestas HTTP crudas.

**Razón**: la separación permite reproducir y medir sin interfaz, y cambiar la fuente sin tocar reglas.

### III. Determinismo y reloj virtual

- Misma cripta, misma semilla y mismas acciones MUST producir la misma partida.
- Toda aleatoriedad MUST derivarse de la semilla de la partida.
- Todo paso del tiempo MUST ocurrir a través del reloj virtual y la agenda de eventos; MUST NOT usarse
  el reloj real ni `sleep` para la lógica del juego.
- Cada acción aceptada MUST anotarse en la bitácora (solo agregar); las acciones rechazadas MUST NOT
  consumir tiempo ni anotarse. `--replay` MUST reproducir la partida completa, incluidas las cargadas
  y continuadas.

**Razón**: la reproducibilidad es requisito funcional (`--replay`) y la base de las pruebas.

### IV. Ningún dato de una cripta concreta en el código

Ningún dato de una cripta concreta (IDs de cripta, salas, objetos o enemigos, llaves, estadísticas,
presupuestos, versiones) MUST escribirse en el código de producción. Todo dato de cripta MUST provenir de
la fuente de datos (servicio web o paquete `--offline`). Los datos de ejemplo solo pueden aparecer en
`tests/` o en paquetes de prueba generados.

**Razón**: el juego debe funcionar con cualquier cripta del servicio, incluidas las que aún no existen.

### V. Pruebas y evidencia de aceptación

- `python -m unittest discover -s tests -v` MUST pasar al 100 % antes de integrar cualquier cambio.
- Las pruebas automatizadas MUST ejecutarse sin red, usando paquetes offline temporales, y solo con
  `unittest` de la biblioteca estándar.
- Cada escenario de aceptación MUST tener al menos una prueba automatizada o un `partida.log` que lo
  ejercite, y esa evidencia MUST citar el identificador del requisito (p. ej. `FR-012`).

**Razón**: el servicio del curso no siempre está disponible, y cada requisito debe poder demostrarse.

### VI. Persistencia versionada y compatibilidad explícita

- Todo archivo persistente (partida `CRPT`, bitácora `CRIPTA-LOG`, caché en disco, tabla de puntajes)
  MUST llevar identificador de formato y versión.
- Al cargar, una diferencia de versión de formato, de cripta o de catálogo MUST rechazarse sin cargar nada,
  con el mensaje `Versión incompatible: ...` y código de salida `2`.
- Los demás errores MUST terminar con `! Error: ...` y código de salida `1`; la salida normal es `0`.
- Cambiar un formato binario o de texto MUST incrementar su número de versión y actualizar el README.

**Razón**: evita corromper partidas o mezclar datos de versiones distintas de la cripta.

### VII. Presupuesto de solicitudes

El `presupuesto_solicitudes` de la cripta MUST respetarse siempre en el modo con red: ninguna ruta de
código (precarga, reintentos ante 429, caché, carga de partidas) puede superarlo. Agotado el presupuesto,
solo fallan las acciones que necesitan red, con `! Error: Se agotó el presupuesto de solicitudes ...`.

**Razón**: es una restricción del servicio del curso y parte de lo que se evalúa.

### VIII. Decisiones medidas

Toda afirmación de rendimiento (en código, README, especificaciones o el Documento de Decisiones) MUST
respaldarse con mediciones que se obtengan con `python main.py --bench`. Una afirmación sin medición
reproducible MUST retirarse o marcarse como hipótesis.

**Razón**: las comparaciones (p. ej. búsqueda binaria vs lineal, disco vs memoria) se evalúan y deben
poder repetirse.

### IX. Especificación antes que implementación

- Una especificación MUST preceder siempre a su implementación.
- El historial de Git MUST mostrar la especificación de cada capacidad confirmada antes del código que la
  implementa.
- Si la especificación estaba mal, MUST corregirse primero la especificación y luego el código, en
  confirmaciones separadas.

**Razón**: el historial debe demostrar que el desarrollo es dirigido por especificaciones.

### X. Trazabilidad de requisitos

- Cada requisito funcional MUST tener un identificador estable (p. ej. `FR-012`) que no se renumera ni se
  reutiliza.
- Cada tarea de `tasks.md` MUST referenciar los requisitos que atiende.
- Las pruebas y bitácoras de evidencia MUST citar el identificador del requisito (Principio V).

**Razón**: permite seguir cada requisito desde la especificación hasta el código y su evidencia.

### XI. Registro de prompts a LLM

Todo comando de Spec Kit invocado con texto propio (`/speckit-constitution`, `/speckit-specify`,
`/speckit-clarify`, `/speckit-plan`, etc.) es un prompt a un LLM y MUST registrarse en `PROMPTS_LLM.md`
en la raíz del repositorio, con al menos la fecha, el comando, el texto enviado y la persona que lo envió.

**Razón**: el uso de LLM debe ser transparente y auditable para la evaluación del curso.

## Restricciones técnicas

- Python 3.11 o superior; la única dependencia externa permitida es `requests`. Añadir otra MUST
  aprobarse según la sección de Gobernanza.
- Aplicación de consola; los comandos y mensajes al usuario se escriben en español.
- La prioridad de opciones de `main.py` y los códigos de salida documentados en el README son contrato
  público: cambiarlos MUST actualizar README y pruebas en el mismo cambio.
- Los archivos generados `*.cripta`, `*.cripta.log`, `puntajes.txt`, `datos_locales/` y `paquete/`
  SHOULD NOT versionarse. `partida.log` y otras bitácoras pueden versionarse cuando sirvan como
  evidencia de aceptación (Principio V).

## Flujo de desarrollo y calidad

- Toda capacidad nueva MUST seguir el flujo Spec Kit: `/speckit-specify` → (`/speckit-clarify`) →
  `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`. El plan MUST incluir una verificación
  explícita contra esta constitución (Constitution Check).
- Se trabaja directamente sobre `main`. Antes de subir cambios, cada persona MUST hacer `git pull`.
- Un cambio solo se sube con la suite de pruebas en verde (Principio V) y con la especificación
  confirmada antes que el código (Principio IX).
- Todo cambio de comportamiento visible (comandos, opciones, formatos, mensajes de error) MUST reflejarse
  en el README en el mismo cambio.
- Un contrato compartido entre personas (interfaces entre capas, DTOs, formatos de archivo, firmas de
  funciones públicas usadas por otra persona) MUST NOT cambiarse unilateralmente: se avisa al grupo
  antes de cambiarlo.
- Los cambios que afecten `Modelo/`, `Persistencia/` o `Bitacora/` SHOULD revisarlos otra persona del grupo.

## Governance

- Esta constitución prevalece sobre cualquier otra práctica del proyecto. Ante conflicto con un plan,
  especificación o tarea, gana la constitución o se enmienda primero.
- Las enmiendas se proponen por escrito (cambio a este archivo), indicando el motivo, y requieren el
  acuerdo del grupo de autores.
- Versionado semántico: MAJOR al eliminar o redefinir un principio; MINOR al añadir un principio o
  sección o ampliar materialmente una guía; PATCH para aclaraciones y redacción.
- Cumplimiento: cada `plan.md` MUST pasar el Constitution Check; cualquier excepción MUST quedar
  justificada en la sección de complejidad del plan. `/speckit-analyze` se usa para detectar
  incumplimientos entre spec, plan y tareas.
- La guía operativa del día a día (comandos, formatos, opciones) está en `README.md`.

**Version**: 3.0.0 | **Ratified**: 2026-11-03 | **Last Amended**: 2026-11-04
