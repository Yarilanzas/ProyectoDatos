# Implementation Plan: Línea de tiempo y su persistencia

**Branch**: `main` (constitución v3.0.2: se trabaja sobre `main`) | **Date**: 2026-11-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-linea-de-tiempo/spec.md` (confirmada en Git en `fc4b613`, con sus clarificaciones).

Etiquetas de dependencia: **[PERSONAS: A]** = capacidad 003 (terreno y cazador), **[PERSONAS: B]** = capacidad 002 (resolubilidad),
**[PERSONAS: C]** = capacidad 001 (niebla, `ir a`), README, constitución y proceso. La persona D es quien escribe este plan. De las otras
capacidades solo se leyó lo que dicen sus specs, contratos y `tasks.md`, y el código público que esta capacidad toca (`Historial`,
`MotorSimulacion`, `ControladorPartida`, persistencia).

## Summary

`historia <t>` y `historia #k` (y `--replay --hasta <t>`) muestran el estado de la partida en un instante pasado sin alterar el
presente. La idea es **guardar poco y rehacer lo que falta**:

- La línea guarda un **guion** de los comandos aceptados, con el sello `(reloj, secuencia)` de cada decisión, y una **copia completa del
  estado cada K acciones** (K = 50 por defecto, **HIPÓTESIS** hasta medir).
- Una consulta busca con **búsqueda binaria propia** el punto de control más cercano, lo copia (con un esqueleto de salas propio, para no
  tocar la partida) y **rehace a lo sumo K acciones** con el propio motor. Para un instante entre dos decisiones corta la agenda del clon
  en `t`, sin modificar el motor.
- Un pergamino de retroceso **recorta** el final de la línea (costo proporcional a lo recortado) y toma un punto de control del estado
  **real**, porque el retroceso no deshace los pergaminos recogidos ni el contenido de salas cargadas.
- Los pergaminos por instante (FR-029) salen de una **serie aparte** que se pliega al recortar.
- **El archivo guarda el guion y K, no los puntos de control**: el `CRPT` 3 lleva un bloque de línea entre el de conocimiento y las salas;
  al cargar, se reproduce el guion con el `Reproductor` y se reconstruyen los puntos, verificando los sellos.
- La reconstrucción **no hace solicitudes**: usa un segundo gestor cuya fuente no puede llegar a la red.

