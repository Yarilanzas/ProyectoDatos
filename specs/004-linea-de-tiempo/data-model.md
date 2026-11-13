# Data Model: Línea de tiempo y su persistencia

**Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md) | **Contratos**: [contracts/](contracts/)

Notación de [research.md](research.md): `n` acciones vigentes, `K`, `C` puntos de control, `S` tamaño del estado vivo, `N`/`E` salas y
salidas, `a` costo de una acción, `V` acciones recortadas, `L` cargas, `P` usos del pergamino. Estructuras propias (Principio I): todo
son listas y arreglos paralelos; ningún `dict` ni `set` como índice; la búsqueda es `Modelo/BusquedaBinaria.py`.

## Mapa de entidades

```text
LineaTiempo ─┬─ guion (registros: ACCION | RETROCESO | CARGA)         append-only
             ├─ vigente (arreglos paralelos, se recorta por el final)
             ├─ puntos de control (arreglos paralelos, ordenados)  ── PuntoControl ── copia del estado + foto del esqueleto
             ├─ épocas (una por carga)                              ── copia privada del archivo cargado
             ├─ serie de pergaminos (ordenada por clave)
             └─ K, gestor histórico (inyectado)
ResumenHistorico (DTO)  <── Modelo/ResumenHistorico.py (motor, reloj, pergaminos)
RegistroLinea (Persistencia)  <──>  guion + K
```

