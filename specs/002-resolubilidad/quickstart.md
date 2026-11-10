# Quickstart: validar la verificación de resolubilidad (spec 002)

**Plan**: [plan.md](plan.md) | Formatos de salida: [contracts/cli-verificacion.md](contracts/cli-verificacion.md)

Guía para comprobar de punta a punta que la capacidad funciona. No contiene implementación.

## Requisitos previos

- Python 3.11 o superior y `requests` (`pip install -r requirements.txt`).
- Un paquete offline con `criptas/<id>/llaves.json` ([contracts/fuente-llaves.md](contracts/fuente-llaves.md)). El
  paquete `paquete/` del repositorio debe actualizarse con ese archivo; las pruebas generan los suyos.

## 1. Suite completa sin red (Principio V)

```bash
python -m unittest discover -s tests -v
```

Esperado: todo en verde, incluidas las pruebas existentes de partidas nuevas (sus paquetes temporales ya traen
`llaves.json`) y las nuevas `tests/test_resolubilidad.py` (modelo) y `tests/test_verificacion_cli.py` (opciones,
códigos y archivos). Cada prueba cita su FR.

## 2. Escenarios por historia

Las criptas de prueba se construyen en `tests/` con un generador de paquetes. Para cada fila, la evidencia es una
prueba automatizada.

| # | Escenario | Comando (con el paquete de la prueba) | Esperado | FR |
|---|-----------|---------------------------------------|----------|----|
| 1 | Resoluble sin abrir puertas | `python main.py --offline <pkg> --verificar c-simple` | «es resoluble», orden, código 0, sin `partida.log` nuevo | FR-006, FR-015, FR-016 |
| 2 | Cadena A → B → salida | `--verificar c-cadena` | `A` (oleada 1), `B` (2), salida (3) | FR-007 |
| 3 | Oleadas con desempate | `--verificar c-oleadas` (C y D al inicio, C abre la sala de A) | `C, D, A` | FR-007 |
| 4 | Llave soltada por enemigo | `--verificar c-enemigo` | la llave cuenta como obtenible | FR-003 |
| 5 | Trampas y cierres automáticos | `--verificar c-trampas` | mismo veredicto que sin ellos | FR-004 |
| 6 | Salida dirigida | `--verificar c-dirigida` (A→B abierta, B→A cerrada sin llave) | B alcanzable; nada vuelve por B→A | FR-005 |
| 7 | Sala de salida alcanzable por puerta abierta, sin puerta con la llave | `--verificar c-sin-puerta` | no resoluble; «no existe ninguna salida hacia la sala …» | FR-009, US1.6 |
| 8 | Ciclo directo | `--verificar c-ciclo-k` | `K -> K (ciclo directo)` | FR-011, US2.2 |
| 9 | Ciclo por cadena | `--verificar c-ciclo-k1k2` | `K1 -> K2 -> K1` | FR-011, US2.3 |
| 10 | Puertas alternativas con llaves distintas | `--verificar c-alternativas` | sin ciclos; K «sin dependencia» | FR-011, US2.4 |
| 11 | Llave sin ubicación | `--verificar c-desconocida` | «ubicación desconocida» | FR-010, US2.5 |
| 12 | Frontera vacía | `--verificar c-desconectada` | «Frontera bloqueada: ninguna …» | FR-009 |
| 13 | Sala inexistente en ubicación o destino | `--verificar c-inexistente` | se reporta «(no existe)»; no falla | Edge Cases |
| 14 | Partida nueva no resoluble | `python main.py --offline <pkg> --cripta c-ciclo-k` | `! Error: … no es resoluble …`, reporte, código 1, sin bitácora ni puntajes | FR-020, SC-006 |
| 15 | Partida nueva resoluble | `--cripta c-simple` (con entrada `salir`) | orden y la partida inicia | FR-019 |
| 16 | Lista interactiva | sin `--cripta`, elegir `c-ciclo-k` | igual que 14 | FR-018, US3.3 |
| 17 | Forzar | `--cripta c-ciclo-k --forzar` | inicia sin reporte ni orden | FR-021 |
| 18 | Verificar y forzar | `--verificar c-ciclo-k --forzar` | resultado completo, no inicia | FR-017, US4.3 |
| 19 | Cargar y replay | `--cargar <forzada>.cripta`, `--replay <forzada>.cripta.log` | funcionan sin verificación | FR-022 |
| 20 | Falta `llaves.json` | paquete sin el archivo, `--verificar` y `--cripta … --forzar` | `! Error: Falta el archivo para /criptas/…/llaves …`, código 1 | FR-024, US5.3 |
| 21 | Presupuesto agotado | fuente HTTP simulada con presupuesto 2 | `! Error: Se agotó el presupuesto de solicitudes …`; solicitudes ≤ presupuesto | FR-024, FR-026, SC-008 |
| 22 | Error del servicio | fuente simulada que responde 500 | `! Error: El servicio respondió 500 …`, código 1, sin veredicto | FR-024, US5.1 |

## 3. Determinismo (SC-003, SC-007)

- Ejecutar `--verificar` 100 veces sobre la misma cripta y sobre variantes con salas, salidas y ubicaciones barajadas
  (semilla fija en la prueba): todas las salidas idénticas carácter por carácter.
- Misma cripta, semilla y acciones, con y sin la verificación previa: misma bitácora y mismo estado final.

## 4. Rendimiento (SC-004, SC-005, FR-030)

```bash
python main.py --bench
```

Esperado en `resultados_bench_resolubilidad.txt`:

- M1: cripta sintética de 300 salas, 760 salidas y 4 llaves, resoluble y no resoluble: p95 < 200 ms.
- M2 y M3: en cada duplicación (300 → 9600 salas), cociente de medianas ≤ 2,5, en ambos casos.
- M4: tabla de la versión elegida contra A1, A2 y A3.

## 5. Con el servicio real (opcional, gasta presupuesto)

```bash
python main.py --verificar cripta-06
```

Esperado: veredicto con a lo sumo 9 solicitudes la primera vez y 2 con la caché de `datos_locales/` válida.

## 6. Documentación

El README (UTF-16, avisar al grupo antes de editarlo) documenta `--verificar`, `--forzar`, la nueva prioridad de
opciones, los códigos de salida y el archivo `llaves.json` del paquete offline (FR-031).
