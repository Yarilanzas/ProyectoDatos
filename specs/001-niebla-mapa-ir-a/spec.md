# Feature Specification: Niebla de guerra, mapa conocido y viaje automático «ir a»

**Feature Branch**: `main` (el grupo trabaja directamente sobre `main`, constitución v3.0.0)

**Created**: 2026-11-04

**Status**: Draft

**Input**: Enunciado Parte II §3.3, §3.4, §5.3 y casos de niebla e «ir a» del Apéndice B. El jugador deja de ver el mapa completo: solo conoce lo que exploró; puede consultar su mapa conocido y viajar automáticamente a una sala explorada con «ir a <sala>».

## Contexto y alcance

Hasta la Parte I el jugador podía razonar sobre la cripta completa. Esta capacidad introduce la **niebla de guerra**: lo que el jugador ve y lo que el viaje automático usa se deriva solo de su **conocimiento**, no del mapa real. El programa sigue obteniendo el esqueleto completo de la cripta y la precarga de salas puede usarlo libremente, porque es infraestructura y no información que se muestre al jugador.

**Comportamiento de la Parte I que se respeta** (no cambia):

- Entrar a una sala activa primero sus trampas y después sus enemigos (§2.4); el jugador empieza en la sala inicial con reloj 0 y los enemigos de esa sala se activan en ese instante.
- Un comando rechazado muestra un aviso, no consume tiempo y no se anota en la bitácora.
- `retroceder` usa un pergamino de retroceso: deshace la última acción del jugador completa (hasta 5 hacia atrás), cuesta 0 y no cuenta como acción.
- La antorcha se enciende con `usar`, dura un tiempo y se apaga sola; es estado de sesión y no se guarda.
- El historial de retroceso no sobrevive a guardar y cargar.
- Las puertas pueden estar cerradas (se abren con `abrir` y su llave) y algunas se cierran solas tiempo después de abrirse.

**Fuera de alcance**: la búsqueda de rutas del cazador (otra capacidad) y cómo se calcula internamente la ruta de «ir a» (va en el plan).

## Clarifications

### Session 2026-11-04

- Q: ¿La antorcha revela el estado de las puertas de las vecinas que explora? → A: No. Revela las salidas (destino y costo), pero su estado queda «sin observar» hasta que el jugador esté en una de las dos salas que conectan; «ir a» no usa salidas sin observar (FR-011).
- Q: ¿Qué cuenta como «recibir daño» para detener el viaje? → A: Cualquier pérdida de vida, incluido el daño de un veneno que ya estaba activo antes de la orden (FR-027c).
- Q: ¿Se puede iniciar «ir a» desde una sala con enemigos? → A: Sí; la parada por enemigos solo aplica al entrar a una sala (FR-028).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Explorar bajo niebla de guerra (Priority: P1)

El jugador recorre la cripta sin conocerla de antemano. Cada sala está, para él, en uno de tres estados: **explorada** (entró al menos una vez; conoce su nombre, sus salidas, el costo de cada salida y el estado de sus puertas según su última observación), **avistada** (no explorada, pero destino de una salida de una sala explorada; solo sabe que existe) o **desconocida** (no sabe nada). Al entrar a una sala, esta pasa a explorada y sus vecinas pasan a avistadas si no estaban exploradas.

**Why this priority**: es la base de la capacidad; el mapa conocido y «ir a» dependen de que exista el conocimiento del jugador.

**Independent Test**: con un paquete offline de prueba, iniciar una partida, moverse y comprobar el estado de cada sala (explorada / avistada / desconocida) tras cada movimiento.

**Acceptance Scenarios**:

