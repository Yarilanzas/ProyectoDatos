# Prueba de contrato de la interfaz de ruta de «ir a» (T043). Contrato: contracts/interfaz-ruta.md.
# FR-022, FR-023, FR-024, PR-10. Ejercita la interfaz sin mirar la implementación, con grafos de prueba
# pequeños, y está parametrizada por buscador:
# - corre ya contra `buscador_prueba` (utilidad de prueba, T042);
# - contra `primer_paso` queda con `skip` hasta T063: su cuerpo delega en Modelo/BusquedaRuta.py, que
#   implementa Persona A (D-PEND-01, opción A) y todavía no existe.

import os
import sys

# Permite ejecutar este archivo desde cualquier carpeta (PyCharm, unittest o pytest).
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import unittest

from Modelo.rutas_ir_a import primer_paso
from tests.utiles_niebla import buscador_prueba


class SalaPrueba:
    def __init__(self, id_sala, ordinal):
        self.id = id_sala
        self.ordinal = ordinal

    def __repr__(self):
        return f"SalaPrueba({self.id})"


class GrafoPrueba:
    """Implementa la interfaz de grafo del contrato: ordinal, cantidad_salas y aristas.

    `aristas` se da como lista de (origen, dirección, destino, costo), y cada sala entrega las
    suyas en ese mismo orden, que a propósito no está ordenado por id.
    """

    def __init__(self, ids, aristas):
        self.salas = [SalaPrueba(id_sala, ordinal) for ordinal, id_sala in enumerate(ids)]
        self.cantidad_salas = len(self.salas)
        self._aristas = [[] for _ in self.salas]
        for origen, direccion, destino, costo in aristas:
            self._aristas[self.sala(origen).ordinal].append((direccion, self.sala(destino), costo))

    def sala(self, id_sala):
        for sala in self.salas:
            if sala.id == id_sala:
                return sala
        raise KeyError(id_sala)

    def ordinal(self, sala):
        return sala.ordinal

    def aristas(self, sala):
        return list(self._aristas[sala.ordinal])

    def foto(self):
        return [[(d, s.id, c) for d, s, c in lista] for lista in self._aristas]


def invertido(aristas):
    return list(reversed(aristas))


