# Contrato: opciones `--verificar` y `--forzar`, salida y códigos

**FR**: FR-006 a FR-024, FR-031 | Contrato público (Restricciones técnicas): cambiarlo exige README y pruebas en el mismo cambio.

## Opciones nuevas

| Opción | Argumento | Efecto |
|--------|-----------|--------|
| `--verificar ID` | id de cripta | Solo verifica y muestra el resultado; no inicia partida ni crea bitácora, partida guardada o puntajes |
| `--forzar` | — | Al iniciar una partida nueva, la inicia aunque no sea resoluble y sin mostrar el orden ni el reporte. La verificación se ejecuta igual |

## Prioridad de opciones (FR-017)

```text
--bench  >  --mostrar-puntajes  >  --verificar  >  --replay  >  --cargar  >  --cripta / lista interactiva
```

| Combinación | Resultado |
|-------------|-----------|
| `--verificar X --forzar` | solo verifica, resultado completo (US4.3) |
| `--verificar X --cripta Y` | verifica X; no inicia nada |
| `--cargar F --forzar`, `--replay F --forzar` | `--forzar` se ignora; sin verificación (FR-022) |
| `--cripta X --forzar` | verifica en silencio; inicia siempre que los datos se puedan obtener |

## Códigos de salida

| Situación | Código |
|-----------|--------|
| `--verificar`: verificación completa, resoluble o no | 0 |
| Partida nueva resoluble, o forzada | lo que devuelva la partida (0 normal) |
| Partida nueva no resoluble sin `--forzar` | 1 |
| No se pudo obtener la ubicación de las llaves, los detalles o las salas (con o sin `--forzar`) | 1 |
| `--verificar` con cripta inexistente | 1 |

No se crean códigos nuevos (spec, Assumptions).

## Mensajes de error

Todos con el formato existente `! Error: <texto>` de `VistaConsola.mostrar_error`.

| Caso | Texto (prefijo fijo; lo que sigue a `:` sale de la excepción) |
|------|------|
| Rechazo de partida (FR-020) | `! Error: La cripta <id> no es resoluble. Usa --forzar para jugarla de todos modos.` y a continuación el reporte |
| Presupuesto agotado (US5.2) | `! Error: Se agotó el presupuesto de solicitudes (<n>) al consultar <url>` |
| Error del servicio (US5.1) | `! Error: El servicio respondió <código> al consultar <url>...` |
| Falta el archivo offline (US5.3) | `! Error: Falta el archivo para /criptas/<id>/llaves: <ruta>` |
| Entrada de llave incompleta | `! Error: Respuesta inválida de /criptas/<id>/llaves: ...` |

En los casos de error no se muestra veredicto.

## Formato de la salida

La salida es texto fijo; dos ejecuciones sobre la misma cripta dan el mismo texto carácter por carácter (FR-012). Los
nombres de llaves y salas son los de la fuente; los ejemplos usan datos ficticios.

### Resoluble (FR-006, FR-007)

```text
La cripta cripta-x es resoluble.
Orden de obtención de llaves:
  1. llave_c (oleada 1)
  2. llave_d (oleada 1)
  3. llave_a (oleada 2) <- llave de salida
```

### No resoluble (FR-008 a FR-011, FR-014)

```text
La cripta cripta-x no es resoluble.
Llaves no obtenibles:
  - llave_k1
  - llave_k2
  - llave_salida_x
Frontera bloqueada:
  - sala 3 (E) -> sala 7: requiere llave_k1
  - sala 5 (N) -> sala 9: sin llave
Puerta hacia la sala de salida (sala 12, requiere llave_salida_x):
  - sala 11 (S) -> sala 12: bloqueada
Ubicación de las llaves:
  - llave_k1: sala 8
  - llave_k2: sala 7; sala 15 (la suelta e-40)
  - llave_salida_x: ubicación desconocida
Dependencias entre llaves:
  - llave_k1 -> llave_k2
  - llave_k2 -> llave_k1
  - llave_salida_x: sin dependencia
Ciclos de llaves:
  - llave_k1 -> llave_k2 -> llave_k1
```

Variantes de cada sección:

| Sección | Texto alternativo |
|---------|-------------------|
| Resoluble sin ninguna llave obtenible (bloque «Resoluble») | `Orden de obtención de llaves: ninguna.` (sin líneas numeradas debajo) |
| La cripta no declara `llave_salida` (Edge Cases) | La sección «Puerta hacia la sala de salida» no aparece, porque no se exige puerta de salida |
| Frontera vacía (Edge Cases) | `Frontera bloqueada: ninguna (no hay puertas cerradas que salgan de la región alcanzable).` |
| Destino inexistente | `- sala 3 (E) -> sala 99 (no existe): requiere llave_k1` |
| Sin puerta de salida (US1.6) | `Puerta hacia la sala de salida: no existe ninguna salida hacia la sala 12 que requiera llave_salida_x.` |
| Ubicación en sala inexistente | `- llave_k1: sala 99 (no existe)` |
| Ciclo directo (US2.2) | `- llave_k -> llave_k (ciclo directo)` |
| Sin ciclos | `Ciclos de llaves: ninguno.` |

Reglas de orden: llaves por identificador; puertas por sala de origen y luego dirección N, S, E, O (otras después, por
texto); ubicaciones por sala y luego enemigo; cada ciclo empieza por su menor llave y los ciclos se ordenan por esa
llave (FR-014).

### Al iniciar una partida

| Veredicto | Sin `--forzar` | Con `--forzar` |
|-----------|----------------|----------------|
| Resoluble | bloque «Resoluble» y la partida inicia | nada; la partida inicia |
| No resoluble | mensaje de error + bloque «No resoluble», código 1, sin bitácora | nada; la partida inicia |
| Error de datos | `! Error: ...`, código 1 | `! Error: ...`, código 1 |
