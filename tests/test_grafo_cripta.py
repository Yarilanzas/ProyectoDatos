# Pruebas de GrafoCripta en Modelo/GrafoCripta.py (spec 003, T008; data-model §2, research R4; Persona A).
# El esqueleto real que ve el cazador: la cripta completa con el estado ACTUAL de las puertas, sin niebla y sin
# depender de Conocimiento. Principio I: estructuras propias, sin dict/set como índice, sin heapq, bisect ni
# collections, sin estado a nivel de módulo.
#
# Interfaz que se prueba:
#   GrafoCripta(salas, destino_de, costo_de)   en el juego: GrafoCripta(motor.salas, motor._destino, motor.costo_salida)
#   grafo.cantidad_salas    atributo entero n
#   grafo.ordinal(sala)     entero en [0, n), propio de GrafoCripta (no es el `_ordinal` de Conocimiento)
#   grafo.aristas(sala)     [(direccion, sala_destino, costo)], solo salidas ABIERTAS, en el orden de sala.salidas
#   grafo.entrantes(sala)   [(direccion, sala_origen, costo)], una por cada salida ABIERTA w->sala, con el costo y el
#                           estado de ESA salida
#
# Modelo.GrafoCripta se importa en setUpClass y no al principio del archivo: mientras el módulo no exista, solo
# fallan las pruebas de este archivo.

import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import ast
import importlib
import random
import unittest

from tests.utiles_terreno import armar_motor, cripta_terreno, mapa_a_mano

MODULOS_PROHIBIDOS = ("heapq", "bisect", "collections")
ATRIBUTOS_DE_CONOCIMIENTO = ("_ordinal", "_origen")
SEMILLAS = (1, 7, 23, 101, 4242)


def sala_por_id(motor, id_sala):
    for sala in motor.salas:
        if sala.id == id_sala:
            return sala
    raise ValueError(f"La sala {id_sala!r} no existe")


def ids(lista):
    """(direccion, id de la sala, costo) por cada tupla de aristas/entrantes, conservando el orden."""
    return [(direccion, sala.id, costo) for direccion, sala, costo in lista]


class ConModulo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modulo = importlib.import_module("Modelo.GrafoCripta")
        cls.GrafoCripta = cls.modulo.GrafoCripta

    def grafo_de(self, motor, salas=None):
        return self.GrafoCripta(motor.salas if salas is None else salas, motor._destino, motor.costo_salida)


# A->B cerrada (costo 250), B->A abierta (costo 100), A->C abierta sin costo declarado, C->A abierta (costo 7).
MAPA_DIRIGIDO = [
    ("A", [("E", "B", 250, True), ("S", "C", None, False)]),
    ("B", [("O", "A", 100, False)]),
    ("C", [("N", "A", 7, False)]),
]


class TestSinConocimiento(ConModulo):
    def test_fr015_funciona_en_motor_a_mano_sin_conocimiento(self):
        """FR-015: GrafoCripta no depende de Conocimiento; funciona en un motor armado a mano que no lo tiene."""
        motor = mapa_a_mano(MAPA_DIRIGIDO, sala_jugador="A")
        motor.conocimiento = None
        grafo = self.grafo_de(motor)

        a, b, c = (sala_por_id(motor, x) for x in ("A", "B", "C"))
        self.assertEqual(grafo.cantidad_salas, 3)
        self.assertEqual(sorted(grafo.ordinal(s) for s in (a, b, c)), [0, 1, 2])
        self.assertEqual(ids(grafo.aristas(a)), [("S", "C", 100)])
        self.assertEqual(ids(grafo.aristas(b)), [("O", "A", 100)])
        self.assertEqual(sorted(ids(grafo.entrantes(a))), [("N", "C", 7), ("O", "B", 100)])
        self.assertEqual(ids(grafo.entrantes(b)), [])
        self.assertEqual(ids(grafo.entrantes(c)), [("S", "A", 100)])


