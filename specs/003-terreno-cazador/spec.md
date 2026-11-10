# Feature Specification: Terreno, cazador e invalidación de rutas

**Feature Branch**: `main` (el grupo trabaja directamente sobre `main`, constitución v3.0.2)

**Created**: 2026-11-09

**Status**: Draft

**Input**: Enunciado Parte II §3.1 (terreno: costo de las salidas), §3.2 (enemigo cazador), §6.1 (rendimiento) y casos de «Terreno y cazador» del Apéndice B. Cada salida tiene un costo que determina cuánto tarda cualquier actor en atravesarla; aparece un nuevo enemigo, el cazador, que persigue al jugador por la ruta más barata dentro de su rango y que siempre decide como si calculara la ruta desde cero.

## Contexto y alcance

En la Parte I todas las salidas eran iguales: moverse siempre costaba 100. Con el **terreno**, cada salida tiene su propio costo (un pasillo corto, una escalera larga, un túnel inundado), y ese costo es el tiempo base de atravesarla, para el jugador y para todos los enemigos. Sobre ese terreno aparece el **cazador**, un enemigo que conoce la cripta entera y persigue al jugador por la ruta más barata, pero solo si el jugador está lo bastante cerca en costo.

**Comportamiento de la Parte I que se respeta** (no cambia):

- El intervalo de una acción es `max(1, costo_base × 100 // velocidad)` (P1).
- Atacar, esperar, usar objetos y las demás acciones que no son moverse por una salida conservan su costo base.
- Los enemigos guardianes, errantes y rastreadores conservan su forma de decidir; solo cambia el tiempo que tarda su movimiento cuando lo hacen (FR-006).
- Un cambio de velocidad durante una acción en curso escala el tiempo que le falta: `restante_nuevo = max(1, restante × velocidad_anterior // velocidad_nueva)` (P1 §2.3).
- Todo enemigo que comparte sala con el jugador lo ataca en su turno.
- Un comando rechazado muestra un aviso, no consume tiempo y no se anota en la bitácora (Constitución III).

**Relación con otras capacidades**:

- La capacidad 001 (niebla e «ir a») ya muestra el costo de cada salida y elige rutas por costo, leyendo «100 si la salida no trae el dato» (001, Suposiciones). Esta capacidad es la que hace que ese costo exista en los datos de la cripta, en la caché y en el paquete offline, y la que hace que atravesar una salida tarde lo que indica su costo (001 FR-024 usa el mismo desempate por menor id que el cazador).
- La capacidad 004 (línea de tiempo) reconstruye estados pasados; las decisiones del cazador en un estado reconstruido deben ser las mismas que tuvo en la partida (FR-025).

## Definiciones

- **Costo de una salida**: entero ≥ 1 en unidades de tiempo base; 100 si la cripta no lo declara. Según el enunciado §3.1 es el mismo en ambos sentidos; esa es una regla sobre los datos de la cripta que el programa no valida: cada actor usa el costo de la salida que atraviesa.
- **Salida abierta**: salida cuya puerta no está cerrada en ese instante (las salidas sin puerta siempre están abiertas).
- **Costo de una ruta**: suma de los costos de las salidas que la forman.
- **Distancia d(u, x)**: costo mínimo de una ruta desde la sala u hasta la sala x usando solo salidas abiertas en ese instante; «sin ruta» si no existe ninguna.
- **costo(u, v)**: el menor costo entre las salidas abiertas que van de u a la vecina v.
- **Rango del cazador**: entero ≥ 0, en unidades de costo; es la máxima distancia a la que el cazador persigue al jugador.
- **Decisión del cazador**: lo que hace en un turno (atacar, esperar, o moverse a una vecina concreta por una salida concreta) y el costo de esa acción.

## Clarifications

### Session 2026-11-09

