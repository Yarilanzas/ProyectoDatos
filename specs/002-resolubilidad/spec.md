# Feature Specification: Verificación de resolubilidad de una cripta

**Feature Branch**: `main` (el grupo trabaja directamente sobre `main`, constitución v3.0.2)

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "Como usuario quiero saber si una cripta es resoluble. Una cripta es resoluble si, partiendo de la sala inicial, el jugador puede obtener la llave de la salida (llave_salida) y llegar a la sala de salida (sala_salida) a través de una puerta que la requiere. Para decidirlo se asume que: el jugador puede atravesar cualquier salida abierta y cualquier salida cerrada cuya llave ya obtuvo; las llaves no se consumen; todo enemigo puede ser derrotado; una llave que suelta un enemigo se considera obtenible en la sala donde ese enemigo inicia; y las trampas y los cierres automáticos no bloquean, porque una puerta puede volver a abrirse con la misma llave. El programa siempre verifica si una cripta es resoluble al momento de iniciar una partida. Mediante las banderas --verificar <cripta> que muestra al usuario si si puede resuelta la crippta (ejecutando únicamente la verificación, sin iniciar la partida) y en caso de saber que no es resoluble poder jugar en esa cripta con la bandera --forzar. En caso de que una cripta no sea resoluble y no se use la manera --forzar la partida no inicia y se me muestra el reporte de por que no es resoluble(la frontera bloqueada y las dependencias entre llaves. ) si una cripta ya me dio su orden de resolubilidad o no resoubilidad entonces si vuelvo a correr la misma cripta deberia de mostrarme el mismo orden. Esto se cumple siempre: la misma cripta produce el mismo orden de llaves y el mismo reporte, con el mismo ciclo señalado, en cada ejecución. En caso de ser resoluble mostrara un mensaje diciendo un orden de obtención de llaves en el que cada llave aparece después de todas las llaves necesarias para alcanzarla, en caso de no serlo se muestran as llaves que no pueden obtenerse; las puertas de la frontera bloqueada, es decir, las puertas cerradas adyacentes a la región alcanzable, con la llave que requiere cada una; y dónde se encuentra cada una de esas llaves. Si una llave está ubicada detrás de puertas que solo ella abre, directamente o mediante una cadena de llaves, el reporte debe señalar ese ciclo. Si se usa --forzar por si solo deberá iniciar la partida omitiendo el reporte. Si no se puede obtener la ubicación de las llaves (por un error del servicio o porque se agotó el presupuesto de solicitudes), el programa informa el motivo y no inicia la partida. La verificación tarda menos de 200 ms en la cripta publicada más grande, y su costo crece aproximadamente de forma lineal con la cantidad de salas, salidas y llaves."

## Contexto y alcance

Hoy una partida puede empezar en una cripta imposible de ganar y el jugador solo lo descubre después 
de explorarla. Esta capacidad decide de antemano si la cripta puede resolverse, 
explica por qué no cuando no se puede, y le deja al usuario la decisión de jugarla de todos modos.

La verificación razona sobre la cripta completa (salas, salidas y ubicación de las llaves). 
Es un análisis previo: no forma parte de la simulación ni del conocimiento del jugador 
de la niebla de guerra (capacidad 001).

**Fuera de alcance**: comprobar que el jugador tenga fuerza suficiente para ganar los combates o 
sobrevivir a las trampas, calcular una ruta sala por sala, verificar partidas cargadas o reproducidas, 
y mostrar una solución durante la partida.

## Clarifications

### Session 2026-11-07

- Q: ¿Cuándo se dice que una llave no obtenible K «depende» de la llave J? → A: Puertas más cercanas: K → J si todas las puertas bloqueadas que entran a la zona de K (salas desde las que se llega a K sin cruzar otra puerta bloqueada) piden J, en todas sus ubicaciones; si piden llaves distintas o alguna no indica llave, K no depende de ninguna.
- Q: Cuando hay varias llaves obtenibles a la vez, ¿cómo se arma el orden de obtención? → A: Por oleadas: primero todas las obtenibles sin abrir puertas, luego todas las que se vuelven obtenibles con las anteriores, y así sucesivamente; dentro de cada oleada, por identificador.

