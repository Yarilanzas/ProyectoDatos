# Quickstart: validar niebla, mapa e «ir a»

Guía para comprobar la capacidad de punta a punta **cuando esté implementada**. Los detalles están en
[data-model.md](data-model.md) y [contracts/](contracts/). Aquí no hay código de implementación.

## Requisitos

- Python 3.11 o superior, con `requests` instalado. Sin él, `test_integracion` y `test_puntajes` ni siquiera se
  importan, aunque las pruebas no usan la red.
- Un paquete offline de prueba. `tests/test_integracion.py` muestra su formato con `crear_paquete_offline`.

```bash
python -m pip install requests
python -m unittest discover -s tests -v
```

**Resultado esperado**: 100 % en verde, incluidas las pruebas de la Parte I (SC-006).

## Escenarios

Cada prueba debe citar su FR en el nombre o en un comentario (Principios V y X).

### 1. Niebla al empezar y al moverse (FR-001 a FR-005)

```bash
python main.py --offline paquete/ --cripta cripta-test --semilla 7
```

```text
> mapa
> e
> mapa
```

**Esperado**: al inicio, solo la sala 1 explorada y la 2 avistada. Después, 1 y 2 exploradas y 3 y 5 avistadas. La
sala 4 nunca aparece. El reloj no cambia por `mapa`, y `mapa` no aparece en `partida.log`.

### 2. Puerta recordada (FR-006, FR-007, FR-008)

Con una puerta de cierre automático: abrirla, alejarse más allá de sus dos salas, esperar a que se cierre, consultar
`mapa` y volver.

**Esperado**: mientras el jugador esté lejos, `mapa` la muestra abierta y no aparece «Una puerta se cerró sola.». Al
entrar a cualquiera de sus dos salas pasa a cerrada.

### 3. Antorcha (FR-009, FR-010, FR-011, FR-014)

Encender la antorcha y entrar a una sala con una vecina que tenga enemigos dormidos y una trampa armada. Después
consultar `mapa`, ver el estado y usar `retroceder`.

**Esperado**: la vecina queda explorada, sin mostrar su contenido; la vida no cambia y sus enemigos siguen dormidos.
Sus salidas sin observar figuran `sin observar`. `retroceder` deja el mapa idéntico al de antes de entrar.

### 4. «ir a» (FR-021 a FR-031)

```text
> ir a 1
> ir a 99
```

**Esperado**, con un paquete cuyas rutas y costos se conozcan:

| Caso | Resultado |
|------|-----------|
| Sala avistada, desconocida o inexistente | Mismo aviso. Reloj, acciones y bitácora iguales (SC-005) |
| Sala actual, o sin ruta conocida | Aviso propio, sin cambios |
| Dos rutas de igual costo | El primer paso va a la vecina de menor id |
| Sala con enemigos en la ruta | Se detiene allí con el motivo |
| Veneno activo | Se detiene al terminar el primer paso con daño |
| Puerta recordada abierta, real cerrada | Al verla recalcula; sigue por otra ruta o se detiene sin gastar tiempo |
| Puerta cerrada con la llave en el inventario | No se abre; esa salida no cuenta |
| Salida `sin observar` | No se usa |
| `retroceder` tras el viaje | Deshace solo el último paso, y el viaje no sigue |

Revisar `partida.log`:

```text
# ir a 1
mover O
```

### 5. Reproducción (FR-017, FR-030, SC-004)

```bash
python main.py --offline paquete/ --replay partida.log
```

**Esperado**: mismo reloj, posición y conocimiento que la partida. La salida no usa `VistaConsola`.

### 6. Guardar, cargar y reproducir (FR-015 a FR-017, SC-003)

```text
> guardar mi.cripta
> salir
```

```bash
python main.py --offline paquete/ --cargar mi.cripta
```

```text
> mapa
> esperar
> salir
```

```bash
python main.py --offline paquete/ --replay partida.log
```

**Esperado**: `mapa` es idéntico antes y después de cargar, también con una puerta recordada distinta de la real y con
salas exploradas por antorcha. `partida.log` contiene `@cargar`. El replay coincide con la partida, también en
azar y `secuencia`. **Es el caso que hoy falla** (hallazgo H1).

Probarlo con antorcha encendida al guardar: en ambos casos debe quedar apagada tras la carga.

### 7. Versiones viejas (FR-016, FR-030)

```bash
python main.py --offline paquete/ --cargar archivo_v2.cripta
python main.py --offline paquete/ --replay bitacora_v1.log
```

**Esperado**: `! Error: Versión incompatible: ...`, código de salida `2`, nada cargado.

### 8. Mediciones (Principio VIII)

```bash
python main.py --bench
```

**Esperado**: se genera `resultados_bench_niebla.txt` con M1 a M6 ([research.md](research.md#r9-qué-se-mide-con---bench)),
sin red y sin vista. Toda afirmación de rendimiento del README y del Documento de Decisiones debe salir de ese archivo.

## Cobertura del Apéndice B (SC-001)

| Caso | Prueba | FR |
|------|--------|----|
| Antorcha explora sin activar enemigos ni trampas | Escenario 3 | FR-009, FR-010 |
| Pergamino revierte entrada con antorcha | Escenario 3 | FR-014 |
| «ir a» hacia sala no explorada | Escenario 4 | FR-022 |
| Puerta recordada abierta que está cerrada | Escenarios 2 y 4 | FR-006, FR-026 |
| «ir a» entra a sala con enemigos dormidos | Escenario 4 | FR-027b |
| Pergamino durante un viaje | Escenario 4 | FR-031 |
| Sala inicial en el instante 0 | Escenario 1 | FR-002 |
| De avistada a explorada | Escenario 1 | FR-003, FR-004 |
| Guardar y cargar con conocimiento | Escenario 6 | FR-015 |