- Q: ¿Qué se hace ante un costo de salida inválido (0, negativo o no entero)? → A: La cripta se rechaza con un mensaje claro; no se asume ningún valor (FR-001).
- Q: ¿Qué se hace si los dos sentidos de una misma conexión declaran costos distintos (incluido uno declarado y el otro ausente)? → A: Se usa el costo de la salida que se atraviesa y no se valida simetría; queda como supuesto sobre los datos del servicio (FR-001, Assumptions).
- Q: ¿Qué se hace si a un cazador le falta el rango, o si es negativo o no entero? → A: La cripta se rechaza con un mensaje claro (FR-009).
- Q: ¿Cómo se comparan los ids de sala en el desempate del cazador? → A: Los ids de sala son opacos y se comparan con el mismo criterio que usa la capacidad 001 en FR-024; si ese criterio cambia, el de esta capacidad cambia igual (FR-014, Assumptions).
- Q: ¿Cuándo se activa un cazador? → A: Como cualquier enemigo, según P1 §2.4: cuando el jugador entra a su sala; una vez activo permanece activo aunque se desplace (FR-034).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - El terreno determina cuánto tarda moverse (Priority: P1)

El jugador ve que algunas salidas son más largas que otras: cruzar un túnel de costo 300 le cuesta el triple que un pasillo de costo 100, y los enemigos que lo cruzan también tardan más. Una salida sin costo declarado se comporta como en la Parte I.

**Why this priority**: es la base de todo lo demás; el cazador y la elección de rutas no tienen sentido sin costos reales.

**Independent Test**: con un paquete offline de prueba con salidas de costos 1, 100 (sin declarar) y 300, mover al jugador y a un enemigo errante por cada una y comprobar en el reloj virtual el instante de su siguiente turno.

**Acceptance Scenarios**:

