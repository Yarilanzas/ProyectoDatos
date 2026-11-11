# Tasks: Terreno, cazador e invalidación de rutas

**Input**: Design documents from `specs/003-terreno-cazador/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md)

**Tests**: la spec los exige (FR-027, FR-028, Constitución V). Las tareas de prueba van antes de su implementación y
deben fallar antes de implementarla. Cada prueba cita su FR en el nombre o en el docstring.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ir en paralelo (otro archivo, sin dependencias pendientes)
- **[Story]**: historia de la spec (US1 a US5)
- **⛔ bloquea a otra persona**: la tarea es requisito de trabajo ajeno a esta capacidad
- **⏳ bloqueada por otra persona**: la tarea depende de trabajo ajeno a esta capacidad
- Comando de pruebas: `python -m unittest discover -s tests -v`

## Path Conventions

Proyecto único MVC en la raíz: reglas en `Modelo/`, pruebas y bench en `tests/`, `--bench` en `main.py`.

---

## Phase 1: Setup

**Purpose**: línea base antes de tocar el motor.

- [x] T001 Correr la suite completa y anotar en `specs/003-terreno-cazador/tasks.md` (sección Notes) cuántas pruebas pasan antes de empezar; es la referencia de no regresión de guardianes, errantes y rastreadores (FR-006, SC-006)
- [x] T002 Medición M8 «antes»: correr la medición de la agenda de la Parte I §4.1 de `tests/bench_motor.py` (`bench_agenda`) con el código actual y guardar la salida en `resultados_bench_agenda_antes.txt`, con equipo y versión de Python, **antes** de cualquier cambio del motor (FR-022, FR-032; enunciado §5.6)
- [x] T003 [P] Criptas sintéticas para pruebas y bench: usar el generador de criptas sintéticas de la capacidad de datos (Persona B) cuando exista; mientras tanto, un generador mínimo propio en `tests/utiles_terreno.py`. Las criptas deben ser deterministas por semilla (enunciado §6.3). Debe ofrecer: cuadrícula de n salas con costos configurables, puertas dirigidas (A→B y B→A con estado propio), costos distintos por sentido, y colocación de jugador y k cazadores con rango dado; sin datos de criptas reales (FR-028, FR-033; Constitución IV). 

---

## Phase 2: Foundational (búsqueda, grafo, puertas y contadores)

**Purpose**: piezas que todas las historias usan. Ninguna historia empieza antes de terminar esta fase.

### Cola de prioridad y espacio de trabajo (Persona A, D-PEND-01)

- [ ] T004 [P] Pruebas propias de la cola en `tests/test_cola_prioridad.py`: extrae en orden de `(distancia, ordinal)`, entradas repetidas de un mismo ordinal (inserción perezosa), `vacia()`, `vaciar()` en O(1), orden determinista ante claves iguales, y que el módulo no importe `heapq`, `bisect` ni `collections` (FR-011, FR-021; Principio I)
- [ ] T005 Implementar `Modelo/ColaPrioridad.py`: montículo binario mínimo en lista con `insertar(distancia, ordinal)`, `extraer_minimo()`, `vacia()`, `vaciar()`; complejidad O(log t) por operación documentada en docstrings; pasa T004 (FR-011, FR-033). **⛔ bloquea a «ir a» (001, T062)**
- [ ] T006 [P] Pruebas de `EspacioBusqueda` en `tests/test_espacio_busqueda.py`: listas `dist`, `primero`, `epoca` de tamaño n; incrementar `epoca_actual` invalida todo en O(1) sin recorrer las listas; un espacio creado para n salas se rechaza con otro `cantidad_salas` (FR-033)
- [ ] T007 Implementar `EspacioBusqueda` en `Modelo/BusquedaRuta.py` (data-model §4.3): `dist`, `primero`, `epoca`, `epoca_actual` y una `ColaPrioridad` reutilizable; creación O(n), reinicio O(1); pasa T006 (FR-033). **⛔ bloquea a «ir a» (001, T062)**

### Grafo de la cripta

- [ ] T008 [P] Pruebas de `GrafoCripta` en `tests/test_grafo_cripta.py`: funciona en un motor armado a mano **sin** `Conocimiento`; asigna ordinales propios 0..n-1 que no pisan `_ordinal` de `Conocimiento`; `aristas(sala)` entrega solo salidas abiertas con `costo_salida` (100 si falta); `entrantes(sala)` entrega cada salida abierta `w→sala` con el costo y la puerta **de esa salida**; con A→B cerrada y B→A abierta, `entrantes(A)` incluye B→A y `entrantes(B)` no incluye A→B; con costos distintos por sentido, cada entrante lleva su propio costo (FR-003, FR-011, FR-015, FR-017)
- [ ] T009 Implementar `Modelo/GrafoCripta.py` (data-model §2): `cantidad_salas`, `ordinal(sala)` con atributo propio en la sala, `aristas(sala)`, `entrantes(sala)`; construcción O(n + m) una vez recorriendo las salas del motor, sin `dict`/`set` como índice y sin usar `_ordinal`, `_origen` ni `entrantes` de `Conocimiento`; el estado de puerta se lee en vivo; pasa T008 (FR-011, FR-015, FR-017)

### Búsqueda de ruta (Persona A, D-PEND-01)

- [ ] T010 [P] Extender `tests/test_ruta_contrato.py` con dos clases nuevas. Hoy el archivo tiene el mixin `ContratoRuta` (casos del contrato, con `buscar` como atributo de clase) y dos subclases: `TestContratoBuscadorPrueba` (`buscar = buscador_prueba`) y `TestContratoPrimerPaso` (`buscar = primer_paso` de `Modelo.rutas_ir_a`, con `@unittest.skip` hasta T063 de 001). Las clases nuevas: (a) `TestContratoBusquedaRuta(ContratoRuta, unittest.TestCase)`, que corre los casos existentes del contrato llamando directamente a `Modelo.BusquedaRuta.primer_paso`, no a `buscador_prueba` ni a `rutas_ir_a`; (b) `TestLimiteBusquedaRuta(unittest.TestCase)`, que **no** hereda de `ContratoRuta`, para que sus casos no corran contra `buscador_prueba`, con los casos de `limite` y `espacio`: `d == limite` devuelve el paso; `d > limite` devuelve `None`; `limite=0` con origen ≠ destino devuelve `None`; mismo resultado con y sin `espacio` dado; dos llamadas seguidas con el mismo `espacio` no se contaminan; la tabla de desempates sigue pasando con `limite` grande. `Modelo.BusquedaRuta` se importa dentro de las clases nuevas (por ejemplo en `setUpClass`, con un alias distinto de `primer_paso`) y no al principio del archivo: así, mientras no exista, solo fallan las clases nuevas y no las existentes, y no se pisa el `primer_paso` de `Modelo.rutas_ir_a` que importa el archivo (FR-012, FR-014, FR-033)
- [ ] T011 Implementar `primer_paso(grafo, origen, destino, limite=None, espacio=None)` en `Modelo/BusquedaRuta.py` (research R3, R6): búsqueda adelante acotada, nada con distancia tentativa > `limite` entra a la cola; `primero[x]` copia de `primero[y]` si mejora y se queda con el de menor id si empata; salida hacia cada vecina directa = la de menor costo, ante empate la primera en N, S, E, O; crea un `EspacioBusqueda` por llamada si `espacio is None`; cumple las 7 obligaciones de `specs/001-niebla-mapa-ir-a/contracts/interfaz-ruta.md`; debe pasar exactamente `TestContratoBusquedaRuta` y `TestLimiteBusquedaRuta` de `tests/test_ruta_contrato.py` (T010), sin romper `TestContratoBuscadorPrueba`; `TestContratoPrimerPaso` sigue con `skip` hasta T063 de 001. **Depende de T014**: no se implementan `limite` ni `espacio` antes de que Persona C haya sido avisada del cambio de contrato y lo haya hecho o aprobado (FR-011, FR-012, FR-013, FR-014, FR-021). **⛔ bloquea a «ir a» (001, T062: `Modelo/rutas_ir_a.py` delega aquí)**
- [ ] T012 [P] Pruebas de `campo_hacia` en `tests/test_campo_hacia.py`: en criptas de `tests/utiles_terreno.py`, `dist[u]` coincide con `primer_paso(...).costo_total` desde cada u para toda sala a distancia ≤ cota; salas a distancia > cota quedan con época vieja (∞); con puertas dirigidas y costos distintos por sentido usa la salida `w→x`, no la `x→w` (FR-003, FR-011, FR-016)
- [ ] T013 Implementar `campo_hacia(grafo, destino, cota, espacio=None)` en `Modelo/BusquedaRuta.py` (data-model §4.2): búsqueda al revés acotada por `grafo.entrantes`; complejidad documentada; pasa T012 (FR-011, FR-016, FR-033)
- [ ] T014 Actualizar `specs/001-niebla-mapa-ir-a/contracts/interfaz-ruta.md`: agregar `limite=None` y `espacio=None` como parámetros opcionales al final de `primer_paso`, y dejar escrito que `entrantes` solo lo ofrece `GrafoCripta` y no se exige a `GrafoConocido`; avisar al grupo en el mismo cambio. El archivo es de Persona C: el cambio lo hace ella o se hace con su aprobación (FR-026; P-01 aceptada; contratos compartidos). **⛔ requiere a Persona C**

### Puertas y contadores en el motor

- [ ] T015 [P] Pruebas en `tests/test_invalidacion_puertas.py`: `version_puertas` crece con el cierre automático, con `abrir`, y con el deshacer de cada uno; nunca decrece; `ciclo` crece al empezar cada ciclo de eventos; y una prueba que lee el código fuente de `Modelo/` y falla si aparece, fuera del método único, `.cerrada =`, `setattr(..., "cerrada", ...)` o `_asignar_reversible(..., "cerrada", ...)`, excluyendo por nombre `Modelo/prueba_actores.py` con el motivo escrito en la prueba (pruebas manuales de la Parte I que arman salas a mano) (FR-016, FR-024, FR-031)
- [ ] T016 Agregar en `Modelo/MotorSimulacion.py` el contador `version_puertas` y el método único de escritura de `salida.cerrada`, que incrementa el contador y registra su deshacer llamándose a sí mismo; redirigir a ese método el evento de cierre automático (`ejecutar_evento`) y `abrir_salida`, incluidos sus dos deshacer que hoy usan `setattr(..., "cerrada", ...)`; no tocar `Persistencia/ConversorPartida.py`; pasa la parte de puertas de T015 (FR-016, FR-031)
- [ ] T017 Agregar en `Modelo/MotorSimulacion.py` el contador `ciclo`, incrementado al empezar `avanzar_hasta_jugador`; no se guarda ni entra en la bitácora; pasa la parte de ciclo de T015 (FR-016, FR-024, FR-025)
- [ ] T018 En `Modelo/MotorSimulacion.py`, construir un `GrafoCripta` y un `EspacioBusqueda` persistentes cuando el motor recibe sus salas (inicio y carga de partida), en O(n + m) una vez; no forman parte del estado guardado (FR-015, FR-033)

**Checkpoint**: la búsqueda pasa el contrato, el grafo no depende de `Conocimiento`, toda escritura de puertas del motor pasa por el método único y la suite sigue en verde.

---

## Phase 3: User Story 1 - El terreno determina cuánto tarda moverse (Priority: P1) 🎯 MVP

**Goal**: moverse por una salida cuesta su costo, para el jugador y todos los enemigos.

**Independent Test**: paquete offline de prueba con salidas de costo 1, sin declarar y 300; comprobar en el reloj virtual el siguiente turno del jugador y de un errante.

### Tests for User Story 1

- [ ] T019 [P] [US1] En `tests/test_terreno.py`: jugador de velocidad 100 cruza una salida de costo 300 y su siguiente turno ocurre 300 después (escenario 1 de la US1; FR-004, FR-005)
- [ ] T020 [P] [US1] En `tests/test_terreno.py`: salida sin costo declarado, actor de velocidad 100, siguiente turno 100 después (escenario 2; FR-002)
- [ ] T021 [P] [US1] En `tests/test_terreno.py`: cripta cuyos datos traen 250 en ambos sentidos de A–B; un actor cruza A→B y otro B→A, los dos tardan 250 (escenario 3; FR-003)
- [ ] T022 [P] [US1] En `tests/test_terreno.py`: **Apéndice B, «actor de velocidad alta cruza salida de costo 1»**: velocidad 1 000 y costo 1 dan intervalo 1, nunca 0 (FR-005)
- [ ] T023 [P] [US1] En `tests/test_terreno.py`: **Apéndice B, «cambia la velocidad de un actor que cruza una salida costosa»**: velocidad 100 cruza costo 400 en t = 1 000; en t = 1 100 la velocidad pasa a 200; su próximo turno queda en 1 250 (FR-007)
- [ ] T024 [P] [US1] En `tests/test_terreno.py`: un errante y un rastreador eligen su destino igual que en la Parte I (misma semilla) y su siguiente turno ocurre según el costo de la salida atravesada (FR-006)
- [ ] T025 [P] [US1] En `tests/test_terreno.py`: atacar, esperar y usar un objeto conservan su costo de la Parte I en una sala cuyas salidas cuestan 300 (escenario 7; FR-005)
- [ ] T026 [P] [US1] En `tests/test_terreno.py`: cada paso de un viaje «ir a» avanza el reloj según el costo de la salida de ese paso (FR-004, FR-026); con `primer_paso` todavía sin implementar, la prueba usa el buscador inyectado de `Viaje`

### Implementation for User Story 1

- [ ] T027 [US1] En `Modelo/MotorSimulacion.py`, `mover_jugador`: cambiar `self.proxima_accion(jugador, costo=100)` por `self.proxima_accion(jugador, costo=self.costo_salida(salida))`; pasa T019, T020, T021, T026 (FR-004, FR-005). Actualizar `TestMoverNoCambia` de `tests/test_costo_salida.py` (T118 de la capacidad 001), que hoy afirma que `mover` ignora el costo, a la regla nueva (`costo * 100 // velocidad`), y avisar a Persona C del cambio.
- [ ] T028 [US1] En `Modelo/MotorSimulacion.py`, rama `Enemigo` de `ejecutar_evento`: recordar la salida usada (`salida_errante`, `salida_rastro`) y, si `mover_enemigo` devolvió `True`, reprogramar con `costo_salida(salida)`; atacar, esperar o un movimiento fallido siguen con 100; `activar_enemigo` no cambia; pasa T022 a T025 (FR-004, FR-005, FR-006, FR-007)
- [ ] T029 [US1] Correr la suite completa de `tests/` y comparar con T001: las pruebas existentes de guardianes, errantes y rastreadores siguen pasando y solo cambian tiempos donde hay costos distintos de 100 (FR-006, SC-006)

