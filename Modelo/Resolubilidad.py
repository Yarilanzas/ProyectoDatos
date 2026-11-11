# Verificación de resolubilidad de una cripta (spec 002).
#
# Modelo puro (Principio II, FR-023): sin red, archivos, consola, random ni reloj. Solo importa DTOS,
# Modelo.ordenamiento.merge_sort y Modelo.Estructuras.Queue (lo comprueba tests/test_resolubilidad.py, T016).
#
# Principio I: las estructuras del recorrido son arreglos (list creada con su tamaño y usada por índice), la cola
# propia y el índice de llaves ordenado con búsqueda binaria escrita a mano. Sin dict, set, heapq, deque, bisect,
# collections, sorted() ni .sort(). Recorrer el dict `sala.salidas` del DTO es uso auxiliar permitido.
#
# Notación (data-model.md): S salas, E salidas, K llaves distintas, L ubicaciones, C salidas cerradas con llave,
# M = L + C + 1 menciones de llaves.

from DTOS.ResultadoVerificacion import (LlaveOrdenada, LugarLlave, PuertaReporte, ResultadoVerificacion,
                                        UbicacionesLlave)
from Modelo.Estructuras import Queue
from Modelo.ordenamiento import merge_sort


def _identidad(valor):
    return valor


class IndiceLlaves:
    """Índice de llaves (R4): arreglo `ids` ordenado y sin repetidos; la posición de cada id es su número de llave.

    Ese número indexa los arreglos del recorrido (`obtenida`, `en_ronda`, `espera`...). Como `ids` está ordenado,
    el orden por número es el orden por identificador (FR-007, FR-014).

    Invariante: ids[i] < ids[i+1].

    | Operación                                          | Complejidad |
    |----------------------------------------------------|-------------|
    | construir(menciones): merge_sort + quitar repetidos| O(M log M)  |
    | numero(id_llave): búsqueda binaria; −1 si no está  | O(log K)    |
    | id_de(numero)                                      | O(1)        |
    | cantidad()                                         | O(1)        |
    """

    def __init__(self, ids):
        self.ids = ids

    @classmethod
    def construir(cls, menciones):
        """Arma el índice con las menciones de llaves (ids de ubicaciones, llaves de salidas cerradas y
        llave_salida). Las menciones None se ignoran. O(M log M)."""
        validas = []
        for id_llave in menciones:
            if id_llave is not None:
                validas.append(id_llave)
        ordenadas, _ = merge_sort(validas, _identidad)

        # los iguales quedan contiguos: un barrido lineal deja una sola copia de cada uno, O(M)
        ids = []
        for id_llave in ordenadas:
            if len(ids) == 0 or ids[len(ids) - 1] != id_llave:
                ids.append(id_llave)
        return cls(ids)

    def numero(self, id_llave):
        """Número (posición) de `id_llave`, o −1 si no está. Búsqueda binaria escrita a mano, O(log K)."""
        inicio, fin = 0, len(self.ids) - 1
        while inicio <= fin:
            medio = (inicio + fin) // 2
            actual = self.ids[medio]
            if actual == id_llave:
                return medio
            if actual < id_llave:
                inicio = medio + 1
            else:
                fin = medio - 1
        return -1

    def id_de(self, numero):
        """Identificador de la llave número `numero`. O(1)."""
        return self.ids[numero]

    def cantidad(self):
        """K, cantidad de llaves distintas. O(1)."""
        return len(self.ids)


# Orden fijo de direcciones (mismo desempate que FR-024 de la spec 001); las demás van después, por su texto.
ORDEN_DIRECCIONES = ("N", "S", "E", "O")


def _es_id_valido(valor):
    # entero no negativo; bool es subclase de int y no vale como id
    return isinstance(valor, int) and not isinstance(valor, bool) and valor >= 0


def _posicion_fija(direccion):
    for i in range(len(ORDEN_DIRECCIONES)):
        if ORDEN_DIRECCIONES[i] == direccion:
            return i
    return -1