1. **Given** una partida nueva, **When** el reloj está en 0 y aún no se hizo ninguna acción, **Then** la sala inicial está explorada, las salas destino de sus salidas están avistadas y todas las demás son desconocidas.
2. **Given** una sala B avistada y adyacente a la sala actual por una salida abierta, **When** el jugador se mueve a B, **Then** B pasa a explorada (se conocen su nombre, salidas, costos y estado de puertas) y los destinos de las salidas de B que no estaban explorados pasan a avistados.
3. **Given** el jugador en la sala A con una salida abierta hacia B, **When** la puerta A→B se cierra mientras el jugador no está en A ni en B, **Then** el mapa del jugador sigue mostrando esa puerta abierta.
4. **Given** el mapa recuerda abierta una puerta que en realidad está cerrada, **When** el jugador entra a cualquiera de las dos salas que esa puerta conecta, **Then** el mapa se actualiza y muestra la puerta cerrada. Apéndice B: puerta recordada abierta que está cerrada

---

### User Story 2 - Antorcha encendida revela las vecinas (Priority: P1)

Con la antorcha encendida, al entrar a una sala también quedan exploradas todas sus vecinas, a través de cualquier salida (abierta o cerrada). Explorar una vecina así revela su nombre y salidas, pero no su contenido, y no activa sus enemigos ni sus trampas.

**Why this priority**: es la interacción obligatoria entre la niebla y un objeto ya existente de la Parte I, y tiene dos casos del Apéndice B.

**Independent Test**: encender la antorcha, entrar a una sala cuyas vecinas tienen enemigos y trampas, y comprobar que las vecinas quedan exploradas sin que cambie la vida del jugador ni el estado de esos enemigos y trampas; después usar un pergamino y comprobar que el conocimiento vuelve al estado anterior.

**Acceptance Scenarios**:

1. **Given** la antorcha encendida y una sala B cuya vecina C (por una salida cerrada) tiene enemigos dormidos y una trampa armada, **When** el jugador entra a B, **Then** B y C quedan exploradas, los enemigos de C siguen dormidos, la trampa de C no se activa y el contenido de C no se muestra. *(Apéndice B: antorcha explora sin activar enemigos ni trampas)*
2. **Given** el jugador entró a una sala con la antorcha encendida y eso exploró varias vecinas, **When** usa un pergamino de retroceso, **Then** la sala de llegada y las vecinas exploradas por la antorcha vuelven exactamente al estado de conocimiento que tenían antes de esa entrada (explorada, avistada o desconocida, y las puertas como se recordaban). *(Apéndice B: pergamino revierte entrada con antorcha)*
3. **Given** la antorcha apagada, **When** el jugador entra a una sala, **Then** solo esa sala pasa a explorada; sus vecinas no exploradas quedan avistadas.
4. **Given** la antorcha encendida y una vecina C explorada por la antorcha con una salida hacia D, **When** el jugador consulta el mapa sin haber estado nunca en C ni en D, **Then** la salida C→D aparece con su destino y costo pero con estado «sin observar», y «ir a» no la usa en ninguna ruta.

---

### User Story 3 - Consultar el mapa conocido (Priority: P2)

El jugador escribe un comando de consulta y ve su mapa conocido: las salas exploradas con sus salidas y el costo de cada una (y el estado de cada puerta tal como lo recuerda) y la lista de salas avistadas. Nada de lo que se muestra proviene de salas desconocidas ni del estado real no observado.

**Why this priority**: da valor al conocimiento acumulado y es la forma de verificar visualmente la niebla; no es imprescindible para «ir a».

**Independent Test**: tras unos movimientos, ejecutar el comando y comparar la salida con las salas recorridas.

**Acceptance Scenarios**:

1. **Given** el jugador exploró las salas 1 y 2, **When** consulta el mapa, **Then** se listan las salas 1 y 2 con cada salida (dirección, destino, costo y estado recordado de la puerta) y, aparte, las salas avistadas; no aparece ninguna sala desconocida.
2. **Given** cualquier estado de la partida, **When** el jugador consulta el mapa, **Then** el reloj no avanza, no se cuenta como acción y no se anota en la bitácora.

---

### User Story 4 - Viaje automático «ir a <sala>» (Priority: P2)

El jugador pide ir a una sala explorada y el juego lo lleva mediante una secuencia de movimientos ordinarios, usando solo su conocimiento, y se detiene ante cualquier peligro o imprevisto.