## LineaTiempo

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `k` | `int ≥ 1` | acciones máximas entre puntos de control (FR-018, FR-031) |
| `guion_tipo`, `guion_nombre`, `guion_argumento`, `guion_reloj`, `guion_secuencia` | listas paralelas | un registro por comando aceptado (R3). Para `RETROCESO`: `guion_reloj` guarda las acciones vigentes que quedan; para `CARGA`: el reloj cargado |
| `vig_guion` | lista de `int` | posición en el guion de cada acción vigente (`vig_guion[j]` es la acción `j+1`) |
| `vig_reloj`, `vig_sec` | listas de `int` | sello de la decisión **previa** a cada acción vigente: `(motor.reloj, motor.secuencia)`. **Se toma al terminar el aviso anterior** (`al_crear_motor`, la acción anterior, el retroceso o `despues_de_carga`), porque `despues_de_accion` llega con el motor ya avanzado ([research.md, R3](research.md#r3-qué-se-registra-entre-puntos-de-control-fr-021)) |
| `pc_accion`, `pc_reloj`, `pc_epoca`, `pc_punto` | listas paralelas | puntos de control, **no decrecientes** en `pc_accion` |
| `epocas_accion`, `epocas_ruta` | listas paralelas | acción en que empezó cada época y ruta de su copia privada (`None` para la época 0) |
| `serie_clave`, `serie_cantidad` | listas de `int` | cantidad de pergaminos, ordenada por clave (R6) |
| `reloj_actual` | `int` | reloj del motor en el último registro |
| `acciones_motor` | `int` | `motor.acciones_jugador` en el último registro (para calcular `V`) |

### Invariantes

1. `len(vig_guion) == len(vig_reloj) == len(vig_sec) == n`. Los `vig_reloj` crecen estrictamente (cada acción cuesta ≥ 1).
2. `pc_accion[i] ≤ n`, no decreciente; hay un punto con `accion == 0` mientras no haya cargas (el inicial) o uno por época.
3. Cada punto de control es una copia del **motor real** cuando estaba en la decisión `pc_accion[i] + 1` (R5). Es lo que permite
   rehacer sin divergencia.
4. `serie_clave` estrictamente creciente, `serie_clave[-1] ≤ n`.
5. El guion termina con el comando más reciente aceptado; `RETROCESO` y `CARGA` no figuran en `vig_*`.
6. `C ≤ ⌈n/K⌉ + 1 + L + P`.

**Nota (costo de las salidas, 003).** Con `Salida.costo` (`costo_salida`), `reloj` **ya no crece linealmente con las acciones**: un
`mover` cuesta lo que diga la salida. El sello `(reloj, secuencia)` sigue siendo válido porque se compara por valor, y `vig_reloj`
sigue creciendo estrictamente.

### Operaciones y complejidad

Ver la tabla de [interfaz-linea.md](contracts/interfaz-linea.md). Resumen: registrar `O(1)` + copia `O(S)` cada K; recortar `O(V + S)`;
consultar `O(log n + log C + S + K·a)`; memoria `O(n) + O(C·S)`.

### Transiciones de estado

```text
iniciar ──► ACCION* ──┬─► RETROCESO ──► (recorte, punto del motor real) ──► ACCION* ...
                      └─► CARGA ──────► (época nueva, punto del motor cargado) ──► ACCION* ...
```

- `ACCION` agrega una posición vigente. Si `n % K == 0`, punto de control.
- `RETROCESO` saca `V` posiciones vigentes y los puntos con `accion > nuevo_n`, reemplaza o agrega el punto en `nuevo_n`, y pliega la
  serie.
- `CARGA` no saca nada: el pasado anterior sigue consultable. Reemplaza un punto regular que esté en la misma acción.

## PuntoControl

| Campo | Descripción |
|-------|-------------|
| `estado` | copia de `MotorSimulacion` hecha con `deepcopy(motor, memo)`: `gestor_datos → None`, `restaurador → None`, `historial → Historial()`, y cada `Sala` y `Salida` del motor real **compartidas** (no se recorren). El inventario es `motor.jugador.inventario` y se copia con un bucle, sin recursión (T015 y T016). **`estado` nunca se ejecuta directamente** (ver abajo) |
| `foto_rastros` | lista con `Sala.rastro` por ordinal de sala; una sala sin atributo `rastro` (nunca visitada) se anota con un **centinela** («sala sin atributo `rastro`», distinto de `None`) |
| `foto_cerradas` | lista de `bool` con `Salida.cerrada` por ordinal de salida (en el orden de recorrido de las salas) |
| `accion`, `reloj`, `secuencia` | posición y sello |
| `epoca` | índice de la época a la que pertenece |

`materializar(punto, gestor_historico, abrir_copia=None, ruta_copia=None)` produce un **clon** nuevo:

1. Esqueleto propio: para cada sala del motor real, `copy.copy` de la sala y de cada salida; `rastro` y `cerrada` de la foto
   (`materializar` **no crea** el atributo `rastro` en una sala donde no existía: el centinela se respeta);
   `_origen` y `_destino` re-ligados por ordinal; `salidas` es un `dict` nuevo (es el del DTO, solo se recorre).
2. `deepcopy(punto.estado, memo)` donde `memo` mapea cada objeto del esqueleto de respaldo → su par nuevo, y `historial → Historial()`.
   Ese `memo` re-liga también `Evento.actor` (un evento `CERRAR_PUERTA` tiene como actor una `Salida`) y, por ser parte del estado,
   el `grafo_cripta` y el `espacio_busqueda`: **se copian con `deepcopy`** y el `memo` los re-liga a las salas y al motor del clon (sus
   métodos enlazados apuntan al clon). El grafo **no depende de `version_puertas`**: lee `cerrada` en vivo y solo guarda estructura fija.
3. `clon.gestor_datos = gestor_historico` y `gestor_historico.conectar_estado_juego(clon)`.
4. Si `abrir_copia` y `ruta_copia` no son `None` (la época tiene copia privada): `clon.restaurador = abrir_copia(ruta_copia)`; si no,
   `clon.restaurador = None`.
5. `clon.eco = False`.

`ciclo` y `version_puertas` (enteros que solo crecen) **viajan dentro del estado** del punto: no se guardan aparte, no entran en la
bitácora y deshacer no los baja. El oráculo de T012 **no los compara** entre el motor vivo y el clon. `materializar` escribe
`Salida.cerrada` **directamente sobre las copias del esqueleto**, dentro de `Modelo/CopiaEstado.py` (excluido por nombre en la prueba
de código fuente de A), antes de que exista el clon; el `version_puertas` que recibe el clon ya es el de la decisión de la foto.

**`punto.estado` nunca se ejecuta directamente.** Sus eventos `CERRAR_PUERTA` apuntan a la `Salida` **viva** (medido en T003: un
clon sin re-ligar cerró la puerta del vivo, `Salida.cerrada` pasó de `False` a `True`). Solo se ejecuta un clon **materializado**,
cuyo `memo` re-liga también `Evento.actor` al esqueleto nuevo.

**El clon sin gestor no puede jugar** (medido en T003): con `gestor_datos = None`, entrar en una sala con trampa lanza
`RuntimeError: No hay gestor de datos para consultar la ficha de la trampa.` y entrar en una sala sin contenido cargado se rechaza
con `El contenido de esa sala aún no está disponible.`. Por eso `materializar` le asigna `gestor_historico`, que sirve
`obtener_ficha` y `asegurar_sala` desde el almacenamiento en disco; si falta un dato local, `SinDatosParaHistoria`. Medido: con un
`GestorDatos` iniciado, un clon copiado en la acción 250 rehace 50 acciones y queda **idéntico** al vivo (N = 20, 200 y 2 000).

**Un solo clon vivo por `gestor_historico`.** `GestorDatos.estado_juego` es un único campo y `conectar_estado_juego(clon)` lo
reemplaza: con dos clones sobre el mismo gestor, el primero quedaría consultando al segundo (`es_ficha_activa` decide qué fichas
desaloja la caché). Se materializa un clon, se consulta, se descarta y recién entonces se materializa otro. **HIPÓTESIS**: leído del
código, no medido.

Constantes (extensibles, ver [interfaz-linea.md](contracts/interfaz-linea.md)): `CAMPOS_MUTABLES_SALA = ("rastro",)`,
`CAMPOS_MUTABLES_SALIDA = ("cerrada",)`. `Salida._destino` es una caché del motor que se re-liga, no un campo de estado. **`Salida.cerrada_en_esqueleto`
(`DTOS/Salida.py`, de la persona C) es constante y no va en `CAMPOS_MUTABLES_SALIDA`**: se fija una sola vez en `Salida.__init__` con
`bool(cerrada)` del esqueleto (en `main` ninguna otra línea la asigna: `aplicar_puertas_reales` y los eventos del motor solo cambian
`cerrada`), así que `copy.copy` la conserva y la foto no la necesita. Si alguien la hiciera cambiar después de crear la salida, tendría
que agregarse a esa constante.

Campos de `Sala` y `Salida` que **no** son mutables en la partida y que `copy.copy` conserva (leídos del código; ver
[research.md, T003](research.md#t003-revisión-de-deepcopy-y-memo-2026-11-12)): `Sala._ordinal`; `Salida._ordinal`, `Salida._direccion`
y `Salida.costo` (inmutable: solo se asigna en `Salida.__init__`; campo nuevo de 003). El único campo de estado de `Sala` es `rastro`
y el de `Salida` es `cerrada`; una sala que el jugador nunca pisó **no tiene el atributo `rastro`**.

`Modelo/CopiaEstado.py` escribe `Salida.cerrada` y `Sala.rastro` solo sobre las salas y salidas **del clon** (la copia del esqueleto), nunca
sobre las del motor vivo. Coherencia con lo que cuelga del motor de 003 (cuando exista): `ciclo` y `version_puertas` son enteros y
`deepcopy` los copia; `GrafoCripta`, `EspacioBusqueda` y `CampoDistancias` guardan listas y referencias a salas, que el `memo` re-liga al
esqueleto nuevo (o, sin ese re-ligado, el clon apuntaría al esqueleto del respaldo). El `CampoDistancias` copiado queda inválido en
el clon porque `ciclo` avanza al empezar cada ciclo re-simulado (003, R5), así que nunca se lee un campo pisado; el mismo
`EspacioBusqueda` queda alcanzable solo desde el clon.

| Operación | Tiempo | Memoria |
|-----------|--------|---------|
| copiar (punto) | `O(S + N + E)` | `O(S) + O(N + E)` en listas planas |
| materializar | `O(S + N + E)` | `O(S + N + E)` temporal |

Exploración previa local, no versionada (E2 y E4; **HIPÓTESIS**, la reemplaza M3): copia 1.1 ms y 26 KiB (N=20), 2.2 ms y 43 KiB (N=200), 11.7 ms y 285 KiB (N=2 000);
consultar 1.85 / 7.95 / 69.4 ms respectivamente. **Esas cifras eran de otro método** (copia estructurada con el esqueleto fuera del
`deepcopy`), no de `deepcopy(motor, memo)`.

Lo medido en T003 con `deepcopy(motor, memo)` ([research.md](research.md#t003-revisión-de-deepcopy-y-memo-2026-11-12); Python 3.14.2
y 3.12.10; 300 acciones; mediana de 20 repeticiones; incluye armar el `memo`):

| N | Tiempo mediano | Memoria neta del clon | Pico con el `memo` |
|---|----------------|-----------------------|--------------------|
| 20 | 0.7 a 1.4 ms | 20 KiB | 53 KiB |
| 200 | 2.7 a 4.4 ms | 62 KiB | 226 KiB |
| 2 000 | 17.8 a 30.0 ms | 407 KiB | 1 429 KiB |

Es **hasta 2.6 veces más lento y +43 % de memoria para N ≥ 200** que las cifras de E2 y E4. M3 (T103) se vuelve a medir con estas
cifras como referencia y, mientras tanto, las de esta sección siguen siendo **HIPÓTESIS**. Riesgo para FR-020 en N altas: la copia de
cada punto y la materialización pesan más de lo anotado; T098 sigue siendo el plan B (copia a mano por campos del estado vivo).

## Época

Una por carga (la época 0 es la partida desde su inicio). Guarda la acción en que empezó y la **copia privada** del archivo cargado
(`<carpeta temporal>/epoca_<i>.cripta`): sin ella un clon no podría restaurar las salas que el archivo tenía pendientes si un guardado
posterior sobrescribió el original (research R10). El controlador crea y borra los archivos; la línea guarda solo la ruta.

**Decisión pendiente de aprobación (M3, de dónde sale la ruta).** `despues_de_carga(motor)` solo recibe el motor, sin la ruta del
archivo cargado. Propuesta: tomarla de `motor.restaurador.ruta` (el motor que devuelve `cargar_partida` abre un
`RestauradorPartida` sobre el archivo cargado; `guardar_motor` ya usa `anterior.ruta` así). Si `motor.restaurador` es `None` no hay
salas pendientes que restaurar: la época se abre **sin copia privada** (`epocas_ruta = None`) y la carga no falla. Hay que
confirmarlo con una prueba contra el código real (¿`cargar_partida` deja siempre un `restaurador`?) y que el grupo lo apruebe;
no está definitivo.

## Serie de pergaminos

Pares `(clave, cantidad)` ordenados por clave. `clave` = acciones vigentes completadas cuando cambió la cantidad.

| Operación | Efecto | Tiempo |
|-----------|--------|--------|
| `registrar` | si la cuenta de `pergamino_retroceso` del inventario cambió, agrega `(n, cantidad)` | `O(capacidad del inventario)` |
| `plegar(nuevo_n)` | saca las claves `> nuevo_n`; agrega `(nuevo_n, cantidad_actual)` si difiere de la última | `O(sacadas)` |
| `en(clave)` | cantidad de la última clave `≤ clave`, o la inicial | `O(log longitud)` |

Para `#k`: `en(k - 1)`. Para `t` con `vig_reloj[k] < t`: `en(k)`. Para `t == vig_reloj[k]`: `en(k - 1)`.

## ReferenciaTemporal

| Forma | Valor | Rango | Se resuelve a |
|-------|-------|-------|---------------|
| instante | `t` (entero ≥ 0) | `0 ≤ t ≤ reloj_actual` | acción en curso `k` y corte `t`, o decisión `k` si `vig_reloj[k] == t` |
| antes de la acción | `#k` (entero ≥ 1) | `1 ≤ k ≤ acciones + 1` | decisión `k` (punto con `accion ≤ k - 1` más `k - 1 - accion` acciones) |

## AgendaConCorte

Subclase de `AgendaEventos` (`Modelo/AgendaConCorte.py`) con el atributo `corte`. `siguiente()` devuelve `None` si el próximo evento tiene
`tiempo > corte`. El clon cambia `agenda.__class__` y fija `corte`. No se usa en la partida real. Costo: `O(1)` más lo de
`AgendaEventos`. El motor no cambia.

## ResumenHistorico (DTO)

Datos de solo lectura, sin referencias a objetos del motor.

| Campo | Fuente |
|-------|--------|
| `referencia` | `("instante", t)`, `("accion", k)`, `("actual", None)` o `("final", None)` |
| `reloj` | el consultado (R9) |
| `sala` | id y nombre de `jugador.sala` |
| `vida`, `vida_max`, `ataque`, `defensa`, `velocidad` | jugador del clon |
| `arma`, `armadura` | nombre del equipo del inventario del clon, o `None` |
| `inventario` | nombres y cantidades; los **pergaminos** salen de la serie, el resto del clon |
| `efectos` | lista `(tipo, detalle)` de `VENENO`, `FIN_VELOCIDAD` y `APAGAR_ANTORCHA` activos del jugador, leídos de la agenda del clon y de `antorcha_encendida` |
| `enemigos` | `(id, tipo, vida, vida_max)` de los vivos en la sala, ordenados por id con `elegir_algoritmo` |
| `mapa` | `clon.mapa_conocido()` (DTO `MapaConocido`, capacidad 001), sin recalcular |
| `resultado` | `"victoria"`, `"derrota"` o `None` (solo en un estado final terminado) |

`Vista/TextoResumen.py` convierte el DTO en texto con una función de módulo; no depende de K (FR-028).

## RegistroLinea (Persistencia)

`k` y la lista de registros del guion (tuplas `(tipo, nombre, argumento, reloj, secuencia)`). Bytes en
[formato-partida.md](contracts/formato-partida.md). `to_bytes()` / `from_bytes()` como `RegistroJugador`.

## GestorHistorico y FuenteSinRed

| Pieza | Descripción |
|-------|-------------|
| `FuenteSinRed` | implementa la interfaz de fuente; devuelve las versiones y los detalles capturados al empezar o cargar, y **lanza `SinDatosParaHistoria`** en cualquier otro método |
| `GestorHistorico` | un `GestorDatos(FuenteSinRed(...))` cuyo `almacenamiento_disco` es el del gestor vivo (solo lectura). Sin contadores ni caché compartidos con la partida |

## Memoria (FR-021, SC-006)

```text
M(n) = n · b_guion  +  (retrocesos y cargas) · b_guion  +  C · (S + N + E)  +  serie
C   ≤ ⌈n/K⌉ + 1 + L + P
```

No contiene el término «acciones × tamaño del estado»: para `K` fijo el segundo sumando crece como `n/K`. Duplicar `n` duplica `M`.
Con los números de la exploración previa local, no versionada (K = 50, N = 20): 100 puntos ≈ 2.6 MB para 5 000 acciones (**HIPÓTESIS**, M2).
