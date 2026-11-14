# Pruebas de los generadores de mapas sintéticos de la Fase 6 (T099).
# Atiende: SC-006, PR-15. Sin red y sin leer ninguna cripta real (Principio IV).

import os
import socket
import sys
import unittest
from unittest import mock

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from tests import mapas_sinteticos
from tests.mapas_sinteticos import cadena, grilla, salas_sinteticas

TAMANOS_V = (25, 100, 400, 2500)          # grilla y cadena de M4 (research R9)
TAMANOS_N = (20, 200, 2000, 20000)        # salas de M1 (research R9)
OPUESTA = (("N", "S"), ("S", "N"), ("E", "O"), ("O", "E"))


def _opuesta(direccion):
    for de, hacia in OPUESTA:
        if de == direccion:
            return hacia
    raise AssertionError(f"dirección desconocida: {direccion}")


def _ids_consecutivos(prueba, salas):
    # ids 1..n en orden: así la sala con id i está en salas[i - 1] (sin dict como índice).
    for posicion in range(len(salas)):
        prueba.assertEqual(salas[posicion]["id"], posicion + 1)


def _conexo(salas):
    # Recorrido en anchura con lista y puntero de cabeza; visitado es una lista de booleanos por id.
    if not salas:
        return False
    visitado = [False] * (len(salas) + 1)
    cola = [1]
    visitado[1] = True
    cabeza = 0
    while cabeza < len(cola):
        actual = salas[cola[cabeza] - 1]
        cabeza += 1
        for datos in actual["salidas"].values():
            destino = datos["sala"]
            if not visitado[destino]:
                visitado[destino] = True
                cola.append(destino)
    return len(cola) == len(salas)


def _todos_los_mapas():
    for v in TAMANOS_V:
        yield f"cadena V={v}", cadena(v)
        yield f"grilla V={v}", grilla(v)
    for n in TAMANOS_N:
        yield f"salas n={n}", salas_sinteticas(n)


class TestTamanos(unittest.TestCase):
    def test_sc006_pr15_cadena_tiene_exactamente_v_salas(self):
        for v in TAMANOS_V:
            with self.subTest(v=v):
                salas = cadena(v)
                self.assertEqual(len(salas), v)
                _ids_consecutivos(self, salas)

    def test_sc006_pr15_grilla_tiene_exactamente_v_salas(self):
        for v in TAMANOS_V:
            with self.subTest(v=v):
                salas = grilla(v)
                self.assertEqual(len(salas), v)
                _ids_consecutivos(self, salas)

    def test_sc006_pr15_grilla_rechaza_v_que_no_es_cuadrado(self):
        with self.assertRaises(ValueError):
            grilla(24)

    def test_sc006_pr15_salas_hasta_n_20000(self):
        for n in TAMANOS_N:
            with self.subTest(n=n):
                salas = salas_sinteticas(n)
                self.assertEqual(len(salas), n)
                _ids_consecutivos(self, salas)

    def test_sc006_pr15_forma_de_cadena_y_grilla(self):
        # cadena: los extremos tienen 1 salida y el resto 2; grilla: las esquinas 2, el interior 4.
        salas = cadena(25)
        self.assertEqual(len(salas), 25)
        self.assertEqual(len(salas[0]["salidas"]), 1)
        self.assertEqual(len(salas[-1]["salidas"]), 1)
        self.assertEqual(len(salas[12]["salidas"]), 2)
        salas = grilla(25)
        self.assertEqual(len(salas), 25)
        self.assertEqual(len(salas[0]["salidas"]), 2)
        self.assertEqual(len(salas[12]["salidas"]), 4)


class TestCostos(unittest.TestCase):
    def test_sc006_pr15_costos_simetricos(self):
        for nombre, salas in _todos_los_mapas():
            with self.subTest(mapa=nombre):
                self.assertTrue(salas)
                for sala in salas:
                    for direccion, datos in sala["salidas"].items():
                        vuelta = salas[datos["sala"] - 1]["salidas"].get(_opuesta(direccion))
                        self.assertIsNotNone(vuelta, f"{sala['id']} {direccion} sin salida de vuelta")
                        self.assertEqual(vuelta["sala"], sala["id"])
                        self.assertEqual(vuelta["costo"], datos["costo"])

    def test_sc006_pr15_costos_enteros_positivos_y_variados(self):
        for nombre, salas in _todos_los_mapas():
            with self.subTest(mapa=nombre):
                self.assertTrue(salas)
                distintos = []
                for sala in salas:
                    for datos in sala["salidas"].values():
                        costo = datos["costo"]
                        self.assertIsInstance(costo, int)
                        self.assertGreaterEqual(costo, 1)
                        if costo not in distintos and len(distintos) < 5:
                            distintos.append(costo)
                self.assertGreaterEqual(len(distintos), 5, "los costos no son variados")

    def test_sc006_pr15_misma_semilla_mismo_mapa_y_otra_semilla_otros_costos(self):
        self.assertEqual(grilla(100, semilla=3), grilla(100, semilla=3))
        self.assertNotEqual(grilla(100, semilla=3), grilla(100, semilla=4))


class TestConexo(unittest.TestCase):
    def test_sc006_pr15_todos_los_mapas_son_conexos(self):
        for nombre, salas in _todos_los_mapas():
            with self.subTest(mapa=nombre):
                self.assertTrue(_conexo(salas))


class TestSinDatosReales(unittest.TestCase):
    def test_sc006_pr15_no_abre_archivos_ni_red(self):
        prohibido = AssertionError("el generador no debe abrir archivos ni red")
        with mock.patch("builtins.open", side_effect=prohibido), \
                mock.patch.object(socket.socket, "connect", side_effect=prohibido):
            for _, salas in _todos_los_mapas():
                self.assertTrue(salas)

    def test_sc006_pr15_no_importa_fuentes_ni_red(self):
        with open(mapas_sinteticos.__file__, encoding="utf-8") as archivo:
            codigo = archivo.read()
        for marca in ("import requests", "from API", "from Gestor", "datos_locales", "open("):
            self.assertNotIn(marca, codigo)


if __name__ == "__main__":
    unittest.main()
