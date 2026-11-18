# Prueba rápida de las mediciones de la línea de tiempo (spec 004, T100; SC-009, SC-007). Cada medición Mn de
# `tests/bench_linea.py` se invoca con tamaños mínimos (n <= 50, un solo K, una repetición), sin red y sin `VistaConsola`, y
# su bloque llega al archivo de resultados. **No afirma tiempos**: eso es de la corrida completa (T112). Escribe en una carpeta
# temporal: el `resultados_bench_linea.txt` de la raíz es el de la corrida completa y esta prueba no lo toca.

import os
import sys
import tempfile
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import gc

from tests import bench_linea
from tests.bench_linea import NOMBRES, estadisticas, percentil, sin_recolector

TITULOS = (("M1", "-M1: tiempo de `historia`"), ("M2", "-M2: memoria de la línea"), ("M3", "-M3: costo de una copia"),
           ("M4", "-M4: costo del recorte"), ("M5", "-M5: sobrecosto de registrar"), ("M6", "-M6: cargar"),
           ("M7", "-M7: los mismos 100 instantes"), ("M8", "-M8: `--replay --hasta`"), ("M9", "-M9: oráculo de la copia"),
           ("M10", "-M10: retroceso antes y después"))


class PruebasMedicionesRapidas(unittest.TestCase):
    """Corre todas las mediciones una vez con tamaños mínimos y revisa lo que salió."""

    @classmethod
    def setUpClass(cls):
        cls.carpeta = tempfile.TemporaryDirectory()
        cls.ruta = os.path.join(cls.carpeta.name, "resultados_bench_linea.txt")
        raiz_antes = cls.estado_del_archivo_de_la_raiz()
        cls.lineas = bench_linea.correr_bench(rapido=True, ruta=cls.ruta)
        cls.raiz_antes = raiz_antes

    @classmethod
    def tearDownClass(cls):
        cls.carpeta.cleanup()

    @staticmethod
    def estado_del_archivo_de_la_raiz():
        ruta = os.path.join(RAIZ, bench_linea.ARCHIVO_RESULTADOS)
        if not os.path.exists(ruta):
            return None
        datos = os.stat(ruta)
        return (datos.st_size, datos.st_mtime_ns)

    def bloque(self, nombre):
        titulo = [t for n, t in TITULOS if n == nombre][0]
        inicio = [i for i, linea in enumerate(self.lineas) if linea.startswith(titulo)][0]
        resultado = []
        for linea in self.lineas[inicio + 1:]:
            if linea == "":
                break
            resultado.append(linea)
        return resultado

    def test_sc009_cada_medicion_deja_su_bloque_con_al_menos_una_linea_propia(self):
        for nombre, _ in TITULOS:
            with self.subTest(medicion=nombre):
                lineas = self.bloque(nombre)
                self.assertGreater(len(lineas), 0)
                self.assertTrue(any(linea.startswith(nombre + " ") for linea in lineas), lineas)

    def test_sc009_las_diez_mediciones_estan_en_el_despachador(self):
        self.assertEqual(NOMBRES, ("M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10"))

    def test_sc007_el_archivo_trae_el_encabezado_y_todas_las_mediciones(self):
        with open(self.ruta, encoding="utf-8") as archivo:
            texto = archivo.read()
        self.assertTrue(texto.startswith("-Línea de tiempo"))
        self.assertIn("equipo: ", texto)
        self.assertIn(f"Python {sys.version.split()[0]}", texto)
        self.assertIn("MODO RÁPIDO", texto)                       # los números de esta corrida no valen como medición
        for _, titulo in TITULOS:
            self.assertIn(titulo, texto)
        self.assertEqual(texto.splitlines(), self.lineas)

    def test_sc007_el_k_por_omision_figura_en_el_encabezado(self):
        from Modelo.LineaTiempo import K_POR_OMISION
        self.assertTrue(any(f"K por omisión del programa: {K_POR_OMISION}" in linea for linea in self.lineas))

    def test_m1_con_tamanos_minimos_consulta_el_k_dado_y_no_afirma_tiempos(self):
        linea = self.bloque("M1")[0]
        self.assertIn("n=40", linea)
        self.assertIn("K=5", linea)
        self.assertIn("< 50 ms", linea)

    def test_m2_mide_con_y_sin_puntos_y_cumple_la_cota_de_puntos(self):
        lineas = self.bloque("M2")
        self.assertTrue(any("sin puntos" in linea and "puntos=1 " in linea for linea in lineas))
        self.assertTrue(any("cota" in linea and "cumple" in linea for linea in lineas))
        self.assertFalse(any("NO CUMPLE" in linea for linea in lineas))

    def test_m3_compara_copiar_materializar_y_deepcopy(self):
        linea = self.bloque("M3")[0]
        for texto in ("copiar", "materializar", "deepcopy a secas", "KiB"):
            self.assertIn(texto, linea)

    def test_m4_y_m10_salen_de_las_mismas_partidas(self):
        self.assertIn("recorte de la línea", self.bloque("M4")[0])
        self.assertTrue(any("antes (solo Historial)" in linea and "después" in linea for linea in self.bloque("M10")))

    def test_m5_compara_con_y_sin_linea(self):
        lineas = self.bloque("M5")
        self.assertTrue(any("sin línea" in linea for linea in lineas))
        self.assertTrue(any("con línea" in linea and "registrar" in linea for linea in lineas))

    def test_m6_da_el_bloque_y_la_cota_de_pickle(self):
        lineas = self.bloque("M6")
        self.assertTrue(any("reconstruir" in linea and "bloque" in linea and "pickle" in linea for linea in lineas))
        self.assertTrue(any("sin @cargar" in linea for linea in lineas))
        self.assertTrue(any("con @cargar" in linea for linea in lineas))

    def test_m7_da_resumenes_identicos(self):
        for linea in self.bloque("M7"):
            if linea.startswith("M7 "):
                self.assertIn("idénticos", linea)
                self.assertNotIn("NO CUMPLE", linea)

    def test_m8_corre_main_replay_con_y_sin_hasta_con_codigo_0(self):
        lineas = [linea for linea in self.bloque("M8") if linea.startswith("M8 acciones")]
        self.assertGreaterEqual(len(lineas), 2)
        for linea in lineas:
            self.assertIn("código 0", linea)

    def test_m9_el_oraculo_da_resumenes_iguales(self):
        lineas = self.bloque("M9")
        self.assertTrue(lineas)
        self.assertNotIn("DISTINTOS", " ".join(lineas))

    def test_t113_la_corrida_completa_justifica_el_k_por_omision(self):
        inicio = [i for i, linea in enumerate(self.lineas) if linea.startswith("-T113: justificación del K por omisión")]
        self.assertEqual(len(inicio), 1)
        bloque = []
        for linea in self.lineas[inicio[0] + 1:]:
            if linea == "":
                break
            bloque.append(linea)
        self.assertTrue(any(linea.startswith("T113 regla") for linea in bloque))
        self.assertTrue(any("T113 K=5" in linea and "consulta: p95" in linea and "memoria" in linea for linea in bloque))
        self.assertTrue(any((linea.startswith("T113 K por omisión: ") and "K_POR_OMISION vale" in linea) or linea.startswith("T113 ningún K cumple") for linea in bloque))
        self.assertTrue(any("HIPÓTESIS" in linea for linea in bloque))

    def test_el_archivo_de_la_raiz_no_se_toca(self):
        self.assertEqual(self.estado_del_archivo_de_la_raiz(), self.raiz_antes)


