# Ayuda del juego para el terreno y el cazador, capacidad 003 (T071; FR-029).
# La ayuda describe el costo de las salidas (100 si no lo traen) y el comportamiento del cazador: persigue por la ruta
# más barata dentro de su rango, espera si no hay ruta abierta o es más cara que su rango, y ataca si comparte sala.

import os
import sys
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Vista.VistaConsola import AYUDA, VistaConsola


class TestAyudaTerrenoCazador(unittest.TestCase):

    def test_fr029_la_ayuda_explica_el_costo_de_las_salidas(self):
        """T071 (FR-029): la ayuda menciona el costo de las salidas, que es tiempo, y el valor 100 por omisión."""
        texto = AYUDA.lower()
        for palabra in ("costo", "salida", "100"):
            with self.subTest(palabra=palabra):
                self.assertIn(palabra, texto)

    def test_fr029_la_ayuda_explica_el_cazador(self):
        """T071 (FR-029): la ayuda menciona al cazador, la ruta más barata, su rango, que espera y que ataca."""
        texto = AYUDA.lower()
        for palabra in ("cazador", "más barata", "rango", "espera", "ataca"):
            with self.subTest(palabra=palabra):
                self.assertIn(palabra, texto)

    def test_fr029_el_comando_ayuda_muestra_ese_texto(self):
        """T071 (FR-029): VistaConsola.mostrar_ayuda muestra la ayuda completa, con la parte del terreno y del cazador."""
        salida = []
        VistaConsola(salida=salida.append).mostrar_ayuda()
        self.assertEqual(salida, [AYUDA])
        self.assertIn("Cazador:", salida[0])
        self.assertIn("Terreno:", salida[0])


if __name__ == "__main__":
    unittest.main()