El análisis encontró cinco hechos del código que condicionan el diseño (detalle en
[research.md](research.md#hallazgos-sobre-el-código-actual)):

- `deepcopy` del motor completo falla con `RecursionError` al crecer el mapa (HL2).
- Compartir el esqueleto con un clon contamina la partida real (HL3).
- El `Historial` no sirve para ir hacia atrás: 5 intervalos, cierres sobre objetos vivos, se consume y no se guarda (HL4).
- El `CRPT` actual no es una copia del estado (HL5).
- El retroceso deja efectos irreversibles (HL9).

## Technical Context

**Language/Version**: Python 3.11 o superior

**Primary Dependencies**: `requests` (única permitida); no se agrega ninguna. Biblioteca estándar usada: `copy` (R2), `struct`, `os`,
`shutil` y `tempfile` (solo en `Controlador/` y `Persistencia/`)

**Storage**: archivo binario `CRPT` 3 (bloque de línea nuevo, [contracts/formato-partida.md](contracts/formato-partida.md)). La
bitácora `CRIPTA-LOG` 2 **no cambia** ([contracts/formato-bitacora.md](contracts/formato-bitacora.md))

**Testing**: `unittest`, sin red, con paquetes offline temporales; oráculos: motor espía, `obtener_estado_resumen()` ampliado y copia con
`deepcopy` completo en cripta chica

**Target Platform**: consola multiplataforma; el desarrollo es en Windows (cerrar archivos antes de reemplazarlos o borrarlos)

**Project Type**: aplicación de consola MVC

**Performance Goals**: `historia` en menos de 50 ms con 5 000 acciones (FR-020); ninguna consulta rehace más de K acciones (FR-019);
recorte proporcional a lo recortado (FR-027); ciclo del juego bajo 20 ms (§5.2). Todo tiempo es hipótesis hasta M1 a M10

**Constraints**: estructuras propias (Principio I), determinismo (III), sin solicitudes nuevas al reconstruir (VII), Parte I sin
regresiones, `Historial` y `retroceso.py` sin cambios

**Scale/Scope**: criptas locales de 5 a 20 salas. La consulta crece con `N + E` (materializar el esqueleto): **HIPÓTESIS** (exploración previa local, no versionada; la reemplazan M1 a M10) ~2 ms (N=20), ~8 ms
(N=200), ~69 ms (N=2 000, fuera de la meta de 50 ms; ver [Riesgos](#riesgos)). Partidas de 5 000 acciones como objetivo, 50 000 como prueba
de esfuerzo del recorte

**Sin NEEDS CLARIFICATION técnicos**: las decisiones están en [research.md](research.md). Lo que requiere a otras personas o al
enunciado está en [Preguntas abiertas](#preguntas-abiertas).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / regla | Antes del diseño | Después del diseño | Cómo se cumple |
|---|---|---|---|
| **I. Estructuras propias** | ✅ | ⚠ Revisar | Guion, historia vigente, puntos de control y serie son **listas paralelas**; la búsqueda es `Modelo/BusquedaBinaria.py` propia (sin `bisect`, `sorted`, `sort`, `heapq`, `collections`); los resúmenes se ordenan con `elegir_algoritmo`. Ningún `dict` ni `set` como índice. **Dos usos de la biblioteca estándar que el grupo debe revisar**: `copy.deepcopy` (no sustituye a ninguna estructura evaluada, [R2](research.md#r2-qué-es-una-copia-completa-del-estado-y-cómo-se-obtiene-fr-017-fr-021)) y su argumento `memo`, un `dict` temporal de una sola llamada (ver [Complexity Tracking](#complexity-tracking)) |
| **I. Complejidad documentada** | ✅ | ✅ | Tablas en [data-model.md](data-model.md) y [interfaz-linea.md](contracts/interfaz-linea.md); se copian a los docstrings |
| **II. MVC** | ✅ | ✅ | `Modelo/` no importa red, archivos, consola ni adaptadores: recibe el gestor histórico y la apertura de la copia **inyectados**. El texto del resumen es una función de módulo de `Vista/`, así `--replay --hasta` **no instancia la vista**. El `Controlador` coordina. T096 de la persona C (`--replay` sin vista) ya está en `main` |
| **III. Determinismo** | ✅ | ✅ | La reconstrucción reproduce acciones desde una copia con su `random.Random`; el sello `(reloj, secuencia)` de cada acción **detecta** un motor no determinista y se rechaza con `ErrorReconstruccion`. No se usa reloj real. Depende de que el cazador no consuma azar (003 FR-021). `--replay` sigue reproduciendo todo, incluido lo cargado |
| **IV. Sin datos de cripta** | ✅ | ✅ | Nada de una cripta concreta en el código; los datos de ejemplo están en `tests/` (paquetes offline temporales y criptas sintéticas) |
| **V. Pruebas** | ⚠ Entorno | ✅ | Suite en verde sin red (quickstart, escenarios 1 a 16). Cada prueba cita su FR. Esta fase solo documenta: la línea base de la suite (con `requests`) está en el [quickstart](quickstart.md) |
| **VI. Persistencia versionada** | ✅ | ✅ | `CRPT` 3 (la persona C ya lo subió en T076 con los tres campos de largo; PR-10 solo llena el bloque de la línea y **no sube la versión**, P-10: no se mantienen archivos v3 intermedios), rechazo de cualquier otra versión con `Versión incompatible` y código `2`, README actualizado. La bitácora no cambia de versión. Los códigos de salida no cambian ([comandos-historia.md](contracts/comandos-historia.md)) |
| **VII. Presupuesto** | ✅ | ✅ | Reconstruir y consultar usan un segundo `GestorDatos` con una `FuenteSinRed` que **lanza** ante cualquier llamada: no existe un camino a la red ([R10](research.md#r10-reconstruir-sin-solicitudes-nuevas-principio-vii)). Una sala desalojada de la caché de memoria se lee del disco; si falta, error sin gastar presupuesto. La reproducción del guion al cargar usa el mismo gestor |
| **VIII. Decisiones medidas** | ✅ | ✅ | M1 a M10 definidas ([R15](research.md#r15-plan-de-mediciones---bench)); M10 repite la medición de P1 §4.6 con la carga nueva (enunciado Parte II §5.6). Las cifras del plan vienen de una exploración previa local, no versionada, y están marcadas **HIPÓTESIS** hasta `--bench`: la reemplazan M1 a M10. El K por defecto (50) también |
| **IX. Spec antes que código** | ✅ | ⚠ Pendiente | La spec está en `fc4b613`. Este plan **propone cambios a la spec** ([abajo](#cambios-propuestos-a-la-spec)): deben aceptarse y confirmarse en Git, **en una confirmación aparte**, antes del primer commit de código |
| **X. Trazabilidad** | ✅ | ✅ | [Tabla de requisitos](#requisitos-del-plan): los 30 FR vigentes (FR-001 a FR-031, sin FR-026, que no existe) están asignados a al menos un PR |
| **XI. Registro de prompts** | ✅ | ⚠ Acción | Este `/speckit-plan` es un prompt con texto propio: registrarlo en las notas para `PROMPTS_LLM.md` (fecha, modelo, prompt textual y para qué se usó) |
| **Contratos compartidos** | — | ⚠ Avisar | `CRPT` 3, firma de `guardar_partida`, `Reproductor` (parámetro nuevo) y `main.py`: avisar al grupo antes de cambiarlos ([Enganches](#enganches-y-requisitos-hacia-otras-personas)) |
| **README en el mismo cambio** | — | ✅ | Incluido en PR-15. Está en UTF-16 y se edita avisando al grupo |

**Resultado del gate**: sin violaciones bloqueantes. Quedan **tres acciones** antes del código: (1) que el grupo acepte los cambios a
la spec (IX), (2) que el grupo revise `copy.deepcopy` y su `memo` (I), (3) que la persona C acepte el `observador` del `Reproductor`
y la regla de rechazo de la bitácora igual a `<guardado>.log` ([formato-bitacora.md](contracts/formato-bitacora.md)).

## Decisiones

| # | Tema | Resolución | Detalle |
|---|------|------------|---------|
| 1 | Reconstruir | Re-simular desde el punto de control más cercano; cortar la agenda en `t`. Invertir hacia atrás **no sirve** con este `Historial` | [R1](research.md#r1-cómo-reconstruir-el-estado-de-un-instante-pasado-fr-001-fr-002-fr-019) |
| 2 | Copia del estado | `deepcopy` con `memo` (gestor, restaurador e historial sustituidos) para el estado vivo + esqueleto de salas propio con foto de campos mutables | [R2](research.md#r2-qué-es-una-copia-completa-del-estado-y-cómo-se-obtiene-fr-017-fr-021) |
| 3 | Qué se registra | Guion append-only con sellos `(reloj, secuencia)`; historia vigente en arreglos paralelos | [R3](research.md#r3-qué-se-registra-entre-puntos-de-control-fr-021) |
| 4 | Búsqueda | Binaria propia sobre `vig_reloj` (por tiempo) y `pc_accion` (por acción) | [R4](research.md#r4-ubicar-el-punto-de-control-más-cercano-fr-019-fr-020) |
| 5 | Recorte | `O(V)` más un punto de control del estado **real** tras cada retroceso (necesario por lo irreversible) | [R5](research.md#r5-recorte-al-usar-un-pergamino-y-punto-de-control-posterior-fr-015-fr-016-fr-027) |
| 6 | Pergaminos | Serie `(clave, cantidad)` ordenada, plegada al recortar | [R6](research.md#r6-cantidad-de-pergaminos-por-instante-fr-029) |
| 7 | K | 50 por defecto (**HIPÓTESIS**); se guarda en el archivo; `--checkpoint-cada` con `--cargar` es error de uso; frontera de carga con punto propio | [R7](research.md#r7-k-por-defecto-fr-031-y-convivencia-con---replay-y-cargar-fr-018-fr-030-fr-031) |
| 8 | Persistencia | Orden `[conocimiento][línea][salas][índice]` (el campo de largo de la línea **ya existe** en `main`, con valor 0); la línea guarda **K y el guion**; los puntos se **reconstruyen al cargar** reproduciendo el guion y verificando sellos. Si faltan datos locales al cargar: error, código `1`, sin cargar nada (R10) | [R8](research.md#r8-persistencia-de-la-línea-fr-022-fr-023-fr-024-fr-025-fr-031), [formato-partida.md](contracts/formato-partida.md) |
| 9 | Resumen | DTO + función de texto de módulo, igual para `historia` y `--hasta` | [R9](research.md#r9-un-resumen-único-para-historia-y---replay---hasta-fr-006-fr-007-fr-028) |
| 10 | Sin red | Segundo `GestorDatos` con `FuenteSinRed`; copia privada del archivo cargado | [R10](research.md#r10-reconstruir-sin-solicitudes-nuevas-principio-vii) |
| 11 | CLI | `--hasta` y `--checkpoint-cada` son modificadores; la prioridad de 002 no cambia | [R11](research.md#r11-opciones-de-mainpy-y-la-tabla-de-prioridad-de-la-capacidad-002), [comandos-historia.md](contracts/comandos-historia.md) |
| 12 | Revisión de P1 §4.6 (enunciado Parte II §5.6) | Repetir la medición de P1 §4.6 con la línea registrando (**M10**, tabla antes y después para `DECISIONES.md`); `Historial` sin cambios mientras M10 muestre que la decisión sigue siendo adecuada; riesgo de P1 §4.6 punto 6 ahora detectable. La agenda (P1 §4.1) **no** es de esta capacidad [PERSONAS: grupo] | [R12](research.md#r12-revisión-de-p1-46-historial-de-retroceso-con-la-carga-nueva) |

## Requisitos del plan

| ID | Requisito | FR / SC | Archivos |
|----|-----------|---------|----------|
| PR-01 | Búsqueda binaria propia (`ultimo_menor_o_igual`) con complejidad documentada | FR-019, FR-020 | `Modelo/BusquedaBinaria.py` (nuevo) |
| PR-02 | Copia estructurada del estado, foto del esqueleto y `materializar`; constantes de campos mutables | FR-017, FR-021, FR-008 | `Modelo/CopiaEstado.py`, `Modelo/PuntoControl.py` (nuevos) |
| PR-03 | `LineaTiempo`: guion, historia vigente, puntos de control cada K, sellos y verificación | FR-001, FR-002, FR-016, FR-017, FR-019, FR-021 | `Modelo/LineaTiempo.py` (nuevo) |
| PR-04 | Estado en `t` y en `#k`: re-simulación, `AgendaConCorte`, regla de la decisión en `t` | FR-001, FR-002, FR-003, FR-004, FR-028 | `Modelo/LineaTiempo.py`, `Modelo/AgendaConCorte.py` (nuevo) |
| PR-05 | Recorte por pergamino y punto del estado real; sin puntos huérfanos | FR-014, FR-015, FR-016, FR-027, SC-010 | `Modelo/LineaTiempo.py` |
| PR-06 | Serie de pergaminos por instante | FR-029 | `Modelo/LineaTiempo.py` |
| PR-07 | `ResumenHistorico` (modelo), DTO y texto sin instanciar la vista | FR-006, FR-007 | `Modelo/ResumenHistorico.py`, `DTOS/ResumenHistorico.py`, `Vista/TextoResumen.py` (nuevos) |
| PR-08 | Comando `historia`, rechazos, ayuda | FR-003, FR-004, FR-005, FR-008, FR-009, FR-010 | `Controlador/ControladorPartida.py`, `Vista/VistaConsola.py` |
| PR-09 | Gestor histórico sin red y copias privadas del archivo cargado | FR-025, Principio VII | `Gestor/GestorHistorico.py` (nuevo), `Controlador/ReconstructorLinea.py` (nuevo) |
| PR-10 | `RegistroLinea` y **llenar** el bloque del `CRPT` 3: el campo `[largo línea]` ya existe (T076, valor 0); falta el parámetro `linea` de `guardar_partida`, guardar `_inicio_linea`/`_largo_linea` en `LectorPartida` y `leer_linea`; `_inicio_salas` y `_validar_encabezado` ya cumplen la fórmula, sin subir la versión | FR-022, FR-023, FR-024, FR-031 | `Persistencia/RegistroLinea.py` (nuevo), `ArchivoPartida.py` [PERSONAS: C], `ExportadorJSON.py`; `FormatoBinario.py` sin cambios |
| PR-11 | Reconstrucción al cargar: reproducir el guion, verificar sellos y jugador, abrir época; si faltan datos locales, error con código `1` sin cargar nada | FR-022, FR-025, FR-030, FR-031 | `Controlador/ReconstructorLinea.py`, `Controlador/ControladorPartida.py` |
| PR-12 | Observador del `Reproductor` y `--replay --hasta` (y estado final con aviso) | FR-011, FR-012, FR-013, FR-025, FR-030 | `Bitacora/Reproductor.py` [PERSONAS: C], `Controlador/ObservadorLinea.py`, `Controlador/ConsultaHistoria.py` (nuevos), `main.py` |
| PR-13 | Opciones `--hasta` y `--checkpoint-cada`, validación y combinaciones | FR-013, FR-018, FR-031, FR-010 | `main.py`, `tests/test_cli_historia.py` (nuevo) |
| PR-14 | Medición M1 a M10, K por defecto, README y Documento de Decisiones. **M10** repite la medición de P1 §4.6 (`bench_retroceso` de `tests/bench_personaC.py`) con la línea registrando, con tabla antes y después para `DECISIONES.md` (Parte II §5.6 y §6.3). La agenda (P1 §4.1) la repite otra capacidad [PERSONAS: grupo] | FR-018, FR-020, FR-021, SC-002, SC-006, SC-007, SC-010 | `tests/bench_linea.py` (nuevo), `main.py` [PERSONAS: B, C] |
| PR-15 | Pruebas por FR, sin regresiones; README | SC-001, SC-003, SC-004, SC-005, SC-008, SC-009, FR-010, FR-023 | `tests/test_linea_*.py`, `tests/utiles_linea.py`, `README.md` |

**Cobertura**: los 30 FR vigentes están asignados a al menos un PR. FR-009 (rechazos) y FR-010 (ayuda y README) en PR-08, PR-13 y PR-15.

## Orden sugerido

```text
Contratos (formato-partida.md, formato-bitacora.md) ──► persona C: aceptar el observador y el rechazo de la bitácora = <guardado>.log
PR-01 búsqueda ─┐
PR-02 copia ────┼─ PR-03/04/05/06 línea ─┬─ PR-07/08 resumen y comando `historia`
                │                        └─ PR-14 medición M1 a M10 (K por defecto) ──► fija K
PR-09 gestor sin red ┘
PR-10 llenar el bloque del archivo ─ PR-11 reconstrucción al cargar ─ PR-12 `--replay --hasta` ─ PR-13 opciones
PR-15 acompaña a cada bloque
```

Todo lo que la línea necesita de la capacidad 001 **ya está en `main`**: T076 (`CRPT` 3 con los tres campos de largo), T084, T092,
T093 (`Reproductor(..., recargar=None)`), T094, T096 y T119. Quedan pendientes solo T113 (README) y T117 (revisión por la persona D),
que no bloquean el código de esta capacidad. PR-01 a PR-12 se prueban hoy contra el código real, sin sustitutos de esas piezas; lo que
falta no es de 001 sino de esta capacidad: el parámetro `linea` de `guardar_partida` y `guardar_motor`, `leer_linea()`, el `observador`
y una entrada de `Reproductor` que reproduzca una lista de acciones en memoria (hoy `reproducir(ruta)` solo lee una bitácora de disco).
PR-14 (M10) no depende de la persona C ni de la A: usa `Historial` y `LineaTiempo`.

## Preguntas abiertas

| ID | Pregunta | Quién | Bloquea | Mientras tanto |
|----|----------|-------|---------|----------------|
| ~~P-D01~~ **Cerrada** | Enunciado Parte II (texto citado por la persona D; no está en el repo). §5.6: «Repitan las mediciones de la primera parte con la carga nueva. Si alguna decisión deja de ser adecuada, cámbienla y documenten el antes y el después; si sigue siendo adecuada, muéstrenlo con datos» (agenda P1 §4.1 e historial de retroceso P1 §4.6). §6.3: `--bench` debe incluir «las mediciones de la primera parte repetidas con la carga nueva (§5.6)» | — | — | Resuelta: se agrega **M10** (P1 §4.6 con la línea registrando, tabla antes y después para `DECISIONES.md`); la agenda (§4.1) **no** es de esta capacidad [PERSONAS: grupo] ([R12](research.md#r12-revisión-de-p1-46-historial-de-retroceso-con-la-carga-nueva)) |
| **P-D02** | `Reproductor(fabrica_motor, version_cripta, version_catalogo, recargar=None)` necesita un `observador` opcional y una entrada que reproduzca acciones en memoria. Al llegar a `@cargar` llama a `recargar(motor)`, que **recibe el motor actual y devuelve el nuevo**; el observador se ajusta a esa firma ([Enganches](#enganches-y-requisitos-hacia-otras-personas)). ¿La persona C lo acepta? | C | PR-12 | Sin él habría que envolver el motor para observarlo, y un `deepcopy` copiaría por referencia un cierre ligado al motor vivo: no se hace |
| ~~P-D03~~ **Cerrada** | T076 ya escribe los tres campos de largo (con el de la línea en `0`) y T119 está implementado en `main`. Esta capacidad **no usa T119 y no debe retirarse**: se conserva por sus propios méritos | C | — | PR-10 solo llena el bloque y agrega la prueba de offsets con línea no vacía [PERSONAS: C] |
| **P-D04** | La persona A mantiene todo su estado colgando del motor, sin cachés de módulo (`ciclo`, `version_puertas`, `GrafoCripta`, `EspacioBusqueda` y `CampoDistancias` cuelgan del motor), declara campos mutables nuevos de `Sala`/`Salida`, y **excluye `Modelo/CopiaEstado.py` por nombre** de la prueba de T015 (choque descrito en [interfaz-linea.md](contracts/interfaz-linea.md#choque-con-t015-de-a-persona-a-003)) | A | Corrección de las consultas con cazadores; T015 | La prueba de oráculo del escenario 14 lo detecta |
| **P-D10** | Si faltan datos locales al **cargar** (paquete o carpeta de datos locales borrados), el guion no se puede reproducir: error y código `1`, sin cargar nada (alternativas en [R10](research.md#r10-reconstruir-sin-solicitudes-nuevas-principio-vii)) | Grupo | PR-11 | Se implementa la opción recomendada |
| **P-D11** | Rechazar en el origen `--bitacora` igual a `<guardado>.log` ([formato-bitacora.md](contracts/formato-bitacora.md#bitácora-igual-a-guardadolog)) [PERSONAS: C] | C | PR-11, PR-12 | Sin el rechazo, la regla 2 de `formato-bitacora.md` tiene una excepción y FR-025 y FR-030 no valen en ese caso |
| **P-D05** | ¿El grupo acepta los [cambios propuestos a la spec](#cambios-propuestos-a-la-spec)? | Grupo | Código (Principio IX) | Se implementa lo que no depende de ellos |
| **P-D06** | ¿Es aceptable el límite de escala (consulta ~69 ms con 2 000 salas)? Las criptas locales tienen 5 a 20 | Grupo | Nada hoy | M3 mide; el plan B es una copia que no recorre salas sin cambios |
| **P-D07** | `main.py` lo tocan B (`--verificar`, `--forzar`), C (`--replay` sin vista, bench) y D (`--hasta`, `--checkpoint-cada`, bench): ¿en qué orden y con qué dueño del merge? | B, C, D | PR-13 | Contratos primero; cambios mínimos y por separado |
| **P-D08** | K por defecto = 50 es **HIPÓTESIS** | D con el grupo | Documentar el valor | M1 y M2 lo confirman o lo cambian |
| **P-D09** | Tras terminar la partida no hay `historia` interactiva (spec: Assumptions); solo `--replay --hasta` | — | Nada | Sin cambio |

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Un campo nuevo de otra persona queda fuera de la copia (campo mutable de `Sala`/`Salida`, o estado global) | La prueba de oráculo (copia frente a `deepcopy` completo y frente al motor vivo tras un retroceso) y el sello `(reloj, secuencia)` lo detectan; requisitos en [interfaz-linea.md](contracts/interfaz-linea.md) |
| `deepcopy` es lento o recursivo con mapas grandes | Esqueleto fuera del `deepcopy` (medido). Plan B: copia a mano por campos del estado vivo, decidido con M3 |
| Consulta de ~69 ms con 2 000 salas (> 50 ms) | Fuera de la escala de los datos (5 a 20 salas). Mejora diferida: materializar solo las salas que cambiaron |
| Cargar una partida larga tarda (se reproduce el guion): ~0.1 ms por acción medido (**HIPÓTESIS**) | M6; aviso si hay muchas acciones |
| Un cambio de comportamiento del motor invalida los guiones guardados | El sello lo detecta y se rechaza con `Versión incompatible` en vez de mostrar una historia falsa |
| Copia privada del archivo cargado (archivos temporales) | Una por carga, en una carpeta temporal propia; cerrar los manejadores antes de borrar (Windows); `cerrar()` en el `finally` de `jugar()` |
| Se rompen `partida.cripta`, `partida.cripta.log` y las bitácoras versionadas | Esperado por FR-024. Regenerar las que sirvan de evidencia |
| Varios cambios simultáneos en `main.py`, `ControladorPartida.py`, `ArchivoPartida.py` y el README (B, C y D) | P-D07; contratos primero; confirmaciones separadas por capacidad |
| La spec exige «no más de uno cada K» y el diseño agrega puntos tras retrocesos y cargas | Cambio propuesto a FR-017 y SC-006; sin el punto extra la reconstrucción no sería exacta (R5) |
| **Interpretación del enunciado**: el riesgo principal es el cambio 3, que se aparta de la letra de «no más de una cada K» (§3.6); los cambios 1 y 2 están respaldados por el propio enunciado (§3.6 permite re-simular y no exige guardar puntos de control) | Los tres cambios se documentarán en `DECISIONES.md` con el enunciado citado, la alternativa descartada y las mediciones que respaldan la decisión (M1, M2, M4 y M6) |
| Cargar sin datos locales: reproducir el guion al cargar usa el gestor sin red, y la carpeta de datos locales (o el paquete) puede faltar | Error con código `1` y nada cargado ([R10](research.md#r10-reconstruir-sin-solicitudes-nuevas-principio-vii)); el jugador sigue con la partida que tenía |
| `--bitacora` igual a `<guardado>.log`: la bitácora conserva acciones posteriores al guardado y el replay no coincide con la línea | Se rechaza en el origen como error de uso (código `1`) [PERSONAS: C] ([formato-bitacora.md](contracts/formato-bitacora.md#bitácora-igual-a-guardadolog)) |
| `Modelo/CopiaEstado.py` restaura `Salida.cerrada` y choca con la prueba de T015 de 003 | La persona A la excluye por nombre con el motivo escrito [PERSONAS: A] ([interfaz-linea.md](contracts/interfaz-linea.md#choque-con-t015-de-a-persona-a-003)) |

## Cambios propuestos a la spec

La spec **no se modifica** en esta fase. Por el Principio IX, si el grupo los acepta se corrige primero la spec y luego el código, en
confirmaciones separadas.

La columna «Texto del enunciado» recoge, para los cambios 1, 2 y 3, las **citas literales** del enunciado de la Parte II (§3.6 y §5.5).
Frases como «todos los cambios», «puntos de control vigentes» y «modificación atómica» son de nuestra spec, no del enunciado. Los
cambios 1 y 2 están respaldados por el propio enunciado; el cambio 3 es el único que se aparta de su letra. Los demás cambios no tocan
una exigencia del enunciado.

| # | Dónde | Hoy | Texto del enunciado | Propuesta | Motivo |
|---|-------|-----|---------------------|-----------|--------|
| 1 | Key Entities «Cambio», FR-021, FR-022, SC-006 | «Cambio»: modificación atómica del estado; la línea guarda «todos los cambios» | §3.6: «Fuera de los puntos de control, solo se almacena la información necesaria para reconstruir los cambios. Pueden reconstruir hacia adelante desde un punto de control, re-simulando, o hacia atrás desde el estado actual, invirtiendo cambios. Si re-simulan, el punto de control debe incluir el estado del generador random.Random.» §5.5: «La memoria total debe crecer con la cantidad de cambios ocurridos, más un punto de control cada K acciones; nunca con "acciones por tamaño del estado".» El enunciado permite re-simular, así que guardar las acciones es la «información necesaria para reconstruir los cambios» | Cambiar «Cambio» por **«acción registrada»**: lo que se guarda entre puntos de control es el comando aceptado con su sello, no una diferencia de estado. FR-021: «fuera de los puntos de control, MUST almacenarse solo la información necesaria para reconstruir las acciones» | El motor no emite cambios aplicables y el `Historial` no sirve para ir hacia atrás (R1, HL4). Lo que dice FR-021 sigue cumpliéndose: la memoria crece con las acciones más un punto cada K |
| 2 | FR-022, US5.1, Edge «Consulta tras cargar», SC-005 | «conservar la línea completa (todos los cambios y los **puntos de control vigentes**)» | §3.6: «Guardar y cargar la partida conserva la línea de tiempo completa. El formato binario cambia; un archivo de la primera parte debe detectarse como incompatible (P1 §4.10) o migrarse de forma explícita.» El enunciado no exige guardar los puntos de control; «puntos de control vigentes» es redacción de nuestra FR-022 | «conservar el **guion** de la línea y K; cargarla MUST **reconstruir** los puntos de control». Agregar que el guion incluye los retrocesos y las cargas | Guardar puntos completos exige un segundo serializador de todo el estado, y el `CRPT` actual no es una copia (HL5). Reconstruir reusa el motor (R8) |
| 3 | FR-017, US6.2, SC-006 | «no más de una copia completa cada K acciones»; «como máximo ⌈acciones/K⌉ + 1» | §3.6: «Se permite guardar copias completas del estado, llamadas puntos de control, pero no más de una cada K acciones del jugador.» y «Una consulta no puede requerir aplicar o deshacer cambios de más de K acciones del jugador.» Este es el único cambio que se aparta de la letra del enunciado | Agregar **«salvo el punto de control posterior a un retroceso y el de una carga»**: «como máximo ⌈acciones/K⌉ + 1 + cargas + usos del pergamino» | Sin esos puntos la reconstrucción de lo posterior a un retroceso no es exacta (R5, HL9) |
| 4 | FR-001 | «…si a t le corresponde una decisión del jugador, MUST ser el estado justo antes de tomarla» | — | Aclarar: **un evento con tiempo `t` y secuencia posterior a la decisión no se refleja** | Es lo que ocurrió en la partida real (R1) |
| 5 | US2.5 (y US2.1) | «un pergamino que revirtió las últimas 5 (quedan 5)» | — | «cinco pergaminos seguidos que revirtieron las últimas 5». **Un pergamino revierte una acción** | README línea 170, P1 §4.6 y `Historial.deshacer_ultimo` (HL4). US2.1 y US2.6 ya lo suponen |
| 6 | FR-006 | «reloj» | — | «el **reloj consultado** `t` (o el de la decisión, para `#k`)» | El motor se detiene en el último evento ≤ t, que puede ser menor (R9) |
| 7 | FR-029 | cantidad de pergaminos en el instante consultado | — | Agregar: **en la posición a la que se retrocedió rige la última ocurrencia (el presente)**; antes de ella, lo que el jugador tenía entonces | La posición ocurrió dos veces en el tiempo real (R6) |
| 8 | Edge «`--checkpoint-cada` junto con `--replay`… rige el K del archivo cargado» | rige el K del archivo cargado | — | «en `--replay`, K es el de la ejecución, también tras `@cargar`; no cambia ningún resumen (FR-028)» | El archivo que cargaría el replay es el temporal que el propio replay guardó (R7) |
| 9 | FR-011 | «reproducir la partida hasta t» | — | «reproducir la bitácora completa e imprimir el estado en `t` de la historia vigente» | Un retroceso posterior a `t` cambia la historia (FR-012 ya define «final» así) |
| 10 | Cabecera | «Feature Branch: `main` (… constitución v3.0.1)» | — | v3.0.2 | Desactualizado |

## Enganches y requisitos hacia otras personas

Ningún archivo de otra persona se modifica en esta fase. Estos son los cambios mínimos que la capacidad necesitará, con el cambio exacto.

| Etiqueta | Archivo | Cambio exacto | Por qué |
|----------|---------|---------------|---------|
| **[PERSONAS: C]** | `Bitacora/Reproductor.py` (T093, ya en `main`) | Hoy: `Reproductor(fabrica_motor, version_cripta, version_catalogo, recargar=None)`; al llegar a `@cargar` llama a `recargar(motor)`, que **recibe el motor actual y devuelve el nuevo** (`None` es error). Cambio: agregar `observador=None` al final. Tras crear el motor, `if self._observador: self._observador.al_crear_motor(motor)`; tras cada `ejecutar_accion` que no devolvió `False`, `.despues_de_accion(motor, nombre, argumento)`; tras `motor = self._recargar(motor)`, `.despues_de_carga(motor)` (recibe el motor **nuevo**; el anterior ya lo cerró `recargar`). Agregar además una entrada que reproduzca una lista `(encabezado, acciones)` en memoria (`reproducir` se reduce a leer la bitácora y llamarla), para reconstruir el guion al cargar. Sin observador, igual que hoy | La línea observa el replay por el mismo camino que la partida jugada (FR-025). Evita duplicar el bucle de reproducción |
| **[PERSONAS: C]** | `Persistencia/ArchivoPartida.py` | **El campo ya existe** (T076): `guardar_partida` escribe `[largo línea]` con valor `0` y `LectorPartida._leer_largos` lo lee y salta el bloque; `_inicio_salas` y `INICIO_MINIMO_SALAS = TAMANO_ENCABEZADO + 12` ya cumplen la fórmula. PR-10 solo llena el bloque: parámetro `linea=None` en `guardar_partida` (objeto con `to_bytes()`), guardar `_inicio_linea` y `_largo_linea` en el lector (hoy son locales de `_leer_largos`) y `leer_linea()`. **No sube `VERSION_FORMATO`**. Agregar pruebas con la línea no vacía: `_inicio_salas = TAMANO_ENCABEZADO + (4 + largo_jugador) + (4 + largo_conocimiento) + (4 + largo_línea)`, `offset_indice < TAMANO_ENCABEZADO + 12` rechazado, bloque de línea que invade las salas rechazado | Una sola disposición ([formato-partida.md](contracts/formato-partida.md)). Los archivos v3 con largo `0` ya escritos siguen siendo válidos (sin línea) |
| **[PERSONAS: C]** | `Controlador/ControladorPartida.py` (T092, T094) | T092 y T094 ya están hechas: `guardar_motor(motor, ruta, gestor)` existe; agregar `linea=None`. En `_accion`: `despues_de_accion(...)` tras `bitacora.registrar`; `nueva_partida` y `cargar` crean y reconstruyen la línea; comando `historia`; `guardar` pasa `linea=...`; `_cerrar` cierra la línea. Rechazar en el origen `--bitacora` igual a `<guardado>.log` (ver el enganche siguiente) | Punto único de registro (HL8) |
| **[PERSONAS: C]** | `Controlador/ControladorPartida.py`, `main.py` (rechazo de la bitácora) | Al **guardar** y al **cargar** con `--bitacora` igual a `ruta_bitacora_de(ruta)` (`<guardado>.log`, comparado con `_misma_ruta`): error de uso con código `1`, sin guardar ni cargar. Hoy `guardar` y `_continuar_bitacora` ya contemplan esa igualdad con `_misma_ruta` y **no copian** el archivo sobre sí mismo | Regla 2 de [formato-bitacora.md](contracts/formato-bitacora.md): lo jugado entre el guardado y la carga no existe en la línea. Sin el rechazo hay una excepción que rompe FR-025 y FR-030 |
| **[PERSONAS: C]** | `main.py` (T096, ya en `main`: `ejecutar_replay(ruta, gestor)` sin vista; la recarga vive en `main.ejecutar_replay`) | `--hasta`, `--checkpoint-cada` como texto con validación a mano; rama `--replay --hasta` (pasa el observador a `Reproductor`; la recarga de `ejecutar_replay` debe avisar al observador por `despues_de_carga`); enganche de `bench_linea` en `--bench` | CLI de esta capacidad |
| **[PERSONAS: C]** | `Vista/VistaConsola.py` | método `mostrar_resumen_historico(dto)` que llama a `Vista/TextoResumen.py`; dos líneas nuevas en `AYUDA` | FR-010 |
| **[PERSONAS: C]** | `Persistencia/ExportadorJSON.py` | clave `linea` con los mismos datos que el binario | Comparación binario frente a JSON |
| **[PERSONAS: C]** | `README.md` (UTF-16) | opciones, comando `historia`, `CRPT` 3 con la línea, nota sobre `retroceder` frente a `historia`, K por defecto con la medición | Principio VI y FR-010, FR-023 |
| **[PERSONAS: C]** | T119 (copiar y serializar `Conocimiento`, lotes `aplicar`/`invertir`) | **Ya está implementado en `main`.** Esta capacidad **no lo usa y no debe retirarse**: `deepcopy` copia `Conocimiento` (arreglos de enteros y referencias al motor y al esqueleto, que se re-ligan; exploración previa local, **HIPÓTESIS** que M9 reemplaza: el método ligado `_destino_de` queda en el clon). De 001 solo se usa `motor.mapa_conocido()` y que `Conocimiento` guarde referencias solo al motor y al esqueleto. Conviene que `Conocimiento.copiar()` no se use para el clon (comparte `_destino_de`, `_salas` y `_salidas` con el original) | Evita trabajo innecesario y aclara que nada se retira |
| **[PERSONAS: C]** | P-07 (b) | Cumplida por [formato-bitacora.md](contracts/formato-bitacora.md), reglas 1 a 5 | Condición de la persona D |
| **[PERSONAS: A]** | Código de 003 | **Sin cambios al `Historial`.** Requisitos: estado colgando del motor, sin cachés de módulo; campos mutables nuevos de `Sala`/`Salida` en `CAMPOS_MUTABLES_*`; el cazador no consume azar (ya está en 003 FR-021) | [interfaz-linea.md](contracts/interfaz-linea.md), tabla «Qué le pide la línea» |
| **[PERSONAS: A]** | `tests/test_invalidacion_puertas.py` (T015) | La prueba falla si aparece `.cerrada =` o `setattr(..., "cerrada", ...)` en `Modelo/` fuera del método único; `Modelo/CopiaEstado.py` (de esta capacidad) restaura `Salida.cerrada` desde la foto del esqueleto. **Excluir `Modelo/CopiaEstado.py` por nombre, con el motivo escrito** (como ya se excluye `Modelo/prueba_actores.py`): escribe `cerrada` sobre una **copia** del esqueleto, nunca sobre el del motor vivo, y no incrementa `version_puertas` porque el clon no tiene un ciclo en marcha | Sin la exclusión, T015 falla en cuanto exista `CopiaEstado.py` |
| **[PERSONAS: A]** | T058 y T059 (`tests/test_cazador_equivalencia.py`) | Qué llamar y con qué motor: [interfaz-linea.md, «Lo que la línea ofrece a A»](contracts/interfaz-linea.md#lo-que-la-línea-ofrece-a-a) | Desbloquea T058 (parcial) y T059 cuando la línea exista |
| **[PERSONAS: B]** | `contracts/cli-verificacion.md` | Solo documentación: una nota de que `--hasta` y `--checkpoint-cada` son modificadores y no cambian la tabla de prioridad; ver [comandos-historia.md](contracts/comandos-historia.md) | Una sola fuente de la tabla |

## Project Structure

### Documentation (this feature)

```text
specs/004-linea-de-tiempo/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── formato-partida.md
│   ├── formato-bitacora.md
│   ├── comandos-historia.md
│   └── interfaz-linea.md
└── tasks.md              # Lo genera /speckit-tasks
```

### Source Code (repository root)

```text
Modelo/
├── LineaTiempo.py          # nuevo: guion, historia vigente, puntos, serie de pergaminos, consultas
├── PuntoControl.py         # nuevo
├── CopiaEstado.py          # nuevo: copiar, materializar, CAMPOS_MUTABLES_*
├── BusquedaBinaria.py      # nuevo: búsqueda propia
├── AgendaConCorte.py       # nuevo
├── ResumenHistorico.py     # nuevo
└── retroceso.py            # sin cambios
DTOS/
└── ResumenHistorico.py     # nuevo
Gestor/
└── GestorHistorico.py      # nuevo: GestorDatos sin red + FuenteSinRed
Persistencia/
├── RegistroLinea.py        # nuevo
├── ArchivoPartida.py       # llenar el bloque de línea, que ya existe con largo 0 (T076 de C) [PERSONAS: C]
├── FormatoBinario.py       # sin cambios (versión 3 ya vigente)
└── ExportadorJSON.py       # clave linea
Controlador/
├── ControladorPartida.py   # enganche en _accion, historia, guardar, cargar
├── ObservadorLinea.py      # nuevo: adaptador de los tres avisos
├── ReconstructorLinea.py   # nuevo: reproduce el guion, verifica sellos, copias privadas
└── ConsultaHistoria.py     # nuevo: --replay --hasta
Bitacora/Reproductor.py     # parámetro observador [PERSONAS: C]
Vista/
├── TextoResumen.py         # nuevo: función de módulo
└── VistaConsola.py         # mostrar_resumen_historico, AYUDA
main.py                     # --hasta, --checkpoint-cada, bench
tests/                      # test_linea_*.py, test_cli_historia.py, utiles_linea.py, bench_linea.py
```

**Structure Decision**: se conserva la estructura MVC por carpetas del proyecto; las carpetas son las existentes. La lógica va en `Modelo/`
(sin entradas ni salidas), el pegamento con archivos, gestor y replay en `Controlador/` y `Gestor/`, y el texto en `Vista/`.

## Complexity Tracking

No hay excepciones a la constitución, pero hay **tres usos que el grupo debe aprobar** (Principio I) y dos costos de diseño:

| Elemento | Por qué hace falta | Alternativa más simple descartada porque |
|----------|--------------------|------------------------------------------|
| `copy.deepcopy` para el estado vivo | No sustituye a ninguna estructura evaluada; copia agenda, inventario, azar y conocimiento sin listar campos | Copiar a mano cada campo del motor: un campo olvidado por A, B o C da un estado falso en silencio. Queda como plan B si M3 lo exige |
| `memo` de `deepcopy`: un `dict` temporal con los pares objeto → sustituto | Es el argumento documentado de `copy` para no copiar ciertos objetos y para re-ligar el esqueleto | Sin él habría que escribir un copiador de grafos propio, con la misma tabla de identidades. No persiste ni indexa datos del juego (uso auxiliar, Principio I) |
| Segundo `GestorDatos` (`GestorHistorico`) | Garantía estructural de que reconstruir no hace solicitudes (Principio VII) | Reusar el gestor vivo: altera contadores y caché y depende de que el disco nunca falle |
| Copia privada del archivo cargado (archivo temporal por carga) | Restaurar salas pendientes tal como estaban al cargar, aunque un guardado posterior sobrescriba el original | Guardar los registros de sala en memoria: exige envolver `motor.restaurador`, que `guardar` reasigna |
| Puntos de control extra tras retroceso y carga | Reconstrucción exacta (R5) | Reemplazar el previo: rompe FR-019 |