### Datos del terreno 

- [ ] T030 [P] [US1] En `tests/test_validacion_datos.py`: `Salida.desde_json` (`DTOS/Salida.py`) rechaza con mensaje claro un costo 0, negativo o no entero (por ejemplo `0`, `-5`, `2.5`, `"100"` y `True`), sin asumir ningún valor (FR-001). Persona B ya implementó la validación en Salida.desde_json: esta tarea solo escribe la prueba.
- [ ] T031 [P] [US1] En `tests/test_validacion_datos.py`: una conexión cuyos sentidos declaran costos distintos (o uno declarado y el otro ausente) **no** se rechaza, y cada actor tarda lo de la salida que atraviesa (FR-001, FR-003). **El campo costo ya existe en Salida.**
- [ ] T032 [P] [US1] En `tests/test_costo_cache.py`: el costo de cada salida sobrevive a `AlmacenamientoLocalApi.guardar_esqueleto` y a la lectura posterior por `GestorDatos.obtener_esqueleto`, y al paquete `--offline`; una salida sin costo sigue sin costo (100 en el juego); sin red, con paquete temporal (FR-008, FR-002). **⏳ bloqueada por la capacidad de datos (campo `costo` y versión de formato)**

**Checkpoint**: el terreno funciona solo; guardianes, errantes y rastreadores sin regresiones.

