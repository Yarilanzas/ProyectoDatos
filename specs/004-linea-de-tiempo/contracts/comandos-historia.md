# Contrato: `historia`, `--replay --hasta` y `--checkpoint-cada`

Comandos y opciones en español, como los demás. Los **textos** de los avisos son propuesta de este plan y pueden ajustarse; las
**distinciones** entre casos, las combinaciones y los códigos de salida son contractuales. Cualquier cambio se refleja en el README y en
`AYUDA` (FR-010). Las opciones de `main.py` y los códigos de salida son contrato público (Restricciones técnicas de la constitución).

## Comando interactivo `historia`

| | |
|---|---|
| **Sintaxis** | `historia <t>` o `historia #<k>` |
| **Tiempo** | No consume, no cuenta como acción, no va a la bitácora ni al guion, no toca el historial de retroceso (FR-008) |
| **Disponible** | Mientras la partida está en curso. Tras terminar, el pasado se consulta con `--replay --hasta` |

- `<t>`: entero decimal sin signo (dígitos ASCII), `0 ≤ t ≤ reloj actual` (FR-003).
- `#<k>`: `#` seguido de un entero decimal sin espacios, `1 ≤ k ≤ acciones + 1`; con `k = acciones + 1` muestra el estado actual
  (FR-004). `k` cuenta acciones de la historia vigente (un paso de `ir a` es una acción).
- `t = reloj actual` muestra el estado actual. `historia 0` y `historia #1` muestran el estado inicial.

### Rechazos (FR-005, FR-009)

Ninguno consume tiempo, cuenta como acción ni se anota. Se distingue el error de uso (`mostrar_error`) del aviso (`mostrar_aviso`),
como `ir a`.

| Caso | Salida |
|------|--------|
| Sin argumento, no numérico, negativo, `#` sin número, `#` con decimales | error: `Use: historia <t> \| historia #<k>` |
| `t` mayor que el reloj actual | aviso: `No hay historia más allá del reloj actual (<reloj>).` |
| `#0` | aviso: `Las acciones se numeran desde 1.` |
| `#k` con `k` mayor que acciones + 1 | aviso: `La acción <k> no existe: la próxima acción es la <acciones+1>.` |
| La reconstrucción no se puede hacer (faltan datos locales, o el sello no coincide) | error: `No se pudo reconstruir ese momento: <causa>` |

### Salida (resumen histórico, FR-006)

Mismo texto para `historia` y para `--replay --hasta` (FR-007). Ejemplo (los valores son ilustrativos):

```text
Historia — instante 250
Sala 2: Pasillo
Vida: 34/40   Ataque: 6   Defensa: 1   Velocidad: 100
Equipo: arma Daga oxidada; armadura —
Inventario (4): Daga oxidada, Antorcha, Pergamino de retroceso x2
Efectos: veneno (2 de daño cada 80, hasta 400); antorcha encendida
Enemigos en la sala: e-rata-1 (8/8)
Mapa conocido:
  Sala 1: Entrada
    E -> sala 2   costo 100   abierta
  Sala 2: Pasillo
    O -> sala 1   costo 100   abierta
    E -> sala 3   costo 100   sin observar
Avistadas: 3
```

- Primera línea: `Historia — instante <t>` para `<t>`; `Historia — antes de la acción <k> (reloj <R>)` para `#<k>`;
  `Historia — estado actual (reloj <R>)` para el estado actual; `Historia — estado final (reloj <R>)` para el final de un replay.
- El **reloj** es el consultado (`<t>`), no el del último evento ejecutado.
- Los **pergaminos de retroceso** son los que el jugador tenía en ese momento (FR-029), aunque después se hayan gastado.
- `Efectos: ninguno` si no hay. `Enemigos en la sala: ninguno` si no hay vivos.
- El bloque `Mapa conocido:` es el texto del comando `mapa` de la capacidad 001, sin recalcular con información posterior (FR-006).
- Si el estado es el final de una partida terminada, se agrega `Resultado: victoria` o `Resultado: derrota`.
- El contenido **no depende de K** (FR-028).

