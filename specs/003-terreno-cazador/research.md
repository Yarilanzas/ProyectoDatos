# Research: Terreno, cazador e invalidación de rutas

**Feature**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Fecha**: 2026-11-09

Cada decisión trae alternativas, elección, complejidad esperada, evidencia a medir y límites. Las complejidades son
análisis; todo tiempo es **hipótesis** hasta medirlo con `python main.py --bench` (Constitución VIII). Las mediciones
M1 a M8 están definidas en [R9](#r9-mediciones-con---bench).

Notación: `n` salas y `m` salidas de la cripta; `k` cazadores activos; `R` = salas a distancia ≤ rango (la región del
rango) y `E_R` las salidas que salen de ellas; `deg(u)` la cantidad de salidas de la sala `u`.

Hechos del código actual que condicionan el diseño:

- `Conocimiento` (capacidad 001) asigna sus propios ordinales y listas de salidas entrantes, pero el cazador **no** los
  usa: su grafo no debe depender del conocimiento del jugador (FR-015) y los motores armados a mano en las pruebas no
  tienen `Conocimiento`. `GrafoCripta` asigna sus propios ordinales y construye sus propias listas de entrantes.
- La restauración de puertas al cargar vive en `Persistencia/ConversorPartida.py`, fuera de `Modelo/`.
- `motor.costo_salida(salida)` es el único acceso al costo: 100 si la salida no lo trae. O(1).
- La puerta es por salida (`salida.cerrada`): la salida A→B y la B→A tienen estado propio. Las salidas son dirigidas.
- El motor reprograma a todo enemigo con costo 100 después de actuar (`MotorSimulacion.ejecutar_evento`, rama
  `Enemigo`, `self.proxima_accion(actor, 100)`), y al jugador con 100 en `mover_jugador`.
- `AgendaEventos` es un montículo mínimo propio de objetos `Evento` con índice intrusivo (`evento.indice_heap`) y
  borrado perezoso por `cancelado`.
- `activar_enemigo` ya programa la primera acción con costo 100 (P1 §2.4, FR-034).

---

## R1. Cola de prioridad de la búsqueda (FR-011, FR-013, Principio I)

**Alternativas**

| Opción | Descripción | Complejidad | Problema |
|---|---|---|---|
| A. Reutilizar `AgendaEventos` | Envolver cada (distancia, sala) en un `Evento` | push/pop O(log N) | Acopla dos contratos: el índice intrusivo vive en el objeto y su `cancelado` es semántica de la agenda. Cada entrada crea un `Evento`. Un cambio en la agenda (capacidad 004 la usa para la línea de tiempo) rompería la búsqueda |
| B. Montículo binario aparte con inserción perezosa | `Modelo/ColaPrioridad.py`; claves `(distancia, ordinal)`; si una sala mejora se inserta de nuevo y la entrada vieja se descarta al extraerla | push/pop O(log E_R); hasta E_R entradas | Memoria algo mayor que con decrease-key |
| C. Montículo con decrease-key | Igual que B, con un arreglo de posiciones por ordinal | push/pop/decrease O(log R) | Un arreglo más que hay que mantener con la marca de época (R2); más código para una ganancia que en grafos de grado ≤ 4 es pequeña |
| D. Búsqueda lineal del mínimo | Sin montículo | O(R²) | Rompe FR-033 en rangos grandes |

**Elección**: B. `Modelo/ColaPrioridad.py` (Persona A, decisión D-PEND-01). Claves enteras `(distancia, ordinal)`: el
segundo campo solo hace el orden de extracción determinista; **no** define el desempate de la decisión (R6).

**Complejidad esperada**: búsqueda completa O((|R| + |E_R|) log |E_R|). Con grado ≤ 4 por sala, |E_R| ≤ 4|R|.

**Evidencia a medir**: M2 compara B con A (misma secuencia de operaciones con la agenda) y con D, para tamaños de
región 10 a 10 000.

**Límites**: con inserción perezosa la cola puede tener hasta |E_R| entradas en lugar de |R|. Si M2 mostrara que la
diferencia con C importa, se cambia a C sin tocar la interfaz.

---

## R2. Distancias en arreglos densos por ordinal (FR-011, FR-033, Principio I)

**Alternativas**

| Opción | Descripción | Costo por decisión | Problema |
|---|---|---|---|
| A. `dict` sala → distancia | — | O(R) | Prohibido (Principio I) |
| B. Lista nueva `[∞] * n` en cada búsqueda | — | O(n) | Rompe FR-033: el costo crece con la cripta |
| C. Listas de tamaño n creadas una vez y reiniciadas con la lista de salas tocadas | Al terminar, se recorren las tocadas y se restauran | O(R) | Correcto; exige recordar las tocadas y no olvidar restaurar ante una salida temprana |
| D. Listas de tamaño n creadas una vez con **marca de época** | `epoca[i] == epoca_actual` indica que `dist[i]` es válido en esta búsqueda; cada búsqueda incrementa `epoca_actual` | O(R) | Una lista más de enteros |

**Elección**: D. Listas `dist`, `primero` (R6) y `epoca`, de tamaño n. Los índices son los ordinales que devuelve
`grafo.ordinal(sala)` (los ids son opacos); en `GrafoCripta` son ordinales propios, asignados al iniciar o cargar la
partida, sin usar los de `Conocimiento`. Un entero de Python no desborda, así que la época no necesita reinicio.

**Dónde viven los arreglos**: en un **espacio de trabajo** propio de `BusquedaRuta` (`EspacioBusqueda`), no en el
grafo, porque `primer_paso` también recibe grafos que no son `GrafoCripta` (por ejemplo `GrafoConocido` de «ir a»).
`primer_paso` y `campo_hacia` lo reciben como parámetro opcional `espacio=None`:

- Si no se les da, crean uno por llamada, de tamaño `grafo.cantidad_salas`: cuesta O(n) por llamada. Es el caso de
  «ir a», que calcula un paso por acción del jugador y no tiene meta ligada a FR-033.
- El motor guarda **un** espacio persistente para los cazadores, creado al iniciar o cargar la partida. Por eso el
  costo O(n) de creación **no** aplica a la decisión del cazador, y FR-033 se cumple con la marca de época.

**Complejidad esperada**: lectura y escritura O(1); memoria O(n) una sola vez; reinicio O(1) por búsqueda.

**Evidencia a medir**: M5 (FR-033) incluye la variante B como control negativo: con B el tiempo debe crecer con n, y
con D no.

**Límites**: la construcción inicial (ordinales, entrantes y espacio del motor) es O(n + m) y ocurre al iniciar o
cargar la partida, no en cada decisión. En criptas muy
grandes los efectos de caché de memoria pueden hacer que el acceso a listas largas cueste algo más aunque se toque lo
mismo; M5 lo mide contra el umbral de 1,5×.

---

## R3. Corte por rango (FR-012, FR-033)

**Alternativas**: (A) búsqueda completa y comparar `d` con el rango al final; (B) búsqueda acotada: no insertar en la
cola ninguna sala cuya distancia supere la cota, y terminar al extraer el destino.

**Elección**: B. Una sala con distancia tentativa mayor que la cota nunca entra a la cola. Si la cola se vacía sin
extraer el destino, el resultado es «sin ruta dentro del rango», que para el cazador es lo mismo que «sin ruta»: espera
con costo 100 (FR-012). Como todo costo es ≥ 1, Dijkstra fija exactamente todas las salas con distancia ≤ cota, así
que el corte no cambia `d` cuando `d ≤ rango`.

**Interfaz**: `primer_paso(grafo, origen, destino)` del contrato de 001 no recibía cota. Se acepta agregar
`limite=None` como parámetro opcional al final (sin cota cuando es `None`), seguido de `espacio=None` (R2). Ninguna
llamada existente de «ir a» cambia ([P-01](plan.md#preguntas-abiertas), aceptada).

**Complejidad esperada**: O((|R| + |E_R|) log |E_R|), independiente de n gracias a R2.

**Evidencia a medir**: M5: criptas sintéticas en cuadrícula de 10², 10³, 10⁴ y 10⁵ salas, mismo rango y misma posición
relativa del cazador y el jugador; la cripta más grande no debe superar 1,5 veces el tiempo de la más pequeña (FR-033,
SC-007). M6 compara rango pequeño frente a rango grande en la misma cripta.

**Límites**: si el rango abarca toda la cripta, R = cripta y no hay ahorro; es lo esperado. El corte no ayuda cuando el
jugador está fuera del rango pero la región del rango es enorme: se explora toda R antes de concluir que hay que esperar.

---

## R4. Un cálculo por cazador frente a un cálculo compartido desde el jugador (FR-016, FR-018, FR-030)

**Individual (adelante)**: cada cazador ejecuta una búsqueda acotada desde su sala hasta la del jugador, por las
salidas abiertas que salen de cada sala. Es el mismo algoritmo que «ir a» (R6).

**Compartido (al revés)**: una sola búsqueda acotada desde la sala del jugador sobre el grafo **transpuesto**: por cada
sala `x` se recorren sus salidas **entrantes** `w→x` (las listas de entrantes propias de `GrafoCripta`), con el
costo y el estado de puerta **de la salida `w→x`**. Al terminar, `dist[u] = d(u, jugador)` para toda sala `u` con
distancia ≤ cota. Cada cazador decide en O(deg(u)) aplicando literalmente FR-014: entre sus salidas abiertas `u→v` con
`costo + dist[v] = dist[u]`, la vecina de menor id; si hay varias salidas a esa vecina, la de menor costo y luego
N, S, E, O.

**¿Es correcto?** Sí, con tres condiciones:

1. Dijkstra sobre el transpuesto da la distancia **hacia** el jugador en el grafo dirigido original, siempre que cada
   arista invertida lleve el costo y el estado de la salida original `w→x`.
2. La cota B debe ser ≥ el rango de todo cazador que la use. Un vecino que califica cumple `dist[v] = d − costo < d ≤
   rango ≤ B`, así que siempre está fijado; un vecino no fijado (distancia > B) nunca califica y se trata como ∞.
3. El campo debe corresponder al estado actual: misma sala del jugador y mismas puertas (R5).

**¿Cuándo cambiaría la respuesta?**

- Si para invertir se usaran las salidas que **salen** de x (x→w) en lugar de las que **entran** (w→x). Con puertas
  dirigidas (A→B cerrada, B→A abierta) o con costos distintos en cada sentido, que FR-001 y FR-003 toleran sin validar,
  la distancia sería otra. La prueba de equivalencia incluye ambos casos.
- Si la cota fuera menor que el rango de algún cazador (por ejemplo, uno que se activa a mitad del ciclo con rango
  mayor que la cota vigente): hay que recalcular con la cota nueva (R5).
- Si el campo quedara de un estado anterior (otra sala del jugador u otras puertas): R5 lo invalida.

**Complejidad esperada**

| Estrategia | Trabajo por ciclo con k cazadores, sin cambios de puertas |
|---|---|
| Individual | Σᵢ W(Rᵢ, dᵢ), donde W es la búsqueda adelante que se detiene al extraer al jugador: crece con dᵢ, no siempre con el rango completo |
| Compartido | W(R_max^rev) + Σᵢ deg(uᵢ), donde R_max^rev = salas a distancia ≤ max(rango) **hacia** el jugador |

**Punto de quiebre (hipótesis)**: el compartido gana cuando k · W̄(Rᵢ, dᵢ) > W(R_max^rev). Con rangos parecidos y
cazadores a distancia comparable al rango, k* ≈ 2. El individual gana cuando hay pocos cazadores y están cerca del
jugador (se detiene pronto), o cuando un único cazador de rango muy grande infla R_max^rev para todos. Con puertas que
cambian entre casi cada turno, el compartido se recalcula casi en cada turno y su región (alrededor del jugador, con
la cota máxima) puede ser mayor que la del individual.

**Elección**: compartido como estrategia del juego, **condicionada a M3 y M4**; individual como **referencia desde
cero** en las pruebas de equivalencia (FR-028, SC-003) y como la alternativa «recalcular siempre» del bench (FR-032).
Las dos quedan detrás de la misma función de decisión del cazador. Si M3 contradice la hipótesis, se invierte la
elección sin cambiar la spec.

**Evidencia a medir**: M3: k ∈ {1, 2, 5, 10, 25, 50} × rango ∈ {pequeño, grande}, individual frente a compartido, con
puertas estables; se reporta el k* medido.

**Límites**: el costo del compartido depende de las salas dentro de la cota alrededor del **jugador**, no de cada
cazador. Sigue sin depender del tamaño de la cripta (FR-033 se mide igual con M5), pero con rangos muy dispares la
cota máxima domina.

---

## R5. Invalidación y reutilización (FR-016, FR-024, FR-031, FR-032)

**Qué determina la decisión**: por FR-015 y FR-018, la decisión de un cazador depende solo de su sala, su rango, la
sala del jugador y el estado de las puertas, sobre el esqueleto fijo (los costos no cambian durante la partida: Fuera
de alcance). El campo compartido depende solo de la sala del jugador, el estado de las puertas y la cota.

**Tabla de eventos**

| Evento | ¿Invalida el campo compartido? | Motivo |
|---|---|---|
| Cierre o apertura de una puerta (cierre automático, `abrir`, y el deshacer de cualquiera de los dos) | **Sí** | Cambia el grafo de salidas abiertas |
| El jugador cambia de sala | **Sí** | Cambia el origen del campo |
| Se activa un cazador con rango mayor que la cota vigente | **Sí** (se recalcula con la cota nueva) | Condición 2 de R4 |
| Un cazador se mueve | No | El campo es hacia el jugador; solo cambia qué celda lee ese cazador |
| Otro actor se mueve o muere | No | FR-015: el contenido de las salas no cuenta |
| Un cazador muere | No | Deja de decidir (FR-019); el campo sirve a los demás |
| Cambio de velocidad | No | Solo cambia cuándo decide, no qué decide (FR-007) |
| Retroceso, carga, `--replay`, reconstrucción de la línea de tiempo (004) | **Sí** (se descarta) | El campo no es estado de la partida y no se guarda |

**Mecanismo elegido**: el campo guarda una **llave** `(ciclo, ordinal de la sala del jugador, versión de puertas,
cota)` y solo se reutiliza si la llave coincide y la cota es ≥ el rango del cazador que decide.

- **Ciclo**: contador que se incrementa al empezar cada ciclo de eventos (entre dos decisiones del jugador). Es la base
  de la validez **entre ciclos**: el campo vive como máximo un ciclo. Retroceder, cargar, reproducir o reconstruir
  ocurren siempre entre ciclos, así que ningún campo los sobrevive (FR-024, FR-025) sin depender de que esos caminos
  recuerden invalidar. Por eso la restauración de puertas al cargar, que vive en `Persistencia/ConversorPartida.py`,
  no se toca: basta con que `ciclo` avance.
- **Versión de puertas**: contador entero del motor que solo crece. Solo es indispensable para las escrituras **dentro
  de un ciclo**, que hoy son las del evento de cierre automático. Se mantiene para todas las escrituras de
  `salida.cerrada` del motor (cierre automático, `abrir_salida` y los deshacer de ambos), que pasan por un único método
  que lo incrementa. Los deshacer del cierre automático y de `abrir_salida`, que hoy escriben con
  `setattr(..., "cerrada", ...)`, también se registran llamando a ese método.

**Demostración de que reutilizar no cambia la decisión**: si la llave coincide, el campo se calculó en este mismo
ciclo (ningún retroceso, carga, replay ni reconstrucción ocurrió en medio), con la misma sala del jugador y el mismo
estado de todas las puertas que hay ahora (dentro del ciclo toda escritura de puertas pasa por el método único, y el
contador nunca vuelve a un valor anterior), sobre el mismo esqueleto y costos. Dijkstra es una función de esos
datos, así que el campo es idéntico al que daría un cálculo desde cero con la misma cota. La regla de decisión solo lee
celdas con distancia ≤ rango ≤ cota (R4, condición 2), que la cota no altera. Por lo tanto la decisión es la misma que
desde cero. La prueba de equivalencia (FR-028) lo verifica turno a turno contra el individual sin reutilización.

**Ahorro esperado**: con puertas estables, una búsqueda por ciclo en lugar de k. Con puertas que cambian, una búsqueda
por tramo entre cambios; en el peor caso (un cambio entre cada par de turnos) se recalcula en cada turno, igual que sin
reutilizar.

**Alternativas descartadas**

| Opción | Por qué no |
|---|---|
| Recalcular siempre desde cero (individual por turno) | Es la referencia y la alternativa medida (FR-032); se descarta como estrategia del juego solo si M4 la muestra peor |
| Ruta recordada por cazador, seguida mientras sus puertas sigan abiertas | No basta revisar la ruta: una puerta que se **abre** en otro lado puede crear una ruta más barata (escenario 2 de la US4) y el cazador seguiría la vieja |
| Búsqueda incremental (LPA*, D* Lite) | Complejidad de implementación y de prueba alta para el alcance del curso; el campo por ciclo ya da el ahorro principal |
| Firmas o hash del estado de puertas | Recorrer las puertas para calcular la firma es O(m) por decisión; el contador es O(1) |

**Evidencia a medir**: M4: tres escenarios con 50 cazadores activos: puertas estables, puertas inestables (un cambio
cada pocos eventos) y recalcular siempre. Se reporta mediana y p95 del ciclo y cuántas búsquedas se hicieron.

**Límites**: dentro de un ciclo, toda escritura de `salida.cerrada` en `Modelo/` debe pasar por el método único. Una
prueba recorre los caminos del motor (cierre automático, abrir, deshacer de ambos) y comprueba que la versión cambia;
otra lee el código fuente de `Modelo/` y falla si aparece, fuera del método único, una asignación de `cerrada` en
cualquiera de sus tres formas: `.cerrada =`, `setattr(..., "cerrada", ...)` o `_asignar_reversible(..., "cerrada", ...)`.
Esa prueba excluye por nombre `Modelo/prueba_actores.py`, que es un archivo de pruebas manuales de la Parte I alojado en
`Modelo/` y arma sus salas a mano (escribe `.cerrada = True` sobre un escenario propio, no sobre un motor en un ciclo);
la exclusión queda escrita en la prueba con su motivo. Las escrituras fuera de `Modelo/` (la restauración al cargar en `Persistencia/`) ocurren entre ciclos y quedan cubiertas
por `ciclo`. Si alguna vez una escritura fuera de `Modelo/` ocurriera dentro de un ciclo, la prueba de equivalencia lo
detectaría como discrepancia.

---

## R6. Desempate por menor id en cualquier orden de recorrido (FR-014, contrato de 001)

**Compartido**: la decisión aplica la definición de FR-014 sobre las salidas de `u`; el orden en que la búsqueda fijó
las salas no interviene.

**Individual (adelante)**: además de `dist`, cada sala guarda `primero[x]`: la vecina del origen por la que empieza la
mejor ruta conocida hasta x, la de menor id entre todas las rutas de costo mínimo.

- Al relajar `y→x`: si `dist[y] + c < dist[x]`, se copia `primero[x] = primero[y]`; si es **igual**, se queda con el
  de menor id.
- Es correcto porque todo costo es ≥ 1: cualquier predecesor óptimo `y` de `x` tiene distancia estrictamente menor y se
  extrae antes, así que `primero[y]` ya es definitivo cuando se usa. El orden de la cola entre salas de igual
  distancia no importa.
- Para las vecinas directas del origen, `primero[v] = v`, y la salida elegida hacia v es la de menor costo; ante igual
  costo, la primera en el orden N, S, E, O, sin importar el orden en que `aristas` las entregue.

**Comparación de ids**: una sola función, la misma que usa «ir a» (001 FR-024). Si ese criterio cambia, cambia para los
dos (Assumptions de la spec).

**Evidencia a medir**: no es de rendimiento. La tabla de casos de desempate de `tests/test_ruta_contrato.py` corre
contra las dos estrategias, permutando el orden de `aristas`, más el caso de empate decidido lejos del origen.

**Límites**: ninguno conocido mientras los costos sean ≥ 1. Con costo 0 la propiedad «el predecesor se extrae antes»
no valdría; FR-001 rechaza ese caso.

---

## R7. Costo del movimiento en el motor (FR-004, FR-005, FR-006, FR-007, FR-034)

**Alternativas**: (A) que cada comportamiento calcule su propio costo; (B) un único punto: después de que el actor
actúa, el costo de reprogramación es `motor.costo_salida(salida)` si se movió por una salida y el de la Parte I en otro
caso.

**Elección**: B.

| Lugar (hoy) | Hoy | Cambio |
|---|---|---|
| `ejecutar_evento`, rama `Enemigo`, `self.proxima_accion(actor, 100)` | 100 siempre | La rama recuerda la salida usada (`salida_errante`, `salida_rastro` o la del cazador) y, si `mover_enemigo` devolvió `True`, reprograma con `costo_salida(salida)`. Atacar, esperar o un movimiento fallido siguen con 100 |
| `mover_jugador`, `self.proxima_accion(jugador, costo=100)` | 100 siempre | `costo_salida(salida)`. Cubre cada paso de «ir a», que es una sucesión de `mover` |
| `activar_enemigo`, `proxima_accion(enemigo, 100)` | 100 | Sin cambio (FR-034: primera acción con costo base 100) |
| `esperar`, `atacar`, usar, abrir y demás | Sus costos | Sin cambio (FR-005) |
| `cambiar_velocidad` | Escala el restante | Sin cambio: ya aplica P1 §2.3 a cualquier acción, incluido un movimiento (FR-007) |

**Complejidad esperada**: O(1) adicional por acción.

**Evidencia a medir**: M8 repite las mediciones de la agenda de la Parte I §4.1 con la carga nueva (intervalos
variables por costo), antes y después (enunciado §5.6).

**Límites**: los errantes y rastreadores no cambian su elección (FR-006); solo su tiempo. SC-006 lo verifica con las
pruebas existentes.

---

## R8. Coordinación de datos (FR-001, FR-002, FR-008, FR-009)

**Elección**: esta capacidad solo **lee** `salida.costo` (con `motor.costo_salida`, que da 100 si falta) y el rango
de la ficha del enemigo. Agregar los campos al DTO `Salida`, a la ficha del enemigo, a la caché en disco y al paquete
offline, con su versión de formato, lo implementa la capacidad de datos (FR-008). Esta capacidad aporta la prueba de
que el costo se conserva en la caché.

**Límites**: FR-001 y FR-009 piden rechazar la cripta ante un costo o un rango inválidos. La spec no dice quién
implementa esa validación. **Propuesta, pendiente de acuerdo** ([P-02](plan.md#preguntas-abiertas)): la hace la
capacidad de datos al convertir el JSON (`Salida.desde_json`, de `DTOS/Salida.py`, y `FichaEnemigo.desde_json`, de la
clase `FichaEnemigo` definida en `DTOS/FichaCatalogo.py`), y esta capacidad aporta las pruebas de rechazo.

---

## R9. Mediciones con `--bench`

Todas en `tests/`, llamadas desde `python main.py --bench`, sin red ni vista, con resultados en archivo como los bench
existentes. Criptas sintéticas generadas en `tests/` (Constitución IV).

| Id | Qué se mide | Variables | Criterio |
|---|---|---|---|
| M1 | Decisión de **un** cazador frente a **muchos** | k ∈ {1, 50} | Informativo |
| M2 | Cola de prioridad (R1) | B frente a agenda y a lineal; región 10 a 10 000 | Justifica R1 |
| M3 | Compartido frente a individual (R4) | k ∈ {1, 2, 5, 10, 25, 50} × rango pequeño/grande | Reporta k*; confirma o invierte R4 |
| M4 | Estables frente a inestables frente a recalcular siempre (R5) | 50 cazadores activos | Ciclo < 20 ms en los dos escenarios (FR-030, FR-031); justifica la reutilización (FR-032) |
| M5 | Tamaño de la cripta con rango fijo (R2, R3) | n ∈ {10², 10³, 10⁴, 10⁵}; control con listas nuevas por búsqueda | Mayor ≤ 1,5 × menor (FR-033, SC-007) |
| M6 | Rango pequeño frente a grande | misma cripta | Informativo: el costo crece con R |
| M7 | 50 cazadores activos en la cripta de referencia | ciclo completo, mediana y p95 | < 20 ms (FR-030, SC-004) |
| M8 | Agenda de la Parte I §4.1 con la carga nueva | antes y después de los costos variables | Comparación (enunciado §5.6) |

Para M4 y M7 los 50 cazadores se activan antes de medir (FR-030). El «antes» de M8 se toma del código previo a esta
capacidad y se guarda junto al «después».