def _texto_direccion(salida):
    return salida.direccion


class SalidaVerif:
    """Una salida dirigida (FR-005): vive solo en el arreglo de su sala de origen.

    - `destino_valido`: 0 <= destino <= max_id y la sala destino existe. Si es False no aporta alcance.
    - `num_llave`: número de la llave que pide en el índice; −1 si está abierta o cerrada sin indicar llave.
    - `id_llave`: id de la llave que pide (para el reporte); None si está abierta o no indica llave.
    El cierre automático no se guarda: no influye en la decisión (FR-004).
    """

    def __init__(self, direccion, origen, destino, destino_valido, cerrada, num_llave, id_llave):
        self.direccion = direccion
        self.origen = origen
        self.destino = destino
        self.destino_valido = destino_valido
        self.cerrada = cerrada
        self.num_llave = num_llave
        self.id_llave = id_llave


class SalaVerif:
    """Una sala del grafo: `salidas` en orden N, S, E, O y otras después por texto; `llaves` con los números de las
    llaves ubicadas aquí, incluidas las que suelta un enemigo que inicia aquí (FR-003)."""

    def __init__(self, id_sala, salidas, llaves):
        self.id = id_sala
        self.salidas = salidas
        self.llaves = llaves


class GrafoSalas:
    """Vector de salas (R1) indexado por id, de largo max_id + 1 (None = la sala no existe), y `entrantes`: por
    cada sala, las salidas que llegan a ella (solo lo usan las dependencias de US2, R7).

    Ids duplicados en el esqueleto: se conserva la primera aparición. Un id que no sea entero no negativo lanza
    ValueError con el id. Las trampas y el contenido de las salas no se reciben (FR-004).

    | Operación                                       | Complejidad       |
    |-------------------------------------------------|-------------------|
    | desde(esqueleto, indice, ubicaciones)           | O(S + E + M log K)|
    | sala(id)                                        | O(1)              |
    | existe(id)                                      | O(1)              |

    (Las «otras» direcciones, fuera de N, S, E, O, se ordenan con merge_sort; en las criptas son 0 por sala.)
    """

    def __init__(self, salas, entrantes, ubicacion_inexistente=None):
        self.salas = salas
        self.entrantes = entrantes
        # ubicacion_inexistente[k]: la llave k tiene alguna ubicación en una sala que no existe (R7: no depende de
        # ninguna). Largo K; lo llena `desde`.
        self.ubicacion_inexistente = [] if ubicacion_inexistente is None else ubicacion_inexistente

    def existe(self, id_sala):
        return _es_id_valido(id_sala) and id_sala < len(self.salas) and self.salas[id_sala] is not None

    def sala(self, id_sala):
        if not self.existe(id_sala):
            return None
        return self.salas[id_sala]

    @classmethod
    def desde(cls, esqueleto, indice, ubicaciones):
        # 1. validar ids y hallar max_id: O(S)
        max_id = -1
        for dto in esqueleto:
            if not _es_id_valido(dto.id):
                raise ValueError(f"Id de sala inválido: {dto.id!r}. Debe ser un entero no negativo.")
            if dto.id > max_id:
                max_id = dto.id

        # 2. primera aparición de cada id y salas vacías: O(S)
        primera = [None] * (max_id + 1)
        for dto in esqueleto:
            if primera[dto.id] is None:
                primera[dto.id] = dto
        salas = [None] * (max_id + 1)
        for id_sala in range(max_id + 1):
            if primera[id_sala] is not None:
                salas[id_sala] = SalaVerif(id_sala, [], [])
        grafo = cls(salas, [[] for _ in range(max_id + 1)])

        # 3. salidas por sala en orden fijo y entrantes: O(E log K) por la búsqueda de cada llave
        for id_sala in range(max_id + 1):
            dto = primera[id_sala]
            if dto is None:
                continue
            fijas = [None] * len(ORDEN_DIRECCIONES)
            otras = []
            for direccion, salida in dto.salidas.items():
                verif = cls._salida_verif(grafo, indice, id_sala, direccion, salida)
                posicion = _posicion_fija(direccion)
                if posicion >= 0:
                    fijas[posicion] = verif
                else:
                    otras.append(verif)
            otras, _ = merge_sort(otras, _texto_direccion)
            ordenadas = [verif for verif in fijas if verif is not None]
            ordenadas.extend(otras)
            salas[id_sala].salidas = ordenadas
            for verif in ordenadas:
                if verif.destino_valido:
                    grafo.entrantes[verif.destino].append(verif)

        # 4. llaves por sala (FR-003: la de un enemigo, en la sala donde inicia): O(L log K).
        # Una ubicación en una sala inexistente no aporta alcance (Edge Cases); se anota para las dependencias (R7).
        grafo.ubicacion_inexistente = [False] * indice.cantidad()
        for ubicacion in ubicaciones:
            numero = indice.numero(ubicacion.id_llave)
            if numero < 0:
                continue
            if grafo.existe(ubicacion.sala):
                salas[ubicacion.sala].llaves.append(numero)
            else:
                grafo.ubicacion_inexistente[numero] = True
        return grafo

    @staticmethod
    def _salida_verif(grafo, indice, origen, direccion, salida):
        destino = salida.sala_destino
        cerrada = bool(salida.cerrada)
        id_llave = salida.llave if cerrada else None
        num_llave = indice.numero(id_llave) if id_llave is not None else -1
        return SalidaVerif(direccion, origen, destino, grafo.existe(destino), cerrada, num_llave, id_llave)


