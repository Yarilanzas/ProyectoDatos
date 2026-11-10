# Bloque de conocimiento del archivo de partida (FR-015, PR-06). Formato: contracts/formato-partida.md.
#
#   <I  cantidad de exploradas;       por cada una, ascendente:            <I id de sala
#   <I  cantidad de puertas recordadas; por cada una, por (sala, dirección): <I sala  <H+s dirección  <B 1|2
#   <I  cantidad de puertas reales;   por cada una, por (sala, dirección):  <I sala  <H+s dirección  <B 0|1
#
# Little endian y sin relleno; textos con largo <H + UTF-8, como RegistroSala. Recuerdos: 1 = abierta,
# 2 = cerrada (lo que no figura está sin observar). Puertas reales: 0 = abierta, 1 = cerrada.
# Las avistadas no se guardan: se recalculan con FR-004.
#
# Solo el registro: ubicarlo dentro del CRPT 3 es T076, que sigue la disposición de Persona D (P-10).
# Un bloque dañado lanza ValueError, como RegistroSala; el lector del archivo lo convierte en
# VersionIncompatible (código 2, FR-016).

import struct

from Modelo.ordenamiento import elegir_algoritmo

FORMATO_ENTERO = "<I"
FORMATO_LARGO_TEXTO = "<H"
FORMATO_ESTADO = "<B"
MAXIMO_ENTERO = 4294967295

ABIERTA = 1  # mismos valores que Modelo.Conocimiento
CERRADA = 2


def _validar_id(valor, nombre):
    if type(valor) is not int or not 0 <= valor <= MAXIMO_ENTERO:
        raise ValueError(f"{nombre} debe ser un entero entre 0 y {MAXIMO_ENTERO}")


def _validar_direccion(direccion):
    if not isinstance(direccion, str):
        raise ValueError("La dirección debe ser texto")
    if len(direccion.encode("utf-8")) > 65535:
        raise ValueError("La dirección supera el límite de 65535 bytes")


def _empaquetar_texto(texto):
    datos = texto.encode("utf-8")
    return struct.pack(FORMATO_LARGO_TEXTO, len(datos)) + datos


def _leer(formato, datos, posicion):
    tamano = struct.calcsize(formato)
    if posicion + tamano > len(datos):
        raise ValueError("El bloque de conocimiento está truncado")
    return struct.unpack_from(formato, datos, posicion)[0], posicion + tamano


def _leer_texto(datos, posicion):
    largo, posicion = _leer(FORMATO_LARGO_TEXTO, datos, posicion)
    final = posicion + largo
    if final > len(datos):
        raise ValueError("El bloque de conocimiento está truncado")
    try:
        return datos[posicion:final].decode("utf-8"), final
    except UnicodeDecodeError as error:
        raise ValueError("El bloque de conocimiento contiene texto UTF-8 inválido") from error


def _ordenado(elementos, clave):
    # Ordenamiento propio del proyecto (prohibido sorted()/list.sort()).
    elementos = list(elementos)
    resultado, _ = elegir_algoritmo(len(elementos))(elementos, clave)
    return resultado


def _sin_repetidos(ordenados, clave, nombre):
    # Sobre una lista ya ordenada: dos claves iguales seguidas son un repetido. O(m).
    for indice in range(1, len(ordenados)):
        if clave(ordenados[indice - 1]) == clave(ordenados[indice]):
            raise ValueError(f"Hay {nombre} repetidas: {clave(ordenados[indice])}")


def _clave_puerta(puerta):
    return puerta[0], puerta[1]


