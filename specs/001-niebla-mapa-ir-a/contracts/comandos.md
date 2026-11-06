# Contrato: comandos `mapa` e `ir a <sala>`

Comandos de consola, en español, igual que los demás. Los textos de los avisos son la propuesta de este plan; pueden
ajustarse, pero las **distinciones** entre casos son contractuales. Cualquier cambio se refleja en el README y en
`AYUDA` (FR-020).

## `mapa`

| | |
|---|---|
| **Sintaxis** | `mapa` (sin argumentos) |
| **Tiempo** | No consume, no cuenta como acción, no va a la bitácora (FR-019) |
| **Muestra** | Salas exploradas y salas avistadas, solo desde el conocimiento (FR-012, FR-018) |

Salida con esta estructura. Salas por id ascendente; `estado` es `abierta`, `cerrada` o `sin observar`:

```text
Mapa conocido:
  Sala 1: Entrada
    E -> sala 2   costo 100   abierta
  Sala 2: Pasillo
    O -> sala 1   costo 100   abierta
    E -> sala 3   costo 100   sin observar
    S -> sala 5   costo 100   sin observar
Avistadas: 3, 5
```

- Una sala avistada solo aparece por su id, ni nombre ni salidas (FR-005).
- Las salas desconocidas no aparecen como entrada propia. Sí puede verse el id de una sala avistada como destino.
- No se muestra llave, enemigos, trampas ni objetos (FR-010, FR-018).
- `Avistadas: ninguna` si la lista está vacía.

## `ir a <sala>`

| | |
|---|---|
| **Sintaxis** | `ir a <sala>`, donde `<sala>` es el id que la pantalla muestra en «Sala N» (FR-021) |
| **Tiempo** | Cada paso es un `mover`: mismo costo, cuenta como acción y corren todos los eventos (FR-025) |
| **Bitácora** | Ver [formato-bitacora.md](formato-bitacora.md) |

### Rechazos (FR-022)

Ninguno consume tiempo, cuenta como acción ni escribe en la bitácora (SC-005).

| Caso | Aviso propuesto |
|------|-----------------|
| Sala inexistente, desconocida, avistada o id no válido | `No conoces esa sala.` |
| Es la sala actual | `Ya estás en esa sala.` |
| Explorada, sin ruta conocida | `No conoces una ruta hasta esa sala.` |
| `ir` sin `a`, o sin sala | Error de uso: `Use: ir a <sala>` |

El primer caso **debe** dar un único mensaje: distinguirlo revelaría si la sala existe (caso borde de la spec).

### Cómo se calcula cada paso

Antes de **cada** paso se recalcula la ruta con el conocimiento vigente (FR-026), por la
[interfaz de ruta](interfaz-ruta.md). Solo cuentan salas exploradas y salidas recordadas abiertas (FR-023). Las
salidas cerradas o sin observar no se usan, y una puerta nunca se abre, aunque se tenga la llave (FR-011, FR-029).

La orden se acepta aunque haya enemigos en la sala actual (FR-028).

### Paradas (FR-027)

Siempre se informa un motivo. Si coinciden varios, se informa por el orden de la tabla.

| Prioridad | Condición | FR | Aviso propuesto |
|-----------|-----------|----|-----------------|
| 1 | La partida termina | FR-027e | Lo muestra el flujo normal de fin de partida |
| 2 | Perdió vida durante el paso | FR-027c | `Viaje detenido: recibiste daño.` |
| 3 | Entró a una sala con enemigos vivos | FR-027b | `Viaje detenido: hay enemigos en la sala.` |
| 4 | Llegó al destino | FR-027a | `Llegaste a la sala <id>.` |
| — | Ya no hay ruta conocida | FR-027d | `Viaje detenido: ya no conoces una ruta.` |

`Sin ruta` se evalúa al recalcular, antes de un paso, por lo que no consume tiempo y no compite con las demás.

**Pendiente**: un paso rechazado por el motor no está en FR-027. Ver pregunta P-04 del plan.

### Después del viaje

- El viaje no se guarda ni se reanuda.
- `retroceder` deshace solo el último paso (FR-031).

## Comandos existentes

| Elemento | Cambio |
|----------|--------|
| `Salidas:` de la pantalla de estado | Se muestra el estado recordado (FR-012) |
| Mensaje «Una puerta se cerró sola.» | Solo si el jugador observa la puerta (FR-007, FR-012) |
| `ayuda` | Agrega `mapa` e `ir a <sala>` (FR-020) |
| Demás comandos | Sin cambios |
