# Feature Specification: Línea de tiempo y su persistencia

**Feature Branch**: `main` (el grupo trabaja directamente sobre `main`, constitución v3.0.1)

**Created**: 2026-11-09

**Status**: Draft

**Input**: Enunciado Parte II §3.6, §5.5, §6.1 y casos de «Línea de tiempo» del Apéndice B. El jugador puede consultar, sin modificar la partida, el estado del juego en cualquier instante desde el inicio (`historia <t>` / `historia #k`), también sin interacción (`--replay partida.log --hasta <t>`); la línea de tiempo se guarda y se carga completa.

## Contexto y alcance

El pergamino de retroceso de la Parte I solo deshace hasta 5 acciones y modifica la partida. La **línea de tiempo** es independiente de él: describe toda la historia de la partida, desde el instante 0, y permite **mirarla** sin tocarla. Consultar el pasado nunca cambia el presente.

**Comportamiento de la Parte I que se respeta** (no cambia):

- El pergamino de retroceso sigue limitado a 5 acciones hacia atrás, cuesta 0 y no cuenta como acción (P1 §2.11).
- Un comando rechazado muestra un aviso, no consume tiempo y no se anota en la bitácora (Constitución III).
- Los eventos del reloj (enemigos, efectos, cierres de puertas, rearmes de trampas) ocurren en instantes de tiempo virtual; varios pueden coincidir en un mismo instante.
- El archivo de partida lleva identificador y versión de formato; una versión distinta se rechaza con «Versión incompatible» (P1 §4.10).

**Comportamiento actual del programa** (no cambia; no se atribuye a un artículo del enunciado):

- Los comandos de consulta no consumen tiempo, no cuentan como acción y no se anotan en la bitácora (Constitución III: solo las acciones aceptadas se anotan y consumen tiempo).
- El historial de retroceso (los intervalos que usa el pergamino) no sobrevive a guardar y cargar.

**Dato que se consume de otra capacidad**: el «mapa conocido» del jugador (capacidad 001). Esta capacidad solo lo lee como dato: lo muestra tal como estaba en el instante consultado.

## Definiciones

- **Instante t**: valor del reloj virtual (≥ 0).
- **Estado en el instante t**: el estado de la partida después de ejecutar todos los eventos cuyo tiempo es menor o igual que t. Si a t le corresponde una decisión del jugador, es el estado justo antes de que la tome.
- **Acción número k**: la k-ésima acción aceptada del jugador (k ≥ 1) en la historia vigente. `#k` designa el estado justo antes de esa acción.
- **Historia vigente**: la historia tal como quedó, sin las acciones revertidas con un pergamino.
- **Punto de control**: copia completa del estado en un momento de la partida, guardada para acelerar las consultas.
- **K**: máximo de acciones del jugador entre dos puntos de control consecutivos.

## Clarifications

### Session 2026-11-09

- Q: ¿Qué se hace con un archivo de partida de la primera parte? → A: Se rechaza como incompatible con la regla vigente de versión (P1 §4.10), sin cargar nada. La migración queda fuera de alcance (ver Suposiciones).
- Q: ¿`historia #k` con k = acciones realizadas + 1 es válido? → A: Sí; es el estado actual (justo antes de la próxima acción). Con k mayor se rechaza (FR-004).
- Q: Tras un pergamino, al consultar un instante anterior al retroceso, ¿cuántos pergaminos de retroceso muestra el inventario del resumen? → A: Los que el jugador tenía en ese instante (FR-029).
- Q: En `--replay --hasta <t>` con una bitácora que contiene `@cargar`, ¿qué significa el instante `<t>`? → A: Reloj global continuo de la historia vigente: tras `@cargar` el reloj sigue desde el del archivo cargado, y lo jugado después de ese guardado y antes de cargar ya no existe en la línea (FR-030).
- Q: Para `--replay --hasta <t>`, ¿qué se entiende por «final» de la partida? → A: El estado resultante de reproducir la bitácora completa (FR-012).
- Q: Si se carga una partida guardada con un K y la nueva ejecución indica otro K, ¿cómo se comporta el programa? → A: Manda el K del archivo; combinar `--checkpoint-cada` con la carga de una partida se rechaza como error de uso (FR-031).
- Q: Justo después de un pergamino que revirtió 5 acciones, ¿qué muestra `historia`? → A: Se aplica la regla de FR-004 sin caso especial: el estado actual es el del punto al que se retrocedió, `#(acciones restantes + 1)` lo muestra y cualquier t o k posterior se rechaza.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar el estado en un instante o antes de una acción (Priority: P1)

