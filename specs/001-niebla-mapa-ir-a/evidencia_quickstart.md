# Evidencia del quickstart (T116)

**Fecha**: 2026-11-16 · **Equipo**: `Windows-11-10.0.26200-SP0`, Python 3.12.10 · **Guía**: [quickstart.md](quickstart.md) ·
**Matriz**: [trazabilidad.md](trazabilidad.md)

Recorrido de los escenarios 1 a 8 con `python main.py` real y entradas guionadas por stdin (una orden por línea), sin
red.

**Cómo se corrió**

- Cada partida corrió en su propia carpeta temporal, fuera del repositorio. Ahí quedaron la caché (`--datos-locales`),
  la bitácora (`--bitacora`, con nombre propio de evidencia) y los puntajes (`--puntajes`). No se creó ni se tocó
  `partida.log`, `partida.cripta`, `partida.cripta.log` ni `datos_locales/` en el repositorio. Aquí solo se copia la
  evidencia en texto.
- En los comandos, `<REPO>` es la raíz del repositorio y `<T116>` la carpeta temporal. Las salidas se recortan a lo
  relevante, sin reordenar ni cambiar nada; `[...]` marca un corte.
- **Paquetes**:
  - El escenario 1 usa el paquete del repositorio (`<REPO>/paquete`, cripta `cripta-test`), como dice el quickstart.
  - Para los demás hacía falta una cripta con puertas de cierre automático, antorcha, enemigos, trampas, llaves y
    pergaminos, y ninguna cripta offline del repositorio las tiene. Se generaron paquetes offline en `<T116>/paquetes`
    con `crear_paquete_niebla` de `tests/utiles_niebla.py`, usando los mismos mapas que las pruebas automáticas. Todos
    son la cripta `cripta-niebla` v1, sala inicial 1.

| Paquete | Mapa (de las pruebas) | Contenido |
|---------|-----------------------|-----------|
| `p_puerta` | `tests/test_conocimiento.py::mapa(cerrada=True, cierre=300)`: 1 -E-> 2 cerrada, se cierra sola 300 después de abrirla | antorcha y pergamino en 1 |
| `p_antorcha` | `tests/test_antorcha.py::mapa()`: 2 -N-> 3 cerrada | antorcha y pergamino en 1; rata dormida y trampa armada en 3 |
| `p_cuadro` | `tests/test_conocimiento.py::mapa()`: cuadro 1-2-4-3, todas las salidas cuestan 100 | pergamino en 1 |
| `p_llave` | `tests/test_viaje.py::mapa_llave()`: 1 -E-> 2 cerrada con `itm_llave`, 3 -E-> 2 cerrada | antorcha y llave en 1 |
| `p_enemigos` | `tests/test_viaje.py::mapa_pasillo()`: 1 - 2 - 3 - 4 | antorcha en 1; babosa dormida en 3 |
| `p_trampa` | `tests/test_viaje.py::mapa_pasillo()` | trampa armada en 2 |

`p_llave`, `p_enemigos` y `p_trampa` tienen la salida inalcanzable a propósito, así que la partida nueva usa
`--forzar` (spec 002, FR-021), igual que sus pruebas.

## Resumen

