# Quickstart: validar terreno y cazador

Guía para comprobar la capacidad de punta a punta **cuando esté implementada**. Los detalles están en
[data-model.md](data-model.md), [research.md](research.md) y [contracts/](contracts/). Aquí no hay código de
implementación.

## Requisitos

- Python 3.11 o superior, con `requests` instalado. Sin él, `test_integracion` y `test_puntajes` ni siquiera se
  importan, aunque las pruebas no usan la red.
- Un paquete offline de prueba con costos en las salidas y al menos un enemigo con `"comportamiento": "cazador"` y
  `"rango"`. `tests/utiles_niebla.py` (`crear_paquete_niebla`, `salida(..., costo=...)`) muestra el formato. Las
  criptas grandes salen de `tests/generador_criptas.py` mediante `tests/utiles_terreno.py` (T003), deterministas por
  semilla y sin datos de criptas reales.

```bash
python -m pip install requests
python -m unittest discover -s tests -v
```

**Resultado esperado**: 100 % en verde. Las pruebas de guardianes, errantes y rastreadores siguen pasando igual que en
la línea base de T001 (FR-006, SC-006). Las 10 omitidas de `test_ruta_contrato` dejan de omitirse cuando exista
`Modelo/BusquedaRuta.py`.

## Escenarios

Cada prueba debe citar su FR en el nombre o en un comentario (Principios V y X; FR-027).

### 1. Terreno con costo (FR-001 a FR-005, FR-008, SC-002)

Con un paquete cuya sala 1 tenga una salida `E` de costo 250 hacia la sala 2, y una salida `S` sin costo declarado:

```bash
python main.py --offline paquete/ --cripta cripta-terreno --semilla 7
```

```text
> e
> o
> s
```

**Esperado**:

| Caso | Resultado |
|------|-----------|
| Jugador de velocidad 100 cruza la salida de costo 250 | El reloj avanza 250 |
| Salida sin costo declarado | Vale 100, igual que en la Parte I (FR-002) |
| Vuelta por una salida con otro costo | Se usa el costo de la salida que se atraviesa, sin validar simetría (FR-001, FR-003) |
| Actor de velocidad 1 000 cruza una salida de costo 1 | Intervalo 1, nunca 0 (FR-005) |
| Velocidad 100, cruza costo 400 en 1 000; en 1 100 la velocidad pasa a 200 | Próximo turno en 1 250 (FR-007) |
| Costo 0, negativo o no entero en el paquete | La cripta se rechaza con un mensaje claro (FR-001) |
| Un viaje «ir a» por salidas con costo | Cada paso cuesta lo de su salida; la ruta elegida es la de menor costo (FR-004, FR-026) |

`mapa` y las rutas de «ir a» usan el costo real de cada salida (FR-026). El costo se conserva en la caché en disco (FR-008); la identificación de versión de esa caché es de la capacidad de datos y tiene un límite conocido, anotado en su plan (spec 002).

### 2. El cazador persigue (FR-009 a FR-015, FR-018, FR-020, FR-034)

Entrar a la sala de un cazador dormido para activarlo y alejarse.

**Esperado**:

| Caso | Resultado |
|------|-----------|
| Antes de que el jugador entre a su sala | Dormido: no decide ni calcula rutas (FR-034) |
| Al entrar el jugador | Se activa; su primera acción tiene costo base 100 (FR-034) |
| Misma sala que el jugador | Ataca con el costo de ataque de la Parte I (FR-010) |
| Ruta de 2 salidas con costo 500 frente a ruta de 4 salidas con costo 400, rango ≥ 400 | Primer paso de la ruta de 400 (FR-011, FR-013) |
| Dos vecinas con rutas de costo mínimo | Va a la de menor id; entre salidas a esa vecina, la de menor costo y luego N, S, E, O (FR-014) |
| Se mueve | Un solo paso; el costo de la acción es el de la salida atravesada (FR-013) |
| Sale de la sala del jugador o entra a ella | Mismos mensajes que los demás enemigos (FR-020) |
| Se mueve a una sala donde el jugador nunca entró | Sigue activo (FR-034) |
| Varios cazadores | Cada uno decide solo con su sala, su rango, la sala del jugador y las puertas; pueden compartir sala (FR-018) |