**Why this priority**: es la funcionalidad de mayor valor de uso, pero depende de las historias 1 y 2.

**Independent Test**: con un paquete offline de prueba cuyas rutas y costos se conocen, explorar varias salas, ejecutar «ir a» y comprobar la secuencia de salas, el reloj final, el motivo de parada y el contenido de la bitácora.

**Acceptance Scenarios**:

1. **Given** una sala que no está explorada (avistada o desconocida), **When** el jugador ordena «ir a» esa sala, **Then** la orden se rechaza con un aviso, el reloj no avanza y no se anota nada en la bitácora. *(Apéndice B: ir a hacia sala no explorada)*
2. **Given** una ruta conocida hacia el destino que pasa por una puerta que el mapa recuerda abierta pero que en realidad está cerrada, **When** el viaje llega a una sala desde la que se observa esa puerta, **Then** el mapa se actualiza, la ruta se recalcula evitándola; si existe otra ruta conocida el viaje continúa por ella, y si no queda ninguna el viaje se detiene con un aviso sin consumir tiempo adicional. *(Apéndice B: puerta recordada abierta que está cerrada)*
3. **Given** una ruta que entra a una sala con enemigos dormidos, **When** el viaje entra a esa sala, **Then** los enemigos se activan según la Parte I (§2.4) y el viaje se detiene en esa sala. *(Apéndice B: ir a entra a sala con enemigos dormidos)*
4. **Given** un viaje de varios pasos ya ejecutado (completo o detenido), **When** el jugador usa un pergamino de retroceso, **Then** solo se deshace el último paso del viaje (el jugador vuelve a la sala anterior a ese paso, con su conocimiento y el resto del estado de antes de ese paso) y el viaje no se reanuda. *(Apéndice B: pergamino durante un viaje)*
5. **Given** dos rutas conocidas de igual costo total cuyos primeros pasos van a vecinas distintas, **When** el jugador ordena «ir a», **Then** el primer paso va hacia la vecina de menor id.
6. **Given** un viaje en curso, **When** el jugador pierde vida en cualquier paso (incluido el daño de un veneno activo desde antes de la orden), **Then** el viaje se detiene al terminar ese paso.
7. **Given** un viaje que llega al destino, **When** termina, **Then** la bitácora contiene una línea de comentario con la orden «ir a <sala>» seguida de un movimiento individual por cada paso, y `--replay` de esa bitácora reproduce la misma partida.
8. **Given** una ruta conocida que solo existe a través de una puerta cerrada de la que el jugador tiene la llave, **When** ordena «ir a», **Then** el viaje no abre la puerta: esa salida no cuenta para la ruta.
9. **Given** el jugador en una sala con enemigos activos y una ruta conocida hacia una sala explorada, **When** ordena «ir a», **Then** la orden se acepta y el viaje empieza (salvo que se detenga por otra condición, por ejemplo al recibir daño en el primer paso).

---

### User Story 5 - Guardar y cargar conservando el conocimiento (Priority: P3)

El conocimiento del jugador forma parte del estado de la partida: se guarda en el archivo de partida, se recupera al cargar y forma parte de la línea de tiempo (§3.6).

**Why this priority**: necesario para que la niebla sea coherente entre sesiones, pero se apoya en el guardado ya existente.

**Independent Test**: explorar varias salas (incluyendo alguna puerta recordada con un estado distinto del real), guardar, cargar en una sesión nueva y comparar el mapa conocido antes y después.

**Acceptance Scenarios**:

1. **Given** una partida con salas exploradas, avistadas y puertas recordadas (incluida una que se recuerda abierta y en realidad está cerrada), **When** se guarda y luego se carga la partida, **Then** el mapa conocido es idéntico al de antes de guardar, incluido el estado recordado de cada puerta.
2. **Given** una partida guardada y cargada, **When** se reproduce su bitácora completa con `--replay`, **Then** el conocimiento final coincide con el de la partida jugada.

