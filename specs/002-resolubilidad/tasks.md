---

description: "Lista de tareas de la verificación de resolubilidad de una cripta (spec 002)"
---

# Tasks: Verificación de resolubilidad de una cripta

**Input**: Documentos de diseño de `specs/002-resolubilidad/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md),
[contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: se piden. El Principio V exige una prueba automatizada por escenario de aceptación, sin red y solo con
`unittest`. **Cada prueba cita en su nombre o docstring el `FR-xxx` que verifica** (por ejemplo
`test_fr007_oleadas_desempate_por_id`).

**Organization**: tareas agrupadas por historia de usuario. Cada tarea indica al final los requisitos que atiende
(`Atiende: FR-xxx`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia de usuario de la tarea (US1 a US5)

## Reglas que valen para todas las tareas

- **Estructuras del recorrido de resolubilidad (Principio I, NO NEGOCIABLE)**: ninguna tarea puede usar `dict`, `set`,
  `heapq`, `deque`, `bisect`, `collections` ni bibliotecas de grafos (`networkx` u otras) en las estructuras del
  recorrido: índice de llaves, vector de salas, `entrantes`, marcas, `espera`, `sello`, `valor_zona`, `depende_de`,
  `marca`, `en_ciclo`, cola y listas del resultado. Tampoco `sorted()` ni `.sort()`: se usa `merge_sort` de
  `Modelo/ordenamiento.py`. `list` solo como arreglo indexado. La cola es `Queue` de `Modelo/Estructuras.py` (solo
  `enqueue`, `dequeue`, `is_empty`; `size()` no se usa). Recorrer el `dict` `sala.salidas` del DTO o parsear JSON es uso
  `merge_sort(items, key)` recibe una función clave y devuelve la tupla `(lista_ordenada, comparaciones)`; nunca se usa como si devolviera solo la lista.
  auxiliar permitido. La regla también vale para el oráculo de las pruebas y para las alternativas A1 a A3 del bench.
- **`main.py` es compartido**: antes de modificarlo, `git pull` y resolver conflictos con el resto del grupo.
- **Contratos compartidos** (avisar al grupo antes de cambiarlos): firma de `ControladorPartida.nueva_partida`,
  `GestorDatos.obtener_llaves`, formato del paquete offline, prioridad de opciones de `main.py`, README (UTF-16).
- **Ningún dato de cripta concreta en producción** (Principio IV): las criptas de prueba y de bench se generan en
  `tests/`.

---

## Phase 1: Setup (infraestructura compartida)

**Purpose**: línea base y generador de criptas sintéticas, que también necesita la spec 003 (su T003).

- [X] T001 `git pull` y ejecutar `python -m unittest discover -s tests -v` desde la raíz; anotar en las notas personales las pruebas que ya fallaban antes de empezar, para no confundirlas con las que romperá la falta de `llaves.json`. Atiende: FR-024, FR-028 (línea base)
- [X] T002 [P] Crear el generador de criptas sintéticas en `tests/generador_criptas.py`, determinista por semilla y con cadenas de llaves. Usar solo una instancia local `random.Random(semilla)` (nunca el `random` global). Debe ofrecer: (a) `generar_cripta(semilla, salas, llaves, resoluble=True, con_ciclo=False, llave_de_enemigo=False, costo_ida=1, costo_vuelta=1, id_cripta="sint")` que devuelve un objeto `CriptaSintetica` con `detalles` (`sala_inicial`, `sala_salida`, `llave_salida`, `presupuesto_solicitudes`), `salas_json` (lista en el formato de `GET /criptas/<id>/salas`) y `llaves_json` (lista en el formato de `GET /criptas/<id>/llaves`: `id`, `sala`, `enemigo` opcional); (b) métodos `esqueleto()` → `list[SalaEsqueleto]` y `ubicaciones()` → `list[UbicacionLlave]`; (c) cuadrícula de `salas` salas con ids enteros contiguos desde 1, salidas en N, S, E, O y unas 2,5 salidas por sala (300 salas → ≈ 760 salidas); salidas **dirigidas** (A→B y B→A con estado, llave y costo propios, costos configurables por sentido); (d) cadena de llaves: `k1` alcanzable desde `sala_inicial` sin abrir puertas, la región de `k(i+1)` detrás de puertas cerradas que piden `k(i)`, `llave_salida` = última de la cadena y una salida hacia `sala_salida` que la pide; (e) variante no resoluble (`resoluble=False`) con frontera bloqueada, al menos una puerta cerrada sin llave y, con `con_ciclo=True`, un ciclo directo (K detrás de una puerta que pide K) y uno por cadena (K1 ↔ K2); en la variante no resoluble, las zonas de las ubicaciones de llaves no obtenibles no se solapan (para que M3 mida el caso lineal de SC-005); (f) `llave_de_enemigo=True` ubica una llave con `enemigo` en la sala donde inicia; (g) `escribir_paquete(carpeta, cripta, escribir_llaves=True)` que escribe un paquete offline completo con el mismo esquema que `crear_paquete_niebla` de `tests/utiles_niebla.py` más `criptas/<id>/llaves.json`. Docstring con la interfaz, para que la persona de la spec 003 lo use en su T003 (lo que es solo de terreno, como colocar jugador y cazadores, queda en `tests/utiles_terreno.py`). Sin datos de criptas reales: 300/760/4 son parámetros. Atiende: FR-013, FR-029, FR-030 (SC-004, SC-005)
- [X] T003 [P] Crear `tests/test_generador_criptas.py`: misma semilla → `salas_json` y `llaves_json` idénticos (comparar `json.dumps(..., sort_keys=True)`); semillas distintas → criptas distintas; 300 salas → entre 700 y 820 salidas; en la variante resoluble, cada puerta de la región de `k(i+1)` pide `k(i)`; la variante no resoluble con `con_ciclo=True` contiene la puerta K→K; existe la salida hacia `sala_salida` con `llave_salida`; el estado del `random` global no cambia. Cada prueba cita FR-013 o FR-029. Atiende: FR-013, FR-029

---

## Phase 2: Foundational (prerrequisitos bloqueantes)

**Purpose**: resultado, lectura de llaves con validación y caché, presupuesto común y paquetes de prueba con `llaves.json`.

**⚠️ CRITICAL**: ninguna historia empieza antes de terminar esta fase. Sin T009 y T010, las pruebas existentes de partida nueva fallarán en cuanto US3 conecte la verificación.

- [X] T004 [P] Crear `DTOS/ResultadoVerificacion.py` con las clases de datos de [data-model.md §3](data-model.md), solo datos y sin lógica: `ResultadoVerificacion` (`cripta_id: str`, `resoluble: bool`, `sala_salida: int`, `llave_salida: str`, `orden`, `no_obtenibles`, `frontera`, `puertas_salida`, `existe_puerta_salida: bool`, `ubicaciones`, `dependencias`, `ciclos`; todas las listas ya ordenadas, «la vista no ordena nada»), `LlaveOrdenada(id_llave: str, oleada: int, es_salida: bool)`, `PuertaReporte(origen: int, direccion: str, destino: int, destino_existe: bool, llave: str | None)` («`None` = sin llave»), `UbicacionesLlave(id_llave: str, lugares: list[LugarLlave])` («vacía = ubicación desconocida»), `LugarLlave(sala: int, sala_existe: bool, enemigo: str | None)`, `DependenciaLlave(id_llave: str, depende_de: str | None)` («`None` = sin dependencia»), `CicloLlaves(llaves: list[str], directo: bool)` («empieza por la menor; no repite la primera al final»). Atiende: FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, FR-014
- [X] T005 [P] En `API/Fuentes.py`, método `obtener_llaves_cripta` (ya existe; el DTO `DTOS/UbicacionLlave.py` también y **no se modifica**): antes de llamar a `UbicacionLlave.desde_json`, rechazar cada entrada que no sea un objeto o a la que le falte `id` o `sala` con `Excepciones.RespuestaInvalidaError(ruta, "entrada de llave sin 'id' o 'sala'")`, en lugar del `KeyError` actual. Una `sala` que no existe en el esqueleto **no** es error de lectura. Atiende: FR-024, FR-025, FR-028
- [X] T006 [P] En `AlmacenamientoLocalApi/AlmacenamientoLocalApi.py`, agregar `guardar_llaves(id_cripta, version, ubicaciones)` y `cargar_llaves(id_cripta, version_esperada)` con el archivo `datos_locales/llaves_<id>.json` = `{"formato": "CRIPTA-LLAVES", "version_formato": 1, "version": "<versión de la cripta>", "llaves": [{"id": ..., "sala": ..., "enemigo": ... o null}]}` (Principio VI), con el mismo manejo que `guardar_esqueleto`/`cargar_esqueleto`; `cargar_llaves` devuelve `None` (y la caché se vuelve a pedir y reescribir) si el archivo falta o no se puede leer, si `formato` o `version_formato` no coinciden, o si la versión de la cripta no coincide. Las constantes de formato van en `AlmacenamientoLocalApi`, no son datos de cripta. Atiende: FR-013, FR-026, FR-028
- [X] T007 En `Gestor/GestorDatos.py`, agregar `obtener_llaves(id_cripta) -> list[UbicacionLlave]`: usa `cargar_llaves` con la versión actual de la cripta (`_version_de_cripta`); si no hay caché válida, llama a `fuente.obtener_llaves_cripta`, guarda con `guardar_llaves` y devuelve; memoriza en el gestor para no repetir la solicitud en el mismo proceso. Propaga sin capturar los errores de la fuente. Depende de T006. Atiende: FR-013, FR-026, FR-028
- [X] T008 En `Gestor/PreparadorPartida.py`, extraer de `_crear_motor` el paso de fijar el presupuesto de solicitudes con `detalles.presupuesto_solicitudes` a una función `_fijar_presupuesto(detalles, gestor)`, sin cambiar el comportamiento de `preparar_partida` ni de `cargar_partida`; la usarán `_crear_motor` y `verificar_cripta` (T022). Atiende: FR-026
- [X] T009 [P] En `tests/utiles_niebla.py`, `crear_paquete_niebla` escribe también `criptas/<CRIPTA_NIEBLA>/llaves.json` con `{"llaves": [...]}`. Parámetros nuevos: `llaves=None` (lista de dicts del formato del servicio; si es `None`, `[{"id": <llave_salida>, "sala": <sala_inicial>}]`, o `[]` si la cripta no declara `llave_salida`) y `escribir_llaves=True` (`False` deja el paquete sin el archivo, para US5.3). Buscar con `grep -rn "salas.json" tests/` cualquier otro generador de paquetes y aplicarle el mismo cambio. Atiende: FR-024, FR-028
- [X] T010 [P] En `tests/test_integracion.py`, `crear_paquete_offline` escribe también `criptas/<CRIPTA>/llaves.json` con la misma regla por defecto que T009 y un parámetro `escribir_llaves=True`. Atiende: FR-024, FR-028
- [X] T011 [P] Crear `tests/test_fuente_llaves.py`: entrada sin `id` → `RespuestaInvalidaError` con la ruta `/criptas/<id>/llaves` (FR-025); entrada sin `sala` → idem (FR-025); falta la clave `llaves` → `RespuestaInvalidaError` (FR-025); con `FuenteDatosOffline` y un paquete de T002/T009 se obtiene la misma lista que con una fuente HTTP simulada sobre el mismo cuerpo (FR-028); paquete sin `llaves.json` → `RuntimeError` con «Falta el archivo para /criptas/<id>/llaves» (FR-024); `GestorDatos.obtener_llaves` con caché válida no hace solicitudes y con versión distinta vuelve a pedir y reescribe (FR-013, FR-026); caché con `formato` o `version_formato` distintos → se descarta, vuelve a pedir y reescribe con el formato actual (FR-026, Principio VI); el resultado es el mismo con caché y sin ella (FR-013). Atiende: FR-013, FR-024, FR-025, FR-026, FR-028

**Checkpoint**: datos de llaves disponibles por la misma interfaz con red, offline y caché; paquetes de prueba con `llaves.json`.

---

## Phase 3: User Story 1 - Consultar si una cripta es resoluble (Priority: P1) 🎯 MVP

**Goal**: `--verificar <cripta>` informa si la cripta es resoluble y, si lo es, el orden de obtención por oleadas, sin iniciar partida.

**Independent Test**: con paquetes offline de prueba, una cripta resoluble y otra no, ejecutar `--verificar` y comprobar veredicto, orden, código 0 y que no se creó ni modificó ningún archivo de partida.

### Tests for User Story 1 ⚠️

> Escribirlas primero y comprobar que fallan antes de implementar.

- [X] T012 [US1] Crear `tests/test_resolubilidad.py` con las pruebas de estructuras: `IndiceLlaves` ordena con `merge_sort`, quita repetidos, `numero` devuelve la posición o −1, `id_de` y `cantidad`, e invariante `ids[i] < ids[i+1]` (FR-007, FR-014); `GrafoSalas.desde` deja las salidas en orden N, S, E, O con otras direcciones después por texto (FR-014), cada salida solo en su origen (FR-005), las llaves soltadas por un enemigo en la sala donde inicia (FR-003), ignora `cierre_automatico` y trampas (FR-004), marca `destino_valido = False` para destinos inexistentes, conserva la primera aparición de un id duplicado y lanza `ValueError` con un id no entero o negativo (FR-001, FR-025)
- [X] T013 [US1] En `tests/test_resolubilidad.py`, un caso por escenario de US1 llamando a `Resolubilidad.verificar(...)` con criptas pequeñas armadas en la prueba: US1.1 resoluble sin abrir puertas (FR-001, FR-006); US1.2 cadena A → B → salida en oleadas 1, 2, 3 (FR-007); orden `C, D, A` del ejemplo de FR-007 (FR-007); US1.3 llave soltada por un enemigo en sala alcanzable cuenta como obtenible (FR-003); US1.4 trampas y cierres automáticos no cambian el veredicto (FR-004); salida dirigida A→B abierta y B→A cerrada sin llave (FR-005); llaves no consumidas: una llave abre varias puertas (FR-002); US1.6 `sala_salida` alcanzable por puerta abierta pero sin puerta con `llave_salida` → no resoluble y `existe_puerta_salida = False` (FR-009); `sala_inicial == sala_salida` sigue exigiendo la puerta (FR-001); llaves prescindibles aparecen en el orden y `es_salida` marca solo `llave_salida` (FR-006); la cripta no declara `llave_salida`: resoluble si `sala_salida` es alcanzable y no resoluble si no lo es, sin exigir puerta de salida y con `es_salida` falso en todo el orden (Edge Cases, FR-001)
- [X] T014 [US1] En `tests/test_resolubilidad.py`, oráculo para SC-001 y SC-002: un verificador ingenuo escrito en la prueba (repite un recorrido completo por cada llave, solo con listas como arreglos, sin `dict`/`set`/`deque`) sobre 50 criptas de `tests/generador_criptas.py` con semillas fijas, resolubles y no resolubles: mismo veredicto, y siguiendo el orden mostrado cada llave se obtiene usando solo las anteriores. Atiende: FR-001, FR-002, FR-007
- [X] T015 [US1] En `tests/test_resolubilidad.py`, determinismo: 100 llamadas a `verificar` sobre la misma cripta dan resultados iguales campo por campo, también barajando salas, salidas y ubicaciones con `random.Random(semilla_fija)` en la prueba (SC-003). Atiende: FR-012, FR-013
- [X] T016 [US1] En `tests/test_resolubilidad.py`, prueba estática del Principio I sobre `Modelo/Resolubilidad.py` con `ast`: falla si importa `heapq`, `bisect`, `collections`, `networkx` u otra biblioteca de grafos; si llama a `sorted`, `.sort`, `dict(...)`, `set(...)`, `frozenset(...)`; o si contiene literales o comprensiones de `dict` o `set`. Comprueba también que solo importa de `DTOS`, `Modelo.ordenamiento` y `Modelo.Estructuras` (sin red, archivos ni consola). Atiende: FR-001, FR-023, FR-029
- [X] T017 [P] [US1] Crear `tests/test_verificacion_cli.py`: llamar a `main.main()` con `sys.argv` parcheado y salida capturada, sobre paquetes de `tests/generador_criptas.py`: `--offline <pkg> --verificar <resoluble>` imprime el bloque «Resoluble» exacto de [cli-verificacion.md](contracts/cli-verificacion.md) y devuelve 0 (FR-006, FR-016); una no resoluble también devuelve 0 (FR-016); no se crean ni modifican `*.cripta`, `*.cripta.log`, `partida.log` ni la tabla de puntajes (comparar el listado y las fechas de la carpeta temporal) (FR-015); `--verificar X --cripta Y` solo verifica X (FR-017); cripta inexistente → `! Error: ...` y código 1 (FR-025); dos ejecuciones dan la misma salida carácter por carácter (FR-012)

### Implementation for User Story 1

- [X] T018 [US1] Crear `Modelo/Resolubilidad.py` con `IndiceLlaves` (R4): `construir(menciones)` reúne ids de ubicaciones, llaves de salidas cerradas y `llave_salida`, ordena con `merge_sort` y quita repetidos con un barrido lineal; `numero(id_llave)` con búsqueda binaria escrita a mano (−1 si no está); `id_de(numero)`; `cantidad()`. Docstring con la tabla de complejidad de data-model §2.1 (construir O(M log M), `numero` O(log K), `id_de` y `cantidad` O(1)). Sin `bisect`, `sorted`, `.sort` ni `dict`. Atiende: FR-007, FR-014
- [X] T019 [US1] En `Modelo/Resolubilidad.py`, `SalidaVerif`, `SalaVerif` y `GrafoSalas.desde(esqueleto, indice, ubicaciones)` (R1): arreglo `salas` de largo `max_id + 1` indexado por id (`None` = no existe), salidas en orden N, S, E, O y otras después ordenadas con `merge_sort`, `num_llave` = −1 si está abierta o «no indica llave», `destino_valido` = «`0 <= destino <= max_id` y `salas[destino] is not None`», llaves por sala incluidas las que suelta un enemigo, arreglo `entrantes` de largo `max_id + 1`, primera aparición ante ids duplicados y `ValueError` con el id si no es entero no negativo. Docstring con la complejidad O(S + E + M log K). Atiende: FR-001, FR-003, FR-004, FR-005
- [X] T020 [US1] En `Modelo/Resolubilidad.py`, `recorrer(grafo, indice, sala_inicial) -> EstadoRecorrido` por oleadas (R5): `Queue` de `Modelo/Estructuras.py` marcando al encolar; arreglos `visitada[max_id + 1]`, `obtenida[K]`, `en_ronda[K]`; `espera[K]` con los destinos de puertas cerradas que esperan cada llave; al cerrar cada oleada, ordenar `nuevas` por número con `merge_sort`, marcar `obtenida`, anotar `(k, oleada)` en `orden` y soltar `espera[k]`. Sin solicitudes ni E/S. Docstring con la tabla de data-model §2.4 (recorrido O(S + E + K log K)). Atiende: FR-001, FR-002, FR-007, FR-026
- [X] T021 [US1] En `Modelo/Resolubilidad.py`, función pública `verificar(cripta_id, sala_inicial, sala_salida, llave_salida, esqueleto, ubicaciones) -> ResultadoVerificacion` según [interfaz-verificador.md](contracts/interfaz-verificador.md): construye índice y grafo, recorre, decide el veredicto («`obtenida[llave_salida]` y existe una salida con origen visitado, destino `sala_salida` y llave `llave_salida`»); si la cripta no declara `llave_salida`, es resoluble si `sala_salida` fue visitada (Edge Cases); arma `orden` como `LlaveOrdenada` con `es_salida`, y en el caso no resoluble llena `puertas_salida` (todas las salidas del grafo hacia `sala_salida` que piden `llave_salida` y no se pueden cruzar, por origen y dirección) y `existe_puerta_salida`; los demás campos del reporte quedan como listas vacías hasta US2. No modifica sus argumentos. Atiende: FR-001, FR-006, FR-007, FR-009, FR-012, FR-013
- [X] T022 [US1] En `Gestor/PreparadorPartida.py`, `verificar_cripta(cripta_id, gestor) -> ResultadoVerificacion`: `gestor.obtener_detalles` → `_fijar_presupuesto` (T008) → `gestor.obtener_esqueleto` → `gestor.obtener_llaves` (T007) → `Resolubilidad.verificar(...)`. Propaga sin capturar los errores de la fuente. Atiende: FR-001, FR-025, FR-026, FR-028
- [X] T023 [P] [US1] En `Vista/VistaConsola.py`, `mostrar_verificacion(resultado)`: bloque «Resoluble» (`La cripta <id> es resoluble.`, `Orden de obtención de llaves:` y `  n. <llave> (oleada m)` con ` <- llave de salida` en `es_salida`) y, si no es resoluble, la cabecera `La cripta <id> no es resoluble.` y la sección «Puerta hacia la sala de salida» con su variante «no existe ninguna salida hacia la sala … que requiera …», con el texto exacto de [cli-verificacion.md](contracts/cli-verificacion.md). Solo da formato: no ordena ni decide. Atiende: FR-006, FR-007, FR-009
- [X] T024 [US1] En `main.py` (**`git pull` antes**): argumento `--verificar ID`; rama después de `--bench` y `--mostrar-puntajes` y antes de `--replay`, `--cargar` y `--cripta`; crea el gestor como las demás ramas, llama a `verificar_cripta`, muestra con `vista.mostrar_verificacion` y devuelve 0; no crea controlador, bitácora ni partida; ante `ValueError`, `RuntimeError` u `OSError` (incluidas las subclases de `ErrorCliente`), `vista.mostrar_error` y 1. Atiende: FR-015, FR-016, FR-017, FR-025

**Checkpoint**: `--verificar` da veredicto y orden de punta a punta; T012 a T017 en verde.

---

## Phase 4: User Story 2 - Entender por qué una cripta no es resoluble (Priority: P1)

**Goal**: el reporte lista llaves no obtenibles, frontera bloqueada, puertas hacia la salida, ubicaciones, dependencias y ciclos.

**Independent Test**: con criptas de prueba construidas para cada causa de bloqueo, comparar el reporte con el contenido esperado.

### Tests for User Story 2 ⚠️

- [X] T025 [US2] En `tests/test_resolubilidad.py`, reporte sin dependencias: US2.1 llaves no obtenibles por id, frontera con origen, dirección, destino y llave, ubicaciones con sala y enemigo (FR-008, FR-009, FR-010); US2.5 llave requerida sin ubicación → `lugares` vacío (FR-010); frontera vacía con salas desconectadas (FR-009); puerta cerrada sin llave → `llave = None` y no falla (FR-009); puerta cerrada entre dos salas alcanzables no está en la frontera (FR-009); `sala_salida` alcanzable con su puerta con `llave_salida` bloqueada → aparece en `puertas_salida` (FR-009); llave con varias ubicaciones → todas, por sala y luego enemigo (FR-010, FR-014); ubicación y destino en sala inexistente → `sala_existe`/`destino_existe` falsos y no detiene la verificación (FR-010); llave más allá de `sala_salida` (FR-001); orden de puertas por sala de origen y dirección N, S, E, O (FR-014)
- [X] T026 [US2] En `tests/test_resolubilidad.py`, dependencias y ciclos: US2.2 ciclo directo `K -> K` con `directo = True` (FR-011); US2.3 ciclo `K1 -> K2 -> K1` (FR-011); US2.4 puertas alternativas con K y con J, J sin ubicación → K sin dependencia y sin ciclos (FR-011); contraejemplo de R7 (K en R; región →(K) R; R →(J) Z; Z → R abierta) → `K -> K` porque la puerta R→Z es interna (FR-011); puerta sin llave entrando a la zona → sin dependencia (FR-011); cada llave de un ciclo aparece en exactamente un ciclo; cada ciclo empieza por su menor llave y los ciclos salen ordenados por ella (FR-011, FR-014); llaves sin dependencia listadas como tales (FR-011)
- [X] T027 [US2] En `tests/test_resolubilidad.py`, US2.6: una cripta con varios ciclos, barajando salas, salidas y ubicaciones con semillas fijas, da siempre los mismos ciclos, en el mismo orden y empezando por la misma llave. Atiende: FR-012, FR-013, FR-014
- [X] T028 [P] [US2] En `tests/test_verificacion_cli.py`, el texto completo del bloque «No resoluble» de [cli-verificacion.md](contracts/cli-verificacion.md) para una cripta con ciclo por cadena, frontera, llave de enemigo y llave sin ubicación, comparado carácter por carácter; y las variantes: frontera vacía, destino inexistente, sin puerta de salida, ubicación en sala inexistente, ciclo directo, «Ciclos de llaves: ninguno.». Con la salida, una persona puede señalar puerta, llave faltante y ubicación sin consultar los datos (SC-009). Atiende: FR-008, FR-009, FR-010, FR-011, FR-012, FR-014

### Implementation for User Story 2

- [X] T029 [US2] En `Modelo/Resolubilidad.py`, barrido final del reporte (R6), sin estructuras nuevas: `no_obtenibles` recorriendo k = 0..K−1; `frontera` recorriendo salas visitadas por id y sus salidas en el orden fijo (cerrada, destino no visitado o inexistente, llave no obtenida o «sin llave»); `ubicaciones` agrupadas por número de llave tras ordenar las ubicaciones una vez con `merge_sort` por la clave `(número de llave, sala, 0 si no hay enemigo y 1 si hay, enemigo o "")`, porque Python no compara `None` con texto, para cada llave no obtenible y cada llave de la frontera. Docstring O(S + E + K + L log L). Atiende: FR-008, FR-009, FR-010, FR-014
- [X] T030 [US2] En `Modelo/Resolubilidad.py`, `calcular_dependencias(grafo, indice, estado) -> list[int]` (R7): zona hacia atrás desde cada sala de ubicación con la misma `Queue`, siguiendo `entrantes` que no son puertas bloqueadas y cuyo origen está fuera de la región; arreglo `sello[max_id + 1]` (nunca se limpia, un sello nuevo por zona); descartar candidatas con origen sellado (puertas internas); reducir a ninguna / J / conflicto con corte al primer conflicto; `valor_zona[max_id + 1]` (−2 sin calcular, −1 sin dependencia, j) para compartir la zona entre llaves de la misma sala; ubicación en sala inexistente o zona sin puertas → −1. Docstring con O(S + E + Σ zonas) y peor caso O(L·(S + E)) (P-11). Atiende: FR-011
- [X] T031 [US2] En `Modelo/Resolubilidad.py`, `hallar_ciclos(depende_de, no_obtenible) -> list[list[int]]` (R8): arreglos `marca[K]` y `en_ciclo[K]`, detección siguiendo `depende_de` en O(K) y emisión barriendo k = 0..K−1 para que cada ciclo empiece por su menor llave y salgan ordenados sin ordenar nada; directo si `depende_de[k] == k`. Docstring O(K). Atiende: FR-011, FR-014
- [X] T032 [US2] En `Modelo/Resolubilidad.py`, `verificar` llena `no_obtenibles`, `frontera`, `ubicaciones`, `dependencias` (`DependenciaLlave` por cada no obtenible, por id) y `ciclos` (`CicloLlaves`) solo cuando no es resoluble. Atiende: FR-008, FR-009, FR-010, FR-011, FR-012
- [X] T033 [US2] En `Vista/VistaConsola.py`, completar `mostrar_verificacion` con las secciones «Llaves no obtenibles», «Frontera bloqueada» (y su variante vacía), «Ubicación de las llaves» (con `(la suelta <enemigo>)`, `(no existe)` y «ubicación desconocida»), «Dependencias entre llaves» (`a -> b` o `a: sin dependencia`) y «Ciclos de llaves» (`(ciclo directo)` y «ninguno.»), en el orden y texto exactos del contrato. Atiende: FR-008, FR-009, FR-010, FR-011, FR-014

**Checkpoint**: US1 y US2 completas; `--verificar` explica cualquier cripta no resoluble.

---

## Phase 5: User Story 3 - Impedir partidas imposibles al iniciar (Priority: P2)

**Goal**: toda partida nueva se verifica antes de crear motor y bitácora; si no es resoluble, no inicia.

**Independent Test**: iniciar una partida nueva en una cripta no resoluble y comprobar el reporte, el código 1 y que no se creó bitácora; repetir con una resoluble y comprobar que inicia.

### Tests for User Story 3 ⚠️

- [X] T034 [US3] En `tests/test_verificacion_cli.py`: `--cripta <no resoluble>` → `! Error: La cripta <id> no es resoluble. Usa --forzar para jugarla de todos modos.` seguido del reporte, código 1, sin bitácora ni cambios en la tabla de puntajes (FR-020, SC-006); `--cripta <resoluble>` con entrada `salir` → muestra el orden y la partida inicia (FR-019); sin `--cripta`, eligiendo la no resoluble de la lista interactiva → igual que `--cripta` (FR-018); con fuente simulada, la verificación seguida de la partida no repite las solicitudes de detalles, versión, esqueleto ni llaves (FR-026)
- [X] T035 [US3] En `tests/test_verificacion_cli.py`, SC-007: misma cripta, semilla y acciones, con la verificación y llamando directamente a `preparar_partida` sin ella → misma bitácora y mismo estado final; el estado del generador de azar de la partida es el mismo antes y después de verificar; la verificación no aparece en la bitácora ; el conocimiento del jugador (mapa conocido) es el mismo con verificación y sin ella (FR-023)

### Implementation for User Story 3

- [X] T045 [US3] En `Gestor/PreparadorPartida.py`, confirmar que `verificar_cripta` fija el presupuesto antes de pedir esqueleto y llaves, y que `preparar_partida` reutiliza los detalles, la versión y el esqueleto ya memorizados por el gestor tras la verificación (sin solicitudes repetidas); ajustar si T034 lo muestra (T043 lo vuelve a comprobar en US5). Atiende: FR-024, FR-026
- [X] T036 [US3] En `Controlador/ControladorPartida.py` (contrato compartido: avisar al grupo): clase `CriptaNoResoluble(Exception)` con atributo `resultado` y mensaje `La cripta <id> no es resoluble. Usa --forzar para jugarla de todos modos.` (no hereda de `ValueError`, `RuntimeError` ni `OSError`); `nueva_partida(cripta_id, semilla=None, forzar=False)` llama a `verificar_cripta` **antes** de `preparar_partida` y de crear `BitacoraPartida`; si es resoluble, `vista.mostrar_verificacion(resultado)`; si no, `raise CriptaNoResoluble(resultado)`. `cargar(...)` no cambia. Atiende: FR-018, FR-019, FR-020, FR-023
- [X] T037 [US3] En `main.py` (**`git pull` antes**): en la rama de partida nueva (`--cripta` y lista interactiva), capturar `CriptaNoResoluble` antes que los demás errores: `vista.mostrar_error(str(e))`, `vista.mostrar_verificacion(e.resultado)` y `return 1`, sin crear bitácora ni tocar puntajes. Atiende: FR-018, FR-020
- [X] T038 [US3] Ejecutar la suite completa y corregir las pruebas existentes que inician partidas nuevas y ahora fallan: si su cripta de prueba no es resoluble, hacerla resoluble en `tests/utiles_niebla.py` o `tests/test_integracion.py` (por ejemplo, agregando la salida hacia `sala_salida` que pide `llave_salida`) cuando eso no cambie lo que la prueba comprueba; si lo cambiaría, pasar `forzar=True` con un comentario que cite FR-021. Comparar con la línea base de T001. Las criptas de prueba sin `llave_salida` son resolubles si `sala_salida` es alcanzable; no hace falta agregarles llave. Atiende: FR-018, FR-021, FR-028

**Checkpoint**: ninguna partida nueva inicia en una cripta no resoluble; la suite previa sigue en verde.

---

## Phase 6: User Story 4 - Jugar de todos modos con `--forzar` (Priority: P2)

**Goal**: `--forzar` inicia la partida sin reporte ni orden, con la verificación ejecutándose igual.

**Independent Test**: iniciar con `--forzar` una cripta no resoluble y comprobar que la partida inicia sin reporte.

### Tests for User Story 4 ⚠️

- [X] T039 [US4] En `tests/test_verificacion_cli.py`: `--cripta <no resoluble> --forzar` inicia sin reporte (FR-021, US4.1); `--cripta <resoluble> --forzar` inicia sin reporte ni orden (FR-021, US4.2); `--verificar <no resoluble> --forzar` muestra el resultado completo, código 0 y no inicia partida (FR-017, US4.3); una partida forzada guardada y su bitácora funcionan con `--cargar` y `--replay` sin `--forzar` y sin verificar (con fuente simulada: cero solicitudes a `/llaves`) (FR-022); `--cargar F --forzar` y `--replay F --forzar` ignoran la opción (FR-022)

### Implementation for User Story 4

- [X] T040 [US4] En `Controlador/ControladorPartida.py`, rama `forzar=True` de `nueva_partida`: verifica igual (los errores de datos se propagan) pero no muestra nada ni lanza `CriptaNoResoluble`. Atiende: FR-018, FR-021
- [X] T041 [US4] En `main.py` (**`git pull` antes**): argumento `--forzar` (`store_true`) pasado a `controlador.nueva_partida(..., forzar=argumentos.forzar)` solo en la rama de partida nueva; las ramas `--cargar` y `--replay` no lo leen; con `--verificar` no tiene efecto. Atiende: FR-017, FR-021, FR-022

**Checkpoint**: US1 a US4 completas.

---

## Phase 7: User Story 5 - Fallo al obtener la ubicación de las llaves (Priority: P3)

**Goal**: ante un error del servicio, presupuesto agotado o falta de `llaves.json`, se informa el motivo, sin veredicto, y la partida no inicia (también con `--forzar`).

**Independent Test**: con una fuente que falla o con el presupuesto agotado, comprobar el motivo, el código 1 y que la partida no inició.

### Tests for User Story 5 ⚠️

- [X] T042 [P] [US5] En `tests/test_verificacion_cli.py`: paquete de T002/T009 con `escribir_llaves=False`; `--verificar` y `--cripta … --forzar` → `! Error: Falta el archivo para /criptas/<id>/llaves: <ruta>`, sin veredicto, código 1, sin bitácora (FR-024, FR-028, US5.3); paquete con una entrada de llave sin `sala` → `! Error: Respuesta inválida de /criptas/<id>/llaves: ...` y código 1 (FR-025)
- [X] T043 [P] [US5] En `tests/test_fuente_llaves.py`, con una fuente HTTP simulada (sesión falsa, sin red): presupuesto 2 → `Se agotó el presupuesto de solicitudes (2) al consultar <url>`, sin hacer la solicitud de llaves y con solicitudes ≤ presupuesto, también con respuestas 429 que provocan reintentos (FR-024, FR-026, SC-008); respuesta 500 en `/llaves` → `El servicio respondió 500 ...` propagado por `verificar_cripta` sin resultado (FR-024, US5.1); fallo en detalles o en salas → mismo trato (FR-025); cripta sintética de 300 salas en 6 páginas → 9 solicitudes sin caché y 2 con caché válida (FR-026)

### Implementation for User Story 5

- [X] T044 [US5] En `main.py` (**`git pull` antes**): revisar que la rama `--verificar` y la de partida nueva capturen `ErrorCliente` y sus subclases, `RuntimeError`, `ValueError` y `OSError` con `vista.mostrar_error` y `return 1`, sin mostrar veredicto, también con `--forzar`, y que `CriptaNoResoluble` se capture antes que ellos. Atiende: FR-024, FR-025

**Checkpoint**: las cinco historias completas.

---

## Phase 8: Rendimiento y `--bench`

**Purpose**: respaldar con mediciones el límite de 200 ms y el crecimiento lineal, y comparar el recorrido incremental con el recorrido repetido por llave. T046 a T048 pueden empezar en cuanto termine T021.

- [X] T046 [P] Crear `tests/bench_resolubilidad.py` con `correr_bench()`: genera las criptas con `tests/generador_criptas.py` y semillas fijas, mide solo `Resolubilidad.verificar(...)` con los datos ya en memoria (sin obtención de datos), con `time.perf_counter`, repeticiones y calentamiento; imprime y escribe `resultados_bench_resolubilidad.txt` con el mismo formato que los demás bench (equipo, versión de Python, mediana y p95). No instancia la vista. Atiende: FR-029, FR-030
- [X] T047 M1 en `tests/bench_resolubilidad.py`: cripta sintética de 300 salas, ≈ 760 salidas y 4 llaves, resoluble y no resoluble con `con_ciclo=True`; p95 < 200 ms y línea `CUMPLE`/`NO CUMPLE` por caso. Atiende: FR-029, FR-030 (SC-004)
- [X] T048 M2 y M3 en `tests/bench_resolubilidad.py`: duplicaciones 300 → 600 → 1200 → 2400 → 4800 → 9600 salas, escalando salidas y llaves, caso resoluble (M2) y no resoluble con reporte, dependencias y ciclos (M3); cociente de medianas entre duplicaciones consecutivas ≤ 2,5, informado por par. M3 usa criptas con zonas disjuntas (T002); el peor caso de P-11 (zonas que se solapan) se mide aparte como dato informativo, sin el límite de 2,5 (SC-005). Atiende: FR-029, FR-030 (SC-005)
- [X] T049 M4 en `tests/bench_resolubilidad.py`: **recorrido incremental por oleadas (elegido) frente a A1, recorrido completo repetido por cada llave obtenida**, con salas fijas y K creciente (4, 16, 64, 256) y en las duplicaciones de M2; además A2 (zona de cada llave por separado limpiando marcas) y A3 (búsqueda lineal del id en vez de binaria). A1 a A3 viven solo en el archivo de bench, con listas como arreglos y sin `dict`/`set`/`deque`/`heapq`/`bisect`/`collections`; antes de medir, comprobar que dan el mismo resultado que `verificar`. Atiende: FR-029, FR-030
- [X] T050 M5 en `tests/bench_resolubilidad.py`: contar las comparaciones de `merge_sort` con el contador que ya devuelve y los pasos de la búsqueda binaria de `IndiceLlaves` al crecer M y K, para respaldar O(M log M) y O(log K). Atiende: FR-029, FR-030
- [ ] T051 En `main.py` (**`git pull` antes**): la rama `--bench` llama a `tests.bench_resolubilidad.correr_bench()` después de los bench existentes, separado con una línea en blanco. Atiende: FR-030
- [ ] T052 Ejecutar `python main.py --bench` y conservar `resultados_bench_resolubilidad.txt`. Si M1 o M2 fallan, corregir el código; si M3 supera 2,5 con zonas disjuntas, es un defecto: corregir el código. El peor caso de P-11 solo se informa. Atiende: FR-029, FR-030

---

## Phase 9: Polish y documentación

- [ ] T053 Completar en Decisiones/DECISIONES.md la sección «§5.4 — Resolubilidad» de la Parte II, con la estructura de P1 §8 y enlaces a spec.md y plan.md, indicando si la decisión final coincide con la de este plan.md y, si no, qué medición motivó el cambio (enunciado §7.1). Incluir: decisiones R1 a R8 de research.md con sus alternativas; la comparación del recorrido incremental contra el recorrido repetido por llave (A1), y de A2 y A3, con los números de resultados_bench_resolubilidad.txt; M1 (p95 frente a 200 ms), cocientes de M2 y M3 y conteos de M5; el peor caso O(L·(S + E)) de las dependencias (P-11). Toda cifra sale del archivo de bench; lo no medido se marca como hipótesis (Principio VIII). Depende de T052. Atiende: FR-029, FR-030
- [ ] T054 [P] Revisar que los docstrings de `IndiceLlaves`, `GrafoSalas`, `recorrer`, el barrido del reporte, `calcular_dependencias`, `hallar_ciclos` y `verificar` en `Modelo/Resolubilidad.py` tengan las tablas de complejidad de [data-model.md](data-model.md), y que T016 siga en verde. Atiende: FR-029
- [ ] T055 [P] Actualizar `README.md` (UTF-16: abrirlo y guardarlo en esa codificación; avisar al grupo antes): `--verificar` y `--forzar`, prioridad `--bench > --mostrar-puntajes > --verificar > --replay > --cargar > --cripta / lista`, códigos de salida de este modo, archivo `criptas/<id>/llaves.json` del paquete offline con su formato, caché `datos_locales/llaves_<id>.json` y el nuevo archivo de resultados del bench. Atiende: FR-017, FR-028, FR-031
- [ ] T056 [P] Agregar `criptas/<id>/llaves.json` a cada cripta de `paquete/` (versionado y compartido: avisar al grupo antes de confirmarlo), con la misma herramienta con que se armó el paquete; si no hay herramienta, documentar en `README.md` cómo descargar el archivo de `GET /criptas/<id>/llaves`. Atiende: FR-024, FR-028
- [ ] T057 Validación final según [quickstart.md](quickstart.md): `python -m unittest discover -s tests -v` al 100 %, los 22 escenarios de la sección 2 cubiertos por al menos una prueba que cita su FR (revisar con `grep -rn "FR-0" tests/test_resolubilidad.py tests/test_verificacion_cli.py tests/test_fuente_llaves.py`), determinismo de la sección 3 y bench de la sección 4. Atiende: FR-001 a FR-026 y FR-028 a FR-031 (SC-001 a SC-009)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001–T003)**: sin dependencias. T002 bloquea T003, T011, T014, T017, T046 y la T003 de la spec 003.
- **Foundational (T004–T011)**: depende de Setup. Bloquea todas las historias. T007 depende de T006.
- **US1 (T012–T024)**: depende de Foundational. Es el MVP.
- **US2 (T025–T033)**: depende de T018–T021 (índice, grafo, recorrido y `verificar`) y de T023 para la vista.
- **US3 (T034–T038, T045)**: depende de US1 (T022, T023). T034 depende de T045. Puede avanzar en paralelo con US2, pero el reporte completo de T034 necesita T033.
- **US4 (T039–T041)**: depende de US3 (T036, T037).
- **US5 (T042–T044)**: depende de T022 y T024; las ramas de partida nueva, de T037 y T041.
- **Rendimiento (T046–T052)**: T046–T049 desde T021; M3 completo desde T032; T051 tras T024 por ser el mismo archivo.
- **Polish (T053–T057)**: T053 depende de T052; T057 de todo.

### Archivos compartidos y dependencias con otros integrantes

| Archivo / contrato | Tareas | Coordinación |
|---|---|---|
| `main.py` | T024, T037, T041, T044, T051 | Compartido: `git pull` antes de cada tarea; nunca dos en paralelo |
| `tests/utiles_niebla.py`, `tests/test_integracion.py` | T009, T010, T038 | Generadores de paquetes del grupo: deben escribir `llaves.json`; avisar a sus autores |
| `tests/generador_criptas.py` | T002 | Lo necesita la T003 de la spec 003 (terreno y cazador): avisar a esa persona cuando esté |
| `ControladorPartida.nueva_partida` | T036, T040 | Firma nueva con `forzar=False` por defecto: avisar al grupo |
| `GestorDatos`, `AlmacenamientoLocalApi`, `API/Fuentes.py` | T005–T007 | Adaptadores compartidos: avisar al grupo |
| `README.md` | T055 | UTF-16; avisar al grupo |
| `Decisiones/DECISIONES.md` | T053 | Sección §5.4; el resto del documento es del grupo |
### Within Each User Story

- Pruebas primero, comprobando que fallan.
- Modelo (`Modelo/Resolubilidad.py`) → gestor → vista → controlador → `main.py`.
- Las tareas sobre `tests/test_resolubilidad.py`, `Modelo/Resolubilidad.py` y `main.py` van en secuencia (mismo archivo).

### Parallel Opportunities

- Setup: T002 y T003 se escriben en paralelo (T003 se ejecuta cuando T002 exista).
- Foundational: T004, T005, T006, T009, T010 y T011 en paralelo; luego T007 y T008.
- US1: T017 (CLI) en paralelo con T012–T016 (modelo); T023 (vista) en paralelo con T018–T022.
- US2: T028 (CLI) en paralelo con T025–T027; T033 en paralelo con T029–T031 si se acuerdan los campos de T004.
- US5: T042 y T043 en paralelo.
- Rendimiento: T046 en paralelo con US2–US5.
- Polish: T054, T055 y T056 en paralelo.

---

## Parallel Example: User Story 1

```text
# Pruebas en paralelo (archivos distintos):
T012–T016  tests/test_resolubilidad.py   (en secuencia entre sí)
T017       tests/test_verificacion_cli.py

