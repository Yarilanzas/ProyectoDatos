class TrampaInstancia:
    def __init__(self, instancia, tipo):
        self.instancia= instancia
        self.tipo= tipo


    @classmethod
    def desde_json(cls, datos):
        return cls(
            instancia=datos["instancia"],
            tipo=datos["tipo"],


        )


