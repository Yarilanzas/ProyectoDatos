import os
import struct
import tempfile
import unittest

from Persistencia.ArchivoPartida import (guardar_partida, LectorPartida, TAMANO_ENTRADA, FORMATO_ENTRADA)
from Persistencia.FormatoBinario import VersionIncompatible, VERSION_FORMATO, FORMATO_PREFIJO
from Persistencia.RegistroSala import RegistroSala


def crear_sala_prueba(sala_id):
    return RegistroSala(
        sala_id=sala_id,
        rastro=sala_id * 10,
        enemigos=[("e-201", "ent_rata_gigante", 12, 340), ("e-202", "ent_rata_gigante", 7, -1)],
        objetos=[("obj-1", "itm_daga_oxidada"), ("obj-2", "itm_antorcha")],
        trampas=[("t-17", "trp_dardos", True)],
        puertas=[("E", True), ("N", False)],
    )

def crear_sala_vacia(sala_id):
    return RegistroSala(sala_id, -1, [], [], [], [])

def iguales(a, b):
    for campo in RegistroSala.__slots__:
        if getattr(a, campo) != getattr(b, campo):
            return False
    return True

class PruebasRegistroSala(unittest.TestCase):

    def test_persistencia_datos(self): # testea la serialización y deserialización con información
        original = crear_sala_prueba(7)
        self.assertTrue(iguales(original, RegistroSala.from_bytes(original.to_bytes())))

    def test_persistencia_sala_vacia(self): # evalua el caso extremo de una sala vacía
        original = crear_sala_vacia(3)
        self.assertTrue(iguales(original, RegistroSala.from_bytes(original.to_bytes())))

    def test_tipos_datos(self): # conserva tildes y booleanos
        original = RegistroSala(1, 5, [("e-1", "ent_guardián", 3, -1)], [], [("t-1", "trp_ñu", False)], [("O", True)])
        leido = RegistroSala.from_bytes(original.to_bytes())
        self.assertEqual(leido.enemigos[0][1], "ent_guardián")
        self.assertIs(leido.trampas[0][2], False)
        self.assertIs(leido.puertas[0][1], True)

