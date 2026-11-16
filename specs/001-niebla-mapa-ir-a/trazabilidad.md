# Matriz de trazabilidad: niebla de guerra, mapa conocido e «ir a»

**Tarea**: T115 · **Fecha**: 2026-11-16 · **Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Tareas**: [tasks.md](tasks.md)

Una fila por cada uno de los **31 FR** (FR-001 a FR-031) y los **7 SC** (SC-001 a SC-007) de la spec, más los
**9 casos de SC-001** (los 6 de «Niebla de guerra e ir a» del Apéndice B y los 3 adicionales). Las cifras se contaron
en `spec.md`.

**Cómo leer las columnas**

- **PR**: requisito del plan ([plan.md](plan.md#requisitos-del-plan)).
- **Tareas**: las de [tasks.md](tasks.md) cuyo «Atiende» cita el FR o el SC. Una tarea con `*` sigue abierta (`[ ]`).
- **Prueba**: `archivo::nombre` de la prueba. Cada una se buscó por su ID y se verificó abriendo el archivo. Los IDs de
  esta tabla son los de la spec 001. Otras specs (002, 003, 004) usan los mismos números para requisitos distintos
  (por ejemplo, `tests/test_terreno.py` y algunas clases de `tests/test_ruta_contrato.py` siguen la numeración de
  la spec 003), y esas pruebas no se citan como evidencia de un FR de la 001.
- **Estado**: uno solo de *hecho* (hay prueba que pasa en la suite actual), *bloqueado* (con la causa) o *pendiente*
  (con la causa).

**Suite al escribir esta matriz**: `python -m unittest discover -s tests -t .` → `Ran 810 tests`, `OK`, sin red.

## Requisitos funcionales (FR)

| FR | PR | Tareas | Prueba | Estado |
|----|----|--------|--------|--------|
| FR-001 | PR-01 | T013, T025, T029, T101 | `tests/test_conocimiento.py::test_fr001_fr002_fr004_sala_inicial_en_el_instante_0`<br>`tests/test_conocimiento.py::test_fr001_lo_revelado_es_coherente_con_los_estados`<br>`tests/test_conocimiento.py::test_fr001_ids_opacos_y_destino_inexistente` | hecho |
| FR-002 | PR-01, PR-05 | T013, T019, T026, T029 | `tests/test_conocimiento.py::test_fr001_fr002_fr004_sala_inicial_en_el_instante_0`<br>`tests/test_conocimiento.py::test_fr002_la_sala_inicial_no_se_puede_revertir` | hecho |
| FR-003 | PR-01 | T014, T026, T030, T102 | `tests/test_conocimiento.py::test_fr003_fr004_fr005_de_avistada_a_explorada`<br>`tests/test_conocimiento.py::test_fr003_una_trampa_mortal_no_impide_explorar_la_sala` | hecho |
| FR-004 | PR-01 | T013, T014, T024, T025, T069, T074 | `tests/test_conocimiento.py::test_fr004_una_sala_explorada_no_vuelve_a_avistada`<br>`tests/test_antorcha.py::test_fr004_los_vecinos_de_una_explorada_con_antorcha_quedan_avistados`<br>`tests/test_persistencia_conocimiento.py::test_fr004_fr015_avistadas_recalculadas_y_no_guardadas` | hecho |
| FR-005 | PR-01, PR-13 | T002\*, T003, T118, T006\*, T007\*, T008\*, T009\*, T010\*, T011\*, T012\*, T014, T025, T033, T036, T038, T101 | `tests/test_conocimiento.py::test_fr003_fr004_fr005_de_avistada_a_explorada`<br>`tests/test_mapa.py::test_fr005_avistada_solo_por_su_id`<br>`tests/test_mapa.py::test_fr005_costo_distinto_de_100`<br>`tests/test_costo_salida.py::test_fr005_mover_usa_el_costo_de_la_salida`<br>`tests/test_viaje.py::test_fr005_fr024_el_costo_viene_de_costo_salida` | pendiente: **depende de T010** (capacidad de terreno y costos) para probarse con costos reales; ver [Estado de T010](#estado-de-t010) |
| FR-006 | PR-02, PR-07 | T061, T016, T017, T023, T026, T031, T071, T077 | `tests/test_conocimiento.py::test_fr006_al_entrar_al_origen_el_recuerdo_queda_cerrado`<br>`tests/test_conocimiento.py::test_fr006_al_entrar_al_destino_el_recuerdo_queda_cerrado`<br>`tests/test_conocimiento.py::test_fr006_esperando_en_la_sala_se_observa_el_cierre`<br>`tests/test_persistencia_conocimiento.py::test_fr006_fr015_h2_puerta_abierta_de_una_sala_no_restaurada` | hecho |
| FR-007 | PR-02 | T015, T016, T026, T031 | `tests/test_conocimiento.py::test_fr007_fr012_cierre_no_observado_conserva_el_recuerdo` | hecho |
| FR-008 | PR-02 | T017, T026, T031 | `tests/test_conocimiento.py::test_fr008_abrir_se_refleja_de_inmediato` | hecho |
| FR-009 | PR-03 | T020, T022, T024, T027, T030, T102 | `tests/test_antorcha.py::test_fr009_fr010_explora_sin_activar_enemigos_ni_trampas`<br>`tests/test_antorcha.py::test_fr009_con_la_antorcha_apagada_solo_explora_la_sala_de_llegada`<br>`tests/test_antorcha.py::test_fr009_vecinas_ya_exploradas_no_cambian` | hecho |
| FR-010 | PR-03 | T020, T027, T030, T036 | `tests/test_antorcha.py::test_fr009_fr010_explora_sin_activar_enemigos_ni_trampas`<br>`tests/test_mapa.py::test_fr010_fr018_sin_llaves_enemigos_trampas_ni_objetos` | hecho |
| FR-011 | PR-03, PR-10 | T023, T024, T027, T035, T044, T055, T062 | `tests/test_antorcha.py::test_fr006_fr011_las_puertas_de_una_vecina_quedan_sin_observar`<br>`tests/test_antorcha.py::test_fr011_una_salida_observada_no_vuelve_a_sin_observar`<br>`tests/test_viaje.py::test_fr011_una_salida_sin_observar_no_existe_para_la_busqueda`<br>`tests/test_viaje.py::test_fr011_fr023_sc002_escenario_us2_4_ir_a_no_usa_salidas_sin_observar` | hecho |
| FR-012 | PR-04 | T015, T018, T031, T032, T033, T036, T038, T055 | `tests/test_conocimiento.py::test_fr012_la_linea_salidas_sale_del_recuerdo`<br>`tests/test_conocimiento.py::test_fr007_fr012_cierre_no_observado_conserva_el_recuerdo`<br>`tests/test_mapa.py::test_fr012_sc002_muestra_el_recuerdo_y_no_la_puerta_real` | hecho |
| FR-013 | PR-04 | T018 | `tests/test_conocimiento.py::test_fr013_la_precarga_no_cambia_el_conocimiento` | hecho |
| FR-014 | PR-05 | T019, T021, T028, T030, T048, T103, T106 | `tests/test_conocimiento.py::test_fr014_pergamino_revierte_un_mover_sin_antorcha`<br>`tests/test_antorcha.py::test_fr014_pergamino_restaura_exactamente_el_conocimiento`<br>`tests/test_conocimiento.py::test_fr014_varios_pergaminos_seguidos_restauran_cada_estado`<br>`tests/test_persistencia_conocimiento.py::test_fr014_el_pergamino_sigue_restaurando_el_conocimiento` | hecho |
| FR-015 | PR-06, PR-07 | T068 a T080, T105, T119 | `tests/test_persistencia_conocimiento.py::test_fr015_sc003_escenario_us5_1_el_mapa_conocido_es_identico`<br>`tests/test_persistencia_conocimiento.py::test_fr015_ida_y_vuelta_binaria`<br>`tests/test_persistencia_conocimiento.py::test_fr015_ida_y_vuelta_json`<br>`tests/test_json.py::test_fr015_t073_incluye_conocimiento_con_los_mismos_campos_que_el_binario` | hecho |
| FR-016 | PR-06, PR-16 | T066, T070, T076, T079, T098, T119, T122, T113\* | `tests/test_persistencia_conocimiento.py::test_fr016_version_2`<br>`tests/test_persistencia_conocimiento.py::test_fr016_rechaza_bloques_danados`<br>`tests/test_persistencia_conocimiento.py::test_fr016_inicio_salas_sigue_la_formula_de_d` | pendiente: el rechazo de la versión anterior tiene prueba, pero el README todavía describe el formato sin el bloque de conocimiento (`[encabezado][bloque del jugador][bloques de sala][índice]`). Documentar `CRPT` 3 es T113, abierta |
| FR-017 | PR-12, PR-14 | T067, T084, T086 a T096, T120, T121, T123, T124, T113\* | `tests/test_persistencia_conocimiento.py::test_fr017_sc004_escenario_us5_2_guardar_cargar_continuar_y_reproducir`<br>`tests/test_persistencia_conocimiento.py::test_fr017_cargar_con_la_bitacora_del_guardado_se_rechaza`<br>`tests/test_persistencia_conocimiento.py::test_fr017_guardar_con_la_bitacora_del_destino_se_rechaza`<br>`tests/test_bitacora.py::test_fr017_cargar_llama_a_recargar_y_sigue_con_el_motor_que_devuelve`<br>`tests/test_integracion.py::test_fr017_pr14_replay_termina_con_codigo_0_sin_vista` | hecho. Aparte: la condición (d) de P-07 (documentar `@cargar` en el README) sigue en T113 |
| FR-018 | PR-08 | T033, T035 a T040, T111 | `tests/test_mapa.py::test_fr005_fr012_fr018_exploradas_con_salidas_y_avistadas_aparte`<br>`tests/test_mapa.py::test_fr018_el_dto_trae_direccion_destino_costo_y_estado`<br>`tests/test_mapa.py::test_fr018_ninguna_sala_desconocida_aparece_como_entrada_propia` | hecho |
| FR-019 | PR-08 | T034, T040, T111 | `tests/test_mapa.py::test_fr019_en_el_instante_0`<br>`tests/test_mapa.py::test_fr019_despues_de_moverse_y_con_pergamino`<br>`tests/test_mapa.py::test_fr019_mapa_no_se_anota_en_la_bitacora` | hecho |
| FR-020 | PR-08, PR-09, PR-16 | T039, T059, T111, T112\* | `tests/test_mapa.py::test_fr020_la_ayuda_incluye_mapa` | pendiente: la ayuda incluye `ir a <sala>` (T059), pero **sin prueba**: la única prueba comprueba `mapa`. El README documenta `mapa` (T111), pero no `ir a <sala>`: eso es T112, abierta |
| FR-021 | PR-09 | T053, T054, T058, T064, T065, T112\* | `tests/test_viaje.py::test_fr021_fr023_recorrido_completo_de_ida_y_vuelta_sin_inyeccion`<br>`tests/test_viaje.py::test_fr021_ir_mal_formado_da_error_de_uso`<br>`tests/test_viaje.py::test_fr021_el_comando_admite_mayusculas_y_espacios` | hecho |
| FR-022 | PR-09 | T045, T053, T057, T058, T083, T085 | `tests/test_viaje.py::test_fr022_sc005_escenario_us4_1_sala_avistada_desconocida_inexistente_o_no_valida`<br>`tests/test_viaje.py::test_fr022_sala_actual`<br>`tests/test_viaje.py::test_fr022_explorada_sin_ruta`<br>`tests/test_viaje.py::test_fr022_rechazos_sin_inyeccion_no_tienen_efectos` | hecho |
| FR-023 | PR-10 | T041, T043, T044, T051, T055, T057, T062, T064 | `tests/test_viaje.py::test_fr023_fr029_solo_salas_exploradas_y_puertas_recordadas_abiertas`<br>`tests/test_viaje.py::test_fr005_fr023_el_motor_arma_el_grafo_con_su_conocimiento_y_costo_salida`<br>`tests/test_ruta_contrato.py::test_fr023_las_aristas_son_dirigidas` | hecho |
| FR-024 | PR-10, PR-13 | T003, T118, T008\*, T012\*, T041, T042, T043, T049, T062, T063, T064, T104, T109, T110\* | `tests/test_ruta_contrato.py::test_fr024_ruta_mas_barata_con_mas_saltos`<br>`tests/test_ruta_contrato.py::test_fr024_empate_va_a_la_vecina_de_menor_id_en_cualquier_orden`<br>`tests/test_ruta_contrato.py::test_fr024_dos_salidas_a_la_misma_vecina_gana_n_s_e_o`<br>`tests/test_ruta_contrato.py::test_fr024_pr10_misma_tabla_de_desempates_que_la_busqueda_compartida`<br>`tests/test_viaje.py::test_fr024_escenario_us4_5_empate_va_a_la_vecina_de_menor_id_con_busqueda_real` | pendiente: **depende de T010** (capacidad de terreno y costos) para probarse con costos reales; hoy se prueba con grafos de prueba y costos puestos a mano. Ver [Estado de T010](#estado-de-t010) |
| FR-025 | PR-09 | T002\*, T007\*, T009\*, T011\*, T054, T056, T058 | `tests/test_viaje.py::test_fr021_fr025_mismo_estado_y_bitacora_que_los_mover_a_mano` | hecho |
| FR-026 | PR-09 | T046, T053, T054, T056, T104 | `tests/test_viaje.py::test_fr026_con_otra_ruta_el_viaje_sigue_por_ella`<br>`tests/test_viaje.py::test_fr026_recalcula_antes_de_cada_paso`<br>`tests/test_viaje.py::test_fr026_puerta_que_se_cierra_sola_con_el_jugador_en_ella` | hecho |
| FR-027 | PR-09 | T046, T047, T050, T052 a T054, T056 a T058, T060, T112\* | (a) y prioridad: `tests/test_viaje.py::test_fr027_prioridad_fin_dano_enemigos_destino`<br>(b) `tests/test_viaje.py::test_fr027b_escenario_us4_3_enemigo_dormido_se_activa_y_detiene`<br>(c) `tests/test_viaje.py::test_fr027c_escenario_us4_6_veneno_activo_desde_antes_de_la_orden`<br>(d) `tests/test_viaje.py::test_fr027d_sin_ruta_al_recalcular`<br>(e) `tests/test_viaje.py::test_fr027e_victoria_en_un_paso`<br>(f) `tests/test_viaje.py::test_fr027f_paso_rechazado_detiene_con_el_mensaje_de_mover_sin_tiempo` | hecho |
| FR-028 | PR-09 | T052, T057 | `tests/test_viaje.py::test_fr028_escenario_us4_9_se_acepta_con_enemigos_en_la_sala_actual` | pendiente: **hueco conocido**. La única prueba usa un enemigo **activo** en la sala de partida; no hay prueba con un enemigo **dormido** ahí, y FR-028 cubre los dos. No se implementa en esta tarea |
| FR-029 | PR-10 | T044, T051, T055, T062 | `tests/test_viaje.py::test_fr023_fr029_escenario_us4_8_puerta_cerrada_con_llave_no_cuenta`<br>`tests/test_viaje.py::test_fr023_fr029_solo_salas_exploradas_y_puertas_recordadas_abiertas` | hecho |
| FR-030 | PR-11 | T066, T081 a T085, T088, T098, T113\* | `tests/test_bitacora.py::test_fr030_comentar_escribe_numeral_y_texto`<br>`tests/test_bitacora.py::test_fr030_leer_bitacora_omite_los_comentarios`<br>`tests/test_bitacora.py::test_fr030_cripta_log_1_se_rechaza`<br>`tests/test_viaje.py::test_fr030_sc004_viaje_completo_deja_comentario_antes_del_primer_mover_y_se_reproduce` | pendiente: el comportamiento tiene prueba, pero el README todavía muestra `CRIPTA-LOG 1` y no documenta los comentarios. Documentar la versión 2 es T113, abierta |
| FR-031 | PR-05, PR-09 | T028, T048, T056, T088 | `tests/test_viaje.py::test_fr014_fr031_escenario_us4_4_tras_viaje_completo_deshace_solo_el_ultimo_paso`<br>`tests/test_viaje.py::test_fr014_fr031_tras_viaje_detenido_deshace_el_paso_con_su_conocimiento`<br>`tests/test_persistencia_conocimiento.py::test_fr017_fr030_fr031_ir_a_y_pergaminos_sin_y_con_carga` | hecho |

### Estado de T010

- **En tasks.md de la 001**, T010 sigue abierta (`[ ]`), igual que T002 y T006 a T012, todas a cargo de quien implemente §3.1.
- **En el código**, la spec 003 (terreno y cazador) ya hizo ese trabajo con sus tareas T027 a T031, marcadas como hechas
  en `specs/003-terreno-cazador/tasks.md`:
  - `DTOS/Salida.py` tiene el campo `costo` y `desde_json` valida que sea un entero mayor o igual que 1.
  - `mover_jugador` cobra `self.costo_salida(salida)`, y los enemigos también.
- **Diferencia con el texto de T010**: el valor por defecto del DTO es `COSTO_POR_DEFECTO = 100`, no `None`. Así
  `costo_salida` sigue dando 100, pero se pierde la distinción entre «sin costo propio» y «cuesta 100» que pedía R7.
- **Pruebas**: las de la 001 usan costos puestos a mano en la salida o grafos de prueba. La única prueba de «ir a» con
  costos de un paquete es de la spec 003 (`tests/test_terreno.py::test_fr004_fr026_cada_paso_de_ir_a_avanza_el_costo_de_su_salida`,
  numeración de la 003), y no se cita como evidencia de la 001.
- **Lo que falta para pasar FR-005 y FR-024 a «hecho»**: que el grupo decida si T027 a T031 de la 003 cierran T010 de
  la 001, o que se cierre T010.

## Criterios de éxito (SC)

| SC | PR | Tareas | Prueba o medición | Estado |
|----|----|--------|-------------------|--------|
| SC-001 | PR-16 | T005, T098, T116\* | Los 9 casos, en [la tabla de abajo](#los-9-casos-de-sc-001); cada uno tiene al menos una prueba automática que cita su FR | hecho (las pruebas automáticas bastan según SC-001). El recorrido manual del quickstart es T116 y no se hizo en esta tarea |
| SC-002 | PR-04, PR-08, PR-10 | T035, T036, T044, T116\* | `tests/test_mapa.py::test_fr011_fr018_sc002_puerta_de_una_vecina_sin_observar`<br>`tests/test_mapa.py::test_fr012_sc002_muestra_el_recuerdo_y_no_la_puerta_real`<br>`tests/test_viaje.py::test_fr011_fr023_sc002_escenario_us2_4_ir_a_no_usa_salidas_sin_observar` | hecho |
| SC-003 | PR-06 | T068, T116\* | `tests/test_persistencia_conocimiento.py::test_fr015_sc003_escenario_us5_1_el_mapa_conocido_es_identico` | hecho |
| SC-004 | PR-11, PR-12 | T083, T087, T088, T090, T091, T094, T116\* | `tests/test_persistencia_conocimiento.py::test_fr017_sc004_escenario_us5_2_guardar_cargar_continuar_y_reproducir`<br>`tests/test_persistencia_conocimiento.py::test_fr017_fr030_fr031_ir_a_y_pergaminos_sin_y_con_carga`<br>`tests/test_viaje.py::test_fr030_sc004_viaje_completo_deja_comentario_antes_del_primer_mover_y_se_reproduce` | hecho. Nota: la prueba con «ir a» y pergaminos usa un buscador de prueba inyectado, no la búsqueda real |
| SC-005 | PR-09, PR-11 | T045, T053, T058, T083, T085, T116\* | `tests/test_viaje.py::test_fr022_sc005_escenario_us4_1_sala_avistada_desconocida_inexistente_o_no_valida`<br>`tests/test_viaje.py::test_fr022_sc005_orden_rechazada_no_deja_linea`<br>`tests/test_viaje.py::test_fr030_sc005_rechazo_del_primer_mover_no_deja_linea` | hecho |
| SC-006 | PR-16 | T001, T009\*, T019, T081, T097, T099, T106, T108, T116\* | Suite completa: `Ran 810 tests`, `OK`, sin red<br>`tests/test_conocimiento.py::test_sc006_motor_sin_iniciar_partida_funciona_sin_conocimiento`<br>`tests/test_bench_niebla.py::test_sc006_pr15_t108_m1_a_m6_con_tamanos_minimos_sin_red_ni_vista` | hecho |
| SC-007 | PR-15 | T003, T104, T109, T110\* | `tests/test_bench_niebla.py::test_sc007_pr15_t108_m4_con_y_sin_espacio_compara_contra_la_constante` (forma y veredicto, sin afirmar tiempos)<br>Medición M4 en [`resultados_bench_niebla.txt`](../../resultados_bench_niebla.txt), PROVISIONAL, con mapas sintéticos (ver abajo) | **pendiente de T110**: §6.1 no se da por cumplido |

**SC-007 y §6.1.** El límite es de 5 ms por paso «con el mapa conocido completo de la cripta de referencia», que aún no
está publicada. M4 mide la `primer_paso` real sobre mapas sintéticos. Todas sus filas son PROVISIONAL. Filas de un
paso, por llamada, de `resultados_bench_niebla.txt`:

```text
M4 grilla/paso      V=400 pasos=1 espacio=por llamada     1.4221 ms   PROVISIONAL cumple
M4 grilla/paso      V=2500 pasos=1 espacio=por llamada    12.3162 ms   PROVISIONAL no cumple
M4 cadena/paso      V=2500 pasos=1 espacio=por llamada     2.5780 ms   PROVISIONAL cumple
M4 grilla/paso      V=2500 pasos=1 espacio=reutilizado     8.8986 ms   PROVISIONAL no cumple
```

Con V = 400 o menos todo cumple. La grilla de 2500 es una prueba de estrés y no cumple. El veredicto definitivo es
T110, que agrega a M4 el mapa conocido completo de la cripta de referencia. El detalle está en
[DECISIONES.md, §5.3](../../Decisiones/DECISIONES.md).

## Los 9 casos de SC-001

**Evidencia de partidas jugadas.** `partida.log` ya no se versiona: está en `.gitignore`. La evidencia de partidas
jugadas que agregue T116 irá en un archivo con otro nombre, que se define en esa tarea. Esta tarea no lo crea.

| # | Caso | Origen | FR | Prueba automática | Partida jugada (T116) | Estado |
|---|------|--------|----|-------------------|-----------------------|--------|
| 1 | Antorcha explora sin activar enemigos ni trampas | Apéndice B | FR-009, FR-010 | `tests/test_antorcha.py::test_fr009_fr010_explora_sin_activar_enemigos_ni_trampas` | pendiente (T116, quickstart 3) | hecho |
| 2 | Pergamino revierte entrada con antorcha | Apéndice B | FR-014 | `tests/test_antorcha.py::test_fr014_pergamino_restaura_exactamente_el_conocimiento` | pendiente (T116, quickstart 3) | hecho |
| 3 | «ir a» hacia sala no explorada | Apéndice B | FR-022 | `tests/test_viaje.py::test_fr022_sc005_escenario_us4_1_sala_avistada_desconocida_inexistente_o_no_valida` | pendiente (T116, quickstart 4) | hecho |
| 4 | Puerta recordada abierta que está cerrada | Apéndice B | FR-006, FR-026 | `tests/test_conocimiento.py::test_fr006_al_entrar_al_origen_el_recuerdo_queda_cerrado`<br>`tests/test_viaje.py::test_fr026_con_otra_ruta_el_viaje_sigue_por_ella`<br>`tests/test_viaje.py::test_fr026_fr027_sin_otra_ruta_se_detiene_sin_tiempo_adicional` | pendiente (T116, quickstart 2 y 4) | hecho |
| 5 | «ir a» entra a sala con enemigos dormidos | Apéndice B | FR-027b | `tests/test_viaje.py::test_fr027b_escenario_us4_3_enemigo_dormido_se_activa_y_detiene` | pendiente (T116, quickstart 4) | hecho |
| 6 | Pergamino durante un viaje | Apéndice B | FR-031 | `tests/test_viaje.py::test_fr014_fr031_escenario_us4_4_tras_viaje_completo_deshace_solo_el_ultimo_paso`<br>`tests/test_viaje.py::test_fr014_fr031_tras_viaje_detenido_deshace_el_paso_con_su_conocimiento` | pendiente (T116, quickstart 4) | hecho |
| 7 | Sala inicial en el instante 0 | Adicional | FR-002 | `tests/test_conocimiento.py::test_fr001_fr002_fr004_sala_inicial_en_el_instante_0` | pendiente (T116, quickstart 1) | hecho |
| 8 | De avistada a explorada | Adicional | FR-003, FR-004 | `tests/test_conocimiento.py::test_fr003_fr004_fr005_de_avistada_a_explorada` | pendiente (T116, quickstart 1) | hecho |
| 9 | Guardar y cargar con conocimiento | Adicional | FR-015 | `tests/test_persistencia_conocimiento.py::test_fr015_sc003_escenario_us5_1_el_mapa_conocido_es_identico` | pendiente (T116, quickstart 6) | hecho |

## Resumen

| | Total | hecho | bloqueado | pendiente |
|---|---|---|---|---|
| FR | 31 | 25 | 0 | 6 (FR-005, FR-016, FR-020, FR-024, FR-028, FR-030) |
| SC | 7 | 6 | 0 | 1 (SC-007) |
| Casos de SC-001 | 9 | 9 | 0 | 0 |

**Causas de lo pendiente**

- **FR-005 y FR-024**: T010 abierta en la 001, aunque el código ya existe por la spec 003.
- **FR-016 y FR-030**: falta el README de los formatos (T113).
- **FR-020**: falta la prueba de `ir a` en la ayuda, y el README de `ir a` (T112).
- **FR-028**: falta la prueba con un enemigo dormido en la sala de partida.
- **SC-007**: §6.1 queda pendiente de T110.

Ningún FR quedó **sin prueba**. FR-020 tiene una prueba solo para `mapa`; la parte de `ir a <sala>` en la ayuda está
sin prueba.
