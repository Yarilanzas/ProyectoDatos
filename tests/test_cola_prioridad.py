# Pruebas de Modelo/ColaPrioridad.py (spec 003, T004): montículo binario mínimo propio con inserción perezosa
# (data-model §3, research R1). Principio I: estructura propia, sin heapq, bisect ni collections.

import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import random
import re
import unittest

from Modelo.ColaPrioridad import ColaPrioridad

ARCHIVO = os.path.join(RAIZ, "Modelo", "ColaPrioridad.py")


def extraer_todo(cola):
    resultado = []
    while not cola.vacia():
        resultado.append(cola.extraer_minimo())
    return resultado


class TestOrdenDeExtraccion(unittest.TestCase):
    def test_fr011_principio_i_extrae_en_orden_de_distancia_y_ordinal(self):
        cola = ColaPrioridad()
        for distancia, ordinal in [(300, 2), (100, 7), (200, 1), (100, 3), (0, 9), (200, 0)]:
            cola.insertar(distancia, ordinal)
        self.assertEqual(extraer_todo(cola), [(0, 9), (100, 3), (100, 7), (200, 0), (200, 1), (300, 2)])

    def test_fr011_principio_i_insercion_perezosa_entradas_repetidas_del_mismo_ordinal(self):
        # Si una sala mejora se inserta otra vez; la cola devuelve todas las entradas, en orden, y quien la usa
        # descarta las viejas (data-model §3).
        cola = ColaPrioridad()
        cola.insertar(500, 4)
        cola.insertar(300, 4)
        cola.insertar(400, 2)
        cola.insertar(300, 4)
        cola.insertar(100, 4)
        self.assertEqual(extraer_todo(cola), [(100, 4), (300, 4), (300, 4), (400, 2), (500, 4)])

    def test_fr011_fr033_principio_i_mil_elementos_en_orden_pseudoaleatorio(self):
        azar = random.Random(2026)
        cantidad = 1000
        distancias = [azar.randint(0, 5000) for _ in range(cantidad)]
        ordinales = list(range(cantidad))
        azar.shuffle(ordinales)

        cola = ColaPrioridad()
        for ordinal in ordinales:
            cola.insertar(distancias[ordinal], ordinal)
        extraidos = extraer_todo(cola)

        self.assertEqual(len(extraidos), cantidad)
        visto = [False] * cantidad
        for distancia, ordinal in extraidos:
            self.assertFalse(visto[ordinal])
            visto[ordinal] = True
            self.assertEqual(distancia, distancias[ordinal])
        for indice in range(1, cantidad):
            self.assertLessEqual(extraidos[indice - 1], extraidos[indice])


class TestDeterminismo(unittest.TestCase):
    def test_fr021_principio_i_orden_determinista_ante_claves_iguales(self):
        inserciones = [(100, 5), (100, 2), (100, 8), (100, 2), (50, 9), (100, 0), (50, 1)]

        def corrida():
            cola = ColaPrioridad()
            for distancia, ordinal in inserciones:
                cola.insertar(distancia, ordinal)
            return extraer_todo(cola)

        primera = corrida()
        self.assertEqual(primera, corrida())
        self.assertEqual(primera, [(50, 1), (50, 9), (100, 0), (100, 2), (100, 2), (100, 5), (100, 8)])


class TestVaciaYVaciar(unittest.TestCase):
    def test_fr033_principio_i_vacia_en_cola_nueva_con_elementos_y_tras_extraer_todo(self):
        cola = ColaPrioridad()
        self.assertTrue(cola.vacia())
        cola.insertar(10, 1)
        cola.insertar(20, 2)
        self.assertFalse(cola.vacia())
        cola.extraer_minimo()
        self.assertFalse(cola.vacia())
        cola.extraer_minimo()
        self.assertTrue(cola.vacia())

    def test_fr033_principio_i_vaciar_deja_la_cola_vacia_y_usable(self):
        cola = ColaPrioridad()
        for ordinal in range(50):
            cola.insertar(100 - ordinal, ordinal)
        cola.vaciar()
        self.assertTrue(cola.vacia())
        self.assertIsNone(cola.extraer_minimo())

        cola.insertar(7, 3)
        cola.insertar(2, 8)
        self.assertEqual(extraer_todo(cola), [(2, 8), (7, 3)])

    def test_fr011_principio_i_extraer_minimo_en_cola_vacia_devuelve_none(self):
        # Mismo criterio que AgendaEventos.extraer: sin elementos devuelve None y no cambia la cola.
        cola = ColaPrioridad()
        self.assertIsNone(cola.extraer_minimo())
        self.assertTrue(cola.vacia())
        cola.insertar(1, 1)
        cola.extraer_minimo()
        self.assertIsNone(cola.extraer_minimo())
        self.assertTrue(cola.vacia())


class TestEstructuraPropia(unittest.TestCase):
    def test_fr011_principio_i_no_importa_heapq_bisect_ni_collections(self):
        with open(ARCHIVO, encoding="utf-8") as archivo:
            codigo = archivo.read()
        prohibido = re.compile(r"^\s*(?:import|from)\s+(heapq|bisect|collections)\b", re.MULTILINE)
        self.assertIsNone(prohibido.search(codigo), "Modelo/ColaPrioridad.py importa un módulo prohibido")


if __name__ == "__main__":
    unittest.main()
