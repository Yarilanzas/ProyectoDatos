# Contrato: archivo de partida `CRPT` 3, bloque de la línea de tiempo

**Para la persona C.** Es la **disposición final** que pedía P-10: acepta el orden `[conocimiento][línea de tiempo][salas][índice]` y
fija el contenido del bloque de la línea y la fórmula de `_inicio_salas`. Contrato compartido (Flujo de desarrollo): el README se
actualiza en el mismo cambio y se avisa al grupo.

**Estado real en `main` (verificado en `Persistencia/ArchivoPartida.py` y `FormatoBinario.py`)**: el `CRPT` 3 **ya escribe y lee los
tres campos de largo** `[largo jugador][largo conocimiento][largo línea de tiempo]` (T076). El de la línea se escribe con valor `0` y el
lector lo salta con su largo; `_inicio_salas` ya es la suma de los tres y `_validar_encabezado` ya exige
`offset_indice ≥ TAMANO_ENCABEZADO + 12` (`INICIO_MINIMO_SALAS`). El contrato de 001 dice «dos campos» en una línea y muestra tres en
otra: **son tres** (esta es la fuente; 001 debe corregir esa línea [PERSONAS: C]).

El `CRPT` 3 es **un solo salto de versión** con dos bloques nuevos: el de conocimiento
([specs/001-niebla-mapa-ir-a/contracts/formato-partida.md](../../001-niebla-mapa-ir-a/contracts/formato-partida.md), de la persona C)
y el de línea de tiempo (este documento). Esta capacidad **solo llena el bloque de la línea**: no agrega el campo de largo ni sube
`VERSION_FORMATO` (P-10: no se mantienen archivos v3 intermedios). Los archivos v3 ya escritos con `largo línea = 0` siguen siendo
válidos: se cargan sin historia previa.

## Disposición

```text
v2: [encabezado][largo jugador][jugador]                                                                  [salas][índice]
v3: [encabezado][largo jugador][jugador][largo conocimiento][conocimiento][largo línea][línea][salas][índice]
```

Little endian y sin relleno, como el resto del archivo (`<`). El encabezado, los bloques de sala y el índice no cambian, salvo el
número de versión.

| Campo | Tipo | Contenido |
|-------|------|-----------|
| `largo jugador` | `<I` | bytes del bloque del jugador (igual que en v2) |
| `largo conocimiento` | `<I` | bytes del bloque de conocimiento; `0` si no hay (lo define la capacidad 001) |
| `largo línea` | `<I` | bytes del bloque de la línea; **`0` = sin línea** |

### Fórmulas

```text
inicio_largo_jugador      = TAMANO_ENCABEZADO
inicio_largo_conocimiento = inicio_largo_jugador      + 4 + largo_jugador
inicio_largo_linea        = inicio_largo_conocimiento + 4 + largo_conocimiento
_inicio_salas             = inicio_largo_linea        + 4 + largo_linea
                          = TAMANO_ENCABEZADO + (4 + largo_jugador) + (4 + largo_conocimiento) + (4 + largo_linea)
inicio_bloque_linea       = _inicio_salas - largo_linea
```

`guardar_partida` calcula `posicion` (donde empieza la primera sala) con la misma suma, y la primera posición del índice de salas
sigue siendo `offset_indice`.

### `_validar_encabezado`

- `cantidad_salas ≥ 0` (igual que hoy).
- `offset_indice ≥ TAMANO_ENCABEZADO + 12`: caben los tres campos de largo (ya es `INICIO_MINIMO_SALAS`).
- El índice cabe en el archivo: `offset_indice + cantidad_salas·TAMANO_ENTRADA ≤ tamaño del archivo` (igual que hoy).

### Lectura de los largos (sin leer los bloques)

`LectorPartida._leer_largos()` (ya implementado) hace **tres lecturas de 4 bytes**, saltando de bloque en bloque; no lee el contenido de
ninguno. PR-10 agrega solo guardar `_inicio_linea` y `_largo_linea` (hoy locales) para `leer_linea()`:

```text
pos = TAMANO_ENCABEZADO
para cada campo en (jugador, conocimiento, línea):
    exigir pos + 4 <= offset_indice
    largo = leer <I en pos
    pos  += 4 + largo
    exigir pos <= offset_indice            # si no: "El bloque de <campo> invade las salas del archivo"
_inicio_salas = pos
```

Cualquier incumplimiento es `VersionIncompatible` (código `2`). `bytes_leidos` aumenta en `TAMANO_ENCABEZADO + 12`; **leer una sala no
lee la línea** (P1 §4.10; `test_carga_perezosa_solo_lee_la_sala_actual` no cambia salvo por esos 12 bytes).

## Bloque de la línea

```text
<I  K                          acciones máximas entre puntos de control (FR-031), K >= 1
<I  cantidad de registros R
    por cada registro, en orden cronológico:
<B    tipo                     1 = ACCION, 2 = RETROCESO, 3 = CARGA
      si tipo = 1 (ACCION, cuenta como acción del jugador):
<H      largo del nombre
        nombre (UTF-8)
<H      largo del argumento
        argumento (UTF-8)
<Q      reloj en la decisión previa a la acción     (sello)
<Q      secuencia en la decisión previa a la acción (sello)
      si tipo = 2 (RETROCESO, un 'retroceder' aceptado):
<I      acciones vigentes que quedan tras retroceder
      si tipo = 3 (CARGA, frontera de un @cargar):
<Q      reloj del motor cargado
```