class ContratoRuta:
    """Casos del contrato. Cada subclase define `buscar` con la firma de `primer_paso`."""

    buscar = None

    def paso(self, grafo, origen, destino):
        return self.buscar(grafo, grafo.sala(origen), grafo.sala(destino))

    def assertPaso(self, paso, direccion, vecina, costo_total):
        self.assertIsNotNone(paso)
        self.assertEqual((paso.direccion, paso.destino.id, paso.costo_total), (direccion, vecina, costo_total))

    # Obligación 1 (FR-024): costo total mínimo.

    def test_fr024_ruta_unica(self):
        grafo = GrafoPrueba([1, 2, 3], [(1, "E", 2, 100), (2, "E", 3, 100)])
        self.assertPaso(self.paso(grafo, 1, 3), "E", 2, 200)

    def test_fr024_ruta_mas_barata_con_mas_saltos(self):
        aristas = [(1, "E", 3, 500), (1, "S", 2, 100), (2, "E", 4, 100), (4, "N", 3, 100)]
        grafo = GrafoPrueba([1, 2, 3, 4], aristas)
        self.assertPaso(self.paso(grafo, 1, 3), "S", 2, 300)

    def test_fr024_costos_distintos_de_100(self):
        # Nada debe asumir el valor por defecto de 100.
        grafo = GrafoPrueba([1, 2, 3], [(1, "E", 2, 7), (2, "E", 3, 5), (1, "S", 3, 13)])
        self.assertPaso(self.paso(grafo, 1, 3), "E", 2, 12)
        grafo = GrafoPrueba([1, 2, 3], [(1, "E", 2, 7), (2, "E", 3, 5), (1, "S", 3, 11)])
        self.assertPaso(self.paso(grafo, 1, 3), "S", 3, 11)

    # Obligación 3 (FR-022, FR-027d): sin ruta, None.

    def test_fr022_sin_ruta_devuelve_none(self):
        grafo = GrafoPrueba([1, 2, 3], [(1, "E", 2, 100)])
        self.assertIsNone(self.paso(grafo, 1, 3))

    def test_fr023_las_aristas_son_dirigidas(self):
        # Solo existe 2 -> 1: desde 1 no hay ruta hacia 2.
        grafo = GrafoPrueba([1, 2], [(2, "O", 1, 100)])
        self.assertIsNone(self.paso(grafo, 1, 2))
        self.assertPaso(self.paso(grafo, 2, 1), "O", 1, 100)

    # Obligación 2 (FR-024): desempate.

    def test_fr024_empate_va_a_la_vecina_de_menor_id_en_cualquier_orden(self):
        aristas = [(1, "E", 3, 100), (1, "S", 2, 100), (3, "S", 4, 100), (2, "E", 4, 100)]
        for orden in (aristas, invertido(aristas)):
            grafo = GrafoPrueba([1, 2, 3, 4], orden)
            self.assertPaso(self.paso(grafo, 1, 4), "S", 2, 200)

    def test_fr024_el_empate_se_decide_por_el_primer_paso_no_por_el_ultimo(self):
        # 1 -> 2 -> 8 -> 9 y 1 -> 3 -> 4 -> 9 cuestan lo mismo. La penúltima de menor id es 4 (rama de 3),
        # pero el criterio es la primera vecina: 2.
        aristas = [(1, "S", 3, 100), (3, "E", 4, 100), (4, "E", 9, 100),
                   (1, "E", 2, 100), (2, "E", 8, 100), (8, "S", 9, 100)]
        for orden in (aristas, invertido(aristas)):
            grafo = GrafoPrueba([1, 2, 3, 4, 8, 9], orden)
            self.assertPaso(self.paso(grafo, 1, 9), "E", 2, 300)

    def test_fr024_dos_salidas_a_la_misma_vecina_gana_n_s_e_o(self):
        # P-03: con igual costo gana la primera en el orden N, S, E, O, sin importar el orden de `aristas`.
        casos = (
            ([(1, "E", 2, 100), (1, "N", 2, 100)], "N"),
            ([(1, "O", 2, 100), (1, "S", 2, 100)], "S"),
            ([(1, "O", 2, 100), (1, "E", 2, 100)], "E"),
        )
        for aristas, esperada in casos:
            for orden in (aristas, invertido(aristas)):
                grafo = GrafoPrueba([1, 2], orden)
                self.assertPaso(self.paso(grafo, 1, 2), esperada, 2, 100)

    def test_fr024_dos_salidas_a_la_misma_vecina_con_distinto_costo_gana_la_barata(self):
        grafo = GrafoPrueba([1, 2], [(1, "N", 2, 300), (1, "E", 2, 100)])
        self.assertPaso(self.paso(grafo, 1, 2), "E", 2, 100)

    # Obligaciones 4 y 5: solo usa el grafo, no lo modifica, y es determinista.

    def test_no_modifica_el_grafo_y_es_determinista(self):
        aristas = [(1, "E", 3, 100), (1, "S", 2, 100), (3, "S", 4, 100), (2, "E", 4, 100)]
        grafo = GrafoPrueba([1, 2, 3, 4], aristas)
        antes = grafo.foto()
        primero = self.paso(grafo, 1, 4)
        segundo = self.paso(grafo, 1, 4)
        self.assertEqual(grafo.foto(), antes)
        self.assertEqual((primero.direccion, primero.destino, primero.costo_total),
                         (segundo.direccion, segundo.destino, segundo.costo_total))


class TestContratoBuscadorPrueba(ContratoRuta, unittest.TestCase):
    buscar = staticmethod(buscador_prueba)


@unittest.skip("T063: primer_paso delega en Modelo/BusquedaRuta.py de Persona A, que aún no existe (D-PEND-01, opción A)")
class TestContratoPrimerPaso(ContratoRuta, unittest.TestCase):
    buscar = staticmethod(primer_paso)


class TestPrimerPasoPendiente(unittest.TestCase):
    # T041: mientras Persona A no suba Modelo/BusquedaRuta.py, primer_paso solo lanza NotImplementedError.
    # Se retira en T062.

    def test_primer_paso_lanza_not_implemented_error(self):
        grafo = GrafoPrueba([1, 2], [(1, "E", 2, 100)])
        with self.assertRaises(NotImplementedError):
            primer_paso(grafo, grafo.sala(1), grafo.sala(2))


if __name__ == "__main__":
    unittest.main()
