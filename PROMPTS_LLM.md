# PROMPTS_LLM.md

Registro de los prompts usados con el agente de IA durante la Parte 2 (Principio XI de la constitución). Las fechas y horas son las de Costa Rica (UTC−6) y pueden diferir unos minutos de la hora real de envío; el texto de cada prompt es el enviado.

# Persona C — capacidad 001 (niebla de guerra, mapa conocido y viaje «ir a»)

## 2026-11-04 11:59 · Enmienda de la constitución acordada por el grupo (se elimina el punto 12).

- **Fecha**: 2026-11-04 11:59
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Enmienda de la constitución acordada por el grupo (se elimina el punto 12).

**Prompt**

````text
/speckit-constitution Enmienda por acuerdo de todo el grupo: se elimina el punto 12 (una rama por capacidad, sin commits directos a main, integración por PR). Quita de la constitución esa regla y toda mención a ramas por capacidad, PR o a la prohibición de commitear a main (incluidas las referencias cruzadas, por ejemplo en el flujo de desarrollo y en la gobernanza). Se trabaja directamente sobre main; antes de subir cambios cada persona hace git pull. Conserva todo lo demás tal como está, en particular que la especificación se confirme antes del código y en confirmaciones separadas (Principio IX), y que los contratos compartidos no se cambian unilateralmente. Actualiza la versión y el Sync Impact Report.
````

## 2026-11-04 13:41 · Primera redacción de la especificación de niebla de guerra y mapa conocido (reemplazada por la versión siguiente).

- **Fecha**: 2026-11-04 13:41
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Primera redacción de la especificación de niebla de guerra y mapa conocido (reemplazada por la versión siguiente).

**Prompt**

````text
/speckit-specify Capacidad: Niebla de guerra y mapa conocido del jugador (enunciado Parte II §3.3, §5.3 y casos de niebla del Apéndice B). Describe QUÉ debe hacer el programa y por qué, sin decisiones de implementación (estructuras de datos, clases, algoritmos): eso va en el plan. Usa identificadores estables FR-001, FR-002, etc. para cada requisito funcional.

El jugador deja de ver el mapa completo. Para el jugador, cada sala está en uno de tres estados:
- Explorada: el jugador entró a ella al menos una vez. La sala inicial está explorada desde el instante 0. El jugador conoce su nombre, sus salidas, el costo de cada salida y el estado de sus puertas según la última observación.
- Avistada: no está explorada, pero es destino de una salida de una sala explorada. El jugador solo sabe que existe una sala detrás de esa salida.
- Desconocida: ninguna de las anteriores. El jugador no sabe nada.

Memoria de puertas: el jugador observa una puerta cuando está en cualquiera de las dos salas que conecta. El mapa del jugador recuerda el estado de cada puerta tal como estaba en su última observación, aunque haya cambiado después (por ejemplo, una puerta con cierre automático puede figurar abierta en el mapa y estar cerrada en realidad). Al volver a observarla, el mapa se actualiza.

Antorcha: mientras esté encendida, al entrar a una sala también quedan exploradas todas sus vecinas, a través de cualquier salida, abierta o cerrada. Explorar una vecina de esta forma revela su nombre y salidas, no su contenido, y no activa sus enemigos ni sus trampas.

Separación entre mapa y conocimiento: el programa sigue descargando el esqueleto completo y la precarga puede usarlo libremente, porque es infraestructura. Todo lo que la vista muestra y lo que use el futuro comando «ir a» debe derivarse exclusivamente del conocimiento del jugador.

Estado del juego: el conocimiento del jugador se guarda en el archivo de partida, se revierte con el pergamino de retroceso y forma parte de la línea de tiempo (§3.6).

Interfaz: debe existir un comando para ver el mapa conocido: salas exploradas con sus salidas (y el costo de cada una), y las salas avistadas.

Escenarios de aceptación obligatorios (Apéndice B), cada uno con su resultado definido:
1. Con la antorcha encendida, entrar a una sala explora sus vecinas sin activar sus enemigos ni sus trampas.
2. Un pergamino revierte una entrada hecha con la antorcha encendida: las salas exploradas por la antorcha vuelven a su estado anterior.
3. El mapa recuerda abierta una puerta que en realidad está cerrada: al observarla, el mapa se actualiza.
Añade además escenarios para: sala inicial explorada en el instante 0, paso de avistada a explorada al entrar, y guardar y cargar una partida conservando el conocimiento.

Fuera de alcance de esta especificación: el comando «ir a» (spec aparte), la búsqueda de rutas del cazador y la distinción visual de cazadores en la vista.

Si algo del enunciado es ambiguo, márcalo como [NEEDS CLARIFICATION] en vez de suponerlo.
````

## 2026-11-04 13:45 · Especificación vigente: niebla de guerra, mapa conocido y viaje automático «ir a» (spec.md).

- **Fecha**: 2026-11-04 13:45
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Especificación vigente: niebla de guerra, mapa conocido y viaje automático «ir a» (spec.md).

**Prompt**

````text
/speckit-specify Capacidad: Niebla de guerra, mapa conocido y viaje automático «ir a» (enunciado Parte II §3.3, §3.4, §5.3 y casos de niebla e «ir a» del Apéndice B). Describe QUÉ debe hacer el programa y por qué, sin decisiones de implementación (estructuras de datos, clases, algoritmos): eso va en el plan. Usa identificadores estables FR-001, FR-002, etc. para cada requisito funcional.

El jugador deja de ver el mapa completo. Para el jugador, cada sala está en uno de tres estados:
- Explorada: el jugador entró a ella al menos una vez. La sala inicial está explorada desde el instante 0. El jugador conoce su nombre, sus salidas, el costo de cada salida y el estado de sus puertas según la última observación.
- Avistada: no está explorada, pero es destino de una salida de una sala explorada. El jugador solo sabe que existe una sala detrás de esa salida.
- Desconocida: ninguna de las anteriores. El jugador no sabe nada.

Memoria de puertas: el jugador observa una puerta cuando está en cualquiera de las dos salas que conecta. El mapa del jugador recuerda el estado de cada puerta tal como estaba en su última observación, aunque haya cambiado después (por ejemplo, una puerta con cierre automático puede figurar abierta en el mapa y estar cerrada en realidad). Al volver a observarla, el mapa se actualiza.

Antorcha: mientras esté encendida, al entrar a una sala también quedan exploradas todas sus vecinas, a través de cualquier salida, abierta o cerrada. Explorar una vecina de esta forma revela su nombre y salidas, no su contenido, y no activa sus enemigos ni sus trampas.

Separación entre mapa y conocimiento: el programa sigue descargando el esqueleto completo y la precarga puede usarlo libremente, porque es infraestructura. Todo lo que la vista muestra y lo que usa el comando «ir a» debe derivarse exclusivamente del conocimiento del jugador.

Estado del juego: el conocimiento del jugador se guarda en el archivo de partida, se revierte con el pergamino de retroceso y forma parte de la línea de tiempo (§3.6).

Interfaz: debe existir un comando para ver el mapa conocido: salas exploradas con sus salidas (y el costo de cada una), y las salas avistadas.

Viaje automático «ir a <sala>»: lleva al jugador a una sala explorada mediante una secuencia de movimientos ordinarios.
- La ruta se calcula solo con el conocimiento del jugador: salas exploradas y salidas que el mapa recuerda abiertas. Se minimiza la suma de costos y se desempata igual que el cazador: primer paso hacia la vecina de menor id.
- Cada paso es una acción completa del jugador: consume tiempo y entre paso y paso ocurren los eventos del reloj.
- La ruta se recalcula antes de cada paso con el conocimiento vigente; si al llegar a una sala el jugador observa una puerta cerrada de su ruta, el siguiente cálculo la evita.
- El viaje se detiene cuando: llega al destino, entra a una sala con enemigos (activos o dormidos), recibe daño, o deja de existir una ruta conocida.
- No abre puertas aunque el jugador tenga la llave.
- En partida.log cada paso es un movimiento individual, y la orden ir a se registra además como comentario.
- El pergamino revierte solo el último paso y el viaje no continúa.

Escenarios de aceptación obligatorios (Apéndice B), cada uno con su resultado definido:
1. Con la antorcha encendida, entrar a una sala explora sus vecinas sin activar sus enemigos ni sus trampas.
2. Un pergamino revierte una entrada hecha con la antorcha encendida: las salas exploradas por la antorcha vuelven a su estado anterior.
3. El mapa recuerda abierta una puerta que en realidad está cerrada: al observarla, el mapa se actualiza.
4. ir a hacia una sala no explorada: se rechaza y no consume tiempo.
5. El mapa recuerda abierta una puerta que en realidad está cerrada: al observarla se recalcula la ruta; si no queda ruta, el viaje se detiene sin consumir tiempo adicional.
6. ir a entra a una sala con enemigos dormidos: se activan según la Parte I (§2.4) y el viaje se detiene.
7. Un pergamino durante un viaje: revierte solo el último paso y el viaje no continúa.
Añade además escenarios para: sala inicial explorada en el instante 0, paso de avistada a explorada al entrar, y guardar y cargar una partida conservando el conocimiento.

Fuera de alcance de esta especificación: la búsqueda de rutas del cazador (es de otra capacidad) y cómo se calcula la ruta internamente (eso va en el plan).

Antes de redactar, revisa el README y el código existente para usar la misma terminología y respetar el comportamiento ya implementado de la Parte I (antorcha, pergamino de retroceso, Historial, guardado de partidas). Usa eso solo para que la especificación sea coherente: no copies nombres de clases, archivos ni estructuras a la spec.

Si algo del enunciado es ambiguo, márcalo como [NEEDS CLARIFICATION] en vez de suponerlo.
````

## 2026-11-04 14:29 · Plan técnico de la capacidad (plan.md, research.md, data-model.md, contratos, quickstart).

- **Fecha**: 2026-11-04 14:29
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Plan técnico de la capacidad (plan.md, research.md, data-model.md, contratos, quickstart).

**Prompt**

````text
/speckit-plan Plan técnico para la especificación specs/001-niebla-mapa-ir-a/spec.md (niebla de guerra, mapa conocido y «ir a»). No implementes nada: solo genera los documentos del plan.

Antes de planear, lee la constitución (.specify/memory/constitution.md), la spec, el README y el código existente (MotorSimulacion, Historial/pergamino de retroceso, modelo de sala y puertas, antorcha, persistencia del archivo de partida, bitácora y replay, controlador y vista), para integrar la capacidad con lo ya implementado. Cada requisito del plan debe citar los FR de la spec que atiende.

Restricciones de la constitución que el plan debe cumplir y verificar en el Constitution Check:
- Estructuras de datos propias: sin dict ni set como índice o caché, y sin heapq, bisect, collections (deque, OrderedDict, defaultdict, Counter), networkx ni bibliotecas de grafos o de rutas. Tampoco sorted()/list.sort() como sustituto de un ordenamiento evaluado. Si se necesita una cola de prioridad, se implementa a mano.
- Documentar la complejidad temporal de las operaciones principales de cada estructura propia.
- Determinismo: misma cripta, misma semilla y mismas acciones dan la misma partida.
- MVC: el modelo no depende de la vista; --replay y --bench no instancian la vista.
- Ningún dato de una cripta concreta en el código.
- Toda afirmación de rendimiento debe respaldarse con una medición de --bench: el plan debe definir qué se mide.

Decisiones de diseño que el plan debe resolver, con alternativas, justificación y complejidad:
1. Representación del conocimiento del jugador (§5.3): consultar si una sala es explorada, avistada o desconocida, y el estado recordado de una puerta (abierta, cerrada o sin observar), son operaciones frecuentes (cada vista, cada paso de «ir a», cada actualización por antorcha). Explorar salas nuevas debe costar proporcionalmente a las salas reveladas, no al tamaño del mapa conocido.
2. Registro de cambios en el Historial: todo cambio del conocimiento debe formar parte de la acción del jugador para que el pergamino lo revierta exactamente, incluidas las salas exploradas por la antorcha (FR-014). El diseño debe hacer barato registrar e invertir cambios.
3. Persistencia: cómo se guarda y restaura el conocimiento en el archivo de partida, el cambio de versión de formato, y cómo se reproduce con --replay incluidas las partidas cargadas (FR-015 a FR-017).
4. Comandos nuevos (`mapa` e `ir a <sala>`) y su integración en el controlador, la ayuda y la bitácora, con las líneas de comentario de FR-030.
5. Búsqueda de la ruta de «ir a»: debe correr sobre el subgrafo conocido, minimizar el costo total y desempatar por el primer paso hacia la vecina de menor id. DECISIÓN PENDIENTE con otra persona del grupo: si comparte implementación con la búsqueda del cazador o va separada. No la decidas: presenta ambas opciones con sus ventajas y costos, y propón un diseño donde la ruta de «ir a» quede detrás de una interfaz mínima, de modo que cualquiera de las dos opciones se pueda adoptar sin rehacer el resto del plan. Registra la decisión como pendiente.
6. Costo de cada salida: la spec asume 100 (el de `mover`) mientras otra capacidad no defina el costo propio. Diseña para que el costo se lea del dato de la salida y no esté escrito en el código de esta capacidad.

Genera los documentos que pide la plantilla de plan (plan.md, research.md, data-model.md, contratos y quickstart) dentro de specs/001-niebla-mapa-ir-a/. Si algo es ambiguo, déjalo como pregunta abierta en el plan; no lo supongas.
````

## 2026-11-06 11:15 · Resolver en plan.md y research.md las dudas tomadas del enunciado de la Parte II.

- **Fecha**: 2026-11-06 11:15
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Resolver en plan.md y research.md las dudas tomadas del enunciado de la Parte II.

**Prompt**

````text
Actualiza specs/001-niebla-mapa-ir-a/plan.md y research.md con estas resoluciones tomadas del enunciado de la Parte II. No cambies nada más y no toques spec.md.
- P-02 resuelta: el campo se llama `costo` (§3.1 y §4.1), es un entero mayor o igual que 1, vale 100 si la salida no lo declara y es el mismo en ambos sentidos. Sigue pendiente confirmar con el grupo quién cambia mover_jugador.
- P-08 resuelta: §6.1 fija 5 ms para el cálculo de un paso de «ir a» con el mapa conocido completo de la cripta de referencia (los valores pueden ajustarse por enmienda). La medición M4 de --bench debe verificar ese límite y el objetivo de rendimiento del plan debe citarlo.
- P-09 resuelta: manda FR-027. El enunciado (§3.4) lista exactamente las condiciones de parada: llegar al destino, entrar a una sala con enemigos, recibir daño, o que deje de existir una ruta conocida.
Marca P-02, P-08 y P-09 como resueltas en la tabla de Preguntas abiertas, citando el enunciado. Deja las demás abiertas.
````

## 2026-11-06 11:20 · Lista de tareas de la capacidad (tasks.md).

- **Fecha**: 2026-11-06 11:20
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Lista de tareas de la capacidad (tasks.md).

**Prompt**

````text
/speckit-tasks Genera tasks.md para specs/001-niebla-mapa-ir-a a partir de la spec y el plan. Cada tarea debe citar los FR (y los PR-xx del plan) que atiende, e indicar el archivo que toca. Cada escenario de aceptación de la spec debe tener una tarea de prueba automatizada que cite su FR.

Organiza las tareas en este orden, con puntos de control entre fases:
1. Costo de salida y acceso único (campo `costo`, entero mayor o igual que 1, 100 si no se declara, igual en ambos sentidos según §3.1).
2. Conocimiento del jugador, memoria de puertas y antorcha, integrados al Historial (historias 1 y 2).
3. Comando `mapa` (historia 3).
4. Viaje «ir a» (historia 4). La tarea del cuerpo de `primer_paso` queda marcada como bloqueada por D-PEND-01; el resto del viaje se prueba con un buscador de prueba inyectado.
5. Fase aparte, marcada «requiere aviso previo al grupo» (contratos compartidos): persistencia de partida v3, bitácora v2 con comentarios, directiva @cargar, corrección de --replay y de las puertas al cargar, y --replay sin instanciar la vista.
6. Mediciones de --bench M1 a M6, con mapas sintéticos en tests/ (la cripta de referencia aún no está publicada) y el límite de 5 ms por paso de «ir a» de §6.1 tomado de una sola constante.
7. README, Documento de Decisiones y matriz de trazabilidad.

Marca qué tareas se pueden hacer en paralelo y cuáles dependen de otras personas. No implementes nada.
````

## 2026-11-06 13:47 · Análisis de consistencia entre spec, plan y tareas.

- **Fecha**: 2026-11-06 13:47
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Análisis de consistencia entre spec, plan y tareas.

**Prompt**

````text
/speckit-analyze
````

## 2026-11-06 13:47 · Corregir tasks.md tras /speckit-analyze (T011 y otros hallazgos).

- **Fecha**: 2026-11-06 13:47
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Corregir tasks.md tras /speckit-analyze (T011 y otros hallazgos).

**Prompt**