---

## Phase 4: User Story 2 - El cazador persigue por la ruta más barata (Priority: P1)

**Goal**: el cazador activo da un paso por una ruta de costo mínimo y ataca si comparte sala.

**Independent Test**: cripta con dos rutas al jugador (pocas salas caras frente a muchas baratas) y un cazador con rango suficiente; seguir su recorrido y el costo de cada paso.

### Tests for User Story 2

- [ ] T033 [P] [US2] En `tests/test_cazador.py`: cazador en la sala del jugador ataca con el costo de ataque de la Parte I, también con rango 0 (escenario 1; FR-010)
- [ ] T034 [P] [US2] En `tests/test_cazador.py`: **Apéndice B, «ruta de menos salas pero mayor costo vs. más salas y menor costo»**: rutas de 2 salidas con costo 500 y de 4 salidas con costo 400, rango ≥ 400; da el primer paso de la de 400 (FR-011, FR-013)
- [ ] T035 [P] [US2] En `tests/test_cazador.py`: **Apéndice B, «dos vecinas con rutas de costo mínimo»**: va a la vecina de menor id; y con dos salidas hacia esa vecina de igual costo usa la primera en N, S, E, O (FR-014)
- [ ] T036 [P] [US2] En `tests/test_cazador.py`: paso por una salida de costo 150 con velocidad 100; siguiente turno 150 después (escenario 4; FR-013)
- [ ] T037 [P] [US2] En `tests/test_cazador.py`: distancia exactamente igual al rango, se mueve (escenario 5; FR-012)
- [ ] T038 [P] [US2] En `tests/test_cazador.py`: el jugador cambia de sala entre dos turnos del cazador y este decide con la sala nueva (escenario 6; FR-016)
- [ ] T039 [P] [US2] En `tests/test_cazador.py`: activación según P1 §2.4: dormido dentro del rango no actúa ni busca (escenario 7); tras entrar el jugador a su sala queda activo, su primera acción se programa con costo base 100, y persigue cuando el jugador sale dentro del rango (escenario 8); un cazador activo que cambia de sala sigue activo (FR-034)
- [ ] T040 [P] [US2] En `tests/test_cazador.py`: la decisión no cambia al agregar enemigos, objetos, trampas o rastro en las salas de la ruta, ni con la niebla del jugador (sala nunca vista) (FR-015)
- [ ] T041 [P] [US2] En `tests/test_cazador.py`: varios cazadores con el mismo objetivo deciden cada uno con su sala y su rango, y pueden terminar en la misma sala (FR-018)
- [ ] T042 [P] [US2] En `tests/test_cazador.py`: un cazador muerto no vuelve a actuar y su turno pendiente se descarta sin efecto (FR-019)
- [ ] T043 [P] [US2] En `tests/test_cazador.py`: al entrar o salir de la sala del jugador y al atacar se muestran los mismos mensajes que con los demás enemigos (FR-020)
- [ ] T044 [P] [US2] En `tests/test_cazador.py`: el estado del generador de azar es el mismo antes y después de cualquier decisión del cazador (FR-021)

