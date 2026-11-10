# Implementation Plan: Verificación de resolubilidad de una cripta

**Branch**: `main` (constitución v3.0.2: se trabaja sobre `main`) | **Date**: 2026-11-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-resolubilidad/spec.md`

## Summary

Antes de cada partida nueva, y con `--verificar`, el programa decide si la cripta es resoluble con **un único
recorrido en memoria, por oleadas**, sobre el grafo dirigido de salas. El esqueleto y la ubicación de las llaves se
obtienen una sola vez antes del recorrido; durante el recorrido no hay solicitudes (FR-026).

Estructuras, todas a mano (Principio I): vector de salas indexado por id, la `Queue` existente de
`Cache/Estructuras.py` (solo `enqueue`, `dequeue`, `is_empty`), vectores de marcas, un índice de llaves en arreglo
ordenado con búsqueda binaria propia, y puertas en espera por número de llave. Las oleadas se ordenan con el
`merge_sort` de `Modelo/ordenamiento.py`. Si la cripta no es resoluble, el reporte es un barrido final y las
dependencias se calculan con zonas hacia atrás marcadas con sello; los ciclos salen de seguir los enlaces.

Costo: **O(S + E + M log M)** para veredicto y orden (M = menciones de llaves, crece con K), que en la práctica es el
O(S + E + K log K) pedido. La cripta publicada más grande (cripta-06) tiene 300 salas, 760 salidas y 4 llaves.

El análisis encontró dos cosas que el plan corrige: la lectura de llaves ya existe en `API/Fuentes.py` pero una
entrada incompleta lanza `KeyError` sin capturar, y ningún paquete offline (ni los de las pruebas) trae `llaves.json`.

## Technical Context

**Language/Version**: Python 3.11 o superior (desarrollo con 3.12.10)

**Primary Dependencies**: `requests` (única permitida); no se agrega ninguna

**Storage**: caché en disco nueva `datos_locales/llaves_<id>.json` (mismo esquema versionado que el esqueleto); archivo
nuevo `criptas/<id>/llaves.json` en el paquete offline. El resultado no se persiste.

**Testing**: `unittest`, sin red, con paquetes offline temporales y fuentes simuladas para errores y presupuesto

**Target Platform**: consola multiplataforma; desarrollo en Windows

**Project Type**: aplicación de consola MVC

**Performance Goals**: verificación < 200 ms en una cripta de 300 salas, 760 salidas y 4 llaves (SC-004); cociente
≤ 2,5 por duplicación (SC-005). Las complejidades son análisis; todo tiempo es hipótesis hasta medirlo (M1 a M5)

**Constraints**: estructuras propias (sin `dict`/`set` como índice, sin `heapq`, `bisect`, `collections`, `networkx`,
`sorted()` ni `.sort()`); `list` solo como arreglo; sin red durante el recorrido; presupuesto de solicitudes;
determinismo carácter por carácter

**Scale/Scope**: criptas publicadas de 20 a 300 salas; mediciones sintéticas hasta 9600 salas

**Sin NEEDS CLARIFICATION técnicos**: las decisiones están en [research.md](research.md). Lo que conviene confirmar
con el grupo está en [Preguntas abiertas](#preguntas-abiertas).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / regla | Antes del diseño | Después del diseño | Cómo se cumple |
|---|---|---|---|
| **I. Estructuras propias** | ✅ | ✅ | Vector de salas, vectores de marcas, índice ordenado con búsqueda binaria propia, `espera` por llave, `sello`, `depende_de`: todos arreglos indexados. Cola: `Queue` propia. Orden: `merge_sort` propio. Sin `dict`/`set` como índice; los `dict` de los DTO (`sala.salidas`, JSON) solo se recorren o parsean |
| **I. Complejidad documentada** | ✅ | ✅ | Tablas en [data-model.md](data-model.md); se copian a los docstrings. Alternativas en [research.md](research.md) R1 a R8 |
| **II. MVC** | ✅ | ⚠️ Justificado | La decisión vive en `Modelo/Resolubilidad.py`, sin red, archivos ni consola. La red y la caché están en `API/` y `Gestor/`; el formato en `Vista/`. El resultado cruza como DTO. **Excepción**: `Modelo/` importa `Queue` de `Cache/Estructuras.py`, que es una estructura pura sin E/S pero vive en un paquete de adaptadores ([Complexity Tracking](#complexity-tracking), P-12). `--bench` no instancia la vista |
| **III. Determinismo** | ✅ | ✅ | Sin `random` ni reloj real; la verificación ocurre antes de crear el motor y no se anota. Todos los órdenes salen de id de sala, dirección fija e índice ordenado (R11) |
| **IV. Sin datos de cripta** | ✅ | ✅ | El orden N, S, E, O es una regla, no un dato. Las criptas de prueba y del bench se generan en `tests/`. Las dimensiones de cripta-06 solo aparecen en la documentación y como parámetros del bench |
| **V. Pruebas** | ✅ | ✅ | Un escenario por fila del [quickstart](quickstart.md), cada uno con su FR. Los paquetes temporales existentes se actualizan con `llaves.json` para no romper la suite |
| **VI. Persistencia versionada** | ✅ | ✅ | `llaves_<id>.json` lleva la versión de la cripta y se descarta si cambia, igual que el esqueleto. No cambia `CRPT`, `CRIPTA-LOG` ni puntajes |
| **VII. Presupuesto** | ✅ | ✅ | El presupuesto se fija tras los detalles y antes de esqueleto y llaves; todo pasa por `_hacer_solicitud`, que lo revisa antes de cada intento. Cripta-06: 9 de 63 sin caché, 2 con caché. La partida reutiliza lo ya pedido |
| **VIII. Decisiones medidas** | ✅ | ✅ | M1 a M5 en `tests/bench_resolubilidad.py`, incluidas las alternativas A1 a A3 |
| **IX. Spec antes que código** | ✅ | ✅ | Spec confirmada en `e07ac0a` y clarificaciones en `ba1f47d`. Las correcciones de texto de P-13 y P-14, si se aceptan, van a la spec en una confirmación propia antes del código |
| **X. Trazabilidad** | ✅ | ✅ | [Requisitos del plan](#requisitos-del-plan) cubre los 30 FR. FR-027 no existe en la spec y no se reutiliza (P-13) |
| **XI. Registro de prompts** | ✅ | ✅ | Este `/speckit-plan` se anota en las notas personales para `PROMPTS_LLM.md` |
| **Contratos compartidos** | — | ⚠️ Avisar | `nueva_partida` gana `forzar`; `GestorDatos.obtener_llaves`; formato del paquete offline; prioridad de opciones de `main.py`. Avisar al grupo antes de cambiarlos |
| **README en el mismo cambio** | — | ✅ | PR-09 (README en UTF-16: avisar al grupo) |

**Resultado del gate**: aprobado. Una sola desviación (importar `Queue` desde `Modelo/`), pedida explícitamente y
justificada abajo. Ningún principio bloqueante.

## Decisiones

| # | Tema | Resolución | Detalle |
|---|------|------------|---------|
| 1 | Grafo | Vector de salas por id; salidas en orden N, S, E, O; llaves de cada sala, incluidas las que suelta un enemigo | [R1](research.md#r1-vector-de-salas-fr-001-fr-003-fr-005) |
| 2 | Cola | `Queue` de `Cache/Estructuras.py`; marcar al encolar; `size()` no se usa | [R2](research.md#r2-cola-fifo-del-recorrido-fr-001-fr-002) |
| 3 | Marcas | `visitada`, `obtenida`, `en_ronda`: arreglos de booleanos | [R3](research.md#r3-vectores-de-marcas-fr-001-fr-007) |
| 4 | Índice de llaves | Arreglo ordenado con `merge_sort` + búsqueda binaria propia; el número de llave indexa los demás vectores | [R4](research.md#r4-índice-de-llaves-fr-007-fr-014) |
| 5 | Oleadas | `espera[K]`; al obtener la llave se sueltan sus puertas y forman la oleada siguiente; cada oleada se ordena con `merge_sort` | [R5](research.md#r5-recorrido-por-oleadas-y-puertas-en-espera-fr-001-fr-002-fr-006-fr-007) |
| 6 | Reporte | Barrido final por id de sala y dirección, sin estructura propia | [R6](research.md#r6-veredicto-y-reporte-como-barrido-final-fr-006-fr-008-fr-009-fr-010-fr-014) |
| 7 | Dependencias | Zona hacia atrás por sala de ubicación, con `entrantes` y `sello`; descarta puertas internas; `depende_de[K]` | [R7](research.md#r7-dependencias-entre-llaves-fr-011-clarifications) |
| 8 | Ciclos | Seguir `depende_de` con marcas; emitir barriendo por número, sin ordenar | [R8](research.md#r8-ciclos-de-llaves-fr-011-fr-014-us22-us23-us26) |
| 9 | Datos | `obtener_llaves_cripta` existente + validación; `llaves.json` offline; caché versionada en disco | [R9](research.md#r9-lectura-de-la-ubicación-de-las-llaves-fr-024-fr-025-fr-026-fr-028) |
| 10 | Integración | `--verificar`, `--forzar`, `CriptaNoResoluble`, verificación antes de motor y bitácora | [R10](research.md#r10-integración-en-mainpy-y-el-controlador-fr-015-a-fr-023) |
| 11 | Bench | M1 a M5, alternativas A1 a A3 | [R12](research.md#r12-mediciones-en---bench-fr-029-fr-030-sc-004-sc-005) |

### Alternativas consideradas (resumen)

| Estructura | Elegida | Consideradas | Medida en `--bench` |
|---|---|---|---|
| Índice de llaves | arreglo ordenado + búsqueda binaria, O(log K) | árbol rojo-negro (misma búsqueda, más código, inserciones que no se usan); tabla hash (descartada por la restricción) | A3: búsqueda lineal del id |
| Recorrido | una pasada por oleadas con puertas en espera, O(S + E + K log K) | revisar todas las cerradas tras cada oleada, O(K·C) | A1: repetir el recorrido completo por cada llave |
| Dependencias | zona hacia atrás con sello, compartida por sala | propagación hacia adelante (incorrecta, R7); SCC + DAG | A2: zona de cada llave por separado |
| Ciclos | barrido del grafo funcional, O(K) | ordenar los ciclos con `merge_sort`, O(K log K) | — |

## Requisitos del plan

| ID | Requisito | FR / SC | Archivos |
|----|-----------|---------|----------|
| PR-01 | `IndiceLlaves`: menciones, `merge_sort`, quitar repetidos, búsqueda binaria propia | FR-007, FR-014 | `Modelo/Resolubilidad.py` (nuevo) |
| PR-02 | `GrafoSalas`: vector por id, salidas en orden fijo, llaves por sala (incluidas las de enemigos), `entrantes`, salas y destinos inexistentes | FR-001, FR-003, FR-004, FR-005 | `Modelo/Resolubilidad.py` |
| PR-03 | Recorrido por oleadas con `Queue`, marcas y `espera`; veredicto y orden | FR-001, FR-002, FR-006, FR-007, FR-026 | `Modelo/Resolubilidad.py` |
| PR-04 | Barrido del reporte: no obtenibles, frontera, puertas de salida, ubicaciones | FR-008, FR-009, FR-010, FR-014 | `Modelo/Resolubilidad.py`, `DTOS/ResultadoVerificacion.py` (nuevo) |
| PR-05 | Dependencias por zona y ciclos | FR-011, FR-014 | `Modelo/Resolubilidad.py` |
| PR-06 | Validación de `UbicacionLlave`; `GestorDatos.obtener_llaves` con caché versionada; `verificar_cripta` con presupuesto | FR-024, FR-025, FR-026, FR-028 | `DTOS/UbicacionLlave.py`, `API/Fuentes.py`, `AlmacenamientoLocalApi/AlmacenamientoLocalApi.py`, `Gestor/GestorDatos.py`, `Gestor/PreparadorPartida.py` |
| PR-07 | `nueva_partida(..., forzar)`, `CriptaNoResoluble`, `mostrar_verificacion` | FR-018 a FR-023 | `Controlador/ControladorPartida.py`, `Vista/VistaConsola.py` |
| PR-08 | `--verificar`, `--forzar`, prioridad y códigos | FR-015, FR-016, FR-017, FR-022, FR-024 | `main.py` |
| PR-09 | `llaves.json` en los generadores de paquetes y en `paquete/`; README | FR-028, FR-031 | `tests/utiles_niebla.py`, `tests/test_integracion.py`, otros generadores, `README.md` |
| PR-10 | Pruebas por escenario y determinismo | SC-001, SC-002, SC-003, SC-006, SC-007, SC-008, SC-009, FR-012, FR-013 | `tests/test_resolubilidad.py`, `tests/test_verificacion_cli.py` (nuevos) |
| PR-11 | Bench M1 a M5 | FR-029, FR-030, SC-004, SC-005 | `tests/bench_resolubilidad.py` (nuevo), `main.py` |

**Cobertura**: FR-001 a FR-026 y FR-028 a FR-031 asignados (30 de 30; FR-027 no existe).

## Orden sugerido

```text
PR-01 índice ─ PR-02 grafo ─ PR-03 recorrido ─┬─ PR-04 reporte ─ PR-05 dependencias y ciclos
                                              └─ PR-11 bench (M1, M2 desde aquí)
