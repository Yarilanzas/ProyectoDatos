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


# --- T013: escenarios de US1 ------------------------------------------------------------------------------------

def orden_de(resultado):
    return [(o.id_llave, o.oleada, o.es_salida) for o in resultado.orden]


def puertas_de(lista):
    return [(p.origen, p.direccion, p.destino, p.destino_existe, p.llave) for p in lista]


def verificar(esqueleto, ubicaciones, sala_inicial=1, sala_salida=None, llave_salida="ks", cripta_id="c-prueba"):
    if sala_salida is None:
        sala_salida = esqueleto[-1].id
    return Resolubilidad.verificar(cripta_id, sala_inicial, sala_salida, llave_salida, esqueleto, ubicaciones)


class PruebasEscenariosUS1(unittest.TestCase):

    def test_us1_1_fr001_fr006_resoluble_sin_abrir_puertas(self):
        esqueleto = [sala(1, E=abierta(2)), sala(2, E=cerrada(3, "ks")), sala(3)]
        resultado = verificar(esqueleto, [llave("ks", 2)])
        self.assertTrue(resultado.resoluble)
        self.assertEqual(resultado.cripta_id, "c-prueba")
        self.assertEqual((resultado.sala_salida, resultado.llave_salida), (3, "ks"))
        self.assertEqual(orden_de(resultado), [("ks", 1, True)])

    def test_us1_2_fr007_cadena_en_oleadas_1_2_3(self):
        esqueleto = [sala(1, E=cerrada(2, "a")), sala(2, E=cerrada(3, "b")), sala(3, E=cerrada(4, "ks")), sala(4)]
        resultado = verificar(esqueleto, [llave("ks", 3), llave("b", 2), llave("a", 1)])
        self.assertTrue(resultado.resoluble)
        self.assertEqual(orden_de(resultado), [("a", 1, False), ("b", 2, False), ("ks", 3, True)])

    def test_fr007_ejemplo_c_d_a(self):
        """Desde el inicio se alcanzan C y D, y C abre la sala de A: el orden es C, D, A."""
        esqueleto = [sala(1, E=abierta(2), S=cerrada(3, "c")), sala(2), sala(3, E=cerrada(4, "a")), sala(4)]
        resultado = verificar(esqueleto, [llave("a", 3), llave("d", 2), llave("c", 1)], llave_salida="a")
        self.assertTrue(resultado.resoluble)
        self.assertEqual(orden_de(resultado), [("c", 1, False), ("d", 1, False), ("a", 2, True)])

    def test_us1_3_fr003_llave_de_enemigo_alcanzable_es_obtenible(self):
        esqueleto = [sala(1, E=abierta(2)), sala(2, E=cerrada(3, "ks")), sala(3)]
        resultado = verificar(esqueleto, [llave("ks", 2, enemigo="e-errante-1")])
        self.assertTrue(resultado.resoluble)
        self.assertEqual(orden_de(resultado), [("ks", 1, True)])

    def test_us1_4_fr004_cierres_automaticos_no_cambian_el_veredicto(self):
        sin = [sala(1, E=abierta(2), S=abierta(4)), sala(2, E=cerrada(3, "ks")), sala(3), sala(4, N=abierta(1))]
        con = [sala(1, E=abierta(2, cierre=1), S=abierta(4, cierre=3)), sala(2, E=cerrada(3, "ks", cierre=2)),
               sala(3), sala(4, N=abierta(1, cierre=1))]
        ubicaciones = [llave("ks", 4)]
        a, b = verificar(sin, ubicaciones, sala_salida=3), verificar(con, ubicaciones, sala_salida=3)
        self.assertTrue(a.resoluble)
        self.assertEqual((a.resoluble, orden_de(a)), (b.resoluble, orden_de(b)))

    def test_fr005_salidas_dirigidas(self):
        """A→B abierta y B→A cerrada sin llave: desde A se llega a B, desde B no se vuelve a A."""
        esqueleto = [sala(1, E=abierta(2), S=cerrada(3, "ks")), sala(2, O=cerrada(1)), sala(3)]
        desde_a = verificar(esqueleto, [llave("ks", 2)], sala_inicial=1, sala_salida=3)
        self.assertTrue(desde_a.resoluble)
        esqueleto = [sala(1, E=abierta(2)), sala(2, O=cerrada(1), S=cerrada(3, "ks")), sala(3)]
        desde_b = verificar(esqueleto, [llave("ks", 1)], sala_inicial=2, sala_salida=3)
        self.assertFalse(desde_b.resoluble)

    def test_fr002_llaves_no_consumidas(self):
        esqueleto = [sala(1, E=cerrada(2, "a")), sala(2, E=cerrada(3, "a")), sala(3, E=cerrada(4, "ks")), sala(4)]
        resultado = verificar(esqueleto, [llave("a", 1), llave("ks", 3)])
        self.assertTrue(resultado.resoluble)
        self.assertEqual(orden_de(resultado), [("a", 1, False), ("ks", 2, True)])

    def test_us1_6_fr009_salida_alcanzable_sin_puerta_con_llave_salida(self):
        esqueleto = [sala(1, E=abierta(2)), sala(2)]
        resultado = verificar(esqueleto, [llave("ks", 1)], sala_salida=2)
        self.assertFalse(resultado.resoluble)
        self.assertFalse(resultado.existe_puerta_salida)
        self.assertEqual(resultado.puertas_salida, [])
        self.assertEqual(resultado.orden, [])

    def test_fr009_puertas_salida_no_atravesables(self):
        """Todas las salidas hacia sala_salida que piden llave_salida y no se pueden cruzar, por origen y dirección."""
        esqueleto = [sala(1, E=abierta(2), S=cerrada(4, "ks")), sala(2, S=cerrada(4, "ks"), E=cerrada(4, "otra")),
                     sala(3, N=cerrada(4, "ks")), sala(4)]
        resultado = verificar(esqueleto, [llave("ks", 3)], sala_salida=4)
        self.assertFalse(resultado.resoluble)
        self.assertTrue(resultado.existe_puerta_salida)
        self.assertEqual(puertas_de(resultado.puertas_salida),
                         [(1, "S", 4, True, "ks"), (2, "S", 4, True, "ks"), (3, "N", 4, True, "ks")])

    def test_fr009_puerta_salida_hacia_sala_inexistente(self):
        esqueleto = [sala(1, E=cerrada(9, "ks"))]
        resultado = verificar(esqueleto, [llave("ks", 5)], sala_salida=9)
        self.assertFalse(resultado.resoluble)
        self.assertEqual(puertas_de(resultado.puertas_salida), [(1, "E", 9, False, "ks")])

    def test_fr001_sala_inicial_igual_a_sala_salida_exige_la_puerta(self):
        sin_puerta = verificar([sala(1)], [llave("ks", 1)], sala_inicial=1, sala_salida=1)
        self.assertFalse(sin_puerta.resoluble)
        self.assertFalse(sin_puerta.existe_puerta_salida)
        con_puerta = verificar([sala(1, N=cerrada(1, "ks"))], [llave("ks", 1)], sala_inicial=1, sala_salida=1)
        self.assertTrue(con_puerta.resoluble)

    def test_fr006_llaves_prescindibles_y_es_salida(self):
        esqueleto = [sala(1, E=abierta(2), S=cerrada(3, "ks")), sala(2, E=cerrada(4, "b")), sala(3), sala(4)]
        resultado = verificar(esqueleto, [llave("z", 2), llave("ks", 1), llave("b", 1), llave("m", 4)], sala_salida=3)
        self.assertTrue(resultado.resoluble)
        self.assertEqual(orden_de(resultado), [("b", 1, False), ("ks", 1, True), ("z", 1, False), ("m", 2, False)])

    def test_edge_fr001_sin_llave_salida_resoluble_si_sala_salida_alcanzable(self):
        esqueleto = [sala(1, E=abierta(2)), sala(2)]
        resultado = verificar(esqueleto, [llave("a", 1)], sala_salida=2, llave_salida=None)
        self.assertTrue(resultado.resoluble)
        self.assertEqual(orden_de(resultado), [("a", 1, False)])

    def test_edge_fr001_sin_llave_salida_no_resoluble_si_no_alcanzable(self):
        esqueleto = [sala(1, E=cerrada(2, "x")), sala(2)]
        resultado = verificar(esqueleto, [llave("a", 1)], sala_salida=2, llave_salida=None)
        self.assertFalse(resultado.resoluble)
        self.assertEqual(resultado.puertas_salida, [])
        for o in resultado.orden:
            self.assertFalse(o.es_salida)

    def test_edge_ubicacion_y_destino_inexistentes_no_detienen(self):
        esqueleto = [sala(1, E=abierta(7), S=cerrada(2, "ks")), sala(2)]
        resultado = verificar(esqueleto, [llave("ks", 50)], sala_salida=2)
        self.assertFalse(resultado.resoluble)

    def test_fr025_id_de_sala_invalido(self):
        with self.assertRaises(ValueError):
            verificar([sala(1), sala_con("dos", {})], [], sala_salida=1)

    def test_fr013_no_modifica_sus_argumentos(self):
        esqueleto = [sala(1, E=abierta(2), S=cerrada(3, "ks")), sala(2), sala(3)]
        ubicaciones = [llave("ks", 2, enemigo="e-1")]
        antes = ([s.a_json() for s in esqueleto], [(u.id_llave, u.sala, u.enemigo) for u in ubicaciones])
        verificar(esqueleto, ubicaciones, sala_salida=3)
        despues = ([s.a_json() for s in esqueleto], [(u.id_llave, u.sala, u.enemigo) for u in ubicaciones])
        self.assertEqual(antes, despues)


