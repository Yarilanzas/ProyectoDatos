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

**Resultados medidos (T070)**: de `resultados_bench_cazador.txt` (`tests/bench_cazador.py`, `python main.py --bench`).
Cripta sintética de 300 salas (semilla 7, costo 100 por salida), cazadores activados en salas al azar a distancia ≤
rango; una muestra es decidir los k cazadores una vez (la compartida empieza un ciclo nuevo y recalcula el campo una
vez); 40 muestras intercaladas; medianas.

| k | Rango 500 (\|R\| = 48): individual | compartida | ind/comp | Rango 2000 (\|R\| = 296): individual | compartida | ind/comp |
|---|---|---|---|---|---|---|
| 1 | 289.2 µs | 358.0 µs | 0.81 | 758.9 µs | 1.94 ms | 0.39 |
| 2 | 362.1 µs | 367.1 µs | 0.99 | 1.11 ms | 1.95 ms | 0.57 |
| 5 | 835.5 µs | 397.2 µs | 2.10 | 3.56 ms | 1.99 ms | 1.79 |
| 10 | 1.28 ms | 429.5 µs | 2.99 | 6.35 ms | 2.09 ms | 3.03 |
| 25 | 3.15 ms | 567.0 µs | 5.56 | 17.75 ms | 2.18 ms | 8.13 |
| 50 | 6.74 ms | 742.9 µs | 9.08 | 31.63 ms | 2.40 ms | 13.16 |

- **k\* medido = 5** con rango pequeño (500) y con rango grande (2000): desde k = 5 la compartida es más rápida para todo
  k mayor medido. La hipótesis (k\* ≈ 2) no se confirmó: con k = 1 y 2 gana la individual, porque se detiene al extraer
  al jugador y el campo recorre toda la cota.
- Con 50 cazadores la compartida tarda 9.08 veces menos (rango 500) y 13.16 veces menos (rango 2000); su tiempo casi no
  crece con k (de 1.94 ms a 2.40 ms con rango 2000), como predice W(R_max^rev) + Σ deg(uᵢ).
- **M2** (FR-033, R1): insertar n entradas y extraer todas. `ColaPrioridad` frente a la agenda y a la búsqueda lineal
  del mínimo, medianas: n = 10: 24.6 µs, 70.5 µs, 14.0 µs; n = 100: 360.9 µs, 943.1 µs, 755.3 µs; n = 1000: 6.23 ms,
  15.27 ms, 92.14 ms; n = 10 000: 96.50 ms, 260.88 ms, 10045.28 ms. La lineal solo gana con n = 10; con 10 000 es
  104.1 veces más lenta que la cola; la agenda es entre 2.45 y 2.87 veces más lenta que la cola en todos los tamaños.
- **M5** (FR-033, SC-007, R2, R3): decisión individual, rango 600, cazador 3 salas a la derecha del jugador en la misma
  fila, 500 llamadas de calentamiento por tamaño y 5 repeticiones de todos los tamaños. Mediana de las 5: 82.2 µs (10²
  salas), 68.0 µs (10³), 42.2 µs (10⁴), 78.7 µs (10⁵); **cociente final tiempo(10⁵) / tiempo(10²) = 0.96 ≤ 1.5:
  cumple** (cocientes por repetición: 0.93, 0.79, 0.97, 1.05, 0.97). Sin calentamiento, una corrida anterior dio 1.59
  (no cumple); que fuera una medición en frío es una hipótesis no verificada por separado, y M5 calienta antes de
  cronometrar. Entre 10⁴ y 10⁵ salas la mediana sube de 42.2 a 78.7 µs (1.87 veces); el cociente 0.96 es contra 10²,
  cuya mediana es 82.2 µs. La subida de 10⁴ a 10⁵ probablemente es efecto de caché de memoria (ver R2, Límites). Control: con un espacio
  nuevo por llamada (`espacio=None`) la misma búsqueda tarda 2.32 ms con 10⁵ salas, 53.5 veces más que reutilizando el
  `EspacioBusqueda` (43.4 µs).

**Decisión (T070)**: se confirma la elección. La estrategia por defecto del motor pasa a **"compartida"**
(`MotorSimulacion.__init__`, `estrategia_cazador`; único lugar de elección, `decidir_cazador`, sin cambios). Motivo:
desde k = 5 es más rápida con los dos rangos medidos, con 50 cazadores lo es entre 9 y 13 veces, y en el ciclo completo
(M4, R5) cumple el límite de 20 ms donde recalcular siempre no lo cumple. Cambiar la estrategia no cambia ninguna
decisión: la equivalencia turno a turno con la referencia desde cero la prueba T057 (`tests/test_cazador_equivalencia.py`),
y la individual sigue siendo la referencia de las pruebas y la alternativa «recalcular siempre» del bench (FR-032).

