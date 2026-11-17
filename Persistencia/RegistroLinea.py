# Bloque de la línea de tiempo del archivo de partida (spec 004, T081; FR-022, FR-024, FR-031; PR-10).
# Formato: specs/004-linea-de-tiempo/contracts/formato-partida.md, sección «Bloque de la línea».
#
#   <I  K                       acciones máximas entre puntos de control, K >= 1
#   <I  cantidad de registros
#       por cada registro, en orden cronológico:
#   <B    tipo                  1 = ACCION, 2 = RETROCESO, 3 = CARGA
#         ACCION:     <H largo del nombre + nombre (UTF-8), <H largo del argumento + argumento,
#                     <Q reloj y <Q secuencia de la decisión previa a la acción (el sello)
#         RETROCESO:  <I acciones vigentes que quedan tras el retroceso
#         CARGA:      <Q reloj del motor cargado
#
# Little endian y sin relleno. Es el guion completo de los comandos aceptados (con los retrocesos y las cargas): los puntos
# de control no se guardan, se reconstruyen al cargar reproduciendo el guion. No lleva número de versión propio: lo cubre
# `VERSION_FORMATO` del encabezado del archivo.
#
# Un registro es una tupla: (ACCION, nombre, argumento, reloj, secuencia), (RETROCESO, acciones_vigentes) o
# (CARGA, reloj_cargado). `from_bytes` y `from_dict` lanzan `VersionIncompatible` ante cualquier daño (código 2, FR-024);
# `to_bytes` y `to_dict` lanzan `ValueError` si el registro se armó mal, como el resto de los registros del archivo.
#
# Complejidad (n registros, B bytes): to_bytes, from_bytes, to_dict y from_dict O(n + B) en tiempo y memoria. Sin dict ni
# set: solo listas y tuplas.

import struct

from Persistencia.FormatoBinario import VersionIncompatible

ACCION = 1
RETROCESO = 2
CARGA = 3

NOMBRES_TIPO = ("ACCION", "RETROCESO", "CARGA")  # el nombre del tipo `t` es NOMBRES_TIPO[t - 1] (solo para el JSON)

FORMATO_CABECERA = "<II"
FORMATO_TIPO = "<B"
FORMATO_LARGO_TEXTO = "<H"
FORMATO_SELLO = "<QQ"
FORMATO_QUEDAN = "<I"
FORMATO_RELOJ = "<Q"

MAXIMO_U32 = 4294967295
MAXIMO_U64 = 18446744073709551615
MAXIMO_TEXTO = 65535
NOMBRE_RETROCESO = "retroceder"  # nunca es una acción del guion: tiene su propio tipo

MENSAJE = "El bloque de la línea de tiempo"