### Implementation for User Story 2

- [ ] T045 [US2] Leer el rango de la ficha del enemigo y guardarlo en el enemigo (`Modelo/Enemigo.py` y la construcción de enemigos en `Modelo/MotorSimulacion.py`); «entero ≥ 0 en unidades de costo»; solo lectura, sin valor por defecto (FR-009). FichaEnemigo ya trae rango validado (Persona B): falta copiarlo al Enemigo en `crear_enemigo`
- [ ] T046 [US2] Implementar en `Modelo/MotorSimulacion.py` la decisión de referencia del cazador (data-model §8): misma sala → `ATACAR`; si no, `primer_paso(grafo_cripta, sala, sala_jugador, limite=rango, espacio=espacio_motor)`; `None` → `ESPERAR` con costo 100; si no → `MOVER` por esa salida con su costo; devuelve `accion`, `salida`, `costo_base` (FR-010, FR-011, FR-012, FR-013, FR-014, FR-017)
- [ ] T047 [US2] Implementar en `Modelo/MotorSimulacion.py` el campo compartido (data-model §5): llave `(ciclo, sala del jugador, version_puertas, cota)`; si no es válido o la cota es menor que el rango del que decide, recalcular con `campo_hacia` y cota = mayor rango entre los cazadores activos y vivos; decidir aplicando FR-014 sobre las salidas abiertas de la sala del cazador (vecinas no fijadas = ∞); misma salida de datos que T046 (FR-014, FR-016, FR-018)
- [ ] T048 [US2] Integrar en `Modelo/MotorSimulacion.py`: `accion_enemigo` devuelve la acción del cazador para `comportamiento == "cazador"`; `ejecutar_evento` mueve con `mover_enemigo`, ataca con `atacar` o espera, y reprograma con el `costo_base` de la decisión; la estrategia activa se elige en un solo lugar; la estrategia inicial es la referencia desde cero (búsqueda individual acotada, T046), y el campo compartido (T047) solo se activa si T070 lo decide con M3 y M4; pasa T033 a T044 (FR-010, FR-013, FR-019, FR-020, FR-022, FR-034)
- [ ] T049 [US2] En `tests/test_ruta_contrato.py` o `tests/test_cazador.py`, correr la tabla de casos de desempate del contrato contra la decisión del cazador con las dos estrategias, permutando el orden de las salidas (FR-014, FR-021)

