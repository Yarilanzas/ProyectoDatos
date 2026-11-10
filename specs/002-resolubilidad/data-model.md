# Data Model: Verificación de resolubilidad (spec 002)

**Plan**: [plan.md](plan.md) | **Research**: [research.md](research.md)

Notación: S salas, E salidas, K llaves distintas, L ubicaciones, C salidas cerradas con llave, M = L + C + 1.
«Arreglo» significa una `list` de Python creada con su tamaño final y usada solo por índice (Principio I).

Las complejidades de cada tabla se copian al docstring de la clase o función correspondiente.

## 1. Entradas (DTOs existentes)

| DTO | Campos usados | Origen |
|-----|---------------|--------|
| `CriptaDetalles` | `sala_inicial`, `sala_salida`, `llave_salida`, `presupuesto_solicitudes` | `GET /criptas/<id>` |
| `SalaEsqueleto` | `id`, `salidas` (`dict` dirección → `Salida`, solo se recorre) | `GET /criptas/<id>/salas` |
| `Salida` | `sala_destino`, `cerrada`, `llave` (`cierre_automatico` se ignora, FR-004) | idem |
| `UbicacionLlave` | `id_llave`, `sala`, `enemigo` (opcional) | `GET /criptas/<id>/llaves` |

Las trampas y el contenido de las salas no se leen (FR-004).

**Validación de `UbicacionLlave.desde_json`**: falta `id` o `sala` → `RespuestaInvalidaError` (hoy `KeyError`).

## 2. Estructuras internas del modelo (`Modelo/Resolubilidad.py`)

### 2.1 `IndiceLlaves` (R4)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `ids` | arreglo de `str`, ordenado, sin repetidos | posición = número de llave |

| Operación | Complejidad |
|-----------|-------------|
| `construir(menciones)` con `merge_sort` + quitar repetidos | O(M log M) |
| `numero(id_llave)` búsqueda binaria; −1 si no está | O(log K) |
| `id_de(numero)` | O(1) |
| `cantidad()` | O(1) |

Invariante: `ids[i] < ids[i+1]`. Por eso el orden por número es el orden por identificador (FR-007, FR-014).

### 2.2 `SalidaVerif` y `SalaVerif` (R1)

`SalidaVerif`

| Campo | Tipo | Regla |
|-------|------|-------|
| `direccion` | `str` | |
| `origen` | `int` | |
| `destino` | `int` | puede no existir |
| `destino_valido` | `bool` | `0 <= destino <= max_id` y `salas[destino] is not None` |
| `cerrada` | `bool` | |
| `num_llave` | `int` | −1 si está abierta o no indica llave |
| `id_llave` | `str` o `None` | para el reporte |

`SalaVerif`

| Campo | Tipo | Regla |
|-------|------|-------|
| `id` | `int` | |
| `salidas` | arreglo de `SalidaVerif` | orden N, S, E, O; otras direcciones después, por texto (`merge_sort`) |
| `llaves` | arreglo de `int` | números de llave ubicados aquí (incluidas las que suelta un enemigo que inicia aquí, FR-003) |

### 2.3 `GrafoSalas` (R1, R7)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `salas` | arreglo de `SalaVerif` o `None`, largo `max_id + 1` | indexado por id de sala |
| `entrantes` | arreglo de listas de `SalidaVerif`, largo `max_id + 1` | salidas que llegan a cada sala; solo lo usa R7 |

| Operación | Complejidad |
|-----------|-------------|
| construir desde esqueleto, índice y ubicaciones | O(S + E + M log K) |
| `sala(id)` | O(1) |
| `existe(id)` | O(1) |

Ids duplicados en el esqueleto: se conserva la primera aparición. Id no entero o negativo: `ValueError` con el id
(se informa con `! Error: ...`).

### 2.4 Estado del recorrido (R2, R3, R5)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `cola` | `Queue` (`Cache/Estructuras.py`) | salas por visitar; solo `enqueue`, `dequeue`, `is_empty` |
| `visitada` | arreglo de `bool`, largo `max_id + 1` | se marca al encolar |
| `obtenida` | arreglo de `bool`, largo K | |
| `en_ronda` | arreglo de `bool`, largo K | llave ya anotada en la oleada en curso |
| `espera` | arreglo de listas de `int`, largo K | destinos de puertas cerradas que esperan esa llave |
| `nuevas` | lista de `int` | llaves halladas en la oleada en curso |
| `orden` | lista de `(num_llave, oleada)` | resultado de FR-007 |

