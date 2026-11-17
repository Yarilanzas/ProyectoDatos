import json
import os
import tempfile
import unittest

from Persistencia.ArchivoPartida import (guardar_partida, LectorPartida)
from Persistencia.ExportadorJSON import (guardar_partida_json, cargar_partida_json, leer_sala_json)
from Persistencia.RegistroConocimiento import RegistroConocimiento
from Persistencia.RegistroLinea import ACCION, CARGA, RETROCESO, RegistroLinea
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

    # ───────────── la línea de tiempo (spec 004, T066 y T088; FR-022, PR-10) ─────────────

    def linea(self):
        return RegistroLinea(10, [(ACCION, "mover", "E", 0, 0), (ACCION, "esperar", "", 100, 3),
                                  (RETROCESO, 1), (CARGA, 100), (ACCION, "atacar", "e-rata-1", 100, 0)])

    def test_fr022_t066_incluye_la_clave_linea_con_k_y_la_lista_de_registros(self):
        linea = self.linea()
        guardar_partida_json(self.ruta, "cripta-01", "a3f91c", "cat-2026-08-01", 12345, 250,
                             [crear_sala_prueba(1)], linea=linea)
        with open(self.ruta, encoding="utf-8") as archivo:
            datos = json.load(archivo)
        self.assertIn("linea", datos)
        self.assertEqual(datos["linea"]["k"], 10)
        self.assertEqual(len(datos["linea"]["registros"]), 5)
        self.assertEqual(datos["linea"]["registros"][0], ["ACCION", "mover", "E", 0, 0])
        self.assertEqual(datos["linea"]["registros"][2], ["RETROCESO", 1])
        self.assertEqual(datos["linea"]["registros"][3], ["CARGA", 100])

    def test_fr022_t066_los_mismos_datos_que_el_binario(self):
        linea = self.linea()
        registros = [crear_sala_prueba(1), crear_sala_prueba(2)]
        ruta_binaria = os.path.join(self.carpeta.name, "partida.bin")
        guardar_partida_json(self.ruta, "cripta-01", "a3f91c", "cat-2026-08-01", 12345, 250, registros, linea=linea)
        guardar_partida(ruta_binaria, "cripta-01", "a3f91c", "cat-2026-08-01", 12345, 250, registros, linea=linea)
        with open(self.ruta, encoding="utf-8") as archivo:
            datos = json.load(archivo)
        with LectorPartida(ruta_binaria) as lector:
            binario = lector.leer_linea()
        self.assertEqual(datos["linea"], binario.to_dict())
        self.assertEqual(RegistroLinea.from_dict(datos["linea"]), binario)
        self.assertEqual(RegistroLinea.from_dict(datos["linea"]).to_bytes(), linea.to_bytes())

    def test_fr022_t066_sin_linea_la_clave_existe_y_es_nula(self):
        self.guardar([crear_sala_prueba(1)])
        with open(self.ruta, encoding="utf-8") as archivo:
            datos = json.load(archivo)
        self.assertIn("linea", datos)
        self.assertIsNone(datos["linea"])

    def test_fr022_t066_la_linea_no_cambia_las_salas_ni_lo_demas(self):
        registros = [crear_sala_prueba(i) for i in range(1, 6)]
        self.guardar(registros)
        sin = cargar_partida_json(self.ruta)
        guardar_partida_json(self.ruta, "cripta-01", "a3f91c", "cat-2026-08-01", 12345, 250, registros, linea=self.linea())
        con = cargar_partida_json(self.ruta)
        self.assertEqual(len(con), len(sin))
        for uno, otro in zip(sin, con):
            self.assertTrue(iguales(uno, otro))
        self.assertTrue(iguales(leer_sala_json(self.ruta, 3), crear_sala_prueba(3)))

    def test_fr022_t066_el_json_es_texto_con_tildes_y_orden_canonico(self):
        linea = RegistroLinea(5, [(ACCION, "usar", "pergamino-ñandú", 0, 0)])
        guardar_partida_json(self.ruta, "cripta-01", "a3f91c", "cat-2026-08-01", 12345, 250, [crear_sala_prueba(1)], linea=linea)
        with open(self.ruta, encoding="utf-8") as archivo:
            texto = archivo.read()
        self.assertIn("pergamino-ñandú", texto)             # sin escapar, como el resto del archivo
        primero = texto
        guardar_partida_json(self.ruta, "cripta-01", "a3f91c", "cat-2026-08-01", 12345, 250, [crear_sala_prueba(1)], linea=linea)
        with open(self.ruta, encoding="utf-8") as archivo:
            self.assertEqual(archivo.read(), primero)       # el mismo estado, el mismo texto


if __name__ == "__main__":
    unittest.main()