# Data Model: Terreno, cazador e invalidación de rutas

**Feature**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Research**: [research.md](research.md)

Todas las estructuras son propias (Principio I): listas densas indexadas por ordinal, sin `dict`/`set` como índice ni
caché, sin `heapq`, `bisect`, `collections` ni bibliotecas de grafos. `sala.salidas` es el `dict` del DTO existente:
solo se recorre, no se agrega ningún índice nuevo con `dict`.

Notación: `n` salas, `m` salidas, `R` región dentro de la cota, `E_R` sus salidas, `deg(u)` salidas de `u`.

---

## 1. Salida (existente; solo lectura en esta capacidad)

| Campo | Origen | Uso aquí |
|---|---|---|
| `sala_destino` | DTO `Salida` | Destino del paso |
| `cerrada` | DTO `Salida`; estado de la partida | «Abierta» = `not cerrada` (FR-011). Es por salida: A→B y B→A son independientes |
| `costo` | Lo agrega la capacidad de datos (FR-008) | Se lee **solo** con `motor.costo_salida(salida)`: 100 si falta (FR-002) |

**Reglas**: costo entero ≥ 1; un costo inválido rechaza la cripta (FR-001; quién valida: [P-02](plan.md#preguntas-abiertas)).
No se valida simetría: cada actor usa el costo de la salida que atraviesa (FR-003). Los costos no cambian durante la
partida (Fuera de alcance).

**Escritura de `cerrada`**: toda escritura dentro de `Modelo/` (cierre automático, `abrir_salida` y los deshacer de
ambos) pasa por un único método del motor que incrementa `version_puertas` (sección 6). La restauración de puertas al
cargar vive en `Persistencia/ConversorPartida.py`, ocurre entre ciclos y no se toca: la cubre `ciclo`.

---

## 2. GrafoCripta (nuevo; el esqueleto real que ve el cazador)

Implementa la interfaz de grafo del contrato de 001 (`ordinal`, `cantidad_salas`, `aristas`) sobre la cripta completa
y el estado **actual** de las puertas, sin niebla (FR-015). Agrega `entrantes` para la búsqueda al revés (R4); solo
`GrafoCripta` lo ofrece, y no se exige a `GrafoConocido`. **No depende de `Conocimiento`**: no usa sus `_ordinal`,
`_origen` ni `entrantes`, porque el cazador no ve lo que sabe el jugador y los motores armados a mano no lo tienen.

| Miembro | Contenido | Complejidad |
|---|---|---|
| `cantidad_salas` | n | O(1) |
| `ordinal(sala)` | Ordinal propio de `GrafoCripta`, guardado en la sala con un atributo propio que no choca con el de `Conocimiento` | O(1) |
| `aristas(sala)` | `(direccion, destino, costo)` por cada salida **abierta** de la sala; costo con `costo_salida` | O(deg) |
| `entrantes(sala)` | `(direccion, origen, costo)` por cada salida **abierta** `w→sala`, con el costo y el estado de **esa** salida | O(grado de entrada) |
| lista de entrantes | Por ordinal, pares `(origen, salida)` construidos por `GrafoCripta` | O(n + m) memoria, una vez |

**Construcción**: al iniciar o cargar la partida, recorriendo las salas del motor: asigna ordinales 0..n-1 y arma la
lista de entrantes de cada sala. O(n + m), una sola vez. El estado de la puerta se lee en vivo, nunca se copia. Los
arreglos de la búsqueda no viven aquí, sino en `EspacioBusqueda` (§4.3).

**No es estado de la partida**: no se guarda ni se revierte.

---

## 3. ColaPrioridad (nuevo; `Modelo/ColaPrioridad.py`, Persona A)

Montículo binario mínimo en una lista, con inserción perezosa (R1).

| Operación | Complejidad |
|---|---|
| `insertar(distancia, ordinal)` | O(log t) |
| `extraer_minimo()` → `(distancia, ordinal)` | O(log t) |
| `vacia()` | O(1) |
| `vaciar()` | O(1) (reasigna la lista) |

`t` = entradas en la cola, ≤ |E_R| + 1. Las entradas con distancia mayor que `dist[ordinal]` vigente se descartan al
extraerlas. El orden entre claves iguales es determinista (por ordinal) y no define la decisión (R6).

---

## 4. BusquedaRuta (nuevo; `Modelo/BusquedaRuta.py`, Persona A)

Dos operaciones sobre el mismo grafo, la misma cola y los mismos arreglos.

### 4.1 `primer_paso(grafo, origen, destino, limite=None, espacio=None)` → `Paso | None`

Búsqueda adelante acotada. Cumple las 7 obligaciones del contrato de 001. `limite` es la extensión aceptada
([P-01](plan.md#preguntas-abiertas)): ninguna sala con distancia tentativa > `limite` entra a la cola. `espacio` es
opcional (§4.3); las llamadas existentes de «ir a» no pasan ninguno de los dos. Mantiene
`primero[x]` para el desempate por menor id (R6). Devuelve `None` si no hay ruta o si toda ruta supera `limite`.

Complejidad: O((|R| + |E_R|) log |E_R|), con R = salas a distancia ≤ `limite` desde `origen` (o hasta extraer `destino`).

Es la **referencia desde cero** del cazador (FR-028) y la alternativa «recalcular siempre» de M4.

### 4.2 `campo_hacia(grafo, destino, cota, espacio=None)` → llena `dist` del espacio para las salas con distancia ≤ cota

Búsqueda al revés acotada por `grafo.entrantes` (solo `GrafoCripta`). Al terminar, para todo `u` con
`espacio.epoca[u] == espacio.epoca_actual`, `espacio.dist[u] = d(u, destino)`; cualquier otra sala se trata como ∞.

Complejidad: O((|R^rev| + |E_R^rev|) log |E_R^rev|), con R^rev = salas a distancia ≤ cota hacia `destino`.

### 4.3 EspacioBusqueda (nuevo; en `Modelo/BusquedaRuta.py`)

Los arreglos de trabajo de la búsqueda, separados del grafo porque `primer_paso` recibe grafos distintos
(`GrafoCripta`, `GrafoConocido`).

| Campo | Contenido | Complejidad |
|---|---|---|
| `dist`, `primero`, `epoca` | Listas de tamaño n (R2) | O(n) memoria al crearlo |
| `epoca_actual` | Entero; se incrementa en cada búsqueda | O(1) |
| `cola` | Una `ColaPrioridad` reutilizable | O(1) para vaciarla |

- **Sin `espacio`**: la función crea uno por llamada, de tamaño `grafo.cantidad_salas`: O(n) por llamada. Es lo que
  hace «ir a».
- **Con `espacio`**: el motor guarda uno persistente para los cazadores, creado al iniciar o cargar la partida junto con
  `GrafoCripta`. La decisión del cazador nunca paga el O(n) de creación (FR-033).
- Un espacio solo sirve para grafos con la misma `cantidad_salas` con que se creó.

---

## 5. CampoDistancias (nuevo; la reutilización del cazador)

Resultado de `campo_hacia` más la llave que dice cuándo sirve (R5). Vive en el motor; **no** es estado de la partida.

| Campo | Contenido |
|---|---|
| `ciclo` | Valor de `motor.ciclo` al calcularlo |
| `sala_jugador` | Ordinal de la sala del jugador usada |
| `version_puertas` | Valor de `motor.version_puertas` usado |
| `cota` | Cota usada: el mayor rango entre los cazadores activos y vivos en ese momento |
| `epoca` | Época del espacio persistente del motor que contiene este campo |

**Válido** si los cuatro primeros coinciden con el estado actual, la cota es ≥ el rango del cazador que decide y
ninguna otra búsqueda reutilizó el espacio (la época coincide).

**Transiciones**

```text
vacío ──(primer cazador que decide en el ciclo)──► válido
válido ──(cambio de puerta | jugador cambia de sala | cazador con rango > cota | nuevo ciclo)──► inválido
inválido ──(siguiente cazador que decide)──► válido (recalculado)
```

Las búsquedas individuales del bench o de las pruebas incrementan la época y dejan el campo inválido: nunca se lee un
campo pisado.

---

## 6. Contadores del motor (nuevos)

| Contador | Se incrementa cuando | Se guarda |
|---|---|---|
| `version_puertas` | Toda escritura de `salida.cerrada` del motor (cierre automático, abrir, deshacer de ambos). Indispensable solo dentro de un ciclo | No |
| `ciclo` | Empieza un ciclo de eventos (entre dos decisiones del jugador) | No |

Solo crecen. No son estado de la partida: no cambian la bitácora, el archivo de partida ni la línea de tiempo.
`ciclo` sostiene la validez entre ciclos: retroceder, cargar (incluida la restauración de puertas en
`Persistencia/ConversorPartida.py`, que no se toca), reproducir y reconstruir ocurren entre ciclos.

---

## 7. Cazador (Enemigo con comportamiento «cazador»)

| Campo | Origen | Regla |
|---|---|---|
| `comportamiento` | Ficha del enemigo | `"cazador"` |
| `rango` | Ficha del enemigo (capacidad de datos) | Entero ≥ 0 en unidades de costo; ausente, negativo o no entero rechaza la cripta (FR-009, [P-02](plan.md#preguntas-abiertas)) |
| `activo` | Existente (P1 §2.4) | Dormido hasta que el jugador entra a su sala (FR-034) |
| `sala`, `velocidad`, vida, etc. | Existentes | Sin cambios |

**Estados**

```text
dormido ──(el jugador entra a su sala; primera acción con costo base 100)──► activo
activo ──(vida ≤ 0)──► muerto
```

Un cazador activo que se mueve sigue activo (FR-034). Dormido o muerto no decide, no busca y no cuenta como activo en
el bench (FR-019, FR-034). Su decisión no guarda memoria propia: depende solo del estado en su turno (Key Entities de
la spec).

---

## 8. DecisionCazador (valor de retorno; no se guarda)

| Campo | Valores |
|---|---|
| `accion` | `ATACAR`, `ESPERAR`, `MOVER` |
| `salida` | La salida atravesada si `MOVER`; si no, ninguna |
| `costo_base` | Ataque de la Parte I, 100 al esperar, `costo_salida(salida)` al moverse |

**Regla** (FR-010 a FR-014), en este orden:

1. Misma sala que el jugador → `ATACAR`.
2. Sin ruta abierta, o `d > rango` → `ESPERAR`, costo 100.
3. Si no → `MOVER` a la vecina de menor id entre las `v` con `costo(u, v) + d(v, jugador) = d`; entre salidas a esa
   vecina, la de menor costo y luego N, S, E, O.

La prueba de equivalencia compara los tres campos (más la sala de destino) contra la referencia desde cero (SC-003).

---

## 9. Relaciones

```text
Motor ──tiene──► GrafoCripta (ordinales y entrantes propios; sin Conocimiento)
Motor ──tiene──► EspacioBusqueda persistente (para los cazadores)
Motor ──tiene──► CampoDistancias ──apunta a──► EspacioBusqueda del motor
Motor ──tiene──► version_puertas, ciclo
Cazador ──decide con──► CampoDistancias (juego) | primer_paso con limite (referencia)
BusquedaRuta ──usa──► ColaPrioridad
«ir a» (001) ──usa──► primer_paso sobre GrafoConocido (sin limite ni espacio: crea uno por llamada)
```