````text
En specs/001-niebla-mapa-ir-a/tasks.md corrige esto y no cambies nada más:
- T011: según el enunciado §3.1 la regla del costo de salida aplica a todos los actores, incluidos los enemigos: el intervalo de su movimiento es max(1, costo_salida * 100 // velocidad). Cambia la tarea para que mover_enemigo también use motor.costo_salida, o márcala como «depende de quién implemente §3.1».
- Marca toda la Fase 1 como «pendiente de confirmar con el grupo quién implementa el costo de §3.1 (afecta a todos los actores). Si lo hace otra persona, esta capacidad solo consume motor.costo_salida con valor por defecto 100».
````

## 2026-11-06 14:01 · Aclaración PATCH de la constitución sobre el Principio XI (PROMPTS_LLM.md).

- **Fecha**: 2026-11-06 14:01
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Aclaración PATCH de la constitución sobre el Principio XI (PROMPTS_LLM.md).

**Prompt**

````text
/speckit-constitution Aclaración (PATCH): el Principio XI y toda mención de PROMPTS_LLM.md deben decir que el registro de prompts se lleva en el documento de prompts del grupo (Word, Prompts.docx en la raíz del repositorio), con fecha, comando, texto enviado y persona. No cambies nada más.
````

## 2026-11-06 14:01 · Agregar SC-007 y otros ajustes de spec/plan tras el análisis.

- **Fecha**: 2026-11-06 14:01
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Agregar SC-007 y otros ajustes de spec/plan tras el análisis.

**Prompt**

````text
Haz estos cambios en specs/001-niebla-mapa-ir-a y no cambies nada más:
1. spec.md: agrega el criterio de éxito SC-007: el cálculo de un paso de «ir a» tarda 5 ms o menos con el mapa conocido completo de la cripta de referencia (enunciado §6.1; puede ajustarse por enmienda). En la suposición sobre costos, aclara que esta capacidad solo LEE el costo de cada salida mediante un acceso único (valor 100 si no hay dato). Implementar el costo de §3.1 para todos los actores (jugador y enemigos), el campo costo en el DTO Salida y la versión de formato de la caché del esqueleto corresponden a la capacidad de terreno y costos, no a esta.
2. tasks.md: reduce la Fase 1 a una sola tarea: crear motor.costo_salida(salida), solo de lectura, que devuelve el costo de la salida o 100 si no lo trae, sin cambiar el movimiento de ningún actor. Marca las demás tareas de la Fase 1 (T002, T003 en lo referido a enemigos, T006, T008, T010, T011, T012) como «a cargo de quien implemente §3.1», sin borrarlas ni renumerar. Cita SC-007 en T104. Mueve T061 (pregunta P-05) a la Fase 0. Indica qué sección del README sube con cada fase.
3. plan.md: corrige la frase que dice que Modelo/ no importa nada fuera de sí mismo, porque mapa_conocido() devuelve un DTO de DTOS/.
````

## 2026-11-06 14:11 · Corregir la fila del Principio XI en el Constitution Check de plan.md.

- **Fecha**: 2026-11-06 14:11
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Corregir la fila del Principio XI en el Constitution Check de plan.md.

**Prompt**

````text
En specs/001-niebla-mapa-ir-a corrige solo esto: (1) plan.md, fila del Principio XI en el Constitution Check: el registro de prompts ya se lleva en el documento de prompts del grupo (Prompts.docx, Word), así que marca el principio como cumplido y quita la mención de que PROMPTS_LLM.md no existe. (2) tasks.md, T004: ya está decidido dónde se lleva el registro (Prompts.docx); reformula la tarea como «al final, pasar los prompts de cada persona al Word, con fecha, comando, texto enviado y persona», sin pedir confirmación al grupo. No cambies nada más y no renumeres.
````

## 2026-11-06 14:15 · Corregir el resultado del gate del plan (Principio XI ya no bloqueante).

- **Fecha**: 2026-11-06 14:15
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Corregir el resultado del gate del plan (Principio XI ya no bloqueante).

**Prompt**

````text
Sí: corrige plan.md:72 para que el resultado del gate ya no diga que el Principio XI es bloqueante, corrige la fila de T004 en la tabla de dependencias de tasks.md (el registro ya se lleva en Prompts.docx y el Principio XI está resuelto), y mueve T004 a la Fase 7 sin renumerar. No cambies nada más.
````

## 2026-11-06 14:25 · Fase 0 (preparación) y Fase 1 (T118).

- **Fecha**: 2026-11-06 14:25
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Fase 0 (preparación) y Fase 1 (T118).

**Prompt**

````text
/speckit-implement Implementa únicamente la Fase 0 (preparación) y la Fase 1 (T118) de specs/001-niebla-mapa-ir-a/tasks.md, y detente en el punto de control 1: no empieces la Fase 2. Marca cada tarea terminada con [X] en tasks.md. No toques las tareas marcadas «a cargo de quien implemente §3.1», no cambies archivos fuera de los que cita cada tarea y no hagas commit. Ejecuta las pruebas con `py -m unittest discover -s tests -v` (el Python del sistema de Claude Opus 5.5 no tiene requests), y si alguna falla, detente y reporta cuál. Al terminar, dime qué archivos cambiaste y qué tareas quedaron hechas.
````

## 2026-11-06 15:19 · Fase 2: conocimiento del jugador, memoria de puertas y antorcha.

- **Fecha**: 2026-11-06 15:19
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Fase 2: conocimiento del jugador, memoria de puertas y antorcha.

**Prompt**

````text
/speckit-implement Implementa únicamente la Fase 2 (conocimiento del jugador, memoria de puertas y antorcha, integrados al Historial) de specs/001-niebla-mapa-ir-a/tasks.md, y detente en el punto de control 2: no empieces la Fase 3. Respeta el orden de las tareas: primero las pruebas de cada historia, verifica que fallen, y luego el código. Marca cada tarea terminada con [X] en tasks.md. No toques las tareas de otras capacidades ni de la Fase 5, no cambies archivos fuera de los que cita cada tarea y no hagas commit. Respeta la constitución: estructuras propias (sin dict ni set como índice, sin heapq/bisect/collections), determinismo y complejidades documentadas en los docstrings. Ejecuta las pruebas con `py -m unittest discover -s tests -v` y, si alguna falla, detente y reporta cuál. Al terminar, dime qué archivos cambiaste, qué tareas quedaron hechas y qué limitaciones quedan (por ejemplo, que al cargar una partida el mapa vuelve a la sala inicial hasta la Fase 5).
````

## 2026-11-06 15:47 · Ajustar una prueba de la Fase 3 al nuevo orden de ruta y repetir la suite.

- **Fecha**: 2026-11-06 15:47
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Ajustar una prueba de la Fase 3 al nuevo orden de ruta y repetir la suite.

**Prompt**

````text
Sí, aplica el cambio de ruta a E, S, O, N, E en esa prueba y vuelve a correr la suite completa. Si todo pasa, deja las tareas T013 a T032 marcadas [X]; si algo sigue fallando, desmarca las que dependan de lo que falla y reporta cuál. No cambies nada más y no hagas commit.
````

## 2026-11-06 15:49 · Redactar el bloque de Markdown de niebla de guerra para pegarlo a mano en el README (T111).

- **Fecha**: 2026-11-06 15:49
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Redactar el bloque de Markdown de niebla de guerra para pegarlo a mano en el README (T111).

**Prompt**

````text
Redacta la parte de niebla de T111 como un bloque de Markdown para que yo lo pegue a mano en README.md. No edites README.md, porque está en UTF-16. Describe solo lo que ya está implementado hasta la Fase 2 (estados de sala, memoria de puertas, antorcha, el mensaje «Una puerta se cerró sola.» solo si el jugador ve la puerta y la línea Salidas:), no menciones `mapa` ni `ir a` porque todavía no existen, y dime en qué sección del README conviene pegarlo.
````

## 2026-11-06 16:09 · Fase 3: comando `mapa`.

- **Fecha**: 2026-11-06 16:09
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Fase 3: comando `mapa`.

**Prompt**

````text
/speckit-implement Implementa únicamente la Fase 3 (comando `mapa`) de specs/001-niebla-mapa-ir-a/tasks.md, y detente en el punto de control 3: no empieces la Fase 4. Respeta el orden de las tareas: primero las pruebas, verifica que fallen, y luego el código. Marca cada tarea terminada con [X] en tasks.md solo después de que la suite pase. No toques las tareas de otras capacidades ni de la Fase 5, no cambies archivos fuera de los que cita cada tarea y no hagas commit. Respeta la constitución: estructuras propias (sin dict ni set como índice, sin heapq/bisect/collections), determinismo y complejidades documentadas en los docstrings. Si el comando necesita README, redacta el texto como bloque de Markdown para que yo lo pegue a mano, sin editar README.md porque está en UTF-16. Ejecuta las pruebas con `py -m unittest discover -s tests -v` y, si alguna falla, detente y reporta cuál. Al terminar, dime qué archivos cambiaste, qué tareas quedaron hechas y qué limitaciones quedan.
````

## 2026-11-09 13:07 · Aclaración PATCH de la constitución sobre el Principio XI (registro de prompts en PROMPTS_LLM.md).

- **Fecha**: 2026-11-09 13:07
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Aclaración PATCH de la constitución sobre el Principio XI (registro de prompts en PROMPTS_LLM.md).

**Prompt**

````text
/speckit-constitution Aclaración (PATCH): el Principio XI debe decir que el registro de prompts se lleva en PROMPTS_LLM.md en la raíz del repositorio (como exige el enunciado §7.2), con fecha, modelo, prompt textual y para qué se usó la respuesta. Cada persona puede llevar sus notas por separado, pero el archivo entregado es uno solo. No cambies nada más.
````

## 2026-11-09 13:43 · Corregir documentación de spec 001 y constitución según respuestas del grupo (D-PEND-01, P-05).

- **Fecha**: 2026-11-09 13:43
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Corregir documentación de spec 001 y constitución según respuestas del grupo (D-PEND-01, P-05).

**Prompt**

````text
Corrige solo documentación de specs/001-niebla-mapa-ir-a/ y .specify/memory/constitution.md. No toques código ni pruebas. Aplica estos cambios:

1. I1: en plan.md (Decisión 6, PR-13, P-02, el árbol de archivos), research.md (R7) y data-model.md (sección Salida), esta capacidad SOLO LEE el costo mediante motor.costo_salida (100 si la salida no trae costo). El campo costo de Salida y el cambio de mover son de la capacidad de terreno y costos. Quita todo texto que diga lo contrario.
2. I2, I3, I4: en tasks.md marca lo hecho con su commit (T003 parte de esta capacidad: 6ed5b92; T111 parte de niebla y mapa: c74fd6a y 919ad9f; verifica que sea cierto antes de marcar). Reescribe el Punto de control 0: T002 pasa a ser solo de la otra capacidad, T061 pasa a «antes de la Fase 4».
3. I5: actualiza en plan.md la versión de la constitución (3.0.1) y el conteo de pruebas (185 OK). Corrige la frase del Sync Impact Report de la constitución sobre PROMPTS_LLM.md solo si ya es falsa.
4. I6: cambia el estado de spec.md de Draft a Approved.
5. U1 (P-04): agrega a FR-027 que, si el motor rechaza un paso a mitad del viaje, ir a se detiene e informa el mismo mensaje de rechazo que daría mover; el viaje termina sin consumir tiempo adicional.
6. U4 (P-03): agrega a FR-024 que, ante dos salidas hacia la misma vecina con el mismo costo, gana la primera en el orden N, S, E, O.
7. U5: en contracts/comandos.md, mapa ignora cualquier argumento.
8. U2: en la matriz de trazabilidad (T115) indica que FR-005 y FR-024 dependen de T010 para probarse con costos reales.
9. Actualiza el Principio XI de la constitución para que diga PROMPTS_LLM.md en la raíz del repositorio, armado al final a partir de las notas de cada persona (fecha, modelo, prompt textual, para qué se usó). Es un cambio PATCH: súbela a 3.0.2 con su Sync Impact Report. Ajusta T004 y la fila del plan que lo menciona.
No hagas commit. Al terminar, lista cada archivo cambiado y qué hallazgo resolvió.
````

## 2026-11-09 14:03 · Registrar en la spec la respuesta de Persona D.

- **Fecha**: 2026-11-09 14:03
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Registrar en la spec la respuesta de Persona D.

**Prompt**

````text
Solo documentación de specs/001-niebla-mapa-ir-a/. No toques código ni pruebas. Registra la respuesta de Persona D (línea de tiempo y persistencia, spec 004):
1. plan.md, P-07: aceptado por D, con cuatro condiciones: (a) queda escrito en contracts/formato-bitacora.md; (b) `--replay --hasta t` cuenta el reloj a través de las líneas @cargar; (c) una versión incompatible se rechaza con código 2, como hoy; (d) se actualiza el README, porque «cargar no se anota» deja de ser cierto. Aplica lo mismo a T066/T067 en tasks.md.
2. Formato de partida (plan y contracts/formato-partida.md): D define el layout. Propuesta: un bloque de conocimiento (nuestro) y uno de línea de tiempo (de D) dentro del mismo salto a la versión 3 del CRPT. D no guarda el costo de las salidas en el CRPT; lo toma del esqueleto.
3. tasks.md, Fase 5: agrega una tarea nueva para que `Conocimiento` pueda copiarse y serializarse, con cambios reversibles (aplicar/invertir), porque los puntos de control de D lo necesitan. Atiende FR-015, FR-016. Con su prueba primero. Numérala al final de la fase para no renumerar las demás.
4. T117 (revisión): anota que quien revisa los cambios en Bitacora/, Persistencia/ y main.py es Persona D.
5. No cambies FR ni SC. Al terminar, lista los cambios.
No hagas commit.
````

## 2026-11-09 21:53 · Registrar en tasks.md y contratos las respuestas del grupo (P-07, P-10, T066).

- **Fecha**: 2026-11-09 21:53
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Registrar en tasks.md y contratos las respuestas del grupo (P-07, P-10, T066).

**Prompt**

````text
Solo documentación de specs/001-niebla-mapa-ir-a/. No toques código ni pruebas ni spec.md. Registra las respuestas del grupo:
1. plan.md, D-PEND-01: ✅ Resuelta con la opción A. Persona A implementa la búsqueda compartida en Modelo/BusquedaRuta.py, con la cola de prioridad en Modelo/ColaPrioridad.py, y cumple la interfaz primer_paso de contracts/interfaz-ruta.md. Modelo/rutas_ir_a.py solo la llama. Actualiza la Decisión 5, la fila de la tabla de fases y research.md R6 (la opción B queda descartada).
2. plan.md, P-05: ✅ Confirmada por Personas A y B: «las dos salas que conecta» observa la salida dirigida A→B desde B, y el viaje puede volver por B→A. Se mantiene la lectura del plan.
3. tasks.md: T061 pasa a [X] con esa respuesta. Reescribe T062 (el cuerpo de primer_paso delega en Modelo/BusquedaRuta.py de Persona A; sigue BLOQUEADA hasta que A suba su módulo; sin heapq ni sorted() la responsabilidad es de A), T063 (correr el contrato contra primer_paso y contra el cazador con la misma tabla de desempates) y T064. Quita de T114 la justificación de duplicación (ya no aplica). Actualiza la tabla de dependencias: T062 a T065 y T109 dependen de que A suba Modelo/BusquedaRuta.py.
4. contracts/interfaz-ruta.md: quita el condicional «Si se elige la opción A» (ya es la A) y deja asentado que la implementación de A debe pasar las 7 obligaciones y la prueba de contrato.
Al terminar, lista los cambios. No hagas commit.
````

## 2026-11-09 22:00 · Implementar la Fase 4 («ir a»).

- **Fecha**: 2026-11-09 22:12
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Implementar la Fase 4 («ir a»).

**Prompt**

````text
/speckit-implement Implementa solo la Fase 4 de specs/001-niebla-mapa-ir-a/tasks.md (el comando «ir a», §3.4 del enunciado), incluidas T043 con el desempate N, S, E, O de FR-024 y T060 (FR-027f). La spec ya está confirmada en Git. Reglas:
1. Pruebas primero: escribe y ejecuta las pruebas de la fase y comprueba que fallan antes de escribir código. Cada prueba cita el FR que ejercita.
2. Marca una tarea como [X] solo después de ver la suite completa en verde (py -m unittest discover -s tests). No marques nada antes.
3. D-PEND-01 está resuelta con la opción A: Persona A implementa la búsqueda en Modelo/BusquedaRuta.py y todavía no existe. No la implementes ni crees ese archivo ni ColaPrioridad.py. Crea Modelo/rutas_ir_a.py con la interfaz primer_paso(grafo, origen, destino) de contracts/interfaz-ruta.md, que mientras tanto lanza NotImplementedError (el controlador lo convierte en un aviso sin efectos, T058). Todo se prueba con un buscador de prueba inyectado. Deja T062 a T065 sin marcar.
4. «ir a» solo usa el mapa conocido, no abre puertas, y cada paso es una acción completa del jugador. Para cuando: llega al destino, entra a una sala con enemigos, recibe daño, no hay ruta conocida, termina la partida o el motor rechaza un paso (FR-027).
5. Reglas de la constitución: sin dict/set como índice, sin heapq/bisect/collections/networkx, sin sorted() como sustituto de un ordenamiento evaluado, determinismo, el modelo no instancia la vista.
6. No toques contratos compartidos (formato de partida, bitácora, DTOs de otras personas) sin avisar. Si necesitas hacerlo, detente y dímelo.
7. No hagas commit. Al terminar, dime: archivos cambiados, tareas marcadas, tareas sin marcar y por qué, y el resultado de la suite.
````

## 2026-11-09 22:32 · Clasificar las tareas de la Fase 5 en tandas según dependencias.

- **Fecha**: 2026-11-09 22:32
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Clasificar las tareas de la Fase 5 en tandas según dependencias.

**Prompt**

````text
Solo lectura, no modifiques nada. Lee la Fase 5 de specs/001-niebla-mapa-ir-a/tasks.md y clasifica todas sus tareas en tres grupos: (1) pueden empezar ya, sin esperar a nadie; (2) esperan la disposición final del CRPT 3 de Persona D (P-10) o su --replay --hasta; (3) esperan Modelo/BusquedaRuta.py de Persona A u otra cosa. Para cada tarea en (2) o (3) di exactamente qué falta. Dentro del grupo (1) propón un orden de ejecución y marca cuáles tocan módulos de otras personas (Bitacora/, Persistencia/, main.py). Es una lista, no un plan largo.
````

## 2026-11-09 22:34 · Tanda 1 de la Fase 5: RegistroConocimiento y Conocimiento.exportar/restaurar/copiar.

- **Fecha**: 2026-11-09 22:34
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Tanda 1 de la Fase 5: RegistroConocimiento y Conocimiento.exportar/restaurar/copiar.

**Prompt**

````text
/speckit-implement Implementa solo estas tareas de la Fase 5 de specs/001-niebla-mapa-ir-a/tasks.md: T069, T074, T075 y T119. No toques ninguna otra. Reglas:
1. Pruebas primero: escribe T069 y las pruebas de T119 y comprueba que fallan por aserción antes del código (no solo por importación). Cada prueba cita el FR que ejercita.
2. Marca una tarea [X] solo después de ver la suite completa en verde (py -m unittest discover -s tests). No marques nada antes.
3. T075 usa el formato exacto de contracts/formato-partida.md (bloque de conocimiento). No modifiques ese contrato ni Persistencia/FormatoBinario.py, ArchivoPartida.py ni ConversorPartida.py: eso es T076 a T080 y espera la disposición de Persona D.
4. T119: lotes con valor anterior y nuevo, aplicar e invertir; Modelo/retroceso.py no cambia y el Historial sigue funcionando igual.
5. Sin dict/set como índice, sin heapq/bisect/collections, sin sorted() como sustituto de un ordenamiento evaluado, complejidad documentada en los docstrings, determinismo.
6. Además corrige en tasks.md dos textos desactualizados: T060 (la spec ya está confirmada en Git, commit da81905) y el Punto de control 5 (debe incluir también las implementaciones T074 a T080, T084, T085, T091 a T094, T096 y T097).
7. No hagas commit. Al terminar dime: archivos cambiados, tareas marcadas, y el resultado de la suite.
````

## 2026-11-10 10:17 · Tanda 2 de la Fase 5: bitácora v2 con comentarios y @cargar, recarga en el Reproductor.

- **Fecha**: 2026-11-10 10:17
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Tanda 2 de la Fase 5: bitácora v2 con comentarios y @cargar, recarga en el Reproductor.

**Prompt**

````text
/speckit-implement Implementa solo estas tareas de la Fase 5 de specs/001-niebla-mapa-ir-a/tasks.md: T081, T082, T083, T084, T085, T086, T091 y T093. No hagas T092 ni T094 (van en otra tanda, junto con el formato v3). Reglas:
1. Pruebas primero: escribe T081, T082, T083 y T086 y comprueba que fallan por aserción (no solo por importación; usa stubs si hace falta) antes del código. Cada prueba cita el FR que ejercita.
2. Marca una tarea [X] solo después de ver la suite completa en verde (py -m unittest discover -s tests). No marques nada antes.
3. Contratos que ya le prometimos a Persona D: leer_bitacora devuelve ("@cargar", "") dentro de acciones; Reproductor acepta recargar=None y, al llegar a @cargar, llama a recargar() y sigue con el motor que devuelve; sin recargar y con @cargar da error y no se ignora; una directiva desconocida lanza VersionIncompatible (código 2); CRIPTA-LOG 1 se rechaza con código 2; registrar rechaza nombres que empiezan con # o @.
4. Como T092 no se hace, nada debe escribir @cargar todavía en una bitácora real: las pruebas de integración existentes (guardar, cargar, continuar, replay) tienen que seguir pasando sin cambios. Los únicos cambios permitidos a pruebas existentes son los literales de versión de la bitácora que describe T081. Si otra prueba existente se rompe, detente y dímelo en vez de modificarla.
5. El comentario de «ir a» se escribe después de que el motor acepte el primer paso y antes de la línea de ese paso (T085); un rechazo no deja línea.
6. Sin dict/set como índice, sin heapq/bisect/collections, sin sorted() como sustituto de un ordenamiento evaluado, determinismo, el modelo no instancia la vista.
7. No cambies FormatoBinario.py, ArchivoPartida.py ni ConversorPartida.py. No hagas commit. Al terminar dime: archivos cambiados, tareas marcadas, y el resultado de la suite.
````

## 2026-11-10 10:26 · Actualizar dos aserciones de pruebas existentes por el comentario «# ir a» en la bitácora (FR-030).

- **Fecha**: 2026-11-10 10:26
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Actualizar dos aserciones de pruebas existentes por el comentario «# ir a» en la bitácora (FR-030).

**Prompt**

````text
Opción 1. Actualiza solo esas dos aserciones para que esperen la línea «# ir a 4» antes del primer mover del viaje (FR-030, T085). En test_fr021_fr025_mismo_estado_y_bitacora_que_los_mover_a_mano, la bitácora del viaje debe ser igual a la de los mover a mano con «# ir a 4» insertada antes del primer paso; el estado del motor y los mensajes se siguen comparando exactamente. No cambies nada más de esas dos pruebas ni toques otras. Después vuelve a correr la suite completa, marca T081 a T086, T091 y T093 solo si queda en verde, y dime en el informe que modificaste esas dos pruebas de la Fase 4 y por qué. No hagas commit.
````

## 2026-11-10 10:31 · Tanda 3a de la Fase 5: archivo CRPT 3 con bloque de conocimiento, carga y guardado.

- **Fecha**: 2026-11-10 10:31
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Tanda 3a de la Fase 5: archivo CRPT 3 con bloque de conocimiento, carga y guardado.

**Prompt**

````text
/speckit-implement Implementa solo estas tareas de la Fase 5 de specs/001-niebla-mapa-ir-a/tasks.md: T068, T070, T071, T072, T073, T076, T077, T078, T079 y T080. No hagas T087 a T090, T092, T094 ni T095 a T097 (van en otra tanda). Reglas:
1. Pruebas primero: escribe T068, T070 a T073 y comprueba que fallan por aserción (no solo por importación; usa stubs si hace falta) antes del código. Cada prueba cita el FR que ejercita.
2. Marca una tarea [X] solo después de ver la suite completa en verde (py -m unittest discover -s tests). No marques nada antes.
3. Formato según contracts/formato-partida.md: CRPT versión 3 en un solo salto, con el orden [encabezado][largo jugador][jugador][largo conocimiento][conocimiento][largo línea de tiempo][línea de tiempo][salas][índice]. La línea de tiempo es de Persona D y es un bloque opaco: por ahora escribe y salta su largo con valor 0 y no interpretes su contenido. _inicio_salas y _validar_encabezado suman los dos campos de largo. Una versión 2, un bloque faltante, truncado, con valor inválido o con bytes sobrantes, o una sala del jugador no explorada, se rechaza con VersionIncompatible (código 2) y no deja nada cargado.
4. No cambies el costo de las salidas en el archivo: no se guarda, se toma del esqueleto. La carga sigue siendo perezosa: test_carga_perezosa_solo_lee_la_sala_actual no puede cambiar.
5. No regeneres partida.cripta, partida.cripta.log ni partida.log (T098). Si una prueba existente se rompe porque usa un archivo v2, detente y dímelo en vez de modificarla, salvo ajustes de versión estrictamente necesarios que describas en el informe.
6. Sin dict/set como índice, sin heapq/bisect/collections, sin sorted() como sustituto de un ordenamiento evaluado, complejidad documentada en docstrings, determinismo, el modelo no instancia la vista.
7. No toques Bitacora/, main.py ni nada de la bitácora. No hagas commit. Al terminar dime: archivos cambiados, tareas marcadas, el resultado de la suite y qué pruebas existentes tuviste que tocar, si alguna.
````

## 2026-11-10 10:48 · Corrección del hueco de puertas reales (cerradas en el esqueleto), T077/T071.

- **Fecha**: 2026-11-10 10:48
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Corrección del hueco de puertas reales (cerradas en el esqueleto), T077/T071.

**Prompt**

````text
/speckit-implement Corrige el hueco de puertas reales (T077/T071), sin tocar el formato binario.

Regla nueva en Persistencia/ConversorPartida.py (_puerta_puede_diferir): una puerta entra en la tabla de puertas reales si hoy está cerrada, O estaba cerrada en el esqueleto, O tiene llave, O tiene cierre automático. El formato en bytes (<I sala, dirección, <B 0|1) no cambia; el valor guardado sigue siendo el estado actual.

Pasos:
1. Prueba primero: en tests/test_persistencia_conocimiento.py, agrega una prueba H2 con mapa(cerrada=True) de tests/test_conocimiento.py (puerta cerrada sin llave ni cierre automático): abrirla, pasar a otra sala, guardar y cargar; la puerta sigue abierta en memoria sin leer el bloque de la sala origen. Debe fallar con la regla actual.
2. Implementa el cambio y verifica que la prueba pase y la suite siga en verde.
3. Actualiza el texto de specs/001-niebla-mapa-ir-a/contracts/formato-partida.md (y data-model.md si menciona la regla) con la regla nueva.
4. No hagas commit. Informa los archivos tocados y el resultado de la suite.
````

## 2026-11-10 10:56 · Actualizar T077 en tasks.md y prueba de doble ida y vuelta.

- **Fecha**: 2026-11-10 10:56
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Actualizar T077 en tasks.md y prueba de doble ida y vuelta.

**Prompt**

````text
/speckit-implement Dos cosas más, sin commit.

1. Actualiza la línea de T077 en specs/001-niebla-mapa-ir-a/tasks.md con la regla nueva de puertas reales (cerrada hoy, o cerrada en el esqueleto, o con llave, o con cierre automático).

2. Prueba de doble ida y vuelta en TestPuertasReales: con mapa(cerrada=True), abrir 1→2, pasar a 2, guardar, cargar, visitar la sala 1 (para que se lea su bloque), guardar otra vez, cargar otra vez; la puerta 1→2 sigue abierta y el archivo del segundo guardado contiene la puerta en la tabla. Si falla porque restaurar_sala reconstruye la Salida sin cerrada_en_esqueleto, corrige restaurar_sala para que conserve el valor del esqueleto (no el del archivo).

Informa archivos tocados y la suite.
````

## 2026-11-10 11:05 · Tanda 3b de la Fase 5: @cargar en la bitácora, replay con recarga y sin vista.

- **Fecha**: 2026-11-10 11:05
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Tanda 3b de la Fase 5: @cargar en la bitácora, replay con recarga y sin vista.

**Prompt**

````text
/speckit-implement Tanda 3b de la Fase 5: T087, T088, T089, T090, T092, T094, T095, T096, T097, en este orden de dependencias: T092 y T093 → T094 → T096 → T097.

Lee antes tasks.md (texto exacto de cada tarea), contracts/formato-bitacora.md y la constitución (MVC: --replay y --bench NO instancian la vista; determinismo; estructuras propias; spec antes que código).

Reglas específicas:
- T092: Controlador escribe `@cargar` con marcar_carga al cargar una partida. Verifica que las pruebas de bitácora siguen en verde.
- T094: Reproductor.recargar(motor) con ejecutar_replay(ruta, gestor) sin vista. En el replay la recarga NO ejecuta --verificar. En Windows hay que cerrar el archivo temporal antes de reemplazarlo o borrarlo.
- T096: main.py con --replay y --bench sin vista. Al terminar avísame para notificar a B.
- Prueba primero en todas las que tengan prueba; el mensaje de fallo debe ser por aserción, no por import.
- No toques contratos compartidos; si algo exige cambiarlos, detente y dímelo.
- No hagas commit. Informa tareas marcadas, archivos tocados, pruebas existentes modificadas (debe ser lo mínimo) y la suite.
````

## 2026-11-11 18:40 · Ajustes pedidos por Persona D, paso 1 (documentos): tres largos del formato y rechazo de --bitacora igual al guardado.

- **Fecha**: 2026-11-11 18:40
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Ajustes pedidos por Persona D, paso 1 (documentos): tres largos del formato y rechazo de --bitacora igual al guardado.

**Prompt**

````text
/speckit-implement Dos ajustes pedidos por Persona D (spec 001). Hazlo en DOS pasos y detente tras el paso 1.

PASO 1 (solo documentos, sin código):
a) contracts/formato-partida.md: la línea 26 dice «dos campos de largo»; debe decir tres (jugador, conocimiento, línea de tiempo). Agrega la fórmula final de D: _inicio_salas = TAMANO_ENCABEZADO + (4 + largo_jugador) + (4 + largo_conocimiento) + (4 + largo_linea); _validar_encabezado exige offset_indice >= TAMANO_ENCABEZADO + 12; se leen tres largos de 4 bytes sin leer los bloques.
b) Regla nueva (pedido de D, FR-030 de su spec 004): usar --bitacora igual a <guardado>.log es un error de uso, con código 1 y mensaje «! Error: ...», antes de jugar. Es decir: (i) al cargar una partida, si la bitácora activa es la misma que ruta_bitacora_de(archivo cargado); (ii) al guardar, si la bitácora activa es la misma que ruta_bitacora_de(destino). Escríbela en spec.md (FR-017 o el caso límite de T090), en contracts/comandos.md y en contracts/formato-bitacora.md donde corresponda, y agrega las tareas nuevas al final de la Fase 5 en tasks.md (prueba primero, luego implementación), con la siguiente numeración libre.
c) Informa los archivos tocados. No hagas commit.

