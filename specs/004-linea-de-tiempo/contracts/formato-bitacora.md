# Contrato: bitácora `CRIPTA-LOG` 2 y el reloj de `--hasta` con `@cargar`

**Urgente para la persona C.** Completa la **condición (b) de P-07** (`--replay --hasta t` cuenta el reloj a través de las líneas
`@cargar`) y precisa FR-030. Es un contrato compartido: se avisa al grupo antes de cambiar nada.

## Esta capacidad no cambia el formato de la bitácora

`CRIPTA-LOG 2` (capacidad 001, [formato-bitacora.md](../../001-niebla-mapa-ir-a/contracts/formato-bitacora.md)) queda **tal cual**:
mismas líneas (`#` comentario, `@cargar` directiva, el resto acciones), mismo encabezado. La capacidad 004 **no agrega líneas, campos ni
versión**:

- `K` (`--checkpoint-cada`) y `--hasta` **no** se escriben en la bitácora.
- Los sellos (reloj y secuencia) **no** se escriben: se recalculan al reproducir.
- `historia` **no** se anota (FR-008).

Lo que sí hace falta es dejar escrito **cómo se interpreta el reloj**.

## El reloj de `--hasta`

`--replay <bitácora> --hasta <t>` interpreta `<t>` como el **reloj virtual del motor**, `motor.reloj`, tal como lo produce la
reproducción. Es global y continuo en la historia vigente (FR-030):

1. **`@cargar` no avanza ni reinicia el reloj.** Guardar ocurre siempre en un punto de decisión, y `cargar_partida` fija
   `motor.reloj = encabezado.reloj`; por eso, tras `@cargar`, el reloj sigue desde el del archivo cargado, que es el del punto de guardado.
