class TrampaInstancia:
    def __init__(self, instancia, tipo):
        self.instancia= instancia
        self.tipo= tipo


    def a_json(self):
        return {
            "instancia": self.instancia,
            "tipo": self.tipo,
        }
    @classmethod
    def desde_json(cls, datos):
        return cls(
            instancia=datos["instancia"],
            tipo=datos["tipo"],


        )


