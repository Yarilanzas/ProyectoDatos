# Ruta de «ir a»: la interfaz de una sola función de contracts/interfaz-ruta.md. FR-023, FR-024, PR-10.
#
# D-PEND-01 se resolvió con la opción A: la búsqueda se comparte con el cazador. Persona A la implementa en
# Modelo/BusquedaRuta.py, con la cola de prioridad en Modelo/ColaPrioridad.py, y este módulo solo la llama.
# Mientras ese módulo no exista, `primer_paso` lanza NotImplementedError y el controlador lo convierte en un
# aviso sin efectos (T058). Escribir su cuerpo es T062.


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


def primer_paso(grafo, origen, destino):
    """Devuelve el primer paso de una ruta de costo total mínimo de `origen` a `destino`, o None si no hay.

    Contrato: contracts/interfaz-ruta.md (7 obligaciones). `grafo` expone `ordinal`, `cantidad_salas` y
    `aristas`; en el juego es un `GrafoConocido`, que solo entrega lo transitable (FR-011, FR-023, FR-029).

    Pendiente de T062: delega en Modelo/BusquedaRuta.py de Persona A (D-PEND-01, opción A). Cumplir las
    obligaciones, la cola de prioridad a mano y la complejidad documentada son responsabilidad de ese módulo.
    """
    raise NotImplementedError("«ir a» espera Modelo/BusquedaRuta.py de Persona A (T062)")