## Definiciones

- **Salida**: conexión dirigida de una sala origen a una sala destino. Que A→B esté cerrada no dice nada 
de B→A.
- **Región alcanzable**: salas a las que se llega desde la sala inicial atravesando salidas abiertas 
y salidas cerradas cuya llave ya se obtuvo, repitiendo hasta que no se pueda obtener ninguna llave más.
- **Llave obtenible**: llave con al menos una ubicación dentro de la región alcanzable. 
Si la suelta un enemigo, su ubicación es la sala donde ese enemigo inicia.
- **Cripta resoluble**: `llave_salida` es obtenible y existe una salida cuyo origen está en la 
región alcanzable, cuyo destino es `sala_salida` y cuya llave es `llave_salida`.
- **Frontera bloqueada**: salidas cerradas cuyo origen está en la región alcanzable, cuyo destino 
está fuera de ella y cuya llave no es obtenible (o que no indican llave).
- **Puerta bloqueada**: salida cerrada cuyo destino está fuera de la región alcanzable y cuya llave
no es obtenible (o que no indica llave). Su origen puede estar dentro o fuera de la región alcanzable.
- **Puerta de salida no atravesable**: salida cuyo destino es `sala_salida`, cuya llave es `llave_salida`
y que no se puede cruzar, porque su origen está fuera de la región alcanzable o porque `llave_salida` no es
obtenible. A diferencia de la puerta bloqueada, su destino puede estar dentro de la región alcanzable.
- **Zona de una sala no alcanzable**: salas fuera de la región alcanzable desde las que se llega a ella
sin cruzar ninguna puerta bloqueada.
- **Dependencia entre llaves**: la llave no obtenible K depende de la llave J cuando todas las puertas
bloqueadas que entran a la zona de cada ubicación de K piden J. Se escribe K → J. Si esas puertas piden
llaves distintas, o alguna no indica llave, K no depende de ninguna llave. Por eso cada llave depende
como mucho de una, y los ciclos no comparten llaves.
- **Ciclo de llaves**: cadena de dependencias entre llaves no obtenibles que vuelve a su inicio.
Es directo si K depende de sí misma (K → K) y por cadena en otro caso (K → J → K).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar si una cripta es resoluble (Priority: P1)

El usuario ejecuta `--verificar <cripta>` y sabe si la cripta es resoluble,
sin que se inicie ninguna partida. Si lo es, ve un orden de obtención de llaves.

**Why this priority**: es el núcleo de la capacidad; las demás historias reutilizan este veredicto.

**Independent Test**: con paquetes offline de prueba, una cripta resoluble y otra no, ejecutar 
`--verificar` y comprobar el veredicto, el orden y que no se creó ni modificó ningún archivo de partida.

**Acceptance Scenarios**:

1. **Given** una cripta donde `llave_salida` está en una sala alcanzable sin abrir puertas y 
la puerta que la requiere lleva a `sala_salida`, **When** se ejecuta `--verificar`,
**Then** se informa que es resoluble, se muestra el orden de llaves y el programa termina con código 0
sin iniciar la partida.
2. **Given** una cripta donde A abre la puerta hacia la sala de B y B abre la puerta hacia la sala de
`llave_salida`, **When** se ejecuta `--verificar`, **Then** el orden muestra A antes que B y B antes que 
`llave_salida`.
3. **Given** una cripta donde una llave necesaria la suelta un enemigo errante que inicia en una sala alcanzable,
**When** se ejecuta `--verificar`, **Then** esa llave cuenta como obtenible sin evaluar si el jugador 
puede ganar el combate.
4. **Given** una cripta con trampas y puertas con cierre automático en la ruta, **When** se ejecuta
`--verificar`, **Then** ni unas ni otras cambian el veredicto.
5. **Given** una cripta cualquiera, **When** se ejecuta `--verificar` dos veces, **Then** la salida es
idéntica carácter por carácter.
6. **Given** una cripta donde `sala_salida` se alcanza por una salida abierta pero ninguna puerta hacia
ella requiere `llave_salida`, **When** se ejecuta `--verificar`, **Then** se informa que no es resoluble 
y el reporte indica que no existe esa puerta.