- Es el **guion completo** de los comandos aceptados, **incluidos** los retrocesos y las cargas, no solo la historia vigente.
  Tras un retroceso la partida real conserva efectos irreversibles (un pergamino recogido, el contenido de una sala cargada), y solo el
  guion completo permite reproducirlos (research R5, HL9). La historia vigente se recalcula al reproducir.
- **Sin puntos de control**: no se guardan. Se reconstruyen al cargar reproduciendo el guion (research R8). Por eso el bloque mide
  ~30 bytes por comando y no depende del tamaño del estado.
- **Orden canónico**: el mismo estado produce los mismos bytes (el orden es el cronológico).
- Los nombres de acción son los de la bitácora: sin espacios, sin empezar por `#` ni `@`.
- `K` se guarda tal como estaba (FR-031). Al cargar rige ese K.
- No hay número de versión interno: lo cubre `VERSION_FORMATO`.

### Tamaño

`largo línea = 8 + Σ registros`. Una acción de nombre `mover` y argumento `E` ocupa `1 + 2 + 5 + 2 + 1 + 8 + 8 = 27` bytes; un
retroceso, 5; una carga, 9. 5 000 acciones ≈ 135 KB (**HIPÓTESIS**, la mide M6).

## Lectura y validación

| Caso | Comportamiento |
|------|----------------|
| Versión de formato distinta de 3 (incluida la 2, de la Parte I y de la capacidad 001 sin línea) | `VersionIncompatible`, nada se carga, código `2` (FR-024) |
| `largo línea = 0` | Válido: la línea empieza en la carga, sin historia previa; `K` = el de la ejecución (no hay K guardado) |
| Bloque truncado, `tipo` desconocido, `K < 1`, nombre inválido o bytes sobrantes | `VersionIncompatible`, código `2` |
| Un `RETROCESO` que deja más acciones vigentes que las que había | `VersionIncompatible`, código `2` |
| El guion reproducido no coincide con los sellos o con el bloque del jugador | `VersionIncompatible: la línea de tiempo no coincide con la partida`, código `2`, sin cargar nada |
| Correcto | La línea queda restaurada: `historia` responde igual que antes de guardar (FR-022, SC-005) |

La lectura del bloque (`LectorPartida.leer_linea()`) es de una sola vez y devuelve un `RegistroLinea` o `None` si `largo línea = 0`.
**Reconstruir** (reproducir el guion) ocurre en el controlador, no en `Persistencia/`: el guion solo es datos. El procedimiento está en
[research R8](../research.md#r8-persistencia-de-la-línea-fr-022-fr-023-fr-024-fr-025-fr-031) y en
[interfaz-linea.md](interfaz-linea.md).

## API

```text
RegistroLinea(k, registros)              # registros: lista de tuplas; Persistencia/RegistroLinea.py
RegistroLinea.to_bytes() -> bytes
RegistroLinea.from_bytes(datos) -> RegistroLinea      # lanza VersionIncompatible
guardar_partida(ruta, cripta_id, version_cripta, version_catalogo, semilla, reloj, registros,
                jugador=None, conocimiento=None, linea=None)   # linea: objeto con to_bytes(); None -> largo 0
LectorPartida.leer_linea() -> RegistroLinea | None
```

`linea=None` escribe `largo línea = 0` (es lo que hace hoy `guardar_partida`, que aún no tiene el parámetro). `guardar_motor(motor, ruta,
gestor)` (T094) también recibe `linea=None`. El temporal que usa `--replay` en `@cargar` puede pasar `None`.

## `ExportadorJSON`

Agrega la clave `linea` con `k` y la lista de registros (mismos datos que el binario), para que la comparación binario frente a JSON
siga siendo de los mismos datos.

## Qué no se guarda

Los puntos de control, la serie de pergaminos y las épocas (se reconstruyen al cargar), ni la copia privada del archivo. El
historial de retroceso sigue sin guardarse.

## Archivos y pruebas afectados

| Archivo | Cambio |
|---------|--------|
| `Persistencia/FormatoBinario.py` | **Sin cambios**: `VERSION_FORMATO = 3` ya está (T076) |
| `Persistencia/ArchivoPartida.py` [PERSONAS: C] | el campo, `_leer_largos`, `_inicio_salas` y `INICIO_MINIMO_SALAS` **ya existen**; falta el parámetro `linea`, guardar `_inicio_linea`/`_largo_linea` y `leer_linea` |
| `Persistencia/RegistroLinea.py` | nuevo |
| `Persistencia/ExportadorJSON.py` | clave `linea` |
| `tests/test_archivo_partida.py` [PERSONAS: C] | los casos actuales (línea con largo `0`) siguen valiendo. Agregar, con la línea no vacía: `_inicio_salas` igual a `TAMANO_ENCABEZADO + (4 + largo_jugador) + (4 + largo_conocimiento) + (4 + largo_línea)`; `offset_indice < TAMANO_ENCABEZADO + 12` rechazado; bloque de línea que invade las salas rechazado; `bytes_leidos` (`TAMANO_ENCABEZADO + 12` al abrir; leer una sala no lee la línea). La prueba de carga perezosa de `tests/test_integracion.py` no cambia |
| `tests/test_encabezado.py` | versión vigente y rechazo de la versión 2 (ya cubierto por la persona C; sin cambios de offsets) |
| `README.md` (UTF-16) | documenta `CRPT` 3 con la línea (FR-023) |
| `partida.cripta`, `partida.cripta.log` | dejan de cargarse (versiones anteriores); no deberían versionarse |