**Checkpoint**: el cazador persigue y ataca; US1 sigue pasando.

---

## Phase 5: User Story 3 - El cazador espera cuando no puede o no le conviene perseguir (Priority: P1)

**Goal**: sin ruta abierta o con `d > rango`, el cazador espera con costo 100.

**Independent Test**: jugador tras una puerta cerrada, y jugador a distancia mayor que el rango; el cazador no cambia de sala y su siguiente turno corresponde a costo 100.

### Tests for User Story 3

- [ ] T050 [P] [US3] En `tests/test_cazador.py`: **Apéndice B, «sin ruta abierta»**: todas las rutas pasan por puertas cerradas; espera con costo 100 y ninguna puerta cambia (FR-012, FR-017)
- [ ] T051 [P] [US3] En `tests/test_cazador.py`: **Apéndice B, «ruta más barata cuesta más que el rango»**: ruta de 600 con rango 500; espera con costo 100 (FR-012)
- [ ] T052 [P] [US3] En `tests/test_cazador.py`: cazador que esperaba por una puerta cerrada persigue en su siguiente turno cuando la puerta se abre y la nueva ruta no supera el rango (escenario 3; FR-016)
- [ ] T053 [P] [US3] En `tests/test_cazador.py`: rango 0 en otra sala, espera con costo 100 (escenario 4; FR-012)
- [ ] T054 [P] [US3] En `tests/test_cazador.py`: cazador que porta la llave de una puerta cerrada de su única ruta no la abre ni la usa, y espera (FR-017)

