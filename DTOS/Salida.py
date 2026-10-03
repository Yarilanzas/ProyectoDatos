class Salida:
    def __init__(self, sala_destino, cerrada, llave, cierre_automatico):
        self.id= id
        self.sala_destino= sala_destino
        self.cerrada= cerrada
        self.llave= llave
        self.cierre_automatico= cierre_automatico


    @classmethod
    def desde_json(cls, datos):
        return cls(
            id=datos["id"],
            sala_destino=datos["sala"],
            cerrada=datos["cerrada"],
            llave=datos["llave"],
            cierre_automatico = datos["cierre_automatico"]

        )


