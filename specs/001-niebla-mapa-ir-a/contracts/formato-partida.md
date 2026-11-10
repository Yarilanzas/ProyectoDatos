# Contrato: archivo de partida `CRPT`, versión 3

Cambia de la versión 2 a la **3** (FR-016, Principio VI). Es un contrato compartido: el README se actualiza en el
mismo cambio y se avisa al grupo.

**Disposición acordada con Persona D** (línea de tiempo y persistencia, spec 004), pregunta P-10 del plan, resuelta:
`[encabezado][jugador][conocimiento][línea de tiempo][salas][índice]`, en un solo salto a la versión 3.

## Disposición

El salto a la versión 3 lleva **dos bloques nuevos**: el de conocimiento (de esta capacidad, detallado abajo) y el de
línea de tiempo (de Persona D, que define su contenido). Ninguno de los dos justifica un salto de versión aparte. No se
mantienen archivos v3 intermedios: al integrar, las partidas guardadas se regeneran.

```text
v2: [encabezado][largo jugador][jugador]                                                                        [salas][índice]
v3: [encabezado][largo jugador][jugador][largo conocimiento][conocimiento][largo línea de tiempo][línea de tiempo][salas][índice]
```

El conocimiento va primero y la línea de tiempo después, antes de las salas. Encabezado, bloques de sala e índice no
cambian, salvo el número de versión.

- `largo conocimiento`: `<I`. Vale 0 si no hay conocimiento (solo los benchmarks de registros sueltos).
- `largo línea de tiempo` y su bloque: para esta capacidad el bloque es **opaco**: se salta con su largo, sin
  interpretar su contenido, hasta que Persona D publique su contrato (spec 004). El contenido lo define D.
- `_inicio_salas` suma los dos campos de largo y los dos bloques; la fórmula final la cierra D en su plan (spec 004).
- `_validar_encabezado` exige que el índice esté después de todos los campos de largo.

**Costo de las salidas**: el `CRPT` no lo guarda. Al cargar se toma del esqueleto, igual que la topología (decisión de
D).

## Bloque de conocimiento

Little endian y sin relleno, como el resto del archivo. Textos con largo `<H` + UTF-8, igual que `RegistroSala`.

```text
<I  cantidad de exploradas
    por cada una, en orden ascendente:
<I    id de sala

<I  cantidad de puertas recordadas
    por cada una, en orden (sala, dirección):
<I    id de la sala de origen
<H+s  dirección
<B    1 = abierta, 2 = cerrada

<I  cantidad de puertas reales
    por cada una, en orden (sala, dirección):
<I    id de la sala de origen
<H+s  dirección
<B    0 = abierta, 1 = cerrada
```

- **Exploradas** incluye las exploradas con antorcha, que no tienen bloque de sala.
- **Avistadas**: no se guardan; se recalculan con FR-004.
- **Puertas recordadas**: solo las observadas. Lo que no figura está «sin observar». Incluye salidas de salas no
  exploradas, cuando el jugador ya las observó desde la otra sala.
- **Puertas reales**: toda salida que hoy esté cerrada o que tenga llave o cierre automático, es decir, las únicas que
  pueden diferir del esqueleto.
- **Orden canónico**: el mismo estado produce los mismos bytes. Se ordena con `elegir_algoritmo`.

## Lectura

| Paso | Comportamiento |
|------|----------------|
| Versión distinta de 3 | `VersionIncompatible`, nada se carga, código de salida `2` (FR-016) |
| Partida sin bloque de conocimiento | `VersionIncompatible`, código `2` |
| Bloque truncado, valor de estado inválido o bytes sobrantes | `VersionIncompatible`, código `2` |
| Sala o dirección que no existe en la cripta | `VersionIncompatible`, código `2` |
| Sala del jugador no explorada | `VersionIncompatible`, código `2` |
| Correcto | El mapa queda idéntico al guardado (FR-015, SC-003) |

La lectura de `leer_conocimiento` es de una sola vez y no lee bloques de sala: la carga sigue siendo perezosa.

## Qué no se guarda

Igual que hoy: antorcha, veneno, velocidad, cierres automáticos pendientes e historial de retroceso, salvo lo que el
bloque de línea de tiempo de D defina guardar. El conocimiento ganado con la antorcha sí se conserva. `Viaje` no se
guarda. Tampoco el costo de las salidas: sale del esqueleto.

## `ExportadorJSON`

Agrega la clave `conocimiento` con los mismos tres campos, para que la comparación binario frente a JSON siga siendo
de los mismos datos.

## Archivos afectados

`partida.cripta` y `partida.cripta.log`, hoy versionados, usan formatos anteriores y dejan de cargarse. La
constitución dice que esos archivos no deberían versionarse.