PASO 2 (solo cuando yo escriba «sigue»): implementa las tareas nuevas. Cambia la prueba de T090 que hoy toma como caso seguro «guardar y cargar con la misma bitácora» para que ahora compruebe el rechazo. Verifica también que _validar_encabezado exige offset_indice >= TAMANO_ENCABEZADO + 12 y que _inicio_salas coincide con la fórmula; si no, corrígelo con prueba. Suite en verde. Sin commit.
````

## 2026-11-11 18:45 · Mismos ajustes de Persona D, paso 2 (código): T120–T122.

- **Fecha**: 2026-11-11 18:45
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Mismos ajustes de Persona D, paso 2 (código): T120–T122.

**Prompt**

````text
sigue. Confirmo el caso (ii): guardar se rechaza con `! Error: ...`, sin escribir nada, y la partida continúa. El código 1 aplica solo al cargar.

Implementa T120, T121 y T122 (prueba primero, y comprueba que fallan por aserción antes del código). Una mejora: la comparación de rutas debe usar también os.path.normcase (en Windows X.LOG y x.log son el mismo archivo); agrégalo a _misma_ruta y prueba un caso con mayúsculas. No hagas commit. Informa tareas marcadas, archivos tocados, pruebas existentes modificadas y la suite.
````

## 2026-11-11 19:00 · Observador del Reproductor (pedido de Persona D), paso 1 (documentos).

- **Fecha**: 2026-11-11 19:00
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Observador del Reproductor (pedido de Persona D), paso 1 (documentos).

**Prompt**

````text
/speckit-implement Cambio de Persona D en Bitacora/Reproductor.py, en DOS pasos; detente tras el paso 1.

Lee antes specs/004-linea-de-tiempo/plan.md, sección «Enganches».

PASO 1 (solo documentos): agrega tareas nuevas en tasks.md (Fase 5, con la numeración libre siguiente) y una nota en plan.md o en contracts/formato-bitacora.md sobre la interfaz del Reproductor: parámetro opcional observador=None al final de Reproductor(fabrica_motor, version_cripta, version_catalogo, recargar=None, observador=None); si hay observador, llama a al_crear_motor(motor) tras crear el motor, despues_de_accion(motor, nombre, argumento) tras cada ejecutar_accion que no devolvió False, y despues_de_carga(motor) tras motor = self._recargar(motor) (con el motor nuevo); y una entrada que reproduce una lista (encabezado, acciones) en memoria, de modo que reproducir(ruta) solo lea la bitácora y la llame. Sin observador, el comportamiento es idéntico al actual. Prueba primero, luego implementación. Si el plan de D no fija el nombre de esa entrada, usa reproducir_acciones(encabezado, acciones). No hagas commit.

PASO 2 (cuando yo escriba «sigue»): pruebas primero, que fallen por aserción (con un observador falso que registra el orden de las llamadas, con y sin @cargar), implementación, y suite en verde. Las pruebas existentes de Reproductor no deben cambiar. Sin commit.
````

## 2026-11-11 19:15 · Observador del Reproductor, paso 2 (código): T123–T124.

- **Fecha**: 2026-11-11 19:15
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Observador del Reproductor, paso 2 (código): T123–T124.

**Prompt**

````text
sigue. Implementa T123 y T124: pruebas primero (que fallen por aserción antes del código), luego el código en Bitacora/Reproductor.py. Las pruebas existentes de Reproductor no cambian. Suite en verde. No hagas commit. Informa tareas marcadas, archivos tocados, pruebas existentes modificadas (debe ser ninguna) y la suite.
````

## 2026-11-11 19:43 · Integración de «ir a» con la búsqueda de Persona A, T062–T065 (primera versión; reemplazada por la del 2026-11-12 21:43).

- **Fecha**: 2026-11-11 19:43
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Integración de «ir a» con la búsqueda de Persona A, T062–T065 (primera versión; reemplazada por la del 2026-11-12 21:43).

**Prompt**

````text
/speckit-implement T062, T063, T064 y T065 (integración de «ir a» con la búsqueda de Persona A, que ya está en main).

Lee antes, en este orden: tasks.md (texto exacto de T062 a T065), contracts/interfaz-ruta.md, Modelo/BusquedaRuta.py (firma real de primer_paso y de EspacioBusqueda), Modelo/rutas_ir_a.py y Controlador/ControladorPartida.py (donde hoy `primer_paso` lanza NotImplementedError y se muestra el aviso temporal ««ir a» aún no está disponible.»).

Reglas:
- Una sola EspacioBusqueda por viaje, creada con grafo.cantidad_salas y reutilizada en todos los pasos del viaje. Verifica que GrafoConocido expone cantidad_salas; si no, agrégalo.
- primer_paso no modifica el grafo y es determinista; desempate: menor id de vecino y, si empata, N, S, E, O. La tabla de casos del contrato debe dar el mismo resultado con la búsqueda real (A la corre en tests/test_ruta_contrato.py; no dupliques ni modifiques sus pruebas).
- Quita el aviso temporal «ir a no está disponible» y los saltos de prueba (skip) que dependían de A, si existen.
- Estructuras propias: sin dict/set como índice, sin heapq/bisect/collections/networkx, sin sorted()/list.sort() como sustituto de un ordenamiento evaluado.
- Prueba primero (que fallen por aserción), luego implementación, FR-IDs en los nombres de las pruebas.
- No cambies contratos compartidos ni archivos de A. Si algo exige cambiarlos, detente y avísame.
- No hagas commit. Informa tareas marcadas, archivos tocados, pruebas existentes modificadas (lista cuáles y por qué) y la suite.
````

## 2026-11-12 21:43 · Integración de «ir a» con la búsqueda de Persona A, T062–T065 (versión enviada).

- **Fecha**: 2026-11-12 21:43
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Integración de «ir a» con la búsqueda de Persona A, T062–T065 (versión enviada).

**Prompt**

````text
/speckit-implement T062, T063, T064 y T065 (integración de «ir a» con la búsqueda de Persona A, ya en main).

Lee antes: tasks.md (texto exacto de T062 a T065), contracts/interfaz-ruta.md, Modelo/BusquedaRuta.py (primer_paso(grafo, origen, destino, limite=None, espacio=None) devuelve el Paso o None; EspacioBusqueda(cantidad_salas); precondición destino != origen), Modelo/rutas_ir_a.py y Controlador/ControladorPartida.py.

Haz:
- En rutas_ir_a.py importa arriba: from Modelo.BusquedaRuta import primer_paso as primer_paso_busqueda (no hay import circular: A importa Paso dentro de su función). Tu primer_paso delega en él y deja de lanzar NotImplementedError.
- Una sola EspacioBusqueda(grafo.cantidad_salas) por viaje, creada al empezar el viaje y reutilizada en todos sus pasos.
- Quita el aviso temporal ««ir a» aún no está disponible.» y los skip que dependían de A. En tests/test_ruta_contrato.py quita el skip de TestContratoPrimerPaso y retira TestPrimerPasoPendiente. NO modifiques las clases que A agregó (TestContratoBusquedaRuta, TestLimiteBusquedaRuta).
- Determinismo y desempate como el contrato (menor id de vecino y, si empata, N, S, E, O).
- Estructuras propias: sin dict/set como índice, sin heapq/bisect/collections/networkx, sin sorted()/list.sort() como sustituto de un ordenamiento evaluado.
- Prueba primero (que fallen por aserción), FR-IDs en los nombres. No cambies contratos compartidos ni archivos de A (BusquedaRuta.py, ColaPrioridad.py).
- No hagas commit. Informa tareas marcadas, archivos tocados, pruebas existentes modificadas (con el motivo) y la suite.
````

## 2026-11-13 17:13 · Enmienda PATCH de la constitución: excepción acotada al Principio I para `copy.deepcopy` en CopiaEstado (v3.0.3).

- **Fecha**: 2026-11-13 17:13
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Enmienda PATCH de la constitución: excepción acotada al Principio I para `copy.deepcopy` en CopiaEstado (v3.0.3).

**Prompt**

````text
/speckit-constitution Enmienda PATCH (aclaración de alcance, acordada por el grupo): agrega al Principio I una excepción acotada y documentada.

Texto de la excepción: el único uso de un `dict` permitido por esta excepción es el argumento `memo` de `copy.deepcopy`, un dict temporal de una sola llamada, en `Modelo/CopiaEstado.py` (capacidad 004, línea de tiempo). No autoriza `dict` ni `set` como índice, ni como caché, en ningún otro archivo ni con ningún otro fin; todo lo demás del Principio I sigue igual.

Fundamento: autorización de José Pablo Calvo Suárez (profesor del curso), el 2026-11-12, por chat, como respuesta a la pregunta de Persona D sobre si `copy.deepcopy` con su argumento `memo` chocaba con el Principio I. Cita textual: «Para este proyecto sí pueden usar el dict como caché. No hay problema». Referencia: specs/004-linea-de-tiempo (T003, T114 de esa capacidad, y DECISIONES.md).

Versión: sube de 3.0.2 a 3.0.3 (PATCH) con la fecha 2026-11-13, y actualiza el informe de sincronización si el archivo lo usa. No cambies nada más de la constitución. No hagas commit. Informa qué líneas cambiaste.
````

## 2026-11-13 17:31 · Fase 6, paso previo: solo lectura y reporte de T099–T110 (mediciones M1 a M6).

- **Fecha**: 2026-11-13 17:31
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Fase 6, paso previo: solo lectura y reporte de T099–T110 (mediciones M1 a M6).

**Prompt**

````text
/speckit-implement Fase 6 de specs/001-niebla-mapa-ir-a (T099 a T110, mediciones --bench M1 a M6 y M10). Todavía NO escribas código: primero solo lee y reporta.

Lee tasks.md (Fase 6), plan.md, contracts/comandos.md y el --bench que ya exista en main.py/Controlador, y dime:
1. Qué hace cada tarea T099 a T110 y de cuáles depende (incluye qué existe ya de --bench y de tests/bench_personaC.py).
2. Cómo propones agruparlas en tandas, con tests primero (que fallen por aserción antes del código), IDs FR/PR en los nombres de test y T marcadas en tasks.md al cerrar cada tanda.
3. Para M4: ahora existe EspacioBusqueda de A y un espacio por viaje (buscador_de_viaje en Modelo/rutas_ir_a.py). Cómo medirías "con espacio reutilizado" contra "sin reutilizar" sin tocar archivos de A.
4. El texto de T104 está desactualizado: dime qué dice hoy y qué debería decir.
5. T110/M10 necesita tests/bench_personaC.py: dime si existe, qué cubre, y si D podría reutilizarlo en solo lectura.
6. Cualquier tarea que choque con la constitución 3.0.3 (Principio I: nada de heapq, bisect, collections, networkx, sorted()/list.sort() como sustituto de un ordenamiento evaluado; dict/set no como índice) o con un contrato compartido.

Reglas: no hagas commit, no toques archivos de A, B ni D, no toques .idea/ ni datos_locales/catalogo.json, no edites README.md. Registra este prompt en PROMPTS_LLM.md según el Principio XI.
````

## 2026-11-13 17:35 · Fase 6, tanda 1: T099–T100, generadores sintéticos y base de la medición.

- **Fecha**: 2026-11-13 17:35
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Fase 6, tanda 1: T099–T100, generadores sintéticos y base de la medición.

**Prompt**

````text
/speckit-implement T099 y T100 de specs/001-niebla-mapa-ir-a (Fase 6, tanda 1: generadores sintéticos y base de la medición).

Antes de escribir código, lee tasks.md (T099, T100), plan.md §6.1, y tests/bench_ciclo.py para reusar su estilo.

Orden (tests primero):
1. Escribe pruebas que fallen por aserción (nombre con SC-006 / PR-15) para: los generadores cadena y grilla producen exactamente V = 25, 100, 400, 2500 y salas hasta n = 20000; los costos son variados y simétricos (costo de a hacia b igual al de b hacia a); el grafo es conexo; no se lee ninguna cripta real ni hay red. Y para la medición: la mediana de varias repeticiones es correcta con casos conocidos, y LIMITE_PASO_IR_A_MS existe como una sola constante con valor 5.
2. Verifica que fallan por aserción, no por ImportError.
3. Implementa tests/mapas_sinteticos.py (T099) y la base de tests/bench_niebla.py (T100): mediana de repeticiones, escritura de resultados_bench_niebla.txt con equipo y versión de Python, y una sola constante LIMITE_PASO_IR_A_MS = 5 con comentario que cita §6.1 y dice que el valor puede cambiar por enmienda. Ningún otro archivo escribe ese número.

Restricciones: Principio I de la constitución 3.0.3. La mediana (y luego el p95) NO usan sorted(), list.sort(), statistics ni heapq; usa el ordenamiento propio del repo o escribe uno a mano. Sin dict/set como índice. No toques archivos de A, B ni D, ni .idea/, ni datos_locales/catalogo.json, ni README.md.

Marca T099 y T100 como [X] en tasks.md solo al terminar y con la suite en verde (python -m unittest discover -s tests -t .). No hagas commit. Reporta: archivos nuevos o cambiados, tests añadidos, resultado de la suite, y registra este prompt en PROMPTS_LLM.md.
````

## 2026-11-13 18:00 · Fase 6, tanda 2: T101–T103, mediciones M1, M2 y M3.

- **Fecha**: 2026-11-13 18:00
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Fase 6, tanda 2: T101–T103, mediciones M1, M2 y M3.

**Prompt**

````text
/speckit-implement T101, T102 y T103 de specs/001-niebla-mapa-ir-a (Fase 6, tanda 2: mediciones M1, M2 y M3 en tests/bench_niebla.py).

Lee antes: tasks.md (T101 a T103), plan.md (las alternativas que compara cada medición), el código real de Modelo/ que guarda el conocimiento (estado de sala, recuerdo de puerta, revelar con radio r) y el deshacer con antorcha (FR-014), y lo que ya hay en tests/bench_niebla.py y tests/mapas_sinteticos.py.

Qué se mide (las alternativas "frente a" son líneas base escritas a mano en tests/, no código del juego):
- M1 (FR-001, FR-005): consultar estado de sala y recuerdo de puerta con arreglos densos (lo real), lista ordenada con búsqueda binaria y lista lineal, n = 20, 200, 2000, 20000. Hipótesis: los arreglos no crecen con n.
- M2 (FR-003, FR-009): revelar r fijo con k = 10, 100, 1000, 10000, arreglos frente a lista ordenada. Hipótesis: con arreglos no crece con k.
- M3 (FR-014): registrar y deshacer una entrada con antorcha con lote, cierres por escritura y copia completa, varios r y n. Hipótesis: lote y cierres crecen con r, la copia con n.

Orden (tests primero):
1. Pruebas que fallen por aserción (nombres con FR/PR-15): cada medición devuelve filas con sus parámetros (n, k o r) y el tiempo en ms, para todos los tamaños de la lista; con tamaños mínimos corre sin red ni vista; la búsqueda binaria y la lista lineal de las líneas base dan el mismo resultado que los arreglos (corrección antes de medir); las tres variantes de M3 dejan el mismo estado tras registrar y deshacer. Las pruebas NO afirman tiempos, solo forma y corrección.
2. Verifica que fallan por aserción, no por ImportError (stubs mínimos si hace falta).
3. Implementa las tres mediciones reusando medir_ms y escribir_resultados de T100. Cada fila dice qué hipótesis se contrasta y, si no se pudo medir algo, lo marca como hipótesis no medida; no inventes conclusiones.

Restricciones: Principio I (constitución 3.0.3): la búsqueda binaria de la línea base va escrita a mano, sin bisect; nada de sorted(), list.sort(), heapq, collections ni statistics; dict/set no como índice. Si alguna medición inicia una partida con nueva_partida o crear_paquete_niebla, usa forzar=True con un comentario (spec 002; los mapas sintéticos no son resolubles) y no cambies utiles_niebla.py. No toques archivos de A, B ni D, ni .idea/, ni datos_locales/catalogo.json, ni README.md.

Marca T101 a T103 como [X] en tasks.md solo al terminar y con la suite en verde (python -m unittest discover -s tests -t .). No hagas commit. Reporta: archivos cambiados, tests añadidos, resultado de la suite y las filas de ejemplo que imprime cada medición con tamaños mínimos. Registra este prompt en PROMPTS_LLM.md.
````

## 2026-11-13 18:14 · Fase 6, tanda 3: T104–T106, mediciones M4, M5 y M6 (se reenvió igual el 2026-11-16 16:06).

- **Fecha**: 2026-11-13 18:14
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Fase 6, tanda 3: T104–T106, mediciones M4, M5 y M6 (se reenvió igual el 2026-11-16 16:06).

**Prompt**

````text
/speckit-implement T104, T105 y T106 de specs/001-niebla-mapa-ir-a (Fase 6, tanda 3: mediciones M4, M5 y M6 en tests/bench_niebla.py).

