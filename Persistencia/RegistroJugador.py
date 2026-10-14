# registro del jugador dentro del archivo binario de la partida (S4.10)
# guarda solo lo que cambia durante la partida. Ataque, defensa, velocidad y vida maxima
# salen de los datos de la cripta al cargar, asi un efecto temporal (pocion de velocidad)
# no queda "pegado" para siempre despues de cargar.
# El inventario reutiliza la serializacion binaria de Inventario (persona C).

import struct

from Modelo.Inventario import Inventario

# I sala actual | i vida | I acciones del jugador | I enemigos derrotados | B llave de salida usada
FORMATO_JUGADOR = "<IiIIB"
TAMANO_JUGADOR = struct.calcsize(FORMATO_JUGADOR)

# el inventario empieza con su largo en 2 bytes big endian (asi lo escribe Inventario.to_bytes)
FORMATO_LARGO_INVENTARIO = ">H"
TAMANO_LARGO_INVENTARIO = struct.calcsize(FORMATO_LARGO_INVENTARIO)


class RegistroJugador:
    __slots__ = ("sala_id", "vida", "acciones", "derrotados", "llave_usada", "inventario")

    def __init__(self, sala_id, vida, acciones, derrotados, llave_usada, inventario):
        self.sala_id = sala_id
        self.vida = vida
        self.acciones = acciones
        self.derrotados = derrotados
        self.llave_usada = llave_usada
        self.inventario = inventario

    def to_bytes(self):
        if type(self.llave_usada) is not bool:
            raise ValueError("llave_usada debe ser True o False")

        try:
            base = struct.pack(FORMATO_JUGADOR, self.sala_id, self.vida, self.acciones,
                               self.derrotados, int(self.llave_usada))
            inventario = self.inventario.to_bytes()
        except struct.error as error:
            # struct.error no dice que campo fallo, se traduce al mismo error que usa RegistroSala
            raise ValueError(f"El jugador tiene un valor fuera de rango: {error}") from error

        return base + inventario

    @classmethod
    def from_bytes(cls, datos):
        datos = bytes(datos)

        if len(datos) < TAMANO_JUGADOR + TAMANO_LARGO_INVENTARIO:
            raise ValueError("El registro del jugador está incompleto")

        sala_id, vida, acciones, derrotados, llave = struct.unpack_from(FORMATO_JUGADOR, datos, 0)

        if llave not in (0, 1):
            raise ValueError("Valor booleano invalido en el registro del jugador")

        # el largo del inventario dice exactamente donde termina el registro
        (largo,) = struct.unpack_from(FORMATO_LARGO_INVENTARIO, datos, TAMANO_JUGADOR)
        fin = TAMANO_JUGADOR + TAMANO_LARGO_INVENTARIO + largo

        if fin != len(datos):
            raise ValueError("El registro del jugador tiene un largo inválido")

        inventario = Inventario.from_bytes(datos[TAMANO_JUGADOR:fin])
        return cls(sala_id, vida, acciones, derrotados, bool(llave), inventario)

    # para el exportador JSON (comparacion de S4.10)
    def to_dict(self):
        return {
            "sala_id": self.sala_id,
            "vida": self.vida,
            "acciones": self.acciones,
            "derrotados": self.derrotados,
            "llave_usada": self.llave_usada,
            "inventario": self.inventario.to_dict(),
        }

    @classmethod
    def from_dict(cls, datos):
        return cls(datos["sala_id"], datos["vida"], datos["acciones"], datos["derrotados"],
                   datos["llave_usada"], Inventario.from_dict(datos["inventario"]))