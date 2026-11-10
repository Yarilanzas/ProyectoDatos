# Implementation Plan: Terreno, cazador e invalidación de rutas

**Branch**: `main` (constitución v3.0.2: se trabaja sobre `main`) | **Date**: 2026-11-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-terreno-cazador/spec.md`

Este plan es el borrador de la sección de esta capacidad en el Documento de Decisiones (§7.1). Cada decisión trae
alternativas, elección, complejidad esperada, evidencia a medir y límites; el detalle está en [research.md](research.md)
y las estructuras en [data-model.md](data-model.md).

## Summary

Moverse por una salida pasa a costar el costo de esa salida, para todos los actores, desde un único punto de
reprogramación en el motor. Atacar, esperar y la primera acción tras activarse siguen con sus costos (R7).

El cazador decide con la búsqueda compartida con «ir a» (D-PEND-01, opción A: `Modelo/BusquedaRuta.py` y
`Modelo/ColaPrioridad.py`, de Persona A), sobre un grafo de la cripta completa con el estado actual de las puertas.
Hay dos formas de calcular la misma decisión:

- **Referencia desde cero**: búsqueda adelante acotada por el rango, por cazador y por turno (`primer_paso` con
  `limite`). Es el oráculo de las pruebas de equivalencia y la alternativa «recalcular siempre» del bench.
- **Estrategia del juego (hipótesis por medir)**: un campo de distancias hacia el jugador, calculado una vez sobre el
  grafo transpuesto (salidas entrantes, con el costo y la puerta de cada salida original) y compartido por todos los
  cazadores mientras no cambien la sala del jugador ni las puertas, y como máximo durante un ciclo.

Los arreglos son densos por ordinal con marca de época, así que una decisión no toca nada de tamaño n (FR-033). La
reutilización se controla con contadores que solo crecen (`version_puertas`, `ciclo`), y se demuestra y prueba que no
cambia ninguna decisión (FR-016).

## Technical Context

**Language/Version**: Python 3.11 o superior

**Primary Dependencies**: `requests` (única permitida); no se agrega ninguna

**Storage**: sin formatos nuevos en esta capacidad. El costo en la caché y en el paquete offline, con su versión de
formato, lo implementa la capacidad de datos (FR-008); aquí solo se verifica que se conserve. Los contadores y el campo
de distancias no se guardan

**Testing**: `unittest`, sin red, con paquetes offline temporales y criptas sintéticas en `tests/`

**Target Platform**: consola multiplataforma; desarrollo en Windows

**Project Type**: aplicación de consola MVC; los cambios están en `Modelo/` y en `tests/`

**Performance Goals**: ciclo entre dos decisiones del jugador < 20 ms con 50 cazadores activos en la cripta de
referencia, con puertas estables e inestables (FR-030, FR-031); tiempo de decisión con la cripta más grande medida
≤ 1,5 × el de la más pequeña, mismo rango (FR-033). Son metas; todo tiempo es hipótesis hasta medirlo (M1 a M8)

**Constraints**: estructuras propias (Principio I), determinismo sin azar en el cazador (III, FR-021), Parte I sin
regresiones en la forma de decidir (SC-006), contrato `primer_paso` compartido con 001

**Scale/Scope**: criptas locales de 5 a 20 salas; se mide con criptas sintéticas de 10² a 10⁵ salas y k de 1 a 50
cazadores

**Sin NEEDS CLARIFICATION técnicos**: resueltos en [research.md](research.md). Lo que depende de otras personas está
en [Preguntas abiertas](#preguntas-abiertas).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / regla | Antes del diseño | Después del diseño | Cómo se cumple |
|---|---|---|---|
| **I. Estructuras propias** | ✅ | ✅ | Montículo propio en `ColaPrioridad.py`; listas densas por ordinal con marca de época en un espacio de trabajo propio; ordinales y listas de entrantes propios de `GrafoCripta`, sin depender de `Conocimiento`. Sin `dict`/`set` como índice ni caché, sin `heapq`, `bisect`, `collections`, `networkx` ni `sorted()`/`list.sort()` en ordenamientos evaluados. El campo compartido es una caché propia en listas |
| **I. Complejidad documentada** | ✅ | ✅ | Tablas en [data-model.md](data-model.md); se copian a los docstrings |
| **II. MVC** | ✅ | ✅ | Todo en `Modelo/`; no importa red, archivos ni consola. El bench no instancia la vista |
| **III. Determinismo y reloj virtual** | ✅ | ✅ | El cazador no consume azar; desempate total por menor id y N, S, E, O; todo paso del tiempo por la agenda (FR-021, FR-022). Los contadores no dependen del reloj real |
| **IV. Sin datos de cripta** | ✅ | ✅ | Costo y rango vienen de la fuente de datos; 100 es la regla por defecto de FR-002, no un dato de cripta. Criptas sintéticas solo en `tests/` |
| **V. Pruebas** | ✅ | ✅ | Cada caso del Apéndice B con prueba que cita su FR (FR-027); equivalencia turno a turno contra la referencia (FR-028) |
| **VI. Persistencia versionada** | ✅ | ✅ | Sin formato nuevo aquí. El cambio de versión de caché y paquete es de la capacidad de datos (FR-008) |
| **VII. Presupuesto** | ✅ | ✅ | El cazador no hace solicitudes: usa el esqueleto ya cargado |
| **VIII. Decisiones medidas** | ✅ | ✅ | M1 a M8 con `python main.py --bench`; la elección del campo compartido (R4) queda condicionada a M3 y M4 |
| **IX. Spec antes que código** | ✅ | ✅ | Spec confirmada (`381fdd6`, `749bd2f`) antes del código; FR-034 ya corregida a P1 §2.4 en la spec |
| **X. Trazabilidad** | ✅ | ✅ | [Trazabilidad FR → decisión](#trazabilidad-fr--decisión) cubre FR-001 a FR-034 |
| **XI. Registro de prompts** | ✅ | ✅ | Este prompt va a las notas para `PROMPTS_LLM.md` |
| **Contratos compartidos** | — | ✅ | P-01 aceptada: `primer_paso` recibe `limite=None` como parámetro opcional al final (y `espacio=None`); `entrantes` solo lo ofrece `GrafoCripta` y no se exige a `GrafoConocido`. No cambia ninguna llamada existente de «ir a» |
| **README en el mismo cambio** | — | ✅ | Ayuda y README describen costo de salidas y cazador (FR-029) |

**Resultado del gate**: sin violaciones. El único punto abierto es de coordinación (contrato compartido), no un
incumplimiento. No hace falta llenar la tabla de excepciones.

## Decisiones

| # | Tema | Alternativas | Elección | Complejidad | Evidencia | Límites | Detalle |
|---|------|--------------|----------|-------------|-----------|---------|---------|
| D1 | Cola de prioridad | Reutilizar `AgendaEventos`; montículo aparte con inserción perezosa; con decrease-key; mínimo lineal | Montículo aparte, inserción perezosa, en `Modelo/ColaPrioridad.py` | O(log \|E_R\|) por operación | M2 | Hasta \|E_R\| entradas en la cola | [R1](research.md#r1-cola-de-prioridad-de-la-búsqueda-fr-011-fr-013-principio-i) |
| D2 | Distancias | `dict`; lista nueva por búsqueda; reinicio por lista de tocadas; marca de época | Listas de tamaño n con marca de época, en un `EspacioBusqueda` (persistente en el motor para los cazadores; por llamada si no se da), indexadas por los ordinales propios de `GrafoCripta` | O(1) acceso, O(1) reinicio, O(n) memoria una vez | M5 (control con lista nueva) | Efectos de caché en n grande | [R2](research.md#r2-distancias-en-arreglos-densos-por-ordinal-fr-011-fr-033-principio-i) |
| D3 | Corte por rango (FR-033) | Búsqueda completa y comparar al final; búsqueda acotada | Acotada: nada con distancia > cota entra a la cola | O((\|R\|+\|E_R\|) log \|E_R\|), sin n | M5, M6 | Rango que cubre toda la cripta: sin ahorro | [R3](research.md#r3-corte-por-rango-fr-012-fr-033) |
| D4 | Individual frente a compartido | Búsqueda adelante por cazador; campo hacia el jugador por el transpuesto | Compartido en el juego, condicionado a M3/M4; individual como referencia | Σ W(Rᵢ, dᵢ) frente a W(R_max^rev) + Σ deg | M3 (k*), M4 | Rangos dispares: domina la cota máxima | [R4](research.md#r4-un-cálculo-por-cazador-frente-a-un-cálculo-compartido-desde-el-jugador-fr-016-fr-018-fr-030) |
| D5 | Invalidación | Recalcular siempre; ruta recordada; búsqueda incremental; firma de puertas; contadores | Llave (ciclo, sala del jugador, versión de puertas, cota) con contadores que solo crecen; `ciclo` sostiene la validez entre ciclos | O(1) por verificación | M4 | Dentro de un ciclo, toda escritura de puertas de `Modelo/` debe pasar por el método único | [R5](research.md#r5-invalidación-y-reutilización-fr-016-fr-024-fr-031-fr-032) |
| D6 | Desempate por menor id | — | Compartido: regla de FR-014 directa. Individual: `primero[x]` con mínimo por id ante empate | O(1) por relajación | Prueba de contrato en ambas estrategias | Requiere costo ≥ 1 | [R6](research.md#r6-desempate-por-menor-id-en-cualquier-orden-de-recorrido-fr-014-contrato-de-001) |
| D7 | Costo del movimiento | Costo por comportamiento; punto único de reprogramación | Punto único en `ejecutar_evento` y `mover_jugador` | O(1) | M8, SC-002 | No cambia la elección de errantes ni rastreadores | [R7](research.md#r7-costo-del-movimiento-en-el-motor-fr-004-fr-005-fr-006-fr-007-fr-034) |
| D8 | Datos | — | Solo lectura de `costo` (`costo_salida`) y `rango`; los campos los agrega la capacidad de datos | O(1) | Prueba de conservación en caché | Validación de FR-001/FR-009: P-02 | [R8](research.md#r8-coordinación-de-datos-fr-001-fr-002-fr-008-fr-009) |
| D9 | Mediciones | — | M1 a M8 en `--bench` | — | — | El «antes» de M8 se toma del código previo | [R9](research.md#r9-mediciones-con---bench) |

### Dónde cambia el costo del movimiento (FR-004, FR-005)

| Lugar en `Modelo/MotorSimulacion.py` | Hoy | Después |
|---|---|---|
| `ejecutar_evento`, rama `Enemigo`: `self.proxima_accion(actor, 100)` | 100 siempre | Si el enemigo se movió (`mover_enemigo` devolvió `True`), `costo_salida(salida)` de la salida usada; si atacó, esperó o no pudo moverse, 100 |
| `mover_jugador`: `self.proxima_accion(jugador, costo=100)` | 100 | `costo_salida(salida)`; cubre cada paso de «ir a» |
| `accion_enemigo` | guardián, errante, rastreador | Agrega `"cazador"`, que delega en la decisión del cazador (data-model §8) |
| `activar_enemigo` | 100 | Sin cambio (FR-034) |
| `esperar`, `atacar`, usar, abrir, `cambiar_velocidad` | Sus costos y P1 §2.3 | Sin cambio (FR-005, FR-007) |
| Evento de cierre automático, `abrir_salida` y sus deshacer | Escriben `salida.cerrada` directo; los deshacer, con `setattr(..., "cerrada", ...)` | Pasan por el método único que incrementa `version_puertas`, incluidos los dos deshacer (D5) |
| `avanzar_hasta_jugador` | — | Incrementa `ciclo` al empezar (D5) |

La restauración de puertas al cargar vive en `Persistencia/ConversorPartida.py` y no se toca: ocurre entre ciclos y
basta con que `ciclo` avance.

## Trazabilidad FR → decisión

| FR | Decisión del plan |
|---|---|
| FR-001 | D8: se lee el costo; el rechazo de un costo inválido depende de P-02 |
| FR-002 | D8: `costo_salida` da 100 si falta, en movimiento, cazador, «ir a» y mapa |
| FR-003 | D4: el transpuesto usa el costo y la puerta de cada salida original; sin validar simetría |
| FR-004 | D7: `mover_jugador` y rama `Enemigo` reprograman con `costo_salida` |
| FR-005 | D7: el resto de las acciones conserva su costo |
| FR-006 | D7: errantes y rastreadores solo cambian el tiempo; SC-006 |
| FR-007 | D7: `cambiar_velocidad` sin cambios |
| FR-008 | D8: prueba de conservación del costo en la caché; el formato es de la capacidad de datos |
| FR-009 | D8: se lee el rango; el rechazo depende de P-02 |
| FR-010 | data-model §8, paso 1 |
| FR-011 | D2, D3, D4: distancia por salidas abiertas, costo por `costo_salida` |
| FR-012 | D3: corte por rango; «sin ruta dentro del rango» → esperar 100 |
| FR-013 | D7 y data-model §8: un paso, costo de la salida atravesada |
| FR-014 | D6 |
| FR-015 | D4: `GrafoCripta` sobre la cripta completa, sin niebla ni contenido de salas |
| FR-016 | D5: llave y demostración; referencia desde cero |
| FR-017 | `GrafoCripta.aristas` solo entrega salidas abiertas; el cazador no abre ni usa llaves |
| FR-018 | D4, D5: la decisión depende solo de sala, rango, sala del jugador y puertas |
| FR-019 | data-model §7: muerto no decide; su evento se descarta como hoy |
| FR-020 | `mover_enemigo` y `atacar` existentes: mismos mensajes |
| FR-021 | D6: desempate total, sin azar |
| FR-022 | D7: reprogramación por la agenda |
| FR-023 | Los comandos rechazados no escriben puertas ni mueven al jugador, así que no tocan los contadores |
| FR-024 | D5: el campo vive un ciclo y no se guarda; retroceder y cargar ocurren entre ciclos y `ciclo` avanza |
| FR-025 | D5: igual que FR-024 para `--replay` y la reconstrucción de 004 |
| FR-026 | D8: «ir a» y el mapa ya leen `costo_salida`; con el dato real usan el costo real |
| FR-027 | Plan de pruebas: un caso por viñeta del Apéndice B, con su FR |
| FR-028 | D4: individual sin reutilización como oráculo; partidas con puertas, jugador en movimiento y varios cazadores |
| FR-029 | README y ayuda en el mismo cambio |
| FR-030 | D9: M7 |
| FR-031 | D9: M4, escenarios estable e inestable |
| FR-032 | D9: M4 con «recalcular siempre» como alternativa medida |
| FR-033 | D2, D3, D9: M5 |
| FR-034 | D7: `activar_enemigo` sin cambio; dormido no decide ni busca |

## Project Structure

### Documentation (this feature)

```text
specs/003-terreno-cazador/
├── spec.md
├── plan.md          # este archivo
├── research.md      # R1 a R9
├── data-model.md    # estructuras y transiciones
└── checklists/
    └── requirements.md