Lee antes: tasks.md (T104 a T106 y T109, para saber qué deja pendiente), research R9 y plan.md §6.1 y §5.2, tests/bench_ciclo.py, Modelo/rutas_ir_a.py (primer_paso y buscador_de_viaje), Modelo/BusquedaRuta.py de A (EspacioBusqueda), el bloque de conocimiento de Persistencia (registro_conocimiento_desde_motor, leer_conocimiento, ExportadorJSON), y lo ya hecho en tests/bench_niebla.py (M1 a M3, medir_ms, mediana, Fila).

Qué se mide:
- M4 (FR-024, FR-026, SC-007): un paso y un viaje completo POR la interfaz primer_paso real, con grilla y cadena de tests/mapas_sinteticos.py (V = 25, 100, 400, 2500). Compara contra LIMITE_PASO_IR_A_MS e informa cumple o no cumple, siempre marcado como PROVISIONAL (mapa sintético, no la cripta de referencia; §6.1 no se da por cumplido hasta T110). No midas el buscador de prueba. Deja la función con un parámetro opcional `espacio` para que T109 pueda medir con y sin un EspacioBusqueda reutilizado; en esta tanda NO hagas T109.
- M5 (FR-015): tamaño y tiempo del bloque de conocimiento y bytes leídos al cargar, k = 20, 200, 2000, binario frente a JSON, con las funciones reales de Persistencia.
- M6 (FR-014, SC-006): ciclo completo con y sin conocimiento, 10 a 500 enemigos, con p95, reusando tests/bench_ciclo.py. Hipótesis: sin regresión frente a 20 ms (§5.2). El p95 se calcula con el merge_sort del repo.

Además, corrige en tasks.md el texto de T104: A ya subió Modelo/BusquedaRuta.py y primer_paso ya tiene cuerpo, así que reescribe «Si primer_paso no tiene cuerpo, informa pendiente BusquedaRuta.py» como la regla vigente (se mide primer_paso real y nunca el buscador de prueba), sin cambiar su alcance. No toques el resto de las tareas ni los marcadores de T109 y T110.

Orden (tests primero), igual que en la tanda 2: pruebas que fallan por aserción (nombres con FR/SC/PR-15) que solo comprueben forma y corrección, sin afirmar tiempos: filas por cada tamaño y variante con ms e hipótesis, M4 con la marca de provisional y el veredicto cumple/no cumple comparado con la constante, M5 con binario y JSON dando la misma información, M6 con y sin conocimiento sobre el mismo ciclo, todo sin red ni vista. Luego stubs mínimos, verificar que fallan por aserción, e implementar.

Restricciones: Principio I (constitución 3.0.3): nada de sorted(), list.sort(), heapq, bisect, collections ni statistics; dict/set no como índice. Si inicias una partida con nueva_partida o crear_paquete_niebla, usa forzar=True con comentario y no cambies utiles_niebla.py. No toques archivos de A, B ni D (solo lees BusquedaRuta.py), ni .idea/, ni datos_locales/catalogo.json, ni README.md. No marques T109.

Marca T104 a T106 como [X] solo al terminar y con la suite en verde (python -m unittest discover -s tests -t .). No hagas commit. Reporta: archivos cambiados, tests añadidos, resultado de la suite, las filas de ejemplo con tamaños mínimos, y cualquier dato raro de las mediciones sin sacar conclusiones. Registra este prompt en PROMPTS_LLM.md.
````

## 2026-11-16 16:16 · Fase 6, tanda 4: T107–T109, cablear la medición a `--bench`, prueba rápida y resultado provisional de M4.

- **Fecha**: 2026-11-16 16:16
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Fase 6, tanda 4: T107–T109, cablear la medición a `--bench`, prueba rápida y resultado provisional de M4.

**Prompt**

````text
/speckit-implement T107, T108 y T109 de specs/001-niebla-mapa-ir-a (Fase 6, tanda 4: cablear la medición a --bench, prueba rápida y resultado provisional de M4).

Lee antes: tasks.md (T107 a T110), contracts/comandos.md (la sección de --bench), main.py (la rama --bench tal como está HOY en main: otras personas lo han tocado, así que no la reescribas, solo agrega la llamada), tests/bench_niebla.py (correr_bench, medir_m1 a medir_m6) y tests/test_bench_niebla.py.

Qué hacer:
- T107: que `--bench` llame a correr_bench de tests/bench_niebla.py, sin red y sin vista, y deje las demás mediciones que ya tiene como están. Comprueba cómo se llaman hoy las otras (bench_motor, bench_personaB, bench_personaC) y sigue la misma convención. No cambies el contrato de las demás opciones.
- T108: prueba rápida en tests/test_bench_niebla.py con tamaños mínimos: M1 a M6 corren sin red y sin VistaConsola, y M4 compara contra LIMITE_PASO_IR_A_MS, sin afirmar tiempos. Para eso correr_bench debe poder recibir tamaños mínimos (parámetro opcional, sin cambiar el comportamiento por omisión).
- T109: corre M4 con la primer_paso real, con y sin un EspacioBusqueda reutilizado por viaje (parámetro `espacio` de medir_m4) y guarda el resultado en resultados_bench_niebla.txt marcado como PROVISIONAL, con equipo y versión de Python. Antes de escribir el archivo en la raíz, mira cómo manejan los otros archivos de resultados (si están en .gitignore o se suben) y sigue la misma convención. Corrige además el texto de T109 en tasks.md: ya no está bloqueada (A subió Modelo/BusquedaRuta.py) y quita lo de «el jueves 12», sin cambiar su alcance ni tocar T110.

Si M4 da «no cumple» en alguna fila: NO cambies BusquedaRuta.py ni nada de A; solo repórtalo con los números (topología, V, ms por paso, con y sin espacio reutilizado) y el veredicto, para decidirlo con el grupo. Tampoco des §6.1 por cumplido: eso es T110.

Orden (tests primero) igual que las tandas anteriores: T108 primero, fallando por aserción antes del cableado.

Restricciones: Principio I (constitución 3.0.3): nada de sorted(), list.sort(), heapq, bisect, collections ni statistics; dict/set no como índice. No toques archivos de A, B ni D, ni .idea/, ni datos_locales/catalogo.json, ni README.md. No marques T110.

Marca T107 a T109 como [X] solo al terminar y con la suite en verde (python -m unittest discover -s tests -t .). No hagas commit. Reporta: archivos cambiados, tests añadidos, resultado de la suite, cuánto tarda `python main.py --bench` completo, las filas de M4 con y sin espacio reutilizado, y cualquier dato raro sin sacar conclusiones. Registra este prompt en PROMPTS_LLM.md.
````

## 2026-11-16 16:38 · Investigación de solo lectura sobre M4 (grilla de 2500 salas no cumple 5 ms) y la tabla §6.1 (primera versión; reemplazada por la de 16:45).

- **Fecha**: 2026-11-16 16:38
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Investigación de solo lectura sobre M4 (grilla de 2500 salas no cumple 5 ms) y la tabla §6.1 (primera versión; reemplazada por la de 16:45).

**Prompt**

````text
Investigación solo de lectura, SIN cambiar ningún archivo del repositorio (ni tests, ni specs, ni PROMPTS_LLM.md salvo registrar este prompt).

Contexto: M4 de tests/bench_niebla.py da «no cumple» en la grilla de 2500 salas: un paso largo de primer_paso tarda unos 12 ms frente al límite de 5 ms (LIMITE_PASO_IR_A_MS), y reutilizar el EspacioBusqueda no lo arregla. Con V = 400 o menos cumple.

Haz esto, usando un script temporal fuera del repositorio (en el scratchpad):
1. Perfila con cProfile un primer_paso sobre la grilla de 2500 (de la primera a la última sala), igual que M4, y dime en qué funciones se va el tiempo (llamadas y tiempo acumulado), sin cambiar nada.
2. Lee Modelo/BusquedaRuta.py y Modelo/ColaPrioridad.py y dime, citando líneas, si la búsqueda se detiene al sacar el destino de la cola o sigue explorando, y si hay trabajo repetido o reinicios del espacio que se puedan evitar.
3. Propón como máximo dos cambios pequeños que reduzcan el tiempo SIN alterar el resultado (mismo primer paso, mismos empates: id de vecino menor, luego N, S, E, O), con una estimación de cuánto ganarían. No los apliques.
4. Dime qué pruebas existentes protegen los empates, para saber si un cambio se puede validar rápido.

Reglas: Principio I (nada de heapq, bisect, collections ni sorted() como sustituto). No toques Modelo/BusquedaRuta.py ni nada de A. Reporta hallazgos y propuestas, nada más.
````

## 2026-11-16 16:45 · Investigación de solo lectura sobre M4 (grilla de 2500 salas no cumple 5 ms) y la tabla §6.1 (versión enviada).

- **Fecha**: 2026-11-16 16:45
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Investigación de solo lectura sobre M4 (grilla de 2500 salas no cumple 5 ms) y la tabla §6.1 (versión enviada).

**Prompt**

````text
Investigación solo de lectura, SIN cambiar ningún archivo del repositorio (ni tests, ni specs, ni PROMPTS_LLM.md salvo registrar este prompt).

Contexto: M4 de tests/bench_niebla.py da «no cumple» en la grilla de 2500 salas: un paso largo de primer_paso tarda unos 12 ms frente al límite de 5 ms (LIMITE_PASO_IR_A_MS), y reutilizar el EspacioBusqueda no lo arregla. Con V = 400 o menos cumple. El límite de §6.1 es para la cripta de referencia; la grilla de 2500 es una prueba de estrés, pero queremos saber si hay una mejora pequeña y segura.

Haz esto, usando un script temporal fuera del repositorio (en el scratchpad):
1. Perfila con cProfile un primer_paso sobre la grilla de 2500 (de la primera a la última sala), igual que M4, y dime en qué funciones se va el tiempo (llamadas y tiempo acumulado), sin cambiar nada.
2. Lee Modelo/BusquedaRuta.py y Modelo/ColaPrioridad.py y dime, citando líneas, si la búsqueda se detiene al sacar el destino de la cola o sigue explorando, y si hay trabajo repetido o reinicios del espacio que se puedan evitar.
3. Propón como máximo dos cambios pequeños que reduzcan el tiempo SIN alterar el resultado (mismo primer paso, mismos empates: id de vecino menor, luego N, S, E, O), con una estimación de cuánto ganarían. No los apliques.
4. Dime qué pruebas existentes protegen los empates, para saber si un cambio se puede validar rápido.

Reglas: Principio I (nada de heapq, bisect, collections ni sorted() como sustituto). No toques Modelo/BusquedaRuta.py ni nada de A. Reporta hallazgos y propuestas, nada más.
````

## 2026-11-16 16:50 · T114, crear DECISIONES.md (primera versión; reemplazada por la de 16:54).

- **Fecha**: 2026-11-16 16:50
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: T114, crear DECISIONES.md (primera versión; reemplazada por la de 16:54).

**Prompt**

````text
/speckit-implement T114 de specs/001-niebla-mapa-ir-a: crear DECISIONES.md (Markdown, UTF-8 sin BOM, finales de línea LF) con las decisiones 1 a 6 del plan.

Lee antes: plan.md (las decisiones 1 a 6 y D-PEND-01), research.md (R1 a R9 y sus alternativas), tasks.md (T114 y T116), resultados_bench_niebla.txt (los datos medidos, que se citan tal cual, sin redondear ni inventar), la constitución .specify/memory/constitution.md (Principio VIII y el Principio I v3.0.3) y la ruta donde la constitución, el plan o tasks.md dicen que va este documento (si no la indican, la raíz del repositorio). Si ya existe un archivo de decisiones en el repositorio, extiéndelo en vez de duplicarlo; si hay un Documento_de_Decisiones*.docx dentro del repo, léelo para reutilizar su texto.

Para cada decisión 1 a 6: qué se decidió, qué alternativas se consideraron, por qué se eligió, y qué dato medido la respalda (con la fila de resultados_bench_niebla.txt que corresponda). Lo que no se midió se marca expresamente como HIPÓTESIS, no como hecho. Incluye la resolución de D-PEND-01 (opción A: búsqueda compartida con el cazador en Modelo/BusquedaRuta.py, de Persona A).

Sección obligatoria sobre «ir a» y §6.1 (datos de la investigación del 2026-11-16 en el equipo de Lucía, mediciones puntuales y ruidosas, a citar como tales):
- M4 sobre mapas sintéticos, por la primer_paso real: cumple el límite de 5 ms con grilla y cadena hasta V = 400; la cadena de 2500 también; en la grilla de 2500 NO cumple (paso largo 12.3 ms, 8.9 ms con espacio reutilizado; promedio por paso del viaje 7.7 ms).
- Diagnóstico (perfil con cProfile, una búsqueda de la sala 1 a la 2500): se expanden 2498 de las 2500 salas porque el destino es la sala más lejana y la búsqueda se detiene al sacar el destino de la cola; GrafoConocido.aristas ocupa cerca del 49 % del tiempo, la cola de prioridad cerca del 28 %.
- Mejoras pequeñas probadas (guardar el destino de cada salida en Conocimiento; leer funciones una vez antes del bucle en BusquedaRuta): dieron el mismo resultado en 2800 casos y ganaron entre 0 % y 9 %, dentro del ruido; no se aplicaron. Bajar de verdad exigiría cambiar el algoritmo (búsqueda bidireccional o A* con estimación de distancia), que se deja como trabajo futuro y es de Persona A.
- La medición con la grilla de 2500 es una prueba de estrés, no el criterio de §6.1, que es con el mapa conocido completo de la cripta de referencia. §6.1 NO se da por cumplido: el veredicto definitivo queda pendiente de T110. El tamaño de las criptas reales se está confirmando con Persona B: no lo afirmes si no está en el plan.
- Reutilizar el EspacioBusqueda por viaje no dio una mejora consistente (en la cadena de 2500 salió algo peor): hipótesis no concluyente.
- M3: el dato de que con n = 200 la copia no pierde frente al lote y con n = 20000 sí, junto con el ruido de r = 18, se presenta como medido con esa salvedad, no como hipótesis confirmada. M5: los bytes leídos al cargar (binario: bloque más 142 bytes; JSON: el archivo entero) son el dato; las diferencias de microsegundos en «guardar» no se interpretan.

Además, corrige en tasks.md el texto de T114: dice «Es un .docx: se edita con Word» y debe decir que es DECISIONES.md en Markdown. NO marques T114 como [X]: es una tarea de revisión del grupo. Corrige también la nota de T119 que dice que «los confirma ella el martes 10» y deja el resto igual.

Restricciones: no toques código, ni archivos de A, B ni D, ni .idea/, ni datos_locales/catalogo.json, ni README.md. No hagas commit. Reporta: la ruta del archivo, la lista de secciones, qué quedó marcado como HIPÓTESIS, y cualquier dato que no hayas podido sustentar con resultados_bench_niebla.txt o con el plan. Registra este prompt en PROMPTS_LLM.md.
````

## 2026-11-16 16:54 · T114, crear DECISIONES.md con las decisiones 1 a 6, la medición M4 y §6.1 (versión enviada).

- **Fecha**: 2026-11-16 16:54
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: T114, crear DECISIONES.md con las decisiones 1 a 6, la medición M4 y §6.1 (versión enviada).

**Prompt**

````text
/speckit-implement T114 de specs/001-niebla-mapa-ir-a: crear DECISIONES.md (Markdown, UTF-8 sin BOM, finales de línea LF) con las decisiones 1 a 6 del plan.

Lee antes: plan.md (las decisiones 1 a 6 y D-PEND-01), research.md (R1 a R9 y sus alternativas), tasks.md (T114 y T116), resultados_bench_niebla.txt (los datos medidos, que se citan tal cual, sin redondear ni inventar), la constitución .specify/memory/constitution.md (Principio VIII y el Principio I v3.0.3) y la ruta donde la constitución, el plan o tasks.md dicen que va este documento (si no la indican, la raíz del repositorio). Si ya existe un archivo de decisiones en el repositorio, extiéndelo en vez de duplicarlo; si hay un Documento_de_Decisiones*.docx dentro del repo, léelo para reutilizar su texto.

Para cada decisión 1 a 6: qué se decidió, qué alternativas se consideraron, por qué se eligió, y qué dato medido la respalda (con la fila de resultados_bench_niebla.txt que corresponda). Lo que no se midió se marca expresamente como HIPÓTESIS, no como hecho. Incluye la resolución de D-PEND-01 (opción A: búsqueda compartida con el cazador en Modelo/BusquedaRuta.py, de Persona A).

Sección obligatoria sobre «ir a» y §6.1 (datos de la investigación del 2026-11-16 en el equipo de Lucía, mediciones puntuales y ruidosas, a citar como tales):
- M4 sobre mapas sintéticos, por la primer_paso real: cumple el límite de 5 ms con grilla y cadena hasta V = 400; la cadena de 2500 también; en la grilla de 2500 NO cumple (paso largo 12.3 ms, 8.9 ms con espacio reutilizado; promedio por paso del viaje 7.7 ms).
- Diagnóstico (perfil con cProfile, una búsqueda de la sala 1 a la 2500): se expanden 2498 de las 2500 salas porque el destino es la sala más lejana y la búsqueda se detiene al sacar el destino de la cola; GrafoConocido.aristas ocupa cerca del 49 % del tiempo, la cola de prioridad cerca del 28 %.
- Mejoras pequeñas probadas (guardar el destino de cada salida en Conocimiento; leer funciones una vez antes del bucle en BusquedaRuta): dieron el mismo resultado en 2800 casos y ganaron entre 0 % y 9 %, dentro del ruido; no se aplicaron. Bajar de verdad exigiría cambiar el algoritmo (búsqueda bidireccional o A* con estimación de distancia), que se deja como trabajo futuro y es de Persona A.
- La medición con la grilla de 2500 es una prueba de estrés, no el criterio de §6.1, que es con el mapa conocido completo de la cripta de referencia. §6.1 NO se da por cumplido: el veredicto definitivo queda pendiente de T110. El tamaño de las criptas reales se está confirmando con Persona B: no lo afirmes si no está en el plan.
- Reutilizar el EspacioBusqueda por viaje no dio una mejora consistente (en la cadena de 2500 salió algo peor): hipótesis no concluyente.
- M3: el dato de que con n = 200 la copia no pierde frente al lote y con n = 20000 sí, junto con el ruido de r = 18, se presenta como medido con esa salvedad, no como hipótesis confirmada. M5: los bytes leídos al cargar (binario: bloque más 142 bytes; JSON: el archivo entero) son el dato; las diferencias de microsegundos en «guardar» no se interpretan.
- Cita textual de §6.1 del enunciado, para la sección: «Los valores pueden ajustarse cuando se publique la cripta de referencia; el ajuste se comunicará como enmienda (§2.7)». El límite de «ir a» es de 5 ms «con el mapa conocido completo de la cripta de referencia». Incluye también una tabla breve con los cuatro límites de §6.1 (ciclo de eventos 20 ms con decenas de cazadores activos; verificación de resolubilidad 200 ms con la cripta publicada más grande; consulta historia 50 ms con una partida de al menos 5000 acciones y K por defecto; paso de «ir a» 5 ms), indicando de cuál de ellos se ocupa esta capacidad (solo el de «ir a») y que M6 mide el ciclo con enemigos genéricos, no con los cazadores de la spec 003, por lo que no sustituye al criterio de los 20 ms de §6.1.

Además, corrige en tasks.md el texto de T114: dice «Es un .docx: se edita con Word» y debe decir que es DECISIONES.md en Markdown. NO marques T114 como [X]: es una tarea de revisión del grupo. Corrige también la nota de T119 que dice que «los confirma ella el martes 10» y deja el resto igual.

Restricciones: no toques código, ni archivos de A, B ni D, ni .idea/, ni datos_locales/catalogo.json, ni README.md. No hagas commit. Reporta: la ruta del archivo, la lista de secciones, qué quedó marcado como HIPÓTESIS, y cualquier dato que no hayas podido sustentar con resultados_bench_niebla.txt o con el plan. Registra este prompt en PROMPTS_LLM.md.
````

## 2026-11-16 17:03 · T115, matriz de trazabilidad (`trazabilidad.md`).

- **Fecha**: 2026-11-16 17:03
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: T115, matriz de trazabilidad (`trazabilidad.md`).

**Prompt**

````text
/speckit-implement T115 de specs/001-niebla-mapa-ir-a: crear la matriz de trazabilidad en specs/001-niebla-mapa-ir-a/trazabilidad.md (Markdown, UTF-8 sin BOM, finales de línea LF). NO hagas T116 (el recorrido manual del quickstart) en esta tanda.

Lee antes: spec.md (los 31 FR, los 7 SC y los 9 casos de SC-001; cuéntalos tú y confirma las cifras), plan.md (los PR), tasks.md (T115, T116 y el estado de cada tarea), quickstart.md si existe, y los tests/ del repo. La convención del proyecto es que el nombre de cada prueba lleva sus IDs de FR/SC/PR (por ejemplo test_fr024_...), así que localiza las pruebas con búsquedas por esos IDs (Grep) y verifica cada una abriendo el archivo.

Formato (trabaja por etapas: primero el esqueleto con todas las filas, luego rellena):
1. Tabla de FR: una fila por cada FR con columnas FR | PR | tareas | prueba (archivo::nombre de la prueba, o varias) | estado.
2. Tabla de SC: una fila por cada SC con los mismos datos y, si se verifica con una medición, la fila de resultados_bench_niebla.txt.
3. Los 9 casos de SC-001: una fila por caso, con la evidencia que exista hoy (prueba automática) y, si requiere una partida jugada, la evidencia pendiente para T116.
4. Estado, solo uno de: hecho (hay prueba que pasa en la suite actual), bloqueado (con la causa), pendiente (con la causa).

