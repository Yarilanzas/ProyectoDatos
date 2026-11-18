# Revisión T117 (solo lectura, 2026-11-16)

> **Estado al 2026-11-17.** H1 (`cargar` no atómico): resuelto en T085. H2 (`--bitacora` igual al guardado): resuelto por C en `f592da4`. H3 (README contradecía el formato): resuelto por C en `142109b` y posteriores. H4 (llenar el bloque de la línea): resuelto en T070 a T085. H5 (`ErrorReconstruccion` y `ReferenciaInvalida` sin atrapar): resuelto en T086. H6 a H14 son mejoras que no bloquean la entrega.
**Alcance**: cambios de C (capacidad 001) en `Modelo/`, `Persistencia/`, `Bitacora/` y `main.py`, más `Controlador/ControladorPartida.py` porque ahí vive el rechazo de `--bitacora`.
Apoyo: `specs/001-niebla-mapa-ir-a/trazabilidad.md` y `.specify/memory/constitution.md`.
No se modificó ningún archivo versionado ni se hizo pull, commit ni push.
Los experimentos (3, abajo) corrieron en carpetas temporales con scripts del scratchpad.
La suite está en verde (819 pruebas, OK, medido en el informe anterior).

No hice una revisión línea por línea de `Conocimiento`, `Viaje`, `rutas_ir_a` ni `GrafoConocido`: me centré en los seis puntos pedidos.

## Resumen

| Gravedad | Hallazgo | Clasificación |
|----------|----------|---------------|
| Alta | H1: `cargar` no es atómico: un fallo tras `cargar_partida` deja la partida reemplazada (reproducido) | **Bloquea** (se arregla con T085) |
| Alta | H2: `--cargar G --bitacora G` sobrescribe el guardado con la bitácora (reproducido) | **Bloquea** (2 líneas) |
| Alta | H3: el README contradice el formato (`CRPT` 3, `CRIPTA-LOG` 2, `@cargar`, conocimiento guardado, prioridad con `--verificar`) | **Bloquea** (documental, Principio VI) |
| Alta | H4: lo que hay que cambiar para llenar el bloque de la línea (T070 a T085) | **Bloquea T070 a T085** (trabajo tuyo, no defecto de C) |
| Media | H5: `ErrorReconstruccion` y `ReferenciaInvalida` no las atrapa `main.py` | Con T086 |
| Media | H6: una partida nueva con `--bitacora <guardado>.log` pisa la copia de bitácora de un guardado | Mejora |
| Media | H7: bitácora de copia no validada contra el guardado, y `.log` viejo tras guardar sin bitácora | Mejora |
| Media | H8: pruebas que faltan (ver sección 5) | Mejora; cuatro entran en T063a, T065, T077, T080 |
| Baja | H9 a H14: comparación de rutas, doble lectura en el replay, `print` en `Modelo/`, dicts de constantes, IDs en pruebas, JSON sin versión | Mejora |

## 1. Formato CRPT v3 con el bloque de la línea en largo 0

**Cómo está hoy (correcto)**

- `Persistencia/FormatoBinario.py:9` fija `VERSION_FORMATO = 3`.
- Líneas 83 a 85: cualquier versión distinta de 3 (1, 2 o 4) lanza `VersionIncompatible`. `main.py:245-247` lo convierte en `Versión incompatible: ...` con código 2 al cargar.
- La disposición es `[encabezado][largo jugador][jugador][largo conocimiento][conocimiento][largo línea][línea][salas][índice]`. Está en `Persistencia/ArchivoPartida.py:3`.
- Escritura (`ArchivoPartida.py:55` y `62-63`): `datos_linea_tiempo = b""`, y `posicion` suma su largo.
- Líneas 106 y 107 escriben `<I 0` y el bloque vacío.
- Lectura (`_leer_largos`, `172-182`): cada largo se valida con `_leer_largo` (`160-170`, rechaza un bloque que invade las salas).
- La fórmula es `_inicio_salas = inicio_linea + largo_linea`. Expandida: `TAMANO_ENCABEZADO + (4 + jugador) + (4 + conocimiento) + (4 + línea)`. Coincide con `contracts/formato-partida.md`.
- `_validar_encabezado` (`145-158`) exige `offset_indice >= INICIO_MINIMO_SALAS` (línea 29), es decir, encabezado más los tres largos de 4 bytes.
- `buscar_sala` y `leer_todas_salas` comprueban que cada sala empiece en o después de `_inicio_salas` y que sean contiguas.
- El guardado usa un temporal, `fsync` y `os.replace` (`ArchivoPartida.py:91-122`), así que no deja un archivo a medias.

