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
            vida=datos.get("vida") #hay algunas entidades que agarran su vida del catalogo
                                   #por lo que no siempre va a venir una vida como parametro
                                   #por eso se queda en get

        )