Durante la partida el jugador escribe `historia <t>` o `historia #k` y ve un resumen del estado en ese momento del pasado. La partida no cambia en absoluto.

**Why this priority**: es el núcleo de la capacidad; todo lo demás (replay, persistencia, rendimiento) existe para sostenerlo.

**Independent Test**: con un paquete offline de prueba, jugar una secuencia conocida de acciones y comprobar, para varios `t` y `#k`, que el resumen coincide con el estado que tuvo la partida en ese momento, y que el estado actual es idéntico antes y después de consultar.

**Acceptance Scenarios**:

1. **Given** una partida en el reloj 700 con varias acciones hechas, **When** el jugador ejecuta `historia 250`, **Then** se muestra el resumen del estado después de todos los eventos con tiempo ≤ 250: reloj, sala del jugador, vida y estadísticas, inventario, efectos activos, enemigos de esa sala con su vida y el mapa conocido en ese momento.
2. **Given** que al instante t le corresponde una decisión del jugador, **When** ejecuta `historia <t>`, **Then** el resumen es el estado justo antes de tomarla (la decisión no aparece reflejada).
3. **Given** una partida con al menos 3 acciones, **When** ejecuta `historia #3`, **Then** se muestra el estado justo antes de la tercera acción del jugador, con el reloj de ese momento.
4. **Given** una partida con n acciones, **When** ejecuta `historia #1`, **Then** se muestra el estado inicial (reloj 0, sala inicial, sin acciones hechas).
5. **Given** cualquier consulta aceptada, **When** termina, **Then** el reloj, la posición, la vida, el inventario, los efectos, los enemigos, el mapa conocido y el historial de retroceso son idénticos a los de antes de consultar. *(Apéndice B: historia no consume tiempo ni se registra)*
6. **Given** el jugador en el reloj 400, **When** ejecuta `historia 900`, **Then** la orden se rechaza con un aviso. *(Apéndice B: historia con t mayor que el reloj actual)*
7. **Given** el jugador en cualquier momento de la partida, **When** pide la ayuda del juego, **Then** esta lista `historia <t>`, `historia #k`, `--hasta` y `--checkpoint-cada`. *(FR-010)*

---

### User Story 2 - La línea describe la historia tal como quedó (Priority: P1)

Cuando el jugador usa un pergamino de retroceso, las acciones revertidas dejan de existir en la línea de tiempo. Las consultas posteriores muestran solo la historia vigente, y las nuevas acciones continúan desde el punto al que se retrocedió.

**Why this priority**: sin esto la línea mostraría futuros que ya no existen y contradiría al reloj actual; es un caso explícito del Apéndice B.

**Independent Test**: jugar N acciones, usar un pergamino, consultar instantes y acciones que correspondían a lo revertido, y comprobar que no aparecen.

**Acceptance Scenarios**:

1. **Given** una partida en la que el jugador hizo las acciones 1 a 6 y usó un pergamino que deshizo la 6 (quedan las acciones 1 a 5), **When** ejecuta `historia #6`, **Then** muestra el estado actual (justo antes de la próxima acción, que sería la 6), sin reflejar la acción revertida; y `historia #7` se rechaza. *(Apéndice B: historia después de un pergamino)*
2. **Given** el mismo caso, **When** ejecuta `historia <t>` con t igual al reloj que tenía antes de revertir, **Then** se rechaza por ser posterior al reloj actual, y para cualquier t ≤ reloj actual el resumen no refleja ningún efecto de la acción revertida.
3. **Given** un pergamino usado y luego una nueva acción distinta, **When** consulta un instante posterior al punto de retroceso, **Then** el resumen refleja la nueva acción y nunca la revertida.
4. **Given** una partida con retrocesos, **When** consulta cualquier instante, **Then** el resultado coincide con el de una partida que nunca hubiera hecho las acciones revertidas, salvo la cantidad de pergaminos de retroceso, que queda fuera de la reversión (FR-029, P1 §2.11 y §4.6).
5. **Given** una partida con 10 acciones y un pergamino que revirtió las últimas 5 (quedan 5), **When** ejecuta `historia #6`, **Then** muestra el estado actual y `historia #7` se rechaza; las acciones 6 a 10 revertidas no son consultables. *(FR-004, FR-015)*
6. **Given** una partida con al menos 6 acciones en la que el jugador ya usó 5 pergaminos seguidos sin hacer acciones nuevas, **When** usa un sexto pergamino, **Then** no revierte nada más allá de esas 5 acciones hacia atrás y se comporta como en la Parte I cuando no hay intervalos disponibles; la línea no cambia. *(FR-014)*
7. **Given** un pergamino que revierte acciones de una partida larga, **When** se compara el costo de recortar la línea con la longitud de la partida, **Then** el costo es proporcional a lo recortado (las acciones revertidas y sus cambios) y no al largo total de la partida. *(FR-027)*
8. **Given** una partida en la que el jugador tenía 3 pergaminos en el instante t y después gastó 2 en retrocesos, **When** ejecuta `historia <t>`, **Then** el inventario del resumen muestra 3 pergaminos, y la cantidad real de la partida sigue siendo la actual. *(FR-029)*

---

### User Story 3 - Varios eventos en el mismo instante (Priority: P1)

Si varios eventos ocurren exactamente en el instante t, `historia <t>` muestra el estado después de todos ellos (salvo la decisión del jugador, que aún no se toma).

**Why this priority**: caso explícito del Apéndice B y regla de corte que define qué significa «estado en t».

**Independent Test**: construir una cripta de prueba donde coincidan en t un ataque de enemigo, el fin de un efecto y el cierre de una puerta, y comprobar que el resumen refleja los tres.

**Acceptance Scenarios**:

1. **Given** tres eventos programados exactamente en el instante t, **When** ejecuta `historia <t>`, **Then** el resumen refleja los tres, en el mismo orden de resolución que tuvieron en la partida. *(Apéndice B: varios eventos en el mismo instante)*
2. **Given** un evento en t y otro en t+1, **When** ejecuta `historia <t>`, **Then** el evento de t+1 no se refleja.

---

### User Story 4 - Consulta sin interacción: `--replay ... --hasta <t>` (Priority: P2)

El usuario ejecuta `--replay partida.log --hasta <t>` y el programa reproduce la partida hasta t e imprime el mismo resumen, sin abrir la interfaz interactiva.

**Why this priority**: permite verificar y automatizar consultas, pero se apoya en la consulta de la historia 1 y en el replay de la Parte I.

**Independent Test**: reproducir una bitácora conocida con `--hasta` en varios valores y comparar con el resumen de `historia` en la partida jugada.

**Acceptance Scenarios**:

1. **Given** una bitácora válida, **When** se ejecuta `--replay partida.log --hasta 250`, **Then** se imprime el mismo resumen que `historia 250` mostraría en la partida jugada, sin instanciar la vista.
2. **Given** una bitácora cuya partida terminó en el reloj 900, **When** se ejecuta `--replay partida.log --hasta 5000`, **Then** se muestra el estado final e indica que la partida terminó antes de ese instante. *(Apéndice B: --replay con t posterior al final)*
3. **Given** una bitácora que incluye retrocesos con pergamino, **When** se usa `--hasta`, **Then** el resumen corresponde a la historia vigente (sin las acciones revertidas).
4. **Given** `--hasta` con un valor no numérico o negativo, **When** se ejecuta, **Then** se informa el error de uso sin reproducir nada.
5. **Given** una partida jugada, guardada, cargada y continuada, **When** se reproduce su bitácora con `--replay`, **Then** la línea de tiempo resultante, y por tanto los resúmenes de cualquier instante, son los mismos que los de la partida jugada. *(FR-025)*
6. **Given** una bitácora con una directiva `@cargar` que restauró un guardado, **When** se ejecuta `--replay --hasta <t>`, **Then** `<t>` se interpreta con el reloj virtual global y continuo de la historia vigente, de modo que identifica un único momento. *(FR-030)*

---

### User Story 5 - Guardar y cargar conserva la línea completa (Priority: P2)