**Qué pasa al leer un v3 con largo 0**

- Es válido. `_inicio_salas` queda justo después del campo de largo.
- `cargar_partida` (`Gestor/PreparadorPartida.py:85-137`) no lee la línea. Exige jugador y conocimiento (110-112), pero no la línea.
- `ControladorPartida._cerrar` (≈ línea 448) deja `linea = observador = None`. Después de cargar, `historia` responde «La historia no está disponible en esta partida» (`ControladorPartida.py:311-313`).
- El contrato dice que con largo 0 la línea debe empezar en la carga. Eso se cumple solo cuando T085 esté hecha.

**Qué rompería (o falta) al llenar el bloque**

1. `LectorPartida._leer_largos` (`ArchivoPartida.py:178-182`) descarta `inicio_linea` y `largo_linea`. No existen `_inicio_linea`, `_largo_linea` ni `leer_linea()` (T084).
2. `RestauradorPartida` (`Persistencia/ConversorPartida.py:289-304`) solo reexpone `leer_jugador` y `leer_conocimiento`. `cargar_partida` solo devuelve el motor, así que el controlador no llega al lector. Hay que agregar `leer_linea` al restaurador y leerla desde `motor.restaurador` antes de cerrarlo.
3. `guardar_partida` (`ArchivoPartida.py:32-34`) y `guardar_motor` (`ControladorPartida.py:55-84`) no tienen `linea=`.
   - `ejecutar_replay.recargar` (`main.py:65-71`) llama a `guardar_motor` con tres argumentos. El parámetro nuevo debe quedar con valor por omisión `None`, o el replay con `@cargar` se rompe.
4. `ExportadorJSON.guardar_partida_json` (`Persistencia/ExportadorJSON.py:30-43`) no tiene la clave `linea` (T088).
5. `tests/test_persistencia_conocimiento.py:849-880` (`TestDisposicionCrpt3`) rellena los bloques con bytes de relleno y `cantidad_salas=0`. Sigue valiendo mientras `leer_linea` no se invoque en esas pruebas. **Ninguna prueba lee salas con un bloque de línea no vacío** (`buscar_sala`, `leer_todas_salas`, `cargar_partida`). Hay que escribirla en T065.
6. Comentarios de `ArchivoPartida.py:5`, `22`, `37` y `55` dicen «bloque opaco, por ahora largo 0»: actualizarlos al llenar.
7. Compatibilidad hacia atrás: los archivos v3 escritos hoy tienen largo 0 y seguirán cargando sin línea, que es lo que el contrato permite. No hace falta subir `VERSION_FORMATO`.
8. Tamaño: el campo es `<I` (hasta 4 GiB); 5 000 acciones ≈ 135 KB. Sin riesgo.

## 2. `Bitacora/Reproductor.py`

**Firma y contrato** (líneas 12-61)

- `Reproductor(fabrica_motor, version_cripta, version_catalogo, recargar=None, observador=None)`. Coincide con T054.
- `reproducir(ruta)` lee y llama a `reproducir_acciones(encabezado, acciones)` (líneas 20-22), que es la entrada en memoria.
- Orden de avisos:
  - Primero comprueba versiones (26-30).
  - Luego crea el motor y comprueba `cripta_id` (32-36).
  - Después llama a `al_crear_motor` (40).
  - En un `@cargar` llama a `recargar`, comprueba que no sea `None` y avisa `despues_de_carga(motor_nuevo)` (43-51).
  - En cada acción llama a `ejecutar_accion` y, solo si no devolvió `False`, a `despues_de_accion` (53-59).
- `retroceder` pasa por el mismo camino que en vivo. `ObservadorLinea.despues_de_accion` lo traduce a `registrar_retroceso`.

**Cómo encajan `--hasta` (T063b) y `--checkpoint-cada`**

- `--checkpoint-cada` solo cambia el K de la `LineaTiempo`, que se crea fuera del `Reproductor`. No toca el `Reproductor` (T060 pide que con `@cargar` rija el K de la ejecución).
- `ejecutar_replay` (`main.py:44-79`) todavía no acepta `observador`. En T063b hay que pasarlo y consultar **dentro del `try`**: el `finally` de las líneas 76-79 cierra los restauradores y borra la carpeta temporal. Las copias privadas de épocas (`ObservadorLinea._copia_privada`, `ObservadorLinea.py:52-60`) necesitan esa carpeta viva o una propia que se borre después de consultar.
- `main.py:186-192` ya mapea `VersionIncompatible` a 2 y `ValueError/RuntimeError/OSError` a 1. `ErrorReconstruccion` y `ReferenciaInvalida` heredan de `Exception` (`Modelo/LineaTiempo.py:43-55`) y **no** las atrapa ese `except` (ver H5).
- `ObservadorLinea.despues_de_carga` llama a `linea.registrar_carga`, que `LineaTiempo` todavía no tiene (T082). Hasta entonces, un replay con `@cargar` y línea real lanza `AttributeError`.
- Detalle menor: `ejecutar_replay` lee la bitácora en `main.py:53` y otra vez en `Reproductor.reproducir` (línea 21). Con `reproducir_acciones` basta leer una vez (H10).