---

### User Story 2 - Entender por qué una cripta no es resoluble (Priority: P1)

Cuando la cripta no es resoluble, el usuario recibe un reporte que dice qué llaves no pueden obtenerse,
qué puertas bloquean el avance, dónde están esas llaves y si alguna quedó encerrada en un ciclo.

**Why this priority**: sin la explicación, el veredicto negativo no le dice al usuario nada que pueda usar.

**Independent Test**: con criptas de prueba construidas para cada causa de bloqueo, comparar el reporte
con el contenido esperado.

**Acceptance Scenarios**:

1. **Given** una cripta no resoluble, **When** se ejecuta `--verificar`, **Then** el reporte lista 
las llaves no obtenibles; cada puerta de la frontera bloqueada con su origen, destino y llave; 
la ubicación de cada una de esas llaves (sala, y enemigo si la suelta uno); y las dependencias 
entre llaves. El programa termina con código 0.
2. **Given** una llave K cuya única sala está detrás de una puerta que requiere K,
**When** se genera el reporte, **Then** se señala el ciclo directo K → K.
3. **Given** K1 detrás de una puerta que requiere K2 y K2 detrás de una puerta que requiere K1, 
**When** se genera el reporte, **Then** se señala el ciclo K1 → K2 → K1.
4. **Given** K detrás de dos puertas alternativas, una con K y otra con J, y J no obtenible
porque no tiene ubicación, **When** se genera el reporte, **Then** no se señala ningún ciclo, 
porque las puertas que llevan a K piden llaves distintas.
5. **Given** una llave requerida que no aparece en la ubicación de llaves, 
**When** se genera el reporte, **Then** esa llave figura como no obtenible con ubicación desconocida.
6. **Given** una cripta no resoluble con ciclos, **When** se genera el reporte varias veces,
**Then** se señalan siempre los mismos ciclos, en el mismo orden y empezando por la misma llave.

---

### User Story 3 - Impedir partidas imposibles al iniciar (Priority: P2)

Al iniciar una partida nueva, el programa siempre verifica la cripta. Si no es resoluble,
la partida no inicia y el usuario ve el reporte.

**Why this priority**: evita que el jugador invierta tiempo en una partida que no puede ganar, 
sin que tenga que acordarse de verificarla.

**Independent Test**: iniciar una partida nueva en una cripta no resoluble y comprobar el reporte,
el código de salida y que no se creó bitácora; repetir con una resoluble y comprobar que la partida inicia.

**Acceptance Scenarios**:

1. **Given** una cripta no resoluble, **When** se inicia una partida nueva sin `--forzar`,
**Then** se muestra el mensaje de error y el reporte de la Historia 2, la partida no inicia,
no se crea ni modifica la bitácora ni la tabla de puntajes, y el programa termina con código 1.
2. **Given** una cripta resoluble, **When** se inicia una partida nueva,
**Then** se muestra el orden de llaves y la partida inicia con normalidad.
3. **Given** la cripta se eligió de la lista interactiva, **When** se confirma la elección, 
**Then** se verifica igual que con `--cripta`.
4. **Given** misma cripta y misma semilla, **When** se juega con las mismas acciones habiendo 
pasado por la verificación, **Then** la partida es idéntica: la verificación no consume tiempo virtual
ni aleatoriedad y no se anota en la bitácora.

---

### User Story 4 - Jugar de todos modos con `--forzar` (Priority: P2)

El usuario, sabiendo que la cripta no es resoluble, decide jugarla con `--forzar`.

**Why this priority**: conserva el acceso a criptas no resolubles, útil para explorarlas o probarlas.

