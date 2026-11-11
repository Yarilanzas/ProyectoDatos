# Quickstart: validar la línea de tiempo

Guía para comprobar la capacidad de punta a punta. No contiene código de implementación: eso va en `tasks.md`. Los comandos suponen
la raíz del repositorio y Python 3.11 o superior con `requests` instalado. **Hasta que se implemente, los escenarios 1 a 16 fallan**
(los 14 de la capacidad y los dos de carga sin datos locales y de bitácora igual a `<guardado>.log`); sirven como criterio de aceptación.

## Requisitos previos

```text
py -m pip install -r requirements.txt
py -m unittest discover -s tests -v        # línea base: todo en verde, sin red (Principio V, SC-009)
```

Las pruebas arman un **paquete offline temporal** con `tests/utiles_niebla.py` (`crear_paquete_niebla`). Una utilidad nueva,
`tests/utiles_linea.py`, agrega: el generador determinista de acciones (`random.Random(semilla)` propio), el «motor espía» que guarda
el resumen tras cada evento, y la comparación contra `obtener_estado_resumen()` ampliada con `conocimiento`, `mensajes` y `rastros`.

## Escenarios

Cada fila indica qué se comprueba, con qué se comprueba y el requisito que debe citar la prueba o el `partida.log` de evidencia
(Principio V, SC-001).

| # | Escenario | Cómo | Resultado esperado | Requisitos |
|---|-----------|------|--------------------|------------|
| 1 | Estado en `t` y en `#k` | Jugar una secuencia conocida; comparar `historia <t>` y `historia #k` con el estado registrado en ese momento por el motor espía | Coinciden en el 100 % de los casos (SC-003) | FR-001, FR-003, FR-004, FR-006 |
| 2 | La consulta no cambia nada | Fotografiar reloj, acciones, bitácora, guion, `conocimiento`, `mensajes`, `rastros` e historial de retroceso antes y después de consultas aceptadas y rechazadas | Idénticos (SC-004) | FR-008, FR-009 |
| 3 | Varios eventos en un mismo instante | Cripta de prueba donde coinciden en `t` un ataque, el fin de un efecto y un cierre de puerta; y un caso con decisión del jugador en `t` | El resumen refleja los tres; con decisión en `t`, es el estado previo a decidir | FR-001, FR-002 |
| 4 | Rechazos | `historia`, `historia -3`, `historia abc`, `historia #0`, `historia #99`, `historia 900` con el reloj en 400 | Los avisos de [comandos-historia.md](contracts/comandos-historia.md), sin consumir tiempo | FR-005, FR-009 |
| 5 | Retrocesos | 6 acciones, un `retroceder`; luego `historia #6`, `#7`, `historia <reloj anterior>`; acciones nuevas; escenario de pergamino recogido en la acción revertida y soltado después (R5) | `#6` es el estado actual, `#7` se rechaza; lo revertido no aparece; el estado reconstruido coincide con el real | FR-014, FR-015, FR-016, FR-029 |
| 6 | Cinco usos seguidos y un sexto | 6 acciones, 5 pergaminos, un sexto `retroceder` | Se comporta como la Parte I; la línea no cambia | FR-014 |
| 7 | Pergaminos por instante | Tener 3 en `t`, gastar 2 en retrocesos; `historia <t>` | Muestra 3; la cantidad real sigue siendo la actual | FR-029 |
| 8 | `--replay --hasta` | Bitácora de una partida jugada; `--hasta` en varios valores y mayor que el final | Mismo texto que `historia`; sin instanciar la vista; aviso de FR-012 si `t` > final | FR-007, FR-011, FR-012, FR-025 |
| 9 | Guardar, cargar, continuar | Jugar, guardar, cargar en un proceso nuevo, consultar antes y después del guardado, continuar, guardar, cargar de nuevo, `--replay --hasta` | Resúmenes idénticos antes y después; la línea del replay iguala a la jugada | FR-022, FR-025, FR-030, SC-005 |
| 10 | Versiones y opciones | Cargar un `CRPT` 2; un `CRPT` 3 con la línea alterada; `--hasta` sin `--replay`; `--checkpoint-cada` con `--cargar` y con 0 | `Versión incompatible`, código `2`, nada cargado; errores de uso con código `1` | FR-013, FR-018, FR-023, FR-024, FR-031, SC-008 |
| 11 | Independencia de K | Los mismos 100 instantes con K = 1, 50 y 500 | Resúmenes idénticos | FR-028, SC-003 |
| 12 | Oráculo de la copia | En cripta de ≤ 60 salas, comparar la copia estructurada con `deepcopy` completo | Resúmenes iguales; con 200 salas la estructurada funciona y `deepcopy` completo no | R2 |
| 13 | Sin solicitudes | Reconstruir con una fuente que cuenta llamadas; vaciar la caché de memoria; borrar un dato local | 0 llamadas; con el dato borrado, `! Error: No se puede reconstruir sin nuevas solicitudes...`, código `1` | Principio VII |
| 14 | Estado de A | Con cazadores activos, reconstruir tras guardar, cargar y retroceder | Mismas decisiones que la partida real | 003 FR-025 |
| 15 | Cargar sin datos locales | Guardar una partida con línea; borrar la carpeta de datos locales (o un dato que el guion necesite, con el paquete offline sin red); `--cargar` y el comando `cargar` | `! Error: No se puede reconstruir sin nuevas solicitudes: faltan datos locales (<qué>)`, código `1`; no se carga nada; en el comando `cargar` la partida en curso (reloj, bitácora y línea) queda intacta; 0 llamadas a la fuente | FR-022, FR-025, Principio VII |
| 16 | Bitácora igual a `<guardado>.log` | Intentar `guardar p.cripta` en una sesión con `--bitacora p.cripta.log`, y `--cargar p.cripta --bitacora p.cripta.log`; luego repetir con una bitácora distinta | Error de uso, código `1`, sin guardar ni cargar nada; con una bitácora distinta, el replay de `--hasta` coincide con la línea (regla 2 sin excepciones) | FR-025, FR-030 |

