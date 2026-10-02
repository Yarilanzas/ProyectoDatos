class CriptaDetalles:
    def __init__(self, id, version, salas_total, sala_inicial,sala_salida, llave_salida,presupuesto_solicitudes,inventario_max ):
        self.id= id
        self.version= version
        self.salas_total= salas_total
        self.sala_inicial= sala_inicial
        self.sala_salida = sala_salida
        self.llave_salida = llave_salida
        self.presupuesto_solicitudes = presupuesto_solicitudes
        self.inventario_max = inventario_max

    @classmethod  #decorador en python, hace que se pueda ejecutar el metodo
                  #sin que haya una instancia de el
    def desde_json(cls, datos):
        return cls(
            id=datos["id"],
            version=datos["version"],
            salas=datos["salas"],
            dificultad=datos["dificultad"]
        )
    #este return ejecuta el init como tal y aca se crea el objeto

    #id, version, salas_total, sala_inicial,
    # sala_salida, llave_salida, presupuesto_solicitudes, inventario_max