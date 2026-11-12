# Contrato: interfaz entre el Controlador y la línea de tiempo

Qué le pasa el `ControladorPartida` (y el `Reproductor`, mediante el observador) a la línea, y qué le devuelve. Contrato compartido
dentro del equipo (Flujo de desarrollo): lo usan las personas A y C. `Modelo/LineaTiempo.py` no importa red, archivos, consola ni
adaptadores (Principio II): lo que necesita del exterior se **inyecta**.

## Una sola vía de registro

La partida jugada, el replay y la reconstrucción al cargar registran **por el mismo camino**, que es lo que garantiza FR-025:

```text
ObservadorLinea (Controlador/ObservadorLinea.py)        adaptador: traduce los tres avisos a la LineaTiempo
    al_crear_motor(motor)
    despues_de_accion(motor, nombre, argumento)         nombre == "retroceder" o una acción que cuenta
    despues_de_carga(motor)                             hace la copia privada del archivo y avisa a la línea
```

El controlador llama a `despues_de_accion` desde `_accion`, **después** de que `motor.ejecutar_accion` devolvió `True` y de
`bitacora.registrar`. `Reproductor` los llama con el parámetro `observador` ([formato-bitacora.md](formato-bitacora.md)). Una acción
rechazada no llega: no se registra nada.

**Hecho por C** (`b1b57d7`, 001-T123/T124). La firma real del `Reproductor` es `Reproductor(fabrica_motor, version_cripta, version_catalogo, recargar=None, observador=None)`, con `reproducir_acciones(encabezado, acciones) -> motor` y `reproducir(ruta) -> motor` (lee la bitácora y llama a la anterior); los avisos van en este orden: `al_crear_motor(motor)` tras crear el motor, `despues_de_accion(motor, nombre, argumento)` tras cada acción no rechazada y `despues_de_carga(motor)` tras `@cargar`. Al llegar a `@cargar`
llama a `recargar(motor)`, que **recibe el motor actual y devuelve el nuevo**. `despues_de_carga(motor)` recibe el motor **nuevo**
(el que devolvió `recargar`); el adaptador no conserva el anterior. En el controlador (`cargar`) el motor nuevo viene de
`cargar_partida` y la llamada es la misma.

### De dónde sale el sello previo

`despues_de_accion` llega con el motor **ya avanzado**: la acción *k* ya se ejecutó. Por eso el sello `(reloj, secuencia)` previo de
la acción *k* (el de la decisión anterior a ella) **se toma al terminar el aviso anterior**: el que dejó `al_crear_motor` (acción
1), `despues_de_accion` de la acción *k − 1*, `registrar_retroceso` (tras un `retroceder`) o `despues_de_carga` (tras un `@cargar`,
con el motor nuevo). `registrar_accion(motor, nombre, argumento)` usa el sello que la línea guardó al cerrar el aviso anterior y,
antes de volver, guarda el del motor ya avanzado para la acción siguiente. Una acción rechazada no avisa y no cambia el sello
guardado.

### Decisión pendiente de aprobación (M3): la ruta en `despues_de_carga`