## 3. Rechazo de `--bitacora` igual a `<guardado>.log`

**Lo que funciona**

- Función `_rechazar_bitacora_del_guardado` en `ControladorPartida.py:92-100`. Compara con `_misma_ruta` (87-89), que usa `os.path.normcase(os.path.abspath(...))`. Reconoce rutas con `..`, relativas y, en Windows, distinto uso de mayúsculas.
- `ruta_bitacora_de` (49-52) añade `.log` y es la misma función que usa el guardado.
- `guardar` (226) la llama antes de escribir. Lanza `ValueError`; el comando interactivo la muestra con `No se pudo guardar: ...` y la partida sigue (`ControladorPartida.py:375-379`).
- `cargar` (188) la llama antes de `cargar_partida` y de tocar la bitácora. `main.py:229-252` la recoge como `ValueError`, imprime `! Error: ...` y devuelve **1**.
- Hay pruebas del controlador para las dos direcciones: `tests/test_persistencia_conocimiento.py:753-761` (cargar, ruta equivalente, mayúsculas) y `:793-817` (guardar y comando).

**Defectos**

- **H1: `cargar` no es atómico** (`ControladorPartida.py:187-194` y `196-215`).
  - Después de `cargar_partida` se llama a `_cerrar()` (191) y se asigna `self.motor = motor` (192). Luego `_continuar_bitacora` puede fallar (`shutil.copyfile`, `BitacoraPartida.continuar`/`leer_bitacora` con `VersionIncompatible`).
  - **Reproducido**: con la copia `g.cripta.log` dañada, el comando `cargar g.cripta` en una partida en el reloj 300 mostró `No se pudo cargar: El archivo no es una bitacora de Cripta`, pero la partida **ya era la del archivo** (reloj 100, `bitacora = None`, `linea = None`).
  - Riesgo: viola «rechazarse sin cargar nada» (Principio VI) y el requisito de T085 («si faltan datos locales no se carga nada»). Con T085, que agrega la reconstrucción (`SinDatosParaHistoria`, `ErrorReconstruccion`) justo después de `cargar_partida`, el mismo patrón dejaría una partida cargada sin línea y con un error en pantalla.
  - Arreglo: en `cargar`, armar todo en variables locales (motor, bitácora validada, línea reconstruida) y recién al final asignar a `self` y cerrar lo anterior. Si algo falla, cerrar solo lo nuevo (`motor.restaurador.cerrar()`, `bitacora.cerrar()`).
  - Prueba nueva: el fallo posterior a `cargar_partida` (copia de bitácora dañada) deja `motor`, `bitacora` y `linea` como estaban.
- **H2: `--cargar G --bitacora G` destruye el guardado** (`ControladorPartida.py:188`, `204`).
  - La función solo rechaza `ruta_bitacora == <guardado>.log`; no rechaza `ruta_bitacora == <guardado>`. `_continuar_bitacora` hace `shutil.copyfile(copia, self.ruta_bitacora)`.
  - **Reproducido**: tras `guardar g.cripta`, un controlador con `ruta_bitacora = g.cripta` cargó sin error y `g.cripta` pasó de 257 a 116 bytes, con la magia `CRIP` en lugar de `CRPT`: el guardado quedó sustituido por la bitácora.
  - Arreglo: en `_rechazar_bitacora_del_guardado` rechazar también `_misma_ruta(ruta_bitacora, ruta_guardado)` con el mismo mensaje de error de uso (código 1). `guardar` hace lo mismo con su ruta destino (hoy en Windows da `PermissionError` y en POSIX reemplazaría la bitácora activa).
  - Pruebas: las dos direcciones, y una prueba en `main` (ver sección 5).
