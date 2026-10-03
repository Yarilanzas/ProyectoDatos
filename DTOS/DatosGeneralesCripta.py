from DTOS.EstadisticasJugador import EstadisticasJugador

class CriptaDetalles:
    def __init__(self, id, version, salas_total, sala_inicial,sala_salida, llave_salida,presupuesto_solicitudes,inventario_max, jugador ):
        self.id= id
        self.version= version
        self.salas_total= salas_total
        self.sala_inicial= sala_inicial
        self.sala_salida = sala_salida
        self.llave_salida = llave_salida
        self.presupuesto_solicitudes = presupuesto_solicitudes
        self.inventario_max = inventario_max
        self.jugador = jugador

    @classmethod  #decorador en python, hace que se pueda ejecutar el metodo
                  #sin que haya una instancia de el
    def desde_json(cls, datos):
        return cls(
            id=datos["id"],
            version=datos["version"],
            salas_total=datos["salas_total"],
            sala_inicial=datos["sala_inicial"],
            sala_salida=datos["sala_salida"],
            llave_salida=datos["llave_salida"],
            presupuesto_solicitudes=datos["presupuesto_solicitudes"],
            inventario_max=datos["inventario_max"],
            jugador=EstadisticasJugador.desde_json(datos["jugador"]) #anidado de estaditicas jugador
        )
    #este return ejecuta el init como tal y aca se crea el objeto

    #id, version, salas_total, sala_inicial,
    # sala_salida, llave_salida, presupuesto_solicitudes, inventario_max