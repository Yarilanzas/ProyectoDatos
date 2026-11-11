# Contrato: lo que la línea de tiempo (004) necesita de terreno y cazador (003)

Contrato compartido dentro del equipo (Flujo de desarrollo). Recoge, del lado de esta capacidad, los requisitos que
[specs/004-linea-de-tiempo/contracts/interfaz-linea.md](../../004-linea-de-tiempo/contracts/interfaz-linea.md)
(«Qué le pide la línea a los demás», «Choque con T015» y «Lo que la línea ofrece a A») le hace a la persona A. Si los dos
documentos difieren, se corrigen juntos.

**Por qué**: la línea reconstruye estados pasados con `deepcopy` del motor desde un punto de control y re-simulando a lo
sumo K acciones. Solo se copia lo que cuelga del `MotorSimulacion`, y el sello `(reloj, secuencia)` rechaza cualquier
divergencia. Así se cumple FR-025 de esta capacidad: el replay y la reconstrucción dan las mismas decisiones de los
cazadores que la partida jugada.

## 1. Todo el estado cuelga del motor

Todo estado nuevo de esta capacidad cuelga del `MotorSimulacion`, de sus actores o de las salas. **Ninguna caché ni estado
a nivel de módulo** en `Modelo/ColaPrioridad.py`, `Modelo/BusquedaRuta.py`, `Modelo/GrafoCripta.py` ni
`Modelo/MotorSimulacion.py`: ni variables globales, ni atributos de clase mutables, ni memorias de funciones.

Un estado global se compartiría entre el motor vivo y el clon, y la re-simulación divergiría (escenario 14 de 004).

## 2. Piezas que cuelgan del motor

| Pieza (data-model) | Dónde vive | Qué garantiza en el clon |
|--------------------|-----------|--------------------------|
| `ciclo` y `version_puertas` (§6) | Enteros del motor | `deepcopy` los copia; valen lo mismo que en la decisión del punto de control y avanzan igual al re-simular. Solo crecen; no se guardan ni entran en la bitácora |
| `GrafoCripta` (§2) | Atributo del motor; guarda referencias a las salas del esqueleto del motor | El `memo` de `materializar` liga el grafo del clon al esqueleto del clon. Los ordinales son atributos propios de la sala y se conservan con `copy.copy` |
| `EspacioBusqueda` persistente (§4.3) | Atributo del motor: listas por ordinal (`dist`, `primero`, `epoca`) y su `ColaPrioridad` | Se copia con el motor, sin referencias al esqueleto vivo |
| Campo compartido, `CampoDistancias` (§5) | Atributo del motor; apunta al `EspacioBusqueda` del mismo motor | `deepcopy` conserva la identidad dentro de la copia, así que apunta al espacio copiado. Queda inválido en cuanto `ciclo` avanza en el clon |

Si alguna de estas piezas viviera fuera del motor, el clon la compartiría con la partida real.

Todo campo **mutable** nuevo de `Sala` o `Salida` se agrega a `CAMPOS_MUTABLES_SALA` o `CAMPOS_MUTABLES_SALIDA` de
`Modelo/CopiaEstado.py` (004). `Salida.costo` y `Salida.cerrada_en_esqueleto` **no** son mutables: se fijan al leer el
esqueleto y ninguna otra línea los cambia.

## 3. El cazador no consume azar

La decisión del cazador es función del estado en su turno: su sala, su rango, la sala del jugador y el estado de las
puertas (FR-018). No usa `motor.azar` ni el `random` global (FR-021). Si lo consumiera, `secuencia` o el estado del azar
diferirían en la re-simulación, el sello lo detectaría y la reconstrucción se rechazaría con `ErrorReconstruccion`.

Además:

- Toda mutación reversible que haga la capacidad (puertas mediante el método único, movimientos y ataques del cazador)
  se reporta a `historial.registrar` (FR-024).
- El `Historial` y `usar_pergamino` no cambian.
- Una búsqueda de referencia o del bench incrementa la época del espacio y deja inválido el campo compartido: nunca
  cambia una decisión (FR-016).