---

### Edge Cases

- «ir a» hacia la sala en la que ya está el jugador: se rechaza con un aviso, sin consumir tiempo.
- «ir a» hacia una sala explorada pero sin ruta conocida desde la sala actual (por ejemplo, todas las rutas pasan por puertas recordadas cerradas): se rechaza con un aviso, sin consumir tiempo.
- «ir a» con un identificador que no corresponde a ninguna sala: se rechaza igual que hacia una sala no explorada, sin revelar si la sala existe.
- El viaje entra a la sala de salida en condiciones de victoria, o el jugador muere en un paso: la partida termina y el viaje se detiene.
- Una puerta de la ruta se cierra sola durante el viaje mientras el jugador está en una de sus dos salas: el jugador la observa, el mapa se actualiza y el siguiente cálculo de ruta la evita.
- Entrar con la antorcha encendida a una sala cuyas vecinas ya estaban exploradas: no cambia nada de ellas salvo lo que el jugador observe directamente.
- Una sala explorada por la antorcha cuyos vecinos no fueron visitados: esos vecinos pasan a avistados (por la definición de avistada).
- `retroceder` sin intervalos disponibles tras un viaje (por ejemplo, después de cargar): se comporta igual que en la Parte I.
- Pergamino que deshace la entrada a la sala inicial nunca aplica: la sala inicial está explorada desde el instante 0, antes de cualquier acción, y no puede volver a otro estado.

## Requirements *(mandatory)*

### Functional Requirements

**Conocimiento del jugador**

- **FR-001**: El sistema MUST mantener, para el jugador, el estado de conocimiento de cada sala de la cripta: explorada, avistada o desconocida.
- **FR-002**: La sala inicial MUST estar explorada desde el instante 0, antes de la primera acción del jugador.
- **FR-003**: Cuando el jugador entra a una sala, esa sala MUST pasar a explorada.
- **FR-004**: Una sala MUST considerarse avistada si y solo si no está explorada y es destino de al menos una salida de una sala explorada; en cualquier otro caso, si no está explorada, MUST considerarse desconocida.
- **FR-005**: De una sala explorada el jugador MUST conocer su nombre, sus salidas, el destino y el costo de cada salida, y el estado de cada puerta según su última observación. De una sala avistada solo MUST conocer que existe detrás de una salida conocida; de una desconocida, nada.

**Memoria de puertas**

- **FR-006**: El jugador MUST observar una puerta siempre que esté en cualquiera de las dos salas que conecta, y en ese momento el mapa MUST registrar el estado real de la puerta.
- **FR-007**: Mientras el jugador no observa una puerta, el mapa MUST conservar el estado de su última observación aunque la puerta haya cambiado después (por apertura, cierre automático u otro efecto).
- **FR-008**: Las puertas que el propio jugador abre MUST figurar abiertas en su mapa inmediatamente.

**Antorcha**

- **FR-009**: Mientras la antorcha está encendida, al entrar a una sala el sistema MUST explorar además todas sus vecinas, a través de cualquier salida, abierta o cerrada.
- **FR-010**: Explorar una vecina mediante la antorcha MUST revelar su nombre y sus salidas, MUST NOT revelar su contenido (enemigos, trampas, objetos) y MUST NOT activar sus enemigos ni sus trampas.
- **FR-011**: Explorar una vecina mediante la antorcha MUST NOT revelar el estado (abierta/cerrada) de las puertas de esa vecina que el jugador no observa desde la sala en la que está: esas puertas MUST figurar en el mapa como «sin observar» hasta que el jugador esté en una de las dos salas que conectan (FR-006). Una salida «sin observar» MUST NOT usarse en las rutas de «ir a».

**Separación entre mapa y conocimiento**

- **FR-012**: Todo lo que la interfaz muestra sobre la topología de la cripta (salas, salidas, costos, estado de puertas) y todo lo que usa «ir a» MUST derivarse exclusivamente del conocimiento del jugador.
- **FR-013**: El programa MAY seguir obteniendo el esqueleto completo de la cripta y la precarga de salas MAY usarlo libremente; ese uso MUST NOT reflejarse en lo que se muestra al jugador.