class EstadoRecorrido:
    """Resultado del recorrido por oleadas (data-model §2.4).

    - `visitada[id]`: la sala se alcanzó (se marca al encolarla). Largo max_id + 1.
    - `obtenida[k]`: la llave número k se obtuvo. Largo K. Una llave que nunca se obtiene es no obtenible.
    - `orden`: lista de pares (número de llave, oleada) en el orden de FR-007: por oleada y, dentro de cada una, por
      número, que es el orden por identificador (R4).
    """

    def __init__(self, visitada, obtenida, orden):
        self.visitada = visitada
        self.obtenida = obtenida
        self.orden = orden


def recorrer(grafo, indice, sala_inicial):
    """Recorrido en anchura partido en oleadas (R5), desde `sala_inicial`.

    Una llave hallada en la oleada n no cuenta como obtenida hasta que la oleada termina: las puertas que la piden
    guardan su destino en `espera[k]` y esas salas se procesan en la oleada n+1 (FR-007). Las salidas abiertas, o
    cerradas con una llave ya obtenida, se atraviesan (FR-002); las llaves no se consumen. Una salida cerrada sin
    llave nunca se atraviesa. Sin solicitudes ni E/S: solo lee arreglos en memoria (FR-026).

    | Operación                                            | Complejidad              |
    |------------------------------------------------------|--------------------------|
    | marcar / consultar visitada u obtenida               | O(1)                     |
    | encolar / desencolar (Queue propia)                  | O(1)                     |
    | agregar a espera[k]                                  | O(1) amortizado          |
    | soltar espera[k] (cada entrada una vez)              | O(largo de la lista)     |
    | ordenar `nuevas` de cada oleada con merge_sort       | O(n log n); suma O(K log K) |
    | recorrido completo                                   | O(S + E + K log K)       |
    """
    visitada = [False] * len(grafo.salas)
    cantidad = indice.cantidad()
    obtenida = [False] * cantidad
    en_ronda = [False] * cantidad
    espera = [[] for _ in range(cantidad)]
    orden = []
    cola = Queue()

    def visitar(id_sala):
        # se marca al encolar: cada sala entra a la cola a lo sumo una vez
        if not visitada[id_sala]:
            visitada[id_sala] = True
            cola.enqueue(id_sala)

    if grafo.existe(sala_inicial):
        visitar(sala_inicial)

    oleada = 1
    while True:
        nuevas = []
        while not cola.is_empty():
            sala = grafo.salas[cola.dequeue()]
            for numero in sala.llaves:
                if not obtenida[numero] and not en_ronda[numero]:
                    en_ronda[numero] = True
                    nuevas.append(numero)
            for salida in sala.salidas:
                if not salida.destino_valido:
                    continue
                if not salida.cerrada or (salida.num_llave >= 0 and obtenida[salida.num_llave]):
                    visitar(salida.destino)
                elif salida.num_llave >= 0:
                    espera[salida.num_llave].append(salida.destino)
                # cerrada sin llave: nunca se atraviesa (se reporta en el barrido final, US2)

        if len(nuevas) == 0:
            break
        nuevas, _ = merge_sort(nuevas, _identidad)
        for numero in nuevas:
            obtenida[numero] = True
            en_ronda[numero] = False
            orden.append((numero, oleada))
            for destino in espera[numero]:
                visitar(destino)
            espera[numero] = []
        oleada += 1

    return EstadoRecorrido(visitada, obtenida, orden)