Cada prueba cita el FR en su nombre o docstring. Las pruebas no usan red.

## Mediciones (`--bench`)

```text
py main.py --bench                       # incluye bench_linea; escribe resultados_bench_linea.txt
py -m tests.bench_linea                  # solo la línea de tiempo
```

Plan en [research.md, R15](research.md#r15-plan-de-mediciones---bench): M1 a M10, con **al menos tres valores de K** (1, 10, 50, 100, 500),
la alternativa **sin puntos de control**, memoria y tiempo, y partidas de **5 000 acciones deterministas por semilla**. **M10** repite la
medición de la primera parte (P1 §4.6, el `bench_retroceso` de `tests/bench_personaC.py`: 5 intervalos × 50 cambios, registrar y deshacer)
con la línea registrando; enunciado Parte II §5.6 y §6.3. La agenda (P1 §4.1) la repite otra capacidad [PERSONAS: grupo].

Criterios de aceptación de la medición:

- M1: 100 % de las consultas < 50 ms con el K por defecto, y el K por defecto queda justificado por M1 y M2 (SC-002, SC-007).
- M2: duplicar las acciones duplica la memoria; puntos ≤ ⌈n/K⌉ + 1 + L + P (SC-006).
- M4: el costo del recorte no crece con la longitud de la partida; el umbral se fija con la medición (SC-010).
- M5: el ciclo con registro sigue bajo 20 ms en el p95 (§5.2).
- M10: tabla **antes y después** (solo `Historial` frente a `Historial` con la línea registrando) copiada a `DECISIONES.md`; si el
  `Historial` sigue siendo adecuado se muestra con esos datos, y si no, se cambia y se documenta el antes y el después (§5.6).
- Los cambios 1, 2 y 3 de [plan.md](plan.md#cambios-propuestos-a-la-spec) se documentan en `DECISIONES.md` con el enunciado citado, la
  alternativa descartada y las mediciones M1, M2, M4 y M6.

Los números de [research.md](research.md) son una exploración previa local, no versionada (HIPÓTESIS); este paso los confirma o los
corrige antes de fijar el K por defecto en README o en el Documento de Decisiones.

## Verificación manual (humo)

```text
py main.py --offline paquete/ --cripta cripta-01 --semilla 7 --bitacora p.log
> esperar        (varias veces, y algún mover)
> historia 0
> historia #3
> guardar p.cripta
> salir

py main.py --offline paquete/ --cargar p.cripta
> historia #2                   (antes del guardado)
> salir

py main.py --offline paquete/ --replay p.log --hasta 150
py main.py --offline paquete/ --replay p.log --hasta 99999       (aviso + estado final)
py main.py --hasta 5                                              (error de uso, código 1)
py main.py --cargar p.cripta --checkpoint-cada 10                 (error de uso, código 1)
py main.py --offline paquete/ --cargar p.cripta --bitacora p.cripta.log     (error de uso, código 1: la bitácora no puede ser <guardado>.log)

(con p.cripta guardada) borrar datos_locales/ y repetir --cargar sin red  (faltan datos locales: error, código 1, nada se carga)
```

Para cada `historia`, el texto debe coincidir con el de `--replay --hasta` del mismo instante.
