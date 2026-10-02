
class CriptaResumen:
    def __init__(self, id, nombre, salas, dificultad):
        self.id= id
        self.nombre= nombre
        self.salas= salas
        self.dificultad= dificultad

    @classmethod  #decorador en python, hace que se pueda ejecutar el metodo
                  #sin que haya una instancia de el
    def desde_json(cls, datos):
        return cls(
            id=datos["id"],
            nombre=datos["nombre"],
            salas=datos["salas"],
            dificultad=datos["dificultad"]
        )
    #este return ejecuta el init como tal y aca se crea el objeto
