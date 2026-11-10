# Research: Verificación de resolubilidad (spec 002)

**Fecha**: 2026-11-09 | **Plan**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md)

Cada decisión sigue el formato *Decisión / Razón / Alternativas*. Las complejidades son análisis; todo tiempo es
hipótesis hasta medirlo con `python main.py --bench` (Principio VIII, mediciones M1 a M5 en [R12](#r12-mediciones-en---bench-fr-029-fr-030-sc-004-sc-005)).

Notación: **S** salas, **E** salidas, **K** llaves distintas, **L** ubicaciones de llaves, **C** salidas cerradas que
indican llave, **M = L + C + 1** menciones de llaves (ubicaciones, puertas y `llave_salida`).

## Datos observados en el servicio (2026-11-09)

Consultados con solicitudes de solo lectura (`GET /criptas`, `/criptas/<id>`, `/criptas/<id>/llaves` y las 6 páginas de
`/criptas/cripta-06/salas`). No se copian al código (Principio IV); solo dimensionan el diseño.

| Cripta | Salas | Salidas | Cerradas | Llaves (ubicaciones) | Ids de sala |
|--------|-------|---------|----------|----------------------|-------------|
| cripta-02 | 20 | 40 | 2 | 2 | 1..20 |
| cripta-03 | 40 | — | — | 3 (una la suelta un enemigo) | — |
| cripta-04 | 50 | — | — | 3 (una la suelta un enemigo) | — |
| cripta-05 | 24 | — | — | 3 | — |
| **cripta-06** (la más grande) | **300** | **760** | **56** | **4** (una la suelta un enemigo) | **1..300**, enteros contiguos |

- Formato real de `/criptas/<id>/llaves`: `{"llaves": [{"id": "...", "sala": <entero>, "enemigo": "..."?}]}`. El campo
  se llama `id`, no `llave` como dice la spec en Assumptions; `DTOS/UbicacionLlave.py` ya lee `id`.
- `FuenteDatos.obtener_llaves_cripta` y `DTOS/UbicacionLlave` **ya existen** en el repositorio. Falta usarlos desde el
  gestor, validar las entradas incompletas y agregar el archivo al paquete offline.
- La cripta de referencia para SC-004 es entonces de **S = 300, E = 760, K = 4**. Las mediciones sintéticas usan al
  menos ese tamaño.

---

## R1. Vector de salas (FR-001, FR-003, FR-005)

**Decisión**: arreglo `salas` (una `list` de Python usada como arreglo de tamaño fijo) indexado por id de sala, de
largo `max_id + 1`. Cada posición es `None` (la sala no existe) o un registro `SalaVerif` con:

- `salidas`: arreglo de `SalidaVerif(direccion, destino, cerrada, num_llave, id_llave)` en orden fijo de dirección
  **N, S, E, O** (el mismo desempate que FR-024 de la spec 001); cualquier otra dirección va después, ordenada por
  su texto con `merge_sort`.
- `llaves`: arreglo de números de llave ubicados en esa sala, incluidas las que suelta un enemigo que inicia allí
  (FR-003: la ubicación de una llave soltada es la sala del enemigo, que es justo lo que trae `/llaves`).

Se construye una sola vez con un barrido del esqueleto: O(S + E). Una salida cuyo destino no existe se guarda con
`destino_valido = False`: no aporta alcance, pero aparece en la frontera si está cerrada (Edge Cases).

Las salidas son dirigidas (FR-005): cada `SalidaVerif` vive solo en el arreglo de su origen.

**Razón**: los ids de sala son enteros contiguos desde 1 en todas las criptas observadas; el acceso por índice es
O(1) y no hace falta ninguna búsqueda. El `dict` `sala.salidas` del DTO solo se recorre durante la construcción
(uso auxiliar permitido por el Principio I).

**Alternativas**:

| Alternativa | Costo de llegar a una sala por id | Por qué no |
|---|---|---|
| Recorrer la lista del esqueleto buscando el id | O(S) por salida → O(S·E) | cuadrático |
| Arreglo de ids ordenado + búsqueda binaria | O(log S) por salida → O(E log S) | innecesario mientras los ids sean enteros pequeños |
| `dict` id → sala | O(1) esperado | prohibido como índice (Principio I) |

**Supuesto y salvaguarda**: un id de sala que no sea entero no negativo hace fallar la verificación con
`! Error: ...` (mismo trato que FR-025, datos de la cripta inválidos). Si los ids fueran muy dispersos (por ejemplo
`max_id` > 4·S), la memoria sería O(max_id); no ocurre en ninguna cripta publicada y queda en [Riesgos](plan.md#riesgos).

---

## R2. Cola FIFO del recorrido (FR-001, FR-002)

**Decisión**: se reutiliza `Queue` de `Cache/Estructuras.py` (lista enlazada con `front` y `rear`). Solo se usan
`enqueue`, `dequeue` e `is_empty`, todas O(1). **`size()` no se usa en el recorrido** porque recorre la cola completa
(O(n)); si alguna vez hiciera falta el tamaño, se lleva un contador aparte.

Regla de la cola: una sala se **marca al encolarse**, no al sacarse, así cada sala entra a lo sumo una vez y el
total de operaciones es O(S).

**Razón**: la estructura ya existe, está probada por `CacheCatalogo` y `PlanificadorPrecarga`, y cumple el
Principio I. Importarla desde `Modelo/` se justifica en [Complexity Tracking](plan.md#complexity-tracking).

**Alternativas**: `collections.deque` (prohibida); `list.pop(0)` (O(n) por extracción, O(S²) en total); una cola
nueva en `Modelo/` (duplicaría código ya probado).

---

## R3. Vectores de marcas (FR-001, FR-007)

**Decisión**: dos arreglos de booleanos de tamaño fijo: `visitada[max_id + 1]` y `obtenida[K]`. Un tercero,
`en_ronda[K]`, evita anotar dos veces la misma llave en una oleada. Marcar y consultar: O(1). Crearlos: O(S + K).

**Alternativas**: `set` de visitadas (prohibido); buscar en una lista de visitadas (O(S) por consulta).

---

## R4. Índice de llaves (FR-007, FR-014)

**Decisión**: arreglo ordenado `ids_llaves[0..K-1]` con búsqueda binaria escrita a mano que devuelve el número de
llave (su posición) o −1. Ese número indexa `obtenida`, `en_ronda`, `espera`, `ubicaciones` y `depende_de`.

Construcción, una sola vez antes del recorrido:

1. Reunir las M menciones de llaves: id de cada ubicación, llave de cada salida cerrada que la indica, y
   `llave_salida`.
2. Ordenarlas con `merge_sort` de `Modelo/ordenamiento.py` (O(M log M)). **Prohibidos `sorted()` y `.sort()`.**
3. Quitar repetidos con un barrido lineal (iguales quedan contiguos): O(M).
4. Traducir cada mención a su número con búsqueda binaria: O(M log K).

Como el arreglo está ordenado, **el orden por número coincide con el orden por identificador**. Eso deja todos los
órdenes del resultado (oleadas, llaves no obtenibles, dependencias, ciclos) sin comparar textos otra vez.

Una llave que pide una puerta pero no tiene ubicación queda en el índice igual: es la que se reporta como «ubicación
desconocida» (US2.5).

**Alternativas**:

| Alternativa | Búsqueda | Construcción | Decisión |
|---|---|---|---|
| **Arreglo ordenado + búsqueda binaria** | O(log K) | O(M log M) | **Elegida**: el índice es estático, se arma una vez y no cambia durante el recorrido |
| Árbol rojo-negro | O(log K) | O(M log K) | Misma complejidad de búsqueda con mucho más código; su ventaja (insertar y borrar en O(log K)) no se usa porque el índice no cambia |
| Tabla hash propia | O(1) esperado | O(M) esperado | Descartada por la restricción de este plan; además su orden no sirve para FR-014, habría que ordenar aparte |
| Búsqueda lineal del id | O(K) | O(M·K) | Se mide como alternativa A3 en `--bench` |

**Costo total del algoritmo** (refina el «O(S + E + K log K)» del pedido): **O(S + E + M log M)**. Cada llave aparece
en pocas puertas y ubicaciones, así que M crece con K y C, y al duplicar la cripta el término M log M se multiplica por
algo más que 2 (≈ 2,1 a 2,2), dentro del 2,5 de SC-005. En la cripta de referencia M = 4 + 56 + 1 = 61.

---

## R5. Recorrido por oleadas y puertas en espera (FR-001, FR-002, FR-006, FR-007)

**Decisión**: un único recorrido en anchura, partido en oleadas. Estructura nueva: `espera[K]`, arreglo indexado por
número de llave; cada posición es la lista de destinos de salidas cerradas que esperan esa llave.

```text
marcar y encolar sala_inicial
oleada = 1
repetir:
    mientras la cola no esté vacía:
        s = dequeue
        por cada llave k ubicada en s: si no obtenida[k] y no en_ronda[k] → en_ronda[k] = V, anotar k en nuevas
        por cada salida de s con destino válido:
            abierta, o cerrada con obtenida[llave]  → si destino no visitado: marcar, encolar
            cerrada con llave aún no obtenida        → agregar destino a espera[llave]
            cerrada sin llave                        → nada (se reporta en el barrido final)
    si nuevas está vacía: terminar
    ordenar nuevas por número con merge_sort  (= orden por identificador, R4)
    por cada k de nuevas: obtenida[k] = V, agregar (k, oleada) al orden
                          por cada destino en espera[k]: si no visitado, marcar y encolar
                          vaciar espera[k]
    oleada += 1
```

Por qué cumple FR-007: una llave encontrada en la oleada *n* no se marca obtenida hasta que la oleada termina, así
que las puertas que pide esperan; las salas que esas puertas abren se procesan en la oleada *n+1*. El ejemplo de la
spec (C y D alcanzables, C abre la sala de A) da `C, D, A`.

**Costo**: cada sala se encola una vez (O(S)); cada salida se examina una vez, cuando se procesa su origen (O(E)); cada
entrada de `espera` se suelta una vez (O(C)); ordenar las oleadas suma O(K log K). Sin solicitudes de red (FR-026):
el recorrido solo lee arreglos en memoria.

**Alternativas**:

- **A1, repetir el recorrido completo cada vez que se obtiene una llave**: O(K·(S + E)). Más simple, pero crece con
  K·S. Se mide en `--bench`.
- Volver a revisar todas las puertas cerradas al terminar cada oleada en vez de tenerlas en espera: O(K·C).
- Cola de prioridad por oleada: innecesaria, la oleada ya ordena por tiempo y el orden interno sale del índice.

---

## R6. Veredicto y reporte como barrido final (FR-006, FR-008, FR-009, FR-010, FR-014)

**Decisión**: no hay estructura propia; es un barrido de O(S + E + K + L) sobre lo ya calculado.

- **Veredicto**: `obtenida[llave_salida]` y existe una salida con origen visitado, destino `sala_salida` y llave
  `llave_salida`.
- **Orden de llaves** (si es resoluble): la lista `(k, oleada)` del recorrido, señalando `llave_salida`.
- **Llaves no obtenibles**: `obtenida[k]` falso, recorriendo k = 0..K−1 (= orden por identificador).
- **Frontera bloqueada**: salas visitadas en orden de id; por cada una, sus salidas en el orden fijo de R1; se
  incluye la cerrada cuyo destino no está visitado (o no existe) y cuya llave no está obtenida o no se indica.
  Así queda «por sala de origen y luego por dirección» (FR-014) sin ordenar.
- **Puerta hacia la salida**: barrido de todas las salidas (no solo de la región) que van a `sala_salida` y piden
  `llave_salida`, en el mismo orden. Se listan las que no se pueden cruzar; si no hay ninguna, se dice explícitamente
  (FR-009, US1.6).
- **Ubicaciones**: `ubicaciones[K]`, listas armadas desde las ubicaciones ordenadas una vez con `merge_sort` por
  `(número de llave, sala, enemigo)` → O(L log L). Una ubicación en sala inexistente se reporta tal cual (Edge Cases).

**Razón**: todos los órdenes de FR-014 salen del índice por id de sala, del orden fijo de direcciones o del índice
de llaves; el resultado no depende del orden en que la fuente entregue los datos (FR-013, SC-003).

---

## R7. Dependencias entre llaves (FR-011, Clarifications)

Solo se calcula si la cripta **no** es resoluble.

**Regla** (spec, Definiciones): la zona de una sala no alcanzable *x* son las salas fuera de la región desde las que
se llega a *x* sin cruzar ninguna puerta bloqueada. Las puertas que **entran** a la zona son las puertas bloqueadas con
destino dentro de la zona y origen fuera de ella (el origen puede estar dentro o fuera de la región). K → J si, para
**cada** ubicación de K, todas las puertas que entran a su zona piden J. Si alguna pide otra llave, no indica llave,
la ubicación está en una sala inexistente o la zona no tiene puertas que entren, K no depende de ninguna.

**Decisión**:

1. **Entrantes**: arreglo `entrantes[max_id + 1]` de listas de `(origen, salida)`, armado en el mismo barrido de R1
   (O(S + E)).
2. **Zona por sala de ubicación, hacia atrás**: recorrido en anchura con la misma `Queue`, siguiendo entrantes que
   **no** son puertas bloqueadas y cuyo origen está fuera de la región. Las puertas bloqueadas que llegan a una sala de
   la zona se anotan como candidatas.
3. **Marcas con sello** en vez de booleanos: `sello[max_id + 1]` guarda el número de la zona que visitó la sala. Una
   zona nueva no necesita limpiar el arreglo (sería O(S) por zona); basta con usar un sello nuevo.
4. Al cerrar la zona se descartan las candidatas cuyo origen tiene el sello actual (puertas internas) y se reduce el
   resto a un solo valor: *ninguna*, *J* o *conflicto*. Con el primer conflicto se corta el recorrido de esa zona.
5. Las llaves ubicadas en la misma sala comparten la zona: se calcula una vez por sala distinta.
6. `depende_de[K]`: −1 o el número de J.

**Costo**: O(S + E) de preparación más la suma del tamaño de las zonas recorridas (salas y entrantes). Las zonas de
distintas salas pueden solaparse, así que el peor caso teórico es O(L·(S + E)); en las criptas publicadas y en las
sintéticas de `--bench` las llaves están detrás de pocas puertas y las zonas son pequeñas. Ver
[P-11](plan.md#preguntas-abiertas).

**Alternativas**:

- **A2, calcular la zona de cada llave por separado limpiando las marcas y revisando todas las puertas cada vez**:
  O(K·(S + E)). Se mide en `--bench`.
- **Propagar hacia adelante una etiqueta por sala** (*ninguna* / *J* / *conflicto*) hasta un punto fijo: es O(S + E)
  porque cada etiqueta cambia a lo sumo dos veces, pero **no respeta la regla**: no puede descontar las puertas
  internas. Contraejemplo: K en R; región →(K) R; R →(J) Z; Z → R abierta. La zona de R es {R, Z}, la puerta R→Z es
  interna y la regla da K → K (ciclo directo); la propagación mezcla K y J y da «sin dependencia». Rechazada.
- Componentes fuertemente conexas + DAG: las zonas son conjuntos de ancestros en el DAG, y restar las puertas internas
  sigue requiriendo comparar conjuntos; no baja el peor caso y agrega mucho código.

---

## R8. Ciclos de llaves (FR-011, FR-014, US2.2, US2.3, US2.6)

**Decisión**: `depende_de` forma un grafo funcional (cada llave apunta a lo sumo a una), así que los ciclos son
disjuntos.

1. **Detección**: arreglo `marca[K]` con 0 = sin ver, *r* = vista en el recorrido *r*, y `en_ciclo[K]`. Para cada
   llave no obtenible en orden de número se sigue `depende_de` mientras la llave no tenga marca; si se llega a una con
   la marca del recorrido actual, se recorre ese ciclo y se marca `en_ciclo`. Cada llave se visita una vez: O(K).
2. **Emisión en orden fijo**: se barre k = 0..K−1; la **primera** llave de un ciclo que aparece en el barrido es su
   llave de menor identificador; desde ella se sigue `depende_de` hasta volver y se marca el ciclo como emitido. Así
   cada ciclo empieza por su menor llave y los ciclos salen ordenados por esa llave **sin ordenar nada**: O(K).
3. Directo si `depende_de[k] == k`.

**Alternativas**: detectar con recorrido en profundidad general (innecesario con salida de grado ≤ 1); juntar los
ciclos y ordenarlos con `merge_sort` por su menor llave (O(K log K), funciona, pero el barrido lo da gratis).

---

## R9. Lectura de la ubicación de las llaves (FR-024, FR-025, FR-026, FR-028)

**Decisión**:

- **Fuente**: se usa `FuenteDatos.obtener_llaves_cripta(id)` (ya existe; misma interfaz con red y offline, FR-028).
  Se completa la validación: una entrada sin `id` o sin `sala` hoy lanza `KeyError` (que `main.py` no captura); pasa
  a `RespuestaInvalidaError` con la ruta.
- **Offline**: el paquete agrega `criptas/<id>/llaves.json` con el mismo cuerpo que el servicio. Si falta,
  `FuenteDatosOffline` ya lanza `RuntimeError("Falta el archivo para /criptas/<id>/llaves: <ruta>")`, que cubre
  US5.3.
- **Gestor**: `GestorDatos.obtener_llaves(id)` con caché en disco `datos_locales/llaves_<id>.json` validada por la
  versión de la cripta, igual que el esqueleto. FR-013 se cumple porque los datos son los mismos con caché o sin ella.
- **Presupuesto (FR-026, Principio VII)**: la verificación pide los detalles, **fija el presupuesto** y recién después
  pide versión, esqueleto y llaves. Todas pasan por `_hacer_solicitud`, que ya revisa el presupuesto antes de cada
  intento, incluidos los reintentos. Sin caché, en la cripta de referencia: detalles 1 + versión 1 + páginas 6 +
  llaves 1 = **9 de 63**. Al iniciar la partida en el mismo proceso, `preparar_partida` reutiliza los detalles, la
  versión y el esqueleto ya obtenidos (memoria del gestor y caché en disco), así que la verificación no duplica
  solicitudes.
- **Orquestación**: `verificar_cripta(cripta_id, gestor)` en `Gestor/PreparadorPartida.py`, junto a `_crear_motor`,
  porque comparte el paso de fijar el presupuesto. Devuelve el `ResultadoVerificacion` del modelo.

**Alternativas**: pedir las llaves desde el modelo (viola el Principio II); deducir las llaves del contenido de las
salas (cuesta una solicitud por cada 10 salas y no da las llaves que sueltan enemigos sin pedir el catálogo); no
guardar caché en disco (válido, cuesta una solicitud más por ejecución; se prefiere cuidar el presupuesto).

---

## R10. Integración en `main.py` y el controlador (FR-015 a FR-023)

**Decisión**:

- `main.py` agrega `--verificar ID` y `--forzar`. Prioridad: `--bench` > `--mostrar-puntajes` > **`--verificar`** >
  `--replay` > `--cargar` > `--cripta` / lista (FR-017). `--verificar` no crea el controlador ni la bitácora: llama a
  `verificar_cripta`, muestra el resultado y devuelve 0 (FR-015, FR-016).
- `ControladorPartida.nueva_partida(cripta_id, semilla=None, forzar=False)`: verifica **antes** de
  `preparar_partida` y antes de crear `BitacoraPartida` (FR-018, FR-020, FR-023). Sin `--forzar`: si es resoluble
  muestra el orden; si no, lanza `CriptaNoResoluble(resultado)`. Con `--forzar` no muestra nada (FR-021). La lista
  interactiva pasa por el mismo método (US3.3).
- `main.py` captura `CriptaNoResoluble` antes que los demás errores: `! Error: ...`, el reporte y código 1.
- `--cargar` y `--replay` no llaman a la verificación y no leen `--forzar` (FR-022).
- La verificación no usa `random`, no toca el reloj virtual ni el motor (que todavía no existe en ese momento) y no
  se anota (FR-023, SC-007).

**Alternativas**: verificar dentro de `preparar_partida` (la usa también `--replay` como fábrica: violaría FR-022);
devolver un código desde `nueva_partida` en vez de una excepción (obliga a revisar el valor en todos los llamadores).

---

## R11. Determinismo (FR-012, FR-013, SC-003)

Todo orden del resultado sale de tres fuentes fijas: el id de sala (posición en el vector), el orden de dirección
N, S, E, O, y el número de llave (posición en el índice ordenado). Las ubicaciones se ordenan por
`(llave, sala, enemigo)`. Nada depende de la semilla, del orden de las páginas, del orden de las ubicaciones ni de
la caché. SC-003 se prueba barajando salas, salidas y ubicaciones con una semilla fija en la prueba y comparando la
salida carácter por carácter.

---

## R12. Mediciones en `--bench` (FR-029, FR-030, SC-004, SC-005)

**Decisión**: `tests/bench_resolubilidad.py`, llamado desde `main.py --bench`, escribe
`resultados_bench_resolubilidad.txt` con el mismo formato que los demás bench (equipo, versión de Python, mediana y
p95). Se mide solo `verificar(...)` con los datos ya en memoria (SC-004 excluye la obtención de datos).

Criptas sintéticas generadas con semilla fija en `tests/` (Principio IV): cuadrícula de S salas con salidas en las
cuatro direcciones (E ≈ 2,5·S, como la cripta de referencia), K llaves detrás de puertas cerradas en cadena, y una
variante no resoluble con ciclos y frontera para medir el reporte.

| ID | Medición | Criterio |
|----|----------|----------|
| M1 | Cripta sintética de S = 300, E ≈ 760, K = 4 (tamaño de cripta-06), resoluble y no resoluble | p95 < 200 ms (SC-004) |
| M2 | Duplicaciones S = 300 → 600 → … → 9600, con E y K escalados, caso resoluble | cociente de medianas ≤ 2,5 en cada duplicación (SC-005) |
| M3 | Igual que M2, caso no resoluble con reporte, dependencias y ciclos | ≤ 2,5 (SC-005) |
| M4 | Alternativas A1 (recorrido completo por llave), A2 (zona por llave por separado) y A3 (búsqueda lineal del id) contra la versión elegida, con K creciente | evidencia para el Documento de Decisiones |
| M5 | Cantidad de comparaciones de `merge_sort` y de pasos de la búsqueda binaria | respalda O(M log M) y O(log K) |

Las alternativas A1 a A3 viven solo en el archivo de bench, no en el código de producción.
