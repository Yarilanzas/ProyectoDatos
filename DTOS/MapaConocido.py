# DTO del mapa que conoce el jugador (FR-018, PR-04). Cruza de modelo a vista (Principio II), así la
# vista nunca toca el mapa real (FR-012). Solo trae lo que el jugador sabe: nada de llaves, enemigos,
# trampas ni objetos (FR-010).


class SalidaConocida:
    # `estado` es el recuerdo de la puerta: "abierta", "cerrada" o "sin observar".
    def __init__(self, direccion, destino_id, costo, estado):
        self.direccion = direccion
        self.destino_id = destino_id
        self.costo = costo
        self.estado = estado


class SalaConocida:
    # Una sala explorada. `salidas` es una lista de SalidaConocida, en el orden de la sala.
    def __init__(self, id, nombre, salidas):
        self.id = id
        self.nombre = nombre
        self.salidas = salidas


class MapaConocido:
    # `exploradas`: lista de SalaConocida por id ascendente.
    # `avistadas`: lista de ids ascendentes; una sala avistada no muestra nombre ni salidas (FR-005).
    def __init__(self, exploradas, avistadas):
        self.exploradas = exploradas
        self.avistadas = avistadas
