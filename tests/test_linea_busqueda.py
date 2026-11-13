# Pruebas de la búsqueda binaria propia de la línea de tiempo (spec 004, T011; FR-019, FR-020).
# Sin red. No usa archivos del repositorio salvo la lectura del código fuente de Modelo/BusquedaBinaria.py.

import os
import re
import sys
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Modelo.BusquedaBinaria import ultimo_menor_o_igual

RUTA_MODULO = os.path.join(RAIZ, "Modelo", "BusquedaBinaria.py")


class PruebasUltimoMenorOIgual(unittest.TestCase):

    def test_fr019_arreglo_vacio(self):
        self.assertEqual(ultimo_menor_o_igual([], 5), -1)

    def test_fr019_un_elemento(self):
        self.assertEqual(ultimo_menor_o_igual([10], 9), -1)
        self.assertEqual(ultimo_menor_o_igual([10], 10), 0)
        self.assertEqual(ultimo_menor_o_igual([10], 11), 0)

    def test_fr019_valor_menor_que_todos(self):
        self.assertEqual(ultimo_menor_o_igual([3, 5, 8, 13], 2), -1)

    def test_fr019_igual_al_primero(self):
        self.assertEqual(ultimo_menor_o_igual([3, 5, 8, 13], 3), 0)

    def test_fr019_igual_al_ultimo(self):
        self.assertEqual(ultimo_menor_o_igual([3, 5, 8, 13], 13), 3)

    def test_fr019_entre_dos(self):
        self.assertEqual(ultimo_menor_o_igual([3, 5, 8, 13], 7), 1)
        self.assertEqual(ultimo_menor_o_igual([3, 5, 8, 13], 12), 2)

    def test_fr019_mayor_que_todos(self):
        self.assertEqual(ultimo_menor_o_igual([3, 5, 8, 13], 99), 3)

    def test_fr020_con_repetidos_devuelve_el_ultimo_de_los_iguales(self):
        # pc_accion con un punto regular y el de una carga en la misma acción: no decreciente
        puntos = [0, 50, 50, 100]
        self.assertEqual(ultimo_menor_o_igual(puntos, 50), 2)
        self.assertEqual(ultimo_menor_o_igual(puntos, 75), 2)
        self.assertEqual(ultimo_menor_o_igual([4, 4, 4], 4), 2)
        self.assertEqual(ultimo_menor_o_igual([4, 4, 4], 3), -1)

    def test_fr019_reloj_dec_estrictamente_creciente(self):
        reloj_dec = [0, 100, 250, 300, 700]
        for valor in range(-5, 710):
            esperado = -1
            for indice in range(len(reloj_dec)):
                if reloj_dec[indice] <= valor:
                    esperado = indice
            self.assertEqual(ultimo_menor_o_igual(reloj_dec, valor), esperado, f"valor {valor}")

    def test_fr019_no_modifica_el_arreglo(self):
        arreglo = [1, 2, 2, 9]
        ultimo_menor_o_igual(arreglo, 2)
        self.assertEqual(arreglo, [1, 2, 2, 9])


class PruebasCodigoFuenteBusquedaBinaria(unittest.TestCase):

    PROHIBIDOS = ("bisect", "sorted", r"\.sort\(", "heapq", "collections", "dict", "set")

    def test_fr020_el_codigo_no_usa_librerias_ni_estructuras_prohibidas(self):
        """Principio I: búsqueda propia, sin bisect, sorted, .sort(, heapq, collections, dict ni set."""
        with open(RUTA_MODULO, encoding="utf-8") as archivo:
            fuente = archivo.read()
        for prohibido in self.PROHIBIDOS:
            patron = prohibido if prohibido.startswith("\\") else rf"\b{prohibido}\b"
            self.assertIsNone(re.search(patron, fuente), f"Modelo/BusquedaBinaria.py usa «{prohibido}»")


if __name__ == "__main__":
    unittest.main()