class TestOrdinales(ConModulo):
    def test_fr011_fr015_ordinales_propios_no_pisan_los_de_conocimiento(self):
        """FR-011, FR-015: ordinales 0..n-1 distintos, en el orden de la lista recibida, sin tocar `_ordinal` de
        Conocimiento (se pasa la lista invertida para que ambos órdenes difieran)."""
        motor = armar_motor(cripta_terreno(3, 30), 1, [])
        self.assertIsNotNone(motor.conocimiento, "armar_motor debería crear Conocimiento en iniciar_partida")
        antes = [sala._ordinal for sala in motor.salas]

        invertidas = list(reversed(motor.salas))
        grafo = self.grafo_de(motor, invertidas)

        self.assertIsInstance(grafo.cantidad_salas, int)
        self.assertEqual(grafo.cantidad_salas, len(motor.salas))
        ordinales = [grafo.ordinal(sala) for sala in invertidas]
        self.assertEqual(ordinales, list(range(len(invertidas))), "ordinal no sigue el orden de la lista pasada")
        self.assertTrue(all(isinstance(o, int) for o in ordinales))
        self.assertEqual([sala._ordinal for sala in motor.salas], antes, "GrafoCripta cambió `_ordinal`")
        self.assertNotEqual([grafo.ordinal(sala) for sala in motor.salas], antes,
                            "la prueba no distingue los dos ordinales")

    def test_fr011_ordinales_en_rango_en_motor_a_mano(self):
        """FR-011: cada ordinal está en [0, cantidad_salas) y no se repite."""
        motor = mapa_a_mano(MAPA_DIRIGIDO, sala_jugador="A")
        motor.conocimiento = None
        grafo = self.grafo_de(motor)
        ordinales = [grafo.ordinal(sala) for sala in motor.salas]
        self.assertEqual(ordinales, [0, 1, 2])
        for ordinal in ordinales:
            self.assertTrue(0 <= ordinal < grafo.cantidad_salas)


class TestAristas(ConModulo):
    def test_fr003_fr017_aristas_solo_abiertas_con_costo_salida(self):
        """FR-003, FR-017: aristas entrega solo salidas abiertas, en el orden de sala.salidas, con el costo de
        costo_salida; una salida sin costo declarado vale 100."""
        motor = mapa_a_mano([
            (1, [("N", 2, 300, False), ("S", 3, None, False), ("E", 4, 1, True), ("O", 5, 42, False)]),
            (2, []), (3, []), (4, []), (5, []),
        ], sala_jugador=1)
        grafo = self.grafo_de(motor)
        uno = sala_por_id(motor, 1)

        aristas = grafo.aristas(uno)
        self.assertEqual(ids(aristas), [("N", 2, 300), ("S", 3, 100), ("O", 5, 42)])
        for direccion, destino, costo in aristas:
            salida = uno.salidas[direccion]
            self.assertIs(destino, motor._destino(salida))
            self.assertEqual(costo, motor.costo_salida(salida))
        self.assertIsInstance(aristas, list)

    def test_fr003_aristas_usa_costo_de_y_no_lee_el_costo_por_su_cuenta(self):
        """FR-003: el costo de cada arista es el que entrega costo_de (en el juego, motor.costo_salida)."""
        motor = mapa_a_mano([(1, [("E", 2, 250, False)]), (2, [("O", 1, None, False)])], sala_jugador=1)
        grafo = self.GrafoCripta(motor.salas, motor._destino, lambda salida: motor.costo_salida(salida) * 3)
        self.assertEqual(ids(grafo.aristas(sala_por_id(motor, 1))), [("E", 2, 750)])
        self.assertEqual(ids(grafo.aristas(sala_por_id(motor, 2))), [("O", 1, 300)])