## `--replay <bitácora> --hasta <t>`

Reproduce la bitácora **completa**, sin instanciar la vista (Principio II), e imprime el resumen del instante `<t>` en la historia
vigente. El reloj con `@cargar` está definido en [formato-bitacora.md](formato-bitacora.md).

Salida: solo el resumen (sin `Reproducción finalizada.` ni estado ni puntaje). Código `0`.

| Caso | Salida |
|------|--------|
| `t` ≤ reloj final | el resumen de `<t>` |
| `t` > reloj final (FR-012) | primero `La partida termina antes del instante <t> (la bitácora acaba en el reloj <final>): se muestra el estado final.` y luego el resumen del estado final |
| `t` = reloj final | el resumen del estado final, sin aviso |

## Opciones

| Opción | Argumento | Efecto |
|--------|-----------|--------|
| `--hasta T` | entero ≥ 0 | Modificador de `--replay`: imprime el estado en el instante `T` (FR-011) |
| `--checkpoint-cada K` | entero ≥ 1 | Máximo de acciones entre puntos de control de la partida o del replay (FR-018). Por defecto **50** (**HIPÓTESIS** hasta M1 y M2) |

Los dos se leen como **texto** y se validan a mano: `argparse` con `type=int` terminaría con código `2`, reservado a «versión
incompatible» (research HL11).

### Validación (antes de ejecutar nada; código `1`, FR-013, FR-018)

| Caso | Mensaje |
|------|---------|
| `--hasta` no entero o negativo | `! Error: --hasta requiere un entero mayor o igual que 0 (recibido: <texto>).` |
| `--checkpoint-cada` no entero, 0 o negativo | `! Error: --checkpoint-cada requiere un entero mayor o igual que 1 (recibido: <texto>).` |
| `--hasta` sin `--replay` en la línea de comandos | `! Error: --hasta solo se puede usar junto con --replay.` |
| `--checkpoint-cada` junto con `--cargar` (y `--replay` no manda) | `! Error: --checkpoint-cada no se puede usar al cargar una partida: rige el valor guardado en el archivo.` |

Se valida **antes** de abrir la fuente de datos, de crear el gestor o de leer cualquier archivo: no se reproduce ni se carga nada.

### Combinaciones con la prioridad de la capacidad 002

La tabla `--bench > --mostrar-puntajes > --verificar > --replay > --cargar > --cripta / lista` **no cambia**: `--hasta` y
`--checkpoint-cada` son modificadores, no modos. (README y [cli-verificacion.md](../../002-resolubilidad/contracts/cli-verificacion.md)
de B: sin cambios salvo una nota; ver el plan.)

| Línea de comandos | Resultado |
|-------------------|-----------|
| `--bench` con cualquier otra opción, incluidas las nuevas (también inválidas) | corre las mediciones; ignora todo, sin validar |
| `--mostrar-puntajes --replay F --hasta 5` | muestra puntajes; `--replay` y `--hasta` se ignoran |
| `--mostrar-puntajes --hasta 5` (sin `--replay`) | error de uso, código `1` |
| `--mostrar-puntajes --checkpoint-cada 10` | muestra puntajes; `--checkpoint-cada` se ignora |
| `--verificar X --replay F --hasta 5` | verifica X; `--replay` y `--hasta` se ignoran |
| `--verificar X --hasta 5` (sin `--replay`) | error de uso, código `1` |
| `--verificar X --forzar --checkpoint-cada 10` | verifica; `--forzar` y `--checkpoint-cada` se ignoran |
| `--replay F --hasta T` | reproduce y muestra el estado en `T`; `--cargar`, `--cripta`, `--semilla`, `--forzar` se ignoran |
| `--replay F --hasta T --checkpoint-cada K` | igual; K solo cambia el costo (FR-028) |
| `--replay F --checkpoint-cada K` (sin `--hasta`) | replay normal de la capacidad 001; K no tiene efecto (no se construye línea) |
| `--replay F --cargar G --checkpoint-cada K` | gana `--replay`, `--cargar` se ignora, K es válido |
| `--cargar F --checkpoint-cada K` | error de uso, código `1`, sin cargar nada (FR-031) |
| `--cargar F --hasta T` (sin `--replay`) | error de uso, código `1` |
| `--cargar F` | carga; la línea se reconstruye con el K del archivo (si faltan datos locales: error, código `1`, nada cargado) |
| `--cargar F --bitacora F.log` | `! Error: la bitácora no puede ser F.log, que es la copia de bitácora de la partida guardada; use otra con --bitacora`, código `1`, sin cargar nada (hecho por C, `b6f9f52`). El comando `guardar` con esa bitácora, dentro de la partida, solo se rechaza y la partida sigue |
| `--cripta X --checkpoint-cada K` (o menú) | partida nueva con ese K |
| `--cripta X --forzar --checkpoint-cada K` | verificación en silencio, partida nueva con ese K |

