# Evidencia de T121: escenarios del quickstart y prueba de humo (spec 004)

Fuente: la nota de T121 en `tasks.md` (2026-11-17). Los módulos de la tabla se volvieron a correr uno por uno el 2026-11-17 con `python -m unittest tests.test_<módulo>`; todos pasan con el mismo número de pruebas que anota T121. Suite completa: 1183 pruebas, OK, 0 omitidas.

## Escenarios 1 a 16 ([quickstart](quickstart.md))

La nota no da un texto de resultado esperado por escenario: los cubren las pruebas de la suite, «corridas por módulo y en verde». Por eso el resultado esperado es que el módulo pase completo.

| Esc. | Prueba que lo cubre | Resultado esperado | Resultado obtenido |
|------|---------------------|--------------------|--------------------|
| 1 | `test_linea_consulta` | Módulo en verde (18 pruebas) | Ran 18 tests, OK |
| 2 | `test_linea_solo_lectura` | Módulo en verde (7 pruebas) | Ran 7 tests, OK |
| 3 | `test_linea_mismo_instante` | Módulo en verde (5 pruebas) | Ran 5 tests, OK |
| 4 | `test_linea_comando` | Módulo en verde (18 pruebas) | Ran 18 tests, OK |
| 5 y 6 | `test_linea_retroceso` | Módulo en verde (14 pruebas) | Ran 14 tests, OK |
| 7 | `test_linea_pergaminos` | Módulo en verde (8 pruebas) | Ran 8 tests, OK |
| 8 | `test_linea_replay_hasta` | Módulo en verde (49 pruebas) | Ran 49 tests, OK |
| 9 | `test_linea_cargar` (23), `test_linea_cargar_cli` (14) | Módulos en verde | Ran 23 tests, OK; Ran 14 tests, OK |
| 10 | `test_linea_persistencia` (15), `test_cli_historia` (30) | Módulos en verde | Ran 15 tests, OK; Ran 30 tests, OK |
| 11 | `test_linea_independencia_k` | Módulo en verde (2 pruebas) | Ran 2 tests, OK |
| 12 | `test_linea_copia` | Módulo en verde (26 pruebas) | Ran 26 tests, OK |
| 13 | `test_linea_sin_red` | Módulo en verde (9 pruebas) | Ran 9 tests, OK |
| 14 | `test_linea_cazadores` (con el registro de decisiones de A) | Módulo en verde (15 pruebas) | Ran 15 tests, OK |
| 15 | `test_linea_carga_sin_datos` | Módulo en verde (9 pruebas) | Ran 9 tests, OK |
| 16 | `test_linea_bitacora_guardado` | Módulo en verde (13 pruebas) | Ran 13 tests, OK |

## Prueba de humo con `main.py` real

Hecha con `--offline` y `--datos-locales` en carpetas temporales, borradas al terminar; no se usó `paquete/` ni `datos_locales/` del repositorio. La nota de T121 registra solo el resultado obtenido; el resultado esperado es el que describe la nota (sin diferencias con el quickstart).

| Comando | Resultado (según la nota de T121) |
|---------|-----------------------------------|
| Partida con `historia 0`, `historia #3`, `historia 99999` y `guardar` | Código 0; `historia 99999` y `#99` avisan «La acción 99 no existe» |
| `--cargar` + `historia #2` y `#3` | Código 0; el texto de `#3` es idéntico antes y después de guardar y cargar |
| `--replay --hasta 150` y `--hasta 0` | Mismo texto que `historia`; código 0 |
| `--replay --hasta 99999` | Avisa «La partida termina antes del instante 99999 (la bitácora acaba en el reloj 400)» y muestra el estado final; código 0 |
| `--hasta` sin `--replay` | Código 1 y su aviso |
| `--cargar` con `--checkpoint-cada 10` y con `--checkpoint-cada 0` | Código 1 y su aviso |
| `--cargar` con `--bitacora` igual al `.log` y al propio guardado | Código 1; `p.cripta` y `p.cripta.log` intactos (comparados byte a byte) |
| `guardar` con la bitácora igual a `<guardado>.log` o al guardado | `! Error: No se pudo guardar: la bitácora no puede ser ...`; la partida sigue (código 0) |
| `--cargar` con la carpeta de datos locales borrada | Código 1 y `faltan datos locales (contenido de las salas ...)` |

## Pendiente (de la nota de T121)

Sigue abierto, sin bloquear la tarea: T007 (confirmación de A, solo por chat) y T117 (no existe `informe_t117.md` en el repositorio).