- **H6: partida nueva sobre la copia de bitácora de un guardado** (`ControladorPartida.py:177-180`, `Bitacora/BitacoraPartida.py:39`).
  - `BitacoraPartida` abre con `"w"`. **Reproducido**: una `nueva_partida` con `--bitacora g.cripta.log` redujo la copia del guardado de 107 a 98 bytes.
  - Riesgo: el guardado sigue cargando, pero su copia de bitácora ya no es la suya (`--replay` de ese `.log` sería otra partida).
  - Arreglo: si existe un archivo `<x>` tal que `ruta_bitacora == <x>.log` y `<x>` es un `CRPT` válido, avisar o rechazar. Es solo mejora.
- **H7: `_continuar_bitacora` solo compara `cripta_id` y `semilla`** (`ControladorPartida.py:208`). Una copia de otra partida con la misma cripta y semilla pasa como válida. Además `guardar` sin bitácora (`self.bitacora is None`, línea 229) deja un `<ruta>.log` viejo junto al guardado nuevo. Arreglo: comparar también la cantidad de acciones del `.log` con `motor.acciones_jugador`, o borrar el `.log` viejo al guardar sin bitácora. (`ReconstructorLinea` usa el bloque del CRPT, no el `.log`, así que no te afecta.)
- **H9: la comparación `_misma_ruta` es léxica** (`ControladorPartida.py:87-89`). No cubre enlaces simbólicos, nombres cortos 8.3 de Windows ni sistemas de archivos insensibles a mayúsculas fuera de Windows (normcase es identidad en POSIX). Mejora: si ambos archivos existen, `os.path.samefile`; si no, `abspath + normcase`.
- En `guardar` (`ControladorPartida.py:227-230`) la copia de la bitácora se hace después de escribir el CRPT. Si `copyfile` falla, el jugador ve «No se pudo guardar» y el guardado ya existe (sin su `.log`). Mejora: avisar de forma distinta.

## 4. Prioridad de opciones de `main.py`

Orden real:

- `--bench` (línea 164) devuelve antes de cualquier otra cosa.
- `--replay` (línea 182) solo se atiende si **no** vienen `--mostrar-puntajes` ni `--verificar`.
- `--mostrar-puntajes` (200) va antes que `--verificar` (209).
- Después `--cargar` (230) y la partida nueva (233).
- `--replay` y `--bench` no instancian la vista (`vista = VistaConsola()` está en la línea 198, después del replay). Hay pruebas: `tests/test_integracion.py:190-232` y `tests/test_bench_niebla.py:535-549`.

Discrepancias:

- El README (tabla «Qué pasa al combinar opciones») tiene `--bench` (1), `--mostrar-puntajes` (2), `--replay` (3), `--cargar` (4) y `--cripta` (5), y **no incluye `--verificar`**. En el código `--verificar` gana a `--replay` y `--cargar` (spec 002, comentario de `main.py:179-181`). El texto de ayuda de `--bench` en el README también está desactualizado (persistencia y ciclo; el código corre también resolubilidad y niebla). Es parte de H3.
- Para T063a: `--hasta` y `--checkpoint-cada` deben validarse **después** del bloque `--bench` (línea 177) y **antes** de abrir la fuente en el replay (línea 183). El error de uso es código 1, no 2 (`argparse` usa 2, por eso van como texto con validación a mano).
- No se avisa cuando se ignoran opciones (por ejemplo, `--cargar` con `--cripta`): es lo documentado y no hay que cambiarlo.

## 5. Pruebas que cubren cada punto y las que faltan

| Punto | Cubierto por | Falta |
|-------|--------------|-------|
| Versión de formato | `tests/test_archivo_partida.py:103` (versión + 1), `tests/test_persistencia_conocimiento.py:438` (versión 2), `:445` (sin conocimiento), `:449` (truncado) | v1; `--cargar` con un archivo v2 en `main` con código 2; v3 con largo 0 cargado y `historia` no disponible |
| Fórmula de `_inicio_salas` | `tests/test_persistencia_conocimiento.py:862` (combinaciones de largos), `:874` (índice tras los tres largos) | línea no vacía **con salas reales** (`buscar_sala`, `leer_todas_salas`, `cargar_partida`); bloque de línea que invade las salas (T065) |
| Reproductor y observador | `tests/test_bitacora.py:362` (11 pruebas: orden de avisos, `@cargar`, rechazo, versiones, `reproducir_acciones`) | observador con la `recargar` real de `ejecutar_replay` y `@cargar`; `retroceder` a través del `Reproductor`; `ObservadorLinea` con `LineaTiempo` real y carga (T082) |
| Rechazo de `--bitacora` | `tests/test_persistencia_conocimiento.py:753-761`, `:763`, `:793-817` (controlador) | **código de salida 1 por `main`** (`--cargar G --bitacora G.log`); `--bitacora G` (H2); `nueva_partida` sobre un `.log` (H6); fallo de `_continuar_bitacora` conserva la partida (H1); enlaces simbólicos |
| Prioridad de opciones | pruebas sueltas: `tests/test_verificacion_cli.py:99-105`, `:586-600`, `tests/test_puntajes.py:224-239`, `tests/test_bench_niebla.py:535-549` | combinaciones: `--bench` con otra opción; `--mostrar-puntajes` con `--replay`; `--verificar` con `--replay`; `--replay` con `--cargar`; `--cargar` con `--cripta` |
| Códigos de salida de `--cargar` en `main` | `tests/test_integracion.py:328` (éxito) | códigos 1 y 2 de `--cargar` |

