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