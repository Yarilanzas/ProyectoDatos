# Implementation Plan: Niebla de guerra, mapa conocido y viaje automático «ir a»

**Branch**: `main` (constitución v3.0.2: se trabaja sobre `main`) | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-niebla-mapa-ir-a/spec.md`

## Summary

Lo que el jugador ve y lo que usa «ir a» deja de salir del mapa real y pasa a salir de un objeto `Conocimiento`:
arreglos densos con consulta O(1), y exploración cuyo costo depende de lo revelado, no de lo ya conocido. Cada cambio
se registra como un lote en el `Historial` existente, sin modificarlo. El conocimiento se guarda en un bloque nuevo
del archivo de partida (formato 3). La bitácora pasa a la versión 2, con comentarios y una directiva `@cargar`.

«ir a» es una sucesión de `mover` ordinarios, con la ruta detrás de una interfaz de una sola función. **Si esa búsqueda
se comparte con el cazador sigue pendiente (D-PEND-01)**, y el resto del plan no depende de eso.

El análisis encontró dos defectos existentes que este plan debe corregir para cumplir la spec:

- `--replay` no reproduce partidas cargadas y continuadas: divergió en 20 de 20 semillas probadas.
- Tras cargar, las puertas de las salas no restauradas vuelven a su valor del esqueleto.

## Technical Context

**Language/Version**: Python 3.11 o superior

**Primary Dependencies**: `requests` (única permitida); no se agrega ninguna

**Storage**: archivo binario `CRPT` (versión 2 → 3, disposición definida por Persona D, P-10), bitácora de texto
`CRIPTA-LOG` (versión 1 → 2)

**Testing**: `unittest`, sin red, con paquetes offline temporales

**Target Platform**: consola multiplataforma; el desarrollo es en Windows (cerrar archivos antes de reemplazarlos)

**Project Type**: aplicación de consola MVC

**Performance Goals**: ciclo entre decisiones por debajo de 20 ms (§5.2, `tests/bench_ciclo.py`). Cálculo de un paso
de «ir a» en 5 ms o menos, con el mapa conocido completo de la cripta de referencia (enunciado §6.1; el valor puede
ajustarse por enmienda), verificado por M4. Las complejidades son análisis; todo tiempo es hipótesis hasta medirlo con
`--bench` (M1 a M6).

**Constraints**: estructuras propias (Principio I), determinismo (III), Parte I sin regresiones (SC-006), `Historial`
sin cambios en su contrato

**Scale/Scope**: criptas locales de 5 a 20 salas; el servicio puede traer otras, así que se mide con salas sintéticas
hasta n = 20000

**Sin NEEDS CLARIFICATION técnicos**: las decisiones están en [research.md](research.md). Lo que requiere a otras
personas o al enunciado está en [Preguntas abiertas](#preguntas-abiertas).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / regla | Antes del diseño | Después del diseño | Cómo se cumple |
|---|---|---|---|
| **I. Estructuras propias** | ✅ | ✅ | Listas densas y ordinales. Sin `dict`/`set` como índice, sin `heapq`, `bisect`, `collections`, `networkx`. Ordenar con `elegir_algoritmo`, no con `sorted()`. Cola de prioridad a mano. `sala.salidas` es el `dict` del DTO existente: solo se recorre, no se agrega ningún índice |
| **I. Complejidad documentada** | ✅ | ✅ | Tablas en [data-model.md](data-model.md); se copian a los docstrings |
| **II. MVC** | ❌ **Incumplido hoy** | ✅ con PR-14 | `main.py` crea la vista antes de `--replay` (H4). Fuera de sí mismo, `Modelo/` solo agrega la importación de `DTOS/MapaConocido.py`, porque `mapa_conocido()` devuelve ese DTO; no importa red, archivos, consola ni adaptadores. La vista recibe un DTO. `--bench` no la usa |
| **III. Determinismo** | ❌ **Incumplido hoy** | ✅ con PR-12 | El replay de partidas cargadas diverge (H1). `@cargar` lo corrige. El conocimiento no usa azar ni reloj real, y los órdenes son fijos |
| **IV. Sin datos de cripta** | ✅ | ✅ | `COSTO_MOVER` es la regla de `mover`, no un dato de cripta. Los datos sintéticos están en `tests/` |
| **V. Pruebas** | ⚠️ Entorno | ✅ | Línea base (T001), con `requests` instalado: 128 de 128. Tras las fases 1 a 3: 185 pruebas, OK (`py -m unittest discover -s tests -v`). Cada caso del Apéndice B tiene prueba con su FR ([quickstart](quickstart.md)) |
| **VI. Persistencia versionada** | ✅ | ✅ | `CRPT` 3 y `CRIPTA-LOG` 2, rechazo con código 2, README actualizado |
| **VII. Presupuesto** | ✅ | ⚠️ Verificar | Explorar con antorcha no hace solicitudes. `@cargar` puede repetir solicitudes en un replay con red: PR-12 exige una prueba |
| **VIII. Decisiones medidas** | ✅ | ✅ | M1 a M6 definidas; hasta medirlas, son hipótesis |
| **IX. Spec antes que código** | ✅ | ✅ | Spec confirmada en `c8067f0`, y su corrección de costos y SC-007 en `6ed5b92`, antes del código. FR-024 (P-03) y FR-027f (P-04) se corrigieron en la spec y deben confirmarse en Git antes del código de la Fase 4. Si P-05 cambia requisitos, primero se corrige la spec |
| **X. Trazabilidad** | ✅ | ✅ | [Tabla de requisitos](#requisitos-del-plan) y cobertura de los 31 FR |
| **XI. Registro de prompts** | ✅ | ✅ | `PROMPTS_LLM.md` en la raíz, armado al final a partir de las notas de cada persona: fecha, modelo, prompt textual y para qué se usó (T004) |
| **Contratos compartidos** | — | ⚠️ Avisar | Formatos de archivo y de bitácora, `ejecutar_replay`, `guardar_partida`: avisar al grupo antes de cambiarlos. `Salida` no cambia en esta capacidad |
| **README en el mismo cambio** | — | ✅ | Incluido en PR-16. Está en UTF-16 y se edita avisando al grupo |

**Resultado del gate**: sin violaciones nuevas introducidas por el diseño. Las dos incumplidas por el código actual
(II y III) quedan resueltas dentro del alcance. No queda ningún principio bloqueante. No hace falta llenar la tabla de
excepciones.

## Decisiones

| # | Tema | Resolución | Detalle |
|---|------|------------|---------|
| 1 | Conocimiento | Arreglos densos por ordinal, y listas de lo revelado | [R1](research.md#r1-representación-del-conocimiento-fr-001-a-fr-011) |
| 2 | Historial | Un lote de deltas por operación; `retroceso.py` no cambia | [R2](research.md#r2-registro-de-cambios-en-el-historial-fr-014-fr-031) |
| 3 | Persistencia y replay | Bloque de conocimiento en `CRPT` 3, junto al bloque de línea de tiempo de Persona D en el mismo salto de versión (disposición final de D, P-10); directiva `@cargar` en la bitácora (P-07, aceptada por D con condiciones) | [R3](research.md#r3-persistencia-del-conocimiento-fr-015-y-fr-016), [R4](research.md#r4-replay-de-partidas-cargadas-fr-017) |
| 4 | Comandos | `mapa` e `ir a`, con `Viaje` en el modelo y orquestación en el controlador | [R5](research.md#r5-comandos-nuevos-y-bitácora-fr-018-a-fr-022-fr-030) |
| 5 | Ruta | **PENDIENTE D-PEND-01.** Interfaz `primer_paso` decidida | [R6](research.md#r6-búsqueda-de-la-ruta-de-ir-a-fr-023-fr-024-fr-026) |
| 6 | Costo | Solo lectura por el único acceso `motor.costo_salida` (100 si la salida no trae costo). El campo `costo` de `Salida` y el cambio de `mover` son de la capacidad de terreno y costos | [R7](research.md#r7-costo-de-cada-salida) |

## Requisitos del plan

| ID | Requisito | FR / SC | Archivos |
|----|-----------|---------|----------|
| PR-01 | `Conocimiento`: estados de sala, avistadas, operaciones O(1), complejidades documentadas | FR-001, FR-002, FR-003, FR-004, FR-005 | `Modelo/Conocimiento.py` (nuevo) |
| PR-02 | Memoria de puertas por salida dirigida, observando salidas y entrantes | FR-006, FR-007, FR-008 | `Modelo/Conocimiento.py`, `Modelo/MotorSimulacion.py` |
| PR-03 | Antorcha: explorar vecinas por cualquier salida, sin cargar contenido ni activar nada; puertas sin observar | FR-009, FR-010, FR-011 | `Modelo/Conocimiento.py`, `mover_jugador` |
| PR-04 | Lo mostrado y lo usado por «ir a» salen solo del conocimiento; filtrar el mensaje de cierre; DTO `MapaConocido` | FR-012, FR-013, SC-002 | `DTOS/MapaConocido.py` (nuevo), `Vista/VistaConsola.py`, `ejecutar_evento` |
| PR-05 | Lote de cambios integrado al `Historial`, sin cambiar `retroceso.py` | FR-014, FR-031 | `Modelo/Conocimiento.py` |
| PR-06 | Bloque de conocimiento y `VERSION_FORMATO = 3`; JSON equivalente; rechazo de v2 | FR-015, FR-016, SC-003 | `Persistencia/RegistroConocimiento.py` (nuevo), `ArchivoPartida.py`, `FormatoBinario.py`, `ConversorPartida.py`, `ExportadorJSON.py`, `Gestor/PreparadorPartida.py` |
| PR-07 | Tabla de puertas reales aplicada al cargar (hallazgo H2) | FR-006, FR-015 | `Persistencia/ConversorPartida.py`, `Gestor/PreparadorPartida.py` |
| PR-08 | Comando `mapa`, ayuda y README | FR-018, FR-019, FR-020 | `Controlador/ControladorPartida.py`, `Vista/VistaConsola.py`, `README.md` |
| PR-09 | Comando `ir a`, `Viaje`, recálculo, paradas con motivo, y rechazos sin efectos | FR-021, FR-022, FR-025, FR-026, FR-027, FR-028, FR-029, FR-031, SC-005 | `Modelo/Viaje.py` (nuevo), `Controlador/ControladorPartida.py`, `mover_jugador` |
| PR-10 | Interfaz `primer_paso`, `GrafoConocido` y prueba de contrato. **Implementación bloqueada por D-PEND-01** | FR-011, FR-023, FR-024, FR-029 | `Modelo/rutas_ir_a.py` (nuevo), `Modelo/Conocimiento.py`, `tests/test_ruta_contrato.py` (nuevo) |
| PR-11 | Bitácora v2 con comentarios; `--replay` los ignora | FR-030, SC-004 | `Bitacora/BitacoraPartida.py`, `Controlador/ControladorPartida.py` |
| PR-12 | `@cargar`, recarga en el replay, guardado extraído sin vista; verificar presupuesto (H1) | FR-017, SC-004 | `Bitacora/Reproductor.py`, `Bitacora/BitacoraPartida.py`, `Controlador/ControladorPartida.py`, `main.py` |
| PR-13 | Lectura del costo por el acceso único `motor.costo_salida`, 100 si la salida no lo trae, sin cambiar el movimiento de ningún actor | FR-005, FR-024 | `Modelo/MotorSimulacion.py`, `tests/test_costo_salida.py` |
| PR-14 | `--replay` sin instanciar la vista (Principio II, H4) | FR-017 | `main.py`, `tests/test_integracion.py`, `tests/test_puntajes.py` |
| PR-15 | Medición `--bench` M1 a M6 | Principio VIII | `tests/bench_niebla.py` (nuevo), `main.py` |
| PR-16 | Pruebas por FR, sin regresiones; README y Documento de Decisiones | SC-001, SC-002, SC-003, SC-004, SC-005, SC-006, FR-016, FR-020 | `tests/test_conocimiento.py`, `tests/test_mapa.py`, `tests/test_viaje.py`, `tests/test_persistencia_conocimiento.py`, `README.md` |

**Cobertura**: los 31 FR están asignados a al menos un PR.

## Orden sugerido

```text
PR-13 costo ─┐
PR-01/02/03/05 conocimiento ─┬─ PR-04/08 mapa
             │               ├─ PR-06/07 persistencia ─ PR-11/12/14 bitácora y replay
             └─ PR-10 interfaz ─ PR-09 viaje