1. **Given** el jugador con velocidad 100 junto a una salida de costo 300, **When** se mueve por ella, **Then** su siguiente turno ocurre 300 unidades después. *(FR-004, FR-005)*
2. **Given** una salida sin costo declarado, **When** cualquier actor de velocidad 100 la atraviesa, **Then** su siguiente turno ocurre 100 unidades después, igual que en la Parte I. *(FR-002)*
3. **Given** una cripta cuyos datos traen el mismo costo, 250, en ambos sentidos de la conexión entre las salas A y B, **When** un actor la atraviesa de A a B y otro de B a A, ambos con velocidad 100, **Then** los dos tardan 250. *(FR-003)*
4. **Given** un actor de velocidad alta (por ejemplo 1 000) junto a una salida de costo 1, **When** la atraviesa, **Then** su intervalo es 1 y nunca 0. *(Apéndice B: actor de velocidad alta cruza salida de costo 1; FR-005)*
5. **Given** un actor de velocidad 100 que acaba de atravesar una salida de costo 400 en el instante 1 000 (próximo turno en 1 400), **When** en el instante 1 100 su velocidad cambia a 200, **Then** su próximo turno pasa a 1 100 + max(1, 300 × 100 // 200) = 1 250. *(Apéndice B: cambia la velocidad de un actor que cruza una salida costosa; FR-007)*
6. **Given** un enemigo errante o rastreador, **When** decide moverse, **Then** elige su destino exactamente como en la Parte I, y el tiempo hasta su siguiente turno es el de la salida que atravesó. *(FR-006)*
7. **Given** el jugador que ataca, espera o usa un objeto, **When** realiza la acción, **Then** su costo es el mismo que en la Parte I, sin importar los costos de las salidas de la sala. *(FR-005)*

---

### User Story 2 - El cazador persigue por la ruta más barata (Priority: P1)

Un cazador está a varias salas del jugador. En cada turno da un paso por una ruta de costo mínimo hacia la sala del jugador, aunque esa ruta atraviese más salas que otra más cara. Si comparte sala con el jugador, lo ataca.

**Why this priority**: es el núcleo del nuevo comportamiento y concentra la mayoría de los casos del Apéndice B.

**Independent Test**: cripta de prueba con dos rutas hacia el jugador (pocas salas y caras frente a muchas salas y baratas), un cazador con rango suficiente, y comprobar sala a sala por dónde avanza y cuánto tarda cada paso.

**Acceptance Scenarios**:

1. **Given** un cazador en la sala del jugador, **When** le toca actuar, **Then** ataca al jugador con el costo de ataque de la Parte I, sin importar su rango. *(FR-010)*
2. **Given** dos rutas abiertas del cazador al jugador, una de 2 salidas con costo total 500 y otra de 4 salidas con costo total 400, y rango ≥ 400, **When** le toca actuar, **Then** da el primer paso de la ruta de costo 400. *(Apéndice B: menos salas pero mayor costo vs. más salas y menor costo; FR-011, FR-013)*
3. **Given** un cazador en u con dos vecinas v1 y v2 (id de v1 menor que id de v2) tales que costo(u, v1) + d(v1, jugador) = costo(u, v2) + d(v2, jugador) = d(u, jugador), **When** le toca actuar, **Then** se mueve a v1. *(Apéndice B: dos vecinas con rutas de costo mínimo; FR-014)*
4. **Given** un cazador que se mueve un paso por una salida de costo 150 con velocidad 100, **When** termina la acción, **Then** su siguiente turno ocurre 150 unidades después. *(FR-013)*
5. **Given** un cazador cuya distancia al jugador es exactamente igual a su rango, **When** le toca actuar, **Then** se mueve (solo espera si la distancia es mayor que el rango). *(FR-012)*
6. **Given** un cazador que avanza y el jugador que cambia de sala entre dos turnos del cazador, **When** al cazador le vuelve a tocar, **Then** decide con la sala actual del jugador, no con la anterior. *(FR-016)*
7. **Given** un cazador dormido a una distancia del jugador dentro de su rango, y el jugador nunca ha entrado a su sala, **When** pasa el tiempo de la partida, **Then** el cazador no actúa ni se mueve. *(FR-034)*
8. **Given** un cazador que se activó porque el jugador entró a su sala, **When** el jugador sale y queda a una distancia dentro del rango del cazador, **Then** el cazador lo persigue. *(FR-034)*

---

### User Story 3 - El cazador espera cuando no puede o no le conviene perseguir (Priority: P1)

Si el jugador está fuera de su alcance (no hay ruta abierta o la más barata cuesta más que su rango), el cazador no deambula: espera.

**Why this priority**: dos casos obligatorios del Apéndice B y la regla que hace al cazador predecible para el jugador.

**Independent Test**: cripta de prueba con el jugador encerrado tras una puerta cerrada, y otra con el jugador a distancia mayor que el rango; comprobar que el cazador no cambia de sala y que su siguiente turno ocurre según un costo de 100.

**Acceptance Scenarios**:

1. **Given** que todas las rutas del cazador al jugador pasan por alguna puerta cerrada, **When** le toca actuar, **Then** espera con costo 100 y no abre ninguna puerta. *(Apéndice B: sin ruta abierta; FR-012, FR-017)*
2. **Given** que la ruta abierta más barata del cazador al jugador cuesta 600 y su rango es 500, **When** le toca actuar, **Then** espera con costo 100. *(Apéndice B: ruta más barata cuesta más que el rango; FR-012)*
3. **Given** un cazador esperando porque una puerta estaba cerrada, **When** esa puerta se abre y luego le toca actuar, **Then** persigue por la nueva ruta si su costo no supera el rango. *(FR-016)*
4. **Given** un cazador con rango 0 en una sala distinta de la del jugador, **When** le toca actuar, **Then** espera con costo 100. *(FR-012)*

---

### User Story 4 - La decisión siempre es la de calcular desde cero (Priority: P1)

Entre dos turnos de un cazador pueden cambiar las puertas, la sala del jugador o la posición de otros actores. Sea cual sea el cambio, el cazador decide exactamente lo mismo que decidiría si calculara la ruta desde cero en ese instante. Ninguna ruta recordada puede llevarlo por una puerta que ya se cerró.

**Why this priority**: es la «invalidación de rutas» del título y un caso obligatorio del Apéndice B; un cazador que sigue una ruta vieja rompe el determinismo y la equivalencia con la línea de tiempo y el replay.

**Independent Test**: comparar, turno a turno y en partidas con cierres y aperturas de puertas, la decisión del cazador con la de un cálculo de referencia hecho desde cero en el mismo estado.

**Acceptance Scenarios**:

1. **Given** un cazador que en su turno anterior avanzó por una ruta que pasa por la puerta P, **When** P se cierra antes de su siguiente turno, **Then** decide como si calculara desde cero: toma otra ruta de costo mínimo si existe y no supera el rango, o espera con costo 100. *(Apéndice B: una puerta de su ruta se cierra entre dos turnos; FR-016)*
2. **Given** una puerta que se abre entre dos turnos y crea una ruta más barata, **When** al cazador le toca actuar, **Then** sigue la nueva ruta más barata. *(FR-016)*
3. **Given** cualquier partida de prueba con cazadores, **When** se compara cada decisión de cada cazador con la del cálculo de referencia desde cero en el mismo instante, **Then** coinciden en el 100 % de los turnos (acción, sala de destino, salida usada y costo). *(FR-016, SC-003)*
4. **Given** una partida con cazadores guardada y cargada, o reproducida con `--replay`, o retrocedida con un pergamino, **When** los cazadores actúan después, **Then** sus decisiones son idénticas a las de la partida original en el mismo estado. *(FR-024, FR-025)*

---

### User Story 5 - Muchos cazadores sin que el juego se trabe (Priority: P2)

En una cripta grande con decenas de cazadores activos, el juego responde sin demora perceptible entre una orden del jugador y la siguiente.

**Why this priority**: requisito medible de §6.1; la capacidad funciona sin él, pero no se acepta si no lo cumple.

**Independent Test**: con el modo de medición del programa, una cripta del tamaño de la publicada más grande y decenas de cazadores, medir el tiempo de procesar los eventos entre dos decisiones del jugador, con y sin cambios de puertas.

**Acceptance Scenarios**:

1. **Given** la cripta de referencia con 50 cazadores activos, **When** se procesa el ciclo de eventos entre dos decisiones del jugador, **Then** tarda menos de 20 ms. *(FR-030)*
2. **Given** el mismo escenario con puertas que se cierran y abren durante la medición, **When** se mide, **Then** el límite de 20 ms se sigue cumpliendo. *(FR-031)*
3. **Given** criptas sintéticas de tamaños crecientes y un cazador con el mismo rango en todas, **When** se mide con `--bench` el tiempo de decisión del cazador, **Then** con la cripta más grande medida, el tiempo de decisión del cazador no supera 1,5 veces el tiempo con la cripta más pequeña. *(FR-033)*

---

### Edge Cases

- **Jugador y cazador en la misma sala**: el cazador ataca, sin calcular ruta y sin importar su rango (incluido rango 0) (FR-010).
- **Cazador muerto**: no vuelve a actuar ni a decidir; su turno pendiente no se ejecuta; no participa en ningún cálculo de rutas ni en la medición de rendimiento como «activo» (FR-019).
- **Cazador dormido**: no decide, no calcula rutas y no cuenta como activo en la medición de rendimiento (FR-034).
- **Salida con costo ausente**: vale 100 para todo propósito: tiempo de movimiento, distancias del cazador, rutas de «ir a» y lo que muestra el mapa (FR-002).
- **Velocidad cambiada a mitad de un movimiento**: el tiempo restante hasta el siguiente turno se escala según P1 §2.3, igual que con cualquier otra acción; el actor no vuelve a la sala anterior ni repite el movimiento (FR-007).
- **Varios cazadores con el mismo objetivo**: cada uno decide por su cuenta, según su propia sala y su propio rango; pueden terminar en la misma sala; ninguno bloquea el paso de otro; el resultado no depende del orden en que se calculen, salvo por el orden de turnos de la agenda (FR-018).
- **Otros enemigos en la ruta**: la presencia de enemigos, objetos o trampas en una sala no altera la decisión del cazador (FR-015).
- **Puerta cerrada que el cazador podría abrir con una llave que porta**: no la abre ni la usa (FR-017).
- **Varias salidas de u hacia la misma vecina v**: cuenta la abierta de menor costo; si empatan, la primera en el orden N, S, E, O, como en 001 FR-024 (FR-014).
- **Jugador en una sala nunca vista por el cazador ni por el jugador**: la niebla no afecta al cazador; usa el esqueleto completo (FR-015).
- **Ruta que vuelve sobre la sala del cazador o ciclos de costo 1**: la distancia es el costo mínimo; no hay ciclos que mejoren una ruta porque todos los costos son ≥ 1.
- **La distancia supera el rango y la puerta que acortaba la ruta se reabre**: en el turno siguiente vuelve a perseguir (FR-016).
- **Partida terminada (jugador muerto o victoria)**: los cazadores no actúan más.
- **Cazador sin campo rango, o con rango negativo o no entero en los datos**: la cripta se rechaza con un mensaje claro (Clarifications, FR-009).
- **Costo inválido (0, negativo, no entero) o declarado distinto en cada sentido de una misma conexión**: un costo inválido hace que la cripta se rechace con un mensaje claro; si los dos sentidos difieren (incluido uno declarado y el otro ausente), se usa el costo de la salida que se atraviesa, sin validar simetría (Clarifications, FR-001, FR-003).

## Requirements *(mandatory)*

### Functional Requirements

**Terreno**

- **FR-001**: Cada salida de la cripta MUST poder declarar su costo como un entero ≥ 1. Un costo inválido (0, negativo o no entero) MUST hacer que la cripta se rechace con un mensaje claro, sin asumir ningún valor. Si los dos sentidos de una misma conexión declaran costos distintos (incluido uno declarado y el otro ausente), MUST usarse el costo de la salida que se atraviesa, sin validar simetría.
- **FR-002**: Una salida sin costo declarado MUST valer 100 en todos los usos del juego (tiempo de movimiento, distancias del cazador, rutas de «ir a», mapa).
- **FR-003**: El costo de una salida es el mismo en ambos sentidos según el enunciado §3.1; se trata como regla sobre los datos de la cripta (supuesto de datos) y el programa MUST NOT validarla: cada actor MUST usar el costo de la salida que atraviesa (FR-001).
- **FR-004**: Moverse por una salida MUST ser una acción cuyo costo base es el costo de esa salida, para el jugador y para todos los enemigos. Esto incluye cada paso de un viaje «ir a».
- **FR-005**: El intervalo de toda acción MUST ser `max(1, costo_base × 100 // velocidad)`; para moverse, `costo_base` es el costo de la salida. Las acciones que no son moverse por una salida MUST conservar su costo de la Parte I.
- **FR-006**: Los guardianes, errantes y rastreadores MUST elegir qué hacer y a dónde ir exactamente como en la Parte I; solo el tiempo de su movimiento pasa a ser el de la salida atravesada.
- **FR-007**: Un cambio de velocidad mientras un actor espera el fin de un movimiento MUST escalar el tiempo restante según P1 §2.3 (`max(1, restante × velocidad_anterior // velocidad_nueva)`), igual que para cualquier otra acción.
- **FR-008**: El costo de cada salida MUST llegar al juego desde la fuente de datos de la cripta (servicio o paquete `--offline`) y conservarse en la caché en disco; la caché y el paquete offline MUST incrementar su versión de formato y documentarlo en el README (Constitución IV y VI). Una caché o paquete de versión anterior MUST tratarse como incompatible según la regla vigente. Esta capacidad verifica que el costo se conserve en la caché; el cambio de los datos del servicio y de la caché lo implementa la capacidad de datos.

**Cazador**

- **FR-009**: Los datos de un enemigo MUST poder declarar el comportamiento «cazador» con un campo rango, entero ≥ 0 en unidades de costo. Un cazador sin rango, o con rango negativo o no entero, MUST hacer que la cripta se rechace con un mensaje claro.
- **FR-010**: En su turno, si el cazador comparte sala con el jugador, MUST atacarlo con el costo de ataque de la Parte I.
- **FR-011**: Si no comparte sala, el cazador MUST considerar la distancia d desde su sala hasta la sala actual del jugador, sumando el costo de cada salida y usando solo salidas abiertas en ese instante.
- **FR-012**: Si no hay ruta o d > rango, el cazador MUST esperar con costo 100. Si d ≤ rango, MUST moverse (FR-013).
- **FR-013**: Cuando se mueve, el cazador MUST dar exactamente un paso a una vecina por una ruta de costo d, y el costo de esa acción MUST ser el de la salida que atraviesa.
- **FR-014**: Entre las vecinas v tales que costo(u, v) + d(v, jugador) = d, el cazador MUST ir a la de menor id (mismo criterio de comparación de ids que 001 FR-024). Si hay varias salidas abiertas hacia esa vecina, MUST usar la de menor costo y, si empatan, la primera en el orden N, S, E, O.
- **FR-015**: El cazador MUST conocer el esqueleto completo de la cripta y el estado actual de cada puerta; MUST NOT verse afectado por la niebla ni por el conocimiento del jugador; su decisión MUST NOT depender del contenido de ninguna sala (enemigos, objetos, trampas, rastro).
- **FR-016**: Equivalencia observable: la decisión del cazador en cada turno MUST ser idéntica a la que resultaría de calcular la ruta desde cero en ese instante, aunque entre turnos hayan cambiado las puertas, la sala del jugador o la posición de otros actores. Se MAY reutilizar cálculos de turnos anteriores solo si eso nunca cambia ninguna decisión.
- **FR-017**: El cazador MUST NOT abrir puertas cerradas ni usar llaves, aunque las porte.
- **FR-018**: Varios cazadores MUST decidir de forma independiente; la decisión de cada uno MUST depender solo de su sala, su rango, la sala del jugador y el estado de las puertas en su turno. Varios cazadores MAY ocupar la misma sala.
- **FR-019**: Un cazador muerto MUST NOT volver a actuar; su turno pendiente MUST descartarse sin efecto.
- **FR-020**: Los movimientos y ataques del cazador MUST anunciarse al jugador con los mismos mensajes que los de los demás enemigos (por ejemplo, al entrar o salir de la sala del jugador).

**Determinismo, persistencia y consultas**

- **FR-021**: La decisión del cazador MUST ser determinista: misma cripta, misma semilla y mismas acciones MUST producir las mismas decisiones (Constitución III). El cazador MUST NOT consumir azar.
- **FR-022**: Las acciones del cazador y los movimientos con costo de cualquier actor MUST ocurrir en el reloj virtual a través de la agenda de eventos.
- **FR-023**: Los comandos rechazados del jugador MUST NOT alterar el estado que usa el cazador ni sus decisiones.
- **FR-024**: Guardar y cargar una partida, o retroceder con un pergamino, MUST dejar a los cazadores decidiendo exactamente lo mismo que habrían decidido en ese estado en la partida original; ningún cálculo reutilizado MUST sobrevivir a esas operaciones de forma que altere una decisión.
- **FR-025**: `--replay` y la reconstrucción de estados de la línea de tiempo (capacidad 004) MUST reproducir las mismas decisiones de los cazadores que la partida jugada.
- **FR-026**: El mapa (001 FR-018) y las rutas de «ir a» (001 FR-024) MUST usar el costo real de cada salida definido por esta capacidad.
- **FR-034**: Los cazadores MUST seguir las reglas de activación de la Parte I (P1 §2.4): un cazador permanece dormido, sin decidir ni calcular rutas, hasta que el jugador entra a su sala; desde ese momento está activo y su primera acción se programa con costo base 100. Un cazador activo que se desplaza a otra sala permanece activo, sin importar si el jugador ha entrado alguna vez a esa sala.

**Evidencia**

- **FR-027**: Cada uno de los 7 casos de «Terreno y cazador» del Apéndice B MUST tener al menos una prueba automatizada o un `partida.log` de evidencia que cite el FR correspondiente (Constitución V).
- **FR-028**: Las pruebas de equivalencia (FR-016) MUST comparar la decisión del cazador con un cálculo de referencia desde cero en partidas con cierres y aperturas de puertas, cambios de sala del jugador y varios cazadores.
- **FR-029**: La ayuda del juego y el README MUST describir el costo de las salidas y el comportamiento del cazador.

### Requisitos de rendimiento

- **FR-030**: Con la cripta de referencia (la publicada más grande) y 50 cazadores activos, procesar el ciclo de eventos entre dos decisiones del jugador MUST tardar menos de 20 ms (§6.1). Para la medición, los 50 cazadores deben estar activados.
- **FR-031**: El límite de FR-030 MUST cumplirse en los dos escenarios del bench: puertas que cambian con frecuencia (se cierran o abren durante el ciclo, o el jugador cambia de sala, de modo que ningún cálculo previo puede reutilizarse) y puertas que casi nunca cambian.
- **FR-032**: Las mediciones de FR-030 y FR-031 MUST obtenerse con `python main.py --bench` y quedar reproducibles (Constitución VIII). El bench MUST medir, en los dos escenarios de FR-031, tanto la forma implementada como la alternativa de recalcular siempre desde cero; cualquier reutilización de cálculos MUST justificarse con esa comparación.
- **FR-033**: El costo de decidir de un cazador MUST depender de las salas que quedan dentro de su rango, no del total de salas de la cripta: con la cripta más grande medida, el tiempo de decisión del cazador no supera 1,5 veces el tiempo con la cripta más pequeña. Se mide con `--bench` con criptas sintéticas de tamaños crecientes y el mismo rango (enunciado §5.1).

### Key Entities *(include if feature involves data)*

- **Salida (con costo)**: conexión entre dos salas en una dirección, con su costo (≥ 1, 100 por defecto), su puerta opcional y el estado actual de esa puerta. El costo es dato del esqueleto de la cripta; el estado de la puerta es parte del estado de la partida.
- **Cazador**: enemigo con comportamiento «cazador», con todos los atributos de un enemigo de la Parte I más su rango. Su decisión no guarda memoria propia observable: depende solo del estado de la partida en su turno.
- **Decisión del cazador**: atacar, esperar (costo 100) o moverse a una vecina por una salida concreta (costo de esa salida).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Los 7 casos de «Terreno y cazador» del Apéndice B tienen cada uno al menos una prueba automatizada o un `partida.log` de evidencia que cita su FR, y todos pasan.
- **SC-002**: En las criptas de prueba, el tiempo entre dos turnos de cualquier actor que se mueve coincide en el 100 % de los casos con `max(1, costo_salida × 100 // velocidad)`, y una salida sin costo declarado da los mismos tiempos que en la Parte I.
- **SC-003**: En al menos 1 000 turnos de cazadores en partidas de prueba con cambios de puertas, la decisión coincide con el cálculo de referencia desde cero en el 100 % de los turnos.
- **SC-004**: Con 50 cazadores activos en la cripta de referencia, el ciclo de eventos entre dos decisiones del jugador tarda menos de 20 ms, medido con `--bench`, con y sin cambios de puertas.
- **SC-005**: Una partida con cazadores, jugada, guardada, cargada y continuada, se reproduce con `--replay` con las mismas decisiones de todos los cazadores en el 100 % de los turnos.
- **SC-006**: Los guardianes, errantes y rastreadores toman las mismas decisiones que en la Parte I en todas las pruebas existentes; solo cambian los tiempos donde hay salidas con costo distinto de 100.
- **SC-007**: Medido con `--bench` en criptas sintéticas de tamaños crecientes con el mismo rango, con la cripta más grande medida, el tiempo de decisión del cazador no supera 1,5 veces el tiempo con la cripta más pequeña.

## Assumptions

- **Momento del movimiento**: como en la Parte I, un actor que se mueve cambia de sala al ejecutar su acción, y el intervalo (ahora dependiente del costo de la salida) es el tiempo hasta su siguiente turno. «Cruzar una salida costosa» significa estar en ese intervalo; un cambio de velocidad escala lo que falta (P1 §2.3).
- **Ids de sala**: son opacos y se comparan con el mismo criterio que usa la capacidad 001 en FR-024; si ese criterio cambia, el de esta capacidad cambia igual.
- **Simetría de costos**: se supone que los datos del servicio declaran el mismo costo en ambos sentidos de una conexión; el programa no lo valida y usa el costo de la salida que se atraviesa (FR-001).
- **Activación del cazador**: Se aplica P1 §2.4 sin cambios: la Parte II no lo modifica (“Todo lo establecido en la primera parte sigue vigente salvo que este documento lo modifique explícitamente”).
- **«Decenas de cazadores»** se fija en 50 para la medición de §6.1; «ciclo de eventos» es el procesamiento de todos los eventos entre una decisión del jugador y la siguiente, excluida la espera de la entrada del usuario.
- **Cripta de referencia**: la publicada más grande del servicio del curso, o un paquete de prueba de tamaño equivalente generado para el bench.
- **Cerradura y estado**: «salida abierta» se refiere solo al estado actual de la puerta; si la puerta requiere llave o no es irrelevante para el cazador, que nunca abre puertas.
- **Esperar**: el costo 100 de la espera del cazador es costo base; su intervalo también se calcula con su velocidad (FR-005).
- **Mensajes**: los anuncios de movimiento y ataque del cazador reutilizan los de los demás enemigos; no se agregan mensajes nuevos.
- **Partidas guardadas de la Parte I**: el costo de las salidas es dato de la cripta, no del archivo de partida; la compatibilidad de los archivos de partida se rige por las capacidades que cambian su formato (004).

## Fuera de alcance

- Que el cazador abra puertas, use llaves o recoja objetos.
- Que el cazador se vea afectado por la niebla, el ruido, el rastro o la luz.
- Validar que los costos de los dos sentidos de una conexión coincidan (el programa no lo comprueba; FR-001, FR-003).
- Cambiar la forma de decidir de guardianes, errantes y rastreadores.
- Costos de salida que cambien durante la partida.