**Independent Test**: iniciar con `--forzar` una cripta no resoluble y comprobar que la partida inicia sin reporte.

**Acceptance Scenarios**:

1. **Given** una cripta no resoluble, **When** se inicia una partida con `--forzar`, **Then** 
la partida inicia y no se muestra el reporte.
2. **Given** una cripta resoluble, **When** se inicia una partida con `--forzar`, 
**Then** la partida inicia y no se muestra ni el reporte ni el orden de llaves.
3. **Given** `--verificar <cripta> --forzar`, **When** se ejecuta, 
**Then** solo se verifica: se muestra el resultado completo y no inicia ninguna partida.
4. **Given** una partida forzada guardada, o su bitácora,
**When** se usa `--cargar` o `--replay` sin `--forzar`, **Then** funciona normalmente, sin verificación.

---

### User Story 5 - Fallo al obtener la ubicación de las llaves (Priority: P3)

Si el programa no puede obtener la ubicación de las llaves, informa el motivo y no inicia la partida: 
no da un veredicto que no pudo comprobar.

**Why this priority**: es un camino de error poco frecuente, pero sin él se podría dar un veredicto falso.

**Independent Test**: con una fuente que falla o con el presupuesto agotado, comprobar el motivo, el código de salida y que la partida no inició.

**Acceptance Scenarios**:

1. **Given** el servicio responde con un error al pedir la ubicación de las llaves, 
**When** se ejecuta `--verificar` o se inicia una partida (con o sin `--forzar`), 
**Then** se muestra `! Error: ...` con el motivo, no se emite veredicto, la partida no inicia y el código de salida es 1.
2. **Given** el presupuesto de solicitudes está agotado, **When** se necesita 
la ubicación de las llaves, **Then** se muestra `! Error: Se agotó el presupuesto de solicitudes ...`, 
no se hace la solicitud, la partida no inicia y el código de salida es 1.
3. **Given** `--offline` con un paquete sin el archivo de ubicación de llaves, 
**When** se ejecuta `--verificar` o se inicia una partida, **Then** se informa 
cuál es el archivo que falta, la partida no inicia y el código de salida es 1.

---

### Edge Cases

- **Puerta cerrada sin llave indicada**: nunca se puede atravesar; en la frontera aparece como «sin llave», no provoca un fallo.
- **Frontera vacía**: si la cripta no es resoluble y no hay puertas en la frontera (por ejemplo, salas desconectadas), el reporte lo dice de forma explícita y muestra de todos modos las llaves no obtenibles y sus ubicaciones.
- **`sala_salida` alcanzable, pero sin poder cruzar su puerta**: cada puerta de salida no atravesable se incluye en el reporte aunque su destino ya sea alcanzable por otra ruta.
- **Puerta cerrada entre dos salas alcanzables**: no está en la frontera, porque no bloquea el acceso a ninguna sala nueva.
- **Una llave en varias ubicaciones**: es obtenible si cualquiera es alcanzable; el reporte lista todas.
- **Ubicación en una sala inexistente, o salida hacia una sala inexistente**: no aporta alcance; una llave con una ubicación así se reporta con esa ubicación y como no obtenible si no tiene otra válida. No detiene la verificación.
- **Llaves prescindibles en una cripta resoluble**: el orden lista todas las llaves obtenibles, aunque no sean necesarias para salir; las no obtenibles no se mencionan, porque el reporte solo se muestra si la cripta no es resoluble.
- **Llave más allá de `sala_salida`**: `sala_salida` se atraviesa como cualquier otra sala durante el análisis.
- **`sala_inicial` igual a `sala_salida`**: aplica la misma regla; sigue haciendo falta una puerta hacia `sala_salida` que requiera `llave_salida`.
- **`--verificar` con una cripta inexistente**: `! Error: ...` y código de salida 1.
- **`--forzar` con `--cargar` o `--replay`**: se ignora, porque esos modos no inician una partida nueva.
- **Los datos cambian en el servicio**: una versión distinta de la cripta es otra cripta y puede dar otro resultado.
- **La cripta no declara `llave_salida`**: es resoluble si `sala_salida` es alcanzable desde `sala_inicial`; el orden lista las llaves obtenibles como en cualquier cripta resoluble.

