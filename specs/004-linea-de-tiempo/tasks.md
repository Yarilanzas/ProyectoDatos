---
description: "Lista de tareas: línea de tiempo y su persistencia"
---

# Tasks: Línea de tiempo y su persistencia

**Input**: `specs/004-linea-de-tiempo/` ([spec](spec.md), [plan](plan.md), [research](research.md),
[data-model](data-model.md), [contracts](contracts/), [quickstart](quickstart.md))

**Prerrequisitos**: spec confirmada en Git (`3d306e8`, con los cambios 1 a 10 del plan y dos edge cases, y corregida en `12fecbb`) y
aceptada por el grupo antes del primer commit de código (Principio IX, T002). Se trabaja sobre `main`, con `git pull` antes de subir
y la suite en verde en cada subida. **Línea base vigente**: 466 pruebas, 456 pasan, 10 omitidas, OK (medida el 11-11 sobre `eb92322`, T001); SC-009 pide al menos 456 pasadas.

**Pruebas**: obligatorias (Principios V y X). Cada prueba cita su FR o SC en el nombre o en un comentario, usa `unittest` y **no
usa la red**: arma paquetes offline temporales con `crear_paquete_niebla` (`tests/utiles_niebla.py`) y criptas sintéticas. **Ninguna
prueba depende de `partida.cripta`, `partida.cripta.log` ni `partida.log`** (se retirarán, 001-T098): fabrican sus propios archivos.