**Limitaciones de la medición**: cripta sintética **provisional** de 300 salas (la de referencia publicada aún no
existe; se repite cuando se publique). Equipo: Windows-11-10.0.26100-SP0, Intel Core i5-7300U @ 2.60GHz (Intel64 Family 6
Model 142 Stepping 9), Python 3.13.13. La corrida completa citada se ejecutó dentro de `python -m unittest discover`
(la prueba de `--bench` de `tests/test_bench_niebla.py` todavía no simulaba este bench); M5 se repitió sola con
`python -m tests.bench_cazador M5`. Con k = 1 y 2 la individual es más rápida: si una cripta tuviera casi siempre uno o
dos cazadores activos, la ganancia se invierte (diferencia medida: hasta 1.2 ms por ciclo con rango 2000).

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
cota, época del espacio de búsqueda)` (`Modelo/CampoDistancias.py`) y solo se reutiliza si la llave coincide y la cota
es ≥ el rango del cazador que decide. La época coincide si ninguna otra búsqueda reutilizó el `EspacioBusqueda` del
motor desde que se calculó el campo.

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

**Resultados medidos (T070)**: M4 de `resultados_bench_cazador.txt`. Cripta sintética de 300 salas, 50 cazadores de
rango 2000 en salas al azar, activados con `motor.activar_enemigo` antes de medir; 100 ciclos (`ejecutar_accion("esperar")`
hasta la siguiente decisión del jugador); búsquedas contadas en una pasada idéntica aparte, envolviendo `primer_paso` y
`campo_hacia`; cumple = p95 < 20 ms.

| Escenario | Mediana | p95 | Búsquedas (100 ciclos) | Por ciclo | ¿< 20 ms? |
|---|---|---|---|---|---|
| (a) puertas estables, compartida | 3.95 ms | **6.87 ms** | 100 (`campo_hacia`) | 1.0 | cumple |
| (b) puertas que cambian (2 por ciclo, 398 escrituras), compartida | 3.82 ms | **5.72 ms** | 100 (`campo_hacia`) | 1.0 | cumple |
| (c) recalcular siempre desde cero, individual | 2.56 ms | **29.48 ms** | 603 (`primer_paso`) | 6.0 | NO cumple |

- La reutilización hace **100 búsquedas frente a 603** y lleva el p95 de 29.48 ms a 6.87 ms (estables) y 5.72 ms
  (cambiantes): se justifica con la comparación que pide FR-032.
- La mediana de (c) es baja (2.56 ms) porque el jugador solo espera: los cazadores lo alcanzan y luego atacan sin buscar
  (6 búsquedas por ciclo en promedio). Los ciclos caros son los de la persecución, y eso lo recoge el p95.
- **M7** (FR-030, SC-004), con la estrategia que entonces era la de por defecto (**individual**), 50 cazadores con rangos
  500, 1000 y 2000: mediana 8.83 ms, **p95 19.43 ms**: cumple, pero a 0.57 ms del límite. Ese número de la individual se
  midió antes del cambio de estrategia. **M7 con la compartida** (nueva estrategia por defecto, mismo escenario,
  `python -m tests.bench_cazador M7`): mediana 2.01 ms, **p95 3.39 ms**: cumple. **M1**: decidir los 50
  cazadores con la individual (rango 2000, sin el resto del ciclo) da p95 40.49 ms frente a 597.3 µs de uno solo.

**Decisión (T070)**: ver R4: la compartida pasa a ser la estrategia por defecto. Con la llave
`(ciclo, sala del jugador, version_puertas, cota, época del espacio de búsqueda)` el campo se calcula una vez por ciclo en los dos escenarios medidos.

**Limitaciones de la medición**: las mismas de R4 (cripta sintética provisional de 300 salas, equipo, corrida dentro de
la suite). Además, **M4 (b) cambia las puertas entre ciclos, no durante un ciclo**: como el campo ya vive un solo
ciclo, esos cambios no obligan a recalcular más y (b) hace las mismas 100 búsquedas que (a). El peor caso de R5 (una
escritura de puertas entre cada par de turnos *dentro* del ciclo, por ejemplo con el cierre automático) **no se
midió**; FR-031 queda respaldado solo para cambios entre ciclos.

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

**Resultados medidos (T069)**: de `resultados_bench_agenda_despues.txt` (Intel Core i5-7300U @ 2.60GHz, Python
3.13.13; N = 10, 50, 100, 250; medianas de 5 repeticiones). (1) *Antes/después con la misma carga* (tiempos
consecutivos, `tests/bench_agenda_solo.py`, T002 frente a T069): la razón mediana después/antes es 1.20 para el heap
(`AgendaEventos`) y 1.21 para la lista. `Modelo/AgendaEventos.py` y `Modelo/Evento.py` no cambiaron desde el «antes»
(a4d6299), y la lista no usa código del motor, así que la diferencia es variación del equipo entre corridas, no un cambio
de la agenda. (2) *Carga nueva frente a carga antigua en la misma corrida* (`tests/bench_agenda_costos.py`: 10 actores,
intervalo `max(1, costo * 100 // velocidad)`, costos 50 a 300, velocidades 50, 100 y 200): 30 de 32 razones nueva/antigua
son ≤ 1.5. Las dos mayores son «Buscar un evento», lista N=50 = 2.67 y heap N=50 = 1.75, con lecturas por debajo de
5 µs, en una operación que no compara tiempos. Insertar todos con el heap y N=250 da 1.46, y extraer todos con el heap y
N=250 da 0.84. Conclusión, con cautela: con estas mediciones la agenda no se degrada con intervalos variables por costo;
son medianas de 5 repeticiones en un solo equipo, no una demostración.

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
