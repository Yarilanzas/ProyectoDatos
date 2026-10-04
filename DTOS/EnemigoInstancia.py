class EnemigoInstancia:
    def __init__(self, instancia, tipo, vida):
        self.instancia= instancia
        self.tipo= tipo
        self.vida= vida



    @classmethod
    def desde_json(cls, datos):
        return cls(
            instancia=datos["instancia"],
            tipo=datos["tipo"],
            vida=datos["vida"]

        )