class TestEntrantes(ConModulo):
    def test_fr017_entrantes_con_costo_y_puerta_de_esa_salida(self):
        """FR-017: con A->B cerrada y B->A abierta, entrantes(A) incluye B->A y entrantes(B) no incluye A->B."""
        motor = mapa_a_mano(MAPA_DIRIGIDO, sala_jugador="A")
        grafo = self.grafo_de(motor)
        a, b = sala_por_id(motor, "A"), sala_por_id(motor, "B")

        entrantes_a = ids(grafo.entrantes(a))
        self.assertIn(("O", "B", 100), entrantes_a)
        self.assertNotIn("A", [origen for _, origen, _ in ids(grafo.entrantes(b))])
        self.assertEqual(grafo.entrantes(b), [])
        for direccion, origen, costo in grafo.entrantes(a):
            salida = origen.salidas[direccion]
            self.assertIs(motor._destino(salida), a)
            self.assertFalse(salida.cerrada)
            self.assertEqual(costo, motor.costo_salida(salida))

    def test_fr017_entrantes_incluye_varias_salidas_de_la_misma_sala_origen(self):
        """FR-017: una entrante por cada salida abierta w->sala, aunque w tenga dos salidas hacia sala."""
        motor = mapa_a_mano([
            (1, [("N", 3, 10, False), ("E", 3, 20, False), ("S", 3, 30, True)]),
            (2, [("O", 3, 40, False)]),
            (3, []),
        ], sala_jugador=1)
        grafo = self.grafo_de(motor)
        self.assertEqual(sorted(ids(grafo.entrantes(sala_por_id(motor, 3)))),
                         [("E", 1, 20), ("N", 1, 10), ("O", 2, 40)])

    def test_fr003_costos_distintos_por_sentido(self):
        """FR-003: con A->B 250 y B->A 100, cada entrante lleva el costo de su propia salida, no el de la vuelta."""
        motor = mapa_a_mano([("A", [("E", "B", 250, False)]), ("B", [("O", "A", 100, False)])], sala_jugador="A")
        grafo = self.grafo_de(motor)
        a, b = sala_por_id(motor, "A"), sala_por_id(motor, "B")
        self.assertEqual(ids(grafo.entrantes(b)), [("E", "A", 250)])
        self.assertEqual(ids(grafo.entrantes(a)), [("O", "B", 100)])
        self.assertEqual(ids(grafo.aristas(a)), [("E", "B", 250)])
        self.assertEqual(ids(grafo.aristas(b)), [("O", "A", 100)])


class TestPuertasEnVivo(ConModulo):
    def test_fr015_fr017_abrir_y_cerrar_despues_de_construir(self):
        """FR-015, FR-017: el estado de la puerta se lee en vivo; abrir o cerrar una salida después de construir el
        grafo cambia al instante aristas y entrantes."""
        motor = mapa_a_mano(MAPA_DIRIGIDO, sala_jugador="A")
        grafo = self.grafo_de(motor)
        a, b, c = (sala_por_id(motor, x) for x in ("A", "B", "C"))
        a_b, b_a, a_c = a.salidas["E"], b.salidas["O"], a.salidas["S"]

        a_b.cerrada = False
        self.assertEqual(ids(grafo.aristas(a)), [("E", "B", 250), ("S", "C", 100)])
        self.assertEqual(ids(grafo.entrantes(b)), [("E", "A", 250)])

        b_a.cerrada = True
        self.assertEqual(ids(grafo.aristas(b)), [])
        self.assertNotIn(("O", "B", 100), ids(grafo.entrantes(a)))

        a_c.cerrada = True
        a_b.cerrada = True
        self.assertEqual(ids(grafo.aristas(a)), [])
        self.assertEqual(ids(grafo.entrantes(b)), [])
        self.assertEqual(ids(grafo.entrantes(c)), [])

        b_a.cerrada = False
        a_c.cerrada = False
        self.assertEqual(ids(grafo.aristas(b)), [("O", "A", 100)])
        self.assertEqual(ids(grafo.entrantes(c)), [("S", "A", 100)])
        self.assertIn(("O", "B", 100), ids(grafo.entrantes(a)))