**Línea de tiempo, retroceso y persistencia**

- **FR-014**: Todo cambio del conocimiento del jugador causado por una acción MUST formar parte de esa acción en la línea de tiempo (§3.6), de modo que un pergamino de retroceso que deshace la acción MUST devolver el conocimiento (estados de sala y puertas recordadas) exactamente al estado anterior, incluidas las salas exploradas por la antorcha.
- **FR-015**: El conocimiento del jugador MUST guardarse en el archivo de partida y restaurarse íntegro al cargarla.
- **FR-016**: Como el formato del archivo de partida cambia, su número de versión de formato MUST incrementarse y el README MUST documentarlo; un archivo con la versión anterior MUST rechazarse según la regla de versión incompatible ya vigente.
- **FR-017**: `--replay` de una bitácora MUST producir el mismo conocimiento final que la partida jugada, incluidas las partidas cargadas y continuadas.

**Mapa conocido (interfaz)**

- **FR-018**: El sistema MUST ofrecer un comando de consulta (por defecto `mapa`) que muestre las salas exploradas, cada una con sus salidas (dirección, destino, costo y estado recordado de la puerta: abierta, cerrada o sin observar), y la lista de salas avistadas.
- **FR-019**: El comando de mapa MUST NOT consumir tiempo, MUST NOT contar como acción y MUST NOT anotarse en la bitácora, igual que los demás comandos de consulta.
- **FR-020**: La ayuda del juego y el README MUST incluir los comandos nuevos (`mapa` e `ir a <sala>`).

**Viaje automático «ir a <sala>»**

- **FR-021**: El sistema MUST ofrecer el comando `ir a <sala>`, donde `<sala>` es el id de la sala destino, que lleva al jugador hasta esa sala mediante una secuencia de movimientos ordinarios.
- **FR-022**: Si el destino no está explorado, no existe, es la sala actual o no hay ruta conocida hacia él, la orden MUST rechazarse con un aviso, sin consumir tiempo y sin anotarse en la bitácora.
- **FR-023**: La ruta MUST calcularse solo con el conocimiento del jugador: puede pasar únicamente por salas exploradas y por salidas que el mapa recuerda abiertas.
- **FR-024**: La ruta elegida MUST minimizar la suma de costos de sus salidas; entre rutas de igual costo MUST elegirse la que da el primer paso hacia la vecina de menor id (el mismo desempate que el cazador).
- **FR-025**: Cada paso del viaje MUST ser una acción completa del jugador, equivalente a un `mover` por la salida correspondiente: consume el mismo tiempo, cuenta como acción y, entre paso y paso, ocurren todos los eventos del reloj (enemigos, efectos, cierres de puertas, rearmes de trampas).
- **FR-026**: Antes de cada paso la ruta MUST recalcularse con el conocimiento vigente; si al llegar a una sala el jugador observó que una puerta de la ruta está cerrada, el siguiente cálculo MUST evitarla.
- **FR-027**: El viaje MUST detenerse cuando ocurra cualquiera de estas condiciones, y MUST informar al jugador del motivo:
  - (a) llega al destino;
  - (b) entra a una sala con enemigos vivos, activos o dormidos (los dormidos se activan según §2.4);
  - (c) el jugador pierde vida durante el paso, por cualquier causa (ataques, trampas, veneno, incluido un veneno que ya estaba activo antes de dar la orden);
  - (d) deja de existir una ruta conocida hacia el destino (sin consumir tiempo adicional);
  - (e) la partida termina (victoria o derrota).
