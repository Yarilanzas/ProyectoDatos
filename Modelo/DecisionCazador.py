

class DecisionCazador:
    """Resultado de la decisión de un cazador en su turno (spec 003, data-model §8). No se guarda.

    ``accion`` es ``ATACAR``, ``ESPERAR`` o ``MOVER``; ``salida`` es la salida que se cruza si ``MOVER`` y ``None`` en
    los otros casos; ``costo_base`` es el costo del ataque de la Parte I, 100 al esperar y el costo de la salida al
    moverse.
    """

    ATACAR = "ATACAR"
    ESPERAR = "ESPERAR"
    MOVER = "MOVER"

    def __init__(self, accion, salida=None, costo_base=100):
        self.accion = accion
        self.salida = salida
        self.costo_base = costo_base