Al guardar la partida se conserva toda la línea de tiempo; al cargarla, `historia` responde sobre todo el pasado, incluso el anterior al guardado. Un archivo de la primera parte no se carga en silencio.

**Why this priority**: sin persistencia la línea se perdería entre sesiones, pero depende de que la línea exista (historias 1–3).

**Independent Test**: jugar, guardar, cargar en una sesión nueva y comparar el resumen de varios instantes antes y después; intentar cargar un archivo de formato anterior.

**Acceptance Scenarios**:

1. **Given** una partida guardada con acciones en el reloj 0..800, **When** se carga y se ejecuta `historia <t>` para t en ese rango, **Then** el resumen es idéntico al que se obtenía antes de guardar.
2. **Given** una partida cargada, **When** el jugador continúa y consulta un instante anterior y otro posterior al guardado, **Then** ambos resúmenes son correctos.
3. **Given** un archivo de partida de la primera parte, **When** se intenta cargar, **Then** se reporta «Versión incompatible» con el código de salida `2` y no se carga nada. *(Apéndice B: archivo de la primera parte)*
4. **Given** una partida cargada, **When** el jugador usa `retroceder`, **Then** se comporta como en la Parte I (el historial de retroceso no se guardó), y la línea refleja solo lo que efectivamente ocurra.
5. **Given** un archivo de partida con una versión de formato distinta de la vigente que no es la de la primera parte (por ejemplo una versión intermedia o desconocida), **When** se intenta cargar, **Then** se rechaza con «Versión incompatible» y código de salida `2`, sin cargar nada. *(FR-024)*
6. **Given** una partida guardada con el programa actual, **When** se consulta la versión de formato que declara su archivo, **Then** es distinta de la de la primera parte y el README la documenta. *(FR-023)*
7. **Given** una partida guardada con un K determinado, **When** se intenta cargarla usando `--checkpoint-cada`, **Then** se rechaza como error de uso con código de salida `1` sin cargar nada; y al cargarla sin esa opción rige el K del archivo. *(FR-031)*

---

### User Story 6 - Consultas rápidas y de memoria acotada (Priority: P3)

En partidas largas la consulta sigue siendo instantánea y la memoria no se dispara: ninguna consulta requiere rehacer más de K acciones del jugador y las copias completas del estado son escasas.

**Why this priority**: es un requisito de calidad medible (§6.1); la funcionalidad ya existe sin él, pero la capacidad no se acepta si no cumple.

**Independent Test**: con una partida de 5 000 acciones o más, medir con `--bench` el tiempo de `historia` en instantes variados y el crecimiento de la memoria.

**Acceptance Scenarios**:

1. **Given** una partida de al menos 5 000 acciones del jugador y K por defecto, **When** se ejecuta `historia` en cualquier instante o acción, **Then** responde en menos de 50 ms.
2. **Given** `--checkpoint-cada K`, **When** transcurren las acciones, **Then** nunca hay más de una copia completa del estado cada K acciones del jugador.
3. **Given** cualquier consulta, **When** se resuelve, **Then** no requiere aplicar ni deshacer cambios de más de K acciones del jugador.
4. **Given** una partida más larga, **When** se mide la memoria, **Then** crece con la cantidad de cambios ocurridos más un punto de control cada K acciones, no con «acciones × tamaño del estado».
5. **Given** una misma partida y tres valores distintos de K (por ejemplo 1, 50 y 500), **When** se ejecuta `historia` o `--replay --hasta` con el mismo t en cada uno, **Then** los resúmenes son idénticos en contenido y solo cambia el costo. *(FR-028)*

---

### Edge Cases