2. **Lo jugado entre ese guardado y la carga no existe en la línea**: la bitácora que se continúa es la copia hecha al guardar
   (`_continuar_bitacora`), así que esas acciones ya no están en el archivo. Cada `<t>` identifica un único momento. **Sin
   excepciones**, porque el caso en que la bitácora en uso es el propio `<guardado>.log` se rechaza en el origen (ver
   [Bitácora igual a `<guardado>.log`](#bitácora-igual-a-guardadolog)).
3. **`<t>` se resuelve contra la historia vigente completa** (no contra el punto de la bitácora donde se paró de leer): se reproduce
   la bitácora entera y después se consulta `<t>`. Así un `retroceder` o un `@cargar` posterior a `<t>` se refleja (US4.3, US4.6).
4. **En el instante exacto de una carga** (`<t>` igual al reloj de `@cargar`) rige el **estado cargado**: ese instante es la decisión
   actual del motor cargado, que reemplaza a la del guardado (efectos temporales perdidos, azar resembrado; ver research R7).
   Para un `<t>` dentro de la acción anterior al guardado se usa el estado anterior al guardado.
5. Un `<t>` mayor que el reloj final de la reproducción muestra el estado final con el aviso de FR-012. El «final» es el resultado de
   reproducir la bitácora completa (FR-012).

### Ejemplo

```text
CRIPTA-LOG 2
cripta_id=cripta-test
version_cripta=v1
version_catalogo=cat-1
semilla=7
---
mover E        decisión 1 en el reloj   0   (la acción cuesta 100)
esperar        decisión 2 en el reloj 100
@cargar        se había guardado en la decisión 3 (reloj 200); lo posterior al guardado no está
esperar        decisión 3 en el reloj 200 (la del motor cargado)
```

| Consulta | Resultado |
|----------|-----------|
| `--hasta 0` | Decisión 1: estado inicial |
| `--hasta 150` | Dentro de la acción 2 (`esperar`): estado anterior al guardado, con los eventos hasta 150 |
| `--hasta 200` | Decisión 3 **del motor cargado** (regla 4) |
| `--hasta 300` | Dentro de la acción 3, estado posterior a la carga |
| `--hasta 99999` | Estado final con el aviso de FR-012 |

## Qué hace `--replay` con `--hasta` (para `Reproductor` y `ejecutar_replay`)

Sigue siendo `Reproductor` (T093, ya en `main`): valida versiones, crea el motor con `preparar_partida`, ejecuta cada acción y, al llegar
a `@cargar`, llama a `recargar(motor)`, que **recibe el motor actual y devuelve el nuevo** (en `main.ejecutar_replay`: guarda el motor
en un temporal, cierra su restaurador y llama a `cargar_partida`, T094). La línea de tiempo **observa** el recorrido mediante un
parámetro opcional `observador` de `Reproductor` (**hecho por C**, `b1b57d7`, 001-T123/T124; contrato en [001 formato-bitacora.md](../../001-niebla-mapa-ir-a/contracts/formato-bitacora.md), «Observador y reproducción en memoria»), junto con `reproducir_acciones(encabezado, acciones) -> motor` y `reproducir(ruta) -> motor`:

```text
Reproductor(fabrica_motor, version_cripta, version_catalogo, recargar=None, observador=None)    # firma real + observador

observador.al_crear_motor(motor)                          tras fabrica_motor
observador.despues_de_accion(motor, nombre, argumento)    tras cada acción que el motor aceptó (incluido 'retroceder')
observador.despues_de_carga(motor)                        tras motor = recargar(motor): recibe el motor NUEVO que devolvió recargar
```

`recargar(motor)` recibe el motor **actual** (el que la línea ya observó hasta ese punto) y devuelve el **nuevo**; el observador solo
ve el nuevo, y por eso no guarda referencias al motor anterior (que `recargar` ya cerró). Sin `observador`, `Reproductor` se comporta
exactamente como hoy. `--replay` sin `--hasta` no construye línea. El `Reproductor` ya avisa `despues_de_carga` tras cada `@cargar`, así que la recarga de `main.ejecutar_replay` **no** avisa al observador (se evita el doble aviso). La consulta de `--hasta` se hace dentro del `try` de `ejecutar_replay`, mediante un callback `al_terminar(motor)`, antes de que cierre los restauradores y borre la carpeta temporal.

## Condiciones de P-07

| Condición | Estado |
|-----------|--------|
| (a) `@cargar` queda escrito en `contracts/formato-bitacora.md` | Cumplida por la capacidad 001 |
| **(b) `--replay --hasta t` cuenta el reloj a través de `@cargar`** | **Cumplida por este documento** (reglas 1 a 5) |
| (c) Versión incompatible: código `2` | Sin cambios; `--replay --hasta` conserva el rechazo (FR-011) |
| (d) README actualizado | Pendiente de T113 (001, sigue sin hacerse) y de la tarea de README de esta capacidad (PR-15) |

## Bitácora igual a `<guardado>.log`

**Hecho por C** (`b6f9f52`, 001-T120/T121): si `--bitacora` es la misma ruta que `<guardado>.log` (`ruta_bitacora_de(ruta)`, comparada con
`_misma_ruta`), **se rechaza en el origen** como error de uso (`ValueError` de `_rechazar_bitacora_del_guardado`), sin guardar ni cargar nada. Con `--cargar F --bitacora F.log` el proceso termina con `! Error: ...` y código `1`; con el comando `guardar` o `cargar` dentro de la partida se muestra el error (`No se pudo guardar: ...` / `No se pudo cargar: ...`) y la partida sigue. Mensaje real:

```text
! Error: la bitácora no puede ser <guardado>.log, que es la copia de bitácora de la partida guardada; use otra con --bitacora
```

**El problema.** `_continuar_bitacora` (y `guardar`) no copian el archivo cuando la bitácora en uso es el propio `<guardado>.log`:
`_misma_ruta(copia, self.ruta_bitacora)`. Si se sigue jugando entre guardar y cargar con `--bitacora` igual a ese `.log`, la bitácora **conserva**
las acciones posteriores al guardado. Al cargar, el replay las reproduce y el guion de la línea no las tiene (la carga repone el estado
del guardado): el replay **no coincide** con la línea. Es la limitación señalada por la persona C.

**Por qué rechazar y no solo documentar.** Documentarlo dejaría una excepción a la regla 2 («lo jugado entre el guardado y la carga no
existe en la línea») y obligaría a que cada `<t>` pudiera nombrar dos momentos distintos según cómo se invocó el programa. Con eso:

- **FR-025** (la línea del replay MUST ser igual a la jugada) se rompería para ese caso: el replay y la partida jugada divergirían sin
  que nada lo detecte ni lo avise.
- **FR-030** (el reloj de `--hasta` cuenta de forma única a través de `@cargar`) también: un mismo `<t>` caería en dos momentos, el jugado
  y el descartado.
- Un aviso al jugador no basta: la divergencia aparece después, en otro proceso (`--replay`), lejos de la causa.

Rechazar en el origen cuesta una comparación de rutas y no cambia ningún formato. Cierra la excepción: la regla 2 vale sin excepciones.
Se aplica en `guardar` y en `cargar` (también `--cargar F --bitacora F.log`). `ruta_bitacora_de` y `_misma_ruta` ya existen en
`Controlador/ControladorPartida.py`.

## Relación entre el guion de la línea y la bitácora

La bitácora y el guion de la línea (research R3) llevan **los mismos comandos aceptados, en el mismo orden y con el mismo texto**; se
anotan en el mismo punto del controlador (`_accion`), así que no se desfasan. El guion añade los sellos y las fronteras de carga, y
existe aunque la partida no tenga bitácora. Reproducir cualquiera de los dos da la misma partida.

## Errores

| Caso | Resultado |
|------|-----------|
| Bitácora de versión incompatible (`CRIPTA-LOG 1`, o de cripta o catálogo distintos) con `--hasta` | `Versión incompatible: ...`, código `2` (FR-011) |
| La reproducción rechaza una acción | `! Error: La reproducción se detuvo: ...`, código `1` (como hoy) |
| La línea no coincide en un replay (sello distinto) | `! Error: La reproducción no es determinista en la acción <k>: ...`, código `1` |
| `--bitacora` igual a `<guardado>.log` al guardar o cargar | `ValueError`, nada se guarda ni se carga: con `--cargar` el proceso termina con código `1`; con el comando `guardar`/`cargar` la partida sigue (sección anterior) |
| `@cargar` en el replay y faltan datos locales para recargar | `! Error: No se puede reconstruir sin nuevas solicitudes: faltan datos locales (<qué>)`, código `1` |