**Checkpoint**: US3 pasa con la implementación de US2, sin código nuevo; si alguna prueba falla, se corrige en T046 a T048.

---

## Phase 6: User Story 4 - La decisión siempre es la de calcular desde cero (Priority: P1)

**Goal**: ninguna reutilización cambia una decisión, aunque cambien puertas, jugador u otros actores.

**Independent Test**: comparar turno a turno, en partidas con cierres y aperturas, la decisión del juego con la referencia desde cero.

### Tests for User Story 4

- [ ] T055 [P] [US4] En `tests/test_cazador.py`: **Apéndice B, «una puerta de su ruta se cierra entre dos turnos»**: decide como desde cero: otra ruta mínima dentro del rango o espera con costo 100 (FR-016)
- [ ] T056 [P] [US4] En `tests/test_cazador.py`: una puerta que se abre entre dos turnos crea una ruta más barata y el cazador la sigue (escenario 2; FR-016)
- [ ] T057 [US4] Crear `tests/test_cazador_equivalencia.py`: partidas sintéticas de `tests/utiles_terreno.py` con al menos **1 000 turnos de cazadores** en total, con puertas que se cierran y abren durante el ciclo, el jugador cambiando de sala, varios cazadores con rangos distintos, puertas dirigidas y costos distintos por sentido; en cada turno compara la decisión del campo compartido con la referencia desde cero (acción, sala de destino, salida y costo) y exige 100 % de coincidencia (FR-016, FR-028, SC-003)
- [ ] T058 [US4] En `tests/test_cazador_equivalencia.py`: partida con cazadores jugada, guardada, cargada y continuada, y la misma partida retrocedida con un pergamino y reproducida con `--replay`: las decisiones de todos los cazadores coinciden en el 100 % de los turnos con la partida original (FR-024, FR-025, SC-005). **⏳ bloqueada parcialmente por la capacidad 004 (formato de guardado)**
- [ ] T059 [US4] En `tests/test_cazador_equivalencia.py`: la reconstrucción de un estado pasado de la línea de tiempo da las mismas decisiones de los cazadores que la partida jugada (FR-025). **⏳ bloqueada por la capacidad 004**
- [ ] T060 [P] [US4] En `tests/test_cazador.py`: un comando rechazado del jugador no cambia `version_puertas`, la sala del jugador ni la siguiente decisión de ningún cazador (FR-023)

**Checkpoint**: equivalencia demostrada; la estrategia compartida puede usarse en el juego.

---

## Phase 7: User Story 5 - Muchos cazadores sin que el juego se trabe (Priority: P2)

**Goal**: medir M1 a M8 con `python main.py --bench` y decidir la estrategia con datos.

**Independent Test**: correr `python main.py --bench` y revisar los archivos de resultados.