# --- T014: oráculo ingenuo (SC-001, SC-002) ---------------------------------------------------------------------
# Repite un recorrido completo por cada llave nueva. Solo listas usadas como arreglos o búsquedas lineales:
# sin dict, set ni deque (la regla del Principio I también vale para el oráculo).

def _buscar_sala_ingenuo(esqueleto, id_sala):
    for s in esqueleto:
        if s.id == id_sala:
            return s
    return None


def alcanzables_ingenuo(esqueleto, sala_inicial, obtenidas):
    """Salas alcanzables desde sala_inicial con las llaves `obtenidas` (lista de ids)."""
    if _buscar_sala_ingenuo(esqueleto, sala_inicial) is None:
        return []
    visitadas = [sala_inicial]
    pendiente = 0
    while pendiente < len(visitadas):
        actual = _buscar_sala_ingenuo(esqueleto, visitadas[pendiente])
        pendiente += 1
        for salida in actual.salidas.values():
            cruzable = (not salida.cerrada) or (salida.llave is not None and salida.llave in obtenidas)
            destino = salida.sala_destino
            if cruzable and destino not in visitadas and _buscar_sala_ingenuo(esqueleto, destino) is not None:
                visitadas.append(destino)
    return visitadas


def verificar_ingenuo(sala_inicial, sala_salida, llave_salida, esqueleto, ubicaciones):
    """Devuelve (resoluble, llaves obtenibles en el orden en que se hallaron)."""
    obtenidas = []
    while True:
        visitadas = alcanzables_ingenuo(esqueleto, sala_inicial, obtenidas)
        nuevas = []
        for u in ubicaciones:
            if u.sala in visitadas and u.id_llave not in obtenidas and u.id_llave not in nuevas:
                nuevas.append(u.id_llave)
        if not nuevas:
            break
        obtenidas.extend(nuevas)
    if llave_salida is None:
        return sala_salida in visitadas, obtenidas
    if llave_salida not in obtenidas:
        return False, obtenidas
    for id_sala in visitadas:
        for salida in _buscar_sala_ingenuo(esqueleto, id_sala).salidas.values():
            if salida.sala_destino == sala_salida and salida.cerrada and salida.llave == llave_salida:
                return True, obtenidas
    return False, obtenidas


