# formato binario propio para guardar la partida (S4.10)
# el archivo empieza con un encabezado de tamaño fijo asi se puede leer sin cargar el resto del archivo

import struct

MAGIA = b"CRPT"
VERSION_FORMATO = 2 # v2: se agrega el bloque del jugador y los enemigos/objetos guardan su instancia
LARGO_TEXTO = 32

# el prefijo (magia + version) siempre va en las mismas posiciones, asi una version nueva del formato se detecta antes de intentar leer el resto del encabezado
FORMATO_PREFIJO = "<4sH"
TAMANO_PREFIJO = struct.calcsize(FORMATO_PREFIJO)

# "<" es little endian sin relleno, el tamaño es el mismo en cualquier maquina
# 4s magia | H version del formato | 3 textos de 32 bytes (id cripta, version cripta, version catalogo)
# q semilla | Q reloj virtual | I cantidad de salas | Q posicion del indice de salas
FORMATO_ENCABEZADO = "<4sH32s32s32sqQIQ"
TAMANO_ENCABEZADO = struct.calcsize(FORMATO_ENCABEZADO)


class VersionIncompatible(Exception): # hereda el comportamiento de Exception, para representar un error específico del proyecto
    pass


def _empaquetar_texto(texto):
    if not isinstance(texto, str):
        raise ValueError("El campo del encabezado debe ser texto")

    datos = texto.encode("utf-8")

    if len(datos) > LARGO_TEXTO:
        raise ValueError(f"El texto '{texto}' no cabe en {LARGO_TEXTO} bytes")

    return datos


def _desempaquetar_texto(datos):
    try:
        return datos.rstrip(b"\x00").decode("utf-8")
    except UnicodeDecodeError as error:
        raise VersionIncompatible( "El encabezado contiene texto UTF-8 inválido" ) from error


class EncabezadoPartida:
    # el encabezado se crea una vez por archivo __slots__ evita el dict interno de la instancia
    __slots__ = ("cripta_id", "version_cripta", "version_catalogo",
                 "semilla", "reloj", "cantidad_salas", "offset_indice")

    def __init__(self, cripta_id, version_cripta, version_catalogo,
                 semilla, reloj, cantidad_salas, offset_indice):
        self.cripta_id = cripta_id
        self.version_cripta = version_cripta
        self.version_catalogo = version_catalogo
        self.semilla = semilla
        self.reloj = reloj
        self.cantidad_salas = cantidad_salas
        self.offset_indice = offset_indice

    def to_bytes(self):
        return struct.pack(
            FORMATO_ENCABEZADO,
            MAGIA,
            VERSION_FORMATO,
            _empaquetar_texto(self.cripta_id),
            _empaquetar_texto(self.version_cripta),
            _empaquetar_texto(self.version_catalogo),
            self.semilla,
            self.reloj,
            self.cantidad_salas,
            self.offset_indice,
        )

    @classmethod
    def from_bytes(cls, datos):
        if len(datos) < TAMANO_PREFIJO:
            raise VersionIncompatible("El archivo está incompleto o no es una partida de Cripta")

        magia, version = struct.unpack_from(FORMATO_PREFIJO, datos, 0)
        if magia != MAGIA:
            raise VersionIncompatible("El archivo no es una partida de Cripta")
        if version != VERSION_FORMATO:
            raise VersionIncompatible(
                f"El archivo usa el formato {version} y este programa usa el {VERSION_FORMATO}")

        if len(datos) < TAMANO_ENCABEZADO:
            raise VersionIncompatible("El encabezado del archivo está incompleto")

        (_, _, cripta_id, version_cripta, version_catalogo,
         semilla, reloj, cantidad_salas, offset_indice) = struct.unpack_from(FORMATO_ENCABEZADO, datos, 0)

        return cls(
            cripta_id=_desempaquetar_texto(cripta_id),
            version_cripta=_desempaquetar_texto(version_cripta),
            version_catalogo=_desempaquetar_texto(version_catalogo),
            semilla=semilla,
            reloj=reloj,
            cantidad_salas=cantidad_salas,
            offset_indice=offset_indice,
        )

    # lee solo los primeros bytes del archivo no carga el resto
    @classmethod
    def desde_archivo(cls, archivo):
        archivo.seek(0)
        return cls.from_bytes(archivo.read(TAMANO_ENCABEZADO))