from DTOS.Salida import Salida
class SalaEsqueleto:
    def __init__(self, id, nombre, salidas):
        self.id= id
        self.nombre= nombre
        self.salidas= salidas

    def a_json(self):
        salidas_dict = {}
        for direccion, objeto_salida in self.salidas.items():
            if hasattr(objeto_salida, "a_json"):
                salidas_dict[direccion] = objeto_salida.a_json()
            else:
                salidas_dict[direccion] = objeto_salida

        return {
            "id": self.id,
            "nombre": self.nombre,
            "salidas": salidas_dict
        }

    @classmethod
    def desde_json(cls, datos):
        salidas_convertidas = {}
        for direccion in datos["salidas"]:
            salidas_convertidas[direccion] = Salida.desde_json(datos["salidas"][direccion])

        return cls(
            id=datos["id"],
            nombre=datos["nombre"],
            salidas=salidas_convertidas
        )



