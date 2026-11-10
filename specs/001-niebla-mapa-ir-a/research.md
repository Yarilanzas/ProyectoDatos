# Research: Niebla de guerra, mapa conocido y «ir a»

**Fecha**: 2026-11-06 | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Notación usada en todo el documento: `n` = salas de la cripta; `e` = salidas de la cripta; `k` = salas reveladas
(exploradas + avistadas); `p` = puertas con recuerdo; `r` = salas reveladas por una operación; `d(s)` = salidas que
salen de `s` más las que entran a `s`; `V`, `E` = salas y salidas del subgrafo conocido que usa «ir a».

Las complejidades de este documento son análisis. Cualquier afirmación de tiempo real es **hipótesis** hasta que
la respalde `python main.py --bench` (Principio VIII); las mediciones están definidas en [R9](#r9-qué-se-mide-con---bench).

---

## Hallazgos sobre el código actual

Estos hechos se comprobaron leyendo el código o ejecutando un experimento en una carpeta temporal, sin cambiar el
repositorio. Condicionan varias decisiones.

| # | Hallazgo | Evidencia | Efecto |
|---|----------|-----------|--------|
| H1 | **`--replay` no reproduce hoy una partida cargada y continuada.** Al cargar, el azar se vuelve a sembrar desde el inicio, la agenda se reconstruye y los efectos temporales se pierden; el replay no hace nada de eso. | Experimento con la cripta de `tests/test_integracion.py` y una rata de 200 de vida: `e`, `atacar`, guardar, cargar, 3 × `esperar`. Divergió en 20 de 20 semillas. Siempre en `secuencia` y estado del azar, y en algunas también en la vida. | Sin arreglo, FR-017, SC-004 y el Principio III no se cumplen ([R4](#r4-replay-de-partidas-cargadas-fr-017)). Con niebla es peor: tras cargar la antorcha queda apagada en el juego y encendida en el replay, así que el conocimiento diverge. |
| H2 | **Tras cargar, las puertas de una sala aún no restaurada valen lo del esqueleto.** | Experimento: abrir `1→2`, pasar a 2, guardar, cargar. Con la sala 1 sin restaurar, `1→2` vuelve a estar cerrada en memoria. | Una observación de puerta (FR-006) leería un estado falso ([R3](#r3-persistencia-del-conocimiento-fr-015-y-fr-016)). |
| H3 | **Cada `Salida` es dirigida y tiene su propio `cerrada`.** En los 3 esqueletos locales, toda puerta cerrada `A→B` tiene su inversa `B→A` abierta; `abrir` solo cambia un sentido. | `datos_locales/esqueleto_*.json`, `MotorSimulacion.abrir_salida`. | La memoria debe ser por salida dirigida, y estar en una sala debe observar también las salidas que **entran** ([R1](#r1-representación-del-conocimiento-fr-001-a-fr-011)). Ver pregunta P-05 del plan. |
| H4 | `main.py` crea `VistaConsola` antes de la rama `--replay`. | `main.py`, `vista = VistaConsola()`. | Incumple el Principio II ya hoy; este plan lo corrige porque toca `--replay`. |
| H5 | `mover_jugador` usa `costo=100` escrito en el código; `DTOS/Salida.py` no tiene costo. | `MotorSimulacion.py`, `DTOS/Salida.py`. | La spec asigna el campo `costo` y su cobro en `mover` a la capacidad de terreno y costos; esta capacidad solo lee el costo ([R7](#r7-costo-de-cada-salida)). |
| H6 | `CERRAR_PUERTA` emite «Una puerta se cerró sola.» esté donde esté el jugador. | `MotorSimulacion.ejecutar_evento`. | Revela un cambio no observado; viola FR-007 y FR-012 ([R8](#r8-lo-que-la-interfaz-muestra-hoy-sin-pasar-por-el-conocimiento)). |
| H7 | `Salida` y los dobles de prueba aceptan atributos nuevos. Hay pruebas con ids de texto y motores armados sin `iniciar_partida`. | `tests/test_puertas.py`, `tests/bench_motor.py`, `motor._destino` ya guarda un atributo en la salida. | El conocimiento trata los ids como opacos, y el motor tolera `conocimiento is None`, para que las pruebas de la Parte I sigan sin cambios (SC-006). |
| H8 | Ninguna salida paralela (dos salidas de una sala a la misma vecina) y ninguna salida de un solo sentido en los esqueletos locales. Son 3 criptas de ejemplo; nada garantiza que sea siempre así. | Recorrido de `datos_locales/esqueleto_*.json`. | El diseño no depende de esto (pregunta P-03 del plan). |

**Línea base de pruebas**: en este entorno ni el Python del sistema ni el de `.venv` tienen `requests`, y
`unittest discover` da 2 errores de importación sobre 88 pruebas cargadas (`test_integracion`, `test_puntajes`).
Con un módulo `requests` sustituto, sin red y fuera del repositorio, pasan **128 de 128**. Es un problema del
entorno, no del código, y debe resolverse instalando `requests` antes de implementar.

---

## R1. Representación del conocimiento (FR-001 a FR-011)

**Decisión**: una clase `Conocimiento` en `Modelo/Conocimiento.py` con **arreglos densos** indexados por ordinales
fijos, más dos listas de lo revelado:

- `estado_sala[ordinal]`: desconocida, avistada o explorada.
- `recuerdo_puerta[ordinal]`: sin observar, abierta o cerrada, **por salida dirigida**.
- `reveladas` y `observadas`: listas en orden de revelación, para recorrer solo lo conocido.

Los ordinales se asignan una sola vez al iniciar la partida: las salas en el orden de `_indice_salas` (por id), las
salidas por orden de recorrido. Cada sala y cada salida guarda su ordinal como atributo, igual que `salida._destino`.
Con la referencia al objeto, consultar es un acceso directo al arreglo.

**Justificación**:

- La consulta es O(1) y no depende del tamaño del mapa.
- Explorar solo escribe celdas de las salas reveladas: el costo no depende de cuánto se conoce ya. El arreglo se
  crea una sola vez, al inicio (O(n + e)), nunca durante la partida.
- Los ids pueden no ser densos ni numéricos (H7): por eso los ordinales son propios y no el id.
- `mapa` y el guardado recorren `reveladas` y `observadas`, no toda la cripta: cuestan según lo conocido.
- Separar el conocimiento de `Sala` deja a la vista lo que protege FR-012: el mapa real y lo que sabe el jugador son
  objetos distintos.
- Un arreglo y una lista no sustituyen a ninguna estructura prohibida. No se usa `dict` ni `set` como índice.

**«Avistada» se guarda, no se calcula en cada consulta.** FR-004 la define por una condición que requeriría recorrer
las salidas entrantes en cada consulta. Como explorar solo agrega, al explorar `s` basta marcar como avistadas las
vecinas que estaban desconocidas. Revertir deshace cada escritura por el registro de cambios, así que tampoco hacen
falta contadores de referencias.

**Observación**: al estar en una sala se observan sus salidas y las que entran a ella (H3). Para eso se construye una
vez la lista `entrantes` de cada sala, que no se muestra al jugador (FR-013). El recuerdo se guarda aunque la sala de
origen no esté explorada: así, si la antorcha la explora después, una salida ya observada no aparece como «sin
observar», mientras que las nunca observadas sí (FR-011).

| Operación | Arreglos densos (elegida) | Lista ordenada + binaria | Tabla hash propia | Atributos en `Sala` |
|-----------|---------------------------|--------------------------|-------------------|---------------------|
| Consultar sala o puerta | O(1) | O(log k) | O(1) promedio | O(1) |
| Revelar `r` salas | O(r + Σd) | O(r·k): desplaza elementos | O(r) promedio; O(k) al crecer | O(r + Σd) |
| Revertir un cambio | O(1) | O(k) | O(1) promedio | O(1) |
| Listar lo conocido | O(k) | O(k) | O(capacidad) | O(n) |
| Memoria | O(n + e) | O(k) | O(k) | O(n + e) |

**Alternativas descartadas**:

- **`dict`/`set` por id**: prohibido como índice (Principio I).
- **Lista ordenada + búsqueda binaria**: es el patrón de `_indice_salas`, pero insertar desplaza elementos y el costo
  de explorar crece con el mapa conocido, justo lo que se pide evitar.
- **Tabla hash propia**: cumple las cotas en promedio, pero añade redimensionado y colisiones para resolver un
  problema que los ordinales resuelven sin esa estructura. Solo ahorraría memoria si `k` fuera mucho menor que `n`.
- **Atributos en `Sala`/`Salida`**: igual de rápido, pero mezcla mapa real y conocimiento, y facilita violar FR-012 por
  descuido. Además listar exigiría recorrer toda la cripta.
- **Puerta como par no dirigido**: los datos no lo permiten, porque `A→B` y `B→A` tienen estados distintos (H3).

---

## R2. Registro de cambios en el Historial (FR-014, FR-031)

**Decisión**: `Conocimiento` registra **deltas por lote**. Cada operación pública (`entrar`, `observar_puerta`)
acumula las escrituras que **realmente cambian algo** como tuplas `(tipo, ordinal, valor_anterior)` y, si hubo
alguna, registra **un solo** `Cambio` en el `Historial`. Para deshacer, recorre el lote al revés y restaura cada
valor; si la escritura agregó un elemento a `reveladas` u `observadas`, le hace `pop`.

`Modelo/retroceso.py` **no cambia**: se usa `historial.registrar(deshacer=...)`, el contrato vigente.

**Justificación**:

- Registrar es O(1) por escritura e invertir es O(|lote|). Una entrada sin novedades no registra nada.
- `pop` es correcto porque los lotes se deshacen en orden inverso (LIFO): lo último agregado es lo primero en salir.
- Una entrada con antorcha cae en un solo lote, y por lo tanto en el intervalo de ese paso: FR-014 sale por
  construcción. Cada paso del viaje abre su propio intervalo, y así se cumple FR-031.
- La memoria extra queda acotada por el tamaño de los lotes de los últimos 5 intervalos.
- Los cierres automáticos que el jugador observa ocurren dentro del intervalo de su acción, porque los eventos se
  ejecutan en `avanzar_hasta_jugador`. Quedan incluidos sin trabajo adicional.
- Antes de la primera acción `Historial.registrar` no hace nada: la sala inicial no se puede revertir, tal como pide
  el último caso borde de la spec.

**Orden en `mover_jugador`**: el conocimiento se actualiza después de `accion_jugador()` y de mover al jugador, pero
**antes de las trampas**, porque una trampa mortal retorna de inmediato. La secuencia §2.4 (trampas, luego enemigos)
no cambia.

**Alternativas descartadas**:

- **Copiar el estado completo en cada acción**: O(n + e) por acción, proporcional al mapa. El Documento de Decisiones
  ya la descarta para el Historial, por prohibición del enunciado y por costo.
- **Un cierre (`lambda`) por escritura**: es el estilo del motor y funciona, pero crea un `Cambio` y una función por
  cada sala o puerta. El lote cuesta lo mismo en asintótica con menos objetos. Que eso sea más rápido en la práctica
  es una hipótesis que mide M3.
- **Recalcular el conocimiento desde las acciones**: imposible de hacer exacto sin repetir la partida.

---

## R3. Persistencia del conocimiento (FR-015 y FR-016)

**Decisión**: un **bloque nuevo de conocimiento**, con su largo, entre el bloque del jugador y las salas. Se lee una
vez al cargar. `VERSION_FORMATO` pasa de **2 a 3**. Detalle en [contracts/formato-partida.md](contracts/formato-partida.md).

El bloque guarda tres listas ordenadas de forma canónica por `(sala, dirección)`, para que el mismo estado produzca
los mismos bytes:

1. ids de salas **exploradas**;
2. **puertas recordadas** (solo las observadas);
3. **puertas reales** que pueden cambiar de estado (corrige H2).

Las **avistadas no se guardan**: FR-004 las define a partir de las exploradas y del esqueleto, y se recalculan en
O(Σ salidas de las exploradas). Guardarlas permitiría un archivo incoherente.

**Por qué la lista de puertas reales**: al entrar a una sala se observan las salidas que entran, y su sala de origen
puede no estar restaurada aún (H2). Con esta tabla leída al cargar, `salida.cerrada` es correcta para todas las
salas sin leer sus bloques: la carga de salas sigue siendo perezosa. También corrige, de paso, que un enemigo cruce
puertas de una sala no restaurada con el estado del esqueleto. `_aplicar_registro` puede volver a aplicar
`RegistroSala.puertas` sin riesgo: una puerta de una sala sin restaurar no puede cambiar después de cargar, porque
para abrirla el jugador tiene que estar en esa sala (ya restaurada).

**Rechazo de versiones anteriores**: lo hace el código actual, `EncabezadoPartida.from_bytes` compara
`VERSION_FORMATO` y lanza `VersionIncompatible` (código de salida 2). `partida.cripta` y `partida.cripta.log`, que
hoy están versionados, quedan obsoletos.

**Alternativas descartadas**:

- **Dentro de `RegistroSala`**: las salas exploradas con antorcha no tienen registro (no se cargó su contenido), y el
  bloque de sala se lee de forma perezosa. El mapa completo se necesita al cargar.
- **Dentro de `RegistroJugador`**: funciona, pero mezcla responsabilidades y complica el exportador; un bloque propio
  se prueba aparte y mantiene intacto el registro del jugador.
- **Mapa de bits por ordinal**: tamaño fijo O(n + e) sin importar cuánto se haya explorado, y el archivo dependería
  del orden interno. Identificar por `(sala, dirección)` es más legible, se valida contra el esqueleto y se detectan
  archivos dañados.
- **Restaurar todas las salas al cargar** (para H2): rompe la carga perezosa de §4.10 y
  `test_carga_perezosa_solo_lee_la_sala_actual`.
- **Leer el registro de la sala de origen en cada observación** (para H2): lecturas de disco repetidas dentro del
  turno, y exige marcar qué parte de cada sala ya se aplicó.

**`ExportadorJSON`** debe guardar lo mismo que el binario, porque existe para compararlos («guarda los mismos
datos»). También incluye el conocimiento.

---

## R4. Replay de partidas cargadas (FR-017)

**Decisión**: la bitácora registra el punto de carga con una **línea directiva `@cargar`** y `--replay` repite ahí el
mismo ciclo de guardar y cargar que hizo la partida real, usando un archivo temporal. Formato en
[contracts/formato-bitacora.md](contracts/formato-bitacora.md).

**Justificación**:

- H1 viene de que cargar **cambia el estado**: reinicia el azar, reconstruye la agenda y descarta efectos. Eso es
  comportamiento acordado («tras cargar la antorcha está apagada»), así que el replay tiene que hacer lo mismo.
- Reusa el código real de guardado y carga: no hay una segunda definición de qué se pierde al cargar, y el
  conocimiento pasa por la misma serialización.
- `_continuar_bitacora` ya copia la bitácora del guardado, así que `@cargar` queda justo detrás de las acciones
  anteriores a ese guardado.
- `retroceder` después de cargar se reproduce bien, porque el Historial también se reinicia en el replay.

**Implementación**: `leer_bitacora` conserva `@cargar` como una tupla más de `acciones`. `Reproductor` recibe un
parámetro opcional `recargar(motor) -> motor` y `main.py` le pasa una función que guarda en un temporal y llama a
`cargar_partida`. Para eso, la parte de guardado de `ControladorPartida.guardar` se extrae a una función sin vista.
Después de cada recarga hay que cerrar el restaurador anterior: en Windows no se puede borrar un archivo abierto.

**Costo**: cada `@cargar` cuesta un guardado y una carga. Con red, cargar llama a `obtener_detalles` e
`iniciar_cripta`, y hay que comprobar que eso no gaste presupuesto de más en un replay (Principio VII); el esqueleto
ya se lee de la caché en disco. La prueba de presupuesto queda en el plan.

**Alternativas descartadas**:

- **Guardar azar, agenda y efectos para que cargar no cambie nada**: contradice la spec y el README («los efectos no
  se guardan») y obliga a serializar eventos con referencias a actores.
- **Guardar solo el estado del azar**: no resuelve `secuencia`, efectos ni cierres pendientes; H1 muestra divergencia
  también en `secuencia`.
- **Reproducir desde el último guardado**: no es la partida completa que exige el Principio III.

**Impacto**: el README dice hoy que `cargar` no se anota. Esa frase cambia. Es un contrato compartido y debe avisarse
al grupo (pregunta P-07).

---

## R5. Comandos nuevos y bitácora (FR-018 a FR-022, FR-030)

**Decisión**:

- `mapa` es un comando de consulta del controlador: pide `motor.mapa_conocido()`, un DTO `MapaConocido`, y lo pasa a
  `vista.mostrar_mapa`. No toca el reloj ni la bitácora, igual que `inventario`.
- `ir a <sala>` lo orquesta el controlador con un objeto `Viaje` del modelo. `Viaje` decide (recalcular, detenerse,
  motivo); el controlador ejecuta cada paso con `ejecutar_accion("mover", direccion)` y anota la bitácora. Así el
  replay solo ve `mover`, y `ejecutar_accion` y `ACCIONES` no cambian.
- `ir` se reconoce como comando y su argumento debe tener la forma `a <sala>`. `ir` solo o mal formado es un error
  de uso. `ayuda` y el README agregan los dos comandos.
- La **línea de comentario** `# ir a <sala>` se escribe después de que el motor acepte el primer paso y antes de la
  línea de ese paso. Así una orden rechazada no deja rastro (FR-022, SC-005), tampoco si el primer `mover` falla.

**Resolver el destino**: se busca el texto del argumento comparándolo con `str(sala.id)` **solo entre las salas
exploradas**, O(k). No hace falta convertir a entero (H7), y una sala inexistente, desconocida o avistada producen
por construcción el mismo rechazo, sin revelar si existe.

**Comprobación de vida (FR-027c)**: se compara la vida antes y después del paso. La única curación del jugador en el
código es `usar`, que no ocurre dentro de un viaje, así que no puede ocultar un daño.

**Enemigos al entrar (FR-027b)**: se evalúa **al entrar**, no al final del paso, porque un enemigo errante puede
salir antes de la siguiente decisión. `mover_jugador` guarda el resultado justo antes de activar enemigos, en un
indicador transitorio que `Viaje` lee enseguida. Solo cuentan los enemigos vivos, y no se evalúa en la sala de partida
(FR-028).

**Prioridad del motivo**: si coinciden varias condiciones se informa una: fin de partida, luego daño, luego enemigos,
luego llegada.

**Formato v2**: el comentario hace que el lector v1 falle, porque tomaría `#` como nombre de acción. Por eso
`VERSION_BITACORA` pasa de 1 a 2 (FR-030). Por el Principio VI, una bitácora v1 se rechaza.

**Alternativas descartadas**:

- **Acción `ir_a` en la bitácora**: el replay tendría que recalcular rutas. FR-030 pide movimientos individuales.
- **Viaje dentro del controlador**: las reglas de parada son reglas del juego, y no podrían probarse sin controlador.
- **Viaje dentro de `ejecutar_accion`**: una acción que produce varias líneas rompe la regla «cada acción aceptada,
  una línea».

---

## R6. Búsqueda de la ruta de «ir a» (FR-023, FR-024, FR-026)

### DECISIÓN (D-PEND-01): ¿comparte implementación con el cazador?

**Estado: ✅ resuelta con la opción A.** Persona A implementa la búsqueda compartida en `Modelo/BusquedaRuta.py`, con la
cola de prioridad en `Modelo/ColaPrioridad.py`, y cumple la interfaz `primer_paso` de
[contracts/interfaz-ruta.md](contracts/interfaz-ruta.md). `Modelo/rutas_ir_a.py` solo la llama. **La opción B queda
descartada.** La comparación que preparó la decisión se conserva como registro.

| | **Opción A: implementación compartida (elegida)** | **Opción B: implementaciones separadas (descartada)** |
|---|---|---|
| **Qué es** | Un solo Dijkstra con desempate, parametrizado por el grafo. «ir a» le pasa `GrafoConocido`; el cazador, su vista del mapa real. | «ir a» tiene su búsqueda y el cazador la suya. |
| **Ventajas** | Una sola definición del desempate, y FR-024 pide «el mismo desempate que el cazador». Una sola estructura que documentar, probar y medir. Menos código. | Cada una se ajusta a su uso. Sin dependencia de calendario. Un cambio en una no puede romper la otra. Más simple de revisar. |
| **Costos** | Acordar una abstracción común antes de implementar. Es un contrato compartido (no se cambia sin avisar). Cualquier cambio afecta a dos capacidades. Si el cazador corre en cada ciclo de enemigos, la abstracción cuesta en el camino crítico de 20 ms. Puede forzar a generalizar de más. | Dos implementaciones del mismo algoritmo y del mismo desempate, que pueden divergir. Doble código, pruebas y mediciones. Hay que justificar la duplicación en el Documento de Decisiones. |
| **Riesgo principal** | Las dos búsquedas pueden no ser la misma consulta: «ir a» pide origen → destino una vez por paso; el cazador podría necesitar distancias desde el jugador para muchos enemigos. | Que el desempate difiera sin que nadie lo note. Se mitiga con una tabla de casos de desempate común a ambas pruebas. |
| **Qué cambia en este plan** | Solo el cuerpo de `Modelo/rutas_ir_a.py`, que delega | Solo el cuerpo de `Modelo/rutas_ir_a.py`, que implementa |

**Lo que hacía falta saber para decidir** (registro; con la opción A, son responsabilidad de Persona A en
`Modelo/BusquedaRuta.py`):

1. ¿Es una consulta origen → destino, o de una fuente hacia todas las salas?
2. ¿Sobre qué grafo corre (puertas reales, solo abiertas, costos)?
3. ¿Con qué frecuencia se recalcula, y cuenta para el límite de 20 ms del ciclo?
4. ¿Quién mantiene el código compartido si se elige A? **Persona A.**

### Lo que se decide: la frontera

La búsqueda queda detrás de una **interfaz de una sola función**
([contracts/interfaz-ruta.md](contracts/interfaz-ruta.md)):

```text
primer_paso(grafo, origen, destino) -> Paso | None
```

`Viaje` solo conoce esa función, recibida como parámetro con su valor por defecto en `Modelo/rutas_ir_a.py`, y
`grafo` solo expone las aristas transitables. Como la ruta se recalcula antes de cada paso (FR-026), basta devolver
el primer paso.

**Qué no depende de `Modelo/BusquedaRuta.py`**: `Conocimiento`, `GrafoConocido`, `Viaje`, controlador, vista,
persistencia, bitácora, las pruebas de viaje (pueden correr con un buscador de prueba) y las pruebas de contrato. **Qué
sí depende**: el cuerpo de `primer_paso`, que delega en el módulo de Persona A. La cola de prioridad la aporta ese código
compartido (`Modelo/ColaPrioridad.py`), no esta capacidad.

### Requisitos que debe cumplir la implementación compartida (Persona A)

- Corre solo sobre `GrafoConocido`: salas exploradas y salidas recordadas abiertas. Las salidas cerradas o sin
  observar no existen para la búsqueda (FR-011, FR-023, FR-029).
- Minimiza la suma de costos y desempata por la vecina de menor id en el **primer** paso (FR-024).
- No usa `heapq` ni `networkx`; cola de prioridad a mano (Principio I).
- Determinista: misma entrada, misma salida (Principio III).

### Referencia de complejidad, no vinculante

Un Dijkstra hacia adelante con etiqueta lexicográfica `(costo, id de la primera vecina)` y cola binaria propia cuesta
O((V + E) log V) por cálculo, y S pasos cuestan S veces eso. La etiqueta es correcta porque sumar un costo conserva el
orden entre etiquetas, y permite parar al extraer el destino. Marcar cada arreglo con un número de «época» evita
limpiar O(n) en cada búsqueda. Esto describe una forma posible de cumplir el contrato; **no obliga a Persona A**, que
documenta la complejidad de su implementación (obligación 7).

### Alternativas de frontera descartadas

- **Devolver la ruta completa**: FR-026 la invalida en cada paso, y obliga a toda implementación a reconstruirla.
- **Pasar `Conocimiento` directamente**: ata la interfaz a esta capacidad y dificultaría la opción A.
- **Clase con estado**: nada se conserva entre cálculos; una función basta.

---

## R7. Costo de cada salida

**Decisión**: esta capacidad **solo lee** el costo de cada salida, por un **único acceso**:

- `MotorSimulacion.costo_salida(salida)` devuelve `getattr(salida, "costo", None)`, o `COSTO_MOVER = 100` si la salida
  no trae costo. Es la regla de `mover` de la Parte I, no un dato de una cripta (Principio IV), y va junto a
  `COSTO_USAR`. No escribe nada.
- `MapaConocido` y `GrafoConocido` usan solo ese acceso. **Ni `Conocimiento`, ni `Viaje`, ni `rutas_ir_a` contienen
  un número de costo.**
- Esta capacidad **no** agrega el campo `costo` a `DTOS/Salida.py` ni cambia el movimiento de ningún actor
  (`mover_jugador`, `mover_enemigo`, `ejecutar_evento`). Ambas cosas son de la capacidad de terreno y costos
  (spec, Assumptions; tareas T006 a T012).

**Justificación**: cuando la otra capacidad agregue el campo, solo cambia de dónde sale el dato; el acceso ya existe y
nada más hay que tocar aquí. Mientras ninguna salida traiga costo, todas valen 100 y la ruta y el reloj coinciden, así
que se cumple FR-025 y el comportamiento de la Parte I no cambia. Para no romper FR-025, la otra capacidad debe agregar
el campo y cobrarlo en `mover` en el mismo cambio (T010 y T011).

Las salidas de los dobles de prueba y el DTO actual no tienen el atributo, por eso el acceso usa `getattr`.

**Alternativas descartadas**:

- **Fijar 100 en el esqueleto o en `desde_json`**: no distingue «sin costo propio» de «cuesta 100», y escribe la regla
  en un DTO y en la caché de disco.
- **Constante en `rutas_ir_a`**: es exactamente lo que se pide evitar.
- **Agregar el campo y cambiar `mover` en esta capacidad**: invade la capacidad de terreno y costos y cambia un
  contrato compartido (`Salida`) sin ser su responsable.

**Resuelto** (enunciado §3.1 y §4.1; P-02 del plan): el campo JSON se llama `costo`, es un entero mayor o igual que 1,
vale 100 si la salida no lo declara y es el mismo en ambos sentidos. Con ese dominio se cumple la precondición de
costos no negativos de la búsqueda. Quién agrega el campo y cambia `mover`: la capacidad de terreno y costos.

---

## R8. Lo que la interfaz muestra hoy sin pasar por el conocimiento

FR-012 exige que todo lo que se muestre sobre topología salga del conocimiento. Se revisaron las rutas de salida:

| Punto | Hoy | Plan |
|-------|-----|------|
| `VistaConsola._texto_salidas` | lee `salida.cerrada` real | usa el recuerdo. En la sala actual coinciden (FR-006), pero la fuente debe ser una sola. |
| Mensaje «Una puerta se cerró sola.» (H6) | se emite siempre | se emite solo si el jugador observa la puerta. El evento y el cierre real no cambian. |
| Mensaje «La trampa X se rearmó.» | se emite siempre | **Sin cambio en este plan**: no es topología, y FR-010 solo habla de la antorcha. Pregunta P-06. |
| Llave de la salida en `mostrar_estado` | se muestra en la sala actual | sin cambio: comportamiento de la Parte I. `mapa` no la muestra, FR-018 no la incluye. |
| `gestor`, precarga | usan el esqueleto completo | sin cambio (FR-013). |

Filtrar el mensaje no cambia la simulación: `obtener_estado_resumen` no incluye mensajes y el reloj no depende de
ellos.

---

## R9. Qué se mide con `--bench`

Una medición nueva, `tests/bench_niebla.py`, con salas sintéticas (ningún dato de una cripta real) y sin red ni vista.
`main.py --bench` la agrega y escribe `resultados_bench_niebla.txt`, con equipo y versión de Python, como las demás.
Cada dato es la mediana de varias repeticiones, y el ciclo también informa p95.

| ID | Qué se mide | Variantes y tamaños | Hipótesis (Principio VIII) | Respalda |
|----|-------------|---------------------|----------------------------|----------|
| **M1** | Consultar estado de sala y recuerdo de puerta | arreglos densos, lista ordenada + binaria, lista lineal; n = 20, 200, 2000, 20000 | El tiempo de los arreglos no crece con `n`; la binaria crece con log n | R1 |
| **M2** | Revelar un número fijo de salas con distinto mapa ya conocido | r fijo, k = 10, 100, 1000, 10000; arreglos frente a lista ordenada | Con arreglos no crece con `k`; con lista ordenada sí | R1 |
| **M3** | Registrar y deshacer el cambio de una entrada con antorcha | lote, cierres por escritura, copia completa; varios `r`, varios `n` | Lote y cierres crecen con `r`; la copia crece con `n` | R2 |
| **M4** | Tiempo de `primer_paso` y de un viaje completo | mapa conocido completo de la cripta de referencia, más grilla y cadena con V = 25, 100, 400, 2500; por la interfaz, sirve para A y B | Con la cripta de referencia, el cálculo de un paso cumple el límite de 5 ms de §6.1 | R6 |
| **M5** | Tamaño y tiempo del bloque de conocimiento; bytes leídos al cargar | k = 20, 200, 2000; binario frente a JSON | El bloque crece con lo conocido; cargar sigue sin leer todas las salas | R3 |
| **M6** | Ciclo completo entre decisiones, con conocimiento activo | `bench_ciclo` con y sin conocimiento; 10 a 500 enemigos | Sin regresión frente al límite de 20 ms de §5.2 | R1, R2 |

El límite de 20 ms viene de `tests/bench_ciclo.py` (§5.2). El límite de 5 ms viene del enunciado, §6.1, y se aplica al
cálculo de un paso de «ir a» con el mapa conocido completo de la cripta de referencia. Ese valor puede ajustarse por
enmienda, así que M4 lo toma de una sola constante. M4 informa cumple o no cumple para ese caso; los tiempos del viaje
completo y de los demás tamaños son datos de apoyo.

Si una medición contradice la hipótesis, se corrige el documento o el diseño; no se reescribe la afirmación sin
medición.
