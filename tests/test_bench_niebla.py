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

from unittest import mock
import socket

from Modelo.retroceso import Historial
from tests import bench_niebla
from tests.bench_niebla import (VARIANTES_M3, ListaLineal, ListaOrdenada, clave_puerta, encabezado, escribir_resultados,
                                estado_de, lineas_base_m1, mediana, medir_m1, medir_m2, medir_m3, medir_ms,
                                preparar_m1, preparar_m2, preparar_m3, revelar_en_lista,
                                deshacer_en_lista)
from Modelo.Conocimiento import DESCONOCIDA, SIN_OBSERVAR
from Vista.VistaConsola import VistaConsola


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


# M1 a M3 (T101 a T103). Solo forma y corrección: ninguna prueba afirma tiempos (Principio VIII).

def _buscar_fila(prueba, filas, medicion, variante, **parametros):
    halladas = []
    for fila in filas:
        if fila.medicion != medicion or fila.variante != variante:
            continue
        if all(fila.valor(nombre) == valor for nombre, valor in parametros.items()):
            halladas.append(fila)
    prueba.assertEqual(len(halladas), 1, f"{medicion} {variante} {parametros}: {len(halladas)} filas")
    fila = halladas[0]
    prueba.assertIsInstance(fila.ms, float)
    prueba.assertGreaterEqual(fila.ms, 0.0)
    prueba.assertTrue(fila.hipotesis)
    return fila


def _distintos(valores):
    vistos = []
    for valor in valores:
        if valor not in vistos:
            vistos.append(valor)
    return len(vistos)


class TestFormaDeLasMediciones(unittest.TestCase):
    def test_pr15_tamanos_por_defecto_de_research_r9(self):
        self.assertEqual(bench_niebla.TAMANOS_M1, (20, 200, 2000, 20000))
        self.assertEqual(bench_niebla.TAMANOS_M2, (10, 100, 1000, 10000))
        self.assertGreaterEqual(len(bench_niebla.TAMANOS_M3_N), 3)
        self.assertGreaterEqual(len(bench_niebla.VECINAS_M3), 3)

    def test_fr001_fr005_pr15_m1_una_fila_por_tamano_objeto_y_variante(self):
        filas = medir_m1((20, 40), repeticiones=1, consultas=5)
        self.assertEqual(len(filas), 12)
        for n in (20, 40):
            for objeto in ("sala", "puerta"):
                for variante in ("arreglos", "binaria", "lineal"):
                    _buscar_fila(self, filas, "M1", f"{objeto}/{variante}", n=n)

    def test_fr003_fr009_pr15_m2_una_fila_por_k_y_variante(self):
        filas = medir_m2((10, 20), repeticiones=1)
        self.assertEqual(len(filas), 4)
        for k in (10, 20):
            for variante in ("arreglos", "lista ordenada"):
                fila = _buscar_fila(self, filas, "M2", variante, k=k)
                self.assertGreater(fila.valor("r"), 0)

    def test_fr014_pr15_m3_una_fila_por_variante_n_y_vecinas_y_r_crece_con_las_vecinas(self):
        filas = medir_m3((50, 80), (2, 4), repeticiones=1)
        self.assertEqual(len(filas), 12)
        for variante in ("lote", "cierres", "copia"):
            for n in (50, 80):
                r_por_vecinas = []
                for vecinas in (2, 4):
                    fila = _buscar_fila(self, filas, "M3", variante, n=n, vecinas=vecinas)
                    r_por_vecinas.append(fila.valor("r"))
                self.assertLess(r_por_vecinas[0], r_por_vecinas[1])

    def test_pr15_texto_de_cada_fila_dice_parametros_tiempo_e_hipotesis(self):
        filas = medir_m1((20,), 1, 3) + medir_m2((10,), 1) + medir_m3((50,), (2,), 1)
        self.assertEqual(len(filas), 6 + 2 + 3)
        for fila in filas:
            texto = fila.texto()
            self.assertIn(fila.medicion, texto)
            self.assertIn(fila.variante, texto)
            self.assertIn("ms", texto)
            self.assertIn("hipótesis", texto)
        self.assertIn("n=20", filas[0].texto())

    def test_pr15_m1_a_m3_corren_sin_red_ni_vista(self):
        prohibido = AssertionError("las mediciones no usan red ni vista")
        with mock.patch.object(socket.socket, "connect", side_effect=prohibido), \
                mock.patch.object(VistaConsola, "__init__", side_effect=prohibido):
            filas = medir_m1((20,), 1, 3) + medir_m2((10,), 1) + medir_m3((50,), (2,), 1)
        self.assertEqual(len(filas), 11)