## Requirements *(mandatory)*

### Functional Requirements

**Decisión de resolubilidad**

- **FR-001**: El sistema MUST determinar si una cripta es resoluble según la definición de esta especificación, partiendo de `sala_inicial` y usando las salidas, las llaves que requieren y las ubicaciones de las llaves.
- **FR-002**: La decisión MUST asumir que el jugador atraviesa cualquier salida abierta y cualquier salida cerrada cuya llave ya obtuvo, y que las llaves no se consumen.
- **FR-003**: La decisión MUST asumir que todo enemigo puede ser derrotado y considerar la llave que suelta un enemigo como obtenible en la sala donde ese enemigo inicia.
- **FR-004**: Las trampas y los cierres automáticos MUST NOT influir en la decisión.
- **FR-005**: La decisión MUST respetar la dirección de las salidas: una salida se atraviesa solo de su origen a su destino.

**Resultado cuando es resoluble**

- **FR-006**: Si la cripta es resoluble, el sistema MUST mostrar un mensaje que lo indique y un orden de obtención con todas las llaves obtenibles, señalando cuál es `llave_salida`.
- **FR-007**: En el orden, cada llave MUST ser obtenible usando únicamente las llaves que la preceden, de modo que aparezca después de todas las necesarias para alcanzarla. El orden MUST armarse por oleadas: la oleada 1 son las llaves obtenibles sin abrir ninguna puerta cerrada; la oleada n+1, las que se vuelven obtenibles con las llaves de las oleadas 1 a n. Dentro de cada oleada, las llaves MUST ordenarse por identificador. Ejemplo: si desde el inicio se alcanzan C y D, y C abre la sala de A, el orden es `C, D, A`.

**Reporte cuando no es resoluble**

- **FR-008**: Si la cripta no es resoluble, el sistema MUST mostrar un reporte con las llaves no obtenibles y las dependencias entre llaves.
- **FR-009**: El reporte MUST listar cada puerta de la frontera bloqueada con su sala de origen, su sala de destino y la llave que requiere, e indicar de forma explícita si la frontera está vacía. También MUST incluir cada puerta de salida no atravesable (ver Definiciones), con su origen, dirección y destino, e indicar de forma explícita si no existe ninguna salida hacia `sala_salida` que requiera `llave_salida`.
- **FR-010**: El reporte MUST indicar dónde se encuentra cada llave no obtenible y cada llave de la frontera: sala, enemigo que la suelta si aplica, o «ubicación desconocida».
- **FR-011**: Si existen ciclos de llaves, el reporte MUST señalarlos, tanto directos como por cadena. Como cada llave depende como mucho de otra (ver Definiciones), cada llave que pertenezca a un ciclo MUST aparecer en exactamente un ciclo señalado, y las llaves sin dependencia MUST mostrarse como tales.

**Determinismo**

- **FR-012**: La misma cripta en la misma versión MUST producir siempre el mismo veredicto, el mismo orden de llaves y el mismo reporte, con los mismos ciclos, carácter por carácter.
- **FR-013**: El resultado MUST NOT depender de la semilla, del estado de la caché, de usar red u `--offline` con los mismos datos, ni del orden en que la fuente entregue salas, salidas o llaves.
- **FR-014**: Las listas del reporte MUST tener un orden fijo: llaves por identificador; puertas por sala de origen y luego por dirección en el orden N, S, E, O; ubicaciones por sala; cada ciclo empezando por su llave de menor identificador, y los ciclos ordenados por esa llave.

**Modo `--verificar`**

