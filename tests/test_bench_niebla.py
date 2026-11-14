# Pruebas de la base de la medición de la Fase 6 (T100). T108 agrega aquí la prueba rápida de M1 a M6.
# Atiende: SC-006, PR-15, Principio VIII. Sin red y sin vista.

import contextlib
import io
import os
import platform
import re
import sys
import tempfile
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from tests import bench_niebla
from tests.bench_niebla import encabezado, escribir_resultados, mediana, medir_ms


def _archivos_py():
    for carpeta, subcarpetas, archivos in os.walk(RAIZ):
        subcarpetas[:] = [s for s in subcarpetas if s not in (".git", ".venv", "venv", "__pycache__", ".idea")]
        for nombre in archivos:
            if nombre.endswith(".py"):
                yield os.path.join(carpeta, nombre)


class RelojFalso:
    # Devuelve en orden los instantes (en ns) que se le dan.
    def __init__(self, instantes):
        self._instantes = list(instantes)
        self._siguiente = 0

    def __call__(self):
        valor = self._instantes[self._siguiente]
        self._siguiente += 1
        return valor


class TestMediana(unittest.TestCase):
    def test_pr15_mediana_impar(self):
        self.assertEqual(mediana([3, 1, 2]), 2)
        self.assertEqual(mediana([5]), 5)
        self.assertEqual(mediana([9, 1, 7, 3, 5]), 5)

    def test_pr15_mediana_par_promedia_los_dos_centrales(self):
        self.assertEqual(mediana([4, 1, 3, 2]), 2.5)
        self.assertEqual(mediana([10.0, 2.0]), 6.0)

    def test_pr15_mediana_con_repetidos_y_no_cambia_la_entrada(self):
        valores = [2, 2, 9, 1, 2]
        self.assertEqual(mediana(valores), 2)
        self.assertEqual(valores, [2, 2, 9, 1, 2])

    def test_pr15_mediana_vacia_es_error(self):
        with self.assertRaises(ValueError):
            mediana([])

    def test_pr15_medir_ms_es_la_mediana_de_las_repeticiones(self):
        # tres repeticiones de 4 ms, 1 ms y 2 ms: la mediana es 2 ms
        reloj = RelojFalso([0, 4_000_000, 10_000_000, 11_000_000, 20_000_000, 22_000_000])
        llamadas = []
        resultado = medir_ms(lambda: llamadas.append(1), repeticiones=3, reloj=reloj)
        self.assertEqual(len(llamadas), 3)
        self.assertEqual(resultado, 2.0)


class TestLimite(unittest.TestCase):
    def test_pr15_limite_paso_ir_a_es_5_ms(self):
        self.assertEqual(bench_niebla.LIMITE_PASO_IR_A_MS, 5)

    def test_pr15_limite_se_escribe_una_sola_vez_y_cita_6_1(self):
        asignacion = re.compile(r"^\s*LIMITE_PASO_IR_A_MS\s*=", re.MULTILINE)
        lugares = []
        for ruta in _archivos_py():
            with open(ruta, encoding="utf-8") as archivo:
                codigo = archivo.read()
            for _ in asignacion.finditer(codigo):
                lugares.append(os.path.relpath(ruta, RAIZ))
        self.assertEqual(lugares, [os.path.join("tests", "bench_niebla.py")])

        with open(bench_niebla.__file__, encoding="utf-8") as archivo:
            codigo = archivo.read()
        linea = codigo[asignacion.search(codigo).start():].split("\n", 1)[0]
        comentario_previo = codigo[:asignacion.search(codigo).start()].rsplit("\n\n", 1)[-1]
        texto = comentario_previo + linea
        self.assertIn("§6.1", texto)
        self.assertIn("enmienda", texto)


class TestResultados(unittest.TestCase):
    def test_pr15_encabezado_tiene_equipo_version_de_python_y_aviso_provisional(self):
        texto = "\n".join(encabezado())
        self.assertIn(platform.python_version(), texto)
        self.assertIn(platform.platform(), texto)
        self.assertIn("provisional", texto)

    def test_pr15_escribe_resultados_con_encabezado(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = os.path.join(carpeta, bench_niebla.ARCHIVO_RESULTADOS)
            with contextlib.redirect_stdout(io.StringIO()):
                escribir_resultados(["M0 fila de prueba"], ruta)
            self.assertTrue(os.path.exists(ruta))
            with open(ruta, encoding="utf-8") as archivo:
                texto = archivo.read()
        self.assertIn(platform.python_version(), texto)
        self.assertIn("M0 fila de prueba", texto)
        self.assertTrue(texto.endswith("\n"))

    def test_pr15_nombre_del_archivo(self):
        self.assertEqual(bench_niebla.ARCHIVO_RESULTADOS, "resultados_bench_niebla.txt")


class TestPrincipioI(unittest.TestCase):
    def test_pr15_sin_ordenamientos_ni_estadisticas_de_biblioteca(self):
        for modulo in ("bench_niebla.py", "mapas_sinteticos.py"):
            with open(os.path.join(RAIZ, "tests", modulo), encoding="utf-8") as archivo:
                codigo = archivo.read()
            with self.subTest(modulo=modulo):
                for marca in ("sorted(", ".sort(", "statistics", "heapq", "bisect", "collections"):
                    self.assertNotIn(marca, codigo)


if __name__ == "__main__":
    unittest.main()
