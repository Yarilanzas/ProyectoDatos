from DTOS.Salida import Salida
class SalaEsqueleto:
    def __init__(self, id, nombre, salidas):
        self.id= id
        self.nombre= nombre
        self.salidas= salidas


    @classmethod
    def desde_json(cls, datos):
        salidas_convertidas = {}
        for direccion in datos["salidas"]:
            salidas_convertidas[direccion] = Salida.desde_json(datos["salidas"][direccion])

        return cls(
            id=datos["id"],
            nombre=datos["nombre"],
            salidas=Salida.desde_json(datos["salas"])
        )