- **FR-015**: `--verificar <cripta>` MUST ejecutar únicamente la verificación y mostrar su resultado, sin iniciar una partida ni crear o modificar bitácoras, partidas guardadas o la tabla de puntajes.
- **FR-016**: `--verificar` MUST terminar con código 0 siempre que la verificación se complete, sea cual sea el veredicto.
- **FR-017**: `--verificar` MUST tener prioridad sobre `--replay`, `--cargar`, `--cripta` y `--forzar`, y quedar por debajo de `--bench` y `--mostrar-puntajes`.

**Inicio de partida**

- **FR-018**: Toda partida nueva, elegida con `--cripta` o desde la lista, MUST verificarse antes de iniciar, aunque se use `--forzar`.
- **FR-019**: Si la cripta es resoluble y no se usa `--forzar`, el sistema MUST mostrar el resultado de FR-006 e iniciar la partida.
- **FR-020**: Si la cripta no es resoluble y no se usa `--forzar`, la partida MUST NOT iniciar; el sistema MUST mostrar un mensaje `! Error: ...` y el reporte, terminar con código 1 y no crear ni modificar bitácoras ni la tabla de puntajes.
- **FR-021**: Con `--forzar` y sin `--verificar`, la partida MUST iniciar sin mostrar el reporte ni el orden de llaves, sea cual sea el veredicto.
- **FR-022**: `--cargar` y `--replay` MUST NOT ejecutar la verificación ni exigir `--forzar`, y MUST ignorar esta opción.
- **FR-023**: La verificación MUST NOT consumir tiempo virtual ni aleatoriedad de la partida, MUST NOT anotarse en la bitácora y MUST NOT alterar el conocimiento del jugador.

**Fallos al obtener datos**

- **FR-024**: Si no se puede obtener la ubicación de las llaves, por un error del servicio, por agotarse el presupuesto o por faltar el dato en el paquete offline, el sistema MUST informar el motivo con `! Error: ...`, no emitir veredicto, no iniciar la partida y terminar con código 1, también con `--forzar`.
- **FR-025**: Un fallo al obtener los demás datos necesarios para verificar (datos generales de la cripta o sus salas) MUST tratarse igual que en FR-024.
- **FR-026**: Las solicitudes de la verificación MUST contar para `presupuesto_solicitudes` y MUST NOT superarlo en ningún caso, incluidos los reintentos.
- **FR-027**: *(Retirado durante la revisión de la spec; el identificador no se reutiliza.)*
- **FR-028**: La ubicación de las llaves MUST obtenerse por la misma interfaz con red y con `--offline`. El formato del paquete offline MUST incorporar este dato y documentarse en el README.

**Rendimiento y documentación**

- **FR-029**: La verificación, una vez obtenidos los datos, MUST tardar menos de 200 ms en una cripta del tamaño de la publicada más grande, y su costo MUST crecer aproximadamente de forma lineal con la cantidad de salas, salidas y llaves. Excepción aceptada: el cálculo de dependencias del reporte de una cripta no resoluble tiene peor caso O(L·(S + E)), donde L es la cantidad de ubicaciones de llaves; se documenta como límite conocido y M3 lo vigila.
- **FR-030**: `--bench` MUST incluir las mediciones que respaldan FR-029.
- **FR-031**: El README MUST documentar `--verificar` y `--forzar`, la nueva prioridad de opciones, los códigos de salida de este modo y el archivo de llaves del paquete offline.

### Key Entities

