# Grafo de la cripta completa para el cazador (spec 003, T009; data-model §2; Persona A).
# Principio I: sin dict ni set como índice, sin heapq, bisect ni collections. No usa nada de `Conocimiento`.


class GrafoCripta:
    """Grafo del esqueleto real de la cripta con el estado **actual** de las puertas, sin niebla (FR-015).

    Cumple la interfaz de grafo de contracts/interfaz-ruta.md (``ordinal``, ``cantidad_salas``, ``aristas``) y agrega
    ``entrantes`` para la búsqueda al revés (research R4). ``entrantes`` solo lo ofrece esta clase.

    No depende de ``Conocimiento``: asigna ordinales propios 0..n-1 en un atributo propio de cada sala
    (``_ordinal_cripta``, que no choca con el ``_ordinal`` de ``Conocimiento``), porque el cazador no ve lo que sabe
    el jugador y los motores armados a mano no tienen ``Conocimiento``.

    El estado de cada puerta se lee en vivo y nunca se copia. No es estado de la partida: no se guarda ni se revierte.
    Se construye una vez al recibir las salas el motor, y hay que construirlo de nuevo si cambian las salas.

    Notación: n salas, m salidas, deg(s) salidas de s, ent(s) salidas que entran a s.

    | Operación               | Complejidad |
    |-------------------------|-------------|
    | construcción            | O(n + m)    |
    | cantidad_salas          | O(1)        |
    | ordinal(sala)           | O(1)        |
    | aristas(sala)           | O(deg(s))   |
    | entrantes(sala)         | O(ent(s))   |
    | memoria                 | O(n + m)    |

    ``destino_de(salida)`` devuelve la sala destino de una salida o ``None`` (en el juego, ``motor._destino``) y
    ``costo_de(salida)`` su costo (en el juego, ``motor.costo_salida``, que vale 100 si la salida no lo declara).
    """

    def __init__(self, salas, destino_de, costo_de):
        self._destino_de = destino_de
        self._costo_de = costo_de
        self.cantidad_salas = len(salas)

        # primero todos los ordinales, porque el destino de una salida puede venir después en la lista
        for ordinal in range(len(salas)):
            salas[ordinal]._ordinal_cripta = ordinal

        # por ordinal de la sala destino: (dirección, sala origen, salida) de cada salida que llega a ella
        self._entrantes = [[] for _ in range(len(salas))]
        for sala in salas:
            for direccion, salida in sala.salidas.items():
                destino = destino_de(salida)
                if destino is not None:
                    self._entrantes[destino._ordinal_cripta].append((direccion, sala, salida))

    def ordinal(self, sala):
        """Ordinal propio de la sala, en [0, cantidad_salas). O(1)."""
        return sala._ordinal_cripta

    def aristas(self, sala):
        """``(dirección, sala destino, costo)`` por cada salida **abierta** de ``sala``, en el orden de
        ``sala.salidas``. O(deg(s))."""
        resultado = []
        for direccion, salida in sala.salidas.items():
            if salida.cerrada:
                continue
            destino = self._destino_de(salida)
            if destino is not None:
                resultado.append((direccion, destino, self._costo_de(salida)))
        return resultado

    def entrantes(self, sala):
        """``(dirección, sala origen, costo)`` por cada salida **abierta** ``w→sala``, con el costo y el estado de
        esa salida (no los de la salida de vuelta). O(ent(s))."""
        resultado = []
        for direccion, origen, salida in self._entrantes[sala._ordinal_cripta]:
            if not salida.cerrada:
                resultado.append((direccion, origen, self._costo_de(salida)))
        return resultado