# Contrato: bitácora `CRIPTA-LOG`, versión 2

Cambia de la versión 1 a la **2** (FR-030, Principio VI). Sigue siendo texto de solo agregar. Es un contrato
compartido: el README se actualiza en el mismo cambio y se avisa al grupo.

## Tipos de línea tras el separador `---`

| Primer carácter | Tipo | Ejemplo | `--replay` |
|-----------------|------|---------|------------|
| `#` | Comentario | `# ir a 7` | Lo ignora (FR-030) |
| `@` | Directiva | `@cargar` | La ejecuta |
| Otro | Acción | `mover E` | La ejecuta, igual que en v1 |

Las líneas vacías se siguen ignorando. Una directiva desconocida es un error: no se puede garantizar una reproducción
fiel. Se rechaza con `VersionIncompatible` (código `2`).

## Comentario de «ir a» (FR-030)

```text
CRIPTA-LOG 2
cripta_id=cripta-test
version_cripta=v1
version_catalogo=cat-1
semilla=7
---
mover E
# ir a 3
mover O
mover S
```

- Va **inmediatamente antes** de la línea del primer paso.
- Se escribe después de que el motor acepte ese paso. Una orden rechazada no deja ninguna línea (FR-022, SC-005).
- Cada paso aceptado es una línea `mover` normal. Es lo único que reproduce el replay.
- Un viaje detenido deja solo los pasos dados.
- Un `retroceder` posterior es una línea `retroceder` normal.

## Directiva `@cargar` (FR-017)

```text
---
mover E
atacar e-rata-1
@cargar
esperar
```

- La escribe `_continuar_bitacora` al continuar una partida cargada, después de copiar la bitácora del guardado.
- `guardar` no anota nada.
- La bitácora activa nunca es la copia del guardado: `--bitacora` igual a `<guardado>.log` es un error de uso, al
  cargar (código `1`, antes de jugar) y al guardar (no se escribe nada). Así `_continuar_bitacora` siempre copia y la
  bitácora guardada termina exactamente en el guardado (FR-017, pedido de Persona D, FR-030 de la spec 004). Ver
  [comandos.md](comandos.md).
- Si la partida no tiene bitácora, no hay nada que anotar: se conserva el aviso actual.
- `--replay`, al llegarle, guarda el motor en un archivo temporal, lo carga con `cargar_partida` y sigue con el
  motor resultante. Repite así lo que la carga real cambió: azar, agenda, efectos e Historial.
- La recarga del replay **no** ejecuta la verificación de resolubilidad (`--verificar`, FR-022 de la spec 002).
- **Reloj y `--replay --hasta t`** (condición (b) de P-07): queda cubierta por la regla de Persona D, FR-030 de la
  spec 004. El reloj es global y continuo: tras `@cargar` sigue desde el reloj del archivo cargado, y lo jugado entre
  ese guardado y la carga no existe en la línea, de modo que cada `t` identifica un único momento. Ver
  [specs/004-linea-de-tiempo/contracts/formato-bitacora.md](../../004-linea-de-tiempo/contracts/formato-bitacora.md).

## Lectura

| Caso | Comportamiento |
|------|----------------|
| `CRIPTA-LOG 1` | Se rechaza: `VersionIncompatible`, código `2` |
| `leer_bitacora` | Omite comentarios y devuelve `@cargar` como `("@cargar", "")` dentro de `acciones` |
| `Reproductor` sin `recargar` y con `@cargar` en la bitácora | Error, no se ignora en silencio |

## API

```text
BitacoraPartida.comentar(texto)   escribe "# <texto>"; valida como las demás líneas
BitacoraPartida.marcar_carga()    escribe "@cargar"
Reproductor(fabrica_motor, version_cripta, version_catalogo, recargar=None, observador=None)
```

### Observador y reproducción en memoria (pedido de Persona D, P-D02 de la spec 004)

Cambio exacto en [specs/004-linea-de-tiempo/plan.md, «Enganches»](../../004-linea-de-tiempo/plan.md#enganches-y-requisitos-hacia-otras-personas).
Tareas T123 a T125.

```text
Reproductor(fabrica_motor, version_cripta, version_catalogo, recargar=None, observador=None)
Reproductor.reproducir_acciones(encabezado, acciones) -> motor   reproduce una lista en memoria
Reproductor.reproducir(ruta) -> motor                            solo lee la bitácora y llama a reproducir_acciones
```

- `encabezado` y `acciones` son exactamente lo que devuelve `leer_bitacora`. Las comprobaciones de versión de cripta y
  de catálogo, y la de la cripta del motor creado, pasan a `reproducir_acciones`: valen igual para una lista en
  memoria.
- Si hay `observador`, el `Reproductor` lo avisa en tres puntos, siempre en el orden en que ocurren:

  | Momento | Llamada |
  |---------|---------|
  | Tras crear el motor con `fabrica_motor` y comprobar su cripta | `observador.al_crear_motor(motor)` |
  | Tras cada `ejecutar_accion` que no devolvió `False` (incluido `retroceder`) | `observador.despues_de_accion(motor, nombre, argumento)` |
  | Tras `motor = self._recargar(motor)` en un `@cargar`, ya comprobado que no es `None` | `observador.despues_de_carga(motor)`, con el motor **nuevo** |

- Una acción rechazada sigue deteniendo la reproducción con error, sin avisar al observador. Un `@cargar` sin
  `recargar`, o con `recargar` que devuelve `None`, da error sin llamar a `despues_de_carga`.
- `recargar` cierra el motor anterior: el observador no debe guardar referencias a él.
- **Sin observador, el comportamiento es idéntico al actual**: mismos resultados, mismos errores y mismos mensajes.

`registrar` sigue rechazando nombres con espacios. Además debe rechazar nombres que empiecen con `#` o `@`, para que
una acción nunca se confunda con otro tipo de línea.

## Cambios en lo que hoy está documentado

| Lugar | Hoy | Después |
|-------|-----|---------|
| README, «Bitácora» | Ejemplo `CRIPTA-LOG 1`; `cargar` no se anota | Ejemplo v2; `@cargar` y comentarios documentados |
| `tests/test_bitacora.py` | Usa `CRIPTA-LOG 2` como versión inválida | Debe usar `VERSION_BITACORA + 1` |
| `tests/test_bitacora.py` | Literales `CRIPTA-LOG 1` para probar encabezados dañados | Deben usar la versión vigente |
| `partida.log`, `partida.cripta.log` | v1, versionados | Quedan obsoletos: regenerar si sirven de evidencia |