- `historia 0`: muestra el estado inicial (después de los eventos del instante 0, antes de la primera decisión).
- `historia <t>` con t igual al reloj actual: válido; muestra el estado actual.
- `historia <t>` con t negativo, no numérico o sin argumento: se rechaza con aviso de uso, sin consumir tiempo.
- `historia #0`, `#k` con k no entero o k mayor que acciones + 1: se rechaza.
- `historia` en una partida recién iniciada: válido solo para t = 0 o `#1`.
- Partida terminada (victoria o derrota): tras terminar la partida, el pasado se consulta con `--replay --hasta`, incluido el instante final.
- `--hasta` sin `--replay`: se rechaza como error de uso, sin ejecutar nada.
- `--checkpoint-cada` junto con `--replay`: es válido y solo afecta al costo, no al resumen (FR-028); si la bitácora contiene `@cargar`, rige el K del archivo cargado (FR-031).
- `--replay --hasta` sobre una bitácora de versión incompatible: se rechaza igual que un `--replay` sin `--hasta` (versión incompatible, código de salida `2`).
- Varias acciones consumen el mismo intervalo de tiempo o una acción cuesta 0: `#k` distingue estados que tienen el mismo reloj.
- `--checkpoint-cada` con valor 0, negativo o no entero: se rechaza como error de uso. K = 1 es válido.
- Instante t entre dos acciones del jugador: el estado es el de la última acción más los eventos del reloj hasta t.
- Consulta tras cargar una partida: los puntos de control y los cambios anteriores al guardado siguen disponibles.
- Una consulta durante un viaje automático «ir a»: no aplica; el viaje es un único comando no interactivo.
- Los intervalos descartados por un pergamino no deben dejar cambios ni puntos de control huérfanos que alteren consultas posteriores.

## Requirements *(mandatory)*

### Functional Requirements

**Estado en un instante**

- **FR-001**: El sistema MUST poder reconstruir el estado de la partida en cualquier instante t entre 0 y el reloj actual, definido como el estado después de ejecutar todos los eventos con tiempo ≤ t; si a t le corresponde una decisión del jugador, MUST ser el estado justo antes de tomarla.
- **FR-002**: Cuando varios eventos ocurren en el mismo instante t, la reconstrucción en t MUST reflejarlos todos, en el mismo orden de resolución de la partida real.
- **FR-003**: El sistema MUST aceptar el comando `historia <t>` con t entero no negativo menor o igual que el reloj actual.
- **FR-004**: El sistema MUST aceptar el comando `historia #k`, que muestra el estado justo antes de la acción número k del jugador, para 1 ≤ k ≤ acciones realizadas + 1; con k = acciones + 1 MUST mostrar el estado actual.
- **FR-005**: `historia <t>` con t mayor que el reloj actual MUST rechazarse con un aviso. Igualmente MUST rechazarse un argumento ausente, no numérico, negativo, `#0` o `#k` fuera de rango.

**Contenido del resumen**

- **FR-006**: El resumen MUST incluir como mínimo: reloj, sala del jugador, vida y estadísticas, inventario, efectos activos, los enemigos de esa sala con su vida, y el mapa conocido del jugador en ese instante (tal como lo definía la capacidad 001, sin recalcularlo con información posterior).
- **FR-029**: El inventario del resumen MUST mostrar los pergaminos de retroceso que el jugador tenía en el instante consultado, aunque después se hayan gastado en retrocesos; consultar el pasado no restaura ni modifica la cantidad real de pergaminos de la partida (P1 §2.11 y §4.6).
- **FR-007**: El resumen de `historia` en la partida interactiva y el de `--replay ... --hasta` para el mismo instante MUST ser idénticos en contenido.

**Consulta sin efectos**

- **FR-008**: El comando `historia` MUST NOT consumir tiempo virtual, MUST NOT contar como acción del jugador, MUST NOT anotarse en `partida.log` y MUST NOT alterar ningún estado de la partida ni el historial de retroceso.
- **FR-009**: Una consulta rechazada MUST seguir las reglas de la Parte I: aviso, sin consumo de tiempo y sin anotación en la bitácora.
- **FR-010**: La ayuda del juego y el README MUST incluir `historia <t>`, `historia #k`, `--hasta` y `--checkpoint-cada`.

**Consulta sin interacción**

- **FR-011**: El sistema MUST aceptar `--replay <bitácora> --hasta <t>`, reproducir la partida hasta t e imprimir el resumen del FR-006 sin instanciar la vista. `--hasta` MUST conservar todos los rechazos del replay: una bitácora o cripta de versión incompatible termina con `Versión incompatible: ...` y código de salida `2`.
- **FR-030**: En una bitácora con directivas `@cargar`, el instante `<t>` de `--hasta` MUST ser el reloj virtual global y continuo de la historia vigente: tras `@cargar` el reloj continúa desde el del archivo cargado, y lo jugado entre ese guardado y la carga no existe en la línea, de modo que cada `<t>` identifica un único momento.
- **FR-012**: Si t es posterior al final de la partida, `--replay --hasta` MUST mostrar el estado final e indicar que la partida terminó antes de ese instante. El «final» MUST ser el estado resultante de reproducir la bitácora completa, haya terminado o no la partida (victoria o derrota).
- **FR-013**: `--hasta` con un valor no entero o negativo MUST terminar con error de uso (código de salida `1`), sin reproducir. `--hasta` usado sin `--replay` MUST rechazarse igualmente como error de uso.

