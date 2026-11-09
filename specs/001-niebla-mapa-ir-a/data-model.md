# Modelo de datos: Niebla de guerra, mapa conocido y «ir a»

**Fecha**: 2026-11-06 | **Plan**: [plan.md](plan.md) | **Decisiones**: [research.md](research.md)

Notación: `n` salas, `e` salidas, `k` salas reveladas, `p` puertas con recuerdo, `r` salas reveladas por la
operación, `d(s)` salidas que salen de o entran a `s`, `V`/`E` subgrafo conocido.

Todas las complejidades de este documento deben copiarse al docstring de cada estructura propia (Principio I).

---

## Entidades nuevas

### `Conocimiento` (`Modelo/Conocimiento.py`)

Lo que el jugador sabe de la cripta. Es parte del estado de la partida: se guarda, se carga y se revierte
(FR-001, FR-014, FR-015).

| Campo | Tipo | Contenido | FR |
|-------|------|-----------|----|
| `estado_sala` | lista de enteros, tamaño `n` | `DESCONOCIDA`, `AVISTADA` o `EXPLORADA`, por ordinal de sala | FR-001, FR-004 |
| `recuerdo_puerta` | lista de enteros, tamaño `e` | `SIN_OBSERVAR`, `ABIERTA` o `CERRADA`, por ordinal de salida | FR-006, FR-007, FR-011 |
| `reveladas` | lista de salas, en orden de revelación | Toda sala que dejó de ser desconocida | FR-018 |
| `observadas` | lista de salidas, en orden de observación | Toda salida con recuerdo | FR-015 |
| `entrantes` | lista de listas, tamaño `n` | Salidas que entran a cada sala. Infraestructura: nunca se muestra | FR-006, FR-013 |

**Reglas de validación**:

- La sala del jugador siempre está `EXPLORADA` (FR-002, FR-003).
- Una sala es `AVISTADA` si y solo si no está explorada y es destino de una salida de una sala explorada (FR-004).
- `reveladas` y `estado_sala` son coherentes: una sala está en la lista si y solo si su estado no es `DESCONOCIDA`, y
  aparece una sola vez. Igual `observadas` con `SIN_OBSERVAR`.

**Operaciones**:

| Operación | Efecto | Complejidad | FR |
|-----------|--------|-------------|----|
| `Conocimiento(salas, destino_de)` | Asigna ordinales, crea arreglos y `entrantes`. Se hace una vez por partida | O(n + e) más resolver destinos, O(e log n) la primera vez | FR-001 |
| `estado(sala)` | Consulta | O(1) | FR-001 |
| `recuerdo(salida)` | Consulta | O(1) | FR-005 |
| `entrar(sala, antorcha, historial)` | Explora la sala, avista vecinas y observa sus puertas. Con antorcha, explora todas las vecinas | Sin antorcha O(d(s)). Con antorcha O(d(s) + Σ d(v)) sobre las `v` nuevas. **No depende de `k`** | FR-002, FR-003, FR-006, FR-009, FR-010, FR-011 |
| `observar_puerta(salida, historial)` | Copia el estado real al recuerdo | O(1) | FR-006, FR-008 |
| `explorar(sala)` (interna) | `EXPLORADA` y marca destinos desconocidos como avistados | O(salidas de la sala) | FR-003, FR-004 |
| `revertir(lote)` | Restaura cada escritura en orden inverso | O(tamaño del lote) | FR-014 |
| `exportar()` | Exploradas y recuerdos ya ordenados, con `elegir_algoritmo` | O(k log k + p log p) | FR-015 |
| `restaurar(exploradas, recuerdos)` | Reconstruye todo y recalcula avistadas | O(n + e + Σ salidas de las exploradas) | FR-015 |
| `explorada_por_texto(texto)` | Busca entre las reveladas exploradas comparando `str(sala.id)` | O(k) | FR-022 |

`Conocimiento` no conoce la vista, ni el motor, ni archivos (Principio II). Lee el estado real de una puerta solo
dentro de `observar_puerta`, y solo cuando el motor determina que el jugador la ve.

**Quién llama a `observar_puerta`**:

| Causa | Lugar | Condición |
|-------|-------|-----------|
| Entrar a una sala | `Conocimiento.entrar` | Salidas y entrantes de esa sala |
| El jugador abre una puerta | `MotorSimulacion.abrir_salida` | Siempre: está en esa sala (FR-008) |
| Cierre automático | `MotorSimulacion.ejecutar_evento` | Solo si el jugador está en el origen o el destino de la salida (FR-006, FR-007) |

