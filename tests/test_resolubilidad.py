# Pruebas del verificador de resolubilidad (spec 002, US1: T012 a T016).
# Sin red, solo unittest. Cada prueba cita en su nombre o docstring el FR que verifica.
# Las criptas pequeñas se arman aquí mismo; las grandes salen de tests/generador_criptas.py (Principio IV).

import os
import unittest
from unittest import mock

from DTOS.SalaEsqueleto import SalaEsqueleto
from DTOS.Salida import Salida
from DTOS.UbicacionLlave import UbicacionLlave
from Modelo import Resolubilidad
from Modelo.Resolubilidad import GrafoSalas, IndiceLlaves
from Modelo.ordenamiento import merge_sort

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RUTA_MODULO = os.path.join(RAIZ, "Modelo", "Resolubilidad.py")


# --- Ayudas para armar criptas pequeñas -------------------------------------------------------------------------

def abierta(destino, cierre=None):
    return Salida(destino, False, None, cierre)


def cerrada(destino, llave=None, cierre=None):
    return Salida(destino, True, llave, cierre)


def sala(id_sala, **salidas):
    return SalaEsqueleto(id_sala, f"Sala {id_sala}", salidas)


def sala_con(id_sala, salidas):
    # para direcciones que no son nombres válidos de argumento
    return SalaEsqueleto(id_sala, f"Sala {id_sala}", salidas)


def llave(id_llave, id_sala, enemigo=None):
    return UbicacionLlave(id_llave, id_sala, enemigo)


def indice_para(esqueleto, ubicaciones, llave_salida=None):
    # mismas menciones que reúne verificar: ubicaciones, llaves de salidas cerradas y llave_salida
    menciones = [u.id_llave for u in ubicaciones]
    for s in esqueleto:
        for salida in s.salidas.values():
            if salida.cerrada and salida.llave is not None:
                menciones.append(salida.llave)
    if llave_salida is not None:
        menciones.append(llave_salida)
    return IndiceLlaves.construir(menciones)


def direcciones(sala_verif):
    return [s.direccion for s in sala_verif.salidas]


# --- T012: estructuras ------------------------------------------------------------------------------------------

class PruebasIndiceLlaves(unittest.TestCase):

    def test_fr007_fr014_ordena_y_quita_repetidos(self):
        indice = IndiceLlaves.construir(["llave_b", "llave_a", "llave_c", "llave_a", "llave_b"])
        self.assertEqual(indice.ids, ["llave_a", "llave_b", "llave_c"])
        self.assertEqual(indice.cantidad(), 3)

    def test_fr014_usa_merge_sort(self):
        with mock.patch.object(Resolubilidad, "merge_sort", wraps=merge_sort) as espia:
            IndiceLlaves.construir(["z", "a", "m"])
        self.assertTrue(espia.called, "IndiceLlaves.construir debe ordenar con merge_sort")

    def test_fr007_numero_devuelve_posicion_o_menos_uno(self):
        indice = IndiceLlaves.construir(["k3", "k1", "k2"])
        self.assertEqual(indice.numero("k1"), 0)
        self.assertEqual(indice.numero("k2"), 1)
        self.assertEqual(indice.numero("k3"), 2)
        self.assertEqual(indice.numero("k0"), -1)
        self.assertEqual(indice.numero("k9"), -1)
        self.assertEqual(indice.numero("k15"), -1)

    def test_fr007_id_de_es_inverso_de_numero(self):
        indice = IndiceLlaves.construir(["d", "b", "a", "c"])
        for n in range(indice.cantidad()):
            self.assertEqual(indice.numero(indice.id_de(n)), n)
        self.assertEqual(indice.id_de(0), "a")
        self.assertEqual(indice.id_de(3), "d")

    def test_fr014_invariante_estrictamente_creciente(self):
        menciones = ["k%02d" % ((i * 7) % 23) for i in range(60)]
        indice = IndiceLlaves.construir(menciones)
        for i in range(indice.cantidad() - 1):
            self.assertLess(indice.ids[i], indice.ids[i + 1])
        self.assertEqual(indice.cantidad(), 23)

    def test_fr007_indice_vacio(self):
        indice = IndiceLlaves.construir([])
        self.assertEqual(indice.cantidad(), 0)
        self.assertEqual(indice.numero("k"), -1)


