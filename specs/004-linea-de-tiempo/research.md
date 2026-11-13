# Research: Línea de tiempo y su persistencia

**Fecha**: 2026-11-09 (revisado el 2026-11-10 contra `main`, commit `29d68f5`) | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Notación: `n` = acciones del jugador de la historia vigente; `K` = acciones entre puntos de control; `C` = puntos de control
(`C ≈ ⌈n/K⌉ + 1 + L + P`, ver R5); `S` = tamaño del estado vivo copiado (actores, agenda, inventario, azar, conocimiento);
`N`, `E` = salas y salidas de la cripta; `a` = costo de una acción en el motor; `V` = acciones recortadas por un pergamino;
`L` = cargas en la historia; `P` = usos del pergamino.

Las complejidades son análisis. Todo tiempo o tamaño citado aquí viene de una **exploración previa local, no versionada**
(no está en el repositorio) y es **HIPÓTESIS**: la reemplazan M1 a M10 cuando las reproduzca `python main.py --bench`
(Principio VIII; plan de mediciones en [R15](#r15-plan-de-mediciones---bench)). Equipo de la exploración: Windows 10,
Python 3.12, cripta sintética lineal de 20 salas con enemigos errantes y guardianes, partida de 5 000 acciones
deterministas por semilla.

---

## Hallazgos sobre el código actual

Verificados leyendo el código de `main` (commit `29d68f5`, 2026-11-10); las cifras de tiempo y memoria son de la exploración
previa local, no versionada (**HIPÓTESIS**: la reemplazan M1 a M10). Ningún hallazgo cambió el repositorio. HL1, HL3, HL5, HL6, HL8,
HL10 y HL12 se re-verificaron contra el código de hoy (`MotorSimulacion.py`, `retroceso.py`, `FormatoBinario.py`, `ArchivoPartida.py`,
`Reproductor.py`, `ControladorPartida.py`, `PreparadorPartida.py`, `DTOS/Salida.py`, `GestorDatos.py` y `main.py`); lo que cambió desde
la versión anterior está en HL6 y HL8.

| # | Hallazgo | Evidencia | Efecto en el diseño |
|---|----------|-----------|---------------------|
| HL1 | **(a)** `MotorSimulacion` mezcla estado de partida con colaboradores: `gestor_datos` (con caché, planificador y una referencia de vuelta al motor, `conectar_estado_juego`), `restaurador` (archivo abierto), `historial` (cierres sobre objetos vivos), `mensajes`, el transitorio `enemigos_al_entrar`, `eco`. Sí se puede copiar el estado **sin** copiar la fuente de datos ni arrastrar el historial: `copy.deepcopy(motor, memo)` con `memo` que mapea `gestor_datos → None`, `restaurador → None` y `historial → Historial()` vacío. | `Modelo/MotorSimulacion.py:22-58` (re-verificado: sigue igual; `conocimiento` es parte del estado vivo y cuelga del motor). Lo que la capacidad 003 agregará (`ciclo`, `version_puertas`, `GrafoCripta`, `EspacioBusqueda`, `CampoDistancias`) **todavía no está en `main`**: cuando llegue, también cuelga del motor y `deepcopy` lo copia con él; `GrafoCripta` guarda referencias a las salas del esqueleto, que el `memo` de `materializar` re-liga a las del esqueleto nuevo (ver [interfaz-linea.md](contracts/interfaz-linea.md#choque-con-t015-de-a-persona-a-003)). Exploración previa local, no versionada, **HIPÓTESIS**: con 5 000 acciones y 20 salas, **2.3 a 2.6 ms** de mediana por copia; con 400 acciones, **1.8 ms y 44 KiB**; el clon re-simulado dio **0 diferencias** frente a la partida real. Hoy `Conocimiento._destino_de` es un método ligado al motor: `deepcopy` lo re-liga al motor clon. `Conocimiento.copiar()` (T119) **no** sirve para el clon: comparte `_destino_de`, `_salas` y `_salidas` con el original, es decir, apunta al motor y al esqueleto vivos. | R2: la copia usa `deepcopy` con sustitutos, no una copia campo por campo de todo el motor ni `Conocimiento.copiar()`. |
| HL2 | **`deepcopy` del motor completo falla con `RecursionError` al crecer la cripta** (con 20 y 60 salas funciona; con 120 y 200 en línea falla) porque `Sala → Salida → _origen/_destino → Sala` forma una cadena tan larga como el diámetro del mapa. | **HIPÓTESIS** (exploración previa local, no versionada; la reemplazan M1 a M10, en este caso M3): n=20: 1.8 ms; n=60: 4.5 ms; n=200: `RecursionError`. | El esqueleto (salas y salidas) **no** se copia con `deepcopy` (R2). |
| HL3 | **Compartir el esqueleto entre la partida y un clon contamina el presente**: el clon cambió `rastro` en las salas de la partida real. Atributos que cuelgan hoy del esqueleto: `Sala.rastro` (mutable, **puede no existir** en salas nunca visitadas: `actualizar_rastro` lo crea y su deshacer lo borra), `Salida.cerrada` (mutable); y fijados al crear la partida y sin cambios después: `Sala._ordinal`, `Salida._ordinal`, `_origen`, `_direccion` (de `Conocimiento`), `Salida._destino` (caché del motor) y `Salida.cerrada_en_esqueleto` (de `DTOS/Salida.py`, ver [interfaz-linea.md](contracts/interfaz-linea.md#qué-le-pide-la-línea-a-los-demás)). | Exploración previa local, **HIPÓTESIS**: 404 de 404 instantes con diferencia solo en `rastros`; con ese campo excluido, 0 diferencias. Código de hoy: `Modelo/Conocimiento.py:74-100`, `MotorSimulacion.actualizar_rastro`, `DTOS/Salida.py`. | Cada clon recibe un **esqueleto propio**, rehecho con una pasada iterativa desde una foto de los campos mutables (`Sala.rastro` con su ausencia, `Salida.cerrada`); `copy.copy` conserva los fijados al crear y `materializar` re-liga `_origen` y `_destino` por ordinal (R2). |
| HL4 | **(b)** `Historial`: máximo `MAX_INTERVALOS = 5`; cada `Cambio` es una función `deshacer` más texto; `deshacer_ultimo()` **saca** el intervalo; `to_bytes()` guarda `0` y `from_bytes()` devuelve un historial vacío. Los cierres capturan objetos vivos (`actor`, `salida`, `inventario`). `usar_pergamino` nunca llama a `abrir_intervalo`, así que cada uso revierte **una** acción (hasta 5 usos seguidos). | `Modelo/retroceso.py`; README línea 170 («deshace la última acción (máximo 5 hacia atrás)»); P1 §4.6 puntos 3 y 5. | Invertir hacia atrás con el `Historial` no sirve (R1). La spec, US2.5, habla de «un pergamino que revirtió las últimas 5»: contradice el código y a US2.1 (ver [Cambios propuestos](plan.md#cambios-propuestos-a-la-spec)). |
| HL5 | **(c)** El `CRPT` actual (versión 3) **no** es una copia completa. Guarda, por sala: rastro, enemigos **vivos** (id, tipo, vida, instante), objetos, trampas y puertas; del jugador: sala, vida, acciones, derrotados, llave usada, inventario; y, desde T074 a T077, el **bloque de conocimiento** (exploradas y recuerdos de puertas) y la tabla de **puertas reales** (las cerradas hoy, las cerradas en el esqueleto, las de llave y las de cierre automático). **No** guarda el azar (se resiembra), la agenda (se reconstruye), `secuencia`, efectos (veneno, velocidad, antorcha), cierres automáticos pendientes, `mensajes`, enemigos muertos ni el historial. La carga además cambia el estado a propósito (`cargar_partida` fija `reloj` y `tiempo_siguiente`, y activa los enemigos de la sala). | `Persistencia/ConversorPartida.py` (comentario inicial, `registros_desde_motor`, `registro_jugador_desde_motor`, `registro_conocimiento_desde_motor`, `_aplicar_registro`); `Gestor/PreparadorPartida.py:cargar_partida`. | Un punto de control no puede reutilizar esos bloques (R2, R8): siguen siendo con pérdida. |
| HL6 | **(d)** Estado de lo que la línea necesita de la capacidad 001, ya en `main`. **Hechas**: T076 (`VERSION_FORMATO = 3`; el `CRPT` ya trae los **tres campos de largo** `[largo jugador][largo conocimiento][largo línea de tiempo]`: la línea se escribe con largo `0` y al leer solo se salta con su largo; `_inicio_salas` y `_validar_encabezado` ya los usan), T084 (`VERSION_BITACORA = 2`, `@cargar`), T092, T093 (`Reproductor(fabrica_motor, version_cripta, version_catalogo, recargar=None)`: al llegar a `@cargar` llama a `recargar(motor)`, que **recibe el motor actual y devuelve el nuevo**), T094 (`guardar_motor(motor, ruta, gestor)`, sin vista; la recarga del replay vive en `main.ejecutar_replay`: guarda en un temporal, cierra el restaurador anterior y llama a `cargar_partida`), T096 (`ejecutar_replay(ruta, gestor)` sin vista) y T119 (`Conocimiento.copiar()`, serialización y lotes `aplicar`/`invertir`: está implementado; **esta capacidad no lo usa y no debe retirarse**). **Pendientes**: T113 (README) y T117 (revisión por la persona D). **Falta, y es de esta capacidad**: el parámetro `linea` en `guardar_partida` y `guardar_motor`; `leer_linea()` en `LectorPartida` (que además debe guardar `_inicio_linea` y `_largo_linea`, hoy locales de `_leer_largos`); (el `observador` y `reproducir_acciones` del `Reproductor` **ya están en `main`**, hechos por C en `b1b57d7`, 001-T123/T124: firma `Reproductor(fabrica_motor, version_cripta, version_catalogo, recargar=None, observador=None)`, `reproducir_acciones(encabezado, acciones) -> motor`, `reproducir(ruta) -> motor`, que solo lee la bitácora y llama a la anterior); `--hasta` y `--checkpoint-cada` en `main.py` (que además hoy no tiene `--verificar` ni `--forzar`, de la capacidad 002). | `Persistencia/ArchivoPartida.py`, `Persistencia/FormatoBinario.py`, `Bitacora/Reproductor.py`, `Controlador/ControladorPartida.py`, `Gestor/PreparadorPartida.py`, `main.py`, `specs/001-niebla-mapa-ir-a/tasks.md`. | La capacidad se escribe contra el código real de 001. Lo que falta de otras personas está en [plan.md](plan.md#enganches-y-requisitos-hacia-otras-personas). |
| HL7 | `cargar_partida` fija `motor.reloj = encabezado.reloj` y `jugador.tiempo_siguiente` a mano. En un punto de decisión la agenda **no** contiene el evento del jugador (ya se sacó) y `jugador.evento_actual` apunta a un evento viejo tras cargar. | `Gestor/PreparadorPartida.py:cargar_partida`; `MotorSimulacion.avanzar_hasta_jugador`. | El sello de cada decisión se toma de `motor.reloj` y `motor.secuencia`, no de `jugador.evento_actual` (R3). |
| HL8 | **(e)** El `ControladorPartida` anota la bitácora **solo** desde `_accion`, y solo después de que `motor.ejecutar_accion` devuelve `True`. Registra las ACCIONES `mover, abrir, atacar, recoger, soltar, equipar, usar, esperar, retroceder` (normalizando dirección y vaciando el argumento de `esperar` y `retroceder`). No anota `ayuda, inventario, mapa, mensajes, red, puntajes, guardar`. `cargar` no anota una acción: `_continuar_bitacora` (T092) copia la bitácora del guardado y le agrega la directiva `@cargar` con `marcar_carga()`, **solo si hay bitácora** y corresponde a la partida; el guion de la línea lleva su `CARGA` aunque no haya bitácora. El comentario `# ir a <sala>` va a la bitácora antes del primer `mover` y no entra al guion. Cada paso de `ir a` pasa por `_accion`, así que es una acción registrada. Si no hay bitácora (`self.bitacora is None`) la acción igual se ejecuta. | `Controlador/ControladorPartida.py:_accion, _ir, ejecutar`. | Punto único de enganche: justo después de `bitacora.registrar` (R3). `#k` puede apuntar a cada paso de un viaje. |
| HL9 | **Los pergaminos quedan fuera de la reversión** (P1 §2.11, §4.6 punto 3): `recoger_reversible` y `soltar_reversible` no registran `deshacer` si la clase es `pergamino_retroceso`, y `usar_pergamino` consume el pergamino sin registrarlo. Tampoco se deshace la **carga del contenido de una sala** (`cargar_contenido_salas` no registra nada). | `Modelo/retroceso.py`; `MotorSimulacion.cargar_contenido_salas`. | Rehacer la historia vigente con solo las acciones vigentes **no** reproduce el estado real tras un retroceso (ejemplo en R5). Obliga a un punto de control tomado del estado real después de cada retroceso, y a guardar en el archivo el guion completo (con los retrocesos) y no solo la historia vigente (R5, R8). |
| HL10 | `GestorDatos` tiene estado propio (contadores `aciertos_cache` y `fallos_cache` que muestra el comando `red`, caché LRU de 25 fichas, planificador de precarga) y guarda `estado_juego = motor`. Lee del disco todo lo que ya trajo y solo llama a la fuente ante un fallo. `obtener_esqueleto` devuelve objetos nuevos en cada llamada. | `Gestor/GestorDatos.py`. | Un clon no debe usar el gestor vivo: alteraría contadores y caché de la partida. Se usa un **segundo `GestorDatos`** cuya fuente no puede hacer solicitudes (R10). |
| HL11 | `argparse` termina con código **2** ante un valor inválido (`type=int`), y el código 2 está reservado a «versión incompatible». | `main.py`; Constitución, Principio VI. | `--hasta` y `--checkpoint-cada` se leen como texto y se validan a mano para dar código `1` (FR-013, FR-018) (R11). |
| HL12 | El motor ya tiene `obtener_estado_resumen()`, determinista, que sirve de oráculo de comparación en pruebas. No incluye `conocimiento`, `mensajes` ni `rastros`. | `MotorSimulacion.obtener_estado_resumen`. | Las pruebas lo usan y le agregan los tres campos que faltan (la exploración previa, E1, ya los agregaba). |
| HL13 | Costo de la partida real: **0.04 a 0.06 ms por acción** (mediana; p95 de 0.06 a 0.11 ms), cien veces por debajo del límite de 20 ms (§5.2). **HIPÓTESIS** (exploración previa local, no versionada; la reemplaza M5). | E1. | Rehacer K acciones es barato: el costo de una consulta lo domina la copia, no la re-simulación, mientras K sea pequeño (R7). |

### Respuestas directas a (a) a (e)

- **(a)** Sí. Se copia el estado vivo con `deepcopy` y tres sustitutos en `memo` (HL1), y el esqueleto aparte (HL2, HL3).
- **(b)** El `Historial` no sirve como línea de tiempo: 5 intervalos, funciones ligadas a objetos vivos, se consume y no se guarda (HL4).
- **(c)** Confirmado (HL5): los bloques del `CRPT` no son una copia completa; un punto de control no los reutiliza.
- **(d)** `@cargar` hace que el replay guarde el motor en un temporal y lo recargue (T094). La línea trata esa carga como una
  **frontera**: tras ella el estado cambia a propósito (azar resembrado, agenda rehecha, efectos perdidos). Por eso (1) se
  toma un punto de control del motor **ya cargado** al cargar, siempre, aunque no toque por K; (2) la línea anterior
  a la carga queda intacta y se consulta con sus puntos viejos; (3) en el instante de la carga rige el estado cargado.
  Detalle en [R7](#r7-k-por-defecto-fr-031-y-convivencia-con---replay-y-cargar) y [formato-bitacora.md](contracts/formato-bitacora.md).
- **(e)** HL8: un único punto, `_accion`, tras `bitacora.registrar`.

---

## R1. Cómo reconstruir el estado de un instante pasado (FR-001, FR-002, FR-019)

**Decisión**: **re-simular desde el punto de control más cercano** con las acciones registradas, sobre una copia del estado,
y para un instante `t` entre dos decisiones **cortar la agenda en `t`**.

| Alternativa | Tiempo de una consulta | Memoria | Veredicto |
|-------------|------------------------|---------|-----------|
| **A. Re-simular desde el punto de control** (elegida) | `O(log n + S + K·a)` | `O(n + C·S)` | Reusa el motor como única definición del juego; el determinismo ya es requisito (Principio III) |
| B. Aplicar cambios hacia adelante | `O(log n + S + c)`, `c` = cambios en ≤ K acciones | `O(cambios)` | El motor no emite cambios aplicables, solo cierres de deshacer; calcular el cambio por diferencia de estados cuesta `O(S)` por acción en el ciclo de juego. Exige que cada capacidad (A incluida) emita `aplicar`, lo que se prohibió suponer |
| C. Invertir hacia atrás desde el presente | `O(V)` | `O(1)` | **No sirve**, ver abajo |
| D. Sin puntos de control (desde la acción 0) | `O(n·a)` | `O(n)` | Exploración previa (**HIPÓTESIS**, E5; la reemplaza M1): 112 ms de mediana y 199 ms máximo con 5 000 acciones. Incumple FR-020 |

**Por qué invertir (C) no sirve con este `Historial`** (evaluación pedida):

1. Los cierres de `deshacer` capturan **objetos vivos** (`actor`, `salida`, `inventario`): invertir sobre una copia
   modificaría la partida real. `deepcopy` trata las funciones como atómicas y no re-liga sus celdas.
2. Se limita a 5 intervalos, se **consume** al usarse y no se guarda: no llega a una acción de hace 500.
3. No hay «rehacer»: tras deshacer no se puede volver al presente.
4. Deshacer en la partida real violaría FR-008 (la consulta no puede alterar nada).

**Qué exige re-simular** (cada requisito se comprobó en la exploración previa, E1 a E4, **HIPÓTESIS**; lo confirman M7 y M9):

- **Determinismo (Principio III)**: mismas acciones desde el mismo estado dan el mismo resultado. `random.Random` se copia con su
  estado (`getstate`, 625 enteros); el cazador de la capacidad 003 no consume azar (003 FR-021), así que no agrega estado al azar.
- **Estado completo en el punto de control**: reloj, `secuencia`, azar, agenda **con sus eventos cancelados pero aún en el
  montículo**, actores con sus atributos dinámicos (`veneno`, `evento_regen`, `botin`, `antorcha_encendida`), inventario con su
  cursor y equipo, objetos del suelo, contenido cargado, trampas, conocimiento, `mensajes`, contadores. Todo cuelga del motor, así
  que `deepcopy` lo toma.
- **Datos externos idénticos**: el clon no puede pedir nada nuevo (R10).
- **Comprobación**: antes de cada acción re-simulada se compara `(reloj, secuencia)` del clon con el sello guardado (R3). Si no
  coinciden, la reconstrucción se rechaza con `ErrorReconstruccion`, nunca se muestra un estado inventado.

**Estado en un instante `t` entre decisiones.** `ejecutar_accion` corre todos los eventos hasta la siguiente decisión del
jugador. Para parar en `t`, el clon cambia la clase de su agenda a `AgendaConCorte`, que oculta (`siguiente()` devuelve `None`)
todo evento con `tiempo > corte`. El motor no se modifica. Exploración previa (E3, **HIPÓTESIS**; la reemplaza M7): 404 de 404 instantes de evento coinciden con un «motor espía»
que guarda el resumen tras cada evento real (FR-002 incluido: los eventos coincidentes en `t` se reflejan todos).

**Regla de la decisión en `t`** (aclaración a FR-001): si el jugador decide en `t`, el estado es el punto de decisión. Un evento
con tiempo `t` y secuencia **posterior** a la decisión no se refleja, porque en la partida real ocurrió después de ella.

**Costo de FR-019**: con puntos en los múltiplos de `K`, una consulta rehace a lo sumo `K` acciones (`k - 1 - c ≤ K - 1`
para `#k`, y una más para un `t` dentro de la acción `k`).

---

## R2. Qué es una copia completa del estado y cómo se obtiene (FR-017, FR-021)

**Decisión**: una **copia estructurada** en dos partes.

1. **Estado vivo**: `copy.deepcopy(motor, memo)` donde `memo` mapea `gestor_datos → None`, `restaurador → None`,
   `historial → Historial()` y **cada `Sala` y `Salida` → ella misma** (se comparten solo dentro de la copia de seguridad, que
   nunca se modifica).
2. **Foto del esqueleto**: arreglos por ordinal con los campos mutables, `Sala.rastro` y `Salida.cerrada`
   (constantes `CAMPOS_MUTABLES_SALA` y `CAMPOS_MUTABLES_SALIDA`).

Para **consultar**, `materializar(punto, gestor_historico)` crea un esqueleto nuevo con una pasada iterativa (`copy.copy` de cada
sala y salida, campos mutables tomados de la foto, `_origen` y `_destino` re-ligados por ordinal), llama a `deepcopy` del estado
con un `memo` que mapea esqueleto-de-respaldo → esqueleto-nuevo, y asigna `gestor_datos = gestor_historico`.

| Alternativa | Copia | Memoria por punto | Veredicto |
|-------------|-------|-------------------|-----------|
| `deepcopy(motor)` a secas | 1.8 ms (N=20), 4.5 ms (N=60), **`RecursionError` (N ≥ ~120)** | 44 KiB (N=20), 95 KiB (N=60) | Descartada (HL2) |
| **Estructurada** (elegida) | 1.1 ms (N=20), 1.5 ms (N=60), 2.2 ms (N=200), 11.7 ms (N=2000) | 26, 29, 43, 285 KiB | Sin recursión, memoria casi plana en N |
| Campo por campo, a mano, de todo el motor | `O(S)` | similar | Cada campo nuevo de A, B o C hay que listarlo; un olvido se vuelve un estado falso silencioso. Queda como **plan B** si M3 mostrara que `deepcopy` no alcanza |
| Serialización (`pickle` o bloques `CRPT`) | `O(S)` + empaquetar | similar | `pickle` no admite cierres ni archivos abiertos y **ejecuta código al leer**: inaceptable en un archivo de partida. Los bloques `CRPT` son con pérdida (HL5) |

**Costo de consultar**, exploración previa (esqueleto nuevo + `deepcopy` + K=50 acciones; E4; **HIPÓTESIS**, la reemplaza M3): **1.85 ms** (N=20), **7.95 ms** (N=200),
**69.4 ms** (N=2 000). Con la escala de los datos locales (5 a 20 salas) sobra margen; con miles de salas la materialización del
esqueleto, `O(N + E)`, pasa de los 50 ms. Es el límite de escala de esta decisión (ver [Riesgos](plan.md#riesgos)).

**Principio I (justificación de `copy`).** `copy` no sustituye a ninguna estructura evaluada: las estructuras evaluadas (agenda,
inventario, historial, ordenamientos, archivo con índice, caché) siguen siendo las del proyecto y es lo que se copia. La estructura
que esta capacidad evalúa (arreglos de la línea, búsqueda binaria, recorte, serie de pergaminos) es propia. El `memo` es el
argumento documentado de `deepcopy`: un `dict` temporal, de una sola llamada, que no indexa datos del juego ni se conserva
(uso auxiliar permitido por el Principio I); queda anotado en el [Complexity Tracking](plan.md#complexity-tracking) para revisión del grupo.

**Contrato con las demás personas** (en [interfaz-linea.md](contracts/interfaz-linea.md)): todo el estado nuevo debe colgar del
motor, de sus actores o de sus salas; sin cachés a nivel de módulo; si se agrega un campo mutable a `Sala` o `Salida`, se agrega a
las constantes de campos mutables. Lo comprueba una prueba que compara la copia estructurada con `deepcopy` completo en cripta
chica (oráculo) y el `obtener_estado_resumen()`.

---

## R3. Qué se registra entre puntos de control (FR-021)

**Decisión**: un **guion** append-only con un registro por comando aceptado, y la **historia vigente** como arreglos paralelos
que se recortan por el final.

```text
guion (todo lo aceptado)          vigente (solo las acciones que cuentan)
  tipo, nombre, argumento,         accion_guion[j]   posición en el guion
  reloj, secuencia                 reloj_dec[j]      sello: reloj en la decisión
                                   sec_dec[j]        sello: secuencia en la decisión
```

- Tipos del guion: `ACCION` (cuenta como acción), `RETROCESO` (acepta `retroceder`, no cuenta) y `CARGA`.
- **Sello = (`motor.reloj`, `motor.secuencia`) en el punto de decisión previo a la acción** (HL7). El reloj es estrictamente
  creciente (cada acción cuesta ≥ 1), así que ubica `t`. La secuencia no se usa para ubicar: sirve para **verificar** la
  re-simulación y detectar un motor no determinista.
- **De dónde sale el sello previo (regla de registro)**: `despues_de_accion` llega con el motor **ya avanzado** (el `Reproductor`
  y `_accion` avisan después de `ejecutar_accion`), así que el sello `(reloj, secuencia)` previo de la acción *k* **se toma al
  terminar el aviso anterior**: el que dejó `al_crear_motor` (para la acción 1), `despues_de_accion` de la acción *k − 1*,
  `registrar_retroceso` (tras un `retroceder`) o `despues_de_carga` (tras un `@cargar`, con el motor nuevo). La línea guarda ese
  sello al cerrar cada aviso y lo usa como `vig_reloj`/`vig_sec` de la acción siguiente; no puede leerlo del motor al recibir
  la acción *k*.
- **Relación con la bitácora**: el guion lleva los mismos comandos, en el mismo orden y con el mismo texto que las líneas de
  acción de la bitácora, más los sellos. Se anotan en el mismo lugar (`_accion`), así que no se desfasan. El guion existe aunque
  no haya bitácora (la bitácora es opcional, el aviso de `_continuar_bitacora`), porque FR-022 pide un archivo de partida
  autosuficiente.
- **Por qué el guion y no solo lo vigente**: HL9. Tras un retroceso la partida real conserva efectos irreversibles (un pergamino
  recogido, el contenido de una sala cargada). Solo el guion completo, con el `RETROCESO`, los reproduce.
- **Por qué no se guardan cambios de estado** (spec: «Cambio»): ver R1-B. «Cambio» queda como «acción registrada» (ver
  [Cambios propuestos](plan.md#cambios-propuestos-a-la-spec)).

| Operación | Tiempo | Memoria |
|-----------|--------|---------|
| `registrar_accion` | `O(1)` amortizado (más una copia `O(S)` cada K acciones) | pocas decenas de bytes por registro más el texto (**HIPÓTESIS**, M2) |
| `recortar(V)` | `O(V)` | libera `V` posiciones |

---

## R4. Ubicar el punto de control más cercano (FR-019, FR-020)

**Decisión**: búsqueda binaria **propia** (`Modelo/BusquedaBinaria.py`, sin `bisect`, `sorted`, `sort`, `heapq`, `collections`
ni `dict` o `set` como índice) sobre dos arreglos ordenados.

1. Por **tiempo**: `ultimo_menor_o_igual(reloj_dec, t)` da la acción `k` en curso. Los relojes crecen estrictamente.
2. Por **acción**: `ultimo_menor_o_igual(pc_accion, k - 1)` da el punto de control. `pc_accion` es **no decreciente**
   (puede repetir un valor: un punto regular y el de una carga en la misma acción); la búsqueda devuelve el **último** de los
   iguales, que es el posterior a la carga.

| Alternativa | Tiempo | Veredicto |
|-------------|--------|-----------|
| **Binaria sobre arreglos** (elegida) | `O(log n)` y `O(log C)` | Funciona con puntos irregulares (retroceso, carga) |
| Fórmula `k // K` | `O(1)` | Falla con los puntos extra de R5 y R7 |
| Lista enlazada de puntos | `O(C)` | Sin ventaja; `C` crece con la partida |
| `dict` por número de acción | `O(1)` | Prohibido como índice (Principio I) |

---

## R5. Recorte al usar un pergamino y punto de control posterior (FR-015, FR-016, FR-027)

**Decisión**: tras un `retroceder` aceptado, la línea (1) calcula `V = acciones_antes - acciones_después` con
`motor.acciones_jugador`, (2) saca del final `V` posiciones de `vigente` y todos los puntos de control con `accion > nuevo_n`,
(3) agrega un `RETROCESO` al guion, (4) **toma un punto de control del motor real** en `nuevo_n` (si ya había uno en `nuevo_n`,
lo reemplaza), y (5) pliega la serie de pergaminos (R6).

**Costo**: `O(V)` más una copia `O(S)`. No depende de `n` (FR-027). Con 5 usos seguidos son 5 recortes de 1 acción.

**¿Hace falta el punto de control tras el retroceso? Sí**, y no por las acciones, sino por lo que el retroceso no deshace (HL9):

> Acciones 1 a 6 vigentes. La acción 7 recoge un pergamino P. Se usa otro pergamino Q: vuelve el reloj a la decisión 7,
> **P sigue en el inventario** y Q se consumió. La acción 8 (nueva) es `soltar P`. Rehacer desde un punto anterior a la 7 con la
> historia vigente no tiene a P: el motor rechazaría `soltar P`. Un punto de control en la decisión 7 tomado del motor real sí lo tiene.

Es decir, **un punto de control del estado real es la única forma de que lo posterior a un retroceso se reconstruya igual que la
partida**. Lo anterior al retroceso se reconstruye desde los puntos previos, que son copias del estado real en su momento, y las acciones
vigentes previas no dependen de lo irreversible posterior. Esa misma propiedad (todo punto de control es una copia del motor real en una
decisión) es lo que hace correctas las consultas.

**Cota de memoria con los puntos extra**: `C ≤ ⌈n/K⌉ + 1 + L + P` (el `+1` es el estado inicial, `L` cargas, `P` usos del pergamino
que no coinciden con un punto existente). FR-017 y SC-006 hablan de «no más de uno cada K»: ver
[Cambios propuestos](plan.md#cambios-propuestos-a-la-spec). Sin el punto extra la cota sería la de la spec, pero la reconstrucción
dejaría de ser exacta.

**Alternativas**: (a) no tomar el punto y confiar en que el `Historial` restaura todo: falso por HL9 y por el riesgo que reconoce
P1 §4.6 punto 6 (cualquier mutación no reportada a `registrar` queda sin revertir; es el riesgo con A); (b) reemplazar el punto previo
más cercano por el nuevo: rompe FR-019, porque las consultas anteriores rehacerían hasta `2K - 1` acciones.

---

## R6. Cantidad de pergaminos por instante (FR-029)

**Decisión**: una **serie** aparte, `(clave, cantidad)`, que no depende del punto de control.

- `clave` = acciones vigentes completadas en el momento del cambio. Un cambio ocurrido **durante** la acción `j` (recoger, soltar,
  usar un pergamino) lleva clave `j`; el consumo de `retroceder` lleva clave `nuevo_n`.
- Se agrega un registro cuando, después de cada comando aceptado, la cuenta de objetos de clase `pergamino_retroceso` del inventario
  cambió. Contar cuesta `O(capacidad del inventario)`, ≤ 10.
- **Al recortar** a `nuevo_n`: se sacan los registros con clave `> nuevo_n` y se agrega `(nuevo_n, cantidad_actual)` si difiere
  del último. Costo `O(registros sacados)`. Así la serie queda **ordenada por clave** y admite búsqueda binaria (R4).
- **Consulta**: para `#k` se busca la última clave `≤ k - 1`; para `t` con la acción `k` en curso (R[k] < t), la última clave `≤ k`;
  para `t = R[k]`, la última `≤ k - 1`.
- El resumen muestra esa cantidad en lugar de la del clon, y el resto del inventario sale del clon.

**Regla para el instante del retroceso**: la posición `#m` (a la que se retrocedió) ocurrió dos veces en el tiempo real, antes de
las acciones revertidas y después de usar el pergamino. Se muestra la **última** ocurrencia, que es el presente. Para las posiciones
anteriores a `m`, que ocurrieron una sola vez, se muestra lo que el jugador tenía entonces (US2.8).

| Alternativa | Veredicto |
|-------------|-----------|
| **Serie plegada** (elegida) | `O(1)` por cambio, `O(V)` por recorte, `O(log n)` por consulta, memoria `O(cambios de pergaminos)` |
| Recalcular desde el clon | Falla: el clon rehace la historia vigente, que no tiene los pergaminos recogidos en acciones revertidas ni los consumidos por retrocesos |
| Un campo en cada punto de control | Daría el valor del punto, no el del instante entre puntos |
| Registrar un tiempo real | No existe: el motor no usa reloj real (Principio III) |

---

## R7. K por defecto, FR-031 y convivencia con `--replay` y `@cargar` (FR-018, FR-030, FR-031)

**K por defecto: 50** (**HIPÓTESIS** hasta M1 y M2). Exploración previa local, no versionada, E5 (**HIPÓTESIS**; la reemplazan M1 y M2; 5 000 acciones, 20 salas, 60 consultas
aleatorias, tiempo = materializar + rehacer + resumen):

| K | Puntos de control | Partida de 5 000 acciones | Consulta: mediana / p95 / máximo |
|---|-------------------|---------------------------|----------------------------------|
| 1 | 5 000 | 9.08 s | 1.66 / 2.33 / 4.19 ms |
| 10 | 500 | 1.10 s | 2.21 / 3.87 / 4.63 ms |
| **50** | **100** | **0.40 s** | **2.91 / 4.58 / 5.64 ms** |
| 100 | 50 | 0.30 s | 3.73 / 6.41 / 7.59 ms |
| 500 | 10 | 0.24 s | 12.92 / 25.19 / 32.13 ms |
| sin puntos (5 000) | 1 | 0.22 s | 112.66 / 191.85 / 199.37 ms |

Con K = 50 el costo extra de registrar es ≈ 0.036 ms por acción, la copia sucede cada 50 acciones (≈ 1 a 2 ms, muy por debajo de los
20 ms del ciclo, §5.2), 100 puntos ≈ 2.6 MB y la consulta tiene un margen de 10 veces sobre los 50 ms de FR-020. K = 1 es válido pero
caro en tiempo (1.8 ms por acción) y memoria; K = 500 se acerca al límite; sin puntos de control incumple.

**FR-031**: el `K` se guarda en el bloque de línea (R8). Con `--cargar F --checkpoint-cada N` se rechaza antes de cargar (código `1`).
El comando interactivo `cargar` adopta el K del archivo sin error: el rechazo de FR-031 es de la línea de comandos.

**Con `--replay`**: `--checkpoint-cada` es válido y solo cambia el costo (FR-028). Con `@cargar` dentro del replay, el archivo
temporal que escribe el replay lleva el K de la ejecución, no el de la partida original; la spec dice «rige el K del archivo
cargado» y es literalmente cierto, pero ese archivo es el temporal. No cambia el contenido de ningún resumen.

**Frontera de carga (d)**. Al cargar, la línea: (1) conserva el guion y los puntos anteriores, (2) agrega un registro `CARGA` al
guion con el reloj cargado, (3) toma un punto de control **del motor ya cargado** en la acción `n` (siempre, aunque no toque por K; si
había un punto regular en `n`, lo reemplaza porque es del estado previo al guardado), (4) abre una época nueva con una **copia privada
del archivo cargado** para que los clones puedan restaurar salas pendientes (R10). El historial de retroceso queda vacío (comportamiento
actual): el primer `retroceder` tras cargar se rechaza como en la Parte I.

---

## R8. Persistencia de la línea (FR-022, FR-023, FR-024, FR-025, FR-031)

**Decisión**: el `CRPT` 3 lleva un **bloque de línea** con `K` y el **guion** completo. **Los puntos de control no se guardan: se
reconstruyen al cargar** reproduciendo el guion.

Disposición (acepta el orden de la persona C, P-10). **Verificado en `main`** (`ArchivoPartida.py`, `FormatoBinario.py`): el `CRPT` 3
**ya tiene los tres campos de largo** (el contrato de 001 dice «dos» en una línea y muestra tres en otra; manda el código: tres):

```text
v3: [encabezado][largo jugador][jugador][largo conocimiento][conocimiento][largo línea][línea][salas][índice]
```

- `largo línea`: `<I`. Hoy `guardar_partida` lo escribe siempre en `0` y `LectorPartida._leer_largos` lo lee y salta el bloque. PR-10 **solo
  llena el bloque**: no agrega el campo ni sube `VERSION_FORMATO` (P-10: no se mantienen archivos v3 intermedios). `0` significa «sin
  línea» (benchmarks de registros sueltos, el temporal del replay, archivos v3 escritos antes de esta capacidad); `cargar_partida` lo
  acepta y la línea empieza en la carga, sin historia previa.
- `_inicio_salas = TAMANO_ENCABEZADO + (4 + largo_jugador) + (4 + largo_conocimiento) + (4 + largo_línea)` (ya es la suma que calcula
  el código; PR-10 la deja cerrada en el contrato).
- `_validar_encabezado`: `offset_indice ≥ TAMANO_ENCABEZADO + 12` (hoy `INICIO_MINIMO_SALAS`) y el índice cabe en el archivo.
- Los tres campos de largo se leen con tres lecturas de 4 bytes (se salta de bloque en bloque), sin leer el contenido: leer una sala
  **no** lee la línea (P1 §4.10). Detalle y bytes en [formato-partida.md](contracts/formato-partida.md).

| | Guardar puntos de control completos | **Guardar el guion y reconstruir** (elegida) |
|--|-------------------------------------|---------------------------------------------|
| Código nuevo | Un serializador de **todo** el estado (agenda con referencias a actores, efectos, azar, inventario enlazado, trampas, conocimiento): una segunda definición de «estado» que A, B o C tendrían que mantener | Solo `RegistroLinea` (K + registros) |
| Tamaño | `C · S` serializado: 100 puntos × decenas de KB, y crece con el estado | ~30 bytes por comando (`1+2+nombre+2+argumento+8+8`), `O(n)`, no depende de `S` |
| Carga | `O(C·S)` | `O(n·a + C·S)`: ≈ 0.1 ms por acción (E1, E5), unos 0.5 s para 5 000 acciones (**HIPÓTESIS**, la reemplaza M6) |
| Consistencia | Un campo olvidado deja un punto falso en silencio | El motor es la única definición; el sello detecta divergencias |
| Compatibilidad | Cada cambio del motor invalida los puntos guardados | Cada cambio de comportamiento del motor invalida el guion (lo detecta el sello) |

**Verificación al cargar**: el guion se reproduce desde la cripta y la semilla del encabezado (`preparar_partida` con el gestor
histórico, R10), con los `@cargar` como en el replay de la persona C. Por cada acción se compara `(reloj, secuencia)` con lo
guardado; al final se comparan reloj, sala, vida y acciones con el bloque del jugador. Cualquier diferencia se rechaza con
`Versión incompatible: la línea de tiempo no coincide con la partida` (código `2`) sin cargar nada.

**Si faltan datos locales al cargar.** Reproducir el guion usa el gestor histórico, sin red (R10); si falta un dato que el disco debería
tener (carpeta de datos locales borrada o de otra versión, paquete offline ausente), el guion no se puede reproducir. Alternativas:

| Alternativa | Veredicto |
|-------------|-----------|
| **A. Error y no cargar nada** (elegida): `! Error: No se puede reconstruir sin nuevas solicitudes: faltan datos locales (<qué>)`, código `1`; el motor, la bitácora y la línea que el jugador tenía quedan intactos | Es coherente con el resto de la carga (`cargar_partida` ya falla entera ante un archivo dañado) y con FR-025: lo que se carga es la partida **con** su línea, o nada. Ninguna solicitud, ningún presupuesto gastado |
| B. Cargar la partida sin línea (como si `largo línea = 0`), con aviso | Rompe FR-022 y SC-005 en silencio: `historia` respondería distinto de antes de guardar, y el siguiente `guardar` sobrescribiría el guion con uno vacío: pérdida de datos |
| C. Cargar la partida y reconstruir la línea más tarde (perezosa), cuando se use `historia` | La carga «funciona» y falla en un comando posterior, lejos de la causa; el guion vive en memoria sin verificar sellos y `guardar` guardaría una línea que nunca se comprobó |
| D. Permitir solicitudes a la red solo en este caso | Viola el Principio VII |

El código `1` no es el `2`: faltar datos locales no es una versión incompatible. Con `--cargar` desde la línea de comandos termina el
proceso con `1` sin abrir la partida; con el comando interactivo `cargar` muestra `No se pudo cargar: ...` y la partida en curso sigue
intacta (como hoy con un archivo dañado). Lo mismo vale para `--replay` con `@cargar`: la recarga del replay usa `cargar_partida`.

**Alternativa descartada**: reproducir desde la bitácora `.log` en vez de guardar el guion. La bitácora es opcional y
`_continuar_bitacora` ya contempla que falte; FR-022 pide autosuficiencia.

---

## R9. Un resumen único para `historia` y `--replay --hasta` (FR-006, FR-007, FR-028)

**Decisión**: `Modelo/ResumenHistorico.py` arma un DTO `DTOS/ResumenHistorico.py` a partir de un motor y un reloj de consulta, y
`Vista/TextoResumen.py` lo convierte en texto con una **función de módulo**. `VistaConsola.mostrar_resumen_historico` y `main.py`
(`--replay --hasta`) llaman a la misma función, así `--hasta` no instancia la vista (Principio II, T096 de la persona C).

- Contenido: reloj consultado, referencia, sala, vida/vida_max, ataque, defensa, velocidad, arma y armadura, inventario con los
  pergaminos de la serie (R6), efectos activos (de la agenda del clon), enemigos vivos de la sala con vida y el `MapaConocido`
  de `motor.mapa_conocido()` (capacidad 001, sin recalcular).
- El reloj mostrado es el **consultado**, no el del último evento ejecutado (que puede ser menor).
- La salida depende solo del DTO: K no figura (FR-028).

---

## R10. Reconstruir sin solicitudes nuevas (Principio VII)

**Decisión**: el clon recibe un **segundo `GestorDatos`** (`Gestor/GestorHistorico.py`), construido con la misma carpeta de disco
(`almacenamiento_disco` compartido en solo lectura) y una `FuenteSinRed`: las versiones y los detalles de la cripta salen de valores
capturados al empezar o cargar, y **cualquier otro método lanza** `SinDatosParaHistoria`.

- La caché desaloja fichas de la memoria (25), pero el disco conserva todo lo que ya se trajo (HL10). Por tanto, una sala que la caché
  de memoria desalojó se vuelve a leer del **disco**, sin solicitud. Si el disco no la tiene (carpeta borrada, versión cambiada) la
  consulta termina con `! Error: No se puede reconstruir sin nuevas solicitudes: faltan datos locales (<qué>)` y código `1`; no se
  gasta presupuesto.
- No toca los contadores de `red` ni la caché de la partida (HL10).
- Para los **archivos de partida** (salas pendientes de un `CRPT` cargado): la línea guarda por cada carga una copia privada del
  archivo en una carpeta temporal y el clon abre un `RestauradorPartida` sobre ella. Así lo que se restaura es lo que el archivo
  decía al cargar aunque un guardado posterior sobrescriba el original (que guardaría el estado posterior de esa sala).
- La reconstrucción al **cargar** usa el mismo gestor histórico: reproduce el pasado leyendo del disco y no hace solicitudes aunque el
  modo sea con red (la partida cargada sigue usando su gestor normal). **Si faltan datos locales, la carga falla entera**: error con
  código `1` y nada cargado (alternativas y motivo en [R8](#r8-persistencia-de-la-línea-fr-022-fr-023-fr-024-fr-025-fr-031)).

| Alternativa | Veredicto |
|-------------|-----------|
| **Segundo gestor sin red** (elegida) | La garantía es estructural: no existe camino a la red |
| Reusar el gestor vivo | Altera contadores, caché y `estado_juego`; confía en que nunca falle un acierto de disco |
| Guardar fichas y contenidos en la línea | Duplica datos del catálogo y de la cripta; viola el espíritu del Principio IV (datos de cripta fuera de la fuente) |

---

## R11. Opciones de `main.py` y la tabla de prioridad de la capacidad 002

**Decisión**: `--hasta` y `--checkpoint-cada` **no son modos**: modifican a `--replay`, a la partida nueva y a `--bench`. La tabla de
prioridad `--bench > --mostrar-puntajes > --verificar > --replay > --cargar > --cripta` no cambia (README y contrato público).
Reglas completas, mensajes y códigos en [comandos-historia.md](contracts/comandos-historia.md). Resumen:

1. `--bench` ignora todo, también `--hasta` y `--checkpoint-cada` (sin validarlos).
2. En el resto, los valores se validan **antes** de ejecutar nada, con código `1`.
3. `--hasta` exige `--replay` en la línea de comandos; sin él, error de uso. Si `--replay` queda ignorado por un modo de mayor
   prioridad (`--mostrar-puntajes`, `--verificar`), `--hasta` se ignora con él.
4. `--checkpoint-cada` con `--cargar` es error de uso (FR-031), salvo que `--replay` tenga prioridad y deje a `--cargar` ignorado.
5. `--forzar` no se relaciona con las opciones nuevas.

---

## R12. Revisión de P1 §4.6 (historial de retroceso) con la carga nueva

**Lo que pide el enunciado de la Parte II** (no está en el repositorio; texto citado por la persona D). **§5.6**: «Repitan las
mediciones de la primera parte con la carga nueva. Si alguna decisión deja de ser adecuada, cámbienla y documenten el antes y el
después; si sigue siendo adecuada, muéstrenlo con datos» (agenda P1 §4.1 e historial de retroceso P1 §4.6). **§6.3**: `--bench` debe
incluir «las mediciones de la primera parte repetidas con la carga nueva (§5.6)».

**Qué hace esta capacidad con eso**:

- **Historial de retroceso (P1 §4.6)**: es de esta capacidad. Se repite su medición con la línea registrando (**M10**, [R15](#r15-plan-de-mediciones---bench)):
  el `bench_retroceso` existente (`tests/bench_personaC.py`: 5 intervalos × 50 cambios, tiempo de registrar y de deshacer) con y sin la
  línea, más el costo de `retroceder` con la línea (recorte y punto del estado real, que M4 mide con más detalle). Resultado para
  `DECISIONES.md`: **tabla antes y después**. Si M10 muestra que el `Historial` sigue siendo adecuado, se muestra con datos y no se
  cambia; si no, se cambia y se documenta el antes y el después (§5.6).
- **Agenda (P1 §4.1)**: **no es de esta capacidad** [PERSONAS: grupo]. La línea solo la copia con el motor y la corta con
  `AgendaConCorte`; quien mida la agenda con la carga nueva es otra persona del grupo.
- **§6.3**: M10 va dentro de `python main.py --bench` (PR-14) y su salida se incluye en `resultados_bench_linea.txt`.

Esta revisión además se contrastó con el Documento de Decisiones de la Parte I (`Proyecto Cripta.docx`, §4.6 y §4.10), el README y la
spec 004.

- **P1 §4.6, restricción «está prohibido guardar copias completas del estado»** se refiere a la reversión del pergamino (por acción,
  hasta 5). Los puntos de control son otra cosa (a lo sumo uno cada K acciones, FR-017, aprobado por la Parte II). El `Historial`
  **no cambia** y no los usa; M10 verifica con datos que sigue siendo adecuado.
- **P1 §4.6 punto 6** reconoce que una mutación no reportada a `registrar` queda sin revertir. Con la línea, ese riesgo ahora se
  **detecta**: la prueba «`consultar(#n+1)` igual al motor vivo tras un retroceso» falla si A omitió un cambio.
- **P1 §4.10 punto 6, «tras cargar no se puede deshacer»**: sigue cierto. Tras cargar el `Historial` queda vacío y la línea muestra el
  pasado sin permitir volver a él. El README debe decirlo para no confundir los dos mecanismos.
- **Carga nueva**: ni `guardar` ni `cargar` tocan el `Historial`. La línea registra la frontera de carga (R7) y la reconstrucción
  la rehace sin él.

---

## R13. Dónde vive cada pieza (Principio II)

| Pieza | Capa | Archivo |
|-------|------|---------|
| Línea, puntos de control, serie de pergaminos | Modelo | `Modelo/LineaTiempo.py`, `Modelo/PuntoControl.py`, `Modelo/CopiaEstado.py` |
| Búsqueda binaria propia, agenda con corte | Modelo | `Modelo/BusquedaBinaria.py`, `Modelo/AgendaConCorte.py` |
| Resumen | Modelo + DTO | `Modelo/ResumenHistorico.py`, `DTOS/ResumenHistorico.py` |
| Texto del resumen (sin instanciar la vista) | Vista | `Vista/TextoResumen.py`, `VistaConsola.mostrar_resumen_historico` |
| Gestor sin red | Gestor | `Gestor/GestorHistorico.py` |
| Bloque en el archivo | Persistencia | `Persistencia/RegistroLinea.py`, `ArchivoPartida.py`, `FormatoBinario.py` |
| Enganche en `_accion`, `historia`, reconstrucción, `--replay --hasta` | Controlador | `Controlador/ControladorPartida.py`, `Controlador/ObservadorLinea.py`, `Controlador/ReconstructorLinea.py`, `Controlador/ConsultaHistoria.py` |

`Modelo/` no importa red, archivos, consola ni adaptadores: recibe el gestor histórico y la ruta de la copia privada **inyectados**.

---

## R14. Enganches con otras personas

Ver la sección [Enganches y requisitos hacia otras personas](plan.md#enganches-y-requisitos-hacia-otras-personas) del plan. Resumen:
el `Reproductor` ya tiene `observador` opcional y `reproducir_acciones` (hecho por C, `b1b57d7`) [PERSONAS: C]; el campo `[largo línea]` ya existe y PR-10 solo
llena el bloque [PERSONAS: C]; T119 (copiar y serializar `Conocimiento`, lotes aplicar/invertir) está implementado: esta capacidad no
lo usa y no debe retirarse [PERSONAS: C]; `--bitacora` igual a `<guardado>.log` ya se rechaza en el origen (hecho por C, `b6f9f52`) [PERSONAS: C]; A debe mantener
todo su estado colgando del motor, declarar campos mutables nuevos del esqueleto y excluir `Modelo/CopiaEstado.py` de la prueba de T015
[PERSONAS: A]; M10 (P1 §4.6) y la agenda (P1 §4.1, no es de esta capacidad) [PERSONAS: grupo].

---

## R15. Plan de mediciones (`--bench`)

Archivo: `tests/bench_linea.py`, resultados en `resultados_bench_linea.txt`, enganchado a `python main.py --bench`
([PERSONAS: B, C] el despachador de `--bench` es compartido). Cripta sintética de 20 salas (y 100 y 200 donde se indique) generada
en carpeta temporal, sin red. **Partidas de 5 000 acciones deterministas por semilla** (semillas 1, 2 y 3): un generador con
`random.Random(semilla)` propio elige entre atacar, esperar y mover; el jugador tiene vida alta para sobrevivir. Cada medición se
repite y se toma la mediana, el p95 y el máximo.

| M | Qué mide | Variables | Criterio |
|---|----------|-----------|----------|
| M1 | Tiempo de `historia` (instantes y acciones repartidos en toda la partida) | K ∈ {1, 10, 50, 100, 500}, **sin puntos de control**, n = 5 000 | FR-020/SC-002: 100 % < 50 ms con el K por defecto. Justifica el K por defecto |
| M2 | Memoria de la línea (`tracemalloc`) y bytes por punto | K igual que M1; n ∈ {2 500, 5 000, 10 000} | SC-006: duplicar n duplica la memoria; puntos ≤ ⌈n/K⌉ + 1 + L + P |
| M3 | Costo de una copia y de materializar | N ∈ {20, 60, 200, 2 000}; `deepcopy` a secas frente a estructurada | Justifica R2 y fija el límite de escala; decide el plan B |
| M4 | Costo del recorte | `retroceder` en partidas de 500, 5 000 y 50 000 acciones | SC-010/FR-027: tiempo ~constante; fija el umbral |
| M5 | Sobrecosto de registrar por acción en el ciclo del juego | con y sin línea; mediana, p95 y máximo, incluidos los picos de copia | p95 < 20 ms (§5.2) |
| M6 | Carga: tiempo de reconstrucción y tamaño del bloque | n ∈ {1 000, 5 000, 20 000}; K; con y sin `@cargar`; tamaño del guion frente a `len(pickle.dumps(punto))` solo como **cota de referencia** de guardar puntos completos | Justifica R8 |
| M7 | Equivalencia de contenido (no de tiempo) | los mismos 100 instantes con K ∈ {1, 50, 500}, 3 semillas | FR-028: resúmenes idénticos |
| M8 | `--replay --hasta` de principio a fin | con y sin `--checkpoint-cada` | Informa; el costo es el de un replay completo |
| M9 | Oráculo de la copia | copia estructurada frente a `deepcopy` completo, N ≤ 60 | Resúmenes iguales |
| M10 | **Repetición de P1 §4.6 con la carga nueva** (§5.6, §6.3): el `bench_retroceso` de `tests/bench_personaC.py` (5 intervalos × 50 cambios; registrar y deshacer) **antes** (solo `Historial`) y **después** (con la `LineaTiempo` registrando cada acción y recortando en cada `retroceder`); además un `retroceder` real con la línea en partidas de 500, 5 000 y 50 000 acciones | misma carga de P1 §4.6 más partidas de 5 000 acciones, 3 semillas; mediana, p95 y máximo | Tabla **antes y después** para `DECISIONES.md`. Si el `Historial` sigue siendo adecuado, se muestra con datos; si no, se cambia y se documenta (§5.6). La agenda (P1 §4.1) no se mide aquí [PERSONAS: grupo] |

**Alternativa «sin puntos de control»** = un único punto en la acción 0 (K = n): es la fila de comparación de M1, M2 y M5.

---

## T003: revisión de deepcopy y memo (2026-11-12)

**Método.** Lectura del código de `main` (`eb92322`) y **medición real** de `copy.deepcopy(motor, memo)` con el `memo` de T015
(`gestor_datos → None`, `restaurador → None`, `historial → Historial()` nuevo, cada `Sala` y `Salida` → ella misma). Intérpretes:
Python 3.14.2 y 3.12.10 (Windows 10, límite de recursión 1000). Motor real armado con `crear_paquete_niebla` (paquete offline,
`GestorDatos` y `ControladorPartida` reales); cripta en cuadrícula de N = 20, 200 y 2 000 salas (62, 742 y 7 820 salidas), con
guardianes y trampas; **300 acciones** deterministas (`random.Random(5)`: atacar, esperar, mover; vida alta; 300 aceptadas, 0
rechazadas); **mediana de 20 repeticiones** (`perf_counter`); memoria con `tracemalloc`. Fuente: `informe_t003_deepcopy.md` e
`informe_estado_004.md` (locales, no versionados; los scripts de medición no se conservaron). Estas cifras **reemplazan a las
anteriores solo en lo que miden**; M3 (T103) las repite en `tests/bench_linea.py`.

### Campos de `Sala` y `Salida` (leídos del código y comprobados)

| Objeto | Campo | ¿Mutable en la partida? | Quién lo escribe | Tratamiento |
|--------|-------|-------------------------|------------------|-------------|
| `Sala` | `rastro` | **Sí** (cada acción, reversible) | `MotorSimulacion` (`actualizar_rastro`), `ConversorPartida`, `PreparadorPartida` | `CAMPOS_MUTABLES_SALA`; va en `foto_rastros`. **Una sala que el jugador nunca pisó no tiene el atributo** (medido: `AttributeError: 'SalaEsqueleto' object has no attribute 'rastro'`) |
| `Sala` | `_ordinal` | No (una vez, al armar `Conocimiento`) | `Conocimiento.__init__` | `copy.copy` lo conserva |
| `Salida` | `cerrada` | **Sí** (abrir, cierre automático, restaurar sala; reversible) | `MotorSimulacion`, `ConversorPartida` | `CAMPOS_MUTABLES_SALIDA`; va en `foto_cerradas` |
| `Salida` | `cerrada_en_esqueleto` | No (solo `__init__`) | `DTOS/Salida.py` | `copy.copy` lo conserva |
| `Salida` | `costo` | No (solo `__init__`; campo nuevo de 003) | `DTOS/Salida.py` | `copy.copy` lo conserva |
| `Salida` | `_ordinal`, `_direccion`, `_origen` | No (una vez, al armar `Conocimiento`) | `Conocimiento.__init__` | `copy.copy` conserva `_ordinal` y `_direccion`; `_origen` se re-liga por ordinal |
| `Salida` | `_destino` | No (caché que solo se llena) | `MotorSimulacion._destino`; `Conocimiento.__init__` la resuelve para todas | se re-liga por ordinal |

El inventario no es un atributo del motor: es `motor.jugador.inventario`.

### Pruebas 1 a 9 (resultado medido)

| # | Qué se probó | Resultado medido |
|---|--------------|------------------|
| 1 | `deepcopy(motor, memo)` sin `RecursionError` ni `TypeError`; tiempo y memoria | **Termina bien** en N = 20, 200 y 2 000, en ambos intérpretes. Tiempo mediano (incluye armar el `memo`): **0.7 a 1.4 ms** (N = 20), **2.7 a 4.4 ms** (N = 200), **17.8 a 30.0 ms** (N = 2 000); varía hasta 1.9× entre corridas. Memoria neta del clon: **20, 62 y 407 KiB** (3.14.2; 23, 66 y 412 con 3.12.10); pico con el `memo`: **53, 226 y 1 429 KiB**. El `memo` es entre el 2 % y el 12 % del tiempo. **Frente a las cifras de E2/E4 (1.1 ms y 26 KiB; 2.2 ms y 43 KiB; 11.7 ms y 285 KiB, otro método): hasta 2.6× más lento y +43 % de memoria para N ≥ 200** |
| 2 | 50 acciones en el clon; comparar el vivo antes y después (`obtener_estado_resumen()` ampliado con `conocimiento`, mensajes, rastros, `vars` de cada `Sala` y `Salida`, agenda e historial) | En el vivo **solo cambió `Sala.rastro`** (8, 12 y 12 salas con un clon con gestor propio; 8, 4 y 4 con el clon sin gestor, que juega menos). Nada más cambió: reloj, secuencia, jugador, enemigos, eventos, puertas, acciones, azar, conocimiento, mensajes, `cerrada`, atributos de `Salida`, agenda e historial. Estas acciones no abren puertas |
| 3 | `retroceder` en el clon (con `Historial()` vacío) | **Se rechaza** (`puede_deshacer()` es `False`), el vivo y el clon quedan intactos y el pergamino sigue en el clon. Control: en un motor real, `retroceder` devuelve `True` y `acciones_jugador` baja de 300 a 299 |
| 4 | Inventario grande (`NodoInventario` con lista doble) | 50 y 100 nodos: OK. 200 y 400: `RecursionError: maximum recursion depth exceeded`. **Primer tamaño que falla: 165 nodos** (3.14.2) y 164 (3.12.10), con límite 1000, llamando a pocos marcos de profundidad (dentro del juego el umbral es algo menor). `inventario_max` es 5 en los paquetes de prueba y 10 por defecto en `Jugador`; **el de las criptas reales no se midió** |
| 5 | `CERRAR_PUERTA` pendiente (puerta con `cierre_automatico = 500`, abierta en el vivo) y 7 `esperar` en el clon hasta el reloj 750 | El evento del clon apunta a la **`Salida` viva**; al ejecutarlo **`Salida.cerrada` del vivo pasó de `False` a `True`** (N = 20 y 200). El evento del vivo sigue pendiente (t = 500, sin cancelar). Leído del código: al llegar a su tiempo, el vivo verá la puerta ya cerrada y no registrará el cierre ni el aviso al conocimiento |
| 6 | `eco = True` | **Se copia**: `clon.eco` es `True` y `clon._mensaje(...)` imprime |
| 7 | `azar` | El `azar` del vivo no cambia con lo que haga el clon; el del clon es otro objeto con el mismo estado al copiar. Las 50 acciones usadas **no consumen azar**, así que la independencia se midió solo con sorteos directos (`clon.azar.random()`) |
| 8 | `_indice_origen is salas` | **Se conserva** en el clon, antes y después de 50 acciones; `_indice_salas` sigue siendo la misma lista; las `Sala` del clon son las del vivo |
| 9 | Oráculo: copiar en la acción 250, el vivo sigue 50 acciones y el clon las rehace | **Con un `GestorDatos` iniciado** (`obtener_detalles` e `iniciar_cripta`): 50/50 iguales y `obtener_estado_resumen()` idéntico en N = 20, 200 y 2 000. **Con `gestor_datos = None`**: 47/50, 46/50 y 44/50 iguales y el resumen difiere (`reloj`, `secuencia`, `jugador`, `acciones`, `conocimiento`) |

**El clon sin gestor no puede jugar** (medido, prueba 2 y 9): entrar en una sala con trampa lanza
`RuntimeError: No hay gestor de datos para consultar la ficha de la trampa.` (`MotorSimulacion.py:122`, `activar_trampas_de_sala`), y
entrar en una sala sin contenido cargado se rechaza con `El contenido de esa sala aún no está disponible.` (11 `mover`
rechazados con N = 200 y 2 000; el vivo tenía cargado el contenido de 32 de 200 salas).

### Controles: qué pasa si el `memo` omite algo (N = 200 y 2 000)

| Se omite del `memo` | Resultado medido (mensaje real) |
|---------------------|---------------------------------|
| `Sala` y `Salida` | `RecursionError: maximum recursion depth exceeded` |
| `restaurador` (partida cargada, archivo abierto) | `TypeError: cannot pickle 'BufferedReader' instances`; con `restaurador → None` en el `memo` la copia termina y `clon.restaurador` queda en `None` |
| `historial` | `retroceder` del clon **devuelve `True` y modifica el vivo** (sala del jugador 98 → 97; cambian también reloj, secuencia, acciones, conocimiento y agenda): las funciones de `deshacer` siguen atadas al motor vivo |
| `gestor_datos` | La copia termina (4 a 19 ms), pero **copia todo el `GestorDatos` y su fuente** (con la fuente offline; con HTTP no se probó). El gestor copiado apunta al clon |

Otra comprobación (N = 20): `clon.conocimiento._destino_de.__self__ is clon` es `True` (el método enlazado se re-liga) y el
`Conocimiento` del clon es otro objeto.

### Riesgos de T015 y T016, con lo medido

| # | Riesgo | Estado | Tarea que lo prueba o decisión |
|---|--------|--------|--------------------------------|
| 1 | Los cierres de `Historial` siguen atados al vivo si el `memo` no lo sustituye | Medido (control) | El `memo` lleva `id(motor.historial) → Historial()`. Prueba: T012 (5) |
| 2 | `restaurador` abierto: `TypeError` si no se sustituye; con `None` el clon no lee las salas pendientes del archivo | Medido | `restaurador → None` en el `memo`; `abrir_copia` en T016. Prueba: T012 (5) |
| 3 | `RecursionError` con un inventario largo (desde 165 nodos) | Medido | T015 y T016 copian el inventario con un bucle, sin recursión, y agregan la prueba con 200 y 400 nodos (T015 en `copiar`, T016 (g) en `materializar`). Falta conocer el `inventario_max` real de las criptas (**no medido**) |
| 4 | El clon con `gestor_datos = None` no puede jugar (trampas, salas sin contenido) | Medido | `materializar` asigna `gestor_historico`. Pruebas T016 (a) y (b); T027 (reconstruir sin red); T029 implementa el gestor |
| 5 | La `Salida` compartida deja que el clon cierre la puerta del vivo | Medido | El `memo` de `materializar` re-liga también `Evento.actor`. Prueba T016 (c) |
| 6 | Una sala no visitada no tiene el atributo `rastro` | Medido | `foto_rastros` con centinela; `materializar` no crea el atributo. Pruebas T016 (f) y T012 (3) |
| 7 | `eco = True` se copia | Medido | `materializar` lo fija en `False`. Prueba T016 (d) |
| 8 | Identidad `_indice_origen is salas` | Medido: se conserva | Sin tarea nueva: `materializar` copia `salas` e `_indice_origen` en la misma llamada de `deepcopy` (T016); lo cubre el oráculo de T012 (1) |
| 9 | `azar` independiente | Medido solo con sorteos directos | T012 (6): una acción que consuma azar, si existe; si no, se deja escrito |
| 10 | Costo de la copia mayor que lo anotado (hasta 2.6× y +43 % para N ≥ 200) | Medido | M3 (T103) se repite con estas cifras como referencia; T098 sigue siendo el plan B. Riesgo para FR-020 en N altas |
| 11 | `GestorDatos.estado_juego` es único: dos clones sobre el mismo `gestor_historico` se pisan | **No medido** (leído del código) | Regla de un solo clon vivo por `gestor_historico`. Prueba T016 (e). **HIPÓTESIS** |
| 12 | Estados con eventos pendientes distintos de `CERRAR_PUERTA` (`REARMAR_TRAMPA`, `VENENO`, `FIN_VELOCIDAD`, `APAGAR_ANTORCHA`) | **No medido** (la agenda del vivo quedó vacía en el escenario general) | El oráculo de T012 incluye estados con esos eventos pendientes. **HIPÓTESIS** |

Consecuencia de 003 para el sello: por el costo de las salidas (`costo_salida`) `reloj` ya no crece linealmente con las acciones;
el sello `(reloj, secuencia)` sigue siendo válido porque se compara por valor.

### No medido (HIPÓTESIS)

Lo siguiente no se pudo medir y queda como **HIPÓTESIS** hasta que lo cubra una tarea:

- la fuente HTTP y `FuenteSinRed` (R10): lo medido usó una fuente offline normal;
- `materializar`, el esqueleto propio y `AgendaConCorte` (no existen todavía);
- dos clones vivos a la vez sobre el mismo `gestor_historico`;
- el `inventario_max` real de las criptas del servicio;
- eventos pendientes distintos de `CERRAR_PUERTA` (`REARMAR_TRAMPA`, `VENENO`, etc.);
- acciones del juego que consuman `azar`.

**Decisión (2026-11-12)**: el profesor respondió: «Para este proyecto sí pueden usar el dict como caché. No hay problema». Queda autorizado `copy.deepcopy` con su `memo`; T098 queda solo como opción de rendimiento. Alcance: se usa solo para el `memo`; el resto de las estructuras de esta capacidad sigue sin `dict` ni `set` como índice mientras no se aclare el alcance por escrito.

---

## Origen de las cifras HIPÓTESIS

Las cifras marcadas **HIPÓTESIS** salen de una **exploración previa local, no versionada**; la reemplazan M1 a M10. Las etiquetas E1 a
E5 solo identifican qué comprobó cada experimento:

| Id | Qué comprobó | La reemplaza |
|----|--------------|--------------|
| E1 | Costo por acción, copia, memoria por punto y que un clon re-simulado coincide con la partida | M5, M2, M7 |
| E2 | `deepcopy` completo frente a esqueleto compartido; `RecursionError` | M3, M9 |
| E3 | Corte de agenda en `t` frente a un motor espía; contaminación del esqueleto compartido | M7, M9 |
| E4 | Esqueleto nuevo por clon: 0 diferencias, presente intacto, tiempos por N | M3, M9 |
| E5 | Tabla de K | M1, M2 |

No forman parte de la suite ni de `--bench` y no están en el repositorio.
