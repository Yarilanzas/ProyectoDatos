---
description: "Lista de tareas: niebla de guerra, mapa conocido y viaje «ir a»"
---

# Tasks: Niebla de guerra, mapa conocido y viaje automático «ir a»

**Input**: `specs/001-niebla-mapa-ir-a/` ([spec](spec.md), [plan](plan.md), [research](research.md),
[data-model](data-model.md), [contracts](contracts/), [quickstart](quickstart.md))

**Prerrequisitos**: spec y plan confirmados en Git antes del código (Principio IX). Se trabaja sobre `main`, con
`git pull` antes de subir y la suite en verde en cada subida.

**Pruebas**: obligatorias (Principios V y X). Cada prueba cita su FR en el nombre o en un comentario, usa `unittest`
y no usa la red.

## Formato

`- [ ] T000 [P] [US1] [marcas] Descripción. Atiende: FR, PR. Archivo: ruta.`

| Marca | Significado |
|-------|-------------|
| `[P]` | Se puede hacer en paralelo con tareas de **otros archivos** de su bloque. Dos tareas del mismo archivo van en serie, aunque ambas lleven `[P]` |
| `[US1]`…`[US5]` | Historia de la spec. Las fases 0, 1, 6 y 7 no llevan historia |
| `[BLOQUEADA: BusquedaRuta.py]` | No se puede empezar hasta que Persona A suba `Modelo/BusquedaRuta.py`, la búsqueda compartida con el cazador (D-PEND-01, resuelta con la opción A) |
| `[PERSONAS: …]` | Depende de otra persona o de una respuesta del grupo |
| `[a cargo de quien implemente §3.1]` | Corresponde a la capacidad de terreno y costos. Se conserva como referencia y esta capacidad no la ejecuta |
| `Escenario USx-n` | Escenario de aceptación n de la historia x. Tabla completa en [Cobertura](#cobertura-de-escenarios-de-aceptación) |

Los `§` citados (§3.1, §6.1…) son del enunciado, que no está en el repositorio: se toman tal como los registra el plan.

---

## Fase 0: Preparación

**Propósito**: dejar el entorno y las dependencias con el grupo listos antes de tocar código. Esta fase no estaba en el
pedido: reúne lo que las fases 1 a 7 necesitan y que no pertenece a ninguna de ellas.

- [X] T001 Instalar `requests` en `.venv` y registrar la línea base con `python -m unittest discover -s tests -v`. Esperado: 128 de 128 (research, línea base). Si no da eso, detenerse y aclararlo antes de seguir. Atiende: SC-006, PR-16. Archivo: tests/ (solo lectura).
- [ ] T002 [a cargo de quien implemente §3.1] Avisar al grupo, antes de T010, del cambio del DTO `Salida` (contrato compartido). Es solo de la capacidad de terreno y costos, que también cambia `mover` (P-02 resuelta): no bloquea esta capacidad, que solo lee el costo (T118). Atiende: FR-005, FR-025. Archivo: DTOS/Salida.py (aviso previo).
- [X] T003 Corregir la spec en una confirmación separada y anterior al código (Principio IX): esta capacidad solo lee el costo, el campo `costo` y su cobro en `mover` son de la capacidad de terreno y costos, y se agrega SC-007. **Hecho en `6ed5b92`**, anterior al primer código (`89dcb7a`). Registrar el dominio de `costo` de §3.1 y qué pasa con un dato inválido o asimétrico queda a cargo de la capacidad de terreno y costos (T006, T008). Atiende: FR-005, FR-024, PR-13, SC-007. Archivo: specs/001-niebla-mapa-ir-a/spec.md.
- [X] T005 [P] Crear las utilidades de prueba: `crear_paquete_niebla(carpeta, salas, ...)`, que genera un paquete offline con topología, costos, puertas, llaves, antorcha, pergaminos, veneno, enemigos y trampas (formato de `crear_paquete_offline`), y `partida_niebla(...)`, que devuelve motor y controlador con `VistaFalsa`. El archivo no lleva prefijo `test`, así que `discover` no lo ejecuta. Atiende: SC-001, PR-16. Archivo: tests/utiles_niebla.py.
- [X] T061 [PERSONAS: grupo, P-05] Confirmar que «las dos salas que conecta» observa la salida dirigida `A→B` desde `B`, y que el viaje puede volver por `B→A`. Anotar la respuesta en P-05. Si es negativa, corregir la spec y luego T026 y T016. **Hecho**: confirmada por Personas A y B y anotada en P-05; se mantiene la lectura del plan y no cambian la spec, T016 ni T026. Atiende: FR-006, PR-02. Archivo: specs/001-niebla-mapa-ir-a/plan.md.

**Punto de control 0**: línea base conocida (T001) y spec corregida y confirmada en Git (T003, `6ed5b92`). Sin esto no
empieza la Fase 1. T002 es solo de la capacidad de terreno y costos y no bloquea ninguna fase de esta. P-05 (T061) está
confirmada por Personas A y B: el viaje puede volver por `B→A`, y T016 y T026 ya aplican esa lectura.

---

## Fase 1: Costo de salida y acceso único (solo lectura)

**Propósito**: esta capacidad solo lee el costo de cada salida, por `motor.costo_salida`. Bloquea las fases 3 y 4, que
muestran y usan ese costo. Implementar el costo de §3.1 para todos los actores corresponde a la capacidad de terreno y
costos (spec, Assumptions).

**Prueba independiente**: `costo_salida` devuelve el costo de la salida, o 100 si no lo trae, y ningún movimiento cambia.

### Tarea de esta capacidad

La única tarea es T118. Lleva ese número porque las demás no se renumeraron.

- [X] T118 Crear `motor.costo_salida(salida)`, solo de lectura, junto con `COSTO_MOVER = 100`: devuelve `getattr(salida, "costo", None)`, o 100 si no lo trae. **No** cambiar el movimiento de ningún actor: `mover_jugador`, `mover_enemigo` y `ejecutar_evento` quedan igual. Es el único acceso al costo. Probar costo propio, salida sin el atributo y que `mover` sigue costando 100, citando FR-005. Atiende: FR-005, FR-024, PR-13. Archivo: Modelo/MotorSimulacion.py, tests/test_costo_salida.py.

### A cargo de quien implemente §3.1

Estas tareas no se ejecutan en esta capacidad. Si se retoman, `COSTO_MOVER` y `costo_salida` ya los crea T118.

**Dominio (§3.1, plan P-02)**: campo JSON `costo`, «un entero mayor o igual que 1», «vale 100 si la salida no lo
declara» y «es el mismo en ambos sentidos».

- [ ] T006 [P] [a cargo de quien implemente §3.1] Probar `Salida`: sin `costo` queda `None`; 1 y 250 se conservan; 0, -1, 1.5, `"100"`, `True` y `null` lanzan `ValueError` (termina en `! Error: ...`, código 1, Principio VI); `a_json` omite la clave si es `None`; ida y vuelta por `a_json`/`desde_json`. Atiende: FR-005, PR-13. Archivo: tests/test_costo_salida.py.
- [ ] T007 [P] [a cargo de quien implemente §3.1] Probar `costo_salida` y `mover_jugador`: costo propio, 100 por defecto, doble de prueba sin atributo (`getattr`); `mover` programa la próxima acción igual que `proxima_accion(jugador, costo=<costo>)`; `esperar` y `atacar` siguen en 100; `retroceder` deshace el movimiento con costo. Atiende: FR-005, FR-025, PR-13. Archivo: tests/test_costo_salida.py.
- [ ] T008 [P] [a cargo de quien implemente §3.1] Probar la igualdad en ambos sentidos con el costo efectivo: `A→B` y `B→A` iguales pasan; 100 declarado frente a sin declarar pasa; 200 frente a sin declarar y 200 frente a 300 lanzan `ValueError` al preparar la partida; una salida sin inversa pasa. Atiende: FR-005, FR-024, PR-13. Archivo: tests/test_costo_salida.py.
- [ ] T009 [P] [a cargo de quien implemente §3.1] Probar de punta a punta con paquete offline: el `costo` llega desde `FuenteDatosOffline`, sobrevive la caché en disco (`guardar_esqueleto`/`cargar_esqueleto`) y `mover` lo cobra; un paquete sin `costo` da el mismo reloj que antes. Atiende: FR-005, FR-025, SC-006, PR-13. Archivo: tests/test_costo_salida.py.
- [ ] T010 [a cargo de quien implemente §3.1] Agregar `costo=None` al final del constructor de `Salida`, para que `Salida(2, False, None, None)` siga funcionando; validar el dominio en `desde_json`, distinguiendo clave ausente de valor inválido y rechazando `bool`; escribirlo en `a_json` solo si no es `None`. No fijar 100 en el DTO (R7). Atiende: FR-005, PR-13. Archivo: DTOS/Salida.py.
- [ ] T011 [a cargo de quien implemente §3.1] Agregar `COSTO_MOVER = 100` junto a `COSTO_USAR`, y `costo_salida(salida)` con `getattr(salida, "costo", None)`. Según §3.1 la regla aplica a todos los actores: el intervalo de movimiento es `max(1, costo_salida * 100 // velocidad)`, que ya calcula `calcu_inter`. Cambiar la línea `proxima_accion(jugador, costo=100)` de `mover_jugador`, y hacer que un enemigo que se mueve con `mover_enemigo` (ramas `MOVER` y `MOVER_RASTRO` de `ejecutar_evento`) reprograme su `proxima_accion` con `costo_salida` de la salida usada, porque ese intervalo se fija allí y no dentro de `mover_enemigo`. Un enemigo que ataca, espera o no llega a moverse sigue en 100. **No** tocar `esperar`, `atacar`, `activar_enemigo` ni el valor por defecto de `proxima_accion`. Es el único acceso al costo. Agregar a tests/test_costo_salida.py la prueba del intervalo del enemigo, con costo propio y por defecto y distintas velocidades. Depende de T010 y T002. Atiende: FR-005, FR-025, PR-13. Archivo: Modelo/MotorSimulacion.py, tests/test_costo_salida.py.
- [ ] T012 [a cargo de quien implemente §3.1] Agregar `validar_costos_salidas()`: para cada salida, busca con `_destino` y compara `costo_salida` con el de las salidas de vuelta. Sin `dict` como índice, complejidad documentada, O(e log n) más el grado. Llamarla desde `_crear_motor`, después de `iniciar_partida`, para cubrir partida nueva, carga y replay. Depende de T011. Atiende: FR-005, FR-024, PR-13. Archivo: Modelo/MotorSimulacion.py, Gestor/PreparadorPartida.py.

**Punto de control 1**: T118 en verde y suite completa igual que T001, sin editar pruebas de la Parte I. El movimiento de
ningún actor cambió.

---

## Fase 2: Conocimiento, memoria de puertas y antorcha (Historias 1 y 2) 🎯 MVP

**Propósito**: existe el conocimiento del jugador, integrado al `Historial` sin cambiar `Modelo/retroceso.py`.

**Prueba independiente US1**: con un paquete offline, moverse y comprobar el estado de cada sala tras cada movimiento.

**Prueba independiente US2**: encender la antorcha, entrar a una sala cuyas vecinas tienen enemigos y trampas, comprobar
que nada se activa y que un pergamino devuelve el conocimiento al estado anterior.

### Pruebas de la Historia 1

- [X] T013 [P] [US1] Escenario US1-1: en el instante 0, la sala inicial está explorada, los destinos de sus salidas avistados y el resto desconocido. Apéndice B: sala inicial en el instante 0. Atiende: FR-001, FR-002, FR-004, PR-01. Archivo: tests/test_conocimiento.py.
- [X] T014 [P] [US1] Escenario US1-2: al moverse a B avistada, B queda explorada, con nombre, salidas, costos y puertas, y sus destinos no explorados quedan avistados. Apéndice B: de avistada a explorada. Atiende: FR-003, FR-004, FR-005, PR-01. Archivo: tests/test_conocimiento.py.
- [X] T015 [P] [US1] Escenario US1-3: `A→B` se cierra con el jugador fuera de A y de B; el recuerdo sigue abierto y no aparece «Una puerta se cerró sola.» (H6). Atiende: FR-007, FR-012, PR-02, PR-04. Archivo: tests/test_conocimiento.py.
- [X] T016 [P] [US1] Escenario US1-4: puerta recordada abierta y cerrada en realidad; al entrar a A, y en otra prueba al entrar a B, el recuerdo queda cerrado. El caso B es la salida que entra y aplica la lectura de P-05. Apéndice B: puerta recordada abierta que está cerrada. Atiende: FR-006, FR-007, PR-02. Archivo: tests/test_conocimiento.py.
- [X] T017 [P] [US1] Probar la observación continua: `abrir` deja la puerta abierta en el mapa de inmediato, y con `esperar` en la sala un cierre automático se refleja en el recuerdo y en el mensaje. Atiende: FR-006, FR-008, PR-02. Archivo: tests/test_conocimiento.py.
- [X] T018 [P] [US1] Probar que la precarga no cambia el conocimiento y que la línea `Salidas:` de `mostrar_estado` sale de `salidas_recordadas`. Atiende: FR-012, FR-013, PR-04. Archivo: tests/test_conocimiento.py.
- [X] T019 [P] [US1] Probar retroceso y bordes: un pergamino revierte un `mover` sin antorcha; la sala inicial no se puede revertir; un motor sin `iniciar_partida` funciona con `conocimiento is None` (H7). Atiende: FR-002, FR-014, SC-006, PR-05. Archivo: tests/test_conocimiento.py.

### Pruebas de la Historia 2

- [X] T020 [P] [US2] Escenario US2-1: con antorcha, entrar a B cuya vecina C, por salida cerrada, tiene enemigos dormidos y trampa armada: B y C exploradas, enemigos dormidos, trampa sin activar, vida igual y `contenido_disponible(C)` falso. Apéndice B: antorcha explora sin activar. Atiende: FR-009, FR-010, PR-03. Archivo: tests/test_antorcha.py.
- [X] T021 [P] [US2] Escenario US2-2: tras entrar con antorcha, un pergamino restaura exactamente estados y puertas recordadas. Comparar `estado_sala`, `recuerdo_puerta`, `reveladas` y `observadas` completos. Apéndice B: pergamino revierte entrada con antorcha. Atiende: FR-014, PR-03, PR-05. Archivo: tests/test_antorcha.py.
- [X] T022 [P] [US2] Escenario US2-3: con antorcha apagada solo la sala de llegada queda explorada, y las vecinas quedan avistadas. Atiende: FR-009, PR-03. Archivo: tests/test_antorcha.py.
- [X] T023 [P] [US2] Escenario US2-4, parte del conocimiento: `C→D` queda `SIN_OBSERVAR` mientras el jugador no esté en C ni en D, y al entrar a una de ellas se observa. La parte de `mapa` está en T035 y la de «ir a» en T044. Atiende: FR-006, FR-011, PR-03. Archivo: tests/test_antorcha.py.
- [X] T024 [P] [US2] Casos borde: entrar con antorcha con vecinas ya exploradas no las cambia; los vecinos de una sala explorada con antorcha quedan avistados; una salida ya observada no vuelve a `SIN_OBSERVAR`. Atiende: FR-004, FR-009, FR-011, PR-03. Archivo: tests/test_antorcha.py.

### Implementación

- [X] T025 [US1] Crear `Conocimiento`, con `DESCONOCIDA`/`AVISTADA`/`EXPLORADA` y `SIN_OBSERVAR`/`ABIERTA`/`CERRADA`, ordinales propios (`_ordinal`, `_origen`), `entrantes`, `estado` y `recuerdo`. Ids opacos (H7). Copiar al docstring la tabla de complejidad de data-model. Sin `dict`/`set` como índice ni imports fuera de `Modelo/`. Reglas: «una sala está en la lista si y solo si su estado no es `DESCONOCIDA`, y aparece una sola vez». Atiende: FR-001, FR-004, FR-005, PR-01. Archivo: Modelo/Conocimiento.py.
- [X] T026 [US1] Implementar `entrar` sin antorcha, `explorar` y `observar_puerta`, observando salidas y entrantes. El costo depende de lo revelado, no de `k`. Depende de T025. Atiende: FR-002, FR-003, FR-006, FR-007, FR-008, PR-01, PR-02. Archivo: Modelo/Conocimiento.py.
- [X] T027 [US2] Agregar a `entrar` la antorcha: explora las vecinas por cualquier salida, sin leer contenido ni llamar al gestor; las puertas no observadas siguen `SIN_OBSERVAR`. Depende de T026. Atiende: FR-009, FR-010, FR-011, PR-03. Archivo: Modelo/Conocimiento.py.
- [X] T028 [US1] Implementar el lote de deltas y `revertir`: solo las escrituras que cambian algo, un `Cambio` por operación, nada si el lote está vacío, y `pop` de `reveladas`/`observadas` en orden inverso. `Modelo/retroceso.py` no cambia. Depende de T026. Atiende: FR-014, FR-031, PR-05. Archivo: Modelo/Conocimiento.py.
- [X] T029 [US1] Crear `conocimiento` (`None` por defecto) en `iniciar_partida` y registrar la entrada a la sala inicial sin intervalo abierto. Depende de T028. Atiende: FR-001, FR-002, PR-01. Archivo: Modelo/MotorSimulacion.py.
- [X] T030 [US1] [US2] Llamar a `conocimiento.entrar` en `mover_jugador` después del `historial.registrar` del movimiento y **antes** de las trampas, porque una trampa mortal retorna de inmediato. Tolerar `None`. No cambiar el orden trampas y luego enemigos. Depende de T027 y T029. Atiende: FR-003, FR-009, FR-010, FR-014, PR-02, PR-03. Archivo: Modelo/MotorSimulacion.py.
- [X] T031 [US1] Llamar a `observar_puerta` en `abrir_salida` y en `CERRAR_PUERTA`, en este último solo si el jugador está en el origen o el destino de la salida, y emitir «Una puerta se cerró sola.» solo en ese caso. El cierre real y el evento no cambian. Atiende: FR-006, FR-007, FR-008, FR-012, PR-02, PR-04. Archivo: Modelo/MotorSimulacion.py.
- [X] T032 [US1] Agregar `salidas_recordadas(sala)` y hacer que `_texto_salidas` use el recuerdo, con el comportamiento actual si `conocimiento is None`. La llave de la salida sigue visible (R8). Atiende: FR-012, PR-04. Archivo: Modelo/MotorSimulacion.py, Vista/VistaConsola.py.

**Punto de control 2**: T013 a T024 en verde, suite sin regresiones y `Modelo/retroceso.py` sin diferencias. Sube junto con
la parte de niebla de T111 (ver [Orden del README](#orden-del-readme)).

**Limitación conocida hasta T079**: guardar no conserva el conocimiento, así que tras cargar el mapa vuelve a solo la
sala inicial y los escenarios de la Historia 5 no se cumplen. Tampoco el replay de partidas cargadas (H1), hasta T094.
No se debe declarar FR-015 ni FR-017 como cumplidos antes de la Fase 5.

---

## Fase 3: Comando `mapa` (Historia 3)

**Propósito**: el jugador consulta lo que sabe. No hace falta para «ir a», así que esta fase y la 4 pueden avanzar a la vez.

**Prueba independiente**: tras unos movimientos, ejecutar `mapa` y comparar con las salas recorridas.

### Pruebas

- [X] T033 [P] [US3] Escenario US3-1: exploradas 1 y 2, `mapa` lista cada salida con dirección, destino, costo y estado, y aparte las avistadas; ninguna sala desconocida como entrada propia. Atiende: FR-005, FR-012, FR-018, PR-04, PR-08. Archivo: tests/test_mapa.py.
- [X] T034 [P] [US3] Escenario US3-2: `mapa` no cambia reloj, acciones ni bitácora, en cualquier estado. Atiende: FR-019, PR-08. Archivo: tests/test_mapa.py.
- [X] T035 [P] [US2] [US3] Escenario US2-4, parte de `mapa`: `C→D` aparece con destino y costo y estado `sin observar`. Atiende: FR-011, FR-018, SC-002, PR-08. Archivo: tests/test_mapa.py.
- [X] T036 [P] [US3] Probar el contrato de salida: salas por id ascendente, `Avistadas: ninguna`, avistada solo por id, sin llaves, enemigos, trampas ni objetos, costo distinto de 100, y puerta recordada distinta de la real. Atiende: FR-005, FR-010, FR-012, FR-018, SC-002, PR-04. Archivo: tests/test_mapa.py.

### Implementación

- [X] T037 [P] [US3] Crear los DTO `MapaConocido`, `SalaConocida` (`id`, `nombre`, `salidas`) y `SalidaConocida` (`direccion`, `destino_id`, `costo`, `estado`, que es `abierta`, `cerrada` o `sin observar`). Atiende: FR-018, PR-04. Archivo: DTOS/MapaConocido.py.
- [X] T038 [US3] Agregar `mapa_conocido()`, que recorre `reveladas`, ordena con `elegir_algoritmo` y no con `sorted`, y toma el costo de `costo_salida`. O(k log k + salidas de las exploradas). Depende de T037. Atiende: FR-005, FR-012, FR-018, PR-04. Archivo: Modelo/MotorSimulacion.py.
- [X] T039 [US3] Agregar `mostrar_mapa(mapa)` con el formato de contracts/comandos.md, sin reglas de juego, y agregar `mapa` a `AYUDA`. Atiende: FR-018, FR-020, PR-08. Archivo: Vista/VistaConsola.py.
- [X] T040 [US3] Agregar `mapa` a `ejecutar` como consulta, igual que `inventario`, sin tocar `ACCIONES`. Depende de T038 y T039. Atiende: FR-018, FR-019, PR-08. Archivo: Controlador/ControladorPartida.py.

**Punto de control 3**: T033 a T036 en verde. Sube junto con T111 (ver [Orden del README](#orden-del-readme)).

---

## Fase 4: Viaje «ir a» (Historia 4)

**Propósito**: la orden `ir a <sala>` como sucesión de `mover`. Todo se prueba con un **buscador de prueba inyectado**;
solo el cuerpo de `primer_paso` espera a que Persona A suba `Modelo/BusquedaRuta.py` (D-PEND-01, opción A).

**Prueba independiente**: con rutas y costos conocidos, comprobar la secuencia de salas, el reloj final y el motivo de parada.

**Alcance por el orden de fases**: `comentar` no existe hasta la Fase 5, así que aquí cada paso anota solo su `mover`. El
comentario `# ir a <sala>` lo agrega T085, y el Escenario US4-7 se prueba en T083.

**Mientras Persona A no suba `Modelo/BusquedaRuta.py`**: `primer_paso` lanza `NotImplementedError` y el controlador lo convierte en un aviso
sin efectos (T058), de modo que la suite sigue en verde en `main` y el juego real no se cae.

### Base

- [X] T041 [US4] Crear `Paso` (`direccion`, `destino`, `costo_total`) y `primer_paso(grafo, origen, destino)` con la firma de contracts/interfaz-ruta.md y un cuerpo que solo lanza `NotImplementedError`. Atiende: FR-023, FR-024, PR-10. Archivo: Modelo/rutas_ir_a.py.
- [X] T042 [P] [US4] Agregar `buscador_prueba(grafo, origen, destino)`, que enumera rutas simples y cumple las obligaciones 1 a 3 del contrato. Es solo una utilidad de prueba, no es candidata a implementación. Atiende: FR-024, PR-10. Archivo: tests/utiles_niebla.py.

### Pruebas

- [X] T043 [P] [US4] Escribir la prueba de contrato, parametrizada por buscador: ruta única, más barata con más saltos, sin ruta, empate en cualquier orden de `aristas`, empate decidido lejos del origen, costos distintos de 100, y que no modifica nada. Corre ya contra `buscador_prueba`; contra `primer_paso` queda con `skip` hasta T063. Incluir el desempate de P-03 (FR-024): dos salidas a la misma vecina con igual costo, gana la primera en el orden N, S, E, O. Atiende: FR-023, FR-024, PR-10. Archivo: tests/test_ruta_contrato.py.
- [X] T044 [P] [US2] [US4] Probar `GrafoConocido`, y con él el Escenario US2-4, parte de «ir a»: `aristas` no entrega salidas cerradas, sin observar ni hacia salas no exploradas, y el costo viene de `costo_salida`. Atiende: FR-011, FR-023, FR-029, SC-002, PR-10. Archivo: tests/test_viaje.py.
- [X] T045 [P] [US4] Escenario US4-1: hacia sala avistada o desconocida, rechazo con aviso; reloj, acciones y bitácora iguales. Apéndice B: «ir a» hacia sala no explorada. Atiende: FR-022, SC-005, PR-09. Archivo: tests/test_viaje.py.
- [X] T046 [P] [US4] Escenario US4-2: puerta recordada abierta y cerrada en realidad. Con otra ruta, el viaje sigue por ella; sin otra ruta, se detiene con aviso y sin tiempo adicional. Son dos pruebas. Apéndice B: puerta recordada abierta que está cerrada. Atiende: FR-026, FR-027, PR-09. Archivo: tests/test_viaje.py.
- [X] T047 [P] [US4] Escenario US4-3: al entrar a una sala con enemigos dormidos, se activan según §2.4 y el viaje se detiene ahí con su motivo. Una sala con enemigos ya derrotados no detiene. Apéndice B: «ir a» entra a sala con enemigos dormidos. Atiende: FR-027, PR-09. Archivo: tests/test_viaje.py.
- [X] T048 [P] [US4] Escenario US4-4: tras un viaje completo y otro detenido, un pergamino deshace solo el último paso, con conocimiento incluido, y el viaje no se reanuda. Apéndice B: pergamino durante un viaje. Atiende: FR-014, FR-031, PR-05, PR-09. Archivo: tests/test_viaje.py.
- [X] T049 [P] [US4] Escenario US4-5, parte que no depende de `Modelo/BusquedaRuta.py`: con `buscador_prueba`, dos rutas de igual costo van a la vecina de menor id, y el viaje sigue el paso que el buscador entrega. La prueba con la búsqueda real es T064. Atiende: FR-024, PR-09. Archivo: tests/test_viaje.py.
- [X] T050 [P] [US4] Escenario US4-6: el viaje se detiene al terminar el paso en que pierde vida, incluido el veneno activo desde antes de la orden. Atiende: FR-027, PR-09. Archivo: tests/test_viaje.py.
- [X] T051 [P] [US4] Escenario US4-8: una ruta que solo existe por una puerta cerrada de la que el jugador tiene la llave no cuenta, y la puerta sigue cerrada. Atiende: FR-023, FR-029, PR-09. Archivo: tests/test_viaje.py.
- [X] T052 [P] [US4] Escenario US4-9: la orden se acepta con enemigos activos o dormidos en la sala actual, y la parada por enemigos solo se evalúa al entrar. Atiende: FR-027, FR-028, PR-09. Archivo: tests/test_viaje.py.
- [X] T053 [P] [US4] Casos borde: sala actual, explorada sin ruta, id inexistente y no numérico con el mismo aviso que una no explorada, `ir` mal formado, victoria y muerte en un paso, puerta que se cierra sola durante el viaje estando el jugador en ella. Cada rechazo deja reloj, acciones y bitácora iguales. Atiende: FR-021, FR-022, FR-026, FR-027, SC-005, PR-09. Archivo: tests/test_viaje.py.
- [X] T054 [P] [US4] Probar la equivalencia con `mover`: mismo reloj y estado que los `mover` a mano, una línea `mover` por paso, eventos entre pasos, recálculo antes de cada paso y prioridad `FIN_PARTIDA`, `DANO`, `ENEMIGOS`, `DESTINO`. Atiende: FR-021, FR-025, FR-026, FR-027, PR-09. Archivo: tests/test_viaje.py.

### Implementación

- [X] T055 [US4] Implementar `GrafoConocido(conocimiento, costo_de)`, sin estado propio y sin referencia al motor: una arista existe si y solo si el origen y el destino están explorados y el recuerdo es `ABIERTA`. `Conocimiento` no contiene ningún número de costo. Atiende: FR-011, FR-012, FR-023, FR-029, PR-10. Archivo: Modelo/Conocimiento.py.
- [X] T056 [US4] Crear `Viaje` con `destino`, `buscar` (por defecto `primer_paso`) y `motivo`; los motivos `DESTINO`, `ENEMIGOS`, `DANO`, `SIN_RUTA`, `FIN_PARTIDA`, `PASO_RECHAZADO`; recálculo antes de cada paso; y prioridad de motivos. No se guarda ni se reanuda. Atiende: FR-025, FR-026, FR-027, FR-031, PR-09. Archivo: Modelo/Viaje.py.
- [X] T057 [US4] Agregar `preparar_viaje(texto, buscar=primer_paso)`, que busca con `explorada_por_texto` (O(k)) para que inexistente, desconocida y avistada den por construcción el mismo rechazo. Agregar a `mover_jugador` el indicador transitorio «había enemigos vivos al entrar», leído antes de activar enemigos y limpiado al inicio de cada `mover`. No evaluar la sala de partida. Depende de T055 y T056. Atiende: FR-022, FR-023, FR-027, FR-028, PR-09. Archivo: Modelo/MotorSimulacion.py, Modelo/Conocimiento.py.
- [X] T058 [US4] Agregar `ir` a `ejecutar`: valida `a <sala>`, muestra los rechazos de contracts/comandos.md, ejecuta cada paso con `ejecutar_accion("mover", direccion)`, anota el `mover` y muestra el motivo. `ACCIONES` no cambia. El buscador es un atributo del controlador, que las pruebas reemplazan. Capturar `NotImplementedError` con el aviso temporal `«ir a» aún no está disponible.`, sin efectos. Depende de T057. Atiende: FR-021, FR-022, FR-025, FR-027, SC-005, PR-09. Archivo: Controlador/ControladorPartida.py.
- [X] T059 [P] [US4] Agregar `ir a <sala>` a `AYUDA`. Atiende: FR-020, PR-09. Archivo: Vista/VistaConsola.py.

### Dependen de otras personas

- [X] T060 [US4] Aplicar FR-027f (P-04 resuelta): si el motor rechaza un paso en pleno viaje, el viaje se detiene con `PASO_RECHAZADO`, informa el mismo mensaje de rechazo que daría `mover` y no consume tiempo adicional. La spec está corregida y confirmada en Git en `da81905`, en confirmación separada y anterior al código (Principio IX); luego `Viaje`, el aviso y su prueba. Atiende: FR-027, PR-09. Archivo: specs/001-niebla-mapa-ir-a/spec.md, Modelo/Viaje.py, tests/test_viaje.py.
- [ ] T062 [US4] [BLOQUEADA: BusquedaRuta.py] [PERSONAS: Persona A] Escribir el cuerpo de `primer_paso`: delega en `Modelo/BusquedaRuta.py` de Persona A (D-PEND-01, opción A), sin implementar búsqueda ni cola de prioridad aquí. Que la búsqueda cumpla las 7 obligaciones del contrato, sin `heapq` ni `sorted()`, con la cola de prioridad a mano en `Modelo/ColaPrioridad.py` y la complejidad documentada, es responsabilidad de Persona A. Sigue bloqueada hasta que A suba su módulo. **Fechas de Persona A**: `Modelo/ColaPrioridad.py` el miércoles 11 y `Modelo/BusquedaRuta.py` el jueves 12. `primer_paso` agrega al final los parámetros opcionales `limite=None` y `espacio=None`, que no cambian el contrato (contracts/interfaz-ruta.md). Atiende: FR-011, FR-023, FR-024, FR-029, PR-10. Archivo: Modelo/rutas_ir_a.py.
- [ ] T063 [US4] [BLOQUEADA: BusquedaRuta.py] Quitar el `skip` y correr la prueba de contrato contra `primer_paso` y contra el cazador, con la misma tabla de casos de desempate para los dos. Las llamadas sin `limite` ni `espacio` deben pasar igual. Persona A sube `Modelo/BusquedaRuta.py` el jueves 12. Depende de T062. Atiende: FR-024, PR-10. Archivo: tests/test_ruta_contrato.py.
- [ ] T064 [US4] [BLOQUEADA: BusquedaRuta.py] Escenario US4-5, búsqueda real: con el buscador por defecto (`primer_paso`, que delega en `Modelo/BusquedaRuta.py`), el primer paso va a la vecina de menor id, y hacer el recorrido completo de un viaje sin inyección. Depende de T062. Atiende: FR-021, FR-023, FR-024, PR-09, PR-10. Archivo: tests/test_viaje.py.
- [ ] T065 [US4] [BLOQUEADA: BusquedaRuta.py] Retirar la captura de `NotImplementedError` y el aviso temporal de T058. Depende de T062. Atiende: FR-021, PR-09. Archivo: Controlador/ControladorPartida.py.

**Punto de control 4**: T043 a T054 en verde con el buscador de prueba, y `ir a` en el juego real da el aviso temporal
hasta T065. **La Historia 4 no está terminada** hasta T062 a T065 y T083. Sube junto con T112.

---

## Fase 5: Contratos compartidos (Historia 5 y bitácora de la Historia 4) ⚠️ REQUIERE AVISO PREVIO AL GRUPO

**Propósito**: partida `CRPT` 3, bitácora `CRIPTA-LOG` 2, `@cargar`, corrección de `--replay` (H1) y de las puertas al
cargar (H2), y `--replay` sin vista (H4).

⚠️ **Ninguna tarea de esta fase empieza sin T066 y T067.** Toca formatos de archivo, `guardar_partida`, `ejecutar_replay`
y la bitácora, que usan otras personas. Conviene que esta fase, por tocar `Persistencia/` y `Bitacora/`, la revise otra persona.

**Prueba independiente**: explorar, incluyendo una puerta recordada distinta de la real, guardar, cargar en otra sesión y
comparar el mapa; luego reproducir la bitácora y comparar reloj, posición y conocimiento.

### Aviso

- [X] T066 [PERSONAS: grupo] Avisar antes de cambiar nada: `CRPT` 2→3, `CRIPTA-LOG` 1→2, firmas de `guardar_partida` y `ejecutar_replay`, función nueva `guardar_motor`, y que `partida.cripta`, `partida.cripta.log` y `partida.log` dejan de cargarse. **Respuesta de Persona D** (línea de tiempo y persistencia, spec 004): aceptado, con las cuatro condiciones de P-07: (a) `@cargar` queda escrito en contracts/formato-bitacora.md; (b) `--replay --hasta t` cuenta el reloj a través de las líneas `@cargar`; (c) una versión incompatible se rechaza con código 2, como hoy; (d) se actualiza el README (T113). **Hecho**: aviso mandado; Persona D aceptó, Persona B no objeta y Persona A no respondió sobre formatos (su respuesta fue sobre la búsqueda). P-10 resuelta: el `CRPT` 3 queda `[encabezado][jugador][conocimiento][línea de tiempo][salas][índice]` en un solo salto a la versión 3, con la línea de tiempo de D como bloque opaco con su largo; la fórmula final de `_inicio_salas` y el contenido de la línea los cierra D en su plan (spec 004). No se mantienen archivos v3 intermedios: al integrar se regeneran las partidas guardadas. Atiende: FR-016, FR-030, PR-06, PR-11, PR-12, PR-14. Archivo: specs/001-niebla-mapa-ir-a/contracts/formato-partida.md, specs/001-niebla-mapa-ir-a/contracts/formato-bitacora.md (referencia).
- [X] T067 [PERSONAS: grupo, P-07] Obtener la aceptación de que `@cargar` hace falso «`cargar` no se anota». Anotar la respuesta en P-07. Bloquea T084 a T094. **Hecho**: aceptado por Persona D (spec 004) y anotado en P-07, con cuatro condiciones que obligan a las tareas de la fase: (a) `@cargar` queda escrito en contracts/formato-bitacora.md; (b) `--replay --hasta t` cuenta el reloj a través de las líneas `@cargar` (T084, T093); (c) una versión incompatible se rechaza con código 2, como hoy (T082, T084); (d) se actualiza el README (T113). Atiende: FR-017, PR-12. Archivo: specs/001-niebla-mapa-ir-a/plan.md.

### Pruebas de persistencia v3

- [X] T068 [P] [US5] Escenario US5-1: con exploradas, avistadas y una puerta recordada abierta y cerrada en realidad, guardar y cargar da un `MapaConocido` idéntico. Apéndice B: guardar y cargar con conocimiento. Atiende: FR-015, SC-003, PR-06. Archivo: tests/test_persistencia_conocimiento.py.
- [X] T069 [P] [US5] Probar `RegistroConocimiento`: ida y vuelta binaria y JSON; el mismo estado da los mismos bytes; incluye exploradas por antorcha y recuerdos de salas no exploradas; avistadas recalculadas y no guardadas. Atiende: FR-015, FR-004, PR-06. Archivo: tests/test_persistencia_conocimiento.py.
- [X] T070 [P] [US5] Probar cada rechazo con `VersionIncompatible` y código 2: versión 2, sin bloque de conocimiento, bloque truncado, valor inválido, bytes sobrantes, sala o dirección inexistente, y sala del jugador no explorada. Nada queda cargado. Atiende: FR-016, PR-06. Archivo: tests/test_persistencia_conocimiento.py.
- [X] T071 [P] [US5] Probar H2: abrir `1→2`, pasar a 2, guardar y cargar; `1→2` sigue abierta en memoria sin leer el bloque de la sala 1, y al observarla el recuerdo es correcto. Atiende: FR-006, FR-015, PR-07. Archivo: tests/test_persistencia_conocimiento.py.
- [X] T072 [P] [US5] Probar que el conocimiento ganado con antorcha se conserva, la antorcha queda apagada, cargar no vuelve a observar puertas, la carga sigue perezosa (`test_carga_perezosa_solo_lee_la_sala_actual` sin cambios) y `retroceder` tras cargar se comporta como en la Parte I. Atiende: FR-015, PR-06, PR-07. Archivo: tests/test_persistencia_conocimiento.py.
- [X] T073 [P] [US5] Probar que `ExportadorJSON` incluye `conocimiento` con los mismos tres campos que el binario. Atiende: FR-015, PR-06. Archivo: tests/test_json.py.

### Implementación de persistencia v3

- [X] T074 [US5] Implementar `exportar` y `restaurar` (sin historial; recalcula avistadas por FR-004), ordenando con `elegir_algoritmo`. Atiende: FR-004, FR-015, PR-06. Archivo: Modelo/Conocimiento.py.
- [X] T075 [P] [US5] Crear `RegistroConocimiento` con `to_bytes`, `from_bytes`, `to_dict` y `from_dict`, y el formato exacto de contracts/formato-partida.md: `<I`, `<H+s`, `<B`, little endian y sin relleno. Recuerdos `1 = abierta, 2 = cerrada`; puertas reales `0 = abierta, 1 = cerrada`. Atiende: FR-015, PR-06. Archivo: Persistencia/RegistroConocimiento.py.
- [X] T076 [US5] Subir `VERSION_FORMATO` a 3 y agregar `[largo conocimiento][conocimiento]`; `guardar_partida(..., conocimiento=None)` escribe largo 0; `_inicio_salas` y `_validar_encabezado` usan el bloque; agregar `leer_conocimiento()`, de una sola vez. El bloque va entre el jugador y el bloque de línea de tiempo de Persona D, que se trata como opaco con su largo: `[encabezado][jugador][conocimiento][línea de tiempo][salas][índice]`, en el mismo salto a la versión 3 (P-10 resuelta). La fórmula final de `_inicio_salas` la cierra D en su plan (spec 004). Depende de T075. Atiende: FR-015, FR-016, PR-06. Archivo: Persistencia/FormatoBinario.py, Persistencia/ArchivoPartida.py.
- [X] T077 [US5] Exportar el conocimiento y las puertas reales, solo las que están cerradas hoy, o estaban cerradas en el esqueleto (`Salida.cerrada_en_esqueleto`), o tienen llave, o tienen cierre automático; el valor guardado es el estado actual; aplicar la tabla de puertas reales sin leer bloques de sala (H2). Depende de T074 y T076. Atiende: FR-006, FR-015, PR-06, PR-07. Archivo: Persistencia/ConversorPartida.py.
- [X] T078 [P] [US5] Agregar la clave `conocimiento`. Depende de T075. Atiende: FR-015, PR-06. Archivo: Persistencia/ExportadorJSON.py.
- [X] T079 [US5] En `cargar_partida`, seguir el orden de data-model: leer jugador y conocimiento, `_crear_motor`, aplicar puertas reales, `restaurar`, restaurar jugador y reloj, `preparar_sala`. Rechazar la falta de bloque y la sala del jugador no explorada. Depende de T077. Atiende: FR-015, FR-016, PR-06, PR-07. Archivo: Gestor/PreparadorPartida.py.
- [X] T080 [US5] Pasar el conocimiento desde `guardar` a `guardar_partida`. Depende de T077. Atiende: FR-015, PR-06. Archivo: Controlador/ControladorPartida.py.

### Bitácora v2 con comentarios

- [X] T081 [P] [US4] Actualizar lo que el contrato enumera: `CRIPTA-LOG 2` como versión inválida pasa a `VERSION_BITACORA + 1`, y los literales `CRIPTA-LOG 1` de encabezados dañados pasan a la versión vigente. Atiende: FR-030, SC-006, PR-11. Archivo: tests/test_bitacora.py.
- [X] T082 [P] [US4] Probar comentarios: `comentar` escribe `# <texto>`, `leer_bitacora` los omite, `CRIPTA-LOG 1` se rechaza con código 2, directiva desconocida se rechaza con código 2, y `registrar` rechaza nombres que empiezan con `#` o `@`. Atiende: FR-030, PR-11. Archivo: tests/test_bitacora.py.
- [X] T083 [P] [US4] Escenario US4-7: un viaje que llega al destino deja `# ir a <sala>` inmediatamente antes del primer `mover`, un `mover` por paso, y `--replay` reproduce la misma partida. Un viaje detenido deja solo los pasos dados; un rechazo, incluido el del primer `mover`, no deja línea. Usa `buscador_prueba`: el replay solo ve `mover`. Atiende: FR-022, FR-030, SC-004, SC-005, PR-11. Archivo: tests/test_viaje.py.
- [X] T084 [US4] Subir `VERSION_BITACORA` a 2; agregar `comentar` y `marcar_carga`; `leer_bitacora` omite comentarios y devuelve `("@cargar", "")` en `acciones`; una directiva desconocida lanza `VersionIncompatible`. Depende de T067. Atiende: FR-017, FR-030, PR-11, PR-12. Archivo: Bitacora/BitacoraPartida.py.
- [X] T085 [US4] Escribir el comentario **después** de que el motor acepte el primer paso y antes de la línea de ese paso. Depende de T058 y T084. Atiende: FR-022, FR-030, SC-005, PR-11. Archivo: Controlador/ControladorPartida.py.

### `@cargar` y corrección de `--replay`

- [X] T086 [P] [US5] Probar `Reproductor`: `@cargar` llama a `recargar` y sigue con el motor que devuelve; sin `recargar` y con `@cargar` da error y no se ignora. Atiende: FR-017, PR-12. Archivo: tests/test_bitacora.py.
- [X] T087 [P] [US5] Escenario US5-2: guardar, cargar, continuar y reproducir da reloj, `secuencia`, azar, posición y conocimiento iguales, con varias semillas, repitiendo el experimento de H1. Incluir antorcha encendida al guardar: apagada en ambos casos. Atiende: FR-017, SC-004, PR-12. Archivo: tests/test_persistencia_conocimiento.py.
- [X] T088 [P] [US5] Probar una partida con «ir a» y pergaminos, sin y con carga: el replay da el mismo reloj final, posición y conocimiento. Atiende: FR-017, FR-030, FR-031, SC-004, PR-11, PR-12. Archivo: tests/test_persistencia_conocimiento.py.
- [X] T089 [P] [US5] Probar el presupuesto con una fuente que cuenta solicitudes: un replay con varios `@cargar` no supera `presupuesto_solicitudes`. Si lo supera, detenerse y consultar al grupo (Principio VII). Atiende: FR-017, PR-12. Archivo: tests/test_persistencia_conocimiento.py.
- [X] T090 [P] [US5] Definir con prueba los dos riesgos del plan: `--bitacora` igual a `<guardado>.log`, y un `guardar` sin `cargar`, que carga salas por `_asegurar_salas_con_estado` sin tocar azar ni agenda. **Nota**: el primer riesgo pasa a ser un error de uso (pedido de Persona D); su prueba la reemplaza T120. Atiende: FR-017, SC-004, PR-12. Archivo: tests/test_persistencia_conocimiento.py.
- [X] T091 [US5] Agregar `conocimiento` a `obtener_estado_resumen`, para que las comparaciones de replay lo incluyan. Atiende: FR-017, SC-004, PR-12. Archivo: Modelo/MotorSimulacion.py.
- [X] T092 [US5] Llamar a `marcar_carga` en `_continuar_bitacora`, después de copiar la bitácora y validar el encabezado. Sin bitácora se conserva el aviso actual. Depende de T084. Atiende: FR-017, PR-12. Archivo: Controlador/ControladorPartida.py.
- [X] T093 [US5] Agregar `recargar=None` a `Reproductor` y ejecutar `@cargar` con él. Sin `recargar`, error. Depende de T084. Atiende: FR-017, PR-12. Archivo: Bitacora/Reproductor.py.
- [X] T094 [US5] Extraer de `guardar` una función sin vista, `guardar_motor(motor, ruta, gestor)`, y en `ejecutar_replay` pasar un `recargar` que guarda en un temporal y llama a `cargar_partida`. Cerrar el restaurador anterior tras cada recarga, y el último antes de borrar el temporal: en Windows no se borra un archivo abierto. La recarga **no** ejecuta la verificación de resolubilidad (`--verificar`, FR-022 de la spec 002, de Persona B). Depende de T080, T092 y T093. Atiende: FR-017, SC-004, PR-12. Archivo: Controlador/ControladorPartida.py, main.py.

### `--replay` sin instanciar la vista

- [X] T095 [P] [US5] Probar `main --replay` con `VistaConsola` reemplazada por una que falla al instanciarse: la reproducción termina con código 0, y los errores siguen dando `! Error: ...` con código 1 y `Versión incompatible: ...` con código 2. Atiende: FR-017, PR-14. Archivo: tests/test_integracion.py.
- [X] T096 [US5] Cambiar a `ejecutar_replay(ruta, gestor)`, sin vista, y mover `vista = VistaConsola()` para que la rama `--replay` no la cree. Conservar la prioridad de opciones, que es contrato público. Al subir `main.py`, avisar a Persona B de que la recarga del replay no ejecuta `--verificar` (T094). Depende de T094. Atiende: FR-017, PR-14. Archivo: main.py.
- [X] T097 [US5] Ajustar las llamadas a `ejecutar_replay` que pasan `VistaFalsa`. Son los únicos cambios permitidos a estas pruebas. Depende de T096. Atiende: SC-006, PR-14. Archivo: tests/test_integracion.py, tests/test_puntajes.py.
- [ ] T098 [PERSONAS: grupo] Decidir si `partida.cripta` y `partida.cripta.log`, que quedan obsoletos y que la constitución dice que no deberían versionarse, se retiran, y regenerar `partida.log` si sirve de evidencia. **Respuestas**: Persona B está de acuerdo en retirar `partida.cripta`, `partida.cripta.log` y `partida.log` del repositorio; faltan Persona A y Persona D. Atiende: FR-016, FR-030, SC-001, PR-16. Archivo: partida.log, partida.cripta, partida.cripta.log.

### Puntos de control de la línea de tiempo (pedido de Persona D)

- [X] T119 [US5] Hacer que `Conocimiento` pueda copiarse y serializarse, con cambios reversibles, porque los puntos de control de la línea de tiempo de Persona D (spec 004) lo necesitan. **Prueba primero**: escribir las pruebas y comprobar que fallan antes del código. Probar que (1) una copia es independiente: cambiar el original no cambia la copia y viceversa, y la copia da el mismo `MapaConocido`; (2) serializar y reconstruir da el mismo estado de salas, recuerdos, `reveladas` y `observadas`, y el mismo estado da la misma serialización; (3) cada lote de cambios se puede invertir y volver a aplicar (`invertir`/`aplicar`) en cualquier secuencia válida, y el estado coincide en cada punto con una foto tomada antes; (4) `revertir` del `Historial` sigue funcionando igual y `Modelo/retroceso.py` no cambia. Implementar: `copiar()`; serialización reusando `exportar`/`restaurar` de T074; lotes que guardan valor anterior y nuevo, con `aplicar(lote)` e `invertir(lote)`. Sin `dict`/`set` como índice, complejidad documentada en el docstring (copia y serialización O(n + e); aplicar e invertir O(tamaño del lote)). **Nota**: por ahora Persona D pide solo `copiar()` y la serialización; `aplicar`/`invertir` los confirma ella el martes 10. Los tres ya están implementados. Depende de T074. Atiende: FR-015, FR-016, PR-05, PR-06. Archivo: tests/test_persistencia_conocimiento.py, Modelo/Conocimiento.py.

### Ajustes pedidos por Persona D (FR-030 de la spec 004)

- [X] T120 [US5] **Prueba primero**: `--bitacora` igual a `<guardado>.log` es un error de uso. Reemplazar la prueba de T090 `test_fr017_bitacora_igual_al_log_del_guardado`, que hoy lo toma como caso seguro, por pruebas del rechazo: (i) `cargar` con la bitácora activa igual a `ruta_bitacora_de(archivo)` falla antes de jugar, y `main --cargar X --bitacora X.log` termina con código `1` y `! Error: ...`, sin modificar `X.log`; (ii) `guardar` con la bitácora activa igual a `ruta_bitacora_de(destino)` se rechaza con `! Error: ...` sin escribir el archivo de partida ni su bitácora. Probar también que rutas equivalentes escritas distinto se detectan (`_misma_ruta`). Comprobar que fallan antes del código. Atiende: FR-017, PR-12. Archivo: tests/test_persistencia_conocimiento.py, tests/test_integracion.py.
- [X] T121 [US5] Implementar el rechazo de T120 en `ControladorPartida.cargar` (antes de `cargar_partida` y de tocar la bitácora) y en `ControladorPartida.guardar` (antes de `guardar_motor`), y en `main.py` traducirlo a `! Error: ...` con código `1`. Quitar de `_continuar_bitacora` y de `guardar` la rama de «misma ruta», que deja de ser alcanzable. **Hecho**: `main.py` no cambió, porque ya traduce `ValueError` a `! Error: ...` con código 1; en la partida, `guardar` y `cargar` muestran el error y siguen. `_misma_ruta` usa además `os.path.normcase`. Depende de T120. Atiende: FR-017, PR-12. Archivo: Controlador/ControladorPartida.py, main.py.
- [X] T122 [US5] Verificar con prueba la disposición final de `CRPT` 3 cerrada por D: `_validar_encabezado` exige `offset_indice >= TAMANO_ENCABEZADO + 12` (rechaza con `VersionIncompatible` un índice dentro de los tres campos de largo) y `_inicio_salas = TAMANO_ENCABEZADO + (4 + largo_jugador) + (4 + largo_conocimiento) + (4 + largo_linea)`, leyendo solo los tres largos. Si el código no coincide, corregirlo. **Hecho**: el código ya coincidía; no se corrigió nada. Atiende: FR-016, PR-05. Archivo: tests/test_persistencia_conocimiento.py, Persistencia/ArchivoPartida.py.

**Punto de control 5**: pruebas T068 a T073, T081 a T083, T086 a T090, T095, T119, T120 y T122 en verde, e implementaciones T074 a T080,
T084, T085, T091 a T094, T096, T097 y T121 hechas; suite completa en verde; quickstart 5, 6 y 7 correctos. Sube junto con T113, que es contrato de formatos.

---

## Fase 6: Mediciones `--bench` M1 a M6

**Propósito**: respaldar cada afirmación de rendimiento (Principio VIII). Hasta tener estos datos, son hipótesis.

**Datos**: mapas sintéticos en `tests/`, porque la cripta de referencia aún no está publicada. **El límite de 5 ms de
§6.1 se define para esa cripta**, así que el resultado con mapas sintéticos es provisional y debe decirlo en el archivo.

- [ ] T099 [P] Crear generadores de mapas sintéticos sin datos de ninguna cripta real: cadena y grilla con V = 25, 100, 400, 2500, y salas hasta n = 20000, con costos variados y simétricos. Atiende: SC-006, PR-15. Archivo: tests/mapas_sinteticos.py.
- [ ] T100 Crear la medición con mediana de varias repeticiones, escritura de `resultados_bench_niebla.txt` con equipo y versión de Python, y **una sola constante** `LIMITE_PASO_IR_A_MS = 5`, con comentario que cita §6.1 y que el valor puede cambiar por enmienda. Ningún otro lugar escribe ese número. Depende de T099. Atiende: PR-15, Principio VIII, sin FR. Archivo: tests/bench_niebla.py.
- [ ] T101 M1: consultar estado de sala y recuerdo de puerta con arreglos densos, lista ordenada con binaria y lista lineal, n = 20, 200, 2000, 20000. Hipótesis: los arreglos no crecen con `n`. Depende de T100. Atiende: FR-001, FR-005, PR-15. Archivo: tests/bench_niebla.py.
- [ ] T102 M2: revelar `r` fijo con k = 10, 100, 1000, 10000, arreglos frente a lista ordenada. Hipótesis: con arreglos no crece con `k`. Depende de T100. Atiende: FR-003, FR-009, PR-15. Archivo: tests/bench_niebla.py.
- [ ] T103 M3: registrar y deshacer una entrada con antorcha con lote, cierres por escritura y copia completa, varios `r` y `n`. Hipótesis: lote y cierres crecen con `r`, la copia con `n`. Depende de T100. Atiende: FR-014, PR-15. Archivo: tests/bench_niebla.py.
- [ ] T104 M4: medir un paso y un viaje completo **por la interfaz `primer_paso`**, con grilla y cadena de T099. Compara contra `LIMITE_PASO_IR_A_MS` e informa cumple o no cumple. Si `primer_paso` no tiene cuerpo, informa `pendiente BusquedaRuta.py`; no mide `buscador_prueba`, porque ese número no significaría nada. Depende de T100. Atiende: FR-024, FR-026, SC-007, PR-15. Archivo: tests/bench_niebla.py.
- [ ] T105 M5: tamaño y tiempo del bloque de conocimiento y bytes leídos al cargar, k = 20, 200, 2000, binario frente a JSON. Depende de T100 y T076. Atiende: FR-015, PR-15. Archivo: tests/bench_niebla.py.
- [ ] T106 M6: ciclo completo con y sin conocimiento, 10 a 500 enemigos, con p95, reusando `tests/bench_ciclo.py`. Hipótesis: sin regresión frente a 20 ms (§5.2). Depende de T100. Atiende: FR-014, SC-006, PR-15. Archivo: tests/bench_niebla.py.
- [ ] T107 Agregar la medición a la rama `--bench`, sin red y sin vista. Depende de T101 a T106. Atiende: PR-15, Principio VIII, sin FR. Archivo: main.py.
- [ ] T108 [P] Agregar una prueba rápida con tamaños mínimos: M1 a M6 corren sin red, sin `VistaConsola`, y M4 compara contra la constante, sin afirmar tiempos. Depende de T107. Atiende: SC-006, PR-15. Archivo: tests/test_bench_niebla.py.
- [ ] T109 [BLOQUEADA: BusquedaRuta.py] Correr M4 con `primer_paso` real y guardar el resultado, marcado como provisional. Medir con y sin un `EspacioBusqueda` reutilizado por viaje (parámetro `espacio` de `primer_paso`). Persona A sube `Modelo/BusquedaRuta.py` el jueves 12. Si no cumple, corregir el diseño o el documento (R9). Depende de T062 y T107. Atiende: FR-024, PR-15. Archivo: resultados_bench_niebla.txt.
- [ ] T110 [PERSONAS: curso, publicación de la cripta de referencia] Agregar a M4 el mapa conocido completo de la cripta de referencia y dar el veredicto definitivo de §6.1. Sus datos se obtienen de la fuente o quedan en `tests/` (Principio IV). Depende de T109. Atiende: FR-024, PR-15. Archivo: tests/bench_niebla.py.

**Punto de control 6**: `python main.py --bench` genera `resultados_bench_niebla.txt`, con M1, M2, M3, M5 y M6 medidas, y M4
como provisional o `pendiente BusquedaRuta.py`. **El límite de §6.1 no se da por cumplido hasta T110.**

---

## Fase 7: README, Documento de Decisiones y matriz de trazabilidad

**Propósito**: documentar lo que quedó, con datos medidos. El README está en UTF-16 LE con CRLF: conservar la codificación
y avisar al grupo antes de editarlo (plan).

### Orden del README

La constitución exige el README **en el mismo cambio** que el comportamiento visible. Estas tareas están aquí por el orden
pedido, pero T111, T112 y T113 **suben junto con su fase** si esa fase llega a `main` antes que la Fase 7.

| Fase | Sección del README | Tarea |
|------|--------------------|-------|
| 0 y 1 | Ninguna: no cambian nada visible | — |
| 2 | `### Comandos de juego`: niebla, estado recordado en `Salidas:` y aviso de cierre de puerta | T111, parte de niebla |
| 3 | `### Comandos de juego`: `mapa` | T111, parte de `mapa` |
| 4 | `### Comandos de juego`: `ir a <sala>` | T112 |
| 5 | `### Guardar`, `### Cargar`, `### Bitácora` y `### Reproducir una partida (`--replay`)` | T113 |
| 6 | `### Mediciones (`--bench`)` y `### Archivos generados` | Sin tarea propia: sube con T107 |
| 7 | Ninguna nueva: se revisan las anteriores | — |

- [X] T111 [PERSONAS: aviso al grupo] Documentar `mapa`, la niebla, el estado recordado y que «Una puerta se cerró sola.» solo aparece si el jugador la observa. La parte de niebla sube con la Fase 2; la de `mapa` depende de T040. **Hecho**: niebla, estado recordado y mensaje de cierre en `c74fd6a`; `mapa` en `919ad9f`. Atiende: FR-018, FR-019, FR-020, PR-08, PR-16. Archivo: README.md.
- [ ] T112 [PERSONAS: aviso al grupo] Documentar `ir a <sala>`, rechazos y motivos de parada. Mientras T065 no esté hecha, decir que el comando aún no está disponible. Depende de T058. Atiende: FR-020, FR-021, FR-027, PR-09, PR-16. Archivo: README.md.
- [ ] T113 [PERSONAS: aviso al grupo] Documentar `CRPT` 3 y `CRIPTA-LOG` 2, comentarios, `@cargar`, y corregir «`cargar` no se anota». Actualizar el ejemplo de bitácora. Depende de T094. Atiende: FR-016, FR-017, FR-030, PR-06, PR-11, PR-12, PR-16. Archivo: README.md.

### Documentos

- [ ] T114 [PERSONAS: revisión del grupo] Agregar al Documento de Decisiones las decisiones 1 a 6 del plan, con alternativas y datos de `resultados_bench_niebla.txt`, marcando como hipótesis lo no medido. Incluir la resolución de D-PEND-01 (opción A: búsqueda compartida con el cazador en `Modelo/BusquedaRuta.py`, de Persona A). Es un `.docx`: se edita con Word, no como texto. Depende de T107. Atiende: PR-16, Principio VIII, sin FR. Archivo: Proyecto Cripta.docx.
- [ ] T115 Crear la matriz de trazabilidad: una fila por cada uno de los 31 FR y los 7 SC, con PR, tareas, prueba o `partida.log` de evidencia y estado (hecho, bloqueado o pendiente), más los 9 casos de SC-001. Las filas de FR-005 y FR-024 deben indicar que dependen de T010 (capacidad de terreno y costos) para probarse con costos reales: hasta entonces solo se prueban con costos puestos a mano en la salida o con grafos de prueba. Atiende: SC-001, FR-001 a FR-031, PR-16. Archivo: specs/001-niebla-mapa-ir-a/trazabilidad.md.
- [ ] T116 Recorrer los escenarios 1 a 8 de quickstart y correr la suite completa. Anotar el resultado en la matriz, incluido lo que siga bloqueado. Depende de T115. Atiende: SC-001, SC-002, SC-003, SC-004, SC-005, SC-006, PR-16. Archivo: specs/001-niebla-mapa-ir-a/trazabilidad.md.
- [ ] T117 [PERSONAS: otra persona del grupo; Persona D] Revisar los cambios en `Modelo/`, `Persistencia/`, `Bitacora/` y `main.py` (Flujo de desarrollo). Quien revisa los cambios en `Bitacora/`, `Persistencia/` y `main.py` es Persona D. Atiende: PR-16, sin FR. Archivo: Modelo/, Persistencia/, Bitacora/, main.py (revisión).
- [ ] T004 [PERSONAS: grupo] Al final, armar `PROMPTS_LLM.md` en la raíz del repositorio a partir de las notas de cada persona, con fecha, modelo, prompt textual y para qué se usó. Atiende: Principio XI, sin FR. Archivo: PROMPTS_LLM.md.

**Punto de control 7**: matriz completa, ninguna afirmación de rendimiento sin medición, suite en verde. La capacidad se
da por terminada solo cuando no quede ninguna fila bloqueada.

---

## Dependencias

```text
Fase 0 ─ Fase 1 ─ Fase 2 ─┬─ Fase 3 (mapa) ──────────────┐
                          └─ Fase 4 (ir a, con buscador) ┤
                                                         ├─ Fase 5 ─ Fase 6 ─ Fase 7
  BusquedaRuta.py (A) ─ T062 ─ T063, T064, T065, T109 ──┘

T066 + T067 (aviso) ─ todas las demás tareas de la Fase 5
T084 (bitácora v2) ─ T085, T092, T093
T080, T092, T093 ─ T094 ─ T096 ─ T097
T074 (exportar/restaurar) ─ T119 (copia, serialización y lotes reversibles, para Persona D)
```

- Las fases 3 y 4 necesitan a la 1 porque muestran y usan `costo_salida`.
- Las fases 3 y 4 son independientes entre sí, salvo que tocan `Modelo/MotorSimulacion.py`, `Vista/VistaConsola.py` y
  `Controlador/ControladorPartida.py`: si las llevan dos personas, conviene un `git pull` frecuente.
- T062 a T065 no bloquean las fases 5, 6 y 7: se pueden integrar en cuanto Persona A suba `Modelo/BusquedaRuta.py`.

### Tareas que dependen de otras personas

| Tarea | Quién | Qué necesita | Si no llega |
|-------|-------|--------------|-------------|
| T002, T006 a T012 | Quien implemente §3.1 | Capacidad de terreno y costos | `costo_salida` sigue en 100 y esta capacidad continúa |
| T004 | Cada persona del grupo | Sus notas de prompts (fecha, modelo, prompt textual, para qué se usó) para armar `PROMPTS_LLM.md` | Falta parte del registro del Principio XI |
| T061 | Grupo | P-05 (✅ confirmada por Personas A y B) | Se mantiene la lectura del plan |
| T062 a T065, T109 | Persona A | Que suba `Modelo/ColaPrioridad.py` (miércoles 11) y `Modelo/BusquedaRuta.py` (jueves 12) (D-PEND-01 resuelta con la opción A) | `ir a` no funciona en el juego real |
| T076 | Persona D | Fórmula final de `_inicio_salas` y contenido de la línea de tiempo, en su plan (spec 004). El orden ya está acordado (P-10) | La línea de tiempo se trata como bloque opaco con su largo |
| T098 | Personas A y D | Destino de los archivos versionados (Persona B está de acuerdo en retirarlos) | Quedan archivos obsoletos en el repositorio |
| T110 | Curso | Publicación de la cripta de referencia | §6.1 queda sin veredicto definitivo |
| T111 a T113 | Grupo | Aviso antes de editar el README | No se sube la fase correspondiente |
| T114, T117 | Grupo; Persona D revisa `Bitacora/`, `Persistencia/` y `main.py` | Revisión | Sin cierre de la capacidad |

## Paralelismo

| Bloque | Se puede repartir | Va en serie |
|--------|-------------------|-------------|
| Fase 1 | No aplica: T118 es la única tarea | — |
| Fase 2, pruebas | T013 a T019 (`test_conocimiento.py`) frente a T020 a T024 (`test_antorcha.py`) | Dentro de cada archivo |
| Fase 2, código | Una persona: todo T025 a T032 comparte archivos | T025 → T026 → T027, T028 → T029 → T030 |
| Fases 3 y 4 | Una persona en cada fase, tras el punto de control 2. También T037, T042, T059 | T055 → T056 → T057 → T058 |
| Fase 5, pruebas | `test_persistencia_conocimiento.py`, `test_bitacora.py`, `test_json.py` y `test_viaje.py` | Dentro de cada archivo |
| Fase 5, código | T075 y T078 frente a la Bitácora (T084, T093) | T076 → T077 → T079; T094 → T096 → T097 |
| Fase 6 | T099 frente al resto; T108 al final | T101 a T106 comparten archivo |
| Fase 7 | T111 a T113 frente a T114 y T115 | T115 → T116 |

## Cobertura de escenarios de aceptación

Los 21 escenarios de la spec.

| Escenario | Tarea de prueba | FR | Nota |
|-----------|-----------------|----|------|
| US1-1 | T013 | FR-001, FR-002, FR-004 | |
| US1-2 | T014 | FR-003, FR-004, FR-005 | |
| US1-3 | T015 | FR-007, FR-012 | |
| US1-4 | T016 | FR-006, FR-007 | |
| US2-1 | T020 | FR-009, FR-010 | |
| US2-2 | T021 | FR-014 | |
| US2-3 | T022 | FR-009 | |
| US2-4 | T023, T035, T044 | FR-006, FR-011, FR-018, FR-023 | Una parte por fase |
| US3-1 | T033 | FR-005, FR-012, FR-018 | |
| US3-2 | T034 | FR-019 | |
| US4-1 | T045 | FR-022 | |
| US4-2 | T046 | FR-026, FR-027 | |
| US4-3 | T047 | FR-027 | |
| US4-4 | T048 | FR-014, FR-031 | |
| US4-5 | T049, T064 | FR-024 | T064 bloqueada hasta que A suba `Modelo/BusquedaRuta.py` |
| US4-6 | T050 | FR-027 | |
| US4-7 | T083 | FR-022, FR-030 | En la Fase 5, tras la bitácora v2 |
| US4-8 | T051 | FR-023, FR-029 | |
| US4-9 | T052 | FR-027, FR-028 | |
| US5-1 | T068 | FR-015 | |
| US5-2 | T087 | FR-017 | |

## Estrategia de implementación

- **MVP**: fases 0 a 2. El conocimiento existe y se revierte, y se verifica por pruebas.
- **Primer valor visible**: Fase 3, `mapa`.
- **Entrega completa de la spec**: fases 4 y 5. La Historia 4 funciona en el juego real cuando Persona A suba `Modelo/BusquedaRuta.py`.
- Cada subida a `main` lleva la suite en verde, y las pruebas con búsqueda real quedan con `skip` hasta T063.
- Antes de T079, no presentar guardar y cargar como cumplidos; antes de T110, no afirmar que se cumple §6.1.