class TestConsistencia(ConModulo):
    def test_fr011_fr017_aristas_y_entrantes_describen_el_mismo_conjunto(self):
        """FR-011, FR-017: en criptas sintéticas con puertas cerradas al azar después de construir, el conjunto de
        (origen, direccion, destino, costo) de aristas es igual al de entrantes."""
        for semilla in SEMILLAS:
            with self.subTest(semilla=semilla):
                motor = armar_motor(cripta_terreno(semilla, 40, variacion=60), 1, [])
                grafo = self.grafo_de(motor)
                azar = random.Random(semilla)
                for sala in motor.salas:
                    for direccion in sala.salidas:
                        if azar.random() < 0.3:
                            sala.salidas[direccion].cerrada = not sala.salidas[direccion].cerrada

                desde_aristas = []
                desde_entrantes = []
                for sala in motor.salas:
                    for direccion, destino, costo in grafo.aristas(sala):
                        desde_aristas.append((sala.id, direccion, destino.id, costo))
                    for direccion, origen, costo in grafo.entrantes(sala):
                        desde_entrantes.append((origen.id, direccion, sala.id, costo))

                esperado = []
                for sala in motor.salas:
                    for direccion in sala.salidas:
                        salida = sala.salidas[direccion]
                        if not salida.cerrada:
                            esperado.append((sala.id, direccion, motor._destino(salida).id,
                                             motor.costo_salida(salida)))

                self.assertTrue(esperado, "la cripta no tiene salidas abiertas")
                self.assertEqual(sorted(desde_aristas), sorted(esperado))
                self.assertEqual(sorted(desde_entrantes), sorted(esperado))


class TestDeterminista(ConModulo):
    def test_fr011_dos_grafos_sobre_las_mismas_salas_coinciden(self):
        """FR-011: dos grafos construidos sobre las mismas salas dan los mismos ordinales y las mismas listas."""
        motor = armar_motor(cripta_terreno(11, 35, variacion=40), 1, [])
        uno = self.grafo_de(motor)
        otro = self.grafo_de(motor)
        self.assertEqual(uno.cantidad_salas, otro.cantidad_salas)
        for sala in motor.salas:
            self.assertEqual(uno.ordinal(sala), otro.ordinal(sala))
            self.assertEqual(ids(uno.aristas(sala)), ids(otro.aristas(sala)))
            self.assertEqual(ids(uno.entrantes(sala)), ids(otro.entrantes(sala)))