class ReporteBarrido:
    """Lo que el barrido final (R6) saca de lo ya calculado: `no_obtenibles` (números de llave, en orden),
    `frontera` (PuertaReporte por sala de origen y dirección) y `ubicaciones` (UbicacionesLlave por id)."""

    def __init__(self, no_obtenibles, frontera, ubicaciones):
        self.no_obtenibles = no_obtenibles
        self.frontera = frontera
        self.ubicaciones = ubicaciones


def _clave_ubicacion(item):
    # (número de llave, sala, 0 sin enemigo / 1 con enemigo, enemigo o ""): Python no compara None con texto
    return item[0], item[1], item[2], item[3]


def barrer_reporte(grafo, indice, estado, ubicaciones):
    """Barrido final del reporte (R6), sin estructuras nuevas, sobre el grafo y el estado del recorrido.

    - Llaves no obtenibles: k = 0..K−1 con `obtenida[k]` falso; el orden por número es el orden por id (FR-008).
    - Frontera bloqueada: salas visitadas en orden de id y sus salidas en el orden fijo de R1; entra la salida cerrada
      cuyo destino no está visitado (o no existe) y cuya llave no se obtuvo o no se indica (FR-009). Una puerta
      cerrada entre dos salas alcanzables no entra. Queda por sala de origen y dirección sin ordenar (FR-014).
    - Ubicaciones: las L ubicaciones se ordenan una vez con merge_sort por (número de llave, sala, enemigo) y se
      agrupan por número; se informan las de cada llave no obtenible (FR-010). Toda llave de la frontera es no
      obtenible, así que también quedan cubiertas. Sin lugares = ubicación desconocida; una sala que no existe se
      informa tal cual, con `sala_existe` falso.

    | Paso                                   | Complejidad  |
    |----------------------------------------|--------------|
    | llaves no obtenibles                   | O(K)         |
    | frontera                               | O(S + E)     |
    | ubicaciones (merge_sort y agrupación)  | O(K + L log L) |
    | total                                  | O(S + E + K + L log L) |
    """
    cantidad = indice.cantidad()
    no_obtenibles = []
    for numero in range(cantidad):
        if not estado.obtenida[numero]:
            no_obtenibles.append(numero)

    frontera = []
    for sala in grafo.salas:
        if sala is None or not estado.visitada[sala.id]:
            continue
        for salida in sala.salidas:
            if not salida.cerrada:
                continue
            if salida.destino_valido and estado.visitada[salida.destino]:
                continue  # no bloquea el acceso a ninguna sala nueva
            if salida.num_llave >= 0 and estado.obtenida[salida.num_llave]:
                continue
            frontera.append(PuertaReporte(sala.id, salida.direccion, salida.destino, salida.destino_valido,
                                          salida.id_llave))

    items = []
    for ubicacion in ubicaciones:
        numero = indice.numero(ubicacion.id_llave)
        if numero < 0:
            continue
        enemigo = ubicacion.enemigo
        items.append((numero, ubicacion.sala, 0 if enemigo is None else 1, "" if enemigo is None else enemigo,
                      ubicacion))
    items, _ = merge_sort(items, _clave_ubicacion)
    lugares = [[] for _ in range(cantidad)]
    for numero, id_sala, _, _, ubicacion in items:
        lugares[numero].append(LugarLlave(id_sala, grafo.existe(id_sala), ubicacion.enemigo))

    reporte_ubicaciones = []
    for numero in no_obtenibles:
        reporte_ubicaciones.append(UbicacionesLlave(indice.id_de(numero), lugares[numero]))
    return ReporteBarrido(no_obtenibles, frontera, reporte_ubicaciones)


