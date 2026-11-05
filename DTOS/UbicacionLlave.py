
class UbicacionLlave:
    def __init__(self, id_llave, sala, enemigo=None):
        self.id_llave = id_llave
        self.sala = sala
        self.enemigo = enemigo  # id del enemigo que la suelta; None si está en la sala

    @classmethod
    def desde_json(cls, datos):
        return cls(datos["id"],
                   datos["sala"],
                   datos.get("enemigo"))