- [ ] T061 [US5] Crear `tests/bench_cazador.py` con la estructura de los bench existentes (resultados en `resultados_bench_cazador.txt`, equipo y versión de Python, mediana y p95) y registrarlo en `main.py` dentro de `--bench`, sin instanciar la vista (FR-032; Constitución II y VIII)
- [ ] T062 [P] [US5] M1 en `tests/bench_cazador.py`: decisión de un cazador frente a 50 en la misma cripta (FR-030)
- [ ] T063 [P] [US5] M2 en `tests/bench_cazador.py`: `ColaPrioridad` frente a la agenda y a la búsqueda lineal del mínimo, regiones de 10 a 10 000 salas (FR-033)
- [ ] T064 [P] [US5] M3 en `tests/bench_cazador.py`: campo compartido frente a individual con k ∈ {1, 2, 5, 10, 25, 50} y rango pequeño y grande, puertas estables; reportar el k* medido (FR-030, FR-032)
- [ ] T065 [P] [US5] M4 en `tests/bench_cazador.py`: 50 cazadores activados antes de medir, en tres escenarios: puertas estables, puertas que cambian con frecuencia y recalcular siempre desde cero; mediana, p95, búsquedas hechas y si cumple < 20 ms (FR-030, FR-031, FR-032)
- [ ] T066 [P] [US5] M5 en `tests/bench_cazador.py`: criptas sintéticas deterministas por semilla (enunciado §6.3), del generador de Persona B (tests/generador_criptas.py), usado mediante tests/utiles_terreno.py (T003), de 10², 10³, 10⁴ y 10⁵ salas con el mismo rango y la misma posición relativa; la más grande ≤ 1,5 × la más pequeña; incluir el control con listas nuevas por búsqueda (FR-033, SC-007)
- [ ] T067 [P] [US5] M6 en `tests/bench_cazador.py`: rango pequeño frente a grande en la misma cripta (FR-033)
- [ ] T068 [P] [US5] M7 en `tests/bench_cazador.py`: 50 cazadores activos en la cripta de referencia; ciclo completo, mediana y p95 < 20 ms (FR-030, SC-004)
- [ ] T069 [US5] M8 «después»: repetir `bench_agenda` de `tests/bench_motor.py` con la carga nueva (intervalos variables por costo) y guardar en `resultados_bench_agenda_despues.txt` junto a la comparación con T002 (FR-022, FR-032; enunciado §5.6)
- [ ] T070 [US5] Con M3 y M4, confirmar o invertir la estrategia del juego en el lugar único de T048 y registrar los números y la conclusión en `specs/003-terreno-cazador/research.md` (R4 y R5) para el Documento de Decisiones (FR-030, FR-031, FR-032; Constitución VIII)

**Checkpoint**: FR-030 a FR-033 medidos y reproducibles.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T071 [P] Ayuda del juego en `Vista/VistaConsola.py` (`AYUDA`): explicar que cada salida tiene un costo que define cuánto se tarda en cruzarla y que el cazador persigue por la ruta más barata dentro de su rango (FR-029)
- [ ] T072 [P] `README.md`: costo de las salidas (100 si falta), tiempo de movimiento y comportamiento del cazador; el README está en UTF-16 y se edita avisando al grupo (FR-029)
- [ ] T073 [P] Docstrings de complejidad en `Modelo/ColaPrioridad.py`, `Modelo/BusquedaRuta.py` y `Modelo/GrafoCripta.py`, copiando las tablas de `data-model.md` (FR-033; Principio I)
- [ ] T074 Revisar en `tests/test_terreno.py` y `tests/test_cazador.py` que cada uno de los 7 casos de «Terreno y cazador» del Apéndice B tiene su prueba y cita su FR: T022, T023, T034, T035, T050, T051, T055 (FR-027, SC-001)
- [ ] T075 Correr `python -m unittest discover -s tests -v` sobre `tests/` y dejarla al 100 % (FR-027; Constitución V)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001–T003)**: sin dependencias. T002 debe terminar antes de T016, T027 y T028.
- **Foundational (T004–T018)**: después de Setup; bloquea todas las historias.
  - T005 → T007 → T011 → T013 (cola, espacio, búsqueda adelante, búsqueda al revés).
  - T014 → T011: el cambio de contrato se avisa a Persona C, y ella lo hace o lo aprueba, antes de implementar `limite` y `espacio`. T014 puede hacerse en cuanto termine T010.
  - T007, T009 → T018; T016 y T017 son independientes de la búsqueda.
- **US1 (T019–T032)**: después de Foundational. T032 depende además de la capacidad de datos.
- **US2 (T033–T049)**: después de US1 (el cazador reprograma con el costo de la salida de T028).
- **US3 (T050–T054)**: después de US2; no agrega código.
- **US4 (T055–T060)**: después de US2. T059 depende de la capacidad 004.
- **US5 (T061–T070)**: después de US4 (T070 cambia la estrategia solo con la equivalencia ya probada).
- **Polish (T071–T075)**: al final; T071–T073 pueden empezar cuando US2 termine.