PR-06 datos ─ PR-07 controlador y vista ─ PR-08 main ─ PR-09 paquetes y README
PR-10 acompaña a cada bloque (PR-09 debe entrar junto con PR-07: sin llaves.json las pruebas de partida nueva fallan)
```

## Preguntas abiertas

| ID | Pregunta | Quién | Bloquea | Mientras tanto |
|----|----------|-------|---------|----------------|
| **P-11** | La regla de la zona exige descontar las puertas internas de cada zona; las zonas de distintas llaves pueden solaparse, así que el cálculo de dependencias es O(S + E + Σ zonas), con peor caso O(L·(S + E)). ¿Se acepta, documentado, como excepción a «aproximadamente lineal» de FR-029 en ese peor caso? | Grupo | Nada | Se implementa R7 (sello, memoria por sala, corte al primer conflicto). M3 mide el caso no resoluble; si superara 2,5, se corrige la spec antes que el código (Principio IX) |
| **P-12** | `Modelo/` importará `Queue` desde `Cache/Estructuras.py`. ¿Se mueve la estructura a un paquete neutral (p. ej. `Estructuras/`) en otro cambio? Moverla cambia las importaciones de `CacheCatalogo` y `PlanificadorPrecarga` (contrato compartido) | Grupo | Nada | Se importa desde `Cache/` con la justificación de Complexity Tracking |
| **P-13** | La spec salta de FR-026 a FR-028. ¿Se deja constancia en la spec de que FR-027 no existe? | Autora de la spec | Nada | El plan cubre 30 FR y no reutiliza FR-027 (Principio X) |
| **P-14** | Assumptions dice que `/llaves` trae «llave, sala y enemigo»; el servicio usa el campo `id`. También la cabecera de la spec cita la constitución v3.0.1 | Autora de la spec | Nada | El código usa `id`, como ya hace `UbicacionLlave` |

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Las pruebas existentes que inician partidas nuevas fallan porque sus paquetes no tienen `llaves.json` (FR-024) | PR-09 entra en el mismo cambio que PR-07 |
| `paquete/` y `datos_locales/` locales quedan sin llaves | Regenerarlos; no se versionan (Restricciones técnicas) |
| Ids de sala dispersos harían crecer el vector a O(max_id) | No ocurre en las criptas publicadas (ids 1..S); un id no entero falla con `! Error` |
| Cambia la prioridad de opciones, contrato público | README y pruebas en el mismo cambio |
| `nueva_partida` cambia de firma | Parámetro nuevo con valor por defecto; avisar al grupo |
| Peor caso de dependencias (P-11) | M3 lo vigila |

## Project Structure

### Documentation (this feature)

```text
specs/002-resolubilidad/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli-verificacion.md
│   ├── fuente-llaves.md
│   └── interfaz-verificador.md
├── checklists/requirements.md
└── tasks.md             # Lo genera /speckit-tasks
```

### Source Code (repository root)

```text
Modelo/
├── Resolubilidad.py         # nuevo: IndiceLlaves, GrafoSalas, recorrido, reporte, dependencias, ciclos
└── ordenamiento.py          # sin cambios (se usa merge_sort)
Cache/Estructuras.py         # sin cambios (se usa Queue)
DTOS/
├── ResultadoVerificacion.py # nuevo
└── UbicacionLlave.py        # validación de campos
API/Fuentes.py               # obtener_llaves_cripta: error de entrada incompleta
AlmacenamientoLocalApi/AlmacenamientoLocalApi.py  # guardar/cargar llaves
Gestor/
├── GestorDatos.py           # obtener_llaves
└── PreparadorPartida.py     # verificar_cripta, fijar presupuesto común
Controlador/ControladorPartida.py  # nueva_partida(forzar), CriptaNoResoluble
Vista/VistaConsola.py        # mostrar_verificacion
main.py                      # --verificar, --forzar, bench
README.md
tests/
├── test_resolubilidad.py    # nuevo
├── test_verificacion_cli.py # nuevo
├── bench_resolubilidad.py   # nuevo
├── utiles_niebla.py         # llaves.json
└── test_integracion.py      # llaves.json
```

**Structure Decision**: se conserva la estructura MVC por carpetas. No se crean carpetas nuevas.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| `Modelo/Resolubilidad.py` importa `Queue` de `Cache/Estructuras.py` (paquete listado como adaptador en el Principio II) | Reutilizar la cola propia ya probada, como pide el grupo. `Estructuras.py` no hace red, archivos ni consola, así que el modelo sigue sin depender de la fuente de datos, que es el propósito del principio | Una cola nueva en `Modelo/` duplica código probado; mover `Queue` a un paquete neutral cambia importaciones de otras personas (contrato compartido) y queda como P-12 |