# Valores de las dependencias (R7)
SIN_CALCULAR = -2   # valor_zona aún no calculado para esa sala
SIN_DEPENDENCIA = -1
_SIN_PUERTAS = -3   # todavía no apareció ninguna puerta (o ninguna ubicación) que decida


def _bloqueada(salida, estado):
    # puerta bloqueada (spec, Definiciones): cerrada, destino fuera de la región y llave no obtenida o no indicada.
    # Solo se llama con salidas de `entrantes` hacia salas no visitadas, así que el destino ya está fuera.
    return salida.cerrada and (salida.num_llave < 0 or not estado.obtenida[salida.num_llave])


def _combinar(actual, nuevo):
    # reduce dos valores a ninguna (_SIN_PUERTAS) / J / conflicto (SIN_DEPENDENCIA)
    if actual == _SIN_PUERTAS:
        return nuevo
    if nuevo == _SIN_PUERTAS or nuevo == actual:
        return actual
    return SIN_DEPENDENCIA


def _valor_zona(grafo, estado, x, sello, numero_sello, cola):
    """Valor de la zona de la sala no alcanzable `x` (R7): ninguna puerta → −1, todas piden J → J, conflicto → −1.

    Recorre hacia atrás desde `x` con la Queue, siguiendo las salidas de `entrantes` que no son puertas bloqueadas y
    cuyo origen está fuera de la región; las bloqueadas son candidatas. Al cerrar la zona se descartan las candidatas
    con origen sellado (puertas internas). Las candidatas con origen en la región nunca son internas: un conflicto
    entre ellas ya es definitivo y corta el recorrido. O(salas + entrantes de la zona).
    """
    sello[x] = numero_sello
    cola.enqueue(x)
    seguro = _SIN_PUERTAS        # combinación de las candidatas con origen en la región
    pendientes = []              # candidatas con origen fuera de la región: se deciden al cerrar la zona
    while not cola.is_empty():
        destino = cola.dequeue()
        for salida in grafo.entrantes[destino]:
            origen = salida.origen
            if _bloqueada(salida, estado):
                if estado.visitada[origen]:
                    seguro = _combinar(seguro, SIN_DEPENDENCIA if salida.num_llave < 0 else salida.num_llave)
                    if seguro == SIN_DEPENDENCIA:
                        while not cola.is_empty():  # corte al primer conflicto: se vacía la cola
                            cola.dequeue()
                        return SIN_DEPENDENCIA
                else:
                    pendientes.append(salida)
            elif not estado.visitada[origen] and sello[origen] != numero_sello:
                sello[origen] = numero_sello
                cola.enqueue(origen)

    valor = seguro
    for salida in pendientes:
        if sello[salida.origen] == numero_sello:
            continue  # puerta interna: su origen también está en la zona
        valor = _combinar(valor, SIN_DEPENDENCIA if salida.num_llave < 0 else salida.num_llave)
        if valor == SIN_DEPENDENCIA:
            return SIN_DEPENDENCIA
    return SIN_DEPENDENCIA if valor == _SIN_PUERTAS else valor


