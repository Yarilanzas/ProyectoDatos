class Salida:
    def __init__(self, sala_destino, cerrada, llave, cierre_automatico):
        self.sala_destino= sala_destino
        self.cerrada= cerrada
        self.llave= llave
        self.cierre_automatico= cierre_automatico


    @classmethod
    def desde_json(cls, datos):
        return cls(
            sala_destino=datos["sala"], #aqui si se exige que si o si tenga una sala, no puede quedar en none
            cerrada=datos.get("cerrada", False),
            llave=datos.get("llave"), #.get no exige que la llave esté, osea si no esta se declara como none
            cierre_automatico=datos.get("cierre_automatico")

        )