Con eso no hace falta revisar puertas en cada turno: quedarse en una sala con `esperar` también actualiza el mapa,
porque el único cambio posible llega por esos eventos.

### Lote de cambios (delta)

Tupla `(tipo, ordinal, valor_anterior)` dentro de una lista, registrada como un solo `Cambio` en el `Historial`.

| Tipo | Deshacer |
|------|----------|
| Cambio de `estado_sala` | Restaura el valor; si era `DESCONOCIDA`, `reveladas.pop()` |
| Cambio de `recuerdo_puerta` | Restaura el valor; si era `SIN_OBSERVAR`, `observadas.pop()` |

Las operaciones que no cambian nada no generan entrada, y un lote vacío no registra `Cambio`.

### `GrafoConocido` (`Modelo/Conocimiento.py`)

Adaptador de solo lectura sobre `Conocimiento`, que implementa la [interfaz de grafo](contracts/interfaz-ruta.md). No
guarda estado propio.

Una arista existe si y solo si la sala de origen está explorada, la **sala destino está explorada** y su recuerdo es
`ABIERTA` (FR-023, FR-029). El costo sale de `motor.costo_salida` (FR-005).

### `Paso` (`Modelo/rutas_ir_a.py`)

Resultado de `primer_paso`: `direccion`, sala `destino` del paso y `costo_total` de la ruta.

### `Viaje` (`Modelo/Viaje.py`)

Orden «ir a» en ejecución. **No se guarda ni se reanuda** (spec, Entidades clave). Vive solo durante el comando.

| Campo | Contenido |
|-------|-----------|
| `destino` | Sala destino, explorada |
| `buscar` | Función `primer_paso` inyectada (frontera de D-PEND-01) |
| `motivo` | `None` mientras sigue; al terminar, uno de los motivos de parada |

**Estados**:

```text
              rechazo (FR-022): sin tiempo, sin bitácora
ORDEN ──────────────────────────────────────────────▶ RECHAZADA
  │
  │ aceptada (destino explorado, distinto de la sala actual, con ruta)
  ▼
CALCULAR ruta ──── sin ruta (FR-027d, sin tiempo) ──▶ DETENIDO
  │ ▲
  │ │ sigue
  ▼ │
PASO = mover ───── llegada, enemigos, daño, fin ────▶ DETENIDO
```

Un `retroceder` posterior no reanuda nada, porque el `Viaje` ya no existe (FR-031).

**Motivos de parada**:

| Motivo | Condición | FR |
|--------|-----------|----|
| `DESTINO` | La sala actual es el destino | FR-027a |
| `ENEMIGOS` | Había enemigos vivos al entrar | FR-027b |
| `DANO` | La vida bajó durante el paso | FR-027c |
| `SIN_RUTA` | El recálculo no encuentra ruta | FR-027d |
| `FIN_PARTIDA` | Victoria o derrota | FR-027e |
| `PASO_RECHAZADO` | El motor rechazó un `mover`: se informa el mismo mensaje de rechazo que daría `mover`, sin tiempo adicional | FR-027f |

Si coinciden varias, se informa por prioridad: `FIN_PARTIDA`, `DANO`, `ENEMIGOS`, `DESTINO`.

### `MapaConocido` (`DTOS/MapaConocido.py`)

DTO que cruza de modelo a vista (Principio II) y garantiza que la vista no toque el mapa real (FR-012).

| Campo | Contenido | FR |
|-------|-----------|----|
| `exploradas` | Lista por id ascendente de `SalaConocida` | FR-018 |
| `avistadas` | Lista de ids ascendentes | FR-018 |

`SalaConocida`: `id`, `nombre`, `salidas`. `SalidaConocida`: `direccion`, `destino_id`, `costo`, `estado`
(`abierta`, `cerrada` o `sin observar`).

Construirlo cuesta O(k log k + salidas de las exploradas), usando `elegir_algoritmo` (no `sorted`).

### `RegistroConocimiento` (`Persistencia/RegistroConocimiento.py`)

Forma binaria del conocimiento, con `to_bytes`, `from_bytes`, `to_dict` y `from_dict` (para `ExportadorJSON`).
Formato en [contracts/formato-partida.md](contracts/formato-partida.md).

| Campo | Contenido |
|-------|-----------|
| `exploradas` | Lista de ids |
| `recuerdos` | Lista de `(sala_id, direccion, estado)` |
| `puertas_reales` | Lista de `(sala_id, direccion, cerrada)` |