Reglas de contenido:
- Cada prueba citada debe existir de verdad y corresponder al FR; si un FR no tiene prueba, la fila dice «sin prueba» y el estado no es «hecho». No inventes nombres de pruebas ni resultados.
- FR-005 y FR-024 deben indicar que dependen de T010 (capacidad de terreno y costos) para probarse con costos reales; hasta entonces solo se prueban con costos puestos a mano en la salida o con grafos de prueba. Revisa el estado real de T010 en tasks.md y en el código y dilo.
- §6.1 (límite de 5 ms de «ir a») NO se da por cumplido: está provisional con mapas sintéticos hasta T110. Refleja el límite medido de resultados_bench_niebla.txt y marca el SC correspondiente como pendiente de T110, no como hecho.
- Un FR cubierto solo por una prueba que tiene un hueco conocido debe decirlo. Antes se detectó que falta una prueba del enemigo dormido en la sala de inicio (US4-9); comprueba si existe y, si no, regístralo como hueco (no lo implementes).
- Para la evidencia de partidas jugadas (SC-001) el archivo partida.log ya no se versiona (está en .gitignore); indica que la evidencia nueva de T116 irá en un archivo con otro nombre y no lo crees.

Restricciones: no toques código, tests ni archivos de A, B ni D, ni .idea/, ni datos_locales/catalogo.json, ni README.md. No hagas commit. No marques T115 ni T116 en tasks.md todavía. Al terminar, ejecuta la suite completa (python -m unittest discover -s tests -t .) para confirmar que las pruebas citadas pasan, y reporta: cuántos FR/SC/casos hay, cuántos quedaron hecho, bloqueado y pendiente, la lista de FR sin prueba, y cualquier prueba que citaste pero no pudiste verificar. Registra este prompt en PROMPTS_LLM.md.
````

## 2026-11-16 17:10 · Cerrar dos huecos de pruebas detectados en la matriz (FR-020 y FR-028) y marcar T115.

- **Fecha**: 2026-11-16 17:10
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Cerrar dos huecos de pruebas detectados en la matriz (FR-020 y FR-028) y marcar T115.

**Prompt**

````text
/speckit-implement Cerrar dos huecos de pruebas de la capacidad 001 detectados en specs/001-niebla-mapa-ir-a/trazabilidad.md, y marcar T115.

Lee antes: trazabilidad.md (filas FR-020 y FR-028), spec.md (FR-020 y FR-028 y el escenario US4-9), tests/test_viaje.py y tests/utiles_niebla.py (cómo se arman partidas de prueba; recuerda que nueva_partida verifica resolubilidad desde la spec 002 y los mapas de prueba no resolubles usan forzar=True con comentario), la ayuda de Vista/VistaConsola.py y las pruebas de comandos existentes.

Qué hacer (tests primero, con nombres con los IDs de FR/SC/PR de la convención del proyecto):
1. FR-020: una prueba que compruebe que la ayuda de la consola incluye el comando `ir a <sala>` (además de lo que ya comprueba para `mapa`). Sigue el estilo de la prueba existente de la ayuda y ponla junto a ella.
2. FR-028: una prueba con un enemigo DORMIDO en la sala de partida (el escenario US4-9 hoy solo cubre un enemigo activo ahí), que compruebe lo que FR-028 exige para ese caso. Si no está claro qué exige FR-028 para el enemigo dormido, cítame el texto de la spec y no adivines.
Si alguna prueba nueva falla porque el comportamiento del juego no cumple el FR, NO cambies código: déjala fallando solo el tiempo necesario para reportarlo, márcala con unittest.expectedFailure o quítala, y dímelo con la causa. No toques Vista/, Modelo/ ni archivos de A, B ni D.

Después: actualiza en trazabilidad.md las filas FR-020 y FR-028 (prueba nueva y estado: hecho solo si pasa), los totales de la tabla de cifras y la sección de huecos. Si FR-020 sigue sin documentarse en el README, dilo en la nota de la fila pero el estado depende de la prueba, no del README, que se cierra en T112. Marca T115 como [X] en tasks.md (T116 NO).

Restricciones: no toques código de producción, ni .idea/, ni datos_locales/catalogo.json, ni README.md. No hagas commit. Reporta: las dos pruebas con su archivo y nombre, si pasan, la suite completa (python -m unittest discover -s tests -t .) y las cifras nuevas de la matriz. Registra este prompt en PROMPTS_LLM.md.
````

## 2026-11-16 17:18 · T116, recorrido de los escenarios 1 a 8 del quickstart y evidencia en la matriz.

- **Fecha**: 2026-11-16 17:18
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: T116, recorrido de los escenarios 1 a 8 del quickstart y evidencia en la matriz.

**Prompt**

````text
/speckit-implement T116 de specs/001-niebla-mapa-ir-a: recorrer los escenarios 1 a 8 del quickstart, correr la suite completa y anotar el resultado en la matriz.

Lee antes: quickstart.md (los escenarios 1 a 8 con sus pasos y resultados esperados), trazabilidad.md (columna de partida jugada de los 9 casos de SC-001, y las notas T116*), contracts/comandos.md y el README solo para saber cómo se arranca el juego (no lo edites).

Qué hacer:
1. Para cada escenario, ejecútalo de verdad con entradas guionadas por stdin (python main.py con el comando y las opciones que pida el quickstart) sobre una cripta local u offline que no requiera red. Si un escenario necesita red, una cripta que no hay offline o interacción que no se pueda guionar, NO lo simules: márcalo como «requiere prueba manual» y escribe los pasos exactos que Lucía debe seguir y qué debe ver.
2. Cada partida de evidencia se guarda y se registra con nombres propios de evidencia dentro de una carpeta temporal fuera del repositorio; no crees partida.log, partida.cripta ni partida.cripta.log en la raíz (están en .gitignore). Copia al repositorio solo la evidencia final en texto.
3. Crea specs/001-niebla-mapa-ir-a/evidencia_quickstart.md (Markdown, UTF-8 sin BOM, LF) con una sección por escenario: comando exacto, entrada guionada, salida real recortada a lo relevante (sin inventar ni reordenar nada), y veredicto (cumple o no cumple lo que dice el quickstart), citando qué prueba automática lo respalda cuando exista.
4. Corre la suite completa (python -m unittest discover -s tests -t .) y anota el resultado real.
5. Actualiza trazabilidad.md: en la columna o nota de partida jugada de SC-001 y en los SC que llevan T116*, enlaza a la sección correspondiente de evidencia_quickstart.md. No cambies un estado de «hecho» a otro valor sin decirme por qué. §6.1 sigue sin darse por cumplido (T110).

Si algún escenario no se cumple, NO arregles código: reporta el escenario, el paso exacto, lo que esperaba el quickstart y lo que ocurrió. No toques código, tests, specs de otras capacidades ni archivos de A, B ni D, ni .idea/, ni datos_locales/catalogo.json, ni README.md. No hagas commit. NO marques T116 como [X]: lo decidimos después de revisar.

Reporta: cuántos escenarios se corrieron solos, cuáles quedan para prueba manual (con sus pasos), los veredictos, el resultado de la suite y cualquier comportamiento raro. Registra este prompt en PROMPTS_LLM.md.
````

## 2026-11-16 18:11 · Limpieza final de textos de la capacidad 001 (sin cambiar comportamiento).

- **Fecha**: 2026-11-16 18:11
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Limpieza final de textos de la capacidad 001 (sin cambiar comportamiento).

**Prompt**

````text
/speckit-implement Limpieza final de textos de la capacidad 001 (sin cambiar comportamiento).

Haz estas cuatro cosas, tests primero solo donde haya prueba que cubra el texto:
1. En specs/001-niebla-mapa-ir-a/tasks.md: en la tabla de dependencias externas la fila de T062 a T065 y T109 dice que Persona A sube Modelo/ColaPrioridad.py «(miércoles 11)» y Modelo/BusquedaRuta.py «(jueves 12)» con consecuencia «ir a no funciona en el juego real». Esas dos cosas ya se subieron: reescribe la fila como resuelta (A subió ambas y T062 a T065 y T109 están hechas) sin borrar la fila.
2. En tasks.md, el «Punto de control 6» todavía menciona «pendiente BusquedaRuta.py» para M4. Actualízalo a lo real: `python main.py --bench` genera resultados_bench_niebla.txt con M1 a M6 medidas y M4 PROVISIONAL (mapas sintéticos, §6.1 sin veredicto definitivo hasta T110). No marques T110.
3. En main.py: la ayuda/descripción del argumento --bench dice «Ejecuta el benchmark de persistencia». Cámbiala por un texto que diga que ejecuta las mediciones de persistencia, ciclo de eventos, resolubilidad y niebla de guerra / «ir a» (el cuerpo de --bench ya llama a esas cuatro). Cambia SOLO ese texto. Si alguna prueba comprueba la ayuda de main.py, actualízala y ejecútala primero para ver que falla antes del cambio.
4. En Decisiones/DECISIONES.md, sección §5.3 («Ciclo completo con conocimiento (M6)»), agrega una frase: en la corrida de T116 (escenario 8 de specs/001-niebla-mapa-ir-a/evidencia_quickstart.md) el p95 de M6 con 500 enemigos y conocimiento fue 18.8694 ms, frente a 15.7772 ms en la corrida de T109; sigue por debajo de 20 ms, pero el margen es corto y el equipo es ruidoso, así que se presenta como HIPÓTESIS de ruido, no como conclusión. Antes de citar la cifra, verifica que 18.8694 aparece de verdad en evidencia_quickstart.md y que 15.7772 está en resultados_bench_niebla.txt; si alguna no está, no la escribas y dímelo.

Restricciones: no toques otros textos de tasks.md, ni marques tareas, ni toques archivos de A, B ni D, ni .idea/, ni datos_locales/catalogo.json, ni README.md. No hagas commit. Ejecuta la suite completa (python -m unittest discover -s tests -t .) y reporta archivos cambiados con las líneas exactas, y el resultado de la suite. Registra este prompt en PROMPTS_LLM.md.
````

## 2026-11-16 18:15 · Conciliar T002 y T006–T012 con la spec 003 (primera versión; reemplazada por la de 18:24).

- **Fecha**: 2026-11-16 18:15
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Conciliar T002 y T006–T012 con la spec 003 (primera versión; reemplazada por la de 18:24).

**Prompt**

````text
/speckit-implement Conciliar las tareas T002 y T006 a T012 de specs/001-niebla-mapa-ir-a con lo que de hecho hizo la spec 003, y corregir la Decisión 6 y la matriz. NO implementes nada de código.

Lee antes: tasks.md de la 001 (T002, T006 a T012, T118), el texto de FR-005 y FR-024 en spec.md y plan.md (R7, P-02 y cualquier mención de costos simétricos), specs/003-terreno-cazador/spec.md y tasks.md (T019 a T031, FR-001 a FR-007), DTOS/Salida.py, Modelo/MotorSimulacion.py (COSTO_MOVER, costo_salida, mover_jugador y la rama Enemigo de ejecutar_evento), Gestor/PreparadorPartida.py, tests/test_costo_salida.py, tests/test_terreno.py y tests/test_validacion_datos.py. Lee también Decisiones/DECISIONES.md, sección «Decisión 6 — Costo de cada salida (R7)», y trazabilidad.md (filas FR-005, FR-024 y la sección de pendientes).

Hechos ya comprobados que debes verificar en el código (no los des por buenos sin mirarlos): (a) Salida usa COSTO_POR_DEFECTO = 100 como valor por defecto y a_json escribe costo siempre; tu T010 decía None y omitir la clave. (b) La 003 permite costos distintos por sentido (T031): no existe validar_costos_salidas y no debe existir. (c) mover_jugador y los enemigos cobran costo * 100 // velocidad.

Para cada una de T002, T006, T007, T008, T009, T010, T011 y T012, decide con evidencia (archivo, línea y prueba) una de tres cosas: CUBIERTA por la 003 (cita las tareas T0xx y pruebas), CUBIERTA CON OTRO DISEÑO (di en qué difiere), o SUSTITUIDA por una decisión posterior (cita la tarea o el texto que la sustituye). Marca [X] en tasks.md solo las CUBIERTAS (con otro diseño o no) y añade al final de la línea una nota breve «Cubierta por specs/003 T0xx (diseño: ...)». Para las SUSTITUIDAS NO marques [X]: agrega al inicio del texto «[SUSTITUIDA por specs/003 T031: los sentidos pueden declarar costos distintos]» y deja el cuadro vacío. No cambies el resto de las tareas.

Después: (1) Reescribe en Decisiones/DECISIONES.md la Decisión 6 para que diga lo que hay de verdad en el código (default 100 en el DTO, costo siempre serializado, costos dirigidos sin validación de simetría, quién lo decidió: la spec 003), sin inventar nada que no esté en el código o en la 003; conserva la alternativa original (None y omitir) como alternativa considerada y por qué no es la que quedó, si el plan o la 003 lo dicen; si no lo dicen, no inventes el porqué. (2) Actualiza en trazabilidad.md las filas FR-005 y FR-024 con las pruebas reales y el estado que corresponda, y los totales; no cambies a «hecho» ningún FR sin prueba que lo respalde. Si FR-024 en spec.md presupone costos simétricos, dilo y propón (sin editarlo) el texto corregido para spec.md/plan.md en tu reporte.

Restricciones: no toques código ni tests ni archivos de A, B ni D, ni .idea/, ni datos_locales/catalogo.json, ni README.md, ni spec.md/plan.md (solo repórtalos). No hagas commit. Ejecuta la suite completa y reporta: la decisión por tarea con su evidencia, las líneas cambiadas, lo que quedó marcado y lo que no, y las cifras nuevas de la matriz. Registra este prompt en PROMPTS_LLM.md.
````

## 2026-11-16 18:24 · Conciliar T002 y T006–T012 con la spec 003, corregir la Decisión 6 y la matriz, y limpiar T062/T063 (versión enviada).

- **Fecha**: 2026-11-16 18:24
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Conciliar T002 y T006–T012 con la spec 003, corregir la Decisión 6 y la matriz, y limpiar T062/T063 (versión enviada).

**Prompt**

````text
/speckit-implement Conciliar las tareas T002 y T006 a T012 de specs/001-niebla-mapa-ir-a con lo que de hecho hizo la spec 003, y corregir la Decisión 6 y la matriz. NO implementes nada de código.

Lee antes: tasks.md de la 001 (T002, T006 a T012, T118), el texto de FR-005 y FR-024 en spec.md y plan.md (R7, P-02 y cualquier mención de costos simétricos), specs/003-terreno-cazador/spec.md y tasks.md (T019 a T031, FR-001 a FR-007), DTOS/Salida.py, Modelo/MotorSimulacion.py (COSTO_MOVER, costo_salida, mover_jugador y la rama Enemigo de ejecutar_evento), Gestor/PreparadorPartida.py, tests/test_costo_salida.py, tests/test_terreno.py y tests/test_validacion_datos.py. Lee también Decisiones/DECISIONES.md, sección «Decisión 6 — Costo de cada salida (R7)», y trazabilidad.md (filas FR-005, FR-024 y la sección de pendientes).

Hechos ya comprobados que debes verificar en el código (no los des por buenos sin mirarlos): (a) Salida usa COSTO_POR_DEFECTO = 100 como valor por defecto y a_json escribe costo siempre; tu T010 decía None y omitir la clave. (b) La 003 permite costos distintos por sentido (T031): no existe validar_costos_salidas y no debe existir. (c) mover_jugador y los enemigos cobran costo * 100 // velocidad.

Para cada una de T002, T006, T007, T008, T009, T010, T011 y T012, decide con evidencia (archivo, línea y prueba) una de tres cosas: CUBIERTA por la 003 (cita las tareas T0xx y pruebas), CUBIERTA CON OTRO DISEÑO (di en qué difiere), o SUSTITUIDA por una decisión posterior (cita la tarea o el texto que la sustituye). Marca [X] en tasks.md solo las CUBIERTAS (con otro diseño o no) y añade al final de la línea una nota breve «Cubierta por specs/003 T0xx (diseño: ...)». Para las SUSTITUIDAS NO marques [X]: agrega al inicio del texto «[SUSTITUIDA por specs/003 T031: los sentidos pueden declarar costos distintos]» y deja el cuadro vacío. No cambies el resto de las tareas.

Después: (1) Reescribe en Decisiones/DECISIONES.md la Decisión 6 para que diga lo que hay de verdad en el código (default 100 en el DTO, costo siempre serializado, costos dirigidos sin validación de simetría, quién lo decidió: la spec 003), sin inventar nada que no esté en el código o en la 003; conserva la alternativa original (None y omitir) como alternativa considerada y por qué no es la que quedó, si el plan o la 003 lo dicen; si no lo dicen, no inventes el porqué. (2) Actualiza en trazabilidad.md las filas FR-005 y FR-024 con las pruebas reales y el estado que corresponda, y los totales; no cambies a «hecho» ningún FR sin prueba que lo respalde. Si FR-024 en spec.md presupone costos simétricos, dilo y propón (sin editarlo) el texto corregido para spec.md/plan.md en tu reporte.

Limpieza adicional en tasks.md (solo texto): las líneas de T062 y T063 todavía llevan la etiqueta [BLOQUEADA: BusquedaRuta.py] y la de T063 dice que «Persona A sube Modelo/BusquedaRuta.py el jueves 12». A subió ambos archivos y esas tareas están hechas: quita la etiqueta de bloqueo y reescribe esa frase como hecho pasado, sin cambiar el alcance de las tareas ni su marca.

Restricciones: no toques código ni tests ni archivos de A, B ni D, ni .idea/, ni datos_locales/catalogo.json, ni README.md, ni spec.md/plan.md (solo repórtalos). No hagas commit. Ejecuta la suite completa y reporta: la decisión por tarea con su evidencia, las líneas cambiadas, lo que quedó marcado y lo que no, y las cifras nuevas de la matriz. Registra este prompt en PROMPTS_LLM.md.
````

## 2026-11-16 18:43 · Pruebas de caracterización que faltaban de T006, T007 y T009 (costos de salida desde el paquete offline) y «ir a» con costos reales.

- **Fecha**: 2026-11-16 18:43
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Pruebas de caracterización que faltaban de T006, T007 y T009 (costos de salida desde el paquete offline) y «ir a» con costos reales.

**Prompt**

````text
/speckit-implement Escribir las pruebas que faltan de T006, T007 y T009 de specs/001-niebla-mapa-ir-a en tests/test_costo_salida.py. Solo pruebas, sin cambiar código de producción.