class PruebasArchivoPartida(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.carpeta.name, "partida.bin")

    def tearDown(self):
        self.carpeta.cleanup()

    def guardar(self, registros):
        guardar_partida(self.ruta, "cripta-01", "a3f91c", "cat-2026-08-01", 12345, 250, registros)

    def test_encabezado_guardado(self):
        self.guardar([crear_sala_prueba(1), crear_sala_prueba(2)])
        with LectorPartida(self.ruta) as lector:
            self.assertEqual(lector.encabezado.cripta_id, "cripta-01")
            self.assertEqual(lector.encabezado.version_cripta, "a3f91c")
            self.assertEqual(lector.encabezado.version_catalogo, "cat-2026-08-01")
            self.assertEqual(lector.encabezado.semilla, 12345)
            self.assertEqual(lector.encabezado.reloj, 250)
            self.assertEqual(lector.encabezado.cantidad_salas, 2)

    def test_busqueda_desordenada(self): # busqueda desordenada de salas
        ids = [5, 1, 9, 3, 7, 2, 8, 4, 6, 10]
        self.guardar([crear_sala_prueba(i) for i in ids])
        with LectorPartida(self.ruta) as lector:
            for i in ids:
                self.assertTrue(iguales(lector.leer_sala(i), crear_sala_prueba(i)))

    def test_sala_inexistente(self):
        self.guardar([crear_sala_prueba(2), crear_sala_prueba(4)])
        with LectorPartida(self.ruta) as lector:
            self.assertIsNone(lector.leer_sala(1))
            self.assertIsNone(lector.leer_sala(3))
            self.assertIsNone(lector.leer_sala(99))

    def test_partida_sin_salas(self): # para archivos de guardado sin registros
        self.guardar([])
        with LectorPartida(self.ruta) as lector:
            self.assertIsNone(lector.leer_sala(1))

    def test_salas_repetidas(self): # llaves/IDs repetidos
        with self.assertRaises(ValueError):
            self.guardar([crear_sala_prueba(1), crear_sala_prueba(1)])

    def test_lectura_parcial(self): # leer una sala no carga el archivo completo
        self.guardar([crear_sala_prueba(i) for i in range(1, 2001)])
        tamano = os.path.getsize(self.ruta)
        with LectorPartida(self.ruta) as lector:
            antes = lector.bytes_leidos
            self.assertTrue(iguales(lector.leer_sala(1500), crear_sala_prueba(1500)))
            leido = lector.bytes_leidos - antes
        self.assertLess(leido, tamano // 100)
        # la busqueda binaria sobre 2000 entradas hace a lo sumo 11 lecturas del indice
        self.assertLessEqual(leido, 11 * TAMANO_ENTRADA + len(crear_sala_prueba(1500).to_bytes()))

    def test_version_incompatible(self):
        self.guardar([crear_sala_prueba(1)])
        with open(self.ruta, "r+b") as archivo:
            archivo.write(struct.pack(FORMATO_PREFIJO, b"CRPT", VERSION_FORMATO + 1))
        with self.assertRaises(VersionIncompatible):
            LectorPartida(self.ruta)

    def test_archivo_invalido(self):
        with open(self.ruta, "wb") as archivo:
            archivo.write(b'{"no": "soy una partida"}' + bytes(200))
        with self.assertRaises(VersionIncompatible):
            LectorPartida(self.ruta)


    def test_indice_truncado(self):
        self.guardar([crear_sala_prueba(1), crear_sala_prueba(2)])

        with open(self.ruta, "r+b") as archivo:
            archivo.seek(0, os.SEEK_END)
            archivo.truncate(
                os.path.getsize(self.ruta) - 1
            )

        with self.assertRaises(VersionIncompatible):
            LectorPartida(self.ruta)


    def test_leer_todas_salas(self):
        esperadas = [crear_sala_prueba(3), crear_sala_prueba(1),crear_sala_prueba(2),]

        self.guardar(esperadas)

        with LectorPartida(self.ruta) as lector:
            registros = lector.leer_todas_salas()

        self.assertEqual([registro.sala_id for registro in registros], [1, 2, 3])

    def test_leer_todas_rechaza_posicion_invalida(self):
        self.guardar([crear_sala_prueba(1),crear_sala_prueba(2),])

        with LectorPartida(self.ruta) as lector:
            offset = lector.encabezado.offset_indice

        # Se crea una entrada que apunta dentro del índice, en vez de apuntar a un bloque de sala
        with open(self.ruta, "r+b") as archivo:
            archivo.seek(offset)
            archivo.write(
                struct.pack(FORMATO_ENTRADA, 1, offset, 1)
            )

        with LectorPartida(self.ruta) as lector:
            with self.assertRaises(VersionIncompatible):
                lector.leer_todas_salas()

    def test_guardado_invalido_conserva_archivo_anterior(self):
        self.guardar([crear_sala_prueba(1)])

        with open(self.ruta, "rb") as archivo:
            contenido_anterior = archivo.read()

        registro_invalido = RegistroSala(2, 0, [], [("o-1", "x" * 65536)], [], [])

        with self.assertRaises(ValueError):
            self.guardar([registro_invalido])

        with open(self.ruta, "rb") as archivo:
            contenido_actual = archivo.read()

        self.assertEqual(contenido_actual, contenido_anterior)

    def test_registro_truncado(self):
        original = crear_sala_prueba(7)
        datos = original.to_bytes()

        with self.assertRaises(ValueError):
            RegistroSala.from_bytes(datos[:-1])

    def test_registro_con_bytes_sobrantes(self):
        original = crear_sala_prueba(7)
        datos = original.to_bytes() + b"\x00"

        with self.assertRaises(ValueError):
            RegistroSala.from_bytes(datos)

    def test_booleano_invalido_en_puerta(self):
        original = crear_sala_prueba(7)
        datos = bytearray(original.to_bytes())

        # El ultimo byte es el booleano de la ultima puerta.
        datos[-1] = 2

        with self.assertRaises(ValueError):
            RegistroSala.from_bytes(datos)

    def test_rechaza_vida_fuera_de_rango(self):
        sala = RegistroSala(
            1, 0,
            [("e-1", "ent_rata", 2147483648, -1)],
            [], [], []
        )

        with self.assertRaises(ValueError):
            sala.to_bytes()

    def test_rechaza_cadena_demasiado_larga(self):
        sala = RegistroSala(1, 0, [], [("o-1", "x" * 65536)], [], [])

        with self.assertRaises(ValueError):
            sala.to_bytes()