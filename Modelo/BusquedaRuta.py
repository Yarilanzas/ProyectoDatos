# Búsqueda de ruta de menor costo (spec 003; data-model §4; research R3 y R6; Persona A, D-PEND-01).
# Principio I: estructuras propias, sin heapq, bisect, collections ni networkx.

from Modelo.ColaPrioridad import ColaPrioridad


class EspacioBusqueda:
    """Espacio de trabajo reutilizable de una búsqueda: distancias, primer paso y época por sala.

    Cada sala tiene un ordinal 0..n-1 (el que da el grafo). Una entrada de ``dist`` o ``primero`` solo vale si su
    ``epoca`` coincide con ``epoca_actual``: si no, es basura de una búsqueda anterior y se trata como infinito.
    Así empezar otra búsqueda no obliga a borrar las listas.

    | Operación     | Complejidad |
    |---------------|-------------|
    | crear         | O(n)        |
    | reiniciar     | O(1)        |
    | validar       | O(1)        |

    Un espacio solo sirve para grafos con la misma ``cantidad_salas`` con que se creó. Todo su estado cuelga de la
    instancia, nunca del módulo (contrato con la línea de tiempo, §1).
    """


    def __init__(self, cantidad_salas):
        self.cantidad_salas = cantidad_salas
        self.dist = [0] * cantidad_salas
        self.primero = [None] * cantidad_salas
        # epoca_actual empieza en 1 y las épocas en 0: al principio ninguna entrada vale
        self.epoca = [0] * cantidad_salas
        self.sala = [None] * cantidad_salas
        self.epoca_actual = 1
        self.cola = ColaPrioridad()

    def reiniciar(self):
        """Invalida todas las entradas y vacía la cola para otra búsqueda. O(1): sube la época en lugar de recorrer
        las listas."""
        self.epoca_actual += 1
        self.cola.vaciar()

    def validar(self, grafo):
        """Lanza ``ValueError`` si el grafo no tiene la misma cantidad de salas con que se creó el espacio. O(1)."""
        if grafo.cantidad_salas != self.cantidad_salas:
            raise ValueError(
                f"El espacio de búsqueda es para {self.cantidad_salas} salas y el grafo tiene "
                f"{grafo.cantidad_salas}."
            )

ORDEN_DIRECCIONES = ("N", "S", "E", "O")

def _indice_direccion(direccion):
    # Posición de la dirección en N, S, E, O. O(1): como máximo cuatro comparaciones.
    for indice in range(len(ORDEN_DIRECCIONES)):
        if ORDEN_DIRECCIONES[indice] == direccion:
            return indice
    return len(ORDEN_DIRECCIONES)

def _primero_menor(a, b):
    # a y b son (direccion, vecina) del primer paso. Gana la de vecina con menor id y, si es la misma vecina, la
    # dirección que va antes en N, S, E, O (research R6; contrato de 001, obligación 2). O(1).
    if a[1].id != b[1].id:
        return a[1].id < b[1].id
    return _indice_direccion(a[0]) < _indice_direccion(b[0])

def primer_paso(grafo, origen, destino, limite=None, espacio=None):
    """Primer paso de una ruta de costo total mínimo de ``origen`` a ``destino``, o ``None`` si no hay ruta o si toda
    ruta cuesta más que ``limite``. Contrato: specs/001-niebla-mapa-ir-a/contracts/interfaz-ruta.md (7 obligaciones).

    Búsqueda hacia adelante con cola de prioridad propia e inserción perezosa. ``limite`` es entero >= 0 o ``None``:
    nada con distancia tentativa mayor que ``limite`` entra a la cola. ``espacio`` es un ``EspacioBusqueda``
    reutilizable creado para ``grafo.cantidad_salas``; si es ``None`` se crea uno por llamada. El resultado es el
    mismo con o sin ``espacio``. Precondiciones: ``destino`` distinto de ``origen`` y costos enteros >= 1.

    Desempate: ``primero[x]`` guarda el primer paso (dirección, vecina) de la mejor ruta hasta x. Al llegar a x con la
    misma distancia por otro camino se queda el menor según ``_primero_menor``. Como todo costo es >= 1, todo
    predecesor de x con ``dist[y] + costo == dist[x]`` sale de la cola antes que x, así que ``primero[y]`` ya es el
    definitivo cuando se copia: el resultado no depende del orden de recorrido.

    | Operación        | Complejidad                                                        |
    |------------------|--------------------------------------------------------------------|
    | sin ``espacio``  | O(n) para crearlo, más lo de abajo                                 |
    | con ``espacio``  | O((|R| + |E_R|) log |E_R|)                                         |

    R son las salas con distancia <= ``limite`` desde ``origen`` (o hasta extraer ``destino``) y E_R sus salidas.
    """
    # Se importa aquí para evitar un import circular: Modelo.rutas_ir_a delega en este módulo.
    from Modelo.rutas_ir_a import Paso

    if espacio is None:
        espacio = EspacioBusqueda(grafo.cantidad_salas)
    else:
        espacio.validar(grafo)
    espacio.reiniciar()

    dist = espacio.dist
    primero = espacio.primero
    epoca = espacio.epoca
    sala = espacio.sala
    cola = espacio.cola
    vigente = espacio.epoca_actual

    ordinal_origen = grafo.ordinal(origen)
    ordinal_destino = grafo.ordinal(destino)

    dist[ordinal_origen] = 0
    primero[ordinal_origen] = None
    epoca[ordinal_origen] = vigente
    sala[ordinal_origen] = origen
    cola.insertar(0, ordinal_origen)

    while not cola.vacia():
        distancia, ordinal = cola.extraer_minimo()
        if distancia > dist[ordinal]:
            continue  # entrada vieja de la inserción perezosa: ya salió otra mejor

        if ordinal == ordinal_destino:
            direccion, vecina = primero[ordinal]
            return Paso(direccion, vecina, distancia)

        for direccion, vecina, costo in grafo.aristas(sala[ordinal]):
            nueva = distancia + costo
            if limite is not None and nueva > limite:
                continue

            # Desde el origen el primer paso es esta misma salida; desde otra sala, el que ya traía.
            candidato = primero[ordinal] if ordinal != ordinal_origen else (direccion, vecina)

            otro = grafo.ordinal(vecina)
            if epoca[otro] != vigente or nueva < dist[otro]:
                epoca[otro] = vigente
                dist[otro] = nueva
                primero[otro] = candidato
                sala[otro] = vecina
                cola.insertar(nueva, otro)
            elif nueva == dist[otro] and _primero_menor(candidato, primero[otro]):
                primero[otro] = candidato

    return None