Contexto: la spec 003 ya implementó el código (DTOS/Salida.py con COSTO_POR_DEFECTO = 100 y a_json que escribe costo siempre; costo_salida y el cobro costo * 100 // velocidad en MotorSimulacion). Por eso estas pruebas son de caracterización: van a pasar al primer intento y NO se puede fingir que fallaron antes. Dilo así en el reporte y en los nombres/comentarios no pongas «rojo previo». Si alguna falla, no toques el código: repórtalo como hallazgo.

Lee antes: las tareas T006, T007 y T009 en tasks.md de la 001 (texto actual, con la nota de conciliación), tests/test_costo_salida.py, tests/test_validacion_datos.py (T030 de la 003, para no duplicar lo que ya cubre), tests/test_terreno.py, DTOS/Salida.py, Gestor/FuenteDatosOffline.py y la utilidad crear_paquete_offline (tests/utiles_niebla.py o la que use el repo).

Escribir:
1. T006 (lo que falta): costo null (None) lanza ValueError en desde_json; ida y vuelta Salida -> a_json -> desde_json conserva el costo (1, 100, 250). No pruebes «omite la clave si es None»: ya no aplica con el diseño actual.
2. T007 (lo que falta): después de un mover con costo distinto de 100, retroceder deshace el movimiento (posición y reloj vuelven al estado anterior).
3. T009: un paquete offline con una salida de costo declarado (por ejemplo 250) y otra sin costo; el costo llega desde FuenteDatosOffline, sobrevive la caché en disco (guardar_esqueleto/cargar_esqueleto) y mover lo cobra (reloj = costo * 100 // velocidad del jugador); la salida sin costo cobra 100. Un paquete sin ningún costo da el mismo reloj que antes de la capacidad de terreno.
4. Una prueba de «ir a» con costos que vengan de ese mismo paquete: la ruta elegida es la de menor suma de costos aunque tenga más saltos, y el reloj final coincide con la suma. Si ya existe una equivalente en la 001, no la dupliques: dilo.

Nombres de prueba con el ID del FR (test_fr005_..., test_fr024_...). Registra en el reporte qué prueba cubre T006, T007 y T009, y propón (sin editar) la marca para tasks.md y la fila de la matriz; después de revisar el reporte yo marco. No hagas commit. No toques README.md, spec.md, plan.md, archivos de A, B ni D, ni .idea/ ni datos_locales/catalogo.json. Ejecuta la suite completa y reporta el conteo. Registra este prompt en PROMPTS_LLM.md.
````

## 2026-11-16 18:52 · Cerrar FR-005: prueba del mapa con costo del paquete, marcas de T006/T007/T009, matriz y comentarios viejos de pruebas.

- **Fecha**: 2026-11-16 18:52
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Cerrar FR-005: prueba del mapa con costo del paquete, marcas de T006/T007/T009, matriz y comentarios viejos de pruebas.

**Prompt**

````text
/speckit-implement Cerrar FR-005 y hacer las marcas de la conciliación. Una prueba nueva, más edición de texto. No cambies código de producción.

Contexto: FR-005 (spec.md línea 145) pide que, de una sala explorada, el jugador conozca su nombre, sus salidas, el destino y el costo de cada salida, y el estado de cada puerta. Las pruebas de tests/test_costo_salida.py (commit fce2bed) comprueban que el costo llega del paquete offline y que mover lo cobra, pero ninguna comprueba que el MAPA muestre un costo que viene del paquete.

Lee antes: spec.md FR-005, tests/test_mapa.py (test_fr005_costo_distinto_de_100 y cómo arma el mapa), tests/test_costo_salida.py (BasePaquete, mapa_costos, paquete, partida), Vista/VistaConsola.py o el módulo que formatee el mapa, y el comando que muestra el mapa en el controlador.

1. Escribe UNA prueba en tests/test_costo_salida.py (o en tests/test_mapa.py si encaja mejor con su montaje), con nombre test_fr005_el_mapa_muestra_el_costo_que_viene_del_paquete: con un paquete offline (mapa_costos) donde 1 -E-> 2 cuesta 250 y 1 -S-> 3 no declara costo, el jugador está en la sala 1 (explorada) y el mapa que ve por el comando real (la misma vía del controlador, sin llamar a funciones internas) muestra el costo 250 de esa salida y el 100 de la otra, junto con nombre, destino y estado de puerta. Si el formato del mapa no muestra el costo de cada salida, NO cambies el código: repórtalo como hallazgo con el texto exacto que sale. Es una prueba de caracterización: pasa a la primera y no finjas un rojo previo.

2. tasks.md de la 001, solo estas marcas y notas:
   - T006 [X], nota: «Cubierta por specs/003 T030 y tests/test_costo_salida.py::TestSalidaSerializacion (diseño: con 100 por defecto, «omitir la clave si es None» ya no aplica)».
   - T007 [X], nota: «Cubierta por specs/003 T025 y T027, T118 de esta capacidad y tests/test_costo_salida.py::TestRetrocederTrasMoverConCosto».
   - T009 [X], nota: «Pruebas: tests/test_costo_salida.py::TestCostoDesdeElPaquete».
   Si la prueba del paso 1 pasa, agrega a la nota de T009 «y la del mapa, test_fr005_el_mapa_muestra_el_costo_que_viene_del_paquete».

3. trazabilidad.md: FR-024 a «hecho» citando test_fr024_ir_a_elige_la_ruta_de_menor_suma_aunque_tenga_mas_saltos. FR-005 a «hecho» SOLO si la prueba del paso 1 pasa y muestra el costo; cítala junto con test_fr005_el_costo_llega_del_paquete_pasa_por_la_cache_y_mover_lo_cobra. Si no pasa, FR-005 queda pendiente con la causa real. Actualiza T006, T007 y T009 en las filas, la sección «Estado de T010» (ya no hay causa de pendiente por costos) y los totales. Si ambas pasan, FR quedaría 29 hecho y 2 pendientes (FR-016 y FR-030): verifica la cifra contando las filas, no la des por buena.

4. Comentarios viejos «el DTO Salida aún no trae costo (T010)» y parecidos en tests/test_costo_salida.py, tests/test_mapa.py y tests/test_viaje.py: reescríbelos para que digan lo que es cierto hoy (el DTO trae costo con 100 por defecto, spec 003 T030). Solo comentarios; no cambies código ni nombres de pruebas. Muestra antes y después de cada uno.

Restricciones: no toques README.md, spec.md, plan.md, research.md, archivos de A, B ni D, ni .idea/ ni datos_locales/catalogo.json. No hagas commit. Ejecuta la suite completa y reporta el conteo (esperado 819 si agregas una prueba), las líneas cambiadas y las cifras de la matriz. Registra este prompt en PROMPTS_LLM.md.
````

## 2026-11-16 18:57 · Correcciones de texto: asteriscos de tareas ya hechas en la matriz y límites de la Decisión 6.

- **Fecha**: 2026-11-16 18:57
- **Modelo**: Claude Opus 5.5 (Claude Code)
- **Para qué se usó**: Correcciones de texto: asteriscos de tareas ya hechas en la matriz y límites de la Decisión 6.

**Prompt**

````text
/speckit-implement Dos correcciones de texto, sin tocar código ni tests.

1. specs/001-niebla-mapa-ir-a/trazabilidad.md, fila FR-025: en la columna de tareas quita los asteriscos de T002, T007, T009 y T011 (ya están [X] en tasks.md). Antes de editar, busca en TODA la matriz otros asteriscos de tareas que hoy estén [X] en tasks.md (T002, T006 a T012) y corrígelos igual; no toques los de tareas que sigan abiertas (T110, T112 y las demás [ ]). Muestra antes y después de cada fila cambiada y confirma contando que ninguna tarea con * esté [X] en tasks.md ni ninguna sin * esté [ ].

2. Decisiones/DECISIONES.md, Decisión 6, sección «Límites» (línea ~940): reemplaza la viñeta «No hay prueba de que un costo declarado en un paquete offline atraviese la caché en disco… T009… sigue abierta» por lo que es cierto hoy: T009 quedó cubierta por tests/test_costo_salida.py::TestCostoDesdeElPaquete (el costo llega desde FuenteDatosOffline, pasa por la caché en disco y mover lo cobra), el comando mapa lo muestra (test_fr005_el_mapa_muestra_el_costo_que_viene_del_paquete) y «ir a» elige por la suma (test_fr024_ir_a_elige_la_ruta_de_menor_suma_aunque_tenga_mas_saltos); son pruebas de caracterización, escritas después del código de la 003. Revisa también la lista de pruebas de «Evidencia» de esa decisión y agrega esas tres si faltan, y revisa que nada más en la Decisión 6 diga que T006, T007 o T009 siguen abiertas. Deja el límite «el DTO ya no distingue "sin costo propio" de "cuesta 100"» tal cual.

Restricciones: no toques nada más, ni README.md, spec.md, plan.md, research.md, ni archivos de A, B o D, ni .idea/ ni datos_locales/catalogo.json. No hagas commit. Ejecuta la suite completa (esperado 819) y reporta las líneas cambiadas. Registra este prompt en PROMPTS_LLM.md y confirma con Select-String que quedó escrito, porque en la tanda anterior se afirmó sin comprobarlo.
````

## 2026-11-16 22:39 · Corrección H2 de la revisión de Persona D: `--bitacora` igual al propio guardado (paso 1, solo documentos y contratos).

- **Fecha**: 2026-11-16 22:39
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Corrección H2 de la revisión de Persona D: `--bitacora` igual al propio guardado (paso 1, solo documentos y contratos).

**Prompt**

````text
/speckit-implement Corrección H2 de la revisión de Persona D (spec 001). Hazlo en DOS pasos y detente tras el paso 1.

Hallazgo reproducido por D: `python main.py --cargar G --bitacora G` sobrescribe el guardado G con la bitácora (G pasó de 257 a 116 bytes, con la magia CRIP). Hoy `_rechazar_bitacora_del_guardado` solo compara contra `<guardado>.log`; no compara contra la ruta del propio guardado. Es un hueco de las tareas T120 a T122.

Lee antes: tasks.md (T120 a T122), contracts/formato-partida.md y contracts/comandos.md (la regla del rechazo de --bitacora igual al guardado), Controlador/ControladorPartida.py (`_rechazar_bitacora_del_guardado` y quien la llama, en cargar y en guardar), main.py (manejo de --cargar, --guardar y --bitacora) y las pruebas de T120 a T122 con su forma de comparar rutas (os.path.normcase).

PASO 1 (solo documentos, sin código):
a) Corrige la regla en los contratos donde esté escrita (formato-partida.md y comandos.md): es un error de uso, con código 1 y mensaje «! Error: ...», antes de jugar, cuando la ruta de la bitácora es la misma que la del guardado O la misma que <guardado>.log. Aplica al cargar y al guardar. Cargar: código 1 antes de abrir nada para escritura. Guardar: se rechaza con «! Error: ...», no escribe nada y la partida continúa.
b) La comparación debe tomar rutas equivalentes, no solo texto igual: os.path.normcase, os.path.abspath y, si ambos archivos existen, os.path.samefile (en Windows X.LOG y x.log son el mismo archivo; ./g y g también). Dilo así en el contrato.
c) Agrega la tarea nueva en tasks.md (Fase 5, con la siguiente numeración libre) con su «Atiende» (FR-030) y las pruebas que pide el paso 2. No cambies el texto de T120 a T122.
d) Informa los archivos tocados. No hagas commit.

PASO 2 (solo cuando yo escriba «sigue»): pruebas primero, y comprueba que fallan por aserción antes del código:
- Con un guardado real G (formato con la magia CRIP) y la partida cargada con `--bitacora G`: el programa termina con código 1, imprime «! Error: ...» y G queda byte por byte igual que antes (compara contenido y tamaño, no solo que exista). Esta prueba reproduce el caso de D.
- Lo mismo con la ruta escrita distinto (mayúsculas distintas en Windows, `./G`, ruta absoluta frente a relativa).
- En guardar (dentro de la partida) con la bitácora igual a la ruta del guardado: rechazo, no se escribe nada y la partida continúa.
- La prueba de main para el código 1 (por subproceso o llamando a main como hacen las pruebas de T120 a T122, lo que ya use el repo).
- Las pruebas existentes de T120 a T122 no cambian.
Luego el código en ControladorPartida.py y main.py. Suite completa en verde. No cambies H1 (carga atómica): lo hace Persona D en su T085, dentro de cargar. No toques el resto de ControladorPartida.py ni main.py. No hagas commit.

Restricciones: no toques README.md, archivos de A ni B, ni specs/004, ni .idea/ ni datos_locales/catalogo.json. Registra este prompt en PROMPTS_LLM.md y confirma con Select-String que quedó escrito.
````

## 2026-11-16 22:44 · Ajustar la regla de `--bitacora` en spec.md con el mismo texto de los contratos (H2).

- **Fecha**: 2026-11-16 22:44
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Ajustar la regla de `--bitacora` en spec.md con el mismo texto de los contratos (H2).

**Prompt**

````text
Ajusta specs/001-niebla-mapa-ir-a/spec.md línea 132 (y cualquier otra mención de la misma regla en spec.md): la regla es que --bitacora no puede ser ni el propio archivo de guardado ni su copia <guardado>.log, con el mismo texto de los contratos (comandos.md). Cambia solo esa regla; no toques otras líneas ni specs/004. Muestra antes y después. No hagas commit ni empieces el paso 2.
````

## 2026-11-16 22:46 · Orden «sigue»: paso 2 de H2 (pruebas primero y luego el código).

- **Fecha**: 2026-11-16 22:46
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Orden «sigue»: paso 2 de H2 (pruebas primero y luego el código).

**Prompt**

````text
sigue
````

## 2026-11-16 22:56 · Tres ediciones de texto con la respuesta de Persona A (frase de costo por sentido en plan.md y research.md, nota de T010 y confirmación sobre M4 en DECISIONES.md).

- **Fecha**: 2026-11-16 22:56
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Tres ediciones de texto con la respuesta de Persona A (frase de costo por sentido en plan.md y research.md, nota de T010 y confirmación sobre M4 en DECISIONES.md).

**Prompt**

````text
/speckit-implement Tres ediciones de texto con la respuesta de Persona A (2026-11-16). Sin tocar código ni pruebas.

1. specs/001-niebla-mapa-ir-a/plan.md (P-02, hacia la línea 129) y specs/001-niebla-mapa-ir-a/research.md (R7, hacia la línea 348): la frase «… vale 100 si la salida no lo declara y es el mismo en ambos sentidos» se reemplaza por: «… vale 100 si la salida no lo declara; el enunciado §3.1 lo da por igual en ambos sentidos, pero la spec 003 (aclaración del 2026-11-09, FR-003) lo trata como supuesto de los datos y no lo valida: cada actor, y la ruta de «ir a», usan el costo de la salida que se atraviesa. Persona A confirmó el 2026-11-16 que es la decisión definitiva.» Busca la frase exacta en ambos archivos, muestra antes y después, y revisa que no quede otra mención de «el mismo en ambos sentidos» o de validar simetría en plan.md, research.md y spec.md; si hay otra, repórtala sin cambiarla.

2. tasks.md de la 001, nota de T010: debe citar «specs/003 T027 a T031» en lugar de solo «T030». Deja intacto el resto de la nota y de la línea.

3. Decisiones/DECISIONES.md, sección de M4 (el límite de la grilla de 2500): agrega un párrafo corto, claramente atribuido, con la confirmación de Persona A del 2026-11-16: BusquedaRuta ya corta al sacar el destino de la cola (`if ordinal == ordinal_destino: return`), así que no hay ahorro por ahí; el costo de la grilla de 2500 es el de un Dijkstra sin heurística con el destino lejano; un A* lo reduciría pero cambia el algoritmo y obliga a repetir las pruebas de desempate, por eso no entra antes de la entrega y queda como prueba de estrés documentada; el criterio de §6.1 se mide en la cripta de referencia, y según A, si la cripta real tiene 400 salas o menos, está dentro de los 5 ms (nuestras mediciones son con mapas sintéticos y provisionales: dilo). No agregues cifras que no estén en el repo. No cambies el veredicto «no cumple» de la grilla de 2500 ni marques §6.1 como cumplido.

Restricciones: no toques README.md, spec.md, código, pruebas, .idea/ ni datos_locales/catalogo.json, ni archivos de A, B ni D. No hagas commit. Ejecuta la suite completa (esperado 835) y reporta las líneas cambiadas. Registra este prompt en PROMPTS_LLM.md y confirma con Select-String que quedó escrito.
````

## 2026-11-16 22:58 · Dos correcciones de texto más: nota de dominio de tasks.md y fila D-PEND-01 de plan.md en pasado.

- **Fecha**: 2026-11-16 22:58
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Dos correcciones de texto más: nota de dominio de tasks.md y fila D-PEND-01 de plan.md en pasado.

**Prompt**

````text
Dos correcciones de texto más, sin código ni pruebas:
1. specs/001-niebla-mapa-ir-a/tasks.md, líneas ~68-69 (nota de dominio): cambia «es el mismo en ambos sentidos» por «el enunciado §3.1 lo da por igual en ambos sentidos, pero la spec 003 (FR-003) lo trata como supuesto de los datos y no lo valida; cada actor y la ruta de «ir a» usan el costo de la salida que se atraviesa». No cambies nada más de esa nota.
2. specs/001-niebla-mapa-ir-a/plan.md, fila D-PEND-01: reescribe en pasado lo que ya ocurrió: Persona A subió Modelo/ColaPrioridad.py y Modelo/BusquedaRuta.py (quita «Fechas de Persona A» con miércoles 11 y jueves 12), y en la columna «Mientras tanto» di que ya no hay aviso temporal ni NotImplementedError (T062 a T065 hechas). Conserva el resto de la fila (la opción A, la opción B descartada, los parámetros limite=None y espacio=None).
Muestra antes y después de cada una. No hagas commit. Ejecuta la suite (835). Registra este mensaje en PROMPTS_LLM.md y confirma con Select-String.
````

## 2026-11-17 11:23 · Documentar el veneno no jugable como límite conocido (DECISIONES.md, evidencia 4.9 y matriz SC-001).

- **Fecha**: 2026-11-17 11:23
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Documentar el veneno no jugable como límite conocido (DECISIONES.md, evidencia 4.9 y matriz SC-001).

**Prompt**

````text
Documentar un límite conocido, sin tocar código ni pruebas.

Hecho verificado: ningún DTO (DTOS/) trae un dato de veneno; MotorSimulacion.aplicar_veneno (línea ~831) solo se invoca desde pruebas, así que en una partida real el veneno nunca se aplica. Persona A (autora del motor) lo confirmó y votó dejarlo como límite conocido; se reabre solo si B confirma que el API manda ese dato.

1. Decisiones/DECISIONES.md: agrega, en la sección de límites, un apartado «Veneno no jugable (límite conocido)» con: qué pasa, la causa (sin dato en el DTO), qué sí está probado (tests/test_viaje.py::test_fr027c_escenario_us4_6_veneno_activo_desde_antes_de_la_orden aplica el veneno directamente al motor), la condición para reabrirlo y que la decisión es de A, B y el grupo. No inventes motivos que no estén aquí.

2. specs/001-niebla-mapa-ir-a/evidencia_quickstart.md: en la tabla de resumen (línea ~43) y en 4.9 cambia «requiere prueba manual» por «límite conocido (no se puede producir jugando)»; deja los pasos para cuando exista una fuente de veneno.

3. specs/001-niebla-mapa-ir-a/trazabilidad.md: en la fila SC-001 haz el mismo cambio de etiqueta.

Muéstrame git diff --stat. No hagas commit.
````
## 2026-11-17 12:11 · Marcar T112 y T113 como hechas en tasks.md tras verificar el README.

- **Fecha**: 2026-11-17 12:11
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Marcar T112 y T113 como hechas en tasks.md tras verificar el README.

**Prompt**

````text
Solo documentación de specs/001-niebla-mapa-ir-a/tasks.md. No toques el README (está en UTF-16: léelo con Python decodificando utf-16, sin escribirlo), ni código, ni pruebas.

Marca T112 y T113 como hechas solo si lo verificas en README.md:
- T112: documenta `ir a <sala>`, sus rechazos y los motivos de parada (hay una sección «ir a <sala>»). Reescribe en la tarea la frase «Mientras T065 no esté hecha, decir que el comando aún no está disponible», porque T065 ya está hecha y el comando existe.
- T113: documenta CRPT 3 (con `largo línea` y `_inicio_salas`), CRIPTA-LOG 2, comentarios y `@cargar`; la frase «cargar no se anota» ya no aparece como cierta; el ejemplo de bitácora es de CRIPTA-LOG 2. Si falta alguno de estos puntos, NO marques T113 y dime cuál falta.

En cada tarea marcada agrega una nota breve: «Hecho. README: commits 142109b y afe7e1d (2026-11-16 y 2026-11-17)». No cambies el texto «Atiende» ni el resto de la tarea. Muestra antes y después, ejecuta `git diff --stat`. No hagas commit.
````

## 2026-11-17 12:15 · Quitar de la matriz de trazabilidad los asteriscos de T112 y T113.

- **Fecha**: 2026-11-17 12:15
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Quitar de la matriz de trazabilidad los asteriscos de T112 y T113.

**Prompt**

````text
Solo documentación, sin tocar código, pruebas ni README. En specs/001-niebla-mapa-ir-a/trazabilidad.md, T112 y T113 ya están hechas en tasks.md, así que quita su marca de asterisco (`T112\*` y `T113\*`, o como esté escrito) en todas las filas donde aparezcan, y ajusta la nota o leyenda de los asteriscos para que mencione solo las tareas que siguen pendientes (T110). No cambies ninguna otra cosa. Muestra las líneas antes y después con git diff y ejecuta git diff --stat. No hagas commit.
````

## 2026-11-17 12:17 · Actualizar en la matriz las cinco frases que contradecían T112 y T113 (FR-016, FR-017, FR-020, FR-030 y el resumen).

- **Fecha**: 2026-11-17 12:17
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Actualizar en la matriz las cinco frases que contradecían T112 y T113 (FR-016, FR-017, FR-020, FR-030 y el resumen).

**Prompt**

````text
Sí, actualiza las cinco frases y solo esas. Reglas: no inventes evidencia; cita solo lo que verificaste en el README (la línea del formato de CRPT 3 con `largo línea` y `_inicio_salas`, el ejemplo de CRIPTA-LOG 2 con la tabla de comentarios y directivas, el párrafo de @cargar y la sección «ir a <sala>»). 
- FR-016: estado «hecho»; la nota debe decir que el README ya describe el CRPT 3 con el bloque de conocimiento y la fórmula de _inicio_salas.
- FR-017: quita «sigue en T113»; la condición (d) de P-07 (documentar @cargar) quedó cumplida.
- FR-020: quita «todavía no» y «abierta»; el README documenta `mapa` (T111) e `ir a <sala>` (T112).
- FR-030: estado «hecho»; el README ya muestra CRIPTA-LOG 2 y documenta los comentarios.
- Resumen: FR 31 hechos y 0 pendientes; en «Huecos cerrados» quita «El README de ir a sigue en T112» o pásalo a pasado. SC no cambia: SC-007 sigue pendiente de T110.
No toques «Ran 812» de SC-006 (se actualiza al final con el conteo definitivo), ni T110. Muestra antes y después con git diff y git diff --stat. No hagas commit.
````

## 2026-11-17 12:23 · Repetir el escenario 6 del quickstart con el main.py actual, solo comprobación (tras los cambios de la spec 004).

- **Fecha**: 2026-11-17 12:23
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Repetir el escenario 6 del quickstart con el main.py actual, solo comprobación (tras los cambios de la spec 004).

**Prompt**

````text
Solo comprobación: no modifiques ningún archivo del repositorio (ni specs, ni tests, ni README, ni código). Repite el escenario 6 de specs/001-niebla-mapa-ir-a/evidencia_quickstart.md con el main.py actual, que ya incluye el cambio de la spec 004 (cargar con línea de tiempo reproduce el guion y necesita los datos locales).

Trabaja en una carpeta temporal fuera del repo. Recrea el paquete p_puerta como se hizo en T116 (tests/utiles_niebla.py::crear_paquete_niebla) o reutiliza el de T116 si todavía existe. Ejecuta los tres comandos del escenario con las mismas entradas (sesión 1, sesión 2 y replay) y la carga de comprobación de la puerta real (`n`, `mapa`, `salir`).

Compara con lo escrito en la evidencia y dime punto por punto si coincide: reloj 525 y 7 acciones al guardar, mapa idéntico antes de guardar y después de cargar, sala 6 todavía avistada al entrar a 5 (antorcha apagada), `@cargar` en esc6_cont.log, replay con reloj 825, sala 5, vida 40 y 10 acciones, y la puerta E «cerrada» al entrar a 1.