class TestEstructuraPropia(ConModulo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with open(cls.modulo.__file__, encoding="utf-8") as archivo:
            cls.arbol = ast.parse(archivo.read())

    def test_principio_i_fr015_no_importa_conocimiento_heapq_bisect_ni_collections(self):
        """FR-015, Principio I: no importa Modelo.Conocimiento, heapq, bisect ni collections."""
        for nodo in ast.walk(self.arbol):
            if isinstance(nodo, ast.Import):
                nombres = [alias.name for alias in nodo.names]
            elif isinstance(nodo, ast.ImportFrom):
                nombres = [nodo.module or ""] + [f"{nodo.module}.{alias.name}" for alias in nodo.names]
            else:
                continue
            for nombre in nombres:
                self.assertNotIn(nombre.split(".")[0], MODULOS_PROHIBIDOS,
                                 f"Modelo/GrafoCripta.py importa {nombre} (línea {nodo.lineno})")
                self.assertNotIn("Conocimiento", nombre.split("."),
                                 f"Modelo/GrafoCripta.py importa {nombre} (línea {nodo.lineno})")

    def test_fr015_no_usa_ordinal_origen_ni_entrantes_de_conocimiento(self):
        """FR-015: no accede a `_ordinal` ni `_origen` (nombre exacto, ni por getattr/setattr/hasattr) ni usa el
        `entrantes` de Conocimiento."""
        for nodo in ast.walk(self.arbol):
            if isinstance(nodo, ast.Attribute):
                self.assertNotIn(nodo.attr, ATRIBUTOS_DE_CONOCIMIENTO,
                                 f"accede a .{nodo.attr} en la línea {nodo.lineno}")
                self.assertNotEqual(nodo.attr.lower(), "conocimiento",
                                    f"accede a .{nodo.attr} en la línea {nodo.lineno}")
                if nodo.attr == "entrantes":
                    self.assertTrue(isinstance(nodo.value, ast.Name) and nodo.value.id == "self",
                                    f"usa un `entrantes` ajeno en la línea {nodo.lineno}")
            elif isinstance(nodo, ast.Name):
                self.assertNotEqual(nodo.id.lower(), "conocimiento", f"usa {nodo.id} en la línea {nodo.lineno}")
            elif (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name)
                  and nodo.func.id in ("getattr", "setattr", "hasattr", "delattr") and len(nodo.args) >= 2
                  and isinstance(nodo.args[1], ast.Constant)):
                self.assertNotIn(nodo.args[1].value, ATRIBUTOS_DE_CONOCIMIENTO,
                                 f"{nodo.func.id}(..., {nodo.args[1].value!r}) en la línea {nodo.lineno}")

    def test_principio_i_sin_dict_ni_set(self):
        """FR-011, Principio I: sin literales ni comprensiones de dict/set y sin llamadas a dict() o set()."""
        prohibidos = (ast.Dict, ast.Set, ast.DictComp, ast.SetComp)
        for nodo in ast.walk(self.arbol):
            self.assertNotIsInstance(nodo, prohibidos,
                                     f"{type(nodo).__name__} en la línea {getattr(nodo, 'lineno', '?')}")
            if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name):
                self.assertNotIn(nodo.func.id, ("dict", "set", "frozenset"),
                                 f"llamada a {nodo.func.id}() en la línea {nodo.lineno}")

    def test_principio_i_sin_estado_a_nivel_de_modulo(self):
        """Principio I: en el nivel del módulo solo hay docstring, imports, funciones, clases y constantes
        inmutables en MAYÚSCULAS; ninguna función usa `global`."""
        def es_inmutable(valor):
            if isinstance(valor, ast.Constant):
                return True
            if isinstance(valor, ast.UnaryOp) and isinstance(valor.operand, ast.Constant):
                return True
            if isinstance(valor, ast.Tuple):
                return all(es_inmutable(elemento) for elemento in valor.elts)
            if (isinstance(valor, ast.Call) and isinstance(valor.func, ast.Name) and valor.func.id == "float"
                    and not valor.keywords and len(valor.args) == 1 and isinstance(valor.args[0], ast.Constant)):
                return True
            return False

        for posicion, nodo in enumerate(self.arbol.body):
            if isinstance(nodo, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)):
                continue
            if posicion == 0 and isinstance(nodo, ast.Expr) and isinstance(nodo.value, ast.Constant):
                continue  # docstring del módulo
            if isinstance(nodo, (ast.Assign, ast.AnnAssign)):
                destinos = nodo.targets if isinstance(nodo, ast.Assign) else [nodo.target]
                constante = (all(isinstance(d, ast.Name) and d.id.isupper() for d in destinos)
                             and nodo.value is not None and es_inmutable(nodo.value))
                self.assertTrue(constante, f"estado a nivel de módulo en la línea {nodo.lineno}")
                continue
            self.fail(f"sentencia no permitida a nivel de módulo en la línea {nodo.lineno}: {type(nodo).__name__}")

        for nodo in ast.walk(self.arbol):
            self.assertNotIsInstance(nodo, (ast.Global, ast.Nonlocal),
                                     f"`global`/`nonlocal` en la línea {getattr(nodo, 'lineno', '?')}")


if __name__ == "__main__":
    unittest.main()