class PruebasDeLaBase(unittest.TestCase):
    """T099: lo común de las mediciones."""

    def test_el_percentil_usa_el_rango_mas_cercano_y_no_cambia_la_entrada(self):
        valores = [5.0, 1.0, 4.0, 2.0, 3.0, 10.0, 9.0, 8.0, 7.0, 6.0]
        copia = list(valores)
        self.assertEqual(percentil(valores, 0.95), 10.0)
        self.assertEqual(percentil(valores, 1.0), 10.0)
        self.assertEqual(percentil(valores, 0.5), 5.0)
        self.assertEqual(percentil([7.0], 0.95), 7.0)
        self.assertEqual(valores, copia)
        with self.assertRaises(ValueError):
            percentil([], 0.95)

    def test_estadisticas_da_mediana_p95_y_maximo(self):
        self.assertEqual(estadisticas([4.0, 1.0, 2.0, 3.0]), (2.5, 4.0, 4.0))
        veinte = [float(i) for i in range(1, 21)]
        self.assertEqual(estadisticas(veinte), (10.5, 19.0, 20.0))

    def test_sin_recolector_detiene_el_recolector_y_siempre_lo_enciende(self):
        self.assertTrue(gc.isenabled())
        with sin_recolector():
            self.assertFalse(gc.isenabled())
        self.assertTrue(gc.isenabled())
        with self.assertRaises(RuntimeError):
            with sin_recolector():
                raise RuntimeError("falla midiendo")
        self.assertTrue(gc.isenabled())

    def test_las_partidas_son_deterministas_por_semilla_y_sin_datos_de_criptas_reales(self):
        uno = bench_linea.sesion_de(5, 3, 30)
        otro = bench_linea.sesion_de(5, 3, 30)
        self.addCleanup(uno.cerrar)
        self.addCleanup(otro.cerrar)
        self.assertEqual(uno.linea.a_registro(), otro.linea.a_registro())
        self.assertEqual(len(uno.motor.salas), bench_linea.SALAS)

    def test_mediciones_desconocidas_o_parciales_no_escriben_el_archivo(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = os.path.join(carpeta, "r.txt")
            salida = bench_linea.correr_bench(["M9"], rapido=True, ruta=ruta)
            self.assertFalse(os.path.exists(ruta))
            self.assertTrue(any(linea.startswith("M9 ") for linea in salida))

    def test_ninguna_medicion_usa_la_vista(self):
        # `main --replay` de M8 se corre con una vista que falla al crearse: si la creara, M8 lanzaría
        lineas = bench_linea.medir_m8(rapido=True)
        self.assertTrue(any("código 0" in linea for linea in lineas))


if __name__ == "__main__":
    unittest.main()