**Interacción con el retroceso**

- **FR-014**: El pergamino de retroceso MUST seguir limitado a 5 acciones hacia atrás y su comportamiento de la Parte I no cambia; la línea de tiempo es independiente de ese límite.
- **FR-015**: Las acciones revertidas con un pergamino MUST dejar de existir en la línea de tiempo: ninguna consulta posterior las refleja, ni sus eventos asociados, ni sus puntos de control.
- **FR-016**: Las acciones nuevas tras un retroceso MUST continuar la línea desde el punto al que se retrocedió, y la numeración de acciones MUST ser la de la historia vigente.
- **FR-027**: Recortar la línea de tiempo al usar un pergamino MUST costar en proporción a lo recortado (las acciones revertidas y sus cambios), no al largo total de la partida (§5.5).

**Memoria y rendimiento**

- **FR-017**: El sistema MUST guardar copias completas del estado (puntos de control) en no más de una cada K acciones del jugador.
- **FR-018**: K MUST ser configurable con `--checkpoint-cada K` (entero ≥ 1). El valor por defecto lo fija el grupo y MUST justificarse con mediciones reproducibles de `--bench`, que se documentan en el README o en el Documento de Decisiones.
- **FR-019**: Responder cualquier consulta MUST NOT requerir aplicar o deshacer los cambios de más de K acciones del jugador.
- **FR-020**: La consulta `historia` MUST tardar menos de 50 ms en una partida de al menos 5 000 acciones del jugador con K por defecto.
- **FR-021**: El consumo de memoria de la línea MUST crecer con la cantidad de cambios de estado más un punto de control cada K acciones, y no con el producto «acciones × tamaño del estado». Fuera de los puntos de control, MUST almacenarse solo la información necesaria para reconstruir los cambios.
- **FR-028**: El resumen de cualquier consulta (`historia` y `--replay --hasta`) MUST ser idéntico para cualquier valor de K; K solo afecta al costo, nunca al contenido.

**Persistencia**

- **FR-022**: Guardar la partida MUST conservar la línea de tiempo completa (todos los cambios y los puntos de control vigentes); cargarla MUST restaurarla de modo que `historia` responda igual que antes de guardar para cualquier instante.
- **FR-023**: Como el formato del archivo de partida cambia, su número de versión MUST incrementarse y el README MUST documentarlo.
- **FR-024**: Un archivo de partida con cualquier versión de formato distinta de la vigente (incluida la de la primera parte) MUST rechazarse como incompatible (`Versión incompatible: ...`, código de salida `2`), sin cargar nada y sin conversión silenciosa.
- **FR-031**: El archivo de partida MUST conservar el valor de K con que se guardó, y al cargarla ese valor MUST regir los límites de FR-017 y FR-019. Usar `--checkpoint-cada` junto con la carga de una partida MUST rechazarse como error de uso (código de salida `1`), sin cargar nada.
- **FR-025**: `--replay` MUST producir la misma línea de tiempo (y por tanto los mismos resúmenes) que la partida jugada, incluidas las partidas cargadas y continuadas.

### Key Entities *(include if feature involves data)*