**Restricciones en producción** (Principio I): ningún `dict` ni `set` como índice; sin `bisect`, `sorted`, `sort`, `heapq` ni
`collections`. Único uso de `dict` permitido: el `memo` (un `dict` temporal de una sola llamada) de `copy.deepcopy` en
`Modelo/CopiaEstado.py`, autorizado por el profesor el 2026-11-12 (ver T003), solo para el `memo`. No se crean scripts de exploración ni carpetas fuera de la estructura de [plan.md](plan.md#project-structure).

**Numeración**: los `T` de este archivo son de la capacidad 004. Las tareas de otras capacidades se citan con prefijo
(`001-T117`, `003-T015`, `003-T058`, `003-T059`, `003-T076`) porque los números se repiten entre carpetas.

## Formato

`- [ ] T000 [P] [US1] [marcas] Descripción. Atiende: FR, PR. Archivo: ruta.`

| Marca | Significado |
|-------|-------------|
| `[P]` | Se puede hacer en paralelo con tareas de **otros archivos** de su bloque. Dos tareas del mismo archivo van en serie, aunque ambas lleven `[P]` |
| `[US1]`…`[US6]` | Historia de la spec. Las fases 0, 1, 8 y 9 no llevan historia |
| `[PERSONAS: A]` | Coordinación con la persona A (003): solo se envía o se pide; **no se toca su código** |
| `[PERSONAS: C]` | Cambio en un archivo de la persona C (001), con el cambio exacto de [Enganches](plan.md#enganches-y-requisitos-hacia-otras-personas). Va en un **commit pequeño y separado** y no bloquea el núcleo. Dice quién lo implementa |
| `[PERSONAS: B, C]` | Archivo compartido por B y C (`main.py`, despachador de `--bench`) |
| `[PERSONAS: grupo]` | Necesita una respuesta del grupo |
| `[BLOQUEADA: cazador de A]` | No se puede cerrar hasta que A suba su cazador (un enemigo con `comportamiento == "cazador"`, 003-T045 a T048; no hay clase `Cazador`). Mientras tanto se usa el doble de T010 |
| `Escenario USx-n` | Escenario de aceptación n de la historia x. Tabla completa en [Cobertura](#cobertura-de-escenarios-y-edge-cases) |
| `Quickstart n` | Escenario n (1 a 16) de [quickstart.md](quickstart.md) |
| `[X]` | Hecha |

Los `§` citados (§3.6, §5.5, §5.6, §6.1, §6.3) son del enunciado de la Parte II, que no está en el repositorio: se toman tal como
los registra el plan.

---

## Fase 0: Línea base y acuerdos

**Propósito**: dejar registrada la línea base de pruebas y cerrar con el grupo, con C y con A lo que el código necesita. Todo lo
que la línea necesita de la capacidad 001 **ya está en `main`** (T076, T084, T092 a T094, T096 y T119 de 001): no hay tareas de
espera ni dobles para eso.

- [X] T001 Registrar la línea base: `py -m unittest discover -s tests`. **Resultado (2026-11-11, medida sobre `eb92322`, que incluye los commits de C `b1b57d7` y `b6f9f52` y los de A `8948205` y `5c9cd5c`): 466 pruebas, OK, 10 omitidas (`skipped=10`), es decir, 456 pasan y 10 se omiten; sin red.** (Las mediciones anteriores, 405 pruebas en `3d306e8` y 426 en `a05cb2e`, quedaron obsoletas.) Esa es la referencia de SC-009: cada subida debe dar al menos 456 pasadas, ningún fallo y ninguna omisión nueva sin motivo escrito. Atiende: SC-009. Archivo: tests/ (solo lectura).
- [X] T002 [PERSONAS: grupo] Obtener la aceptación de los [cambios propuestos a la spec](plan.md#cambios-propuestos-a-la-spec) (P-D05). La spec ya los incluye en `3d306e8`. **Hecha (2026-11-12)**: A acepta los cuatro cambios que le tocan (la re-simulación le sirve porque el cazador es determinista y no consume azar); B está de acuerdo (lo de la línea de comandos lo refleja en el README, su T055); C aceptó explícitamente el 2026-11-12 los cambios 1 a 10 de la spec, los incluidos en `3d306e8`, con una condición: el cambio 3, que se aparta de la letra del enunciado, debe quedar justificado en `DECISIONES.md` con la cita del enunciado y las mediciones (T114). Con esto se levanta la regla «ningún commit de código antes de esta respuesta» (Principio IX). Atiende: FR-017, FR-021, FR-022. Archivo: specs/004-linea-de-tiempo/spec.md (solo lectura).
- [X] T003 [PERSONAS: grupo] Obtener la revisión de `copy.deepcopy` y de su argumento `memo` (Principio I, [Complexity Tracking](plan.md#complexity-tracking)). **Medición hecha el 2026-11-12 (sección «T003» de [research.md](research.md#t003-revisión-de-deepcopy-y-memo-2026-11-12)). Revisión hecha (2026-11-12)**: el profesor respondió: «Para este proyecto sí pueden usar el dict como caché. No hay problema». Autoriza `copy.deepcopy` con `memo`; T098 queda solo como opción de rendimiento (plan B decidido con M3), no como salida a un rechazo. **Alcance**: se usa solo para el `memo`; el resto de las estructuras de esta capacidad sigue sin `dict` ni `set` como índice mientras no se aclare el alcance por escrito. Atiende: FR-017, FR-021. Archivo: specs/004-linea-de-tiempo/plan.md (solo lectura).
- [X] T004 [PERSONAS: C] Enviar a C el cambio exacto del `Reproductor` (fila «Bitacora/Reproductor.py» de [Enganches](plan.md#enganches-y-requisitos-hacia-otras-personas)): parámetro `observador=None` al final con `al_crear_motor`, `despues_de_accion` y `despues_de_carga` (recibe el motor **nuevo**), y una entrada `reproducir_acciones(encabezado, acciones)` que reproduce una lista en memoria. **Hecho**: C lo implementó (001-T123 y 001-T124, commit `b1b57d7`; firma real `Reproductor(fabrica_motor, version_cripta, version_catalogo, recargar=None, observador=None)`, `reproducir_acciones(encabezado, acciones) -> motor`, `reproducir(ruta) -> motor`). El aviso 001-T125 a D (P-D02) está cumplido por mensaje de C. Atiende: FR-025, FR-011, FR-030. Archivo: Bitacora/Reproductor.py (solo el envío).
- [X] T005 [PERSONAS: C, grupo] Decidir quién implementa los cambios de la fila (d): `ControladorPartida.py`, `main.py`, `VistaConsola.py`, `ExportadorJSON.py` y `README.md`, y en qué orden y con qué dueño del merge se tocan `main.py` y `ControladorPartida.py` (P-D07). **Decidido por C el 2026-11-12**: **D implementa** T035, T036, T063a, T063b, T085, T086, T088, T066 y T111 (esta última por confirmar con C). **C es dueña de `ControladorPartida.py` y `main.py`**: revisa cada commit y resuelve el merge; y coordina T115 (D redacta los párrafos que su tarea hace visibles). **Reglas**: un turno a la vez; antes de tocar `ControladorPartida.py`, `main.py` o el README se avisa al grupo; `git pull --no-edit` y subir el mismo día. **Orden**: (1) C sube 001-T062 a T065 («ir a») esta semana; (2) T035 y T036 en local hasta T047; (3) T063a y T063b (con B); (4) T085 y T086, tras T084; (5) al final T088, T066, T111 y T115. C avisa los cambios de su bench antes de que D toque `main.py`. T063b queda como está escrito: no se extrae un `recargar` compartido. Cada tarea sigue en su commit pequeño y separado. Atiende: FR-010, FR-013, FR-018, FR-025. Archivo: main.py, Controlador/ControladorPartida.py (solo la decisión).
- [ ] T006 [PERSONAS: A] Pedir a A que **excluya `Modelo/CopiaEstado.py` por nombre, con el motivo escrito, de la prueba de `003-T015`** (la que falla si aparece `.cerrada =` o `setattr(..., "cerrada", ...)` en `Modelo/`). Enviarle el texto exacto de [interfaz-linea.md](contracts/interfaz-linea.md#choque-con-t015-de-a-persona-a-003). El método único que escribe `Salida.cerrada` lo nombra A en su 003-T016. No se toca su prueba. Sin la exclusión `003-T015` falla en cuanto exista T015. Atiende: FR-017, FR-008. Archivo: tests/test_invalidacion_puertas.py (de A, solo el envío).
- [ ] T007 [PERSONAS: A] Enviar a A los requisitos de la tabla «Qué le pide la línea a los demás» de [interfaz-linea.md](contracts/interfaz-linea.md#qué-le-pide-la-línea-a-los-demás): todo su estado cuelga del motor y no hay cachés de módulo; los campos mutables nuevos de `Sala`/`Salida` se agregan a `CAMPOS_MUTABLES_*`; el comportamiento «cazador» (`Enemigo.comportamiento == "cazador"`, decidido en el motor) no consume azar; `ciclo` y `version_puertas` están en el motor (003-T015 a T017, GrafoCripta sube el 2026-11-12); y el **registro de decisiones de los cazadores cuelga del motor** (`003-T076`), no de un módulo ni del controlador, para que el clon lo copie y lo vuelva a anotar al re-simular. Atiende: FR-001, FR-025, FR-028. Archivo: specs/004-linea-de-tiempo/contracts/interfaz-linea.md (solo el envío).
- [ ] T008 [PERSONAS: A] Responder como persona D a `001-T098`: estoy de acuerdo en retirar `partida.cripta`, `partida.cripta.log` y `partida.log` del repositorio, porque ninguna prueba de esta capacidad depende de ellos (T120 lo verifica). Atiende: FR-024. Archivo: partida.cripta, partida.cripta.log, partida.log (solo la respuesta).

**Punto de control 0**: línea base registrada (T001). T002 abre la puerta al código. T003 a T008 no bloquean la Fase 1.

---

## Fase 1: Fundamentos (PR-01 a PR-03)

**Propósito**: búsqueda binaria propia, copia estructurada del estado y el núcleo de la línea (guion, historia vigente, puntos de
control y sellos). Bloquea todas las historias.

**Prueba independiente**: `ultimo_menor_o_igual` correcto sobre arreglos con repetidos; la copia estructurada iguala a `deepcopy`
completo en cripta chica y no contamina el motor vivo; `LineaTiempo` registra N acciones y cumple las invariantes de data-model.

### Pruebas y utilidades

- [X] T009 [P] Crear `tests/utiles_linea.py` (sin prefijo `test`, `discover` no lo ejecuta): (1) generador determinista de acciones con `random.Random(semilla)` propio que elige entre atacar, esperar y mover, con vida alta para sobrevivir; (2) «motor espía» que guarda `obtener_estado_resumen()` tras cada evento; (3) comparación contra `obtener_estado_resumen()` **ampliada con `conocimiento`, `mensajes` y `rastros`**; (4) `partida_linea(...)` que arma motor y controlador con `crear_paquete_niebla` y `VistaFalsa`, sin red, **con una carpeta temporal propia que contiene la ruta de `--bitacora` (nunca el `partida.log` por defecto de `main.py`) y la carpeta de datos locales**, y que devuelve ambas rutas para poder armar un gestor nuevo sobre la misma carpeta. Atiende: SC-003, FR-001, FR-008. Archivo: tests/utiles_linea.py.
- [X] T010 Agregar a `tests/utiles_linea.py` un **doble mínimo de enemigo con comportamiento «cazador»** (no hay clase `Cazador`: en el real es `Enemigo.comportamiento == "cazador"`, decidido en el motor, 003-T046 y T048): un enemigo que decide por una regla fija (acercarse a la sala del jugador), sin consumir azar, y anota cada decisión (acción, sala de destino, salida, costo) en una lista que cuelga del motor. Marcado con el comentario `REPETIR CON EL REAL: el enemigo con comportamiento «cazador» de A (003-T045 a T048) aún no está en main` y con el mismo nombre de tarea de T079 y T118. Depende de T009 (mismo archivo). Atiende: FR-025, FR-001. Archivo: tests/utiles_linea.py.
- [X] T011 [P] Probar `ultimo_menor_o_igual(arreglo, valor)`: vacío, un elemento, valor menor que todos (`-1`), igual al primero, al último, entre dos, mayor que todos; con repetidos devuelve el **último** de los iguales (caso `pc_accion` con un punto regular y el de una carga en la misma acción: «no decreciente»); `reloj_dec` estrictamente creciente. Incluir una prueba que lee el código fuente de `Modelo/BusquedaBinaria.py` y falla si aparece `bisect`, `sorted`, `.sort(`, `heapq`, `collections`, `dict` o `set`. Atiende: FR-019, FR-020. Archivo: tests/test_linea_busqueda.py.
- [X] T012 [P] Probar la copia estructurada (Quickstart 12): (1) en cripta de ≤ 60 salas, `copiar` + `materializar` da el mismo `obtener_estado_resumen()` (ampliado) que `deepcopy` completo del motor; (2) con 200 salas la estructurada funciona y `deepcopy` completo del motor lanza `RecursionError`; (3) materializar y consultar **no cambian** `Sala.rastro` ni `Salida.cerrada` del motor vivo (HL3), incluida una sala sin atributo `rastro` (nunca visitada: «puede no existir»); (4) `CAMPOS_MUTABLES_SALA == ("rastro",)` y `CAMPOS_MUTABLES_SALIDA == ("cerrada",)`, y `Salida.cerrada_en_esqueleto` **no** está en esas constantes; (5) `historial` del clon es un `Historial()` vacío, `gestor_datos` es el histórico y `restaurador` es el de la época; (6) el oráculo incluye estados con **eventos pendientes** (`REARMAR_TRAMPA`, `VENENO`, `FIN_VELOCIDAD`, `APAGAR_ANTORCHA`) y una acción que **consuma `azar`** si existe alguna en el juego (T003 las dejó como no medidas: **HIPÓTESIS**); si no existe ninguna, se deja escrito en la prueba. Atiende: FR-017, FR-021, FR-008. Archivo: tests/test_linea_copia.py.
- [X] T013 [P] Probar el núcleo de `LineaTiempo` con las invariantes de [data-model.md](data-model.md#invariantes): `len(vig_guion) == len(vig_reloj) == len(vig_sec) == n`; `vig_reloj` crece estrictamente; `pc_accion[i] ≤ n`, no decreciente; hay un punto con `accion == 0`; con `n % K == 0` hay punto de control; `K` es `int ≥ 1` (`k=0` y `k=-1` lanzan `ValueError`); el sello se toma de `motor.reloj` y `motor.secuencia` (no de `jugador.evento_actual`, HL7); el guion guarda las acciones con el mismo texto que la bitácora; una acción rechazada no registra nada. Atiende: FR-016, FR-017, FR-021, FR-018. Archivo: tests/test_linea_nucleo.py.

### Implementación

- [X] T014 [P] Implementar `ultimo_menor_o_igual` en `Modelo/BusquedaBinaria.py`, propia, sin `bisect`, `sorted`, `sort`, `heapq` ni `collections`, con la complejidad `O(log n)` documentada en el docstring (copiar la tabla de R4). Depende de T011. Atiende: FR-019, FR-020, PR-01. Archivo: Modelo/BusquedaBinaria.py.
- [X] T015 Implementar `Modelo/PuntoControl.py` y `Modelo/CopiaEstado.py`: constantes `CAMPOS_MUTABLES_SALA = ("rastro",)` y `CAMPOS_MUTABLES_SALIDA = ("cerrada",)`; `copiar(motor)` con `copy.deepcopy(motor, memo)` donde `memo` mapea `gestor_datos → None`, `restaurador → None`, `historial → Historial()` y cada `Sala` y `Salida` → ella misma; `foto_rastros` (lista con `Sala.rastro` por ordinal, con su ausencia) y `foto_cerradas` (lista de `bool` por ordinal de salida). `PuntoControl` guarda `estado`, `foto_rastros`, `foto_cerradas`, `accion`, `reloj`, `secuencia`, `epoca`. `copiar` copia el inventario (`motor.jugador.inventario`) **con un bucle sobre la lista doble, sin recursión**, y lo registra en el `memo` para que `deepcopy` no recorra la cadena de nodos (T003 midió `RecursionError` desde **165 nodos**, límite 1000). **Prueba** con inventarios de **200 y 400 nodos**: la copia termina y es igual al original (tests/test_linea_copia.py). Falta conocer el `inventario_max` real de las criptas (no medido). Sin `dict` ni `set` como índice (el `memo` está autorizado por el profesor el 2026-11-12, ver T003). Complejidad en el docstring: copiar `O(S + N + E)`. Depende de T003 y T012. Atiende: FR-017, FR-021, PR-02. Archivo: Modelo/PuntoControl.py, Modelo/CopiaEstado.py, tests/test_linea_copia.py.
- [X] T016 Implementar `materializar(punto, gestor_historico, abrir_copia=None, ruta_copia=None)` (firma real; el `restaurador` se abre solo si ambos no son `None`) en `Modelo/CopiaEstado.py` en los cinco pasos de [data-model.md](data-model.md#puntocontrol): esqueleto propio con `copy.copy` de cada sala y salida (pasada iterativa, sin recursión), `rastro` y `cerrada` de la foto, `_origen` y `_destino` re-ligados por ordinal; `deepcopy(punto.estado, memo)` con el esqueleto de respaldo mapeado al nuevo; `clon.gestor_datos = gestor_historico` y `conectar_estado_juego(clon)`; si la época tiene copia privada, `clon.restaurador = abrir_copia(ruta)`; `clon.eco = False`. Solo escribe `Salida.cerrada` y `Sala.rastro` sobre el clon, nunca sobre el motor vivo. `Modelo/` no importa red, archivos ni consola: todo se inyecta (Principio II). **Pruebas** (tests/test_linea_copia.py): (a) un clon sobre una **sala con trampa**, con `gestor_historico` (sin gestor lanza `RuntimeError: No hay gestor de datos para consultar la ficha de la trampa.`); (b) una **sala sin contenido cargado**, resuelta desde el disco (sin gestor se rechaza con «El contenido de esa sala aún no está disponible.»); (c) un **`CERRAR_PUERTA` pendiente** que no cierra la puerta del vivo (el `memo` re-liga `Evento.actor`); (d) `eco = False` en el clon aunque el vivo tenga `eco = True`; (e) **un solo clon vivo** a la vez por `gestor_historico` (`GestorDatos.estado_juego` es único); (f) `foto_rastros` con una sala **sin atributo `rastro`**: el clon no lo crea; (g) inventarios de **200 y 400 nodos** materializan sin `RecursionError` y el clon tiene **sus propios nodos** (ninguno es el del vivo). `materializar` también hace `deepcopy(punto.estado, memo)`, así que el inventario (`motor.jugador.inventario`) volvería a recorrerse por recursión (T003 midió `RecursionError` desde 165 nodos): `materializar` copia el inventario con un bucle, sin recursión, igual que T015, y lo registra en el `memo`. Depende de T015. Atiende: FR-017, FR-021, FR-008, PR-02. Archivo: Modelo/CopiaEstado.py, tests/test_linea_copia.py.
- [X] T017 Implementar `Modelo/LineaTiempo.py` (núcleo): `LineaTiempo(k=50, gestor_historico=None, abrir_copia=None)`; listas paralelas `guion_tipo`, `guion_nombre`, `guion_argumento`, `guion_reloj`, `guion_secuencia`, `vig_guion`, `vig_reloj`, `vig_sec`, `pc_accion`, `pc_reloj`, `pc_epoca`, `pc_punto`; `iniciar(motor)` (punto en la acción 0) y `registrar_accion(motor, nombre, argumento)` (`O(1)` más copia `O(S)` cada K); verificación del sello `(reloj, secuencia)`; excepciones `ReferenciaInvalida` y `ErrorReconstruccion`; propiedades `k`, `acciones`, `reloj_actual` y `cantidad_puntos`. Cota `C ≤ ⌈n/K⌉ + 1 + L + P`. Sin `dict`/`set` como índice. Docstring con la tabla de complejidad de [interfaz-linea.md](contracts/interfaz-linea.md). Depende de T014, T016 y T013. Atiende: FR-016, FR-017, FR-021, FR-018, PR-03. Archivo: Modelo/LineaTiempo.py.

**Punto de control 1**: T011 a T017 en verde, suite igual que T001 (456 o más pasadas). `Modelo/retroceso.py` y el `Historial` sin diferencias.

---

## Fase 2: Historia 1 — Consultar el estado en un instante o antes de una acción (P1) 🎯 MVP

**Propósito**: `historia <t>` y `historia #k` muestran el estado pasado sin alterar el presente.

**Prueba independiente**: con un paquete offline, jugar una secuencia conocida; para varios `t` y `#k` el resumen coincide con el
estado que registró el motor espía, y el estado actual es idéntico antes y después de consultar.

### Pruebas de la Historia 1

- [X] T018 [P] [US1] Escenario US1-1 y Quickstart 1: partida en el reloj 700 con varias acciones; `historia 250` coincide en el 100 % de los casos con el estado que el motor espía registró en ese momento (reloj, sala, vida y estadísticas, inventario, efectos activos, enemigos de la sala con su vida y mapa conocido). Repetir para todos los instantes con evento y para todas las acciones. La reconstrucción **nunca ejecuta `retroceder` dentro de un clon**: se comprueba que ninguna acción rehecha lo sea (medido en T003: con `Historial()` vacío el clon lo rechaza). Atiende: FR-001, FR-003, FR-004, FR-006, SC-003. Archivo: tests/test_linea_consulta.py.
- [X] T019 [US1] Escenario US1-2: cuando a `t` le corresponde una decisión del jugador, `historia t` es el estado justo antes de tomarla y la decisión no se refleja. Depende de T018 (mismo archivo). Atiende: FR-001. Archivo: tests/test_linea_consulta.py.
- [X] T020 [US1] Escenarios US1-3 y US1-4: `historia #3` es el estado justo antes de la tercera acción con el reloj de ese momento; `historia #1` es el estado inicial (reloj 0, sala inicial, sin acciones hechas); `#(acciones + 1)` es el estado actual (Clarification). Depende de T019. Atiende: FR-004, FR-001. Archivo: tests/test_linea_consulta.py.
- [X] T021 [US1] Edge cases de consulta: `historia 0` (estado inicial, después de los eventos del instante 0 y antes de la primera decisión); `t` igual al reloj actual; `historia` en una partida recién iniciada (válido solo para `t = 0` o `#1`); instante entre dos acciones (estado de la última acción más los eventos hasta `t`); varias acciones con el mismo intervalo o una acción de costo 0 (`#k` distingue estados con el mismo reloj); los pasos de `ir a` cuentan como acciones y `#k` apunta a cada paso. Depende de T020. **Nota (2026-11-13): el motor no tiene acciones de costo 0 hoy (cada acción cuesta al menos una unidad de reloj y `vig_reloj` crece estrictamente); volver a comprobarlo cuando llegue el cazador real.** Atiende: FR-001, FR-003, FR-004, FR-006. Archivo: tests/test_linea_consulta.py.
- [X] T022 [P] [US1] Escenario US1-5, Quickstart 2 y SC-004: fotografiar reloj, contador de acciones, bitácora, guion, `conocimiento`, `mensajes`, `rastros`, posición, vida, inventario, efectos, enemigos e historial de retroceso antes y después de consultas **aceptadas y rechazadas**: idénticos en el 100 % de las pruebas. `consultar_accion(acciones + 1)` devuelve el motor vivo, y **ninguna consulta llama `siguiente()` ni `esta_vacia()` sobre el motor vivo** (`AgendaEventos.siguiente()` saca del heap los eventos cancelados de la raíz): se comprueba con un espía sobre la agenda del vivo. Atiende: FR-008, FR-009, SC-004. Archivo: tests/test_linea_solo_lectura.py.
- [ ] T023 [P] [US1] Escenario US1-6 y Quickstart 4: con el reloj en 400, `historia 900` se rechaza con aviso; y `historia`, `historia -3`, `historia abc`, `historia #0`, `historia #99`, `historia #`, `historia #1.5` dan los avisos de [comandos-historia.md](contracts/comandos-historia.md) (error de uso frente a aviso), sin consumir tiempo, sin contar como acción y sin anotarse en la bitácora ni en el guion. **Depende de T036; se hacen junto con T036 o después** (prueban el comando `historia` del controlador, que crea T036). Atiende: FR-005, FR-009, FR-008. Archivo: tests/test_linea_comando.py.
- [ ] T024 [US1] Escenario US1-7: la ayuda lista `historia <t>`, `historia #k`, `--hasta` y `--checkpoint-cada`. Depende de T023 (mismo archivo). **Depende de T036; se hacen junto con T036 o después** (las líneas de `AYUDA` las agrega T036). Atiende: FR-010. Archivo: tests/test_linea_comando.py.
- [X] T025 [P] [US1] Probar el texto del resumen ([comandos-historia.md](contracts/comandos-historia.md#salida-resumen-histórico-fr-006)): las cuatro primeras líneas (`Historia — instante <t>`, `antes de la acción <k> (reloj <R>)`, `estado actual (reloj <R>)`, `estado final (reloj <R>)`), `Efectos: ninguno`, `Enemigos en la sala: ninguno`, el bloque `Mapa conocido:` igual al del comando `mapa`, `Resultado: victoria` o `derrota` solo en un final terminado, y que el reloj mostrado es el **consultado** y no el del último evento. La función de módulo se llama sin instanciar `VistaConsola`. Atiende: FR-006, FR-007. Archivo: tests/test_linea_resumen.py.
- [X] T026 [P] [US1] Probar `AgendaConCorte`: `siguiente()` devuelve `None` si el próximo evento tiene `tiempo > corte`; un evento con `tiempo == corte` se entrega; el clon cambia `agenda.__class__` y la partida real nunca usa la subclase; los eventos cancelados que siguen en el montículo no se pierden. Atiende: FR-001, FR-002. Archivo: tests/test_linea_agenda.py.
- [X] T027 [P] [US1] Quickstart 13: reconstruir con una fuente que cuenta llamadas: **0 llamadas**; vaciar la caché de memoria y reconstruir lee del disco; borrar un dato local da `! Error: No se puede reconstruir sin nuevas solicitudes...` con código 1 y presupuesto sin gastar; `FuenteSinRed` lanza `SinDatosParaHistoria` (subclase de `RuntimeError`) en cualquier método distinto de versiones y detalles; el gestor histórico no toca los contadores `aciertos_cache` y `fallos_cache` del gestor vivo. Atiende: FR-008, FR-025. Archivo: tests/test_linea_sin_red.py.

### Implementación de la Historia 1

- [X] T028 [P] [US1] Implementar `AgendaConCorte` como subclase de `AgendaEventos` con el atributo `corte`; `siguiente()` en `O(1)` más lo de `AgendaEventos`. El motor no cambia. Depende de T026. Atiende: FR-001, FR-002, PR-04. Archivo: Modelo/AgendaConCorte.py.
- [X] T029 [P] [US1] Implementar `GestorHistorico` (un `GestorDatos` sobre la misma carpeta de disco en solo lectura, sin contadores ni caché compartidos con la partida), `FuenteSinRed` (devuelve las versiones y los detalles capturados al empezar o cargar y lanza `SinDatosParaHistoria` en cualquier otro método) y `SinDatosParaHistoria(RuntimeError)`. Depende de T027. **Cambio aplicado (2026-11-13):** `GestorHistorico.desde_gestor(gestor, id_cripta)` comparte el `almacenamiento_disco` del vivo y no comparte contadores ni caché; tras cada consulta la línea desconecta el gestor (`conectar_estado_juego(None)`); `SinDatosParaHistoria` llega por `FuenteSinRed.tomar_falta()` (el motor atrapa los `RuntimeError` al cargar una sala) y `LineaTiempo` la relanza tras cada acción rehecha mirando al gestor por nombre de método ([interfaz-linea.md](contracts/interfaz-linea.md)). Atiende: FR-008, FR-025, PR-09. Archivo: Gestor/GestorHistorico.py.
- [X] T030 [P] [US1] Crear el DTO `ResumenHistorico` de solo lectura, sin referencias al motor: `referencia`, `reloj`, `sala`, `vida`, `vida_max`, `ataque`, `defensa`, `velocidad`, `arma`, `armadura`, `inventario`, `efectos`, `enemigos`, `mapa`, `resultado` (campos de [data-model.md](data-model.md#resumenhistorico-dto)). Atiende: FR-006, FR-007, PR-07. Archivo: DTOS/ResumenHistorico.py.
- [X] T031 [US1] Implementar `Modelo/ResumenHistorico.py`: arma el DTO desde un motor, un reloj de consulta y la cantidad de pergaminos; efectos `VENENO`, `FIN_VELOCIDAD` y `APAGAR_ANTORCHA` leídos de la agenda del clon y de `antorcha_encendida`; enemigos vivos de la sala ordenados por id con `elegir_algoritmo` (no `sorted`); `mapa = clon.mapa_conocido()` sin recalcular. Por ahora el inventario usa los pergaminos del clon; T048 los cambia por la serie. Depende de T030. Atiende: FR-006, FR-007, FR-028, PR-07. Archivo: Modelo/ResumenHistorico.py.
- [X] T032 [P] [US1] Implementar `Vista/TextoResumen.py`: **función de módulo** que convierte el DTO en texto con el formato de [comandos-historia.md](contracts/comandos-historia.md), sin reglas de juego y sin depender de K, de modo que `--replay --hasta` no instancie la vista. Depende de T025 y T030. Atiende: FR-006, FR-007, FR-028, PR-07. Archivo: Vista/TextoResumen.py.
- [X] T033 [US1] Implementar en `LineaTiempo` las consultas de solo lectura: `consultar_accion(k, motor)` (`k == acciones + 1` devuelve el motor vivo; punto con `accion ≤ k - 1` por búsqueda binaria; `materializar`; comparar el sello de cada acción rehecha y lanzar `ErrorReconstruccion` si difiere o si el clon rechaza una acción), `consultar_instante(t, motor)` (`ReferenciaInvalida` si `t > reloj_actual`; `k` por búsqueda binaria sobre `vig_reloj`; si `vig_reloj[k] == t` es `consultar_accion(k)`; si no, `AgendaConCorte(corte = t)` y `ejecutar_accion`) y `clon_antes_de(k, motor)` para las pruebas de A. Rehace a lo sumo K acciones. Depende de T017, T028, T029 y T031. **Nota:** la parte de que el clon rechaza una acción queda cubierta por las pruebas de T013 y T022. Atiende: FR-001, FR-002, FR-003, FR-004, FR-005, FR-019, PR-04. Archivo: Modelo/LineaTiempo.py.
- [X] T034 [US1] Implementar `Controlador/ObservadorLinea.py` (mío, archivo nuevo): adaptador que traduce `al_crear_motor`, `despues_de_accion` y `despues_de_carga` a `iniciar`, `registrar_accion`/`registrar_retroceso` y `registrar_carga` de la línea; no guarda referencias al motor anterior. Depende de T033. Atiende: FR-025, FR-016, PR-12. Archivo: Controlador/ObservadorLinea.py.
- [ ] T035 [US1] [PERSONAS: C] **Implementa: D (decidido en T005, 2026-11-12); C es dueña de `ControladorPartida.py`, revisa el commit y resuelve el merge; se avisa al grupo antes de tocarlo.** Enganche en `Controlador/ControladorPartida.py`: `nueva_partida` crea `LineaTiempo(k, gestor_historico)` y llama `iniciar(motor)`; `_accion` llama `despues_de_accion(...)` **después** de `bitacora.registrar` y solo si `ejecutar_accion` devolvió `True`; `_cerrar` cierra la línea. Commit pequeño y separado, con su prueba (acción rechazada no registra; la bitácora y el guion llevan los mismos comandos en el mismo orden; sin bitácora la línea igual registra; **y el caso en que `ejecutar_accion` lanza `RuntimeError` con el motor ya avanzado**: `_accion` lo muestra y no anota nada, y la línea **no queda desfasada en silencio** (se detecta y se avisa, por ejemplo con el sello de la acción siguiente; la forma exacta se confirma al implementar)). Depende de T034. Depende de T047: el commit se hace en local y no sube a main antes que T047, para que retroceder no rompa el juego real. Atiende: FR-008, FR-009, FR-025, PR-08. Archivo: Controlador/ControladorPartida.py, tests/test_linea_comando.py.
- [ ] T036 [US1] [PERSONAS: C] **Implementa: D (decidido en T005, 2026-11-12); C revisa y resuelve el merge; aviso al grupo antes de tocar `ControladorPartida.py` y el README.** Comando `historia` en `ControladorPartida.ejecutar` (rechazos de [comandos-historia.md](contracts/comandos-historia.md): error de uso frente a aviso, `ReferenciaInvalida`, `ErrorReconstruccion`, `SinDatosParaHistoria`), `VistaConsola.mostrar_resumen_historico(dto)` que llama a `Vista/TextoResumen.py`, y las líneas nuevas de `AYUDA`. **Incluye su párrafo del README** (UTF-16, con aviso al grupo): comando `historia <t>` / `historia #k` y la nota de que `retroceder` y `historia` son mecanismos distintos. Commit pequeño y separado. Depende de T032 y T035. Depende de T047: el commit se hace en local y no sube a main antes que T047, para que retroceder no rompa el juego real. Atiende: FR-003, FR-004, FR-005, FR-009, FR-010, PR-08. Archivo: Controlador/ControladorPartida.py, Vista/VistaConsola.py.

**Punto de control 2 (MVP)**: T018 a T027 en verde, `historia <t>` e `historia #k` funcionan en el juego real, suite sin regresiones (SC-009). Falta todavía el recorte (Historia 2), guardar y cargar (Historia 5) y el replay (Historia 4).

---

## Fase 3: Historia 2 — La línea describe la historia tal como quedó (P1)

**Propósito**: tras un pergamino las acciones revertidas dejan de existir en la línea; las nuevas continúan desde el punto al que se
retrocedió; la cantidad de pergaminos por instante sale de una serie aparte.

**Prueba independiente**: jugar N acciones, usar un pergamino, consultar lo que correspondía a lo revertido y comprobar que no aparece.

### Pruebas de la Historia 2

- [ ] T037 [P] [US2] Escenario US2-1 y Quickstart 5: acciones 1 a 6 y un pergamino que deshizo la 6 (quedan 1 a 5); `historia #6` muestra el estado actual sin reflejar la acción revertida y `historia #7` se rechaza. Atiende: FR-004, FR-015, FR-016. Archivo: tests/test_linea_retroceso.py.
- [ ] T038 [US2] Escenario US2-2: el mismo caso; `historia <t>` con `t` igual al reloj anterior a revertir se rechaza por ser posterior al reloj actual, y para todo `t ≤ reloj actual` el resumen no refleja ningún efecto de la acción revertida. Depende de T037 (mismo archivo). Atiende: FR-005, FR-015. Archivo: tests/test_linea_retroceso.py.
- [ ] T039 [US2] Escenario US2-3: pergamino y luego una acción distinta; consultar un instante posterior al punto de retroceso refleja la nueva acción y nunca la revertida; la numeración es la de la historia vigente. Depende de T038. Atiende: FR-016, FR-015. Archivo: tests/test_linea_retroceso.py.
- [ ] T040 [US2] Escenario US2-4 y Quickstart 5 (pergamino recogido): el resultado de cualquier consulta coincide con el de una partida que nunca hizo las acciones revertidas, salvo la cantidad de pergaminos; incluye el caso de R5: el pergamino P se recoge en la acción 7, se usa otro pergamino Q (P **sigue en el inventario**), la acción 8 nueva es `soltar P` y el estado reconstruido coincide con el real. Depende de T039. Atiende: FR-015, FR-029, FR-014. Archivo: tests/test_linea_retroceso.py.
- [ ] T041 [US2] Escenario US2-5: 10 acciones y **cinco pergaminos seguidos** que revirtieron las últimas 5 (quedan 5; un pergamino revierte una acción); `historia #6` muestra el estado actual, `historia #7` se rechaza y las acciones 6 a 10 no son consultables. Depende de T040. Atiende: FR-004, FR-015. Archivo: tests/test_linea_retroceso.py.
- [ ] T042 [US2] Escenario US2-6 y Quickstart 6: al menos 6 acciones, 5 pergaminos seguidos y un sexto `retroceder`: no revierte nada más, se comporta como en la Parte I y la línea no cambia (guion, vigente, puntos y serie idénticos). Depende de T041. Atiende: FR-014. Archivo: tests/test_linea_retroceso.py.
- [ ] T043 [P] [US2] Escenario US2-7 y SC-010: el recorte cuesta en proporción a lo recortado. Con `V` fijo en partidas de 500 y 5 000 acciones, el trabajo del recorte (posiciones retiradas y puntos retirados) es `V` y el tiempo no crece con `n` (razón entre ambos por debajo de un margen generoso, mediana de varias repeticiones); el umbral numérico lo fija M4 (T104). Atiende: FR-027, SC-010. Archivo: tests/test_linea_recorte.py.
- [ ] T044 [P] [US2] Escenario US2-8, Quickstart 7 y FR-029: 3 pergaminos en `t`, gastar 2 en retrocesos; `historia <t>` muestra 3 y la cantidad real sigue siendo la actual; en la posición a la que se retrocedió rige la última ocurrencia (el presente) y antes de ella lo que el jugador tenía entonces; `serie_clave` estrictamente creciente con `serie_clave[-1] ≤ n`; `plegar` agrega `(nuevo_n, cantidad_actual)` solo si difiere de la última. Atiende: FR-029. Archivo: tests/test_linea_pergaminos.py.
- [ ] T045 [US2] Edge «intervalos descartados» y oráculo de A: tras un retroceso no quedan acciones registradas ni puntos de control con `accion > nuevo_n` (sin huérfanos), y `consultar_accion(acciones + 1)` es igual al motor vivo (la prueba que detecta una mutación no reportada a `historial.registrar`). Depende de T042 (mismo archivo que T037). Atiende: FR-015, FR-016. Archivo: tests/test_linea_retroceso.py.

### Implementación de la Historia 2

- [ ] T046 [US2] Implementar la serie de pergaminos en `LineaTiempo`: `serie_clave` y `serie_cantidad` ordenadas por clave; `registrar` agrega `(n, cantidad)` si cambió la cuenta de `pergamino_retroceso` del inventario (`O(capacidad del inventario)`); `plegar(nuevo_n)` en `O(sacadas)`; `en(clave)` por búsqueda binaria propia en `O(log longitud)`. Depende de T033 y T044. Atiende: FR-029, PR-06. Archivo: Modelo/LineaTiempo.py.
- [ ] T047 [US2] Implementar `registrar_retroceso(motor)`: `V = acciones_antes - acciones_después` con `motor.acciones_jugador`; saca `V` posiciones de `vig_*` y los puntos con `accion > nuevo_n`; agrega `RETROCESO` al guion con las acciones vigentes que quedan; toma un punto de control del **motor real** en `nuevo_n` (si ya había uno, lo reemplaza); pliega la serie. `O(V + S)`, independiente de `n`. Depende de T046 y T042. Atiende: FR-014, FR-015, FR-016, FR-027, SC-010, PR-05. Archivo: Modelo/LineaTiempo.py.
- [ ] T048 [US2] Hacer que `consultar_accion` y `consultar_instante` pasen al resumen la cantidad de la serie (`en(k - 1)` para `#k`; `en(k)` para `t` con `vig_reloj[k] < t`; `en(k - 1)` para `t == vig_reloj[k]`) y que `ResumenHistorico` la muestre en lugar de la del clon. Depende de T047. Atiende: FR-029, PR-06. Archivo: Modelo/LineaTiempo.py, Modelo/ResumenHistorico.py.

**Punto de control 3**: T037 a T045 en verde; `Modelo/retroceso.py` sin diferencias; suite sin regresiones.

---

## Fase 4: Historia 3 — Varios eventos en el mismo instante (P1)

**Propósito**: `historia <t>` refleja todos los eventos de `t`, en el orden de resolución de la partida real, salvo la decisión del
jugador.

**Prueba independiente**: una cripta de prueba donde coinciden en `t` un ataque, el fin de un efecto y el cierre de una puerta.

- [ ] T049 [US3] Agregar a `tests/utiles_linea.py` el constructor de la cripta de coincidencia: un enemigo que ataca, un efecto de velocidad que termina y una puerta que se cierra sola, los tres programados exactamente en `t`, más un evento en `t + 1`; devuelve `t` y el orden de resolución observado por el motor espía. Depende de T010 (mismo archivo). Atiende: FR-002. Archivo: tests/utiles_linea.py.
- [ ] T050 [P] [US3] Escenario US3-1 y Quickstart 3: `historia t` refleja los tres eventos, en el mismo orden de resolución que tuvieron en la partida (comparado con el motor espía). Depende de T049. Atiende: FR-001, FR-002. Archivo: tests/test_linea_mismo_instante.py.
- [ ] T051 [US3] Escenario US3-2: el evento de `t + 1` no se refleja en `historia t`. Depende de T050 (mismo archivo). Atiende: FR-001, FR-002. Archivo: tests/test_linea_mismo_instante.py.
- [ ] T052 [US3] Quickstart 3 (segundo caso): con una decisión del jugador en `t`, `historia t` es el estado previo a decidir, y un evento con tiempo `t` y secuencia **posterior** a la decisión no se refleja. Depende de T051. Atiende: FR-001. Archivo: tests/test_linea_mismo_instante.py.
- [ ] T053 [US3] Si T050 a T052 fallan, corregir el corte en `consultar_instante` o en `AgendaConCorte` (sin tocar el motor); si pasan a la primera, dejarlo escrito en esta tarea y marcarla hecha sin cambios de código. Depende de T052. Atiende: FR-001, FR-002. Archivo: Modelo/LineaTiempo.py, Modelo/AgendaConCorte.py.

**Punto de control 4**: T050 a T052 en verde. Las tres historias P1 completas.

---

## Fase 5: Historia 4 — Consulta sin interacción: `--replay ... --hasta <t>` (P2)

**Propósito**: reproducir la bitácora completa e imprimir el estado en `t` de la historia vigente, sin instanciar la vista; y las
opciones `--hasta` y `--checkpoint-cada`.

**Prueba independiente**: reproducir una bitácora conocida con `--hasta` en varios valores y comparar con `historia` en la partida jugada.

**Dependencias de otra persona**: ninguna pendiente. El `observador` y `reproducir_acciones` del `Reproductor` ya están en `main`
(C, `b1b57d7`, 001-T123/T124; T004 y T061 hechas). Las pruebas de PR-12 se escriben contra el código real, sin omisiones.

### Pruebas de la Historia 4

- [ ] T054 [P] [US4] Probar el `observador` del `Reproductor` (PR-12): `al_crear_motor` tras la fábrica; `despues_de_accion(motor, nombre, argumento)` tras cada acción que el motor no rechazó, incluido `retroceder`; `despues_de_carga(motor)` recibe el motor **nuevo** que devolvió `recargar`; sin observador el `Reproductor` se comporta igual que hoy; `reproducir_acciones` reproduce una lista `(encabezado, acciones)` en memoria y `reproducir(ruta)` se reduce a leer y llamarla. Las pruebas se escriben contra el `Reproductor` real (firma `Reproductor(fabrica_motor, version_cripta, version_catalogo, recargar=None, observador=None)`), sin `skipUnless`; el orden de avisos es el de [formato-bitacora.md de 001](../001-niebla-mapa-ir-a/contracts/formato-bitacora.md#observador-y-reproducción-en-memoria-pedido-de-persona-d-p-d02-de-la-spec-004), y no duplican las pruebas 001-T123. Atiende: FR-025, FR-011, FR-030. Archivo: tests/test_linea_observador.py.
- [ ] T055 [P] [US4] Escenario US4-1 y Quickstart 8: `--replay bitácora --hasta 250` imprime el mismo texto que `historia 250` en la partida jugada, **sin instanciar la vista** (`VistaConsola` reemplazada por una que falla al crearse; código 0; solo el resumen, sin `Reproducción finalizada.`). Atiende: FR-007, FR-011. Archivo: tests/test_linea_replay_hasta.py.
- [ ] T056 [US4] Escenario US4-2 y edge «partida terminada»: `--hasta 5000` con la partida terminada en el reloj 900 muestra primero `La partida termina antes del instante 5000 (la bitácora acaba en el reloj 900): se muestra el estado final.` y luego el estado final; `t` igual al reloj final no lleva aviso; el final de una victoria o derrota incluye `Resultado:`; el «final» es el de reproducir la bitácora completa. Depende de T055. Atiende: FR-012. Archivo: tests/test_linea_replay_hasta.py.
- [ ] T057 [US4] Escenario US4-3: una bitácora con `retroceder` da un resumen de la historia vigente (sin las acciones revertidas), también cuando el retroceso es posterior a `t`. Depende de T056. Atiende: FR-011, FR-015. Archivo: tests/test_linea_replay_hasta.py.
- [ ] T058 [US4] Escenario US4-6: bitácora con `@cargar`; la tabla del ejemplo de [formato-bitacora.md](contracts/formato-bitacora.md#ejemplo) (`--hasta 0`, `150`, `200` = decisión del motor cargado, `300`, `99999`) con el reloj global y continuo; lo jugado entre el guardado y la carga no existe en la línea. Depende de T057. Atiende: FR-030. Archivo: tests/test_linea_replay_hasta.py.
- [ ] T059 [P] [US4] Escenario US4-4 y Quickstart 10 (opciones): `--hasta` no entero o negativo y `--hasta` sin `--replay` terminan con `! Error: ...` y código **1** (nunca 2; los casos de K de `--checkpoint-cada` los prueba solo T095) **antes** de abrir la fuente, crear el gestor o leer archivos; `--bench` ignora las opciones sin validarlas; la tabla de combinaciones de [comandos-historia.md](contracts/comandos-historia.md#combinaciones-con-la-prioridad-de-la-capacidad-002) fila por fila (`--mostrar-puntajes`, `--verificar`, `--replay F --cargar G --checkpoint-cada K`, `--replay F --checkpoint-cada K` sin `--hasta` no construye línea). Atiende: FR-013, FR-018. Archivo: tests/test_cli_historia.py.
- [ ] T060 [US4] Edges de `--replay`: `--replay --hasta` sobre una bitácora de versión incompatible termina con `Versión incompatible: ...` y código **2** igual que `--replay` sin `--hasta`; `--checkpoint-cada` con `--replay` es válido, solo cambia el costo, y con `@cargar` rige el K de la ejecución sin cambiar ningún resumen. Depende de T059 (mismo archivo). Atiende: FR-011, FR-028, FR-024. Archivo: tests/test_cli_historia.py.

### Implementación de la Historia 4

- [X] T061 [US4] [PERSONAS: C] **Hecha por C** (001-T123 y 001-T124, commit `b1b57d7`, con el cambio exacto que envió T004): `observador=None` en `Reproductor` y su entrada en memoria `reproducir_acciones`; orden de avisos `al_crear_motor`, `despues_de_accion` tras cada acción no rechazada y `despues_de_carga` con el motor nuevo. Las pruebas propias son T054. Atiende: FR-025, FR-011, FR-030, PR-12. Archivo: Bitacora/Reproductor.py.
- [ ] T062 [US4] Implementar `Controlador/ConsultaHistoria.py` (mío): arma `Reproductor(..., observador=ObservadorLinea(linea))`, reproduce la bitácora completa y devuelve `consultar_instante(t)` o el estado final con el aviso de FR-012; el texto sale de `Vista/TextoResumen.py`. **La consulta se hace dentro del `try` de `ejecutar_replay`**, con un callback `al_terminar(motor)` que `ejecutar_replay` llama justo después de `reproductor.reproducir(ruta)` y **antes** del `finally` que cierra los restauradores y borra la carpeta temporal (hoy `ejecutar_replay(ruta, gestor)`, `main.py`); así el estado final y los clones aún leen archivos abiertos. Depende de T033, T034 y T055. Atiende: FR-011, FR-012, FR-030, PR-12. Archivo: Controlador/ConsultaHistoria.py.
- [ ] T063a [US4] [PERSONAS: B, C] **Implementa: D (decidido en T005, 2026-11-12), con B; C es dueña de `main.py`, revisa y resuelve el merge; C avisa los cambios de su bench antes de que D toque `main.py`.** En `main.py`: `--hasta` y `--checkpoint-cada` leídos como texto con validación a mano (código 1, no el 2 de `argparse`, HL11); reglas de combinación y orden de evaluación de [comandos-historia.md](contracts/comandos-historia.md#orden-de-evaluación-en-mainpy) (incluido `--cargar F --checkpoint-cada K` como error de uso antes de cargar). Se valida antes de abrir la fuente y después de `--bench`; la tabla de prioridad no cambia. **Bloquea T059, T060, T077 y T095** (sus pruebas la ejercitan). Commit pequeño y separado, que sube en el mismo push que T063b. Depende de T005. Atiende: FR-013, FR-018, FR-031, PR-13. Archivo: main.py.
- [ ] T063b [US4] [PERSONAS: B, C] **Implementa: D (decidido en T005, 2026-11-12), con B; C revisa y resuelve el merge. Queda como está escrito: no se extrae un `recargar` compartido.** En `main.py`: rama `--replay --hasta` sin instanciar la vista. `ejecutar_replay` pasa `observador=` al `Reproductor` y recibe el callback `al_terminar(motor)` de T062, que consulta dentro del `try`; la recarga de `ejecutar_replay` **no** avisa al observador, porque el `Reproductor` ya llama a `despues_de_carga` tras cada `@cargar` (`Bitacora/Reproductor.py:49-50`). **Incluye su párrafo del README**: opciones `--hasta` y `--checkpoint-cada` en la tabla de opciones y la salida de `--replay --hasta`. Commit pequeño y separado. Depende de T062, T063a, T059 y T060. Atiende: FR-011, FR-012, FR-013, FR-018, FR-030, PR-12, PR-13. Archivo: main.py, README.md.

**Punto de control 5**: T055 a T060 en verde (la parte `@cargar` de T058 puede esperar a la Fase 6); `--replay --hasta` funciona.

---

## Fase 6: Historia 5 — Guardar y cargar conserva la línea completa (P2) — Persistencia

**Propósito**: el `CRPT` 3 lleva un bloque de línea con K y el guion; al cargar se reproduce el guion, se verifican los sellos y se
reconstruyen los puntos de control. **Cambios en archivos de C**: yo lleno el bloque en un commit pequeño y separado que C revisa
(T084); el resto de los archivos de la fila (d) los implementa D según T005 (2026-11-12), con C como dueña de `ControladorPartida.py` y `main.py`.

**Prueba independiente**: jugar, guardar, cargar en una sesión nueva y comparar el resumen de varios instantes antes y después;
intentar cargar un archivo de formato anterior.

### Pruebas de la Historia 5

- [ ] T064 [P] [US5] Probar `RegistroLinea`: ida y vuelta binaria y JSON; el mismo estado da los mismos bytes (orden canónico); tamaños de [formato-partida.md](contracts/formato-partida.md#tamaño) (`mover E` = 27 bytes, un retroceso = 5, una carga = 9, `largo línea = 8 + Σ registros`); rechazo con `VersionIncompatible` de bloque truncado, `tipo` desconocido, `K < 1`, nombre inválido (empieza por `#` o `@`), bytes sobrantes y un `RETROCESO` que deja más acciones vigentes que las que había. Atiende: FR-022, FR-024, FR-031. Archivo: tests/test_linea_registro.py.
- [ ] T065 [P] [US5] [PERSONAS: C] Pruebas de `ArchivoPartida` **limitadas a la línea no vacía**, `leer_linea` y `bytes_leidos`: con un bloque de línea no vacío, `leer_linea()` devuelve el `RegistroLinea` escrito y `None` con `largo línea = 0`; un bloque de línea que invade las salas se rechaza (código 2); `bytes_leidos` es `TAMANO_ENCABEZADO + 12` al abrir y leer una sala **no** lee la línea. No repite lo que 001-T122 ya probó (`offset_indice >= TAMANO_ENCABEZADO + 12` y la fórmula de `_inicio_salas`); sí comprueba que esa fórmula sigue valiendo con `largo_línea` distinto de 0. Va en el mismo commit pequeño que T084. Atiende: FR-022, FR-023, FR-024. Archivo: tests/test_archivo_partida.py.
- [ ] T066 [P] [US5] [PERSONAS: C] **Implementa: D (decidido en T005, 2026-11-12); va al final, con T088.** Probar que `ExportadorJSON` incluye la clave `linea` con `k` y la lista de registros, los mismos datos que el binario. Atiende: FR-022. Archivo: tests/test_json.py.
- [ ] T067 [P] [US5] Agregar a `tests/utiles_linea.py` la fabricación de archivos propios (sin `partida.cripta`): un `CRPT` con encabezado de versión 1 o 2 (el de la Parte I), uno de versión desconocida, uno de versión 3 con la línea alterada (sello cambiado, bloque truncado, `tipo` desconocido) y una copia con el paquete o la carpeta de datos locales borrados. Depende de T049 (mismo archivo). Atiende: FR-024, FR-022. Archivo: tests/utiles_linea.py.
- [ ] T068 [P] [US5] Probar el modelo de épocas y cargas: `registrar_carga` agrega `CARGA` al guion con el reloj cargado, toma un punto del **motor cargado** en la acción `n` (reemplaza un punto regular en `n`), abre una época con la copia privada, deja `pc_accion` con repetidos y la búsqueda devuelve el último; la línea anterior a la carga queda intacta; el primer `retroceder` tras cargar se rechaza como en la Parte I. Atiende: FR-017, FR-022, FR-030. Archivo: tests/test_linea_epoca.py.
- [ ] T069 [P] [US5] Probar `ReconstructorLinea`: reproduce el guion desde la cripta y la semilla del encabezado, compara `(reloj, secuencia)` por acción y, al final, reloj, sala, vida y acciones con el bloque del jugador; cualquier diferencia termina en `Versión incompatible: la línea de tiempo no coincide con la partida` (código 2) sin cargar nada; una copia privada del archivo cargado por carga, en una carpeta temporal propia, que `cerrar()` borra después de cerrar los manejadores (Windows). Atiende: FR-022, FR-025, FR-031. Archivo: tests/test_linea_reconstructor.py.
- [ ] T070 [US5] Escenario US5-1 y Quickstart 9: jugar, guardar, cargar con un controlador y un gestor nuevos sobre **la misma carpeta de datos locales** que creó `partida_linea` (T009) (equivale a un proceso nuevo) y `historia <t>` para `t` en 0..800 es idéntico al de antes de guardar, en el 100 % de los casos. Depende de T067. Atiende: FR-022, SC-005. Archivo: tests/test_linea_persistencia.py.
- [ ] T071 [US5] Escenario US5-2: tras cargar, continuar y consultar un instante anterior y otro posterior al guardado: ambos correctos; guardar de nuevo, cargar de nuevo y repetir. Depende de T070 (mismo archivo). Atiende: FR-022, FR-025. Archivo: tests/test_linea_persistencia.py.
- [ ] T072 [US4] Escenario US4-5: partida jugada, guardada, cargada y continuada; `--replay` de su bitácora da la misma línea y los mismos resúmenes para todo `t` (Quickstart 9, `--replay --hasta`). Depende de T071. Atiende: FR-025, FR-030. Archivo: tests/test_linea_persistencia.py.
- [ ] T073 [US5] Escenario US5-3: un archivo de la Parte I (encabezado de versión 1 o 2, fabricado en T067) se rechaza con `Versión incompatible` y código **2**, sin cargar nada. Depende de T072. Atiende: FR-024, SC-008. Archivo: tests/test_linea_persistencia.py.
- [ ] T074 [US5] Escenario US5-4: tras cargar, `retroceder` se comporta como en la Parte I (el historial no se guardó) y la línea refleja solo lo que ocurra. Depende de T073. Atiende: FR-022, FR-014. Archivo: tests/test_linea_persistencia.py.
- [ ] T075 [US5] Escenario US5-5 y Quickstart 10: versión intermedia o desconocida, línea alterada, bloque truncado, `tipo` desconocido y `K < 1` se rechazan con `Versión incompatible` y código 2, sin cargar nada, en el 100 % de los intentos. Depende de T074. Atiende: FR-024, SC-008. Archivo: tests/test_linea_persistencia.py.
- [ ] T076 [US5] Escenario US5-6: el archivo guardado declara `VERSION_FORMATO` 3, distinta de la de la Parte I, y el README (UTF-16) documenta el `CRPT` 3 con la línea (la prueba lee el README con su codificación). Queda con `skipUnless` y el motivo `espera T115 (README)` hasta que el README documente el `CRPT` 3 con la línea; T121 comprueba que ya no esté omitida. Depende de T075. Atiende: FR-023. Archivo: tests/test_linea_persistencia.py.
- [ ] T077 [US5] Escenario US5-7: cargar un archivo guardado con K = 10 usando `--checkpoint-cada` termina con `! Error: --checkpoint-cada no se puede usar al cargar una partida: rige el valor guardado en el archivo.` y código **1**, sin cargar nada; sin esa opción rige el K del archivo; el comando interactivo `cargar` adopta el K del archivo sin error. Depende de T076. Atiende: FR-031. Archivo: tests/test_linea_persistencia.py.
- [ ] T078 [P] [US5] Quickstart 15 y edge «cargar sin datos locales»: guardar una partida con línea, borrar la carpeta de datos locales (o un dato que el guion necesite, con el paquete offline sin red) y repetir `--cargar` y el comando `cargar`: `! Error: No se puede reconstruir sin nuevas solicitudes: faltan datos locales (<qué>)`, código **1**; no se carga nada; en el comando `cargar` la partida en curso (reloj, bitácora y línea) queda intacta; **0 llamadas** a la fuente. Lo mismo con `--replay` y `@cargar`. Atiende: FR-022, FR-025. Archivo: tests/test_linea_carga_sin_datos.py.
- [ ] T079 [P] [US5] Quickstart 14: con enemigos de comportamiento «cazador» activos (el doble de T010; `[BLOQUEADA: cazador de A]` para repetir con el real, `Enemigo.comportamiento == "cazador"`, 003-T045 a T048) y **activando en el motor, antes de clonar, el registro de decisiones de A** (`003-T076`, apagado por defecto; el clon lo hereda por `deepcopy`), reconstruir tras guardar, cargar y retroceder da las mismas decisiones que la partida real, turno por turno, usando `clon_antes_de`. Si el cazador consumiera azar el sello lo detecta y el resultado es `ErrorReconstruccion`. **Repetir con el cazador real de A y el registro de decisiones de 003-T076 si cuelga del motor.** Atiende: FR-025, FR-001. Archivo: tests/test_linea_cazadores.py.
- [ ] T080 [P] [US5] Quickstart 16 y edge «`--bitacora` igual a `<guardado>.log`», con el **comportamiento real** de C (`b6f9f52`, 001-T120/T121; `ControladorPartida._rechazar_bitacora_del_guardado`): el comando `guardar p.cripta` con `--bitacora p.cripta.log` **se rechaza y la partida sigue** (`! Error: No se pudo guardar: la bitácora no puede ser p.cripta.log, que es la copia de bitácora de la partida guardada; use otra con --bitacora`, sin escribir el archivo ni su bitácora); solo `--cargar p.cripta --bitacora p.cripta.log` sale con `! Error: la bitácora no puede ser p.cripta.log, que es la copia de bitácora de la partida guardada; use otra con --bitacora` y código **1**, sin cargar. **Limitada a lo que 001-T120 y 001-T121 no prueban**: con una bitácora distinta, el replay de `--hasta` coincide con la línea (regla 2 sin excepciones). La implementación de C ya está en `main` (T087), así que la prueba se sube sin esperar. Atiende: FR-025, FR-030. Archivo: tests/test_linea_bitacora_guardado.py.

### Implementación de la Historia 5

- [ ] T081 [US5] Implementar `RegistroLinea` en `Persistencia/RegistroLinea.py` con `to_bytes`, `from_bytes`, `to_dict` y `from_dict` y el formato exacto de [formato-partida.md](contracts/formato-partida.md#bloque-de-la-línea): `<I` K, `<I` cantidad, por registro `<B` tipo (`1 = ACCION`, `2 = RETROCESO`, `3 = CARGA`), `<H`+nombre UTF-8, `<H`+argumento, `<Q` reloj, `<Q` secuencia, `<I` acciones que quedan, `<Q` reloj cargado; little endian y sin relleno; `from_bytes` lanza `VersionIncompatible`. Depende de T064. Atiende: FR-022, FR-031, PR-10. Archivo: Persistencia/RegistroLinea.py.
- [ ] T082 [US5] Implementar en `LineaTiempo` `registrar_carga(motor, ruta_copia)` (épocas: `epocas_accion`, `epocas_ruta`), `a_registro()` (`O(n)`), `LineaTiempo.desde_registro(registro, ...)` (solo datos) y `cerrar()`. Depende de T068, T081 y T047. **Decisión confirmada por lectura del código el 2026-11-13 (M3): `PreparadorPartida.py:133` asigna `motor.restaurador` al cargar y `.ruta` es público (lo usa `guardar_motor`). La copia privada se hace al cargar, antes de cualquier guardar, porque `guardar_motor` pone el restaurador en `None` y lo reasigna. En una partida nueva no hay restaurador y la época se abre sin copia privada.** Atiende: FR-017, FR-022, FR-031, PR-10. Archivo: Modelo/LineaTiempo.py.
- [ ] T083 [US5] Implementar `Controlador/ReconstructorLinea.py` (mío): reproduce el guion con `Reproductor.reproducir_acciones` y el observador, verifica los sellos y el bloque del jugador, abre la época con una copia privada del archivo cargado en una carpeta temporal propia y entrega la línea; si falta un dato local lanza `SinDatosParaHistoria` y no cambia nada. Depende de T061, T069 y T082. Atiende: FR-022, FR-025, FR-030, PR-09, PR-11. Archivo: Controlador/ReconstructorLinea.py.
- [ ] T084 [US5] [PERSONAS: C] **Implementa D, revisa C.** Commit pequeño y separado (sube en el mismo push que T085); la revisión se pide en T122. Llenar el bloque de la línea en `ArchivoPartida.py`: parámetro `linea=None` en `guardar_partida` (objeto con `to_bytes()`; `None` escribe `largo línea = 0`), guardar `_inicio_linea` y `_largo_linea` en `LectorPartida` (hoy locales de `_leer_largos`), `leer_linea()` de una sola vez, y `linea=None` en `guardar_motor` de `ControladorPartida.py`. `FormatoBinario.py` sin cambios: **no sube `VERSION_FORMATO`** (P-10). Con las pruebas de T065. Depende de T065 y T081. Atiende: FR-022, FR-023, FR-024, PR-10. Archivo: Persistencia/ArchivoPartida.py, Controlador/ControladorPartida.py.
- [ ] T085 [US5] [PERSONAS: C] **Implementa: D (decidido en T005, 2026-11-12), tras T084; C es dueña de `ControladorPartida.py`, revisa y resuelve el merge.** En `ControladorPartida.py`: `guardar` pasa `linea=linea.a_registro()`; `cargar` reconstruye con `ReconstructorLinea`, llama `registrar_carga` y, si faltan datos locales o el guion no coincide, **no cambia el estado del controlador** (motor, bitácora y línea intactos); `nueva_partida` y `_cerrar` borran las copias privadas; el comando `cargar` adopta el K del archivo. **Incluye su párrafo del README** (el `CRPT` 3 con el bloque de la línea y su fórmula de `_inicio_salas`, y el error de carga sin datos locales). Commit pequeño y separado, con T070 a T078. Depende de T083 y T084. **Decisión confirmada por lectura del código el 2026-11-13 (M3): `PreparadorPartida.py:133` asigna `motor.restaurador` al cargar y `.ruta` es público (lo usa `guardar_motor`). La copia privada se hace al cargar, antes de cualquier guardar, porque `guardar_motor` pone el restaurador en `None` y lo reasigna. En una partida nueva no hay restaurador y la época se abre sin copia privada.** Atiende: FR-022, FR-025, FR-031, PR-11. Archivo: Controlador/ControladorPartida.py.
- [ ] T086 [US5] [PERSONAS: C] **Implementa: D (decidido en T005, 2026-11-12), tras T085; C es dueña de `main.py`, revisa y resuelve el merge.** En `main.py`: `ErrorReconstruccion` y `SinDatosParaHistoria` terminan con `! Error: ...` y código 1; `Versión incompatible: la línea de tiempo no coincide con la partida` y el rechazo de un bloque inválido, con código 2; `--cargar F --checkpoint-cada K` es error de uso antes de cargar. Commit pequeño y separado. Depende de T063a y T085. Atiende: FR-024, FR-031, PR-11. Archivo: main.py.
- [X] T087 [US5] [PERSONAS: C] **Hecha por C** (001-T121, commit `b6f9f52`): rechazo de `--bitacora` igual a `ruta_bitacora_de(ruta)` (`<guardado>.log`, comparado con `_misma_ruta` y `normcase`) en `guardar` (antes de `guardar_motor`) y en `cargar` (antes de `cargar_partida`), con `ValueError`; `main.py` no cambió porque ya traduce `ValueError` a `! Error: ...` y código 1. En la partida, `guardar` y `cargar` muestran el error y la partida sigue. La prueba de aceptación propia es T080. Atiende: FR-025, FR-030, PR-11. Archivo: Controlador/ControladorPartida.py, main.py.
- [ ] T088 [US5] [PERSONAS: C] **Implementa: D (decidido en T005, 2026-11-12); va al final, con T066.** `ExportadorJSON`: clave `linea` con los mismos datos que el binario. Con T066. Depende de T081. Atiende: FR-022, PR-10. Archivo: Persistencia/ExportadorJSON.py.
- [ ] T089 [US5] [PERSONAS: A] Avisar a A cuando suban las piezas que sus tareas esperan: `003-T059` espera T016, T033 y T017 (`clon_antes_de`); `003-T058` (c) espera T084 y T085. `003-T058` (a) y (b) no esperan a esta capacidad. Atiende: FR-025. Archivo: specs/003-terreno-cazador/tasks.md (solo el aviso).

**Punto de control 6**: T064 a T080 en verde (T066, T080 y la parte `@cargar` de T058 según lleguen los commits de C); `largo línea = 0` sigue cargando; suite sin regresiones. Hasta T085 no declarar FR-022 ni SC-005 como cumplidos.

---

## Fase 7: Historia 6 — Consultas rápidas y de memoria acotada (P3)

**Propósito**: ninguna consulta rehace más de K acciones; las copias completas son escasas; `historia` responde en menos de 50 ms
con 5 000 acciones.

**Prueba independiente**: partida de 5 000 acciones o más; medir el tiempo de `historia` en instantes variados y el crecimiento de la memoria.

### Pruebas de la Historia 6

- [ ] T090 [P] [US6] Escenario US6-1 y SC-002: partida de 5 000 acciones (semilla fija) y K por defecto; el 100 % de las consultas de una muestra repartida en toda la partida responde en menos de 50 ms. Es una comprobación de humo; la medición completa es M1 (T101). Atiende: FR-020, SC-002. Archivo: tests/test_linea_rendimiento.py.
- [ ] T091 [P] [US6] Escenario US6-2 y SC-006: con `--checkpoint-cada K` nunca hay más de una copia completa cada K acciones salvo el punto posterior a un retroceso y el de una carga; `C ≤ ⌈acciones / K⌉ + 1 + L + P` con 5 000 acciones, varias K, retrocesos y cargas. Atiende: FR-017, SC-006. Archivo: tests/test_linea_memoria.py.
- [ ] T092 [US6] Escenario US6-3: ninguna consulta (`#k` o `t`, en todas las posiciones de una partida con retrocesos y cargas) rehace más de K acciones, medido con el contador de T096. Depende de T091 y T096. Atiende: FR-019. Archivo: tests/test_linea_memoria.py.
- [ ] T093 [US6] Escenario US6-4: la memoria de la línea (`tracemalloc`) crece con las acciones más un punto cada K, no con «acciones × tamaño del estado»: duplicar las acciones duplica aproximadamente la memoria (con un margen); sin puntos de control extra no crece el término `C · S` más rápido que `n/K`. Depende de T092. Atiende: FR-021, SC-006. Archivo: tests/test_linea_memoria.py.
- [ ] T094 [P] [US6] Escenario US6-5, Quickstart 11 y SC-003: los mismos 100 instantes con K = 1, 50 y 500 dan resúmenes idénticos en contenido, por `historia` y por `--replay --hasta`, y solo cambia el costo; con tres semillas. Atiende: FR-028, SC-003. Archivo: tests/test_linea_independencia_k.py.
- [ ] T095 [P] [US6] Edge «`--checkpoint-cada` con valor 0, negativo o no entero se rechaza como error de uso; K = 1 es válido» (los casos de K viven solo aquí; T059 valida `--hasta` y las combinaciones): `0`, `-5`, `abc` y `1.5` dan `! Error: --checkpoint-cada requiere un entero mayor o igual que 1 (recibido: <texto>).` con código 1; `1` arma una línea con un punto por acción; el valor por defecto es el que fije T113. Atiende: FR-018. Archivo: tests/test_cli_historia.py.

### Implementación de la Historia 6

- [ ] T096 [US6] Agregar a `LineaTiempo` un contador de solo lectura de las acciones rehechas por la última consulta (`acciones_rehechas`), sin cambiar el comportamiento, para probar FR-019. Depende de T033. Atiende: FR-019, PR-04. Archivo: Modelo/LineaTiempo.py.
- [ ] T097 [US6] Copiar a los docstrings de `LineaTiempo`, `CopiaEstado`, `BusquedaBinaria`, `PuntoControl` y `AgendaConCorte` las tablas de complejidad de [interfaz-linea.md](contracts/interfaz-linea.md) y [data-model.md](data-model.md) (registrar `O(1)` más `O(S)` cada K; recortar `O(V + S)`; consultar `O(log n + log C + S + K·a)`; memoria `O(n) + O(C·S)`). Principio I. Depende de T048 y T082. Atiende: FR-019, FR-020, FR-021. Archivo: Modelo/LineaTiempo.py, Modelo/CopiaEstado.py, Modelo/BusquedaBinaria.py, Modelo/PuntoControl.py, Modelo/AgendaConCorte.py.
- T098 **se movió a la Fase 8, después de T101**, porque depende de sus datos.

**Punto de control 7**: T090 a T095 en verde. FR-019 y FR-020 se confirman con los datos de T101 y T098 (Fase 8).

---

## Fase 8: Mediciones `--bench` (M1 a M10)

**Propósito**: respaldar cada afirmación de rendimiento (Principio VIII). Hasta tener estos datos, las cifras del plan son
**HIPÓTESIS** (exploración previa local, no versionada). Cripta sintética de 20 salas (100 y 200 donde se indique) en carpeta
temporal, sin red; **partidas de 5 000 acciones deterministas por semilla** (1, 2 y 3); cada medición se repite y se toma la
mediana, el p95 y el máximo.

- [ ] T099 Crear `tests/bench_linea.py` con la base común: generador de partidas deterministas por semilla (reusa `tests/utiles_linea.py`), cripta sintética sin datos de ninguna cripta real, repeticiones con mediana, p95 y máximo, y escritura de `resultados_bench_linea.txt` con equipo y versión de Python. Atiende: SC-007, SC-002. Archivo: tests/bench_linea.py.
- [ ] T100 [P] Crear `tests/test_bench_linea.py`: cada medición `Mn` que agregan T101 a T110 se invoca con tamaños mínimos (n ≤ 50, un solo K, una repetición), sin red y sin `VistaConsola`, y escribe su línea en `resultados_bench_linea.txt`; no afirma tiempos. Se amplía con cada medición que sube y queda completa (M1 a M10) cuando termina T110. Depende de T099. Atiende: SC-009, SC-007. Archivo: tests/test_bench_linea.py.
- [ ] T101 M1: tiempo de `historia` (instantes y acciones repartidos en toda la partida) con K ∈ {1, 10, 50, 100, 500} y la **alternativa sin puntos de control** (un único punto en la acción 0), n = 5 000. Criterio: 100 % de las consultas < 50 ms con el K por defecto. Depende de T099. Atiende: FR-020, FR-018, SC-002, SC-007. Archivo: tests/bench_linea.py.
- [ ] T098 [US6] (movida aquí desde la Fase 7) Si T101 (o T090) no cumple 50 ms, ajustar antes de seguir: plan B de [Riesgos](plan.md#riesgos) (copia a mano por campos del estado vivo o menos trabajo por materializar), decidido con los datos de M1 y M3 (T103); es solo una opción de rendimiento, pues el profesor autorizó `deepcopy` con `memo` (T003); si cumple, dejarlo escrito aquí y marcarla hecha sin cambios. Depende de T090 y T101. Atiende: FR-020, SC-002. Archivo: Modelo/CopiaEstado.py, Modelo/LineaTiempo.py.
- [ ] T102 M2: memoria de la línea (`tracemalloc`) y bytes por punto con los mismos K y la alternativa sin puntos; n ∈ {2 500, 5 000, 10 000}. Criterio: duplicar n duplica la memoria; puntos ≤ ⌈n/K⌉ + 1 + L + P. Depende de T099. Atiende: FR-021, SC-006, SC-007. Archivo: tests/bench_linea.py.
- [ ] T103 M3: costo de una copia y de materializar con N ∈ {20, 60, 200, 2 000}: `deepcopy` a secas frente a la estructurada. Fija el límite de escala (P-D06) y decide el plan B de T098. **Se vuelve a medir y las cifras de T003 son la referencia** ([research.md](research.md#t003-revisión-de-deepcopy-y-memo-2026-11-12): 0.7 a 1.4 ms y 20 KiB con N = 20, 2.7 a 4.4 ms y 62 KiB con N = 200, 17.8 a 30.0 ms y 407 KiB con N = 2 000). **Referencia nueva: las cifras de la sección «T018: medición de copiar con grafo_cripta y espacio_busqueda (2026-11-13)» de [research.md](research.md)** (con `grafo_cripta` y `espacio_busqueda` incluidos y motor tras 10 acciones: 0.81 ms y 15 KiB con N = 20, 3.87 ms y 74 KiB con N = 200, 42.5 ms y 664 KiB con N = 2 000). Depende de T099. Atiende: FR-017, FR-020. Archivo: tests/bench_linea.py.
- [ ] T104 M4: costo del recorte (`retroceder`) en partidas de 500, 5 000 y 50 000 acciones. Criterio: tiempo casi constante; **fija el umbral numérico de SC-010** (Constitución VIII). Depende de T099. Atiende: FR-027, SC-010. Archivo: tests/bench_linea.py.
- [ ] T105 M5: sobrecosto de registrar por acción en el ciclo del juego, con y sin línea, mediana, p95 y máximo incluidos los picos de copia. Criterio: p95 < 20 ms (§5.2). Depende de T099. Atiende: FR-021, FR-017. Archivo: tests/bench_linea.py.
- [ ] T106 M6: carga: tiempo de reconstrucción y tamaño del bloque para n ∈ {1 000, 5 000, 20 000}, con K distintos, con y sin `@cargar`; comparar el tamaño del guion con `len(pickle.dumps(punto))` solo como cota de referencia de guardar puntos completos. Respalda la decisión 2 (guardar el guion). Depende de T099 y T085. Atiende: FR-022, FR-031. Archivo: tests/bench_linea.py.
- [ ] T107 M7: equivalencia de contenido (no de tiempo): los mismos 100 instantes con K ∈ {1, 50, 500} y 3 semillas dan resúmenes idénticos. Depende de T099. Atiende: FR-028, SC-003. Archivo: tests/bench_linea.py.
- [ ] T108 M8: `--replay --hasta` de principio a fin, con y sin `--checkpoint-cada`. Informa; el costo es el de un replay completo. Depende de T099 y T062. Atiende: FR-011, FR-028. Archivo: tests/bench_linea.py.
- [ ] T109 M9: oráculo de la copia: estructurada frente a `deepcopy` completo con N ≤ 60, resúmenes iguales (repite T012 a escala de medición). Depende de T099. Atiende: FR-017, FR-021. Archivo: tests/bench_linea.py.
- [ ] T110 M10: **repetición de P1 §4.6 con la carga nueva** (§5.6 y §6.3): el `bench_retroceso` de `tests/bench_personaC.py` (5 intervalos × 50 cambios; registrar y deshacer) **antes** (solo `Historial`) y **después** (con la `LineaTiempo` registrando cada acción y recortando en cada `retroceder`), más un `retroceder` real con la línea en partidas de 500, 5 000 y 50 000 acciones y 3 semillas. Salida: tabla **antes y después** para `DECISIONES.md`; si el `Historial` sigue siendo adecuado se muestra con los datos, y si no, se cambia y se documenta. La agenda (P1 §4.1) no se mide aquí [PERSONAS: grupo]. Depende de T099 y T047. Atiende: FR-014, FR-027, SC-010. Archivo: tests/bench_linea.py.
- [ ] T111 [PERSONAS: B, C] Enganchar `bench_linea` al despachador de `--bench` de `main.py` (sin red y sin vista; escribe `resultados_bench_linea.txt`); `--bench` sigue ignorando `--hasta` y `--checkpoint-cada`. **Implementa: D (decidido en T005, 2026-11-12; por confirmar con C)**; C es dueña de `main.py` y avisa los cambios de su bench antes de que D lo toque. Commit pequeño y separado. Depende de T101 a T110. Atiende: SC-007, FR-018. Archivo: main.py.
- [ ] T112 Correr `py main.py --bench` y guardar `resultados_bench_linea.txt`; reemplazar en la documentación todas las cifras **HIPÓTESIS** de la exploración previa por las medidas, o dejar escrito cuáles siguen sin medir. Depende de T111. Atiende: SC-002, SC-006, SC-007, SC-010. Archivo: resultados_bench_linea.txt.
- [ ] T113 Justificar el **K por defecto** con M1 y M2 (al menos tres valores de K y la alternativa sin puntos de control): fijar la constante única del K por defecto, hoy 50 (**HIPÓTESIS**), y dejar la tabla en `DECISIONES.md` y **en su párrafo del README** (K por defecto con su medición; UTF-16, con aviso al grupo). Si el valor cambia, actualizar la constante y los textos que dicen 50. Depende de T112. Atiende: FR-018, SC-007, SC-002. Archivo: Modelo/LineaTiempo.py, resultados_bench_linea.txt.

**Punto de control 8**: `python main.py --bench` genera `resultados_bench_linea.txt` con M1 a M10; el K por defecto está justificado; M10 con tabla antes y después.

---

## Fase 9: Documentación, revisión y cierre

**Propósito**: documentar lo que quedó con datos medidos y cerrar las revisiones. El README está en UTF-16 LE con CRLF: conservar
la codificación y avisar al grupo antes de editarlo.

- [ ] T114 Crear `DECISIONES.md` en la raíz con una sección por cada uno de los **cambios 1, 2 y 3** del plan: (1) «Cambio» pasa a «acción registrada»; (2) se guarda el guion y K y los puntos se reconstruyen al cargar; (3) puntos extra tras un retroceso y una carga. Cada una cita el enunciado (§3.6 y §5.5, tal como los registra el plan), la **alternativa descartada** (invertir cambios hacia atrás; guardar puntos completos; reemplazar el punto previo) y las mediciones **M1, M2, M4 y M6**; agrega la tabla **antes y después de M10** y el K por defecto. **Condición de C (T002)**: la sección del cambio 3 cita literalmente el enunciado (§3.6, «Restricción de memoria»: «Se permite guardar copias completas del estado, llamadas puntos de control, pero no más de una cada K acciones del jugador») y las mediciones que lo respaldan (M4 y M6; M7 respalda SC-003). Anota también que el punto de control incluye el estado de `random.Random`, como exige el enunciado si se re-simula, y que el `memo` de `deepcopy` está autorizado por el profesor el 2026-11-12 (cita literal: «Para este proyecto sí pueden usar el dict como caché. No hay problema»). Marca como hipótesis lo no medido. Depende de T112 y T113. Atiende: FR-021, FR-022, FR-017, SC-006, SC-007, SC-010. Archivo: DECISIONES.md.
- [ ] T115 [PERSONAS: C] **Implementa: D (decidido en T005, 2026-11-12), que redacta los párrafos que su tarea hace visibles; C coordina**, avisando al grupo; el README está en UTF-16 con CRLF. **Revisión final de coherencia del README**: cada párrafo ya subió con su tarea (T036: comando `historia` y la nota `retroceder` frente a `historia`; T063b: opciones `--hasta` y `--checkpoint-cada`; T085: `CRPT` 3 con la línea y el error de carga sin datos locales; T113: K por defecto con su medición). T115 comprueba que no se contradigan entre sí ni con el comportamiento real: el rechazo de `--bitacora` igual a `<guardado>.log` (`guardar` rechaza el comando y la partida sigue; solo `--cargar` sale con código 1), la tabla de opciones y de códigos de salida, y la versión del `CRPT`; corrige lo que falte. Depende de T036, T063b, T085 y T113. Atiende: FR-010, FR-023, FR-031. Archivo: README.md.
- [ ] T116 Aportar a `PROMPTS_LLM.md` (raíz; lo arma 001-T004 a partir de las notas de cada persona) **solo los prompts reales** de esta capacidad, cada uno con fecha, modelo, prompt textual y para qué se usó: el `/speckit-plan`, el `/speckit-tasks` y los demás prompts con texto propio. No se inventan entradas ni se reconstruyen prompts de memoria. Atiende: Principio XI, sin FR. Archivo: PROMPTS_LLM.md.
- [ ] T117 [PERSONAS: grupo] Mi revisión de `Bitacora/`, `Persistencia/` y `main.py` (es la `001-T117`, que la constitución asigna a la persona D): revisar los cambios de T061, T063a, T063b, T084, T086, T087 y T111 contra el [contrato de la bitácora](contracts/formato-bitacora.md) y el [formato de partida](contracts/formato-partida.md); comprobar `Historial` y `retroceso.py` sin cambios. Atiende: FR-024, FR-025, FR-030. Archivo: Bitacora/, Persistencia/, main.py (revisión).
- [ ] T118 [PERSONAS: A] Repetir T079 con el enemigo de comportamiento «cazador» real de A (no hay clase `Cazador`; `003-T045` a `003-T048`, previsto el viernes 13; luego `003-T058` y `003-T059`), retirando el doble de T010. `[BLOQUEADA: cazador de A]`: sigue bloqueada hasta `003-T048`. No bloquea el cierre de esta capacidad; deja constancia en la matriz si llega tarde. Depende de T079 y T089. **Repetir con el cazador real de A y el registro de decisiones de 003-T076 si cuelga del motor.** Atiende: FR-025. Archivo: tests/test_linea_cazadores.py, tests/utiles_linea.py.
- [ ] T119 [P] Probar el cumplimiento de las restricciones de producción (Principio I) leyendo el código fuente de los archivos nuevos de `Modelo/`, `DTOS/`, `Gestor/`, `Persistencia/RegistroLinea.py`, `Controlador/ObservadorLinea.py`, `Controlador/ReconstructorLinea.py` y `Controlador/ConsultaHistoria.py`: falla si aparecen `bisect`, `sorted(`, `.sort(`, `heapq`, `collections`, `dict` o `set` como índice (la única excepción por nombre es el `memo` de `Modelo/CopiaEstado.py`, con su comentario). Atiende: FR-019, FR-020, FR-021. Archivo: tests/test_linea_restricciones.py.
- [ ] T120 [P] Probar que ninguna prueba de esta capacidad depende de `partida.cripta`, `partida.cripta.log` ni `partida.log`: lee `tests/test_linea_*.py`, `tests/test_cli_historia.py` y `tests/utiles_linea.py` y falla si aparece alguno de esos nombres; además comprueba, con una prueba que corre el controlador y `main` con las rutas de `partida_linea` (T009), que **no se crea `partida.log`** (ni `partida.cripta` ni `partida.cripta.log`) en la raíz del repositorio. Atiende: FR-024, SC-009. Archivo: tests/test_linea_restricciones.py.
- [ ] T121 Recorrer los escenarios 1 a 16 del [quickstart](quickstart.md) y la verificación manual de humo (`--offline paquete/`, `historia 0`, `historia #3`, `guardar`, `--cargar`, `--replay --hasta 150`, `--hasta` sin `--replay`, `--cargar` con `--checkpoint-cada`, `--cargar` con `--bitacora` igual al `.log`, datos locales borrados) y correr la suite completa; anotar el resultado y lo que siga bloqueado en la tabla de [trazabilidad](#trazabilidad-fr-y-sc--tareas). Depende de T085, T087, T112 y T115. Atiende: SC-001, SC-009, SC-003, SC-005. Archivo: specs/004-linea-de-tiempo/tasks.md.
- [ ] T122 **Final**: avisar a C y pedir su revisión. Un solo mensaje con los commits pequeños y separados: T084 (bloque de la línea en `ArchivoPartida.py` y `guardar_motor`), T035, T036, T085, T086, T088 y T115 (`ControladorPartida.py`, `VistaConsola.py`, `ExportadorJSON.py`, README), T063a, T063b y T111 (`main.py`), cada uno con su prueba (T061, el `Reproductor`, y T087, el rechazo de la bitácora, ya están en `main` por C) y el cambio exacto de [Enganches](plan.md#enganches-y-requisitos-hacia-otras-personas). La acción 3 del gate del plan (aceptación de C al `observador` y al rechazo de la bitácora) ya está cumplida por los commits `b1b57d7` y `b6f9f52`. Atiende: FR-025, FR-030, FR-022, SC-009. Archivo: Controlador/ControladorPartida.py, Persistencia/ArchivoPartida.py, main.py, Bitacora/Reproductor.py (aviso).

- [ ] T123 [PERSONAS: B] Enviar a la persona B la nota para `specs/002-resolubilidad/contracts/cli-verificacion.md` (fila «[PERSONAS: B]» de [Enganches](plan.md#enganches-y-requisitos-hacia-otras-personas)): `--hasta` y `--checkpoint-cada` son modificadores, no modos, y **no cambian la tabla de prioridad** `--bench > --mostrar-puntajes > --verificar > --replay > --cargar > --cripta`; el detalle de combinaciones está en [comandos-historia.md](contracts/comandos-historia.md#combinaciones-con-la-prioridad-de-la-capacidad-002) (por ejemplo `--verificar X --hasta 5` sin `--replay` es error de uso, código 1, y `--verificar X --forzar --checkpoint-cada 10` ignora las dos). Solo documentación en el archivo de B; no se toca su código. Se envía junto con T122. Atiende: FR-013, FR-018. Archivo: specs/002-resolubilidad/contracts/cli-verificacion.md (de B, solo el envío).

**Punto de control 9**: matriz completa, ninguna afirmación de rendimiento sin medición, suite en verde. La capacidad se da por
terminada cuando no queda ninguna fila bloqueada, salvo T118 si A no ha subido su cazador (se deja constancia).

---

## Orden del README

La constitución exige el README **en el mismo cambio** que el comportamiento visible (Flujo de desarrollo). El README está en
UTF-16 LE con CRLF: conservar la codificación y avisar al grupo antes de editarlo. Cada párrafo sube **con la tarea que lo hace
visible**; T115 queda como revisión final de coherencia (sigue la sección «Orden del README» de
[001/tasks.md](../001-niebla-mapa-ir-a/tasks.md)).

| Fase | Sección del README | Tarea |
|------|--------------------|-------|
| 0 y 1 | Ninguna: no cambian nada visible | — |
| 2 | `### Comandos de juego`: `historia <t>` y `historia #k`; nota de que `retroceder` y `historia` son mecanismos distintos | T036 |
| 5 | Tabla de opciones: `--hasta` y `--checkpoint-cada`; `--replay --hasta` | T063b (T063a sube en el mismo push) |
| 6 | `### Guardar` y `### Cargar`: `CRPT` 3 con el bloque de la línea; error de carga sin datos locales | T085 (T084 sube en el mismo push) |
| 8 | K por defecto con su medición y `### Mediciones (`--bench`)` | T113 |
| 9 | Revisión final de coherencia de todo lo anterior | T115 |

## Dependencias

```text
Fase 0 ─ Fase 1 ─ Fase 2 (US1, MVP) ─┬─ Fase 3 (US2) ─ Fase 4 (US3)
                                     ├─ Fase 5 (US4) ──┐
                                     └─ Fase 7 (US6)   ├─ Fase 6 (US5, persistencia) ─┐
                                                       │                              ├─ Fase 8 (bench) ─ Fase 9
T002 (hecha 2026-11-12) ─ todo commit de código  └─ T061 (C) ─ T062, T083 ──────┘
T003 (hecha 2026-11-12) ─ T015                  T084 (bloque) ─ T085 (cargar) ─ T086, T106
T004, T061 y T087 hechas (C: b1b57d7 y b6f9f52) ─ T062, T083 y T080 ya pueden empezar
T005 (decidida 2026-11-12): D implementa T035, T036, T063a, T063b, T085, T086, T088, T066, T111 (T111 por confirmar con C);
     C es dueña de ControladorPartida.py y main.py (revisa y resuelve el merge) y coordina T115 (D redacta sus párrafos)
     Orden: 001-T062 a T065 (C, esta semana) ─ T035, T036 (local hasta T047) ─ T063a, T063b (con B) ─ T085, T086 (tras T084)
            ─ T088, T066, T111, T115
T047 ─ T035 y T036 (no suben a main antes que T047)
T063a ─ T059, T060, T077, T095 (sus pruebas); T062 ─ T063b
```

- Las fases 3 y 7 dependen de la 2; la 4 solo agrega pruebas sobre lo ya hecho. La Fase 5 necesita de la 2 y de T061.
- La Fase 6 necesita de la 3 (`registrar_retroceso` va en el guion) y de T061. Su mitad de modelo (T064 a T069, T081, T082) avanza sin C.
- Las fases 2 a 4 y 7 **no esperan a C**: cada cambio en un archivo de C va en un commit pequeño, con su prueba, y nada del núcleo depende de él salvo lo indicado.
- Dos tareas del mismo archivo van en serie aunque lleven `[P]`.

### Tareas que dependen de otras personas

| Tarea | Quién | Qué necesita | Si no llega |
|-------|-------|--------------|-------------|
| T002 | Grupo | **Hecha (2026-11-12)**: A, B y C aceptan los cambios de la spec | Nada pendiente |
| T003 | Grupo | **Hecha (2026-11-12)**: el profesor autoriza `copy.deepcopy` con `memo` (el `dict` como caché) | Nada pendiente; T098 solo como opción de rendimiento |
| T004, T061 | C | **Hechas** (001-T123/T124, `b1b57d7`): `observador` y `reproducir_acciones` ya están en `main` | Nada pendiente; 001-T125 (aviso a D) cumplida por mensaje de C |
| T005 | C | **Decidida (2026-11-12)**: D implementa T035, T036, T063a, T063b, T085, T086, T088, T066 y T111 (T111 por confirmar con C); C es dueña de `ControladorPartida.py` y `main.py` (revisa cada commit, resuelve el merge) y coordina T115 | C revisa cada commit; un turno a la vez; aviso al grupo antes de tocar `ControladorPartida.py`, `main.py` o el README; `git pull --no-edit` y subir el mismo día |
| T006, T007 | A | Excluir `Modelo/CopiaEstado.py` de `003-T015`; estado colgando del motor; registro de decisiones colgado del motor | `003-T015` falla en cuanto exista T015; el escenario 14 falla con el cazador real |
| T079, T118 | A | Subir el enemigo con `comportamiento == "cazador"` (003-T045 a T048, viernes 13; `ciclo` y `version_puertas` en 003-T015 a T017 el 2026-11-12; GrafoCripta el 2026-11-12). T118 bloqueada hasta 003-T048 | Se usa el doble de T010 marcado para repetir |
| T084 | C | Revisar el commit pequeño del bloque de la línea (la revisión se pide en T122) | Se sube con la revisión pendiente anotada |
| T087 | C | **Hecha** (001-T121, `b6f9f52`): rechazo de `--bitacora` igual a `<guardado>.log` | Nada pendiente; T080 prueba lo que 001-T120 no cubre |
| T111 | B, C | Despachador de `--bench` (lo implementa D, por confirmar con C; C avisa los cambios de su bench antes) | M1 a M10 se corren con `py -m tests.bench_linea` |
| T115 | C (coordina) y grupo | Aviso antes de editar el README (UTF-16); D redacta los párrafos que su tarea hace visibles | FR-010 y FR-023 sin cumplir: no se cierra |

## Paralelismo

| Bloque | Se puede repartir | Va en serie |
|--------|-------------------|-------------|
| Fase 0 | T002 a T008 entre sí | — |
| Fase 1, pruebas | T009, T011, T012, T013 (archivos distintos) | T010 tras T009 |
| Fase 1, código | T014 frente a T015 | T015 → T016 → T017 |
| Fase 2, pruebas | `test_linea_consulta.py` (T018 a T021), `test_linea_solo_lectura.py` (T022), `test_linea_comando.py` (T023, T024), `test_linea_resumen.py` (T025), `test_linea_agenda.py` (T026), `test_linea_sin_red.py` (T027) | Dentro de cada archivo |
| Fase 2, código | T028, T029, T030 y T032 | T031 → T033 → T034 → T035 → T036 |
| Fase 3 | T043 y T044 frente a T037 a T042 | T046 → T047 → T048 |
| Fase 4 | — | T049 → T050 → T051 → T052 |
| Fase 5, pruebas | T054, T055, T059 | Dentro de cada archivo |
| Fase 6, pruebas | T064, T065, T066, T067, T068, T069, T078, T079, T080 | T070 → … → T077 |
| Fase 6, código | T081 frente a T084; T083 tras T061 | T082 → T083 → T085 → T086 |
| Fase 7 | T090, T091, T094, T095 | T092 → T093 |
| Fase 8 | T101 a T110 comparten archivo (en serie); T100 tras cada medición | T111 → T112 → T113 |
| Fase 9 | T116, T119, T120 | T114 → T115; T121 → T122 |

## Cobertura de escenarios y edge cases

### Escenarios de aceptación de las seis historias (35)

| Escenario | Tarea de prueba | FR | Archivo de prueba |
|-----------|-----------------|----|-------------------|
| US1-1 | T018 | FR-001, FR-003, FR-006 | tests/test_linea_consulta.py |
| US1-2 | T019 | FR-001 | tests/test_linea_consulta.py |
| US1-3 | T020 | FR-004 | tests/test_linea_consulta.py |
| US1-4 | T020 | FR-004 | tests/test_linea_consulta.py |
| US1-5 | T022 | FR-008, FR-009 | tests/test_linea_solo_lectura.py |
| US1-6 | T023 | FR-005, FR-009 | tests/test_linea_comando.py |
| US1-7 | T024 | FR-010 | tests/test_linea_comando.py |
| US2-1 | T037 | FR-004, FR-015, FR-016 | tests/test_linea_retroceso.py |
| US2-2 | T038 | FR-005, FR-015 | tests/test_linea_retroceso.py |
| US2-3 | T039 | FR-015, FR-016 | tests/test_linea_retroceso.py |
| US2-4 | T040 | FR-015, FR-029 | tests/test_linea_retroceso.py |
| US2-5 | T041 | FR-004, FR-015 | tests/test_linea_retroceso.py |
| US2-6 | T042 | FR-014 | tests/test_linea_retroceso.py |
| US2-7 | T043 | FR-027, SC-010 | tests/test_linea_recorte.py |
| US2-8 | T044 | FR-029 | tests/test_linea_pergaminos.py |
| US3-1 | T050 | FR-001, FR-002 | tests/test_linea_mismo_instante.py |
| US3-2 | T051 | FR-001, FR-002 | tests/test_linea_mismo_instante.py |
| US4-1 | T055 | FR-007, FR-011 | tests/test_linea_replay_hasta.py |
| US4-2 | T056 | FR-012 | tests/test_linea_replay_hasta.py |
| US4-3 | T057 | FR-011, FR-015 | tests/test_linea_replay_hasta.py |
| US4-4 | T059 | FR-013 | tests/test_cli_historia.py |
| US4-5 | T072 | FR-025 | tests/test_linea_persistencia.py |
| US4-6 | T058 | FR-030 | tests/test_linea_replay_hasta.py |
| US5-1 | T070 | FR-022, SC-005 | tests/test_linea_persistencia.py |
| US5-2 | T071 | FR-022, FR-025 | tests/test_linea_persistencia.py |
| US5-3 | T073 | FR-024, SC-008 | tests/test_linea_persistencia.py |
| US5-4 | T074 | FR-022, FR-014 | tests/test_linea_persistencia.py |
| US5-5 | T075 | FR-024, SC-008 | tests/test_linea_persistencia.py |
| US5-6 | T076 | FR-023 | tests/test_linea_persistencia.py |
| US5-7 | T077 | FR-031 | tests/test_linea_persistencia.py |
| US6-1 | T090 | FR-020, SC-002 | tests/test_linea_rendimiento.py |
| US6-2 | T091 | FR-017, SC-006 | tests/test_linea_memoria.py |
| US6-3 | T092 | FR-019 | tests/test_linea_memoria.py |
| US6-4 | T093 | FR-021, SC-006 | tests/test_linea_memoria.py |
| US6-5 | T094 | FR-028, SC-003 | tests/test_linea_independencia_k.py |

### Edge cases de la spec (17)

| Edge case | Tarea de prueba | FR | Archivo de prueba |
|-----------|-----------------|----|-------------------|
| `historia 0` | T021 | FR-001 | tests/test_linea_consulta.py |
| `historia <t>` con `t` igual al reloj actual | T021 | FR-003 | tests/test_linea_consulta.py |
| `t` negativo, no numérico o sin argumento | T023 | FR-005, FR-009 | tests/test_linea_comando.py |
| `#0`, `#k` no entero o mayor que acciones + 1 | T023 | FR-005, FR-009 | tests/test_linea_comando.py |
| `historia` en una partida recién iniciada | T021 | FR-003, FR-004 | tests/test_linea_consulta.py |
| Partida terminada: se consulta con `--replay --hasta` | T056 | FR-012 | tests/test_linea_replay_hasta.py |
| `--hasta` sin `--replay` | T059 | FR-013 | tests/test_cli_historia.py |
| `--checkpoint-cada` junto con `--replay` | T060 | FR-028 | tests/test_cli_historia.py |
| `--replay --hasta` sobre bitácora de versión incompatible | T060 | FR-011, FR-024 | tests/test_cli_historia.py |
| Varias acciones con el mismo intervalo o de costo 0 | T021 | FR-004 | tests/test_linea_consulta.py |
| `--checkpoint-cada` con 0, negativo o no entero; K = 1 válido | T095 | FR-018 | tests/test_cli_historia.py |
| Instante entre dos acciones del jugador | T021 | FR-001 | tests/test_linea_consulta.py |
| Consulta tras cargar una partida | T070 | FR-022 | tests/test_linea_persistencia.py |
| (a) Cargar sin datos locales: código 1, nada cargado, partida en curso intacta | T078 | FR-022, FR-025 | tests/test_linea_carga_sin_datos.py |
| (b) `--bitacora` igual a `<guardado>.log` al guardar o cargar: código 1 | T080 | FR-025, FR-030 | tests/test_linea_bitacora_guardado.py |
| Consulta durante un viaje «ir a»: no aplica; cada paso es una acción | T021 | FR-004 | tests/test_linea_consulta.py |
| Intervalos descartados sin acciones ni puntos huérfanos | T045 | FR-015, FR-016 | tests/test_linea_retroceso.py |

### Escenarios 1 a 16 del quickstart

| # | Escenario | Tarea de prueba | Requisitos | Archivo de prueba |
|---|-----------|-----------------|------------|-------------------|
| 1 | Estado en `t` y en `#k` | T018 | FR-001, FR-003, FR-004, FR-006 | tests/test_linea_consulta.py |
| 2 | La consulta no cambia nada | T022 | FR-008, FR-009 | tests/test_linea_solo_lectura.py |
| 3 | Varios eventos en un mismo instante | T050, T052 | FR-001, FR-002 | tests/test_linea_mismo_instante.py |
| 4 | Rechazos | T023 | FR-005, FR-009 | tests/test_linea_comando.py |
| 5 | Retrocesos | T037, T040 | FR-014, FR-015, FR-016, FR-029 | tests/test_linea_retroceso.py |
| 6 | Cinco usos seguidos y un sexto | T042 | FR-014 | tests/test_linea_retroceso.py |
| 7 | Pergaminos por instante | T044 | FR-029 | tests/test_linea_pergaminos.py |
| 8 | `--replay --hasta` | T055 | FR-007, FR-011, FR-012, FR-025 | tests/test_linea_replay_hasta.py |
| 9 | Guardar, cargar, continuar | T070, T071, T072 | FR-022, FR-025, FR-030, SC-005 | tests/test_linea_persistencia.py |
| 10 | Versiones y opciones | T059, T075, T077, T095 | FR-013, FR-018, FR-023, FR-024, FR-031, SC-008 | tests/test_cli_historia.py, tests/test_linea_persistencia.py |
| 11 | Independencia de K | T094 | FR-028, SC-003 | tests/test_linea_independencia_k.py |
| 12 | Oráculo de la copia | T012 | FR-017, FR-021 | tests/test_linea_copia.py |
| 13 | Sin solicitudes | T027 | FR-008, FR-025 | tests/test_linea_sin_red.py |
| 14 | Estado de A | T079 | FR-025, FR-001 | tests/test_linea_cazadores.py |
| 15 | Cargar sin datos locales | T078 | FR-022, FR-025 | tests/test_linea_carga_sin_datos.py |
| 16 | Bitácora igual a `<guardado>.log` | T080 | FR-025, FR-030 | tests/test_linea_bitacora_guardado.py |

## Trazabilidad FR y SC → tareas

Los 30 FR vigentes (FR-001 a FR-031, **sin FR-026**, que no existe) y los 10 SC. Una fila no está completa hasta que las tareas
bloqueadas o pendientes terminen.

| Requisito | Tareas |
|-----------|--------|
| FR-001 | T018, T019, T020, T021, T026, T033, T050, T051, T052, T053, T079 |
| FR-002 | T026, T028, T033, T049, T050, T051, T053 |
| FR-003 | T018, T021, T033, T036 |
| FR-004 | T020, T021, T033, T036, T037, T041 |
| FR-005 | T023, T033, T036, T038 |
| FR-006 | T018, T025, T031, T032 |
| FR-007 | T025, T030, T031, T032, T055 |
| FR-008 | T009, T012, T016, T022, T023, T027, T029, T035 |
| FR-009 | T022, T023, T035, T036 |
| FR-010 | T024, T036, T115 |
| FR-011 | T054, T055, T057, T060, T062, T063b, T108 |
| FR-012 | T056, T062, T063b |
| FR-013 | T059, T063a, T063b, T123 |
| FR-014 | T040, T042, T074, T110 |
| FR-015 | T037, T038, T039, T040, T041, T045, T047, T057 |
| FR-016 | T013, T017, T034, T037, T039, T045, T047 |
| FR-017 | T002, T012, T015, T016, T013, T017, T068, T091, T103, T105, T109 |
| FR-018 | T013, T063a, T063b, T095, T101, T111, T113, T123 |
| FR-019 | T011, T014, T033, T092, T096, T097, T119 |
| FR-020 | T011, T014, T090, T097, T098, T101, T103, T119 |
| FR-021 | T002, T012, T015, T016, T013, T017, T093, T097, T102, T105, T109, T114, T119 |
| FR-022 | T064, T065, T066, T068, T069, T070, T071, T074, T078, T081, T082, T083, T085, T088, T106, T114 |
| FR-023 | T065, T076, T084, T115 |
| FR-024 | T008, T060, T064, T065, T067, T073, T075, T084, T086, T117, T120 |
| FR-025 | T004, T007, T010, T027, T029, T034, T035, T054, T069, T071, T072, T078, T079, T080, T083, T085, T087, T089, T117, T118, T122 |
| FR-027 | T043, T047, T104, T110 |
| FR-028 | T007, T031, T032, T060, T094, T107, T108 |
| FR-029 | T040, T044, T046, T048 |
| FR-030 | T004, T054, T058, T062, T068, T072, T080, T083, T087, T117, T122 |
| FR-031 | T063a, T064, T069, T077, T081, T082, T085, T086, T106 |
| SC-001 | T121 |
| SC-002 | T090, T098, T099, T101, T112, T113 |
| SC-003 | T009, T018, T094, T107, T121 |
| SC-004 | T022 |
| SC-005 | T070, T121 |
| SC-006 | T091, T093, T102, T112, T114 |
| SC-007 | T099, T100, T101, T102, T111, T112, T113, T114 |
| SC-008 | T073, T075 |
| SC-009 | T001, T100, T120, T121, T122 |
| SC-010 | T043, T047, T104, T110, T112, T114 |

**Tareas sin FR ni SC**: solo T116 (`PROMPTS_LLM.md`, Principio XI). Todas las demás citan al menos un FR o un SC.

## Estrategia de implementación

### MVP

Fases 0 a 2: `historia <t>` e `historia #k` en la partida real, sin alterar el presente (Historia 1). Es lo que se demuestra primero.
Con las fases 3 y 4 las tres historias P1 están completas.

### Calendario propuesto (hoy: jueves 12; entrega: miércoles 18)

| Día | Meta |
|-----|------|
| Jue 12 (hoy) | Decisiones T002, T003 y T005 registradas; A sube GrafoCripta y 003-T015 a T017 (`ciclo`, `version_puertas`) esa noche |
| Vie 13 | Fases 1 y 2 (T009 a T034); A sube el cazador real (003-T045 a T048) |
| Sáb 14 | Fases 3 y 4 (incluye T046 y T047); T035 y T036 suben tras T047 |
| Dom 15 | Fase 5 (T054 a T063b, con B) |
| Lun 16 | Fases 6 y 7 |
| Mar 17 | Fases 8 y 9 (bench, `DECISIONES.md`, T117, T122) |
| **Mié 18** | Entrega |

El corte mínimo no cambia.

### Corte mínimo si falta tiempo

Nada de lo que el enunciado exige se difiere. Se mantiene **obligatorio**: `historia <t>` y `historia #k` (Fase 2 y Fase 3),
`--replay --hasta` (Fase 5), `--checkpoint-cada` (T063a, T063b, T095), guardar y cargar la línea (Fase 6), `--bench` con **al menos
tres valores de K y la alternativa sin puntos de control** (T099, T101, T102, T111 a T113), **M10** (T110), y la documentación
(T114, T115). También se mantienen M4 y M6, que respaldan los cambios 2 y 3 en `DECISIONES.md`, y M7, que respalda SC-003.

Lo que **puede diferirse sin perder nada exigido**, en este orden:

1. T098 (plan B de la copia), solo si T090 cumple; y T053 si T050 a T052 pasan a la primera.
2. M3 (T103), M5 (T105), M8 (T108) y M9 (T109): informan escala, sobrecosto de registrar y duplican T012. Si se difieren, sus cifras
   quedan marcadas **HIPÓTESIS** en el README y en `DECISIONES.md` (Principio VIII), no se afirman.
3. T066 y T088 (clave `linea` en `ExportadorJSON`), que no son parte del enunciado.
4. T100 (prueba rápida de `bench_linea`), siempre que la suite sin ella siga en verde.
5. T118 (repetir con el cazador real), que depende de A.

Las pruebas de T054 y la rama `@cargar` de T058 siguen el calendario de C (T061) y no cambian este corte.

### Entrega incremental

Cada subida a `main` lleva la suite en verde (T001 como referencia). Antes de T085 no se presenta guardar y cargar la línea como
cumplido; antes de T112 no se afirma ninguna cifra de rendimiento como medida. Ningún commit que conecte el controlador a la línea
(T035, T036) sube a main sin T047, para que `retroceder` no rompa el juego real.

---

## Contradicciones y dudas entre documentos

No se modificaron `spec.md` ni `plan.md`; esto es lo que encontré al cruzar los documentos.

1. *(Resuelta: ver «Resueltas» al final.)*
2. *(Resuelta: ver «Resueltas» al final.)*
3. **«Antes de jugar» frente a «al guardar o cargar».** El pedido dice que C rechaza `--bitacora` igual a `<guardado>.log` «antes de
   jugar»; el contrato (`formato-bitacora.md`) y `plan.md` dicen «al guardar y al cargar». Solo `--cargar F --bitacora F.log` se puede
   rechazar antes de jugar: en `guardar p.cripta` el destino se conoce durante la partida. No está definido si ese error termina el
   proceso o solo rechaza el comando. T080 prueba el rechazo sin fijar eso; aclarar con C.
4. **«Documento de Decisiones».** `plan.md`, `quickstart.md` y este pedido hablan de `DECISIONES.md`; `001/tasks.md` (T114) usa
   `Proyecto Cripta.docx` como Documento de Decisiones. `DECISIONES.md` no existe en el repositorio. T114 lo crea; el grupo debe decidir
   si la fuente única es el `.md` o el `.docx`.
5. **Numeración de tareas ajenas.** `T015`, `T058`, `T059` y `T098` existen en 001 y en 003 con contenido distinto (por ejemplo, 001-T058
   es el comando `ir`; 003-T058 es la equivalencia de cazadores). Aquí van con prefijo. El pedido pide además «la tarea T117»: es la
   `001-T117` de la persona D; en este archivo es T117 por coincidencia de numeración, pero su contenido es esa revisión.
6. **FR-023 («su número de versión MUST incrementarse»).** La versión 3 la subió `001-T076`; `plan.md` (P-10) dice que esta capacidad
   **no** sube la versión. FR-023 se cumple por 001, y aquí solo se prueba (T076) y se documenta (T115): ninguna tarea de esta capacidad
   incrementa la versión.
7. **Cazador de A no está en `main`.** No hay clase `Cazador` (nunca la habrá: es un enemigo con `Enemigo.comportamiento == "cazador"`,
   decidido en el motor, 003-T046 y T048) ni `GrafoCripta` en el código (solo `Modelo/BusquedaRuta.py` y `Modelo/ColaPrioridad.py`);
   `003-T015`, `003-T058`, `003-T059` y `003-T076` están sin hacer. GrafoCripta sube el 2026-11-12; 003-T015 a T017 (`ciclo`,
   `version_puertas`) esa noche; el cazador real (003-T045 a T048) el viernes 13. Por eso T010 y T079 usan un doble y T118 queda
   `[BLOQUEADA: cazador de A]` hasta 003-T048.
8. **Redacción de la spec (no se tocó).** El Edge «`--checkpoint-cada` junto con `--replay`» repite «(FR-028)» y «no cambia ningún
   resumen» dos veces, y ya no cita FR-031; la entidad «Línea de tiempo» sigue diciendo «lo que cambió» y FR-021 «cambios de estado»
   (el vocabulario se aclaró en la entidad «Acción registrada»).
9. **Sin FR ni SC.** La tarea T116 (`PROMPTS_LLM.md`) no tiene un FR o SC natural; la exige el Principio XI y se dejó sin inventar uno.
10. **Línea base.** `quickstart.md` y `plan.md` dicen «todo en verde»; hoy son 405 pruebas con 10 omitidas (`skipped=10`), así que «en
    verde» incluye esas omisiones. T001 las registra para no confundirlas con una regresión.

### Resueltas

1. **«No bloquea» frente a la carga.** Resuelta: C implementó el `observador` y `reproducir_acciones` (001-T123 y 001-T124, commit
   `b1b57d7`), así que T061 está hecha y ya no hay nada que esperar para T062, T083 ni T063b. El aviso 001-T125 (a D, P-D02) está
   cumplido por mensaje de C.
2. **Nombre de la entrada del `Reproductor`.** Resuelta: es `reproducir_acciones(encabezado, acciones) -> motor`, con
   `reproducir(ruta) -> motor` que solo lee la bitácora y la llama; coincide con `research.md` (HL6), `plan.md`, los contratos y T083.
3. **Quién implementa la fila (d) y quién es dueño del merge (T005, P-D07).** Resuelta el 2026-11-12: el plan y las tareas dejaban
   T035, T036, T063a, T063b, T085, T086, T088, T066, T111 y T115 como «implementa: por decidir» y `main.py` y `ControladorPartida.py`
   sin dueño. Decisión de C: D implementa (T111 por confirmar con C), C es dueña de ambos archivos y coordina T115; orden y reglas en T005.
   (No había una contradicción redactada sobre esto en la lista anterior; se registra aquí.)
