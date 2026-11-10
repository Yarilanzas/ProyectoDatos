import json
import os
import tempfile
import unittest

from Persistencia.ArchivoPartida import (guardar_partida, LectorPartida)
from Persistencia.ExportadorJSON import (guardar_partida_json, cargar_partida_json, leer_sala_json)
from Persistencia.RegistroConocimiento import RegistroConocimiento
from Persistencia.RegistroSala import RegistroSala
from tests.test_archivo_partida import (crear_sala_prueba, crear_sala_vacia, iguales)

class PruebasExportadorJSON(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.carpeta.name, "partida.json")

    def tearDown(self):
        self.carpeta.cleanup()

    def guardar(self, registros):
        guardar_partida_json(self.ruta, "cripta-01", "a3f91c", "cat-2026-08-01", 12345, 250, registros)

    def test_persistencia(self):
        originales = [crear_sala_prueba(1), crear_sala_vacia(2), crear_sala_prueba(3)]
        self.guardar(originales)
        leidas = cargar_partida_json(self.ruta)
        self.assertEqual(len(leidas), 3)
        for original, leida in zip(originales, leidas):
            self.assertTrue(iguales(original, leida))

    def test_leer_una_sala(self):
        self.guardar([crear_sala_prueba(1), crear_sala_prueba(2)])
        self.assertTrue(iguales(leer_sala_json(self.ruta, 2), crear_sala_prueba(2)))
        self.assertIsNone(leer_sala_json(self.ruta, 9))

    def test_conserva_tildes(self):
        original = RegistroSala(1, 5, [("e-1", "ent_guardián", 3, -1)], [], [], [])
        self.guardar([original])
        self.assertEqual(leer_sala_json(self.ruta, 1).enemigos[0][1], "ent_guardián")

    def test_binario_y_json_guardan_lo_mismo(self):
        registros = [crear_sala_prueba(i) for i in range(1, 30)]
        ruta_binaria = os.path.join(self.carpeta.name, "partida.bin")
        self.guardar(registros)
        guardar_partida(ruta_binaria, "cripta-01", "a3f91c", "cat-2026-08-01", 12345, 250, registros)
        with LectorPartida(ruta_binaria) as lector:
            for i in range(1, 30):
                self.assertTrue(iguales(lector.leer_sala(i), leer_sala_json(self.ruta, i)))

    def test_fr015_t073_incluye_conocimiento_con_los_mismos_campos_que_el_binario(self):
        conocimiento = RegistroConocimiento([3, 1], [(2, "O", 2), (1, "E", 1)], [(2, "O", True), (1, "E", False)])
        registros = [crear_sala_prueba(1)]
        ruta_binaria = os.path.join(self.carpeta.name, "partida.bin")
        guardar_partida_json(self.ruta, "cripta-01", "a3f91c", "cat-2026-08-01", 12345, 250, registros,
                             conocimiento=conocimiento)
        guardar_partida(ruta_binaria, "cripta-01", "a3f91c", "cat-2026-08-01", 12345, 250, registros,
                        conocimiento=conocimiento)

        with open(self.ruta, encoding="utf-8") as archivo:
            datos = json.load(archivo)
        self.assertIn("conocimiento", datos)
        self.assertEqual(set(datos["conocimiento"]), {"exploradas", "recuerdos", "puertas_reales"})
        with LectorPartida(ruta_binaria) as lector:
            binario = lector.leer_conocimiento()
        self.assertIsNotNone(binario)
        self.assertEqual(datos["conocimiento"], binario.to_dict())
        self.assertEqual(datos["conocimiento"]["exploradas"], [1, 3])

if __name__ == "__main__":
    unittest.main()