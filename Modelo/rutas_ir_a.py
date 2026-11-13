# Ruta de «ir a»: la interfaz de una sola función de contracts/interfaz-ruta.md. FR-023, FR-024, PR-10.
#
# D-PEND-01 se resolvió con la opción A: la búsqueda se comparte con el cazador. Persona A la implementa en
# Modelo/BusquedaRuta.py, con la cola de prioridad en Modelo/ColaPrioridad.py, y este módulo solo la llama (T062).
# No hay import circular: Modelo/BusquedaRuta.py importa `Paso` de aquí dentro de su función.

from Modelo.BusquedaRuta import EspacioBusqueda
from Modelo.BusquedaRuta import primer_paso as primer_paso_busqueda


class Paso:
    """Primer paso de una ruta: `direccion`, sala `destino` del paso (la vecina) y `costo_total` de la
    ruta completa. Solo datos; O(1) en memoria."""

    __slots__ = ("direccion", "destino", "costo_total")

    def __init__(self, direccion, destino, costo_total):
        self.direccion = direccion
        self.destino = destino
        self.costo_total = costo_total

    def __eq__(self, otro):
        return (isinstance(otro, Paso) and self.direccion == otro.direccion
                and self.destino is otro.destino and self.costo_total == otro.costo_total)

    def __repr__(self):
        return f"Paso({self.direccion}, {getattr(self.destino, 'id', self.destino)}, {self.costo_total})"


def primer_paso(grafo, origen, destino, limite=None, espacio=None):
    """Devuelve el primer paso de una ruta de costo total mínimo de `origen` a `destino`, o None si no hay.

    Contrato: contracts/interfaz-ruta.md (7 obligaciones). `grafo` expone `ordinal`, `cantidad_salas` y
    `aristas`; en el juego es un `GrafoConocido`, que solo entrega lo transitable (FR-011, FR-023, FR-029).
    Precondición: `destino` distinto de `origen`.

    Solo delega en `Modelo.BusquedaRuta.primer_paso` de Persona A (D-PEND-01, opción A): el desempate (menor
    id de la vecina y, entre salidas a la misma vecina, N, S, E, O), la cola de prioridad a mano y la
    complejidad documentada son de ese módulo. `limite` y `espacio` son opcionales y no cambian el contrato:
    llamar con solo `(grafo, origen, destino)` da el mismo resultado. Complejidad: la de esa búsqueda.
    """
    return primer_paso_busqueda(grafo, origen, destino, limite, espacio)


class BuscadorViaje:
    """Buscador de un solo viaje, con la firma de `primer_paso`: crea un `EspacioBusqueda` al empezar el
    viaje y lo reutiliza en todos sus pasos (contracts/interfaz-ruta.md, parámetro `espacio`). El resultado
    es el mismo que sin espacio.

    Vale porque `GrafoConocido.cantidad_salas` no cambia durante la partida. Crear: O(n); cada llamada, la
    de `primer_paso` con espacio.
    """

    __slots__ = ("espacio",)

    def __init__(self, cantidad_salas):
        self.espacio = EspacioBusqueda(cantidad_salas)

    def __call__(self, grafo, origen, destino):
        return primer_paso(grafo, origen, destino, None, self.espacio)


def buscador_de_viaje(buscar, grafo):
    """Buscador para un viaje que empieza: si `buscar` es `primer_paso`, uno con su propio `EspacioBusqueda`;
    si es otro (un buscador de prueba inyectado, PR-10), el mismo `buscar`. O(n) o O(1).
    """
    if buscar is primer_paso:
        return BuscadorViaje(grafo.cantidad_salas)
    return buscar
