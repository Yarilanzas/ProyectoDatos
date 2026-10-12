
# registro de una sala dentro del archivo binario de la partida (S4.10)
# guarda solo los datos modificables de cada sala

import struct


FORMATO_BASE = "<Iq"
FORMATO_CANTIDAD = "<H"
FORMATO_VIDA = "<i"
FORMATO_BOOLEANO = "<B"

TAMANO_BASE = struct.calcsize(FORMATO_BASE)
TAMANO_CANTIDAD = struct.calcsize(FORMATO_CANTIDAD)


def _validar_entero(valor, minimo, maximo, nombre):
    if type(valor) is not int or not minimo <= valor <= maximo:
        raise ValueError(f"{nombre} debe ser un entero entre {minimo} y {maximo}")


def _empaquetar_cadena(texto):
    if not isinstance(texto, str):
        raise ValueError("El texto debe ser una cadena")

    datos = texto.encode("utf-8")

    if len(datos) > 65535:
        raise ValueError("La cadena supera el limite de 65535 bytes")

    return struct.pack("<H", len(datos)) + datos


def _leer_unpack(formato, datos, posicion):
    tamano = struct.calcsize(formato)

    if posicion < 0 or posicion + tamano > len(datos):
        raise ValueError("El registro de sala está dañado")

    valores = struct.unpack_from(formato, datos, posicion)
    return valores, posicion + tamano


def _leer_cadena(datos, posicion):
    (largo,), posicion = _leer_unpack("<H", datos, posicion)
    final = posicion + largo

    if final > len(datos):
        raise ValueError("La cadena del registro está dañada")

    try:
        texto = datos[posicion:final].decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("El registro contiene texto UTF-8 invalido") from error

    return texto, final


def _validar_cantidad(elementos, nombre):
    cantidad = len(elementos)

    if cantidad > 65535:
        raise ValueError(f"Hay demasiados elementos en {nombre}")

    return cantidad


def _validar_booleano(valor, nombre):
    if type(valor) is not bool:
        raise ValueError(f"{nombre} debe ser True o False")


class RegistroSala:
    # rastro: instante de la ultima visita (-1 si nunca estuvo)
    # enemigos: lista de (instancia, tipo, vida)
    # objetos: lista de tipos de objetos en el suelo
    # trampas: lista de (instancia, tipo, armada)
    # puertas: lista de (direccion, cerrada)

    __slots__ = (
        "sala_id",
        "rastro",
        "enemigos",
        "objetos",
        "trampas",
        "puertas",
    )

    def __init__(self, sala_id, rastro, enemigos, objetos, trampas, puertas):
        self.sala_id = sala_id
        self.rastro = rastro
        self.enemigos = enemigos
        self.objetos = objetos
        self.trampas = trampas
        self.puertas = puertas

    def a_bytes(self):
        _validar_entero(self.sala_id, 0, 4294967295, "sala_id")
        _validar_entero(self.rastro, -9223372036854775808,
                        9223372036854775807, "rastro")

        partes = [
            struct.pack(FORMATO_BASE, self.sala_id, self.rastro)
        ]

        cantidad = _validar_cantidad(self.enemigos, "enemigos")
        partes.append(struct.pack(FORMATO_CANTIDAD, cantidad))

        for instancia, tipo, vida in self.enemigos:
            _validar_entero(vida, -2147483648, 2147483647, "vida")
            partes.append(_empaquetar_cadena(instancia))
            partes.append(_empaquetar_cadena(tipo))
            partes.append(struct.pack(FORMATO_VIDA, vida))

        cantidad = _validar_cantidad(self.objetos, "objetos")
        partes.append(struct.pack(FORMATO_CANTIDAD, cantidad))

        for tipo in self.objetos:
            partes.append(_empaquetar_cadena(tipo))

        cantidad = _validar_cantidad(self.trampas, "trampas")
        partes.append(struct.pack(FORMATO_CANTIDAD, cantidad))

        for instancia, tipo, armada in self.trampas:
            _validar_booleano(armada, "armada")
            partes.append(_empaquetar_cadena(instancia))
            partes.append(_empaquetar_cadena(tipo))
            partes.append(struct.pack(FORMATO_BOOLEANO, int(armada)))

        cantidad = _validar_cantidad(self.puertas, "puertas")
        partes.append(struct.pack(FORMATO_CANTIDAD, cantidad))

        for direccion, cerrada in self.puertas:
            _validar_booleano(cerrada, "cerrada")
            partes.append(_empaquetar_cadena(direccion))
            partes.append(struct.pack(FORMATO_BOOLEANO, int(cerrada)))

        return b"".join(partes)

    @classmethod
    def desde_bytes(cls, datos):
        if not isinstance(datos, (bytes, bytearray, memoryview)):
            raise ValueError("El registro debe recibirse como bytes")

        datos = bytes(datos)
        (sala_id, rastro), posicion = _leer_unpack(
            FORMATO_BASE, datos, 0
        )

        (cantidad,), posicion = _leer_unpack(
            FORMATO_CANTIDAD, datos, posicion
        )
        enemigos = []

        for _ in range(cantidad):
            instancia, posicion = _leer_cadena(datos, posicion)
            tipo, posicion = _leer_cadena(datos, posicion)
            (vida,), posicion = _leer_unpack(
                FORMATO_VIDA, datos, posicion
            )
            enemigos.append((instancia, tipo, vida))

        (cantidad,), posicion = _leer_unpack(
            FORMATO_CANTIDAD, datos, posicion
        )
        objetos = []

        for _ in range(cantidad):
            tipo, posicion = _leer_cadena(datos, posicion)
            objetos.append(tipo)

        (cantidad,), posicion = _leer_unpack(
            FORMATO_CANTIDAD, datos, posicion
        )
        trampas = []

        for _ in range(cantidad):
            instancia, posicion = _leer_cadena(datos, posicion)
            tipo, posicion = _leer_cadena(datos, posicion)
            (armada,), posicion = _leer_unpack(
                FORMATO_BOOLEANO, datos, posicion
            )

            if armada not in (0, 1):
                raise ValueError("Valor booleano invalido en una trampa")

            trampas.append((instancia, tipo, bool(armada)))

        (cantidad,), posicion = _leer_unpack(
            FORMATO_CANTIDAD, datos, posicion
        )
        puertas = []

        for _ in range(cantidad):
            direccion, posicion = _leer_cadena(datos, posicion)
            (cerrada,), posicion = _leer_unpack(
                FORMATO_BOOLEANO, datos, posicion
            )

            if cerrada not in (0, 1):
                raise ValueError("Valor booleano invalido en una puerta")

            puertas.append((direccion, bool(cerrada)))

        if posicion != len(datos):
            raise ValueError("El registro contiene bytes sobrantes")

        return cls(sala_id,rastro,enemigos,objetos,trampas,puertas,)