`despues_de_carga(motor)` no trae la ruta del archivo cargado, y la línea necesita una copia privada. **Propuesta, no definitiva**:
tomarla de `motor.restaurador.ruta` (así lo hace `guardar_motor` con `anterior.ruta`). Si `motor.restaurador` es `None`, la época se
abre sin copia privada (`epocas_ruta = None`) y la carga sigue. Requiere confirmar con una prueba contra el código real y la
aprobación del grupo ([data-model.md, Época](../data-model.md#época)).

## `LineaTiempo` (Modelo)

```text
LineaTiempo(k=50, gestor_historico=None, abrir_copia=None)
    k                 acciones máximas entre puntos de control (>= 1); por defecto 50, HIPÓTESIS hasta M1 y M2
    gestor_historico  GestorDatos sin red para los clones (research R10); lo crea el controlador. Un solo clon vivo a la vez
                      (ver «Reglas del clon y del gestor histórico»)
    abrir_copia       función(ruta_copia) -> restaurador de solo lectura, o None; la inyecta el controlador

Registro (los llama el ObservadorLinea)
    iniciar(motor)                                  motor recién creado o recién cargado sin historia previa
    registrar_accion(motor, nombre, argumento)      comando aceptado que cuenta como acción
    registrar_retroceso(motor)                      'retroceder' aceptado
    registrar_carga(motor, ruta_copia)              frontera de @cargar; motor ya cargado

Consulta (solo lectura, ver garantías)
    consultar_instante(t, motor) -> ResumenHistorico
    consultar_accion(k, motor)   -> ResumenHistorico
    clon_antes_de(k, motor)      -> MotorSimulacion   clon desechable del estado justo antes de la acción k, para las pruebas de A
                                                      (ver «Lo que la línea ofrece a A»); la consulta de producción no lo expone

Lectura
    k, acciones, reloj_actual, cantidad_puntos      propiedades

Persistencia y ciclo de vida
    a_registro() -> RegistroLinea                   guion + K, para guardar_partida
    LineaTiempo.desde_registro(registro, ...)       solo datos; la reconstrucción la hace el controlador
    cerrar()                                        pide borrar las copias privadas (el controlador las borra)
```

`motor` es siempre el **motor vivo** de la partida (o del replay). La línea no lo guarda.

### Excepciones

| Excepción | Cuándo | Cómo la trata el controlador |
|-----------|--------|------------------------------|
| `ReferenciaInvalida(motivo)` | `t` o `k` fuera de rango (`t > reloj_actual`, `k < 1`, `k > acciones + 1`) | aviso de [comandos-historia.md](comandos-historia.md) |
| `ErrorReconstruccion(detalle)` | el sello `(reloj, secuencia)` del clon no coincide con el guardado, o el clon rechazó una acción | `! Error: No se pudo reconstruir ese momento: ...`, código `1` |
| `SinDatosParaHistoria(que)` (subclase de `RuntimeError`) | el gestor histórico no tiene un dato local, en una consulta **o al cargar** | `! Error: No se puede reconstruir sin nuevas solicitudes: faltan datos locales (<qué>)`, código `1`. Al cargar, **no se carga nada** (la partida en curso queda intacta) |

## Precondiciones, efectos y complejidad

`n` = acciones vigentes, `K`, `C` puntos, `S` tamaño del estado, `a` costo de una acción, `V` acciones recortadas.

| Operación | Cuándo | Efecto | Tiempo | Memoria |
|-----------|--------|--------|--------|---------|
| `iniciar` | partida nueva | punto de control en la acción 0, sello inicial `(reloj, secuencia)`, cantidad inicial de pergaminos | `O(S)` | `O(S)` |
| `registrar_accion` | tras cada acción que cuenta | agrega al guion y a la historia vigente; compara y actualiza la serie de pergaminos; si `n % K == 0`, punto de control | `O(1)` + `O(S)` cada K | `O(1)` + `O(S)` cada K |
| `registrar_retroceso` | tras `retroceder` aceptado | `V = acciones_antes - acciones_después` del motor; recorta la historia vigente y los puntos con `accion > nuevo_n`; agrega `RETROCESO`; punto del motor real en `nuevo_n`; pliega la serie | `O(V) + O(S)` | `O(S)` |
| `registrar_carga` | tras cargar | agrega `CARGA`; punto del motor cargado en la acción `n` (reemplaza uno regular en `n`); abre época con la copia privada | `O(S)` | `O(S)` + copia |
| `consultar_instante(t)` | `historia <t>`, `--hasta` | ver abajo | `O(log n + log C + S + K·a)` | `O(S)` temporal |
| `consultar_accion(k)` | `historia #k` | ver abajo | `O(log C + S + K·a)` | `O(S)` temporal |
| `a_registro` | `guardar` | copia el guion y K | `O(n)` | `O(n)` |

### `consultar_instante(t)`

```text
si t > reloj_actual:                       ReferenciaInvalida
si t == reloj_actual (partida en curso):   resumen del motor vivo (estado actual)
si la partida terminó y t >= reloj final:  resumen del motor vivo
k = última acción vigente con reloj_dec[k] <= t        # búsqueda binaria propia
si reloj_dec[k] == t:                      return consultar_accion(k)           # decisión en t
clon = antes_de(k)                          # estado de la decisión k
clon.agenda -> AgendaConCorte(corte = t)    # oculta los eventos con tiempo > t
clon.ejecutar_accion(guion de la acción k)  # corre los eventos con tiempo <= t y se detiene
return resumir(clon, reloj = t, pergaminos = serie(clave <= k))
```

### `consultar_accion(k)`

```text
si k == acciones + 1:                      resumen del motor vivo (estado actual)
c = último punto de control con accion <= k - 1        # búsqueda binaria propia
clon = materializar(c)                     # esqueleto propio + deepcopy + gestor histórico
para j = c + 1 .. k - 1:
    comparar (clon.reloj, clon.secuencia) con el sello de la acción j       # ErrorReconstruccion si difiere
    clon.ejecutar_accion(guion de la acción j)                              # rechazo -> ErrorReconstruccion
comparar el sello de la decisión k
return resumir(clon, reloj = reloj_dec[k], pergaminos = serie(clave <= k - 1))
```

Rehace a lo sumo `K` acciones (FR-019).

## Garantías (lo que prueban SC-004 y FR-008)

1. **Solo lectura**: tras cualquier consulta, aceptada o rechazada, el motor vivo es idéntico (`obtener_estado_resumen()`,
   `conocimiento`, `mensajes`, `rastros`, historial de retroceso), no cambia el reloj, ni el contador de acciones, ni la bitácora.
2. **Aislamiento del clon**: el clon tiene esqueleto propio, historial vacío y `restaurador` propio; no comparte con el motor vivo
   ningún objeto mutable. Su gestor es el histórico, sin red.
3. **Sin red**: ninguna operación de la línea llama a la fuente de datos.
4. **Determinismo**: el mismo guion desde el mismo punto da el mismo resumen; K no cambia el contenido (FR-028).
5. **Invariante de la historia vigente**: `acciones == acciones_jugador` del motor, salvo en un estado terminal (una muerte en una trampa
   al entrar o una victoria cuentan distinto en el motor); `len(reloj_dec) == acciones`; `pc_accion` no decreciente y sin
   puntos con `accion > acciones`; la serie de pergaminos está ordenada por clave.

### Reglas del clon y del gestor histórico

Medidas o leídas en T003 ([research.md](../research.md#t003-revisión-de-deepcopy-y-memo-2026-11-12)):

6. **El clon se juega con `gestor_historico`.** Un clon sin gestor no puede jugar (medido): entrar en una sala con trampa lanza
   `RuntimeError: No hay gestor de datos para consultar la ficha de la trampa.` y entrar en una sala sin contenido cargado se rechaza
   con `El contenido de esa sala aún no está disponible.`. `materializar` le asigna `gestor_historico`, que sirve `obtener_ficha` y
   `asegurar_sala` desde el almacenamiento en disco; si falta un dato local, `SinDatosParaHistoria`. Con un `GestorDatos` iniciado el
   clon rehace 50 acciones y queda idéntico al vivo (medido).
7. **Un solo clon vivo por `gestor_historico`.** `GestorDatos.estado_juego` es único y `conectar_estado_juego(clon)` lo reemplaza;
   se materializa un clon, se consulta y se descarta antes de materializar otro. **HIPÓTESIS** (leído del código, no medido).
8. **`materializar` fija `eco = False`.** La copia hereda `eco` (medido: un clon con `eco = True` imprime los mensajes).
9. **Ninguna consulta llama `siguiente()` ni `esta_vacia()` sobre el motor vivo.** `AgendaEventos.siguiente()` y `esta_vacia()` no
   son de solo lectura: sacan del heap los eventos cancelados de la raíz. `consultar_accion(acciones + 1)` devuelve el motor vivo
   sin tocar su agenda; el corte de agenda (`AgendaConCorte`) solo se usa en clones.
10. **La reconstrucción nunca ejecuta `retroceder` dentro de un clon.** El clon tiene un `Historial()` vacío y lo rechaza (medido).
    Tras cada retroceso hay un punto de control del motor real en `nuevo_n`, y solo se rehacen acciones vigentes.

## Qué le pide la línea a los demás

| Requisito | A quién | Por qué |
|-----------|---------|---------|
| Todo estado nuevo cuelga del `MotorSimulacion`, de sus actores o de las salas; **ninguna caché ni estado a nivel de módulo** | A (cazador, terreno, invalidación de rutas) y todos | `deepcopy` solo copia lo que cuelga del motor; un estado global haría que la re-simulación divergiera |
| Todo campo **mutable** nuevo de `Sala` o `Salida` se agrega a `CAMPOS_MUTABLES_SALA` o `CAMPOS_MUTABLES_SALIDA` (`Modelo/CopiaEstado.py`) | A | La foto del esqueleto copia solo esos campos; los demás se comparten entre puntos y no se pueden mutar. `Salida.cerrada_en_esqueleto` **no** es mutable: se fija en `Salida.__init__` y ninguna otra línea la cambia |
| Excluir `Modelo/CopiaEstado.py` **por nombre**, con el motivo escrito, de la prueba de T015 que lee el código de `Modelo/` | A | Ver [Choque con T015](#choque-con-t015-de-a-persona-a-003) |
| `ciclo`, `version_puertas`, `GrafoCripta`, `EspacioBusqueda` y `CampoDistancias` cuelgan del motor | A | `deepcopy` los copia con él; el `memo` re-liga las salas del grafo al esqueleto del clon |
| El cazador no consume azar (003 FR-021) y su decisión es función del estado | A | La re-simulación debe reproducir sus decisiones (003 FR-025) |
| Toda mutación reversible se reporta a `historial.registrar` | A | Sin eso, un retroceso deja el motor real distinto de la historia vigente; la prueba de `consultar_accion(acciones + 1)` frente al motor vivo lo detecta |
| El `Historial` y `usar_pergamino` no cambian | A | La línea depende de que un uso revierta exactamente un intervalo |
| `Conocimiento` solo guarda referencias al motor y al esqueleto | C | `deepcopy` las re-liga. T119 (`copiar()`, serialización, `aplicar`/`invertir`) ya está implementado: esta capacidad **no lo usa y no debe retirarse** |

## Choque con T015 de A (persona A, 003)

La tarea T015 de 003 incluye una prueba que **lee el código fuente de `Modelo/` y falla** si aparece, fuera del método único del motor,
`.cerrada =` o `setattr(..., "cerrada", ...)` (o `_asignar_reversible(..., "cerrada", ...)`); hoy solo excluye por nombre
`Modelo/prueba_actores.py`. `Modelo/CopiaEstado.py` (PR-02) **restaura `Salida.cerrada` desde la foto del esqueleto**, es decir,
contiene exactamente esa escritura y haría fallar la prueba en cuanto exista.

**Propuesta [PERSONAS: A]**: excluir también `Modelo/CopiaEstado.py` por nombre, con el motivo escrito en la prueba:

> `Modelo/CopiaEstado.py` escribe `Salida.cerrada` solo sobre las salidas de la **copia** del esqueleto que arma `materializar`, nunca
> sobre las del motor en juego, y fuera de un ciclo de eventos (el clon no está ejecutando ninguno cuando se materializa): no puede dejar
> desactualizado el `version_puertas` de la partida real. Es la restauración de una foto, no una escritura de juego.

Por qué es correcto no pasar por el método único: ese método incrementa el `version_puertas` **del motor** y registra un deshacer en
su `Historial`; el clon recibe un `Historial` vacío y sus contadores vienen copiados con el estado, y la materialización no es un cambio
de partida. Usar el método único en la copia incrementaría un contador del clon sin que haya pasado nada, y registraría deshacer que
nadie usará.

**Consistencia de lo que cuelga del motor en el clon** (003 data-model §2 a §6):

| Pieza de A | En el clon | Cómo queda consistente |
|------------|-----------|------------------------|
| `ciclo`, `version_puertas` | enteros del motor; `deepcopy` los copia | valen lo mismo que en la decisión del punto de control; al re-simular avanzan igual que en la partida real |
| `GrafoCripta` | cuelga del motor; guarda referencias a las salas | el `memo` de `materializar` mapea cada sala del respaldo a su par nuevo, así que el grafo del clon apunta al esqueleto del clon; sus ordinales (atributo propio de la sala) se conservan con `copy.copy` |
| `EspacioBusqueda` | listas por ordinal (`dist`, `primero`, `epoca`) y cola | se copian con el motor, sin referencias al esqueleto vivo |
| `CampoDistancias` | apunta al `EspacioBusqueda` **del mismo motor** | `deepcopy` conserva la identidad dentro de una misma copia, así que apunta al espacio copiado; queda inválido en cuanto `ciclo` avanza en el clon |

La prueba de oráculo (escenario 14, y T059) lo comprueba con cazadores activos. **Si `GrafoCripta` guardara las salas fuera del motor
(en un módulo), la copia las compartiría con la partida real y el escenario 14 falla**: es el motivo del requisito «ningún estado a nivel de
módulo».

## Lo que la línea ofrece a A

Para sus tareas **T058** y **T059** (`tests/test_cazador_equivalencia.py`). Las dos comparan decisiones de cazadores (acción, sala de
destino, salida y costo en cada turno) entre la partida jugada y su reproducción o reconstrucción.

**Requisito previo de A**: las decisiones de los cazadores se anotan en un **registro que cuelga del motor** (por ejemplo una lista en
el propio motor), no en un módulo ni en el controlador. Así el clon lo copia y, al re-simular, vuelve a anotar las mismas decisiones.

| Tarea | Qué llamar | Con qué motor | Qué comparar |
|-------|-----------|---------------|--------------|
| T058 (a): jugada, guardada, cargada, continuada | `ControladorPartida.guardar` y `ControladorPartida.cargar` (hoy, sin la línea) | el motor del controlador antes de guardar y el que devuelve `cargar` | el registro de decisiones antes de guardar y las de la continuación contra una partida no interrumpida con la misma semilla y acciones. **No depende de esta capacidad**: `CRPT` 3 ya existe (T076) y `cargar_partida` también |
| T058 (b): retrocedida y reproducida | `main.ejecutar_replay(ruta_bitacora, gestor)` (T096), que devuelve el motor final | el motor que devuelve y el de la partida jugada | decisiones turno a turno. **No depende de esta capacidad**; con el `observador` (PR-12) solo cambia que la línea también se arma |
| T058 (c): cargar con línea | `ControladorPartida.cargar` tras PR-11 | `controlador.motor` | el guion reproducido al cargar da las mismas decisiones: lo exige el sello `(reloj, secuencia)`; una divergencia termina con `ErrorReconstruccion`, no con un estado falso |
| **T059**: estado pasado de la línea | `linea.clon_antes_de(k, motor)` (PR-04), con `motor` = el motor **vivo** del controlador (`controlador.linea` y `controlador.motor`) | el clon devuelto: es un motor desechable, con gestor histórico sin red | el registro de decisiones del clon contra el del motor vivo **hasta la misma decisión** (mismo `ciclo`); el clon ya pasó por la re-simulación de a lo sumo K acciones |

Notas para A:

- `clon_antes_de` es **solo lectura** para el motor vivo (garantía 1) y el clon se descarta; no lo usen para jugar. Se pide antes de
  consultar el registro del motor vivo, y la línea no cambia el reloj, `ciclo` ni `version_puertas` del motor vivo.
- `consultar_accion(k, motor)` devuelve un `ResumenHistorico` (texto del estado) y **no** expone decisiones; para decisiones de cazadores
  se usa `clon_antes_de`.
- T059 espera a PR-02 a PR-04 de esta capacidad; T058 (c), a PR-10 y PR-11. T058 (a) y (b) no esperan.
- Una partida con cazadores debe poder reproducirse con `random.Random` sin que el cazador consuma azar (003 FR-021): si lo consumiera,
  el sello lo detecta y la reconstrucción se rechaza.

## Cómo usa el controlador la interfaz

| Momento | Llamada |
|---------|---------|
| `nueva_partida` | crea `LineaTiempo(k, gestor_historico)` y `iniciar(motor)` |
| `_accion` (aceptada, después de la bitácora) | `despues_de_accion(motor, nombre, argumento)` |
| `cargar` | reconstruye (reproduce el guion con el `Reproductor` y el observador, verifica, y entrega la línea), luego `registrar_carga`. Si faltan datos locales: `SinDatosParaHistoria`, no se carga nada y el estado del controlador no cambia |
| `guardar` | `guardar_partida(..., linea=linea.a_registro())` |
| `historia` | `consultar_instante` / `consultar_accion` y `vista.mostrar_resumen_historico(dto)` |
| `_cerrar` | `linea.cerrar()` y borrar las copias privadas |
| `--replay --hasta` | `Reproductor(..., observador=ObservadorLinea(linea))`, luego `consultar_instante(t)` o el estado final |