---

## Entidades modificadas

### `Salida` (`DTOS/Salida.py`)

Esta capacidad **no** cambia los campos de `Salida`. El campo `costo` (enunciado §3.1) lo agrega la capacidad de
terreno y costos (T010). Aquí el costo solo se lee, con `motor.costo_salida`, que usa `getattr` y da 100 si la salida
no lo trae (R7).

Atributos internos asignados por `Conocimiento`, igual que el `_destino` actual: `_ordinal` y `_origen` (necesario
para `CERRAR_PUERTA`, cuyo actor es la salida). Las salas reciben `_ordinal`.

### `MotorSimulacion` (`Modelo/MotorSimulacion.py`)

| Elemento | Cambio | FR |
|----------|--------|----|
| `COSTO_MOVER` | Constante nueva con el valor actual de `mover`; es el costo por defecto de `costo_salida` | FR-005 |
| `conocimiento` | Atributo nuevo; `None` si el motor se armó sin `iniciar_partida` (pruebas de la Parte I) | SC-006 |
| `iniciar_partida` | Crea `Conocimiento` y registra la entrada a la sala inicial, sin intervalo abierto | FR-002 |
| `mover_jugador` | Llama a `entrar` antes de las trampas y guarda «había enemigos al entrar». Su costo no cambia (sigue en 100; cobrar `costo_salida` es de la capacidad de terreno y costos) | FR-003, FR-009, FR-027b |
| `abrir_salida` | Llama a `observar_puerta` | FR-008 |
| `ejecutar_evento` (`CERRAR_PUERTA`) | Observa y avisa solo si el jugador ve la puerta | FR-006, FR-007, FR-012 |
| `costo_salida(salida)` | Nuevo: único acceso al costo, solo lectura | FR-005, FR-024 |
| `mapa_conocido()` | Nuevo: devuelve el DTO | FR-018 |
| `salidas_recordadas(sala)` | Nuevo: salidas para la pantalla de estado | FR-012 |
| `preparar_viaje(texto)` | Nuevo: valida y devuelve un `Viaje` o un rechazo | FR-022 |
| `obtener_estado_resumen` | Agrega `conocimiento` | SC-004 |

### `EncabezadoPartida`, `LectorPartida`, `guardar_partida`

`VERSION_FORMATO = 3`. `guardar_partida` recibe `conocimiento=None`, y `None` escribe largo 0 (los benchmarks de
registros siguen funcionando). `LectorPartida` calcula `_inicio_salas` con el bloque nuevo y agrega `leer_conocimiento()`.

### `BitacoraPartida`, `leer_bitacora`, `Reproductor`

`VERSION_BITACORA = 2`. Métodos nuevos `comentar(texto)` y `marcar_carga()`. `leer_bitacora` omite comentarios y
conserva la directiva. `Reproductor` recibe `recargar` opcional.

---

## Flujos

### Entrada a una sala

```text
mover_jugador
 ├─ accion_jugador()                  abre intervalo
 ├─ jugador.sala = destino            cambio registrado
 ├─ conocimiento.entrar(...)          un lote, un Cambio
 ├─ actualizar_rastro
 ├─ activar_trampas_de_sala           puede matar: el conocimiento ya está actualizado
 ├─ ¿victoria?
 ├─ anotar si hay enemigos vivos      lo lee el Viaje
 ├─ activar_enemigos_de_sala
 ├─ proxima_accion(costo=100)        sin cambio: cobrar costo_salida es de terreno y costos
 └─ avanzar_hasta_jugador             un cierre observado cae en este mismo intervalo
```

### Carga de una partida

```text
cargar_partida
 ├─ validar versiones
 ├─ leer jugador y conocimiento
 ├─ _crear_motor                      arranca con solo la sala inicial explorada
 ├─ aplicar puertas_reales            corrige todas las salas sin leer sus bloques
 ├─ conocimiento.restaurar            sin historial; recalcula avistadas
 ├─ restaurar jugador y reloj
 └─ preparar_sala(actual)             sigue siendo perezoso para las demás
```

Cargar no vuelve a observar las puertas de la sala actual: el recuerdo restaurado ya es idéntico al guardado (FR-015).

### Pergamino después de un viaje

El último paso es un intervalo como cualquier `mover`. Deshacerlo revierte, en orden inverso, los eventos, el lote de
conocimiento y la posición. Los pasos anteriores conservan sus intervalos (FR-031). Tras cargar no hay intervalos y se
comporta como en la Parte I.