## 4. Registro de decisiones de los cazadores

Lo necesitan las pruebas de equivalencia T058 y T059 (`tests/test_cazador_equivalencia.py`), que comparan turno a turno
la acción, la sala de destino, la salida y el costo de cada cazador (data-model §8) entre la partida jugada y su
reproducción o reconstrucción.

| Requisito | Regla |
|-----------|-------|
| Dónde vive | **Colgado del motor** (por ejemplo, una lista del propio motor), no en un módulo, en el controlador ni en la prueba. Así el clon lo copia y, al re-simular, vuelve a anotar las mismas decisiones |
| Reversible con la historia | Cada anotación se registra en `historial.registrar`: un retroceso quita las decisiones del intervalo revertido y el registro coincide con la historia vigente |
| Activable | Apagado por defecto en la partida normal; lo encienden las pruebas (y el bench si hiciera falta). Apagado, no cambia nada: ni decisiones, ni reloj, ni `secuencia`, ni bitácora |
| Guardado | **Fuera del guardado**: no entra en el archivo de partida, ni en la bitácora, ni en el registro de la línea, salvo que 004 decida lo contrario y lo escriba en sus contratos |
| Qué anota | Por decisión: `ciclo`, reloj, id del cazador, acción, sala de destino, salida y costo base |

Cómo lo usa cada prueba (detalle en la sección «Lo que la línea ofrece a A» del contrato de 004):

| Tarea | Motor | Depende de 004 |
|-------|-------|----------------|
| T058 (a): jugada, guardada, cargada y continuada | El del controlador antes de guardar y el que devuelve `cargar` | No |
| T058 (b): retrocedida y reproducida | El que devuelve `main.ejecutar_replay(ruta_bitacora, gestor)` | No |
| T058 (c): cargar con línea | `controlador.motor` tras PR-11 de 004 | Sí (PR-10, PR-11) |
| T059: estado pasado | `linea.clon_antes_de(k, motor)` frente al motor vivo, hasta la misma decisión (mismo `ciclo`) | Sí (PR-02 a PR-04) |

`clon_antes_de` es solo lectura para el motor vivo; el clon se descarta.

## 5. Exclusión de `Modelo/CopiaEstado.py` en la prueba de T015

La prueba de T015 (`tests/test_invalidacion_puertas.py`) lee el código fuente de `Modelo/` y falla si aparece, fuera del
método único de puertas, `.cerrada =`, `setattr(..., "cerrada", ...)` o `_asignar_reversible(..., "cerrada", ...)`. Hoy
solo excluye por nombre `Modelo/prueba_actores.py`.

`Modelo/CopiaEstado.py` (004, PR-02) restaura `Salida.cerrada` desde la foto del esqueleto y contiene exactamente esa
escritura. La prueba lo excluye también **por nombre**, con este motivo escrito en la prueba:

> `Modelo/CopiaEstado.py` escribe `Salida.cerrada` solo sobre las salidas de la **copia** del esqueleto que arma
> `materializar`, nunca sobre las del motor en juego, y fuera de un ciclo de eventos: no puede dejar desactualizado el
> `version_puertas` de la partida real. Es la restauración de una foto, no una escritura de juego.

El método único no se usa en la copia porque incrementaría el `version_puertas` del clon sin que haya pasado nada y
registraría deshacer que nadie usará. La exclusión es por nombre de archivo: cualquier otro archivo nuevo de `Modelo/`
que escriba `cerrada` sigue haciendo fallar la prueba.

## Qué comprueba cada requisito

| Requisito | Prueba |
|-----------|--------|
| §1 y §2 | Escenario 14 de 004 y T059: el clon con cazadores activos decide igual que la partida jugada |
| §3 | T058 y T059; el sello `(reloj, secuencia)` de la línea |
| §4 | T058 (a), (b) y (c) y T059 |
| §5 | T015, con la exclusión escrita en la prueba |