PR-15 y PR-16 acompañan a cada bloque
```

Solo el cuerpo de `primer_paso` espera a D-PEND-01. `Viaje` se puede probar antes, inyectando un buscador de prueba.

## Preguntas abiertas

| ID | Pregunta | Quién | Bloquea | Mientras tanto |
|----|----------|-------|---------|----------------|
| **D-PEND-01** | ¿La búsqueda de «ir a» comparte implementación con el cazador? | Grupo, con quien lleva el cazador | Cuerpo de `primer_paso` | **Decisión pendiente.** Opciones en [R6](research.md#r6-búsqueda-de-la-ruta-de-ir-a-fr-023-fr-024-fr-026) |
| **P-02** | ✅ **Resuelta** (enunciado §3.1 y §4.1): el campo se llama `costo`, es un entero mayor o igual que 1, vale 100 si la salida no lo declara y es el mismo en ambos sentidos. Agregar el campo a `Salida` y cobrarlo en `mover` (jugador y enemigos) corresponde a la capacidad de terreno y costos (spec, Assumptions); esta capacidad solo lo lee | — | Nada | Acceso único de solo lectura `motor.costo_salida`, ver [R7](research.md#r7-costo-de-cada-salida) |
| **P-03** | ✅ **Resuelta** (FR-024): ante dos salidas hacia la misma vecina con el mismo costo, gana la primera en el orden N, S, E, O | — | Nada | La prueba de contrato fija ese desempate (T043) |
| **P-04** | ✅ **Resuelta** (FR-027f): si el motor rechaza un paso en pleno viaje, el viaje se detiene e informa el mismo mensaje de rechazo que daría `mover`, sin consumir tiempo adicional | — | Nada | Motivo `PASO_RECHAZADO` (T060) |
| **P-05** | Las salidas son dirigidas y `A→B` cerrada convive con `B→A` abierta. ¿Se confirma que «las dos salas que conecta» observa la salida dirigida `A→B` desde `B`, y que el viaje puede volver por `B→A`? | Grupo | Nada del diseño; confirma la lectura de FR-006 | El plan aplica esa lectura |
| **P-06** | «La trampa X se rearmó.» se muestra aunque sea en una sala desconocida. ¿Debe filtrarse? Queda fuera de la letra de FR-010 y FR-012 | Grupo | Nada | Sin cambio |
| **P-07** | ✅ **Aceptada por Persona D** (línea de tiempo y persistencia, spec 004): `@cargar` hace falso el texto del README «`cargar` no se anota» y se acepta como contrato nuevo, con cuatro condiciones: (a) queda escrito en [contracts/formato-bitacora.md](contracts/formato-bitacora.md); (b) `--replay --hasta t` cuenta el reloj a través de las líneas `@cargar`; (c) una versión incompatible se rechaza con código 2, como hoy; (d) se actualiza el README, porque «`cargar` no se anota» deja de ser cierto (T113) | Persona D | Nada | PR-12 sigue con `@cargar`, cumpliendo las cuatro condiciones |
| **P-10** | Disposición final del `CRPT` 3. **La define Persona D** (spec 004). Propuesta: un bloque de conocimiento (de esta capacidad) y uno de línea de tiempo (de D), ambos dentro del mismo salto a la versión 3. D no guarda el costo de las salidas en el `CRPT`: lo toma del esqueleto | Persona D | T076 (posiciones y `_inicio_salas`) | El bloque de conocimiento de [contracts/formato-partida.md](contracts/formato-partida.md) es una propuesta |
| **P-08** | ✅ **Resuelta** (enunciado §6.1): el cálculo de un paso de «ir a» tiene un límite de 5 ms con el mapa conocido completo de la cripta de referencia. El valor puede ajustarse por enmienda | — | Nada | M4 verifica el límite |
| **P-09** | ✅ **Resuelta** (enunciado §3.4): manda FR-027. El enunciado lista exactamente las condiciones de parada: llegar al destino, entrar a una sala con enemigos, recibir daño, o que deje de existir una ruta conocida. Un enemigo que entra durante un paso sin hacer daño no detiene el viaje | — | Nada | Se aplica FR-027 |

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Se rompen bitácoras y partidas versionadas (`partida.log`, `partida.cripta`) | Es esperado por FR-016 y FR-030. Regenerar las que sean evidencia |
| El cambio toca `Modelo/`, `Persistencia/` y `Bitacora/` | Revisión de otra persona del grupo (Flujo de desarrollo) |
| Hooks en `mover_jugador` rompen pruebas sin `iniciar_partida` | `conocimiento is None` se tolera; la suite debe quedar igual sin editarla, salvo los cambios listados |
| `--bitacora` igual a `<guardado>.log`: no se trunca al cargar | Comportamiento existente; una prueba debe definir el resultado, porque `@cargar` asume que la bitácora termina en el guardado |
| Un `guardar` sin `cargar` carga salas por `_asegurar_salas_con_estado` | No toca azar ni agenda; lo confirma la prueba de replay de SC-004 |
| Replay con red gasta presupuesto en cada `@cargar` | Prueba de PR-12 antes de cerrar el Principio VII |

## Project Structure

### Documentation (this feature)

```text
specs/001-niebla-mapa-ir-a/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── comandos.md
│   ├── formato-partida.md
│   ├── formato-bitacora.md
│   └── interfaz-ruta.md
└── tasks.md             # Lo genera /speckit-tasks
```

### Source Code (repository root)

```text
Modelo/
├── Conocimiento.py          # nuevo: Conocimiento, GrafoConocido
├── Viaje.py                 # nuevo
├── rutas_ir_a.py            # nuevo: frontera de D-PEND-01
├── MotorSimulacion.py       # hooks, costo_salida (solo lectura), mapa_conocido, preparar_viaje
└── retroceso.py             # sin cambios
DTOS/
└── MapaConocido.py          # nuevo (Salida.py no cambia: su campo costo es de la capacidad de terreno y costos)
Persistencia/
├── RegistroConocimiento.py  # nuevo
├── ArchivoPartida.py        # bloque nuevo
├── FormatoBinario.py        # versión 3
├── ConversorPartida.py      # exportar y restaurar
└── ExportadorJSON.py        # mismos datos
Gestor/PreparadorPartida.py  # restaurar al cargar
Bitacora/
├── BitacoraPartida.py       # versión 2
└── Reproductor.py           # recargar
Controlador/ControladorPartida.py  # mapa, ir a, marcar carga
Vista/VistaConsola.py        # mostrar_mapa, ayuda, estado recordado
main.py                      # replay sin vista, bench
tests/                       # pruebas nuevas y bench_niebla.py
```

**Structure Decision**: se conserva la estructura MVC por carpetas del proyecto. No se crean carpetas nuevas.

## Complexity Tracking

No hay excepciones a la constitución que justificar. Si se eligiera la opción B de D-PEND-01, la duplicación del
algoritmo se justificaría en el Documento de Decisiones, no como excepción a la constitución.