```

No se generan `contracts/` ni `quickstart.md` en esta pasada. El contrato de búsqueda es el de 001
(`specs/001-niebla-mapa-ir-a/contracts/interfaz-ruta.md`); con P-01 aceptada, allí se agregan `limite=None` y
`espacio=None` como parámetros opcionales al final de `primer_paso`. `entrantes` no entra en la interfaz exigida a todo
grafo: solo lo ofrece `GrafoCripta`. No cambia ninguna llamada existente de «ir a».

### Source Code (repository root)

```text
Modelo/
├── ColaPrioridad.py      # nuevo (Persona A): montículo binario propio, inserción perezosa
├── BusquedaRuta.py       # nuevo (Persona A): primer_paso(..., limite=None, espacio=None), campo_hacia(...), EspacioBusqueda
├── GrafoCripta.py        # nuevo: interfaz de grafo sobre la cripta real, con ordinales y entrantes propios (sin Conocimiento)
├── MotorSimulacion.py    # costo del movimiento, decisión del cazador, contadores, método único de puertas
└── rutas_ir_a.py         # sin cambios de esta capacidad (delega en BusquedaRuta)

tests/
├── test_ruta_contrato.py         # existente; la tabla de desempates corre también contra el cazador
├── test_terreno.py               # costo de salidas, intervalo, velocidad (FR-001 a FR-007)
├── test_cazador.py               # casos del Apéndice B y bordes (FR-009 a FR-020, FR-034)
├── test_cazador_equivalencia.py  # campo compartido frente a referencia desde cero (FR-016, FR-028, SC-003)
├── test_invalidacion_puertas.py  # toda escritura de puertas del motor cambia version_puertas; y una prueba que lee el
│                                 # código fuente de Modelo/ y falla si aparece, fuera del método único, `.cerrada =`,
│                                 # setattr(..., "cerrada", ...) o _asignar_reversible(..., "cerrada", ...) (D5).
│                                 # Excluye por nombre Modelo/prueba_actores.py (pruebas manuales de la Parte I que
│                                 # arman salas a mano), con el motivo escrito en la prueba
├── bench_cazador.py              # M1 a M7
└── bench_motor.py                # existente; M8 repite la agenda de §4.1
```

**Structure Decision**: un solo proyecto MVC existente. Todo el cambio de reglas está en `Modelo/`; las mediciones se
agregan al `--bench` existente de `main.py`.

## Preguntas abiertas

| Id | Pregunta | A quién | Qué bloquea |
|---|---|---|---|
| P-01 | **Aceptada**: `primer_paso` recibe `limite=None` como parámetro opcional al final; `entrantes` solo lo ofrece `GrafoCripta` (para `campo_hacia`) y no se exige a `GrafoConocido`. No cambia ninguna llamada existente de «ir a» | Grupo y Persona A | — |
| P-02 | ¿Quién implementa el rechazo de la cripta ante un costo inválido (FR-001) o un rango ausente o inválido (FR-009)? **Propuesta, pendiente de acuerdo**: la capacidad de datos, al convertir el JSON (`Salida.desde_json` de `DTOS/Salida.py` y `FichaEnemigo.desde_json` de la clase `FichaEnemigo`, definida en `DTOS/FichaCatalogo.py`); esta capacidad aporta las pruebas | Grupo (capacidad de datos) | Las pruebas de rechazo de FR-001 y FR-009 |

## Complexity Tracking

Sin violaciones de la constitución que justificar.