- **Línea de tiempo**: registro completo y ordenado de lo que cambió en la partida vigente, desde el instante 0 hasta el reloj actual. Se guarda, se carga y se recorta cuando un pergamino revierte acciones.
- **Cambio**: una modificación atómica del estado de la partida en un instante dado, atribuible a una acción del jugador o a un evento del reloj. Permite reconstruir el estado entre dos puntos de control.
- **Punto de control**: copia completa del estado en un momento de la partida; hay a lo sumo uno cada K acciones del jugador.
- **Resumen histórico**: lo que `historia` y `--replay --hasta` muestran: reloj, sala, vida y estadísticas, inventario, efectos activos, enemigos de la sala con su vida y mapa conocido.
- **Referencia temporal**: la forma de señalar un momento del pasado: un instante `<t>` o «justo antes de la acción `#k`».

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Los 6 casos de «Línea de tiempo» del Apéndice B tienen cada uno al menos una prueba automatizada o un `partida.log` de evidencia que cita su FR, y todos pasan.
- **SC-002**: En una partida de al menos 5 000 acciones del jugador con K por defecto, el 100 % de las consultas `historia` medidas (instantes y acciones distribuidos en toda la partida) responde en menos de 50 ms.
- **SC-003**: Para un conjunto de partidas de prueba, el resumen de `historia <t>` y `historia #k` coincide en el 100 % de los casos con el estado real registrado en ese momento al jugar la partida, y el resumen es idéntico para al menos tres valores distintos de K (FR-028).
- **SC-004**: Tras ejecutar cualquier `historia` (aceptada o rechazada), el reloj, el contador de acciones, la bitácora y el historial de retroceso son idénticos a los de antes, en el 100 % de las pruebas.
- **SC-005**: Tras guardar y cargar, el resumen de cualquier instante coincide con el previo a guardar en el 100 % de los casos probados.
- **SC-006**: Con una partida de 5 000 acciones, ninguna consulta requiere aplicar o deshacer más de K acciones, y el número de copias completas es como máximo ⌈acciones / K⌉ + 1; duplicar las acciones duplica aproximadamente la memoria de la línea.
- **SC-007**: El valor por defecto de K queda respaldado por mediciones de `--bench` (tiempo de consulta y memoria) con al menos tres valores de K y con la alternativa sin puntos de control (§5.5, §6.3), incluidas en la documentación.
- **SC-008**: Un archivo de partida con cualquier versión de formato distinta de la vigente (incluida la de la primera parte) se rechaza como incompatible en el 100 % de los intentos, con salida `2` y sin cargar estado.
- **SC-009**: La suite completa de pruebas sigue al 100 % en verde, sin red, incluidas las de la Parte I y las de la capacidad 001.
- **SC-010**: El costo del recorte no crece con la longitud de la partida; el umbral numérico se fija con mediciones de `--bench` (Constitución VIII) (FR-027).

## Assumptions

- El valor por defecto de K lo escoge el grupo a partir de mediciones durante el plan; la especificación solo exige que exista, que sea configurable y que esté justificado (FR-018, SC-007).
- Un archivo de la primera parte se rechaza (no se migra): es la opción más simple y cumple la regla vigente de versión incompatible; la migración explícita se descarta salvo enmienda de esta especificación.
- `historia #k` cuenta solo acciones aceptadas del jugador de la historia vigente; los comandos de consulta y los rechazados no cuentan.
- Los pasos de un viaje «ir a» (capacidad 001) cuentan como acciones individuales del jugador, por lo que `#k` puede apuntar a cada paso.
- Tras cargar una partida, el historial de retroceso del pergamino está vacío (comportamiento actual del programa), pero la línea de tiempo completa sí está disponible para consultar.
- «Estadísticas» del jugador se entiende como las estadísticas que el juego ya maneja (por ejemplo ataque, defensa); no se añaden nuevas.
- Tras terminar la partida, el pasado se consulta con `--replay --hasta`, incluido el instante final; no se promete uso interactivo de `historia` después del fin.
- Depende de: motor de simulación y agenda de eventos, pergamino de retroceso, bitácora y `--replay`, la directiva `@cargar` de la bitácora (capacidad 001, de la que depende FR-025), archivo de partida con versión de formato (Parte I), y mapa conocido (capacidad 001).

## Fuera de alcance

- La niebla de guerra y cómo se construye el mapa conocido (capacidad 001): aquí solo se consume como dato.
- El comando «ir a» y su cálculo de ruta (capacidad 001).
- La búsqueda de rutas del cazador.
- La verificación de resolubilidad de la cripta (capacidad 002).
- Los costos de salida y de terreno (§3.1).
- Modificar o «viajar» al pasado: la línea solo se consulta; no hay forma de editar ni de reanudar la partida desde un instante pasado (para eso existe el pergamino, limitado a 5 acciones).
- Migración automática de archivos de la primera parte.
- Ampliar el límite de 5 acciones del pergamino de retroceso.
