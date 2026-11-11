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

    def __init__(self, salas, entrantes):
        self.salas = salas
        self.entrantes = entrantes

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
        # Una ubicación en una sala inexistente no aporta alcance (Edge Cases).
        for ubicacion in ubicaciones:
            if grafo.existe(ubicacion.sala):
                numero = indice.numero(ubicacion.id_llave)
                if numero >= 0:
                    salas[ubicacion.sala].llaves.append(numero)
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