class TestCorreccionDeLineasBase(unittest.TestCase):
    def test_pr15_lista_ordenada_inserta_en_orden_busca_y_quita(self):
        lista = ListaOrdenada()
        for clave in (5, 1, 9, 3, 7):
            lista.insertar(clave, clave * 10)
        self.assertEqual(lista.pares(), [(1, 10), (3, 30), (5, 50), (7, 70), (9, 90)])
        self.assertEqual(lista.buscar(7, -1), 70)
        self.assertEqual(lista.buscar(4, -1), -1)
        lista.insertar(7, 71)  # clave existente: actualiza
        self.assertEqual(lista.buscar(7, -1), 71)
        lista.quitar(1)
        lista.quitar(9)
        self.assertEqual(lista.pares(), [(3, 30), (5, 50), (7, 71)])

    def test_pr15_lista_lineal_busca_y_quita(self):
        lista = ListaLineal()
        for clave in (5, 1, 9):
            lista.insertar(clave, clave * 10)
        self.assertEqual(lista.buscar(1, -1), 10)
        self.assertEqual(lista.buscar(2, -1), -1)
        lista.quitar(1)
        self.assertEqual(lista.buscar(1, -1), -1)
        self.assertEqual(len(lista.pares()), 2)

    def test_fr001_fr005_pr15_m1_binaria_y_lineal_dan_lo_mismo_que_los_arreglos(self):
        conocimiento, salas = preparar_m1(40)
        self.assertIsNotNone(conocimiento)
        self.assertEqual(len(salas), 40)
        ordenada_salas, lineal_salas, ordenada_puertas, lineal_puertas = lineas_base_m1(conocimiento)
        self.assertIsNotNone(ordenada_salas)

        estados, recuerdos = [], []
        for sala in salas:
            esperado = conocimiento.estado(sala)
            estados.append(esperado)
            self.assertEqual(ordenada_salas.buscar(sala.id, DESCONOCIDA), esperado)
            self.assertEqual(lineal_salas.buscar(sala.id, DESCONOCIDA), esperado)
            for salida in sala.salidas.values():
                esperado = conocimiento.recuerdo(salida)
                recuerdos.append(esperado)
                self.assertEqual(ordenada_puertas.buscar(clave_puerta(salida), SIN_OBSERVAR), esperado)
                self.assertEqual(lineal_puertas.buscar(clave_puerta(salida), SIN_OBSERVAR), esperado)
        # el mapa preparado mezcla los tres estados y los tres recuerdos, para que la comparación diga algo
        self.assertEqual(_distintos(estados), 3)
        self.assertEqual(_distintos(recuerdos), 3)

    def test_fr003_fr009_pr15_m2_lista_ordenada_da_lo_mismo_que_los_arreglos(self):
        conocimiento, lote, lista = preparar_m2(10)
        self.assertIsNotNone(conocimiento)
        self.assertTrue(lote)
        self.assertGreaterEqual(len(conocimiento.reveladas), 10)
        self.assertEqual(len(lista.pares()), len(conocimiento.reveladas))

        def comparar():
            for sala in conocimiento._salas:
                self.assertEqual(lista.buscar(sala.id, DESCONOCIDA), conocimiento.estado(sala))

        comparar()
        conocimiento.aplicar(lote)
        revelar_en_lista(lista, lote, conocimiento)
        comparar()
        conocimiento.invertir(lote)
        deshacer_en_lista(lista, lote, conocimiento)
        comparar()

    def test_fr014_pr15_m3_las_tres_variantes_dejan_el_mismo_estado(self):
        self.assertEqual(tuple(nombre for nombre, _, _ in VARIANTES_M3), ("lote", "cierres", "copia"))
        despues = []
        for nombre, crear, registrar in VARIANTES_M3:
            with self.subTest(variante=nombre):
                salas, centro = preparar_m3(60, 4)
                conocimiento = crear(salas)
                inicial = estado_de(conocimiento)
                historial = Historial()
                historial.abrir_intervalo()
                registrar(conocimiento, centro, historial)
                tras_registrar = estado_de(conocimiento)
                self.assertNotEqual(tras_registrar, inicial)
                despues.append(tras_registrar)
                self.assertTrue(historial.deshacer_ultimo())
                self.assertEqual(estado_de(conocimiento), inicial)
        self.assertEqual(despues[0], despues[1])
        self.assertEqual(despues[0], despues[2])


if __name__ == "__main__":
    unittest.main()