def criptas_oraculo():
    from tests.generador_criptas import generar_cripta
    criptas = []
    for semilla in range(50):
        variante = semilla % 4
        salas = 15 + (semilla * 7) % 50
        llaves = 4 + semilla % 3
        if variante == 0:
            cripta = generar_cripta(semilla, salas, llaves)
        elif variante == 1:
            cripta = generar_cripta(semilla, salas, llaves, llave_de_enemigo=True)
        elif variante == 2:
            cripta = generar_cripta(semilla, salas, llaves, resoluble=False)
        else:
            cripta = generar_cripta(semilla, salas, llaves, resoluble=False, con_ciclo=True)
        criptas.append(cripta)
    return criptas


class PruebasOraculo(unittest.TestCase):

    def test_sc001_sc002_fr001_fr002_fr007_mismo_veredicto_y_orden_valido(self):
        resolubles = no_resolubles = 0
        for cripta in criptas_oraculo():
            d = cripta.detalles
            esqueleto, ubicaciones = cripta.esqueleto(), cripta.ubicaciones()
            with self.subTest(semilla=cripta.semilla):
                resultado = Resolubilidad.verificar(cripta.id_cripta, d.sala_inicial, d.sala_salida, d.llave_salida,
                                                    esqueleto, ubicaciones)
                esperado, obtenibles = verificar_ingenuo(d.sala_inicial, d.sala_salida, d.llave_salida,
                                                         esqueleto, ubicaciones)
                self.assertEqual(resultado.resoluble, esperado)
                if not esperado:
                    no_resolubles += 1
                    continue
                resolubles += 1
                orden = [o.id_llave for o in resultado.orden]
                # el orden lista exactamente las llaves obtenibles (FR-006)
                self.assertEqual(merge_sort(orden, lambda x: x)[0], merge_sort(obtenibles, lambda x: x)[0])
                # siguiendo el orden, cada llave se obtiene usando solo las anteriores (FR-007, SC-002)
                for i in range(len(orden)):
                    visitadas = alcanzables_ingenuo(esqueleto, d.sala_inicial, orden[:i])
                    lugares = [u.sala for u in ubicaciones if u.id_llave == orden[i]]
                    self.assertTrue(any(lugar in visitadas for lugar in lugares),
                                    f"{orden[i]} no se alcanza con {orden[:i]}")
                # oleadas no decrecientes y, dentro de cada una, por identificador (FR-007)
                for i in range(len(resultado.orden) - 1):
                    a, b = resultado.orden[i], resultado.orden[i + 1]
                    self.assertTrue(a.oleada < b.oleada or (a.oleada == b.oleada and a.id_llave < b.id_llave))
        self.assertGreater(resolubles, 0)
        self.assertGreater(no_resolubles, 0)