| Operación | Complejidad |
|-----------|-------------|
| marcar / consultar visitada u obtenida | O(1) |
| encolar / desencolar | O(1) |
| agregar a `espera[k]` | O(1) amortizado |
| soltar `espera[k]` | O(largo de la lista), cada entrada una vez |
| ordenar `nuevas` de cada oleada con `merge_sort` por número | O(n log n); suma O(K log K) |
| **recorrido completo** | **O(S + E + K log K)** |

**Transición de estados de una llave**: `no vista` → `en_ronda` (hallada en una sala procesada) → `obtenida` (al cerrar
su oleada). Una llave que nunca pasa a `obtenida` es **no obtenible**.

**Transición de una sala**: `sin visitar` → `visitada` (al encolarse) → procesada (al desencolarse). Nunca vuelve.

### 2.5 Dependencias y ciclos (R7, R8) — solo si no es resoluble

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `sello` | arreglo de `int`, largo `max_id + 1` | número de la última zona que visitó la sala (0 = ninguna) |
| `valor_zona` | arreglo de `int`, largo `max_id + 1` | resultado ya calculado por sala de ubicación: −2 sin calcular, −1 sin dependencia, j |
| `depende_de` | arreglo de `int`, largo K | −1 o número de la llave J |
| `marca` | arreglo de `int`, largo K | recorrido que vio la llave (detección de ciclos) |
| `en_ciclo` | arreglo de `bool`, largo K | |

| Operación | Complejidad |
|-----------|-------------|
| zona de una sala (BFS hacia atrás con sello, corte al primer conflicto) | O(salas + entrantes de la zona) |
| todas las dependencias | O(S + E + Σ zonas); peor caso O(L·(S + E)) |
| detectar ciclos | O(K) |
| emitir ciclos en orden (barrido por número) | O(K) |

Valor de una zona: con las puertas bloqueadas cuyo destino tiene el sello actual y cuyo origen no lo tiene:
ninguna → −1; todas piden la misma J → J; alguna pide otra llave o no indica llave → −1 (conflicto).

## 3. Resultado (`DTOS/ResultadoVerificacion.py`, nuevo)

Cruza del modelo a la vista y al controlador (Principio II). Todos los campos son listas ya ordenadas; la vista no
ordena nada.

### `ResultadoVerificacion`

| Campo | Tipo | Cuándo | Orden |
|-------|------|--------|-------|
| `cripta_id` | `str` | siempre | |
| `resoluble` | `bool` | siempre | |
| `sala_salida`, `llave_salida` | `int`, `str` | siempre | |
| `orden` | lista de `LlaveOrdenada` | si es resoluble | oleada, luego id (FR-007) |
| `no_obtenibles` | lista de `str` | si no es resoluble | id (FR-014) |
| `frontera` | lista de `PuertaReporte` | si no es resoluble; vacía = se dice explícitamente | sala origen, dirección |
| `puertas_salida` | lista de `PuertaReporte` | si no es resoluble | sala origen, dirección |
| `existe_puerta_salida` | `bool` | si no es resoluble | |
| `ubicaciones` | lista de `UbicacionesLlave` | si no es resoluble | id de llave |
| `dependencias` | lista de `DependenciaLlave` | si no es resoluble | id de llave |
| `ciclos` | lista de `CicloLlaves` | si no es resoluble | menor llave de cada ciclo |

### `LlaveOrdenada`

`id_llave: str`, `oleada: int`, `es_salida: bool`.

### `PuertaReporte`

`origen: int`, `direccion: str`, `destino: int`, `destino_existe: bool`, `llave: str | None` (`None` = «sin llave»).

### `UbicacionesLlave`

`id_llave: str`, `lugares: list[LugarLlave]` (vacía = «ubicación desconocida»).

`LugarLlave`: `sala: int`, `sala_existe: bool`, `enemigo: str | None`. Orden por sala y luego enemigo.

### `DependenciaLlave`

`id_llave: str`, `depende_de: str | None` (`None` = sin dependencia).

### `CicloLlaves`

`llaves: list[str]` (empieza por la menor; no repite la primera al final), `directo: bool`.

## 4. Persistencia

| Archivo | Contenido | Versión |
|---------|-----------|---------|
| `<paquete>/criptas/<id>/llaves.json` | mismo cuerpo que `GET /criptas/<id>/llaves` | el de la cripta (`version.json`) |
| `datos_locales/llaves_<id>.json` | `{"version": <versión de cripta>, "llaves": [...]}` | se descarta si la versión cambia, igual que `esqueleto_<id>.json` |

El resultado de la verificación **no se guarda** en la partida, la bitácora ni los puntajes (Key Entities).
Detalle en [contracts/fuente-llaves.md](contracts/fuente-llaves.md).