El comando interactivo `cargar` adopta el K del archivo sin error: FR-031 se refiere a la línea de comandos.

### Orden de evaluación en `main.py`

1. `--bench` → mediciones y fin.
2. Leer `--hasta` y `--checkpoint-cada` como texto y validar sus valores (código `1`).
3. Reglas de combinación de la tabla (código `1`).
4. Modos por prioridad: `--mostrar-puntajes`, `--verificar`, `--replay` (con o sin `--hasta`), `--cargar`, `--cripta`.

## Cargar sin datos locales

Cargar una partida reproduce su guion con el gestor sin red (research R8 y R10). Si falta un dato local que el disco debería tener
(carpeta de datos locales borrada o de otra versión, paquete offline ausente):

| Caso | Resultado |
|------|-----------|
| `--cargar F` | `! Error: No se puede reconstruir sin nuevas solicitudes: faltan datos locales (<qué>)`, código `1`; **no se carga nada**, no se abre la partida ni se gasta presupuesto |
| comando `cargar` dentro de una partida | `No se pudo cargar: No se puede reconstruir sin nuevas solicitudes: faltan datos locales (<qué>)`; la partida en curso, su bitácora y su línea quedan intactas |
| `--replay F` con `@cargar` | igual que `--cargar`: código `1` |

Alternativas descartadas (cargar sin línea, reconstruir después, usar la red) y el motivo: [research R8](../research.md#r8-persistencia-de-la-línea-fr-022-fr-023-fr-024-fr-025-fr-031).
`SinDatosParaHistoria` debe ser una subclase de `RuntimeError` para que `main.py` la atrape con las excepciones que ya convierte en el
código `1` (hoy `ValueError`, `RuntimeError` y `OSError`). Se distingue de «Versión incompatible» (código `2`): faltar datos locales no es una
versión distinta.

## Códigos de salida

| Situación | Código |
|-----------|--------|
| `--replay --hasta` correcto, también con `T` mayor que el final | `0` |
| Valor o combinación de opciones inválidos (errores de uso de arriba) | `1` |
| `ErrorReconstruccion`, `SinDatosParaHistoria` (también al cargar: nada se carga), acción rechazada por el replay, otros errores | `1` |
| `--cargar F --bitacora F.log` ([formato-bitacora.md](formato-bitacora.md#bitácora-igual-a-guardadolog)) | `1` (en la partida, `guardar` y `cargar` solo rechazan el comando) |
| Bitácora, archivo de partida, cripta o catálogo de versión incompatible; línea que no coincide con la partida | `2` con `Versión incompatible: ...` |

No se crean códigos nuevos.

## Ayuda y README (FR-010)

`AYUDA` agrega:

```text
  historia <t>       Muestra el estado en el instante t (sin cambiar la partida)
  historia #<k>      Muestra el estado justo antes de la acción k
  (línea de comandos) --hasta T con --replay; --checkpoint-cada K
```

El README agrega las dos opciones a la tabla de opciones, el comando `historia` a la de comandos, el `CRPT` 3 con la línea, y la nota de
que `retroceder` y `historia` son mecanismos distintos (research R12).