def _es_entero(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


def _problema_texto(texto, que, es_nombre):
    """Motivo por el que `texto` no sirve como nombre o argumento de una acción, o None. Las mismas reglas de la bitácora:
    nada de saltos de línea; el nombre, además, sin espacios y sin empezar por `#` ni `@`."""
    if not isinstance(texto, str):
        return f"{que} debe ser texto"
    if "\n" in texto or "\r" in texto:
        return f"{que} no puede tener saltos de línea"
    if len(texto.encode("utf-8", "surrogatepass")) > MAXIMO_TEXTO:
        return f"{que} supera el límite de {MAXIMO_TEXTO} bytes"
    if es_nombre:
        if texto == "":
            return f"{que} no puede estar vacío"
        if any(caracter.isspace() for caracter in texto):
            return f"{que} no puede contener espacios"
        if texto[0] == "#" or texto[0] == "@":
            return f"{que} no puede empezar con '#' ni con '@'"
        if texto == NOMBRE_RETROCESO:
            return f"«{NOMBRE_RETROCESO}» no es una acción del guion: tiene su propio tipo"
    return None


def _problema_entero(valor, que, maximo):
    if not _es_entero(valor) or not 0 <= valor <= maximo:
        return f"{que} debe ser un entero entre 0 y {maximo}"
    return None


def _problema(k, registros):
    """El primer defecto del contenido (un texto) o None si el registro es válido. Es la única validación: la usan
    `to_bytes`, `to_dict`, `from_bytes` y `from_dict`. O(n)."""
    if not _es_entero(k) or not 1 <= k <= MAXIMO_U32:
        return f"K debe ser un entero entre 1 y {MAXIMO_U32}"
    if len(registros) > MAXIMO_U32:
        return "hay demasiados registros"

    vigentes = 0
    for posicion in range(len(registros)):
        entrada = registros[posicion]
        donde = f"registro {posicion + 1}"
        if not isinstance(entrada, tuple) or len(entrada) == 0:
            return f"el {donde} debe ser una tupla"
        tipo = entrada[0]
        if not _es_entero(tipo) or tipo < ACCION or tipo > CARGA:
            return f"el {donde} tiene un tipo desconocido ({tipo!r})"

        if tipo == ACCION:
            if len(entrada) != 5:
                return f"el {donde} (ACCION) necesita nombre, argumento, reloj y secuencia"
            problema = (_problema_texto(entrada[1], f"el nombre del {donde}", True)
                        or _problema_texto(entrada[2], f"el argumento del {donde}", False)
                        or _problema_entero(entrada[3], f"el reloj del {donde}", MAXIMO_U64)
                        or _problema_entero(entrada[4], f"la secuencia del {donde}", MAXIMO_U64))
            if problema is not None:
                return problema
            vigentes += 1
        elif tipo == RETROCESO:
            if len(entrada) != 2:
                return f"el {donde} (RETROCESO) necesita las acciones que quedan"
            problema = _problema_entero(entrada[1], f"las acciones que quedan del {donde}", MAXIMO_U32)
            if problema is not None:
                return problema
            if entrada[1] > vigentes:
                return (f"el {donde} (RETROCESO) deja {entrada[1]} acciones vigentes y solo había {vigentes}")
            vigentes = entrada[1]
        else:
            if len(entrada) != 2:
                return f"el {donde} (CARGA) necesita el reloj cargado"
            problema = _problema_entero(entrada[1], f"el reloj cargado del {donde}", MAXIMO_U64)
            if problema is not None:
                return problema
    return None


def _normalizar(registros):
    """Lista de tuplas: acepta listas (por ejemplo, las que devuelve un JSON)."""
    resultado = []
    for entrada in registros:
        resultado.append(tuple(entrada) if isinstance(entrada, (list, tuple)) else entrada)
    return resultado


class _Lector:
    """Lectura secuencial de `datos` con control de límites: cualquier lectura de más es un bloque truncado."""

    def __init__(self, datos):
        self.datos = datos
        self.posicion = 0

    def leer(self, formato):
        tamano = struct.calcsize(formato)
        if self.posicion + tamano > len(self.datos):
            raise VersionIncompatible(f"{MENSAJE} está truncado")
        valores = struct.unpack_from(formato, self.datos, self.posicion)
        self.posicion += tamano
        return valores

    def leer_texto(self):
        (largo,) = self.leer(FORMATO_LARGO_TEXTO)
        if self.posicion + largo > len(self.datos):
            raise VersionIncompatible(f"{MENSAJE} está truncado")
        crudo = self.datos[self.posicion:self.posicion + largo]
        self.posicion += largo
        try:
            return crudo.decode("utf-8")
        except UnicodeDecodeError as error:
            raise VersionIncompatible(f"{MENSAJE} contiene texto UTF-8 inválido") from error


def _empaquetar_texto(texto):
    crudo = texto.encode("utf-8")
    return struct.pack(FORMATO_LARGO_TEXTO, len(crudo)) + crudo


class RegistroLinea:
    __slots__ = ("k", "registros")

    def __init__(self, k, registros):
        self.k = k
        self.registros = _normalizar(registros)

    def __eq__(self, otro):
        if not isinstance(otro, RegistroLinea):
            return NotImplemented
        return self.k == otro.k and self.registros == otro.registros

    __hash__ = None

    def __repr__(self):
        return f"RegistroLinea(k={self.k!r}, registros={len(self.registros)})"

    def _validar(self):
        problema = _problema(self.k, self.registros)
        if problema is not None:
            raise ValueError(f"{MENSAJE} no es válido: {problema}")

    def to_bytes(self):
        """Los bytes del bloque (el contenido del bloque; el campo `largo línea` lo escribe el archivo). Mismo estado,
        mismos bytes: el orden es el cronológico. O(n)."""
        self._validar()
        partes = [struct.pack(FORMATO_CABECERA, self.k, len(self.registros))]
        for entrada in self.registros:
            tipo = entrada[0]
            partes.append(struct.pack(FORMATO_TIPO, tipo))
            if tipo == ACCION:
                partes.append(_empaquetar_texto(entrada[1]))
                partes.append(_empaquetar_texto(entrada[2]))
                partes.append(struct.pack(FORMATO_SELLO, entrada[3], entrada[4]))
            elif tipo == RETROCESO:
                partes.append(struct.pack(FORMATO_QUEDAN, entrada[1]))
            else:
                partes.append(struct.pack(FORMATO_RELOJ, entrada[1]))
        return b"".join(partes)

    @classmethod
    def from_bytes(cls, datos):
        """Lee un bloque completo. `VersionIncompatible` si está truncado, tiene un tipo desconocido, K < 1, un nombre
        inválido, bytes sobrantes o un retroceso que deja más acciones vigentes de las que había. O(n + B)."""
        lector = _Lector(bytes(datos))
        k, cantidad = lector.leer(FORMATO_CABECERA)
        registros = []
        for _ in range(cantidad):
            (tipo,) = lector.leer(FORMATO_TIPO)
            if tipo == ACCION:
                nombre = lector.leer_texto()
                argumento = lector.leer_texto()
                reloj, secuencia = lector.leer(FORMATO_SELLO)
                registros.append((ACCION, nombre, argumento, reloj, secuencia))
            elif tipo == RETROCESO:
                registros.append((RETROCESO, lector.leer(FORMATO_QUEDAN)[0]))
            elif tipo == CARGA:
                registros.append((CARGA, lector.leer(FORMATO_RELOJ)[0]))
            else:
                raise VersionIncompatible(f"{MENSAJE} tiene un tipo de registro desconocido ({tipo})")
        if lector.posicion != len(lector.datos):
            raise VersionIncompatible(f"{MENSAJE} tiene bytes sobrantes")
        problema = _problema(k, registros)
        if problema is not None:
            raise VersionIncompatible(f"{MENSAJE} no es válido: {problema}")
        return cls(k, registros)

    def to_dict(self):
        """Los mismos datos que el binario, para el JSON: `{"k": K, "registros": [["ACCION", nombre, argumento, reloj,
        secuencia], ["RETROCESO", quedan], ["CARGA", reloj], ...]}`. O(n)."""
        self._validar()
        return {"k": self.k,
                "registros": [[NOMBRES_TIPO[entrada[0] - 1]] + list(entrada[1:]) for entrada in self.registros]}

    @classmethod
    def from_dict(cls, datos):
        """Inversa de `to_dict`. `VersionIncompatible` si falta algo o el contenido no es válido. O(n)."""
        try:
            k = datos["k"]
            registros = []
            for entrada in datos["registros"]:
                nombre_tipo = entrada[0]
                if nombre_tipo not in NOMBRES_TIPO:
                    raise ValueError(f"tipo desconocido ({nombre_tipo!r})")
                registros.append((NOMBRES_TIPO.index(nombre_tipo) + 1,) + tuple(entrada[1:]))
        except (KeyError, TypeError, ValueError, IndexError) as error:
            raise VersionIncompatible(f"{MENSAJE} en JSON está incompleto o dañado: {error}") from error
        problema = _problema(k, registros)
        if problema is not None:
            raise VersionIncompatible(f"{MENSAJE} no es válido: {problema}")
        return cls(k, registros)