def calcular_dependencias(grafo, indice, estado):
    """`depende_de[k]` para cada llave (R7): −1 o el número de la llave J de la que depende la llave no obtenible k.

    K → J si, para cada ubicación de K, todas las puertas bloqueadas que entran a su zona piden J. Si alguna pide otra
    llave o no indica llave, si una ubicación está en una sala inexistente, si la zona no tiene puertas que entren o
    si K no tiene ubicación, K no depende de ninguna. Las llaves obtenidas quedan en −1.

    - `sello[max_id + 1]`: número de la última zona que visitó la sala; nunca se limpia, cada zona usa uno nuevo.
    - `valor_zona[max_id + 1]`: −2 sin calcular, −1 sin dependencia, j; las llaves de una misma sala comparten zona.

    | Paso                                             | Complejidad                 |
    |--------------------------------------------------|-----------------------------|
    | preparar sello, valor_zona y depende_de          | O(S + K)                    |
    | zona de una sala (recorrido hacia atrás con sello) | O(salas + entrantes de la zona) |
    | todas las dependencias                           | O(S + E + Σ zonas)          |
    | peor caso (zonas que se solapan, P-11)           | O(L·(S + E))                |
    """
    largo = len(grafo.salas)
    cantidad = indice.cantidad()
    sello = [0] * largo
    valor_zona = [SIN_CALCULAR] * largo
    acumulado = [_SIN_PUERTAS] * cantidad
    cola = Queue()
    numero_sello = 0

    for sala in grafo.salas:
        if sala is None or estado.visitada[sala.id]:
            continue  # las llaves de salas visitadas son obtenidas
        for numero in sala.llaves:
            if estado.obtenida[numero] or acumulado[numero] == SIN_DEPENDENCIA:
                continue
            if valor_zona[sala.id] == SIN_CALCULAR:
                numero_sello += 1
                valor_zona[sala.id] = _valor_zona(grafo, estado, sala.id, sello, numero_sello, cola)
            acumulado[numero] = _combinar(acumulado[numero], valor_zona[sala.id])

    depende_de = [SIN_DEPENDENCIA] * cantidad
    for numero in range(cantidad):
        if estado.obtenida[numero] or grafo.ubicacion_inexistente[numero] or acumulado[numero] == _SIN_PUERTAS:
            continue
        depende_de[numero] = acumulado[numero]
    return depende_de


def hallar_ciclos(depende_de, no_obtenible):
    """Ciclos de llaves (R8) como listas de números, cada uno empezando por su menor llave y ordenados por ella.

    `depende_de` forma un grafo funcional (cada llave apunta a lo sumo a una), así que los ciclos son disjuntos.
    Detección: por cada llave no obtenible sin marca se sigue `depende_de` marcando con el número de recorrido; si se
    vuelve a una llave del recorrido actual, desde ella se marca el ciclo en `en_ciclo`. Emisión: el barrido
    k = 0..K−1 encuentra primero la menor llave de cada ciclo; desde ella se sigue `depende_de` hasta volver, así
    salen en orden sin ordenar nada (FR-011, FR-014). Un ciclo de una sola llave es directo (K -> K).

    | Paso                                          | Complejidad |
    |-----------------------------------------------|-------------|
    | detectar ciclos (cada llave se visita una vez)| O(K)        |
    | emitir ciclos en orden (barrido por número)   | O(K)        |
    """
    cantidad = len(depende_de)
    marca = [0] * cantidad
    en_ciclo = [False] * cantidad

    recorrido = 0
    for inicio in range(cantidad):
        if not no_obtenible[inicio] or marca[inicio] != 0:
            continue
        recorrido += 1
        actual = inicio
        while actual >= 0 and no_obtenible[actual] and marca[actual] == 0:
            marca[actual] = recorrido
            actual = depende_de[actual]
        if actual >= 0 and marca[actual] == recorrido:
            llave_ciclo = actual
            while True:
                en_ciclo[llave_ciclo] = True
                llave_ciclo = depende_de[llave_ciclo]
                if llave_ciclo == actual:
                    break

    ciclos = []
    for menor in range(cantidad):
        if not en_ciclo[menor]:
            continue
        ciclo = []
        llave_ciclo = menor
        while True:
            ciclo.append(llave_ciclo)
            en_ciclo[llave_ciclo] = False  # ya emitida
            llave_ciclo = depende_de[llave_ciclo]
            if llave_ciclo == menor:
                break
        ciclos.append(ciclo)
    return ciclos