# --- T015: determinismo (SC-003) --------------------------------------------------------------------------------

SEMILLA_BARAJADO = 20261111


def como_tupla(resultado):
    """Todos los campos del resultado, en tuplas comparables campo por campo."""
    return (
        resultado.cripta_id, resultado.resoluble, resultado.sala_salida, resultado.llave_salida,
        tuple(orden_de(resultado)),
        tuple(resultado.no_obtenibles),
        tuple(puertas_de(resultado.frontera)),
        tuple(puertas_de(resultado.puertas_salida)),
        resultado.existe_puerta_salida,
        tuple((u.id_llave, tuple((l.sala, l.sala_existe, l.enemigo) for l in u.lugares))
              for u in resultado.ubicaciones),
        tuple((dep.id_llave, dep.depende_de) for dep in resultado.dependencias),
        tuple((tuple(c.llaves), c.directo) for c in resultado.ciclos),
    )


def barajar(esqueleto, ubicaciones, azar):
    salas = []
    for s in esqueleto:
        items = list(s.salidas.items())
        azar.shuffle(items)
        salas.append(SalaEsqueleto(s.id, s.nombre, dict(items)))
    azar.shuffle(salas)
    ubicaciones = list(ubicaciones)
    azar.shuffle(ubicaciones)
    return salas, ubicaciones


class PruebasDeterminismo(unittest.TestCase):

    def criptas(self):
        from tests.generador_criptas import generar_cripta
        return [generar_cripta(3, 40, 4), generar_cripta(4, 40, 4, llave_de_enemigo=True),
                generar_cripta(5, 40, 4, resoluble=False), generar_cripta(6, 40, 5, resoluble=False, con_ciclo=True)]

    def llamar(self, cripta, esqueleto, ubicaciones):
        d = cripta.detalles
        return Resolubilidad.verificar(cripta.id_cripta, d.sala_inicial, d.sala_salida, d.llave_salida,
                                       esqueleto, ubicaciones)

    def test_sc003_fr012_cien_llamadas_iguales(self):
        for cripta in self.criptas():
            esqueleto, ubicaciones = cripta.esqueleto(), cripta.ubicaciones()
            primero = como_tupla(self.llamar(cripta, esqueleto, ubicaciones))
            with self.subTest(semilla=cripta.semilla):
                for _ in range(100):
                    self.assertEqual(como_tupla(self.llamar(cripta, esqueleto, ubicaciones)), primero)

    def test_sc003_fr013_no_depende_del_orden_de_la_fuente(self):
        import random
        azar = random.Random(SEMILLA_BARAJADO)
        for cripta in self.criptas():
            esqueleto, ubicaciones = cripta.esqueleto(), cripta.ubicaciones()
            primero = como_tupla(self.llamar(cripta, esqueleto, ubicaciones))
            with self.subTest(semilla=cripta.semilla):
                for _ in range(100):
                    salas, lugares = barajar(esqueleto, ubicaciones, azar)
                    self.assertEqual(como_tupla(self.llamar(cripta, salas, lugares)), primero)

    def test_sc003_fr013_llave_en_varias_ubicaciones_barajadas(self):
        import random
        azar = random.Random(SEMILLA_BARAJADO)
        esqueleto = [sala(1, E=abierta(2), S=cerrada(3, "ks")), sala(2, E=abierta(1)), sala(3)]
        ubicaciones = [llave("ks", 2, enemigo="e-2"), llave("ks", 1), llave("b", 3), llave("ks", 2)]
        primero = como_tupla(verificar(esqueleto, ubicaciones, sala_salida=3))
        for _ in range(100):
            salas, lugares = barajar(esqueleto, ubicaciones, azar)
            self.assertEqual(como_tupla(verificar(salas, lugares, sala_salida=3)), primero)