- **FR-028**: La orden «ir a» MUST aceptarse aunque la sala actual tenga enemigos (activos o dormidos): la condición de parada (b) solo se evalúa al *entrar* a una sala, no en la sala de partida.
- **FR-029**: El viaje MUST NOT abrir puertas, aunque el jugador tenga la llave.
- **FR-030**: En la bitácora, cada paso del viaje MUST anotarse como un movimiento individual, y la orden `ir a <sala>` MUST anotarse además como una línea de comentario antes del primer paso; `--replay` MUST ignorar los comentarios y reproducir solo los movimientos. Si el formato de la bitácora cambia para admitir comentarios, su versión MUST incrementarse y documentarse en el README.
- **FR-031**: Un pergamino de retroceso usado después de un viaje MUST deshacer solo el último paso del viaje (no el viaje entero), y el viaje MUST NOT reanudarse.

### Key Entities *(include if feature involves data)*

- **Conocimiento del jugador (mapa conocido)**: lo que el jugador sabe de la cripta. Para cada sala, su estado (explorada, avistada o desconocida); para las exploradas, nombre, salidas con destino y costo, y estado recordado de cada puerta. Es parte del estado de la partida: se guarda, se carga y se revierte.
- **Puerta recordada**: el estado (abierta/cerrada) de una puerta según la última vez que el jugador la observó; puede diferir del estado real.
- **Viaje «ir a»**: una orden del jugador con un destino; se ejecuta como una sucesión de movimientos ordinarios y termina con un motivo de parada. No persiste: no se guarda ni se reanuda.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Los 6 casos de «Niebla de guerra e ir a» del Apéndice B y los 3 adicionales (sala inicial en el instante 0, paso de avistada a explorada, guardar y cargar con conocimiento) tienen cada uno al menos una prueba automatizada o un `partida.log` de evidencia que cita su FR, y todos pasan.
- **SC-002**: En el 100 % de las pruebas, la salida del comando de mapa y las rutas de «ir a» no incluyen ninguna sala desconocida ni ningún estado de puerta no observado.
- **SC-003**: Tras guardar y cargar, el mapa conocido es idéntico al previo en el 100 % de los casos probados.
- **SC-004**: El `--replay` de una partida que usó «ir a» y pergaminos reproduce exactamente el mismo reloj final, posición y conocimiento.
- **SC-005**: Una orden «ir a» rechazada nunca cambia el reloj, el contador de acciones ni la bitácora.
- **SC-006**: La suite completa de pruebas sigue al 100 % en verde, sin red, incluidas las pruebas de la Parte I.

## Assumptions

- El destino de «ir a» se identifica por el id de la sala, el mismo que la pantalla muestra en «Sala N»; los nombres de sala pueden repetirse y no se usan para identificar el destino.
- El nombre del comando de consulta es `mapa`; puede ajustarse en el plan sin cambiar los requisitos.
- Mientras el jugador permanece en una sala (por ejemplo, con `esperar`), observa continuamente las puertas de esa sala; un cierre automático ocurrido en ese tiempo se refleja de inmediato en su mapa.
- «Enemigos» en la condición de parada se refiere a enemigos vivos; una sala solo con enemigos derrotados no detiene el viaje.
- Usar la antorcha no cambia el conocimiento por sí sola; el efecto ocurre al entrar a una sala mientras está encendida. Como la antorcha no se guarda (Parte I), tras cargar una partida está apagada, pero el conocimiento ganado con ella sí se conserva.
- Como el historial de retroceso no se guarda (Parte I), tras cargar no se puede revertir conocimiento ganado antes del guardado.
- El viaje es un único comando no interactivo: el jugador no puede intervenir entre pasos; el pergamino solo puede usarse después de que el viaje termine o se detenga.
- En la Parte I las salidas no tienen costo propio: todo `mover` cuesta 100. Esta capacidad asume que el costo de cada salida lo define la Parte II (dato de la cripta tratado en otra capacidad) y que el movimiento ordinario ya lo usa; mientras una salida no traiga costo propio, su costo es el de `mover` (100). Esta capacidad no define ni modifica costos: solo los muestra y los usa para elegir la ruta.
- Depende de: motor de simulación y agenda de eventos, pergamino de retroceso, antorcha, puertas con cierre automático, archivo de partida y bitácora de la Parte I.