class PruebasGrafoSalas(unittest.TestCase):

    def construir(self, esqueleto, ubicaciones=(), llave_salida=None):
        ubicaciones = list(ubicaciones)
        indice = indice_para(esqueleto, ubicaciones, llave_salida)
        return GrafoSalas.desde(esqueleto, indice, ubicaciones), indice

    def test_fr014_salidas_en_orden_n_s_e_o_y_otras_por_texto(self):
        s1 = sala_con(1, {"O": abierta(2), "arriba": abierta(2), "E": abierta(2), "N": abierta(2),
                          "S": abierta(2), "abajo": abierta(2)})
        grafo, _ = self.construir([s1, sala(2)])
        self.assertEqual(direcciones(grafo.sala(1)), ["N", "S", "E", "O", "abajo", "arriba"])

    def test_fr005_cada_salida_solo_en_su_origen(self):
        grafo, _ = self.construir([sala(1, E=abierta(2)), sala(2)])
        self.assertEqual(direcciones(grafo.sala(1)), ["E"])
        self.assertEqual(grafo.sala(2).salidas, [])
        salida = grafo.sala(1).salidas[0]
        self.assertEqual((salida.origen, salida.destino), (1, 2))
        self.assertEqual([s.origen for s in grafo.entrantes[2]], [1])
        self.assertEqual(grafo.entrantes[1], [])

    def test_fr003_llave_soltada_por_enemigo_en_su_sala_inicial(self):
        grafo, indice = self.construir([sala(1, E=abierta(2)), sala(2)],
                                       [llave("k1", 2, enemigo="e-1"), llave("k2", 1)])
        self.assertEqual(grafo.sala(2).llaves, [indice.numero("k1")])
        self.assertEqual(grafo.sala(1).llaves, [indice.numero("k2")])

    def test_fr004_ignora_cierre_automatico(self):
        grafo, _ = self.construir([sala(1, E=abierta(2, cierre=30), S=cerrada(3, "k", cierre=5)), sala(2), sala(3)],
                                  [llave("k", 1)])
        este, sur = grafo.sala(1).salidas[1], grafo.sala(1).salidas[0]
        self.assertEqual((sur.direccion, este.direccion), ("S", "E"))
        self.assertFalse(este.cerrada)
        self.assertEqual(este.num_llave, -1)
        self.assertTrue(sur.cerrada)

    def test_fr004_no_recibe_trampas_ni_contenido(self):
        import inspect
        for funcion in (GrafoSalas.desde, Resolubilidad.verificar):
            parametros = list(inspect.signature(funcion).parameters)
            for prohibido in ("trampas", "contenido", "enemigos"):
                self.assertNotIn(prohibido, parametros)

    def test_fr001_num_llave_e_id_llave(self):
        s1 = sala(1, N=cerrada(2, "k"), S=cerrada(3), E=Salida(4, False, "k", None))
        grafo, indice = self.construir([s1, sala(2), sala(3), sala(4)])
        norte, sur, este = grafo.sala(1).salidas
        self.assertEqual((norte.num_llave, norte.id_llave), (indice.numero("k"), "k"))
        self.assertEqual((sur.num_llave, sur.id_llave), (-1, None))
        self.assertEqual(este.num_llave, -1, "una salida abierta no pide llave aunque traiga el campo")

    def test_fr001_destino_valido(self):
        s1 = sala(1, N=abierta(2), S=abierta(99), E=abierta(0), O=abierta(4))
        grafo, _ = self.construir([s1, sala(2), sala(4)])
        validos = [(s.direccion, s.destino_valido) for s in grafo.sala(1).salidas]
        self.assertEqual(validos, [("N", True), ("S", False), ("E", False), ("O", True)])
        self.assertIsNone(grafo.salas[3])
        self.assertFalse(grafo.existe(3))
        self.assertFalse(grafo.existe(99))
        self.assertTrue(grafo.existe(4))
        self.assertEqual(len(grafo.salas), 5)

    def test_fr001_id_duplicado_conserva_la_primera(self):
        grafo, _ = self.construir([sala(1, E=abierta(2)), sala(2), sala(1, S=abierta(2))])
        self.assertEqual(direcciones(grafo.sala(1)), ["E"])
        self.assertEqual([s.origen for s in grafo.entrantes[2]], [1])

    def test_fr025_id_no_entero_o_negativo_lanza_value_error(self):
        for malo in ("tres", -1, 2.5, True, None):
            with self.subTest(id=malo):
                with self.assertRaises(ValueError) as ctx:
                    self.construir([sala(1), sala_con(malo, {})])
                self.assertIn(repr(malo), str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