def _menciones(esqueleto, ubicaciones, llave_salida):
    # las M menciones de llaves: ubicaciones, llaves de salidas cerradas que la indican y llave_salida. O(L + E)
    menciones = []
    for ubicacion in ubicaciones:
        menciones.append(ubicacion.id_llave)
    for dto in esqueleto:
        for salida in dto.salidas.values():
            if salida.cerrada and salida.llave is not None:
                menciones.append(salida.llave)
    if llave_salida is not None:
        menciones.append(llave_salida)
    return menciones


def verificar(cripta_id, sala_inicial, sala_salida, llave_salida, esqueleto, ubicaciones):
    """Decide si la cripta es resoluble (contrato: specs/002-resolubilidad/contracts/interfaz-verificador.md).

    Resoluble si `llave_salida` se obtiene y existe una salida con origen visitado, destino `sala_salida` y llave
    `llave_salida`; con `sala_inicial == sala_salida` sigue haciendo falta esa puerta (FR-001). Si la cripta no
    declara `llave_salida` (None), es resoluble si `sala_salida` se alcanza (Edge Cases).

    Si es resoluble, `orden` lista todas las llaves obtenibles por oleada y luego por id, marcando `llave_salida`
    (FR-006, FR-007). Si no, llena `puertas_salida` con cada salida hacia `sala_salida` que pide `llave_salida` y no
    se puede cruzar, por sala de origen y dirección, y `existe_puerta_salida` (FR-009). El resto del reporte (llaves
    no obtenibles, frontera, ubicaciones, dependencias y ciclos) queda en listas vacías hasta US2.

    Pura y determinista: no modifica sus argumentos y el resultado no depende del orden de la entrada (FR-012,
    FR-013); todos los órdenes salen del id de sala, del orden fijo de direcciones y del índice de llaves (R11).
    Lanza ValueError si un id de sala no es un entero no negativo.

    | Paso                                         | Complejidad        |
    |----------------------------------------------|--------------------|
    | índice de llaves                             | O(M log M)         |
    | grafo de salas                               | O(S + E + M log K) |
    | recorrido por oleadas                        | O(S + E + K log K) |
    | veredicto y puertas hacia la salida (barrido)| O(S + E + K)       |
    | total                                        | O(S + E + M log M) |
    """
    indice = IndiceLlaves.construir(_menciones(esqueleto, ubicaciones, llave_salida))
    grafo = GrafoSalas.desde(esqueleto, indice, ubicaciones)
    estado = recorrer(grafo, indice, sala_inicial)

    num_salida = -1 if llave_salida is None else indice.numero(llave_salida)
    resoluble = False
    existe_puerta = True
    puertas = []
    if llave_salida is None:
        resoluble = grafo.existe(sala_salida) and estado.visitada[sala_salida]
    else:
        # barrido de todas las salidas en orden de sala y dirección: el reporte queda ya ordenado (FR-014)
        existe_puerta = False
        for sala in grafo.salas:
            if sala is None:
                continue
            for salida in sala.salidas:
                if salida.destino != sala_salida or salida.num_llave != num_salida:
                    continue
                existe_puerta = True
                if estado.visitada[sala.id] and estado.obtenida[num_salida]:
                    resoluble = True
                else:
                    puertas.append(PuertaReporte(sala.id, salida.direccion, salida.destino, salida.destino_valido,
                                                 salida.id_llave))

    if resoluble:
        orden = []
        for numero, oleada in estado.orden:
            orden.append(LlaveOrdenada(indice.id_de(numero), oleada, numero == num_salida))
        return ResultadoVerificacion(cripta_id, True, sala_salida, llave_salida, orden=orden)
    return ResultadoVerificacion(cripta_id, False, sala_salida, llave_salida, puertas_salida=puertas,
                                 existe_puerta_salida=existe_puerta)