# --- T016: prueba estática del Principio I ----------------------------------------------------------------------

MODULOS_PROHIBIDOS = ("heapq", "bisect", "collections", "networkx", "igraph", "graph_tool", "rustworkx", "scipy")
LLAMADAS_PROHIBIDAS = ("sorted", "dict", "set", "frozenset")
# sin red, archivos ni consola (Principio II, FR-023)
LLAMADAS_DE_E_S = ("print", "open", "input")
IMPORTS_PERMITIDOS = ("Modelo.ordenamiento", "Modelo.Estructuras")


def _permitido(modulo):
    return modulo == "DTOS" or modulo.startswith("DTOS.") or modulo in IMPORTS_PERMITIDOS


class PruebasPrincipioI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import ast
        with open(RUTA_MODULO, "r", encoding="utf-8") as archivo:
            cls.arbol = ast.parse(archivo.read(), filename=RUTA_MODULO)
        cls.nodos = list(ast.walk(cls.arbol))

    def modulos_importados(self):
        import ast
        modulos = []
        for nodo in self.nodos:
            if isinstance(nodo, ast.Import):
                modulos.extend((alias.name, nodo.lineno) for alias in nodo.names)
            elif isinstance(nodo, ast.ImportFrom):
                modulos.append(("." * nodo.level + (nodo.module or ""), nodo.lineno))
        return modulos

    def test_fr029_no_importa_estructuras_ni_bibliotecas_de_grafos(self):
        for modulo, linea in self.modulos_importados():
            raiz = modulo.split(".")[0]
            self.assertNotIn(raiz, MODULOS_PROHIBIDOS, f"línea {linea}: importa {modulo}")

    def test_fr023_solo_importa_dtos_ordenamiento_y_estructuras(self):
        modulos = self.modulos_importados()
        self.assertTrue(modulos, "el módulo debería importar al menos merge_sort y Queue")
        for modulo, linea in modulos:
            self.assertTrue(_permitido(modulo), f"línea {linea}: importa {modulo}")

    def test_fr001_fr029_no_llama_a_sorted_sort_dict_set(self):
        import ast
        for nodo in self.nodos:
            if not isinstance(nodo, ast.Call):
                continue
            if isinstance(nodo.func, ast.Name):
                self.assertNotIn(nodo.func.id, LLAMADAS_PROHIBIDAS, f"línea {nodo.lineno}: {nodo.func.id}(...)")
                self.assertNotIn(nodo.func.id, LLAMADAS_DE_E_S, f"línea {nodo.lineno}: {nodo.func.id}(...)")
            elif isinstance(nodo.func, ast.Attribute):
                self.assertNotEqual(nodo.func.attr, "sort", f"línea {nodo.lineno}: .sort(...)")

    def test_fr029_sin_literales_ni_comprensiones_de_dict_o_set(self):
        import ast
        for nodo in self.nodos:
            self.assertNotIsInstance(nodo, (ast.Dict, ast.Set, ast.DictComp, ast.SetComp),
                                     f"línea {getattr(nodo, 'lineno', '?')}: literal o comprensión de dict/set")


if __name__ == "__main__":
    unittest.main()