- **Ubicación de llave**: identificador de la llave, sala donde se encuentra y, si la suelta un enemigo, ese enemigo. Una llave puede tener varias.
- **Resultado de verificación**: veredicto (resoluble o no) con el orden de llaves o el reporte, según corresponda. No se guarda en la partida.
- **Orden de llaves**: secuencia de llaves obtenibles que cumple FR-007.
- **Reporte de no resolubilidad**: llaves no obtenibles, frontera bloqueada, ubicaciones, dependencias y ciclos.
- **Puerta de frontera**: sala de origen, dirección, sala de destino y llave requerida (o «sin llave»).
- **Ciclo de llaves**: secuencia de llaves cuyas dependencias vuelven a la primera.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El veredicto es correcto en el 100 % de las criptas de prueba, que cubren cada escenario de aceptación y caso límite de esta especificación.
- **SC-002**: En todas las criptas de prueba resolubles, seguir el orden mostrado permite obtener cada llave usando solo las anteriores.
- **SC-003**: 100 ejecuciones sobre la misma cripta, incluidas variantes con salas, salidas y llaves entregadas en otro orden, producen una salida idéntica carácter por carácter.
- **SC-004**: La verificación tarda menos de 200 ms en una cripta al menos tan grande como la publicada más grande, sin contar la obtención de datos, medido con `python main.py --bench`.
- **SC-005**: Al duplicar a la vez salas, salidas y llaves en criptas sintéticas, el tiempo medido con `--bench` se multiplica por 2,5 como máximo en cada duplicación, tanto en el caso resoluble como en el no resoluble con reporte. Queda fuera el peor caso del cálculo de dependencias que FR-029 acepta como excepción (zonas de distintas ubicaciones de llaves que se solapan): las criptas sintéticas de esta medición no lo producen, y si se mide se informa aparte, sin aplicarle el límite.
- **SC-006**: En el 100 % de los intentos sin `--forzar` sobre criptas no resolubles, y de los fallos al obtener la ubicación de las llaves, no inicia ninguna partida ni cambia ningún archivo de partida, bitácora o puntajes.
- **SC-007**: Una partida con misma cripta, semilla y acciones genera la misma bitácora y el mismo estado final, con verificación y sin ella.
- **SC-008**: Con cualquier presupuesto, la cantidad de solicitudes realizadas nunca supera el presupuesto de la cripta.
- **SC-009**: El reporte de una cripta no resoluble basta por sí solo para señalar qué puerta bloquea el avance, qué llave falta y dónde está: cada puerta de la frontera aparece con origen, dirección, destino y llave, y cada una de esas llaves aparece en «Ubicación de las llaves» con su sala, su enemigo o «ubicación desconocida».

## Assumptions

- **`--forzar` no evita la verificación**: omite el reporte y el rechazo, pero la verificación se sigue ejecutando («siempre verifica»), así que un fallo al obtener la ubicación de las llaves también impide iniciar con `--forzar`.
- **`--verificar` con `--forzar`**: se entiende que «`--forzar` por sí solo» significa sin `--verificar`; combinados, prevalece «únicamente la verificación» y no inicia ninguna partida.
- **Resultado al iniciar una partida resoluble**: se muestra el orden de llaves, que solo contiene identificadores de llaves, sin salas ni rutas. No se considera una violación de la niebla de guerra, porque se muestra antes de la partida y no es parte del conocimiento del jugador.
- **Códigos de salida**: no se crean códigos nuevos. Un veredicto negativo de `--verificar` es un resultado normal (0) y el rechazo a iniciar una partida es un error (1).
- **Partidas cargadas y reproducidas**: «iniciar una partida» se refiere solo a partidas nuevas. `--cargar` continúa una ya iniciada y `--replay` debe reproducir cualquier partida existente, incluidas las forzadas.
- **Inventario**: su capacidad no bloquea la obtención de llaves, porque el jugador puede soltar objetos.
- **Medición de los 200 ms**: el límite no incluye la obtención de datos, cuya duración depende de la red y de los reintentos.
- **Fuente de las ubicaciones**: el servicio ofrece la ubicación de las llaves de cada cripta (`GET /criptas/<id>/llaves`: `id` de la llave, `sala` y `enemigo` opcional). Los paquetes offline actuales no incluyen este archivo y deben actualizarse, porque sin él ninguna partida nueva offline podrá iniciar (FR-024). Esto incluye los paquetes temporales de las pruebas automatizadas existentes.
- **Restricciones de la constitución**: los recorridos y las estructuras de esta capacidad se implementan a mano (Principio I), la decisión vive en el modelo, sin red ni consola (Principio II), y ningún dato de una cripta concreta va en el código de producción (Principio IV).