Además prueba cargar ev6.cripta con una carpeta --datos-locales vacía y sin paquete offline (sin red): informa el código de salida y el mensaje exactos.

No edites la evidencia: solo reporta qué coincide, qué cambió y por qué.
````

## 2026-11-17 12:26 · Agregar a la evidencia del escenario 6 la nota de que se repitió el 2026-11-17.

- **Fecha**: 2026-11-17 12:26
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Agregar a la evidencia del escenario 6 la nota de que se repitió el 2026-11-17.

**Prompt**

````text
Solo documentación, sin tocar código, pruebas ni README. En specs/001-niebla-mapa-ir-a/evidencia_quickstart.md, al final del escenario 6 (justo antes de «Respaldo automático:»), agrega esta nota: «Repetido el 2026-11-17 con el main.py posterior a los cambios de la spec 004 (cargar con línea de tiempo): mismo resultado en todos los puntos, con el paquete offline presente.» No cambies nada más. Muestra el diff y git diff --stat. No hagas commit.
````
## 2026-11-17 14:30 · Investigar, solo lectura, cómo agregar a M4 el mapa conocido completo de la cripta publicada más grande (preparar T110).

- **Fecha**: 2026-11-17 14:30
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Investigar, solo lectura, cómo agregar a M4 el mapa conocido completo de la cripta publicada más grande (preparar T110).

**Prompt**

````text
Solo lectura, no modifiques nada. Necesito preparar T110 (specs/001-niebla-mapa-ir-a/tasks.md): agregar a la medición M4 de --bench el mapa conocido completo de la cripta publicada más grande, que según Persona B es cripta-02 con 20 salas (las otras son cripta-01 con 6 y cripta-test con 5). Averigua y respóndeme:
1. Dónde están las copias locales de los esqueletos de esas tres criptas (¿datos_locales/? ¿algún paquete offline en tests o en el repo?) y cómo se leen con el código existente (FuenteDatosOffline, caché, etc.).
2. Cómo arma tests/bench_niebla.py los mapas de M4 y el conocimiento, y cuál es la forma más pequeña de construir el mapa conocido COMPLETO (todas las salas exploradas) a partir del esqueleto real de cripta-02 sin copiar datos de la cripta al código (constitución: ningún dato de una cripta concreta en el código; el bench debe leerlo de las copias al correr, y omitir la fila con un aviso si las copias no están).
3. Qué constante y qué función de bench dan el veredicto contra los 5 ms de §6.1, y cómo se marca hoy el resultado como «provisional».
4. Cuántos enemigos y cazadores tiene cripta-02 (solo para documentarlo; no afecta el cálculo de un paso de «ir a»).
No hagas commit. Responde con rutas y nombres de funciones concretos, sin proponer todavía el cambio.
````

## 2026-11-17 14:43 · Implementar la medición de T110: M4 con el mapa conocido completo de la cripta de referencia (cripta-02).

- **Fecha**: 2026-11-17 14:43
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Implementar la medición de T110: M4 con el mapa conocido completo de la cripta de referencia (cripta-02).

**Prompt**

````text
/speckit-implement Implementa solo la parte de medición de T110 (specs/001-niebla-mapa-ir-a/tasks.md): agregar a la medición M4 de --bench el mapa conocido completo de la cripta publicada más grande (cripta-02, 20 salas), tomado del esqueleto REAL. No edites tasks.md, DECISIONES.md, trazabilidad.md ni el README en este paso; solo código de bench y sus pruebas. No hagas commit.

Reglas:
1. Pruebas primero, en tests/test_bench_niebla.py: escríbelas y comprueba que fallan por aserción antes del código. Citan SC-007 y PR-15. No afirmes tiempos concretos (solo forma, corrección y comparación contra la constante). Casos: (a) con datos_locales/esqueleto_cripta-02.json presente, M4 produce una fila de la cripta real con su veredicto comparado con LIMITE_PASO_IR_A_MS; (b) si falta el esqueleto, la fila sale como «no medido … Motivo: …» y no falla; (c) el código del bench no contiene ningún dato de cripta (ids de sala, nombres ni números de cripta-02 escritos en el código): se lee del archivo al correr; (d) el bench SOLO LEE de datos_locales, no escribe nada ahí (comprueba que catalogo.json y los esqueletos quedan byte por byte iguales).
2. Lectura: usa AlmacenamientoLocalApi.cargar_esqueleto o SalaEsqueleto.desde_json (lo que ya exista; no inventes otro formato) sobre datos_locales/esqueleto_cripta-02.json, pasando la versión que traiga el propio archivo. Construye los objetos con la forma que necesitan Conocimiento y GrafoConocido; el destino_de resuelve sala_destino (id) a la sala por id sin dict ni set como índice (constitución: estructuras propias).
3. Mapa conocido completo: entra a todas las salas sin antorcha (como preparar_m4), de modo que las dos puertas cerradas con llave quedan recordadas cerradas y no entran al grafo. Documenta en el docstring que el grafo es dirigido y que no todas las salas son alcanzables.
4. Medición: el peor caso entre todos los pares (origen, destino) alcanzables, con el mismo método de medición que ya usa M4 para un paso; la fila reporta el máximo en ms, el par que lo produce y cuántos pares alcanzables se midieron. Veredicto con veredicto_paso (LIMITE_PASO_IR_A_MS, la única constante).
5. Marcas: las filas sintéticas siguen siendo provisionales. La fila de cripta-02 NO se marca provisional, pero su nota debe decir exactamente: «cripta publicada más grande (cripta-02, 20 salas), usada como cripta de referencia; el enunciado no la identifica con certeza». Ajusta encabezado(), el título de sección y NOTA_PROVISIONAL_M4 para que no digan que «§6.1 no se da por cumplido hasta T110» sino lo que corresponda ahora (las filas sintéticas son pruebas de estrés; la fila real es la medición de §6.1). Revisa tests/test_bench_niebla.py (D cambió 5 líneas de ese archivo hace poco) y no rompas sus pruebas.
6. Ejecuta SOLO el bench de niebla (no el --bench completo) para regenerar resultados_bench_niebla.txt y reporta el resultado de la fila de cripta-02. Después ejecuta la suite completa y reporta el conteo. Verifica con git status que datos_locales/ no cambió y que solo cambiaron archivos de tests/ y resultados_bench_niebla.txt.
7. Restricciones: no toques archivos de A, B ni D, ni .idea/, ni datos_locales/. Registra este prompt en PROMPTS_LLM.md y confirma con Select-String que quedó escrito.
````

## 2026-11-17 15:11 · Dos arreglos de T110: orden de las filas de M4 y pruebas del bench sin datos_locales.

- **Fecha**: 2026-11-17 15:11
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Dos arreglos de T110: orden de las filas de M4 y pruebas del bench sin datos_locales.

**Prompt**

````text
/speckit-implement Dos arreglos de T110, solo en tests/ (y resultados_bench_niebla.txt al regenerar). No hagas commit. No toques tasks.md, DECISIONES.md, trazabilidad.md, README, datos_locales/ ni archivos de A, B o D.

PARTE 1: el orden de M4 altera las filas sintéticas.
Medición: en el último commit (sin T110) la cadena de 2500 con espacio reutilizado da ≈2,8 ms por paso (paso suelto 2,87; viaje 6928 ms / 2499 pasos). Con T110 da 4,4 a 5,0 ms por paso en el viaje y 5,7 a 7,9 ms en el paso suelto, en tres corridas distintas. Lo único que cambió antes de esas filas es que ahora se mide la fila de la cripta de referencia entre los bloques «por llamada» y «reutilizado». Hipótesis: el orden afecta a las filas que vienen después.
1. Prueba primero (debe fallar por aserción): en correr_bench, las dos filas «referencia/paso» van DESPUÉS de todas las filas sintéticas de M4, es decir, el orden es sintéticas por llamada, sintéticas reutilizado, referencia por llamada, referencia reutilizado. Verifica que fallan antes del cambio.
2. Cambia el orden en correr_bench (solo eso).
3. Cierra todo lo demás que consuma CPU si puedes. Corre SOLO python -m tests.bench_niebla y reporta estas filas, con el valor de HEAD entre paréntesis: cadena/paso y cadena/viaje con V=2500 por llamada y reutilizado (HEAD: 2,46 / 6793 y 2,87 / 6928), y grilla/paso V=2500 por llamada y reutilizado (HEAD: 8,0 y 8,4). Corre el bench DOS veces y reporta las dos.
4. Si tras reordenar la cadena de 2500 reutilizada sigue por encima de ≈4 ms por paso, no cambies más: investiga SOLO LEYENDO (por ejemplo, si EspacioBusqueda o medir_ms guardan estado compartido entre filas, o si hay recolección de basura de por medio) y reporta lo que encuentres sin modificar archivos de A.

PARTE 2: robustez sin datos_locales.
Sin datos_locales/ (copia limpia sin esa carpeta) fallan 3 pruebas de tests/test_bench_niebla.py: test_sc007_pr15_t108_m4_con_y_sin_espacio_compara_contra_la_constante (TypeError al dividir fila.ms, que es None en la fila «no medido») y test_sc006_pr15_t108_m1_a_m6_con_tamanos_minimos_sin_red_ni_vista (falla en M4 porque exige ms en todas las filas). El bench se comporta bien; las pruebas genéricas suponen que la carpeta existe.
1. Prueba primero: haz que _correr_minimo acepte datos_locales y que las dos pruebas genéricas corran con subTest (a) con la carpeta real si existe y (b) SIEMPRE con una carpeta temporal vacía. Confirma que (b) falla antes de corregir las expectativas.
2. Corrección: en (b), las filas «referencia/paso» son una por modo de espacio, con ms None, veredicto "", provisional False, texto con «no medido» y «Motivo:», sin dividir. Las filas medidas conservan las comprobaciones actuales. El conteo de 10 filas de M4 vale en los dos casos.
3. Verificación en copia limpia: robocopy . ..\copia_sin_datos /E /XD datos_locales .git .idea __pycache__ /NFL /NDL /NJH /NJS, corre python -m unittest tests.test_bench_niebla en esa copia (debe dar OK) y bórrala. Luego la suite completa en el proyecto con el conteo, y git status: solo tests/test_bench_niebla.py, tests/bench_niebla.py y resultados_bench_niebla.txt deben haber cambiado.

PARTE 3: registro. Agrega este prompt a PROMPTS_LLM.md con la hora real de envío, sin tocar las entradas anteriores, y confirma con Select-String. Antes, revisa si hay una línea de cuatro comillas inversas sobrante justo antes de la entrada de 14:43; avísame en lugar de corregirla.
````

## 2026-11-17 15:22 · Documentar T110: veredicto de §6.1 en DECISIONES.md, SC-007 en la trazabilidad y T110 marcada.

- **Fecha**: 2026-11-17 15:22
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Documentar T110: veredicto de §6.1 en DECISIONES.md, SC-007 en la trazabilidad y T110 marcada.

**Prompt**

````text
/speckit-implement Solo documentación de T110. No toques código, pruebas, README ni datos_locales/. No hagas commit. Muestra git diff y git diff --stat al terminar.

Contexto medido (tests/bench_niebla.py y resultados_bench_niebla.txt, ya commiteados): M4 mide el peor paso de «ir a» entre todos los pares (origen, destino) alcanzables del mapa conocido completo de la cripta publicada más grande, cripta-02 (20 salas), leída de datos_locales/esqueleto_cripta-02.json. En cuatro corridas distintas el peor paso dio entre 0,02 y 0,09 ms (por llamada y reutilizado), contra el límite de 5 ms de §6.1: cumple con un margen de al menos 50 veces. Son 325 pares medidos de 380 posibles; los 55 restantes no tienen ruta porque hay 2 salidas cerradas con llave (5→19 y 17→18) que el jugador recuerda cerradas. Desde la sala 1 solo se alcanzan 17 de las 20 salas.

Tareas:
1. Decisiones/DECISIONES.md, §6.1: reemplaza la conclusión provisional («no se da por cumplido hasta T110», «PROVISIONAL», cifras viejas de las filas sintéticas) por el veredicto: CUMPLE sobre la cripta de referencia. Debe decir con claridad: (a) «cripta de referencia» se interpreta como la cripta publicada más grande (cripta-02, 20 salas); es una suposición porque el enunciado no la identifica con certeza (la definición viene del FR-029 de la spec 002, según Persona B); (b) el rango medido y el método (peor caso entre todos los pares alcanzables, mediana de 7 repeticiones por par, equipo Windows 11, Intel, Python 3.12.10, con carga normal de PyCharm y otros programas, por lo que las cifras varían entre corridas); (c) las 2 puertas con llave y los 17 de 20 alcanzables; (d) el contenido local de cripta-02 está incompleto (solo salas 1 a 8, 19 y 20) y el catálogo local lista 1 enemigo (ent_rata_gigante, rastreador) y 0 cazadores, dato SIN CONFIRMAR por Persona B; léelo del código (MotorSimulacion.costo_salida y GrafoConocido) y escribe solo si el costo de una salida depende o no de enemigos, citando lo que el código muestra, sin suponer; (e) las filas sintéticas son pruebas de estrés: hasta 400 salas cumplen (grilla de 400: 1,0 a 1,2 ms por paso en condiciones normales, hasta 3,8 con el equipo cargado), la cadena de 2500 cumple (2,5 a 3,4 ms por paso) y la grilla de 2500 NO cumple (8 a 26 ms por paso, Dijkstra sin heurística; A* está fuera de alcance según Persona A); (f) una nota metodológica breve: medir la cripta real entre los dos bloques sintéticos empeoraba las filas siguientes (la cadena de 2500 reutilizada subió de ≈2,9 a 4,4–7,9 ms por paso), por eso las filas de la cripta de referencia van al final; causa no investigada. Mantén el estilo y formato del archivo, en Markdown, y no inventes cifras: usa solo las de este prompt o las que verifiques en resultados_bench_niebla.txt.
2. specs/001-niebla-mapa-ir-a/trazabilidad.md: marca SC-007 como cubierto, citando las pruebas test_sc007_pr15_t110_* de tests/test_bench_niebla.py (obtén los nombres reales con grep), la fila «referencia/paso» de resultados_bench_niebla.txt y §6.1 de DECISIONES.md. Quita los asteriscos y notas de «pendiente T110» y la leyenda que dice «hoy solo T110»; ajusta la fila resumen de SC y cualquier conteo que dependa de eso. NO cambies todavía la cifra «Ran 812 tests» de SC-006: la actualizaré al final.
3. specs/001-niebla-mapa-ir-a/tasks.md: marca T110 como [X] con una nota breve («Hecho. Medición: commit <hash corto de git log -1 --format=%h -- tests/bench_niebla.py>; veredicto en DECISIONES.md §6.1») y quita su asterisco. No marques T114, T117 ni T004.
4. Registra este prompt en PROMPTS_LLM.md con la hora real de envío, sin tocar las entradas anteriores, y confirma con Select-String.
````

## 2026-11-17 15:27 · Corregir las frases que contradicen el veredicto de §6.1 tras T110 y comprobar duplicados en DECISIONES.md.

- **Fecha**: 2026-11-17 15:27
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Corregir las frases que contradicen el veredicto de §6.1 tras T110 y comprobar duplicados en DECISIONES.md.

**Prompt**

