import io
import struct
import unittest

from Persistencia.FormatoBinario import (
    EncabezadoPartida, VersionIncompatible,
    TAMANO_ENCABEZADO, VERSION_FORMATO, FORMATO_PREFIJO)


def encabezado_de_prueba():
    return EncabezadoPartida("cripta-01", "a3f91c", "cat-2026-08-01",
                             semilla=12345, reloj=250, cantidad_salas=20, offset_indice=4096)


class PruebasEncabezado(unittest.TestCase):

    def test_persistencia_datos(self): # guardar y cargar correctamente (conservar los datos)
        original = encabezado_de_prueba()
        leido = EncabezadoPartida.from_bytes(original.to_bytes())
        for campo in EncabezadoPartida.__slots__:
            self.assertEqual(getattr(original, campo), getattr(leido, campo)) # getattr - obtiene el atributo como un string para compararlo con el encabezado binario

    def test_tamano_encabezado(self): #
        self.assertEqual(len(encabezado_de_prueba().to_bytes()), TAMANO_ENCABEZADO)

    def test_semilla_negativa(self):
        encabezado = encabezado_de_prueba()
        encabezado.semilla = -7
        self.assertEqual(EncabezadoPartida.from_bytes(encabezado.to_bytes()).semilla, -7)

    def test_version_incompatible(self):
        datos = bytearray(encabezado_de_prueba().to_bytes())
        datos[:struct.calcsize(FORMATO_PREFIJO)] = struct.pack(FORMATO_PREFIJO, b"CRPT", VERSION_FORMATO + 1)
        with self.assertRaises(VersionIncompatible) as contexto:
            EncabezadoPartida.from_bytes(bytes(datos))
        self.assertIn(str(VERSION_FORMATO + 1), str(contexto.exception))

    def test_archivo_invalido(self):
        with self.assertRaises(VersionIncompatible):
            EncabezadoPartida.from_bytes(b'{"json": "no soy una partida"}' + bytes(100))

    def test_archivo_incompleto(self):
        datos = encabezado_de_prueba().to_bytes()
        with self.assertRaises(VersionIncompatible):
            EncabezadoPartida.from_bytes(datos[:3])
        with self.assertRaises(VersionIncompatible):
            EncabezadoPartida.from_bytes(datos[:TAMANO_ENCABEZADO - 1])

    def test_limite_texto(self): # texto demasiado largo
        encabezado = encabezado_de_prueba()
        encabezado.cripta_id = "x" * 33
        with self.assertRaises(ValueError):
            encabezado.to_bytes()

    def test_lectura_encabezado(self): # desde el archivo lee solo el encabezado
        contenido = encabezado_de_prueba().to_bytes() + bytes(5000)
        archivo = io.BytesIO(contenido)
        leido = EncabezadoPartida.desde_archivo(archivo)
        self.assertEqual(leido.cripta_id, "cripta-01")
        self.assertEqual(archivo.tell(), TAMANO_ENCABEZADO)