class RegistroConocimiento:
    """Forma persistente del conocimiento: `exploradas` (ids), `recuerdos` (sala, dirección, 1|2) y
    `puertas_reales` (sala, dirección, cerrada).

    El orden canónico lo pone el registro (ids ascendentes; puertas por (sala, dirección)), así que el
    mismo estado da los mismos bytes y el mismo JSON sin importar el orden de entrada.

    Notación: x exploradas, p recuerdos, r puertas reales, m = x + p + r.

    | Operación   | Complejidad                                                    |
    |-------------|----------------------------------------------------------------|
    | to_bytes    | O(x log x + p log p + r log r) con elegir_algoritmo, más O(m)  |
    | from_bytes  | O(m) más el largo de los textos; exige el orden canónico       |
    | to_dict     | igual que to_bytes                                             |
    | from_dict   | igual que to_bytes                                             |
    """

    __slots__ = ("exploradas", "recuerdos", "puertas_reales")

    def __init__(self, exploradas, recuerdos, puertas_reales):
        self.exploradas = exploradas
        self.recuerdos = recuerdos
        self.puertas_reales = puertas_reales

    def _canonico(self):
        # Valida y devuelve las tres listas en orden canónico, sin repetidos.
        for id_sala in self.exploradas:
            _validar_id(id_sala, "El id de una sala explorada")
        for id_sala, direccion, estado in self.recuerdos:
            _validar_id(id_sala, "El id de la sala de un recuerdo")
            _validar_direccion(direccion)
            if type(estado) is not int or estado not in (ABIERTA, CERRADA):
                raise ValueError("El recuerdo de una puerta debe ser 1 (abierta) o 2 (cerrada)")
        for id_sala, direccion, cerrada in self.puertas_reales:
            _validar_id(id_sala, "El id de la sala de una puerta real")
            _validar_direccion(direccion)
            if type(cerrada) is not bool:
                raise ValueError("El estado de una puerta real debe ser True o False")

        exploradas = _ordenado(self.exploradas, lambda id_sala: id_sala)
        recuerdos = _ordenado([tuple(r) for r in self.recuerdos], _clave_puerta)
        reales = _ordenado([tuple(p) for p in self.puertas_reales], _clave_puerta)

        _sin_repetidos(exploradas, lambda id_sala: id_sala, "salas exploradas")
        _sin_repetidos(recuerdos, _clave_puerta, "puertas recordadas")
        _sin_repetidos(reales, _clave_puerta, "puertas reales")
        return exploradas, recuerdos, reales

    def to_bytes(self):
        exploradas, recuerdos, reales = self._canonico()

        partes = [struct.pack(FORMATO_ENTERO, len(exploradas))]
        for id_sala in exploradas:
            partes.append(struct.pack(FORMATO_ENTERO, id_sala))

        partes.append(struct.pack(FORMATO_ENTERO, len(recuerdos)))
        for id_sala, direccion, estado in recuerdos:
            partes.append(struct.pack(FORMATO_ENTERO, id_sala))
            partes.append(_empaquetar_texto(direccion))
            partes.append(struct.pack(FORMATO_ESTADO, estado))

        partes.append(struct.pack(FORMATO_ENTERO, len(reales)))
        for id_sala, direccion, cerrada in reales:
            partes.append(struct.pack(FORMATO_ENTERO, id_sala))
            partes.append(_empaquetar_texto(direccion))
            partes.append(struct.pack(FORMATO_ESTADO, int(cerrada)))

        return b"".join(partes)

    @classmethod
    def from_bytes(cls, datos):
        if not isinstance(datos, (bytes, bytearray, memoryview)):
            raise ValueError("El bloque de conocimiento debe recibirse como bytes")
        datos = bytes(datos)

        cantidad, posicion = _leer(FORMATO_ENTERO, datos, 0)
        exploradas = []
        for _ in range(cantidad):
            id_sala, posicion = _leer(FORMATO_ENTERO, datos, posicion)
            if exploradas and id_sala <= exploradas[-1]:
                raise ValueError("Las salas exploradas no están en orden ascendente")
            exploradas.append(id_sala)

        recuerdos, posicion = cls._leer_puertas(datos, posicion, (ABIERTA, CERRADA), "recuerdo")
        reales, posicion = cls._leer_puertas(datos, posicion, (0, 1), "puerta real")

        if posicion != len(datos):
            raise ValueError("El bloque de conocimiento contiene bytes sobrantes")

        return cls(exploradas, recuerdos, [(s, d, bool(c)) for s, d, c in reales])

    @staticmethod
    def _leer_puertas(datos, posicion, validos, nombre):
        cantidad, posicion = _leer(FORMATO_ENTERO, datos, posicion)
        puertas = []
        for _ in range(cantidad):
            id_sala, posicion = _leer(FORMATO_ENTERO, datos, posicion)
            direccion, posicion = _leer_texto(datos, posicion)
            estado, posicion = _leer(FORMATO_ESTADO, datos, posicion)
            if estado not in validos:
                raise ValueError(f"Valor inválido en un {nombre}: {estado}")
            if puertas and (id_sala, direccion) <= _clave_puerta(puertas[-1]):
                raise ValueError(f"Las entradas de {nombre} no están en orden (sala, dirección)")
            puertas.append((id_sala, direccion, estado))
        return puertas, posicion

    def to_dict(self):
        # Los mismos tres campos que el binario, para que la comparación binario frente a JSON sea de los
        # mismos datos (contracts/formato-partida.md, ExportadorJSON).
        exploradas, recuerdos, reales = self._canonico()
        return {
            "exploradas": exploradas,
            "recuerdos": [list(recuerdo) for recuerdo in recuerdos],
            "puertas_reales": [list(puerta) for puerta in reales],
        }

    @classmethod
    def from_dict(cls, datos):
        try:
            registro = cls(list(datos["exploradas"]),
                           [tuple(recuerdo) for recuerdo in datos["recuerdos"]],
                           [tuple(puerta) for puerta in datos["puertas_reales"]])
            for entrada in registro.recuerdos + registro.puertas_reales:
                if len(entrada) != 3:
                    raise ValueError("Cada puerta debe tener sala, dirección y estado")
        except (KeyError, TypeError) as error:
            raise ValueError(f"El conocimiento en JSON está incompleto: {error}") from error

        exploradas, recuerdos, reales = registro._canonico()
        return cls(exploradas, recuerdos, reales)