| Escenario | ¿Se corrió solo? | Veredicto |
|-----------|------------------|-----------|
| [1. Niebla al empezar y al moverse](#esc-1) | sí | cumple |
| [2. Puerta recordada](#esc-2) | sí | cumple |
| [3. Antorcha](#esc-3) | sí | cumple |
| [4. «ir a»](#esc-4) | sí, 8 de los 9 casos de la tabla | cumple en los 8 casos corridos; el caso «veneno activo» es un **límite conocido (no se puede producir jugando)** ([4.9](#esc-4-veneno)) |
| [5. Reproducción](#esc-5) | sí | cumple en reloj, posición, vida y acciones; el conocimiento final no se ve en la salida de `--replay` |
| [6. Guardar, cargar y reproducir](#esc-6) | sí | cumple; azar y `secuencia` no se ven por consola |
| [7. Versiones viejas](#esc-7) | sí | cumple |
| [8. Mediciones](#esc-8) | sí | cumple (en esta corrida M4 solo tenía filas sintéticas, PROVISIONAL; §6.1 lo resolvió después T110: cumple) |

**Suite completa**: `python -m unittest discover -s tests -t .` → `Ran 812 tests in 16.842s`, `OK`.

<a id="esc-1"></a>
## 1. Niebla al empezar y al moverse (FR-001 a FR-005)

```bash
cd <T116>/esc1
python <REPO>/main.py --offline <REPO>/paquete --cripta cripta-test --semilla 7 --datos-locales <T116>/esc1/cache --bitacora <T116>/esc1/esc1.log --puntajes <T116>/esc1/puntajes.txt
```

Entrada: `mapa`, `e`, `mapa`, `salir`. Salida, código `0`:

```text
--- Sala 1: Entrada ---   reloj 0
Vida 40/40   acciones 0   derrotados 0
[...]
> Mapa conocido:
  Sala 1: Entrada
    E -> sala 2   costo 100   abierta
Avistadas: 2

--- Sala 1: Entrada ---   reloj 0
Vida 40/40   acciones 0   derrotados 0
[...]
> 
--- Sala 2: Pasillo ---   reloj 100
Vida 33/40   acciones 1   derrotados 0
[...]
> Mapa conocido:
  Sala 1: Entrada
    E -> sala 2   costo 100   abierta
  Sala 2: Pasillo
    O -> sala 1   costo 100   abierta
    E -> sala 3   costo 100   abierta
    S -> sala 5   costo 100   abierta
Avistadas: 3, 5
```

Bitácora `esc1.log`, después del separador: una sola línea, `mover E`.

**Veredicto: cumple.**

- Al inicio solo la sala 1 está explorada y la 2 avistada; después, 1 y 2 exploradas y 3 y 5 avistadas.
- La sala 4 no aparece.
- `mapa` no cambia el reloj (0 antes y después) y no aparece en la bitácora.

Respaldo automático:

- `tests/test_conocimiento.py::test_fr001_fr002_fr004_sala_inicial_en_el_instante_0`
- `tests/test_conocimiento.py::test_fr003_fr004_fr005_de_avistada_a_explorada`
- `tests/test_mapa.py::test_fr019_mapa_no_se_anota_en_la_bitacora`

<a id="esc-2"></a>
## 2. Puerta recordada (FR-006, FR-007, FR-008)

```bash
cd <T116>/esc2
python <REPO>/main.py --offline <T116>/paquetes/p_puerta --cripta cripta-niebla --semilla 7 --bitacora esc2.log --datos-locales <T116>/esc2/cache --puntajes <T116>/esc2/puntajes.txt
```

Entrada: `abrir e`, `s`, `e`, `esperar`, `mapa`, `n`, `mapa`, `salir`. La puerta 1 -E-> 2 se abre y se cierra sola 300
después; el jugador se aleja por 3 y 4 y vuelve entrando a 2. Salida, código `0`:

```text
--- Sala 1: Entrada ---   reloj 50
Vida 40/40   acciones 1   derrotados 0
Salidas: E este (abierta) | S sur (abierta)
[...]
--- Sala 4: Cruce ---   reloj 350
Vida 40/40   acciones 4   derrotados 0
Salidas: O oeste (abierta) | N norte (abierta) | S sur (abierta)
Inventario: vacío
> Mapa conocido:
  Sala 1: Entrada
    E -> sala 2   costo 100   abierta
    S -> sala 3   costo 100   abierta
[...]
--- Sala 2: Pasillo ---   reloj 450
Vida 40/40   acciones 5   derrotados 0
Salidas: O oeste (abierta) | S sur (abierta)
Inventario: vacío
> Mapa conocido:
  Sala 1: Entrada
    E -> sala 2   costo 100   cerrada
    S -> sala 3   costo 100   abierta
```

**Veredicto: cumple.**

- Lejos de la puerta, `mapa` la muestra abierta.
- «Una puerta se cerró sola.» no aparece en ninguna parte de la salida.
- Al entrar a la sala 2, que es una de sus dos salas, pasa a cerrada.

Respaldo automático:

- `tests/test_conocimiento.py::test_fr007_fr012_cierre_no_observado_conserva_el_recuerdo`
- `tests/test_conocimiento.py::test_fr006_al_entrar_al_destino_el_recuerdo_queda_cerrado`
- `tests/test_conocimiento.py::test_fr008_abrir_se_refleja_de_inmediato`

<a id="esc-3"></a>
## 3. Antorcha (FR-009, FR-010, FR-011, FR-014)

```bash
cd <T116>/esc3
python <REPO>/main.py --offline <T116>/paquetes/p_antorcha --cripta cripta-niebla --semilla 7 --bitacora esc3.log --datos-locales <T116>/esc3/cache --puntajes <T116>/esc3/puntajes.txt
```

Entrada:

```text
recoger obj-cripta-niebla-1-itm_antorcha-0
recoger obj-cripta-niebla-1-itm_pergamino-1
usar obj-cripta-niebla-1-itm_antorcha-0
mapa
e
mapa
retroceder
mapa
salir
```

Salida, código `0`:

```text
--- Sala 1: Entrada ---   reloj 100
Vida 40/40   acciones 3   derrotados 0
Salidas: E este (abierta)
Inventario: Pergamino [obj-cripta-niebla-1-itm_pergamino-1]
> Mapa conocido:
  Sala 1: Entrada
    E -> sala 2   costo 100   abierta
Avistadas: 2
[...]
--- Sala 2: B ---   reloj 200
Vida 40/40   acciones 4   derrotados 0
Salidas: O oeste (abierta) | N norte (cerrada) | S sur (abierta)
Inventario: Pergamino [obj-cripta-niebla-1-itm_pergamino-1]
> Mapa conocido:
  Sala 1: Entrada
    E -> sala 2   costo 100   abierta
  Sala 2: B
    O -> sala 1   costo 100   abierta
    N -> sala 3   costo 100   cerrada
    S -> sala 5   costo 100   abierta
  Sala 3: C
    S -> sala 2   costo 100   abierta
    E -> sala 4   costo 100   sin observar
  Sala 5: Rodeo
    N -> sala 2   costo 100   abierta
    E -> sala 4   costo 100   sin observar
Avistadas: 4
[...]
--- Sala 1: Entrada ---   reloj 100
Vida 40/40   acciones 3   derrotados 0
Salidas: E este (abierta)
Inventario: vacío
> Mapa conocido:
  Sala 1: Entrada
    E -> sala 2   costo 100   abierta
Avistadas: 2
```

**Veredicto: cumple.**

- La sala 3 queda explorada a través de la puerta cerrada, sin mostrar su contenido: ni la rata ni la trampa aparecen
  en la salida.
- La vida no cambia (40/40).
- Las salidas que el jugador no observó figuran `sin observar`.
- `retroceder` deja el mapa idéntico al de antes de entrar, y el pergamino se consume.
- Que la rata siga dormida no se ve por consola, pero no hubo ningún ataque. Lo comprueba la prueba automática.

Respaldo automático:

- `tests/test_antorcha.py::test_fr009_fr010_explora_sin_activar_enemigos_ni_trampas`
- `tests/test_antorcha.py::test_fr006_fr011_las_puertas_de_una_vecina_quedan_sin_observar`
- `tests/test_antorcha.py::test_fr014_pergamino_restaura_exactamente_el_conocimiento`

<a id="esc-4"></a>
## 4. «ir a» (FR-021 a FR-031)

Cada caso de la tabla del quickstart se corrió en una partida propia. Los comandos tienen la misma forma que en el
escenario 3, con el paquete indicado, `--bitacora esc4X.log` y, donde se indica, `--forzar`.

<a id="esc-4-rechazos"></a>
### 4.1 a 4.3: rechazos, empate y `retroceder` tras el viaje (paquete `p_cuadro`)

```bash
python <REPO>/main.py --offline <T116>/paquetes/p_cuadro --cripta cripta-niebla --semilla 7 --bitacora esc4a.log --datos-locales <T116>/esc4a/cache --puntajes <T116>/esc4a/puntajes.txt
```

Entrada:

```text
ir a 2
ir a 5
ir a 99
ir a 1
recoger obj-cripta-niebla-1-itm_pergamino-0
e
s
o
n
ir a 4
retroceder
mapa
salir
```

Salida, código `0`:

```text
--- Sala 1: Entrada ---   reloj 0
Vida 40/40   acciones 0   derrotados 0
Salidas: E este (abierta) | S sur (abierta)
[...]
> * No conoces esa sala.

--- Sala 1: Entrada ---   reloj 0
Vida 40/40   acciones 0   derrotados 0
[...]
> * No conoces esa sala.

--- Sala 1: Entrada ---   reloj 0
Vida 40/40   acciones 0   derrotados 0
[...]
> * No conoces esa sala.

--- Sala 1: Entrada ---   reloj 0
Vida 40/40   acciones 0   derrotados 0
[...]
> * Ya estás en esa sala.
[...]
--- Sala 1: Entrada ---   reloj 425
Vida 40/40   acciones 5   derrotados 0
Salidas: E este (abierta) | S sur (abierta)
> * Llegaste a la sala 4.

--- Sala 4: Cruce ---   reloj 625
Vida 40/40   acciones 7   derrotados 0
Salidas: O oeste (abierta) | N norte (abierta) | S sur (abierta)
> 
--- Sala 2: Pasillo ---   reloj 525
Vida 40/40   acciones 6   derrotados 0
Salidas: O oeste (abierta) | S sur (abierta)
```

Bitácora `esc4a.log`, después del separador:

```text
recoger obj-cripta-niebla-1-itm_pergamino-0
mover E
mover S
mover O
mover N
# ir a 4
mover E
mover S
retroceder
```

**Veredicto: cumple** en estos cuatro casos:

| Caso del quickstart | Qué se vio |
|---------------------|------------|
| Sala avistada, desconocida o inexistente | `ir a 2` (avistada), `ir a 5` (desconocida) e `ir a 99` (inexistente) dan el mismo aviso, «No conoces esa sala.». El reloj y las acciones siguen en 0, y la bitácora no tiene ninguna línea por ellas (SC-005) |
| Sala actual | `ir a 1` da su propio aviso, «Ya estás en esa sala.», sin cambios |
| Dos rutas de igual costo | De 1 a 4 hay dos rutas de 200; el primer paso es `mover E`, hacia la sala 2, la vecina de menor id |
| `retroceder` tras el viaje | Deshace solo el último paso: el jugador vuelve de 4 a 2 (reloj 625 → 525, acciones 7 → 6) y el viaje no sigue. La bitácora tiene `# ir a 4` antes del primer `mover` |

Respaldo automático:

- `tests/test_viaje.py::test_fr022_sc005_escenario_us4_1_sala_avistada_desconocida_inexistente_o_no_valida`
- `tests/test_viaje.py::test_fr022_sala_actual`
- `tests/test_viaje.py::test_fr024_escenario_us4_5_empate_va_a_la_vecina_de_menor_id_con_busqueda_real`
- `tests/test_viaje.py::test_fr014_fr031_escenario_us4_4_tras_viaje_completo_deshace_solo_el_ultimo_paso`

<a id="esc-4-puerta"></a>
### 4.4 Puerta recordada abierta, real cerrada (paquete `p_puerta`)

Entrada: `abrir e`, `e`, `s`, `o`, `esperar`, `mapa`, `ir a 2`, `mapa`, `salir`. Al dar la orden, el jugador está en
la sala 3; la puerta 1 -E-> 2 ya se cerró, pero la recuerda abierta. Salida, código `0`:

```text
--- Sala 3: Bodega ---   reloj 450
Vida 40/40   acciones 5   derrotados 0
Salidas: N norte (abierta) | E este (abierta)
> Mapa conocido:
  Sala 1: Entrada
    E -> sala 2   costo 100   abierta
[...]
> * Llegaste a la sala 2.

--- Sala 2: Pasillo ---   reloj 850
Vida 40/40   acciones 9   derrotados 0
Salidas: O oeste (abierta) | S sur (abierta)
> Mapa conocido:
  Sala 1: Entrada
    E -> sala 2   costo 100   cerrada
```

Bitácora `esc4b.log`, después del separador: `abrir E`, `mover E`, `mover S`, `mover O`, `esperar`, `# ir a 2`,
`mover N`, `mover S`, `mover E`, `mover N`.

**Veredicto: cumple.**

- El primer paso va a la sala 1: empatan 3→1→2 y 3→4→2, ambas de 200, y gana la vecina de menor id.
- En la sala 1 el jugador ve la puerta cerrada y el viaje recalcula: sigue por 1→3→4→2 y llega.

Respaldo automático: `tests/test_viaje.py::test_fr026_con_otra_ruta_el_viaje_sigue_por_ella`.

<a id="esc-4-llave"></a>
### 4.5 Puerta cerrada con la llave en el inventario (paquete `p_llave`, `--forzar`)

Entrada:

```text
recoger obj-cripta-niebla-1-itm_antorcha-0
recoger obj-cripta-niebla-1-itm_llave-1
usar obj-cripta-niebla-1-itm_antorcha-0
s
n
mapa
ir a 2
salir
```

Salida, código `0`:

```text
--- Sala 1: A ---   reloj 300
Vida 40/40   acciones 5   derrotados 0
Salidas: E este (cerrada, llave itm_llave) | S sur (abierta)
> Mapa conocido:
  Sala 1: A
    E -> sala 2   costo 100   cerrada
    S -> sala 3   costo 100   abierta
  Sala 2: B
    O -> sala 1   costo 100   abierta
  Sala 3: C
    N -> sala 1   costo 100   abierta
    E -> sala 2   costo 100   cerrada
Avistadas: ninguna
[...]
> * No conoces una ruta hasta esa sala.

--- Sala 1: A ---   reloj 300
Vida 40/40   acciones 5   derrotados 0
```

**Veredicto: cumple.**

- Con la llave recogida, el viaje no abre la puerta 1 -E-> 2: esa salida no cuenta.
- Como no hay otra ruta, la orden se rechaza con su propio aviso, sin gastar tiempo (reloj 300 y acciones 5, igual
  que antes).
- Esto cubre también el caso «sin ruta conocida» de la tabla.

Respaldo automático:

- `tests/test_viaje.py::test_fr023_fr029_escenario_us4_8_puerta_cerrada_con_llave_no_cuenta`
- `tests/test_viaje.py::test_fr022_explorada_sin_ruta`

<a id="esc-4-sin-observar"></a>
### 4.6 Salida `sin observar` (paquete `p_antorcha`)

Entrada:

```text
recoger obj-cripta-niebla-1-itm_antorcha-0
usar obj-cripta-niebla-1-itm_antorcha-0
e
s
mapa
ir a 3
salir
```

Salida, código `0`:

```text
--- Sala 5: Rodeo ---   reloj 275
Vida 40/40   acciones 4   derrotados 0
Salidas: N norte (abierta) | E este (abierta)
> Mapa conocido:
[...]
  Sala 3: C
    S -> sala 2   costo 100   abierta
    E -> sala 4   costo 100   sin observar
  Sala 4: D
    O -> sala 3   costo 100   sin observar
    S -> sala 5   costo 100   abierta
    E -> sala 6   costo 100   sin observar
  Sala 5: Rodeo
    N -> sala 2   costo 100   abierta
    E -> sala 4   costo 100   abierta
Avistadas: 6
[...]
> * No conoces una ruta hasta esa sala.
```

**Veredicto: cumple.**

- Las salas 3 y 4 están exploradas por la antorcha.
- En el mapa real, 5→4→3 está abierta, pero 4 -O-> 3 figura `sin observar`.
- La otra ruta, 2 -N-> 3, está recordada cerrada.
- `ir a 3` se rechaza: la salida sin observar no se usa.

Respaldo automático:

- `tests/test_viaje.py::test_fr011_una_salida_sin_observar_no_existe_para_la_busqueda`
- `tests/test_viaje.py::test_fr011_fr023_sc002_escenario_us2_4_ir_a_no_usa_salidas_sin_observar`

<a id="esc-4-enemigos"></a>
### 4.7 Sala con enemigos en la ruta (paquete `p_enemigos`, `--forzar`)

Entrada:

```text
recoger obj-cripta-niebla-1-itm_antorcha-0
usar obj-cripta-niebla-1-itm_antorcha-0
e
o
ir a 3
salir
```

Salida, código `0`:

```text
--- Sala 1: A ---   reloj 275
Vida 40/40   acciones 4   derrotados 0
Salidas: E este (abierta)
> * Viaje detenido: hay enemigos en la sala.

--- Sala 3: C ---   reloj 475
Vida 40/40   acciones 6   derrotados 0
Salidas: O oeste (abierta) | E este (abierta)
Enemigos: e-babosa (ent_babosa, vida 8)
```

Bitácora `esc4e.log`, después del separador: `recoger ...`, `usar ...`, `mover E`, `mover O`, `# ir a 3`, `mover E`,
`mover E`.

**Veredicto: cumple.**

- La antorcha exploró la sala 3 sin activar a la babosa.
- El viaje entra a 3, donde la babosa se activa, y se detiene ahí con el motivo.

Respaldo automático: `tests/test_viaje.py::test_fr027b_escenario_us4_3_enemigo_dormido_se_activa_y_detiene`.

<a id="esc-4-dano"></a>
### 4.8 Daño durante el viaje, por una trampa (paquete `p_trampa`, `--forzar`)

Este caso no está en la tabla del quickstart. Se corrió como evidencia jugada de la parada por daño (FR-027c), porque
el caso del veneno no se puede producir jugando ([4.9](#esc-4-veneno)).

Entrada: `e`, `e`, `e`, `esperar`, `esperar`, `ir a 1`, `salir`. Salida, código `0`:

```text
--- Sala 4: D ---   reloj 500
Vida 37/40   acciones 5   derrotados 0
Salidas: O oeste (abierta)
[...]
> * Viaje detenido: recibiste daño.

--- Sala 2: B ---   reloj 700
Vida 34/40   acciones 7   derrotados 0
```

Bitácora `esc4f.log`, después del separador: `mover E`, `mover E`, `mover E`, `esperar`, `esperar`, `# ir a 1`,
`mover O`, `mover O`.

**Veredicto: cumple FR-027c.** La trampa ya rearmada en la sala 2 hace daño (vida 37 → 34) y el viaje se detiene al
terminar ese paso.

Respaldo automático: `tests/test_viaje.py::test_fr027c_trampa_rearmada_en_la_ruta`.

<a id="esc-4-veneno"></a>
### 4.9 Veneno activo: **límite conocido (no se puede producir jugando)**

No se corrió. Ningún dato de cripta ni ninguna acción del juego aplica veneno: `MotorSimulacion.aplicar_veneno` solo
se llama desde las pruebas, y ninguna cripta offline del repositorio envenena. Por eso este caso no se puede producir
hoy jugando y no se simuló. Queda como límite conocido ([DECISIONES.md, «Veneno no jugable»](../../DECISIONES.md#veneno-no-jugable-límite-conocido)); Persona B confirmó el 2026-11-17 que el API no manda ningún dato de veneno (ni en enemigos, ni en objetos, ni en trampas).

Respaldo automático: `tests/test_viaje.py::test_fr027c_escenario_us4_6_veneno_activo_desde_antes_de_la_orden`
(aplica el veneno directamente al motor).

**Pasos para Lucía**, cuando exista una cripta con una fuente de veneno (un enemigo o una trampa que envenene):

1. Empezar la partida y explorar al menos dos salas en línea a partir de la sala donde se recibe el veneno, de modo
   que haya una ruta conocida de dos pasos o más.
2. Recibir el veneno y, mientras sigue activo, dar `ir a <sala>` hacia una sala explorada a dos pasos o más.
3. **Qué debe ver**: «Viaje detenido: recibiste daño.» al terminar el primer paso en que el veneno baja la vida, con
   la vida menor que antes de la orden y una sola línea `mover` en la bitácora después de `# ir a <sala>` (si el daño
   llega en el primer paso).

<a id="esc-5"></a>
## 5. Reproducción (FR-017, FR-030, SC-004)

Replay de las bitácoras de 4.1 a 4.3, 4.4 y 4.7, cada uno con el paquete de su partida y una caché propia.

```bash
python <REPO>/main.py --offline <T116>/paquetes/p_cuadro --replay <T116>/esc4a/esc4a.log --datos-locales <T116>/esc5_a/cache --puntajes <T116>/esc5_a/puntajes.txt
python <REPO>/main.py --offline <T116>/paquetes/p_puerta --replay <T116>/esc4b/esc4b.log --datos-locales <T116>/esc5_b/cache --puntajes <T116>/esc5_b/puntajes.txt
python <REPO>/main.py --offline <T116>/paquetes/p_enemigos --replay <T116>/esc4e/esc4e.log --datos-locales <T116>/esc5_e/cache --puntajes <T116>/esc5_e/puntajes.txt
```

Salidas, código `0` en los tres:

```text
Reproducción finalizada.
Reloj: 525  Sala: 2  Vida: 40
Resumen: {'resultado': 'en_curso', 'acciones': 6, 'enemigos_derrotados': 0, 'tiempo_final': 525}
```

```text
Reproducción finalizada.
Reloj: 850  Sala: 2  Vida: 40
Resumen: {'resultado': 'en_curso', 'acciones': 9, 'enemigos_derrotados': 0, 'tiempo_final': 850}
```

```text
Reproducción finalizada.
Reloj: 475  Sala: 3  Vida: 40
Resumen: {'resultado': 'en_curso', 'acciones': 6, 'enemigos_derrotados': 0, 'tiempo_final': 475}
```

**Veredicto: cumple en lo que se ve por consola.**

- Reloj, sala, vida y acciones coinciden con el final de cada partida: 525 / 2 / 6, 850 / 2 / 9 y 475 / 3 / 6.
- La salida no tiene las pantallas de `VistaConsola`.
- El conocimiento final no aparece en la salida de `--replay`, así que por consola no se puede comparar. Lo comparan
  las pruebas automáticas, campo por campo.

Respaldo automático:

- `tests/test_persistencia_conocimiento.py::test_fr017_fr030_fr031_ir_a_y_pergaminos_sin_y_con_carga` (compara reloj,
  jugador y conocimiento)
- `tests/test_viaje.py::test_fr030_sc004_viaje_completo_deja_comentario_antes_del_primer_mover_y_se_reproduce`
- `tests/test_integracion.py::test_fr017_pr14_replay_termina_con_codigo_0_sin_vista`

<a id="esc-6"></a>
## 6. Guardar, cargar y reproducir (FR-015 a FR-017, SC-003)

Paquete `p_puerta`, con la antorcha encendida al guardar y la puerta 1 -E-> 2 recordada abierta mientras en realidad
está cerrada.

```bash
cd <T116>/esc6
python <REPO>/main.py --offline <T116>/paquetes/p_puerta --cripta cripta-niebla --semilla 7 --bitacora esc6.log --datos-locales <T116>/esc6/cache --puntajes <T116>/esc6/puntajes.txt
python <REPO>/main.py --offline <T116>/paquetes/p_puerta --cargar ev6.cripta --bitacora esc6_cont.log --datos-locales <T116>/esc6/cache --puntajes <T116>/esc6/puntajes.txt
python <REPO>/main.py --offline <T116>/paquetes/p_puerta --replay esc6_cont.log --datos-locales <T116>/esc6/cache --puntajes <T116>/esc6/puntajes.txt
```

**Entradas**

- Sesión 1:

  ```text
  recoger obj-cripta-niebla-1-itm_antorcha-0
  usar obj-cripta-niebla-1-itm_antorcha-0
  abrir e
  e
  s
  o
  esperar
  mapa
  guardar ev6.cripta
  salir
  ```

- Sesión 2: `mapa`, `esperar`, `e`, `s`, `mapa`, `salir`. Además de lo que pide el quickstart (`mapa`, `esperar`,
  `salir`), se agregaron `e` y `s` para comprobar que la antorcha quedó apagada.

Sesión 1, código `0`:

```text
--- Sala 3: Bodega ---   reloj 525
Vida 40/40   acciones 7   derrotados 0
Salidas: N norte (abierta) | E este (abierta)
Inventario: vacío
> Mapa conocido:
  Sala 1: Entrada
    E -> sala 2   costo 100   abierta
    S -> sala 3   costo 100   abierta
  Sala 2: Pasillo
    O -> sala 1   costo 100   abierta
    S -> sala 4   costo 100   abierta
  Sala 3: Bodega
    N -> sala 1   costo 100   abierta
    E -> sala 4   costo 100   abierta
  Sala 4: Cruce
    O -> sala 3   costo 100   abierta
    N -> sala 2   costo 100   abierta
    S -> sala 5   costo 100   abierta
  Sala 5: Sótano
    N -> sala 4   costo 100   abierta
    E -> sala 6   costo 100   sin observar
Avistadas: 6
[...]
> * Partida guardada en ev6.cripta
```

Sesión 2, código `0`:

```text
* Partida cargada desde ev6.cripta
[...]
--- Sala 3: Bodega ---   reloj 525
Vida 40/40   acciones 7   derrotados 0
Salidas: N norte (abierta) | E este (abierta)
Inventario: vacío
> Mapa conocido:
  Sala 1: Entrada
    E -> sala 2   costo 100   abierta
    S -> sala 3   costo 100   abierta
  Sala 2: Pasillo
    O -> sala 1   costo 100   abierta
    S -> sala 4   costo 100   abierta
  Sala 3: Bodega
    N -> sala 1   costo 100   abierta
    E -> sala 4   costo 100   abierta
  Sala 4: Cruce
    O -> sala 3   costo 100   abierta
    N -> sala 2   costo 100   abierta
    S -> sala 5   costo 100   abierta
  Sala 5: Sótano
    N -> sala 4   costo 100   abierta
    E -> sala 6   costo 100   sin observar
Avistadas: 6
[...]
--- Sala 5: Sótano ---   reloj 825
Vida 40/40   acciones 10   derrotados 0
Salidas: N norte (abierta) | E este (abierta)
Inventario: vacío
> Mapa conocido:
[...]
  Sala 5: Sótano
    N -> sala 4   costo 100   abierta
    E -> sala 6   costo 100   abierta
Avistadas: 6
```

Bitácora continuada `esc6_cont.log`, después del separador:

```text
recoger obj-cripta-niebla-1-itm_antorcha-0
usar obj-cripta-niebla-1-itm_antorcha-0
abrir E
mover E
mover S
mover O
esperar
@cargar
esperar
mover E
mover S
```

Replay, código `0`:

```text
Reproducción finalizada.
Reloj: 825  Sala: 5  Vida: 40
Resumen: {'resultado': 'en_curso', 'acciones': 10, 'enemigos_derrotados': 0, 'tiempo_final': 825}
```

**Comprobación de la puerta real.** Otra carga del mismo `ev6.cripta`, con `--bitacora esc6_verif.log` y la entrada
`n`, `mapa`, `salir`:

```text
--- Sala 1: Entrada ---   reloj 625
Vida 40/40   acciones 8   derrotados 0
Salidas: E este (cerrada) | S sur (abierta)
[...]
Mapa conocido:
  Sala 1: Entrada
    E -> sala 2   costo 100   cerrada
```

**Veredicto: cumple.**

- `mapa` es idéntico antes de guardar y después de cargar.
- El mapa incluye la puerta recordada abierta que en realidad estaba cerrada (lo confirma la carga aparte, al entrar
  a 1) y la sala 5, explorada por la antorcha.
- La antorcha queda apagada tras la carga: al entrar a 5, la sala 6 sigue avistada, mientras que con la antorcha
  encendida la sesión 1 exploró 5 desde 4.
- La bitácora continuada contiene `@cargar`.
- El replay coincide en reloj, sala, vida y acciones (825 / 5 / 40 / 10).
- El azar y la `secuencia` no se ven por consola. Los comparan las pruebas automáticas, a través del resumen del
  motor.

Repetido el 2026-11-17 con el main.py posterior a los cambios de la spec 004 (cargar con línea de tiempo): mismo resultado en todos los puntos, con el paquete offline presente.

Respaldo automático:

- `tests/test_persistencia_conocimiento.py::test_fr015_sc003_escenario_us5_1_el_mapa_conocido_es_identico`
- `tests/test_persistencia_conocimiento.py::test_fr017_sc004_escenario_us5_2_guardar_cargar_continuar_y_reproducir`
- `tests/test_persistencia_conocimiento.py::test_fr015_pr06_antorcha_conserva_lo_ganado_queda_apagada_y_no_reobserva`

<a id="esc-7"></a>
## 7. Versiones viejas (FR-016, FR-030)

**Archivos de versión vieja**, preparados en `<T116>/esc7`:

- `archivo_v2.cripta`: copia de `ev6.cripta` (un `CRPT` 3 válido) con el campo de versión del encabezado (bytes 4 y 5,
  `<H`) cambiado de 3 a 2.
- `bitacora_v1.log`: copia de `esc6.log` con la primera línea cambiada de `CRIPTA-LOG 2` a `CRIPTA-LOG 1`.

```bash
cd <T116>/esc7
python <REPO>/main.py --offline <T116>/paquetes/p_puerta --cargar archivo_v2.cripta --bitacora esc7_cont.log --datos-locales <T116>/esc7/cache --puntajes <T116>/esc7/puntajes.txt
python <REPO>/main.py --offline <T116>/paquetes/p_puerta --replay bitacora_v1.log --datos-locales <T116>/esc7/cache --puntajes <T116>/esc7/puntajes.txt
```

```text
! Error: Versión incompatible: El archivo usa el formato 2 y este programa usa el 3
```

Código `2`.

```text
! Error: Versión incompatible: La bitacora usa el formato 1 y este programa usa el 2
```

Código `2`.

**Veredicto: cumple.** Las dos dan `! Error: Versión incompatible: ...` y código `2`. Nada se cargó: no se creó
`esc7_cont.log`, y la carga no llegó a pedir órdenes (la entrada `mapa`, `salir` no se usó).

Respaldo automático:

- `tests/test_persistencia_conocimiento.py::test_fr016_version_2`
- `tests/test_bitacora.py::test_fr030_cripta_log_1_da_codigo_2_en_el_replay`

<a id="esc-8"></a>
## 8. Mediciones (Principio VIII)

```bash
cd <T116>/esc8
python <REPO>/main.py --bench
```

Código `0`, 170 s. Se generaron `resultados_bench_ciclo.txt`, `resultados_bench_guardado.txt`,
`resultados_bench_niebla.txt` y `resultados_bench_resolubilidad.txt` en `<T116>/esc8`.

`resultados_bench_niebla.txt` tiene el encabezado con equipo y versión de Python y 113 filas: M1 24, M2 8, M3 27, M4 32,
M5 12 y M6 10. Filas de un paso de M4 por llamada:

```text
M4 grilla/paso      V=400 pasos=1 espacio=por llamada     1.0753 ms   PROVISIONAL cumple
M4 grilla/paso      V=2500 pasos=1 espacio=por llamada    12.0241 ms   PROVISIONAL no cumple
M4 cadena/paso      V=2500 pasos=1 espacio=por llamada     2.7580 ms   PROVISIONAL cumple
```

**Veredicto: cumple lo que pide el quickstart.** Se genera `resultados_bench_niebla.txt` con M1 a M6, sin red y sin
las pantallas de la vista.

- Este archivo de la corrida de T116 **no** reemplaza al `resultados_bench_niebla.txt` del repositorio, que es el de
  la medición de T110 (commits `70ecfdc` y `c29aebd`, hoy sobre `cripta-06`) y el que citan DECISIONES.md §5.3 y la
  matriz.
- En esta corrida M4 solo tenía filas sintéticas, PROVISIONAL: la grilla de 2500 no cumple, como en T109. §6.1 quedó
  para T110, que después lo dio por cumplido sobre la cripta sustituta: primero `cripta-02` y ahora `cripta-06`
  ([DECISIONES.md, §5.3](../../DECISIONES.md)).

Respaldo automático:

- `tests/test_bench_niebla.py::test_sc006_pr15_t108_m1_a_m6_con_tamanos_minimos_sin_red_ni_vista`
- `tests/test_bench_niebla.py::test_pr15_t107_main_bench_llama_a_la_medicion_de_niebla_sin_red_ni_vista`
