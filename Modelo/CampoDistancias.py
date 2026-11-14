class CampoDistancias:
    """Llave que dice cuándo sirve el resultado de ``campo_hacia`` guardado en el espacio del motor (spec 003,
    data-model §5). No es estado de la partida: no se guarda.

    El campo en sí (las distancias hacia la sala del jugador) vive en el ``EspacioBusqueda`` persistente del motor; esta
    clase solo recuerda con qué valores se calculó: ``ciclo`` y ``version_puertas`` del motor, el ordinal de la sala del
    jugador, la ``cota`` usada y la ``epoca`` del espacio. Sirve para decidir a un cazador de rango ``rango`` si los
    cuatro primeros coinciden con el estado actual, la cota es al menos ese rango y ninguna otra búsqueda reutilizó el
    espacio (la época coincide). Todas sus operaciones son O(1).
    """

    def __init__(self, ciclo, sala_jugador, version_puertas, cota, epoca):
        self.ciclo = ciclo
        self.sala_jugador = sala_jugador
        self.version_puertas = version_puertas
        self.cota = cota
        self.epoca = epoca

    def sirve(self, ciclo, sala_jugador, version_puertas, rango, epoca):
        return (self.ciclo == ciclo and self.sala_jugador == sala_jugador
                and self.version_puertas == version_puertas and self.cota >= rango and self.epoca == epoca)