## 6. Principios I, II y X

**I (estructuras propias)**: no encontré `heapq`, `bisect`, `collections`, `sorted()`, `.sort()`, `set()`, `defaultdict` ni `lru_cache` en `Modelo/`, `Persistencia/`, `Bitacora/`, `Controlador/`, `Gestor/`, `DTOS/`, `Vista/` ni `main.py`.

- El único `dict` de `Modelo/CopiaEstado.py` es el `memo` (líneas 99 y 178), con la excepción de la constitución.
- Tres tablas de constantes que no son índice ni caché, pero conviene dejarlas dichas: `ATAJOS` (`ControladorPartida.py:25`), el selector `claves` de `Modelo/Inventario.py:114` y `NOMBRES_DIRECCION` (`Vista/VistaConsola.py:7`).
- `Sala.salidas` es un `dict` del DTO (`DTOS/SalaEsqueleto.py`) que el modelo consulta por dirección. `Modelo/Resolubilidad.py:8` lo declara uso auxiliar. Interpretación límite (H12): si hay dudas, anotarlo en el Complexity Tracking.

**II (MVC)**: `Modelo/` no importa red, archivos ni consola (grep sin coincidencias), salvo un `print`.

- `Modelo/MotorSimulacion.py:80-81` hace `print(texto)` bajo `if self.eco`. `eco` es `False` y solo las pruebas lo activan (`tests/test_linea_copia.py:353`). Es código de A (Parte I, 10-14). Riesgo: viola «`Modelo/` MUST NOT importar... consola» a la letra. Arreglo: sacar el `print` y que la vista o el controlador muestre los mensajes (H11).
- `--replay` y `--bench` no instancian la vista (líneas 164 y 182 de `main.py`).
- `Bitacora/` y `Persistencia/` solo importan entre sí (`VersionIncompatible`). La inyección de `gestor_datos` y de `gestor_historico` mantiene al modelo independiente de la fuente.

**X (trazabilidad)**: la matriz `trazabilidad.md` cubre FR-001 a FR-031 y SC-001 a SC-007.

- IDs en los nombres de prueba: `test_persistencia_conocimiento.py` 47 de 47; `test_conocimiento.py` 23 de 23; `test_mapa.py` 17 de 17; `test_bitacora.py` 22 de 38; `test_integracion.py` 4 de 21.
- **`tests/test_archivo_partida.py`: 0 de 20**, y sin ningún ID en comentarios. Cubre el CRPT 3 y la matriz no lo cita para FR-016 (H13).
- Persistencia JSON sin identificador ni versión (Principio VI): `ExportadorJSON.py:30-43` (H14). Es un exportador solo de comparación, pero la constitución dice «todo archivo persistente».

## Para el miércoles

**Bloquea la entrega**

1. **H1**: hacer `cargar` atómico (con T085).
2. **H2**: rechazar `--bitacora` igual al archivo guardado y a la ruta destino de `guardar`.
3. **H3**: actualizar el README (001-T112/T113 y 004-T115): `CRPT` 3, `CRIPTA-LOG` 2, `@cargar`, el conocimiento ya se guarda, la tabla de prioridad con `--verificar`, `--bench`.
4. **H4**: los cambios de las secciones 1.1 a 1.4 (lector, restaurador, `guardar_*` y JSON). Son tus tareas T081, T084, T085, T088; sin ellas T070 a T080 no pasan.
5. **H5** (con T086): `main.py` debe atrapar `ErrorReconstruccion` y `ReferenciaInvalida` (hoy darían un traceback) y dar código 1; la incoherencia de la línea con la partida da código 2.
6. Pruebas de `main` para el rechazo (código 1) y para `--cargar` (códigos 1 y 2).

**Mejora (después de entregar, o si sobra tiempo)**: H6, H7, H8 (resto de combinaciones de la sección 5), H9, H10, H11, H12, H13, H14.