El cazador ignora la niebla, el conocimiento del jugador y el contenido de las salas (FR-015).

### 3. El cazador espera (FR-012, FR-017, FR-019)

**Esperado**:

| Caso | Resultado |
|------|-----------|
| Todas las rutas al jugador pasan por una puerta cerrada | Espera con costo 100 y no abre la puerta, aunque porte la llave (FR-012, FR-017) |
| Ruta abierta más barata de 600 con rango 500 | Espera con costo 100 (FR-012) |
| Cazador muerto | No vuelve a actuar; su turno pendiente se descarta sin efecto (FR-019) |

### 4. Equivalencia con el cálculo desde cero (FR-016, FR-021, FR-023 a FR-025, FR-028, SC-003, SC-005)

```bash
python -m unittest tests.test_cazador_equivalencia -v
```

**Esperado**:

| Caso | Resultado |
|------|-----------|
| Una puerta de la ruta del cazador se cierra entre dos turnos | Decide como desde cero: otra ruta de costo mínimo dentro del rango, o espera (FR-016) |
| ≥ 1 000 turnos de cazadores con cierres, aperturas, cambios de sala del jugador y varios cazadores | La decisión (acción, sala de destino, salida, costo) coincide con la referencia desde cero en el 100 % (FR-028, SC-003) |
| Comando rechazado del jugador | No cambia ninguna decisión (FR-023) |
| Misma cripta, semilla y acciones | Mismas decisiones; el cazador no consume azar (FR-021) |
| Jugada, guardada, cargada y continuada | Mismas decisiones que la partida sin interrumpir (FR-024, SC-005) |
| Retroceder con un pergamino | Los cazadores deciden lo mismo que en ese estado de la partida original (FR-024) |

Reproducir la partida jugada:

```bash
python main.py --offline paquete/ --replay partida.log
```

**Esperado**: las mismas decisiones de todos los cazadores en el 100 % de los turnos (FR-025, SC-005). La
reconstrucción de estados de la línea de tiempo (capacidad 004) da también las mismas decisiones; lo que 004 necesita
de esta capacidad está en [contracts/interfaz-cazador-linea.md](contracts/interfaz-cazador-linea.md).

### 5. Mediciones (FR-030 a FR-033, SC-004, SC-007; Principio VIII)

```bash
python main.py --bench
```

**Esperado**: se genera `resultados_bench_cazador.txt` con M1 a M7 ([research.md](research.md#r9-mediciones-con---bench)),
con equipo y versión de Python, sin red y sin vista. Además, `resultados_bench_agenda_despues.txt` (M8) se compara con
`resultados_bench_agenda_antes.txt` (T002), que se repite con `python tests/bench_agenda_solo.py`.

| Medición | Criterio |
|----------|----------|
| M4: 50 cazadores activos, puertas estables, puertas que cambian con frecuencia y recalcular siempre desde cero | Ciclo < 20 ms en los dos escenarios; la reutilización se justifica con la comparación (FR-030, FR-031, FR-032) |
| M5: criptas sintéticas de 10², 10³, 10⁴ y 10⁵ salas, mismo rango | La más grande ≤ 1,5 × la más pequeña (FR-033, SC-007) |
| M7: 50 cazadores activos en la cripta de referencia | Mediana y p95 < 20 ms (FR-030, SC-004) |
| M1, M2, M3, M6, M8 | Informativas; M3 reporta el k* que confirma o invierte la estrategia (R4) |

Toda afirmación de rendimiento del README y del Documento de Decisiones debe salir de esos archivos (FR-032).

## Cobertura del Apéndice B (SC-001)

| Caso | Escenario | Tarea | FR |
|------|-----------|-------|----|
| Actor de velocidad alta cruza salida de costo 1 | 1 | T022 | FR-005 |
| Cambia la velocidad de un actor que cruza una salida costosa | 1 | T023 | FR-007 |
| Menos salas pero mayor costo frente a más salas y menor costo | 2 | T034 | FR-011, FR-013 |
| Dos vecinas con rutas de costo mínimo | 2 | T035 | FR-014 |
| Sin ruta abierta | 3 | T050 | FR-012, FR-017 |
| Ruta más barata cuesta más que el rango | 3 | T051 | FR-012 |
| Una puerta de su ruta se cierra entre dos turnos | 4 | T055 | FR-016 |