# Implementación en paralelo:
T018 → T019 → T020 → T021 → T022   Modelo/Resolubilidad.py y Gestor/PreparadorPartida.py
T023                                Vista/VistaConsola.py
# Al final, solo: T024 main.py (git pull antes)
```

## Parallel Example: User Story 2

```text
T025 → T026 → T027   tests/test_resolubilidad.py
T028                 tests/test_verificacion_cli.py
T029 → T030 → T031 → T032   Modelo/Resolubilidad.py
T033                        Vista/VistaConsola.py
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1: línea base y generador sintético (avisar a la persona de la spec 003 al terminar T002).
2. Phase 2: resultado, llaves con validación y caché, paquetes de prueba con `llaves.json`.
3. Phase 3: US1. **Parar y validar** `--verificar` con una cripta resoluble y otra no.

### Incremental Delivery

1. US1 → `--verificar` con veredicto y orden (MVP).
2. US2 → reporte completo con dependencias y ciclos.
3. US3 → verificación obligatoria al iniciar partida (corregir la suite previa en T038).
4. US4 → `--forzar`.
5. US5 → caminos de error.
6. Rendimiento → M1 a M5 y `--bench`.
7. Polish → `DECISIONES.md`, README, `paquete/`, validación final.

## Notes

- Las tareas citan FR; las pruebas citan en su nombre o docstring el FR que verifican (Principio X).
- FR-027 no existe (retirado); no se reutiliza.
- Las correcciones de texto de la spec P-13 y P-14 del plan, si se aceptan, van a la spec en una confirmación propia antes del código (Principio IX).
- Anotar este `/speckit-tasks` en las notas personales para `PROMPTS_LLM.md` (Principio XI).
- Confirmar al terminar cada tarea o grupo lógico, sobre `main` (constitución v3.0.2).
