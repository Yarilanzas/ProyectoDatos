# bitacora de la partida (S4.11): archivo de texto de solo append, una linea por accion del jugador

from Persistencia.FormatoBinario import VersionIncompatible

MARCA = "CRIPTA-LOG"
VERSION_BITACORA = 1
SEPARADOR = "---"

def _validar_linea(texto):
    if not isinstance(texto, str):
        raise ValueError("El texto de la bitácora debe ser una cadena")

    if "\n" in texto or "\r" in texto:
        raise ValueError("El texto de la bitácora no puede tener saltos de línea")

class EncabezadoBitacora:
    __slots__ = ("cripta_id", "version_cripta", "version_catalogo", "semilla")

    def __init__(self, cripta_id, version_cripta, version_catalogo, semilla):
        self.cripta_id = cripta_id
        self.version_cripta = version_cripta
        self.version_catalogo = version_catalogo
        self.semilla = semilla


class BitacoraPartida:

    def __init__(self, ruta, cripta_id, version_cripta, version_catalogo, semilla):
        for texto in (cripta_id, version_cripta, version_catalogo):
            _validar_linea(texto)

        # el encabezado se escribe una sola vez, una bitacora nueva reemplaza a una anterior con el mismo nombre
        with open(ruta, "w", encoding="utf-8") as archivo:
            archivo.write(f"{MARCA} {VERSION_BITACORA}\n")
            archivo.write(f"cripta_id={cripta_id}\n")
            archivo.write(f"version_cripta={version_cripta}\n")
            archivo.write(f"version_catalogo={version_catalogo}\n")
            archivo.write(f"semilla={semilla}\n")
            archivo.write(f"{SEPARADOR}\n")

        # despues de eso solo se agregan lineas al final
        self._archivo = open(ruta, "a", encoding="utf-8")

    # continua una bitacora existente (partida cargada): valida el encabezado y solo agrega al final
    @classmethod
    def continuar(cls, ruta):
        encabezado, _ = leer_bitacora(ruta)  # lanza VersionIncompatible si no es valida

        bitacora = cls.__new__(cls)  # sin __init__: no se reescribe el encabezado
        bitacora._archivo = open(ruta, "a", encoding="utf-8")
        return bitacora, encabezado

    # se llama despues de que el motor aceptó la accion del jugador
    def registrar(self, nombre, argumento=""):
        if not isinstance(nombre, str):
            raise ValueError("El nombre de la acción debe ser texto")

        if not nombre or any(caracter.isspace() for caracter in nombre):
            raise ValueError( "El nombre de la acción no puede estar vacío ni contener espacios")

        _validar_linea(nombre)
        _validar_linea(argumento)

        linea = nombre if argumento == "" else f"{nombre} {argumento}"

        self._archivo.write(linea + "\n")
        self._archivo.flush()

    def cerrar(self):
        self._archivo.close()

    def __enter__(self):
        return self

    def __exit__(self, tipo, valor, traza):
        self.cerrar()


def _leer_valor(archivo, clave):
    linea = archivo.readline().rstrip("\r\n")
    prefijo = clave + "="

    if not linea.startswith(prefijo):
        raise VersionIncompatible(f"A la bitácora le falta el encabezado '{clave}'")

    valor = linea[len(prefijo):]

    if valor == "":
        raise VersionIncompatible(f"El valor de '{clave}' está vacío en la bitácora")

    return valor

# devuelve el encabezado y la lista de acciones como tuplas (nombre, argumento)
def leer_bitacora(ruta):
    with open(ruta, "r", encoding="utf-8") as archivo:
        marca, _, version = archivo.readline().rstrip("\r\n").partition(" ")
        if marca != MARCA:
            raise VersionIncompatible("El archivo no es una bitacora de Cripta")
        if version != str(VERSION_BITACORA):
            raise VersionIncompatible(
                f"La bitacora usa el formato {version} y este programa usa el {VERSION_BITACORA}")

        cripta_id = _leer_valor(archivo, "cripta_id")
        version_cripta = _leer_valor(archivo, "version_cripta")
        version_catalogo = _leer_valor(archivo, "version_catalogo")
        try:
            semilla = int(_leer_valor(archivo, "semilla"))
        except ValueError:
            raise VersionIncompatible("La semilla de la bitacora no es un numero entero")
        if archivo.readline().rstrip("\r\n") != SEPARADOR:
            raise VersionIncompatible("El encabezado de la bitacora está incompleto")

        acciones = []

        for numero_linea, linea in enumerate(archivo, start=7):
            linea = linea.rstrip("\r\n")
            if linea == "":
                continue

            nombre, separador, argumento = linea.partition(" ")

            if nombre == "" or nombre.isspace():
                raise VersionIncompatible(f"Nombre de acción vacío en la línea {numero_linea}")

            if any(caracter.isspace() for caracter in nombre):
                raise VersionIncompatible(f"Nombre de acción inválido en la línea {numero_linea}")

            if not separador:
                argumento = ""

            acciones.append((nombre, argumento))

    return EncabezadoBitacora(cripta_id, version_cripta, version_catalogo, semilla), acciones