### Bloqueos con otras personas

| Tarea            | Relación                                      | Con quién |
|------------------|-----------------------------------------------|---|
| T005, T007, T011 | ⛔ bloquean                                    | «ir a» de la capacidad 001 (T062 de 001: `Modelo/rutas_ir_a.py` delega en `BusquedaRuta`) |
| T014             | ⛔ cambia un contrato compartido               | Persona C, dueña de `specs/001-niebla-mapa-ir-a/contracts/interfaz-ruta.md`: lo cambia ella o con su aprobación; se avisa al grupo (P-01 aceptada) |
| T016             | Toca `Modelo/MotorSimulacion.py`, que otros usan | Revisión de otra persona (Constitución: cambios en `Modelo/`) |
| T030, T031       | Ya no bloqueadas                              | Persona B implementó `costo` y su validación en `Salida`; solo falta escribir las pruebas |
| T032             | ⏳ bloqueada                                   | Capacidad de datos (campo `costo`, rango en `FichaEnemigo`, versión de formato) y P-02 |
| T045             | Ya no bloqueada                               | FichaEnemigo.rango ya existe (Persona B); solo falta copiarlo al enemigo |
| T003, T066       | Ya no bloqueadas                              |`tests/generador_criptas.py` (Persona B) ya existe; se usa mediante `tests/utiles_terreno.py` |
| T058             | ⏳ bloqueada parcialmente                      | Capacidad 004 (formato de guardado) |
| T059             | ⏳ bloqueada                                   | Capacidad 004 (línea de tiempo) |

### Within Each User Story

- Pruebas primero; deben fallar antes de implementar.
- Lectura de datos antes de la decisión; decisión antes de la integración en el motor.

### Parallel Opportunities

- T003, T004, T006, T008, T010, T012, T015 en paralelo (archivos distintos).
- Todas las pruebas [P] de cada historia en paralelo (mismo archivo pero casos independientes; repartir por clase de prueba si trabajan dos personas).
- M1 a M7 (T062–T068) en paralelo una vez exista T061.

---

## Parallel Example: Foundational

```text
Persona A: T004 → T005 → T006 → T007 → T010 → (T014, Persona C) → T011 → T012 → T013
Persona A: T008 → T009 → T018, y en paralelo T015 → T016 → T017
```

## Parallel Example: User Story 2

```text
Lanzar juntas: T033, T034, T035, T036, T037, T038, T039, T040, T041, T042, T043, T044
Luego en orden: T045 → T046 → T047 → T048 → T049
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Setup y Foundational.
2. US1: terreno con costo real para todos los actores.
3. Validar con la suite (T029) y detenerse a revisar.

### Incremental Delivery

1. US1 (terreno) → US2 (cazador con la referencia desde cero) → US3 (esperas) → US4 (campo compartido demostrado equivalente) → US5 (mediciones y elección final).
2. Hasta T070, la estrategia del juego puede quedar en la referencia desde cero: es correcta por definición, y el campo compartido se activa cuando T057 y M4 lo respaldan.

### Parallel Team Strategy

- Persona A: cola, espacio y búsqueda (T004–T007, T010–T013), que desbloquean «ir a».
- Persona A: grafo, puertas y contadores (T008, T009, T015–T018), luego US1 a US5.
- Capacidad de datos: campos `costo` y `rango`, validación (P-02) y versión de formato, que desbloquean T030–T032.

---

## Notes

- Cada tarea cita al menos un FR; ninguna existe sin requisito.
- Los 7 casos del Apéndice B: T022, T023 (US1); T034, T035 (US2); T050, T051 (US3); T055 (US4).
- No se modifican `spec.md` ni `plan.md`. Los resultados de M3 y M4 se registran en `research.md` (T070).
- FR-008 (versión de caché y paquete) depende de la capacidad de datos; aquí solo se verifica en T032 que el costo se conserve.
- Línea base de T001: 295 pruebas corridas, 285 pasan, 0 fallan, 0 errores, 10 omitidas (skip: `test_ruta_contrato`, T063 pendiente de `Modelo/BusquedaRuta.py`) — `python -m unittest discover -s tests -v`, Python 3.13.13, 2026-11-10.