````text
/speckit-implement Solo documentación; no toques código, pruebas, README ni datos_locales/. No hagas commit. Tras T110 quedan frases que contradicen el veredicto de §6.1 (cumple sobre cripta-02).
1. specs/001-niebla-mapa-ir-a/tasks.md, «Punto de control 6» (≈ línea 318): reescríbelo así: `python main.py --bench` genera resultados_bench_niebla.txt con M1 a M6 medidas; M4 trae filas sintéticas (pruebas de estrés, PROVISIONAL) y la fila «referencia/paso» de cripta-02, que da el veredicto de §6.1: cumple (ver DECISIONES.md §5.3). Elimina «El límite de §6.1 no se da por cumplido hasta T110».
2. tasks.md, la línea de dependencias que dice «T110 | Curso | … §6.1 queda sin veredicto definitivo» (≈ línea 388): ajústala para que diga que T110 está hecha. Lee la línea ≈ 439 («antes de T110, no afirmar que se cumple §6.1») y dime si sigue siendo correcta o también hay que cambiarla; cámbiala solo si contradice el veredicto.
3. Nota de T110 en tasks.md: cambia «veredicto en DECISIONES.md §6.1» por «veredicto en DECISIONES.md §5.3, apartado «"ir a" y el límite de §6.1»».
4. Busca en Decisiones/ y specs/ (sin PROMPTS_LLM.md) estas frases: «hasta T110», «pendiente de T110», «no se da por cumplido», «aún no está publicada», «sin veredicto definitivo», «PROVISIONAL». Para cada coincidencia, indica archivo y línea y si sigue siendo correcta (PROVISIONAL aplicado a las filas sintéticas sí lo es). Corrige solo las que contradicen el veredicto y lista antes/después.
5. Comprobación de duplicados en Decisiones/DECISIONES.md: cuenta las apariciones de «Diagnóstico (medición puntual del 2026-11-16», «**Espacio reutilizado.**», «**Confirmación de Persona A (2026-11-16)», «Veredicto de §6.1 (T110)» y «Nota metodológica: orden de las filas». Cada una debe aparecer exactamente una vez; si alguna se repite, elimina la copia sobrante y dímelo.
6. Muestra git diff --stat. Registra este prompt en PROMPTS_LLM.md con la hora real de envío, sin tocar las anteriores, y confirma con Select-String.
````

## 2026-11-17 15:30 · Corregir en la evidencia la mención al archivo de resultados «de T109» (ahora es el de T110).

- **Fecha**: 2026-11-17 15:30
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Corregir en la evidencia la mención al archivo de resultados «de T109» (ahora es el de T110).

**Prompt**

````text
/speckit-implement Solo documentación; no toques código, pruebas, README ni datos_locales/. No hagas commit. En specs/001-niebla-mapa-ir-a/evidencia_quickstart.md (≈ línea 805), la frase «Este archivo de la corrida de T116 no reemplaza al resultados_bench_niebla.txt del repositorio, que es el de T109 y el que citan DECISIONES.md y la matriz» ya no es cierta: el del repositorio es el de la corrida de T110 (commit 70ecfdc), que citan DECISIONES.md §5.3 y la matriz. Corrígela conservando el resto del sentido. Busca también en specs/001-niebla-mapa-ir-a/ y Decisiones/ otras menciones al archivo de resultados «de T109» y corrige solo las que ya no sean ciertas, mostrando antes/después. Muestra git diff --stat. Registra este prompt en PROMPTS_LLM.md con la hora real de envío, sin tocar las anteriores, y confirma con Select-String.
````

## 2026-11-17 17:28 · Actualizar §5.3 de DECISIONES.md con las respuestas de Persona B (enemigos de cripta-02, veneno, cripta de referencia) y la revisión de Persona A.

- **Fecha**: 2026-11-17 17:28
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Actualizar §5.3 de DECISIONES.md con las respuestas de Persona B (enemigos de cripta-02, veneno, cripta de referencia) y la revisión de Persona A.

**Prompt**

````text
/speckit-implement Solo documentación; no toques código, pruebas, README ni datos_locales/. No hagas commit. Persona B respondió hoy (2026-11-17) y Persona A revisó su parte. Actualiza Decisiones/DECISIONES.md, §5.3, con estas cinco cosas, usando solo estos datos:
1. Enemigos de cripta-02: reemplaza «SIN CONFIRMAR por Persona B» por lo que dijo B: 1 enemigo (ent_rata_gigante, rastreador, en la sala 7) y 0 cazadores en las salas conocidas (1 a 8, 19 y 20); las salas 9 a 18 nunca se descargaron, así que no hay garantía para toda la cripta. Mantén la frase de que el costo de una salida no depende de los enemigos.
2. Veneno: en «Veneno no jugable (límite conocido)» agrega que Persona B confirmó el 2026-11-17 que el API no manda ningún dato de veneno (ni en enemigos, ni en objetos, ni en trampas), por lo que queda como límite conocido. Ajusta la frase que dice que la decisión «queda en Persona B y el grupo» o que se reabre si B confirma el dato, para que refleje que ya está confirmado. No cambies lo que dice sobre el voto de Persona A.
3. Cripta de referencia: donde dice que es una suposición, agrega que Persona B confirmó que coincide con su FR-029 (spec 002) y que el enunciado sigue sin identificarla con certeza. Actualiza también la línea de «Hipótesis»/«Preguntas abiertas» que la menciona si la hay.
4. Confirmación de Persona A del 2026-11-16: cambia «si la cripta real tiene 400 salas o menos, está dentro de los 5 ms» por «debería quedar dentro de los 5 ms», a petición de Persona A, porque la grilla de 400 llegó a 3.8 ms con el equipo cargado. No cambies nada más de esa confirmación.
5. En el apartado de filas sintéticas (pruebas de estrés) de §5.3, donde dice que la cadena de 2500 cumple con 2.5 a 3.4 ms por paso, agrega que eso es en condiciones normales y que en una corrida con el equipo cargado llegó a 7.4 ms por paso («no cumple» en esa corrida), por lo que es un caso en el límite que depende de la carga. No cambies las demás cifras.
Busca también en Decisiones/ y specs/ otras frases «sin confirmar» o «SIN CONFIRMAR» relacionadas con los enemigos de cripta-02 o con el veneno, y corrige solo las que ya no sean ciertas, mostrando antes/después. Muestra git diff --stat. Registra este prompt en PROMPTS_LLM.md con la hora real de envío, sin tocar las anteriores, y confirma con Select-String.
````

## 2026-11-17 18:22 · Corregir T110: cripta-02 es solo la sustituta de la cripta de referencia (aún no publicada), no la «publicada más grande» de FR-029.

- **Fecha**: 2026-11-17 18:22
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Corregir T110: cripta-02 es solo la sustituta de la cripta de referencia (aún no publicada), no la «publicada más grande» de FR-029.

**Prompt**

````text
/speckit-implement Corrección de T110. Persona B indicó que "cripta de referencia" (§6.1 del enunciado, la de «ir a» y el ciclo) NO es "la cripta publicada más grande" (FR-029 de la spec 002, que habla del tiempo de verificación de resolubilidad), y que la de referencia aún no está publicada. La mayor publicada, según specs/002-resolubilidad/research.md y plan.md, es cripta-06 (300 salas, 760 salidas); no hay copia local de ella. cripta-02 (20 salas) es solo la mayor de las copias locales en datos_locales/. No cambies tasks.md más allá de lo indicado, no toques README ni datos_locales/ ni archivos de A, B o D. No hagas commit.

PARTE 1 (código y pruebas, pruebas primero):
1. En tests/test_bench_niebla.py cambia la constante NOTA_REFERENCIA a «la mayor de las copias locales ({}, {} salas), usada como sustituta de la cripta de referencia (HIPÓTESIS: la del enunciado, §6.1, aún no está publicada)». Comprueba que las pruebas que la usan fallan por aserción antes del cambio en el bench.
2. En tests/bench_niebla.py cambia NOTA_REFERENCIA_M4 a ese mismo texto, y revisa docstrings, comentarios, el encabezado() y HIPOTESIS_REFERENCIA_M4 para que no digan «cripta publicada más grande» ni den §6.1 por resuelto de forma definitiva: la fila «referencia/paso» es la medición de §6.1 sobre la cripta sustituta (la mayor de las copias locales). No cambies nombres de funciones ni la lógica de medición.
3. Corre SOLO python -m tests.bench_niebla una vez para regenerar resultados_bench_niebla.txt y confirma que la fila de cripta-02 sale con la nota nueva. Luego la suite completa con el conteo, y git status (solo tests/bench_niebla.py, tests/test_bench_niebla.py y resultados_bench_niebla.txt, más lo que cambie en la parte 2).

PARTE 2 (documentación, solo lo que se refiere a la cripta de referencia de «ir a»; no cambies lo que dice B de la verificación de resolubilidad, que es correcto):
4. Decisiones/DECISIONES.md, §5.3: (a) el encabezado «Veredicto de §6.1 (T110): CUMPLE sobre la cripta de referencia» pasa a decir que cumple sobre la cripta sustituta (cripta-02, la mayor de las copias locales) y que el veredicto definitivo sobre la cripta de referencia del enunciado queda pendiente de su publicación; (b) reescribe el punto «Qué es la cripta de referencia (SUPOSICIÓN)» como HIPÓTESIS: la del enunciado (§6.1) no está publicada; NO es la «publicada más grande» de FR-029 (eso es de la verificación de resolubilidad); se usa cripta-02 (20 salas) como sustituta porque es la mayor de las copias locales; la mayor publicada es cripta-06 (300 salas, 760 salidas, según specs/002-resolubilidad/research.md), sin copia local y SIN MEDIR; con las sintéticas de 400 salas (grilla: 1.0 a 1.7 ms por paso, hasta 3.8 con el equipo cargado) se espera que cumpla con 300, pero es HIPÓTESIS, no medición; (c) quita toda atribución a FR-029 y la frase «Persona B confirmó que coincide con su FR-029»; (d) la línea de «Hipótesis abiertas» sobre cripta-02 pasa a la misma redacción; (e) en «Espacio reutilizado» actualiza las cifras citadas a las del resultados_bench_niebla.txt recién regenerado. Conserva lo demás (enemigos, veneno, nota metodológica, confirmaciones de A y B).
5. specs/001-niebla-mapa-ir-a/trazabilidad.md: en la fila de SC-007 cambia «Supone que la cripta de referencia es la publicada más grande, cripta-02» por la redacción nueva (sustituta; definitivo pendiente de publicación) y ajusta el párrafo «SC-007 y §6.1» igual. SC-007 sigue «hecho». specs/001-niebla-mapa-ir-a/tasks.md: corrige la nota de T110 y la fila de dependencias de T110 («se tomó como cripta de referencia la publicada más grande, cripta-02») para que digan que se usó como sustituta la mayor de las copias locales (cripta-02) y que el veredicto definitivo depende de la publicación; T110 sigue [X].
6. Busca en Decisiones/ y specs/001-niebla-mapa-ir-a/ (sin PROMPTS_LLM.md) las frases «publicada más grande», «FR-029» y «cripta de referencia» y corrige solo las que atribuyan a cripta-02 o a FR-029 la definición de la cripta de referencia de «ir a». Lista antes/después.
7. Muestra git diff --stat. Registra este prompt en PROMPTS_LLM.md con la hora real de envío, sin tocar las anteriores, y confirma con Select-String.
````

## 2026-11-17 18:36 · Cambiar el método de M4 «referencia/paso» (T110) a un par por origen, hacia su destino más lejano, para poder medir criptas grandes.

- **Fecha**: 2026-11-17 18:36
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Cambiar el método de M4 «referencia/paso» (T110) a un par por origen, hacia su destino más lejano, para poder medir criptas grandes.

**Prompt**

````text
/speckit-implement Cambio de método de la medición de §6.1 (T110) para criptas grandes. Contexto: medir_m4_referencia mide todos los pares (origen, destino) alcanzables. Con cripta-06 (300 salas, 760 salidas, 56 cerradas) serían unos 90 000 pares, demasiado para --bench y para la suite. El esqueleto de cripta-06 está en la raíz del repo (esqueleto_cripta-06.json, versión f9ed9afa683d; lo subió B). No lo muevas, no lo copies a datos_locales/, no toques README ni archivos de A, B o D, no cambies BusquedaRuta.py ni Conocimiento.py, y no hagas commit.

Método nuevo: por cada origen alcanzable, medir un solo paso hacia el destino alcanzable con MAYOR costo acumulado desde ese origen. Justificación: Dijkstra con corte al sacar el destino de la cola saca los nodos en orden de distancia, así que el trabajo hasta el destino no decrece con la distancia, y el más lejano es el peor caso de ese origen. Es una suposición sobre el peor caso (los empates pueden alterar el orden), debe quedar escrita como tal en el código y en DECISIONES.md.

PARTE 1 (pruebas primero, sin datos de ninguna cripta real en tests ni en el bench; mapas pequeños sintéticos de tests/mapas_sinteticos.py o armados a mano):
1. Escribe las pruebas nuevas en tests/test_bench_niebla.py y comprueba que fallan por aserción: (a) por cada origen, el destino elegido es el alcanzable de mayor costo acumulado (mapa chico con costos variados y una salida cerrada que dé destinos inalcanzables); (b) los orígenes sin ningún destino alcanzable se omiten y no fallan; (c) la fila reporta cuántos orígenes y cuántos pares se midieron (pares = orígenes medidos) y el peor par con su costo acumulado; (d) todo sigue pasando con la carpeta vacía (fila «no medido») y con la carpeta real.
2. Implementa en tests/bench_niebla.py el cálculo del destino más lejano por origen. Revisa primero Modelo/BusquedaRuta.py (por ejemplo campo_hacia(grafo, destino, cota, espacio)) y úsalo si encaja sin modificarlo; si no encaja, calcula las distancias en el bench con estructuras propias (Principio I: sin dict/set como índice, sin heapq ni bisect). Dime cuál usaste y por qué.
3. Mantén el nombre medir_m4_referencia, las dos variantes (espacio por llamada y reutilizado), la nota de «sustituta» y que las filas de referencia van después de todas las sintéticas. El formato de la fila agrega «origenes=N». Actualiza docstrings y comentarios que digan «todos los pares».
4. Medición de prueba SIN escribir resultados_bench_niebla.txt: corre medir_m4_referencia con carpeta = raíz del repo (una vez, con python -c) y muéstrame las filas de cripta-06 (origenes, pares, peor par, costo acumulado, ms, veredicto) y el tiempo total que tardó. Luego regenera resultados_bench_niebla.txt con python -m tests.bench_niebla una sola vez (queda con cripta-02 por ahora, ahora con el método nuevo) y corre la suite completa con el conteo.

PARTE 2 (solo documentación del método, sin dar veredicto sobre cripta-06 todavía): en Decisiones/DECISIONES.md §5.3, apartado «"ir a" y el límite de §6.1», actualiza el punto «Método» al método nuevo (con la suposición del peor caso y que en cripta-02 los pares medidos pasan de 325 a los orígenes alcanzables), y actualiza trazabilidad.md (SC-007) si cita el número de pares. Muestra antes/después.

Muestra git diff --stat. Registra este prompt en PROMPTS_LLM.md con la hora real de envío, sin tocar las anteriores, y confirma con Select-String.
````

## 2026-11-17 18:47 · Cambiar el método de M4 «referencia/paso» (T110) a cribado de todos los pares y confirmación de los K más lentos, porque la suposición del destino más lejano falló en cripta-06.

- **Fecha**: 2026-11-17 18:47
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Cambiar el método de M4 «referencia/paso» (T110) a cribado de todos los pares y confirmación de los K más lentos, porque la suposición del destino más lejano falló en cripta-06.

**Prompt**

````text
/speckit-implement Corrección del método de la medición de §6.1 (T110). Hallazgo: en cripta-06 (esqueleto_cripta-06.json en la raíz del repo; 300 salas, 299 con aristas, 22 052 pares alcanzables) la SUPOSICIÓN de destinos_mas_lejanos NO se cumple: medidos todos los pares con 1 repetición, el máximo dio 0.89, 0.99 y 1.02 ms (3 corridas), contra 0.15 y 0.17 ms de la fila por origen, y en ninguna corrida el peor par era el destino más lejano de su origen. Medir todos los pares es barato (1.5 a 2.4 s con 1 repetición). No muevas ni copies esqueleto_cripta-06.json, no toques README, datos_locales/, BusquedaRuta.py, Conocimiento.py ni archivos de A, B o D, no hagas commit.

Método nuevo (cribado y confirmación): (1) se miden TODOS los pares (origen, destino) alcanzables con 1 repetición cada uno; (2) los K pares más lentos del cribado se vuelven a medir con la mediana de `repeticiones` (7 por defecto); (3) la fila reporta el máximo de esas medianas (el veredicto es veredicto_paso de ese máximo). K es una constante nombrada en el bench (por ejemplo 50). Los pares alcanzables se enumeran con las distancias de _distancias_desde (un Dijkstra completo por origen), no con una búsqueda primer_paso por par. Si hay menos de K pares, se confirman todos.

PARTE 1 (pruebas primero, sin datos de ninguna cripta real; mapas armados a mano):
1. Reemplaza en tests/test_bench_niebla.py las pruebas de destinos_mas_lejanos por pruebas del método nuevo y comprueba que fallan por aserción: (a) los pares alcanzables que enumera el bench coinciden con un conteo independiente sobre el JSON (Bellman-Ford propio, como _mas_lejanos_json, sin GrafoConocido) en un mapa chico con costos variados y puertas cerradas; los orígenes sin destino alcanzable no aportan pares y no fallan; (b) la fila reporta «pares» = todos los alcanzables, «confirmados» = min(K, pares), el peor par con su costo acumulado, y ese peor par está entre los alcanzables; (c) con K parcheado a 1 y a un valor mayor que los pares, la fila sigue siendo válida; (d) carpeta vacía → fila «no medido»; carpeta real y carpeta con cripta chica → pasan en las dos variantes de espacio.
2. Implementa en tests/bench_niebla.py. Si destinos_mas_lejanos queda sin uso, bórrala junto con sus pruebas (el historial de git la conserva). Mantén medir_m4_referencia, las dos variantes, la nota de «sustituta» y el orden de las filas. La fila reporta origenes, pares, confirmados, peor, costo, ms, veredicto. Actualiza docstrings y comentarios que digan «un par por origen» o «destino más lejano».
3. Medición de prueba SIN escribir resultados_bench_niebla.txt: con carpeta = raíz del repo, corre medir_m4_referencia 3 veces (python -c) y muéstrame las filas de cripta-06 de cada corrida (origenes, pares, confirmados, peor par, costo, ms, veredicto) y el tiempo total de cada una. Luego corre la suite completa con conteo y tiempo; si la suite crece más de unos 30 s por esto, dime qué pruebas lo causan y propón cómo acotarlo (no lo apliques).

PARTE 2 (documentación; sin dar todavía el veredicto sobre cripta-06): en Decisiones/DECISIONES.md §5.3, apartado «"ir a" y el límite de §6.1», reescribe el punto «Método» al método de cribado y confirmación. Quita la SUPOSICIÓN del destino más lejano y en su lugar deja registrado el hallazgo (se probó el destino más lejano por origen; en cripta-06 no se cumplió: máximo de todos los pares con 1 repetición 0.89 a 1.02 ms contra 0.15 y 0.17 ms por origen; por eso se mide todo y se confirma con la mediana). Cambia la fila de la tabla «Pares medidos» (en cripta-02 vuelven a ser los 325 alcanzables) y actualiza trazabilidad.md (SC-007) donde cite pares, origenes u «destino más lejano». Muestra antes/después de cada cambio.

Muestra git diff --stat. Registra este prompt en PROMPTS_LLM.md con la hora real de envío, sin tocar las anteriores, y confirma con Select-String.
````

## 2026-11-17 19:15 · Cerrar T110 con cripta-06 como sustituta (copia local en datos_locales/): regenerar resultados y actualizar DECISIONES.md, trazabilidad, tasks y evidencia.

- **Fecha**: 2026-11-17 19:15
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Cerrar T110 con cripta-06 como sustituta (copia local en datos_locales/): regenerar resultados y actualizar DECISIONES.md, trazabilidad, tasks y evidencia.

**Prompt**

````text
/speckit-implement Cierre de T110 con cripta-06. El esqueleto de cripta-06 ya está movido con git mv a datos_locales/esqueleto_cripta-06.json (300 salas, 760 salidas, 56 cerradas, versión f9ed9afa683d; está en el índice de git, no lo muevas de nuevo). El bench toma la mayor copia local, así que ahora mide cripta-06. No toques README, BusquedaRuta.py, Conocimiento.py ni archivos de A, B o D. No hagas commit.

PARTE 1 (código y datos):
1. Revisa que ninguna prueba ni código asuma que en datos_locales/ hay exactamente 3 criptas o que la mayor es cripta-02 (busca «cripta-02», «datos_locales» y «cripta_mas_grande» en tests/ y en el código de producción). Si alguna prueba depende de eso, muéstramela y corrígela por aserción primero; si no hay ninguna, dilo.
2. Corre python -m tests.bench_niebla UNA vez para regenerar resultados_bench_niebla.txt y confirma que las filas «referencia/paso» son de cripta-06 (V=300, origenes, pares=22052, confirmados=50, peor, costo, ms, veredicto) con la nota «la mayor de las copias locales (cripta-06, 300 salas)…». Luego la suite completa con conteo y tiempo, y git status.

PARTE 2 (documentación, con las cifras del resultados_bench_niebla.txt recién regenerado y de las 3 corridas de 0.15 a 0.43 ms ya medidas; mantén el veredicto como HIPÓTESIS de que sustituye a la referencia, que aún no está publicada):
3. Decisiones/DECISIONES.md §5.3, apartado «"ir a" y el límite de §6.1»: (a) encabezado del veredicto: CUMPLE sobre la cripta sustituta cripta-06 (la mayor de las copias locales y la mayor publicada, 300 salas); el definitivo sobre la cripta de referencia del enunciado sigue pendiente de su publicación; (b) tabla de datos: cripta-06, 300 salas, pares medidos 22 052 (cribado) y 50 confirmados, peor paso con el rango de las corridas, límite 5 ms, margen (calcúlalo con el peor valor registrado); agrega abajo UNA línea con la medición previa sobre cripta-02 (20 salas, 325 pares, 0.02 a 0.09 ms); (c) «Qué cripta se mide (HIPÓTESIS)»: reescribe para decir que ahora la sustituta es cripta-06 (la mayor publicada, según specs/002-resolubilidad/research.md, con copia local desde que B la subió; quita «sin copia local» y «SIN MEDIR»), que no es la «publicada más grande» de FR-029, y que cripta-02 fue la sustituta de la primera medición; (d) «Mapa conocido completo»: da los datos de cripta-06 (704 de 760 salidas abiertas entran al grafo, 56 cerradas con llave no entran, 299 de 300 salas con aristas, la sala 160 «Puerta de la superficie» queda aislada porque su única salida y su única entrada están cerradas, 22 052 pares alcanzables) y conserva lo de cripta-02 como la medición previa; (e) «Enemigos»: aclara que lo confirmado por B es de cripta-02 y que de cripta-06 no se revisaron enemigos (no cambia la medición porque costo_salida no depende de ellos); (f) «Espacio reutilizado»: actualiza las cifras al resultados_bench_niebla.txt regenerado; (g) «Hipótesis abiertas»: la de la cripta sustituta pasa a cripta-06 con 300 salas medida; elimina «SIN MEDIR»; (h) reemplaza las citas del commit 70ecfdc como único commit de la medición por «commits 70ecfdc y c29aebd». Conserva lo demás (nota metodológica, hallazgo del destino más lejano, confirmaciones de A y B, veneno).
4. specs/001-niebla-mapa-ir-a/trazabilidad.md: fila y párrafo «SC-007 y §6.1» con las filas nuevas de cripta-06 (cópialas del archivo regenerado) y el mismo veredicto (cumple sobre la sustituta cripta-06; definitivo pendiente); quita lo de «filas todavía de la corrida con el método anterior». SC-007 sigue «hecho».
5. specs/001-niebla-mapa-ir-a/tasks.md: T110 (sigue [X]), la fila de dependencias de T110, el párrafo «Datos» de la fase 6 y el Punto de control 6: donde digan que la sustituta es cripta-02, pasa a cripta-06 (con cripta-02 como medición previa). Y specs/001-niebla-mapa-ir-a/evidencia_quickstart.md: solo las frases que den a cripta-02 como la sustituta actual.
6. Busca en Decisiones/ y specs/001-niebla-mapa-ir-a/ (sin PROMPTS_LLM.md) «cripta-02», «SIN MEDIR» y «sin copia local» y corrige solo las que quedaron falsas por este cambio. Lista antes/después.
7. Muestra git diff --stat. Registra este prompt en PROMPTS_LLM.md con la hora real de envío, sin tocar las anteriores, y confirma con Select-String.
````

## 2026-11-17 19:57 · Acotar el tiempo de la suite (una sola prueba con la carpeta real), actualizar la cadena de 2500, verificar las llaves de cripta-06 y cerrar T114 y T117.

- **Fecha**: 2026-11-17 19:57
- **Modelo**: Opus 5.5 (Claude Code)
- **Para qué se usó**: Acotar el tiempo de la suite (una sola prueba con la carpeta real), actualizar la cadena de 2500, verificar las llaves de cripta-06 y cerrar T114 y T117.

**Prompt**

````text
/speckit-implement Ajustes finales de T110 y cierre de T114 y T117. No hagas commit, no toques README, datos_locales/, el bench (tests/bench_niebla.py) ni archivos de A, B o D. Conserva la salida temprana que agregaste al Bellman-Ford de _pares_json.

1. Acotar el tiempo de la suite. Hoy 7 pruebas de tests/test_bench_niebla.py miden la carpeta real (datos_locales/, con cripta-06: 22 052 pares) y la suite pasó de 54 s a 96 s. Cámbialas para que usen una carpeta temporal con una copia chica (MAPA_CHICO u otra cripta armada a mano en la prueba, sin datos de cripta real). Deja UNA sola prueba con la carpeta real, que compruebe forma y conteos con CONFIRMADOS_M4_REFERENCIA parcheado a 1 y repeticiones mínimas, y que solo lea la carpeta (la instantánea de antes y después sigue igual). Las pruebas de la carpeta vacía no cambian. No cambies lo que cada prueba verifica, solo de dónde sale el esqueleto; si alguna verifica algo que solo tiene sentido con la carpeta real (por ejemplo que el bench lee de datos_locales/ y no contiene datos de la cripta), explícame cuál y cómo lo resolviste. Corre la suite completa y dame el conteo (debe seguir en 1163 o más) y el tiempo (objetivo: cerca de 55 a 60 s), y lista las 5 pruebas más lentas de test_bench_niebla.

2. En Decisiones/DECISIONES.md, en las filas sintéticas, donde dice que la cadena de 2500 llegó a 7.4 ms por paso en una corrida con el equipo cargado, actualiza a «hasta 11.7 ms» (corrida de T110 del 2026-11-17, equipo cargado) y deja claro que sigue siendo un caso en el límite que depende de la carga. No cambies las demás cifras.

3. Verifica con un script de solo lectura sobre datos_locales/esqueleto_cripta-06.json cuántas de las 56 salidas cerradas tienen llave (campo llave distinto de null) y cuántas tienen cierre_automatico. Si las 56 tienen llave, deja «con llave» en DECISIONES.md; si no, cambia la frase a «cerradas» y escribe el desglose real. Dime los números.

4. En specs/001-niebla-mapa-ir-a/tasks.md marca T114 y T117 como [X], sin cambiar nada más de esas tareas. Agrega a cada una una frase corta: T114 «revisada por Persona A, Persona B y Persona D (confirmado el 2026-11-17)» y T117 «revisión de Persona D de Modelo/, Persistencia/, Bitacora/ y main.py, con el README ya en main (confirmado el 2026-11-17)». Si hay una fila de dependencias o un resumen de pendientes que cite T114 o T117 como abiertas, actualízala igual. Muestra antes/después.

Muestra antes/después de los cambios de documentación y git diff --stat. Registra este prompt en PROMPTS_LLM.md con la hora real de envío, sin tocar las anteriores, y confirma con Select-String.
````
