# Pruebas de EspacioBusqueda en Modelo/BusquedaRuta.py (spec 003, T006; data-model §4.3, research R2, R3, R6;
# Persona A, D-PEND-01). Principio I: listas densas propias por ordinal con marca de época y una ColaPrioridad propia,
# sin dict/set como índice, sin heapq, bisect ni collections, sin estado a nivel de módulo.
#
# Interfaz que se prueba (data-model §4.3, más los nombres decididos para T006):
#   EspacioBusqueda(n)        crea dist, primero y epoca de tamaño n y su cola. O(n), una vez.
#   espacio.dist / .primero / .epoca   listas de tamaño n indexadas por ordinal.
#   espacio.epoca_actual      entero; una entrada i vale solo si epoca[i] == epoca_actual.
#   espacio.cola              ColaPrioridad reutilizable entre búsquedas.
#   espacio.reiniciar()       epoca_actual aumenta y la cola queda vacía. O(1): no recorre las listas.
#   espacio.validar(grafo)    ValueError si grafo.cantidad_salas no es el n con que se creó el espacio.
#
# Modelo.BusquedaRuta se importa en setUpClass y no al principio del archivo: mientras el módulo no exista, solo
# fallan las pruebas de este archivo.

import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import ast
import importlib
import unittest

from Modelo.ColaPrioridad import ColaPrioridad

MODULOS_PROHIBIDOS = ("heapq", "bisect", "collections")


class GrafoFalso:
    """Lo único que EspacioBusqueda mira del grafo: ``cantidad_salas`` (atributo, como en el contrato de 001)."""

    def __init__(self, cantidad_salas):
        self.cantidad_salas = cantidad_salas


class ListaEspia(list):
    """Lista que anota cada operación que recibe. Sirve para demostrar que reiniciar no recorre ni toca las listas."""

    def __init__(self, *args):
        super().__init__(*args)
        self.operaciones = []


def _espiar(nombre):
    original = getattr(list, nombre)

    def metodo(self, *args, **kwargs):
        self.operaciones.append(nombre)
        return original(self, *args, **kwargs)

    metodo.__name__ = nombre
    return metodo


for _nombre in (
    "__getitem__", "__setitem__", "__delitem__", "__iter__", "__reversed__", "__len__", "__contains__",
    "__iadd__", "__imul__", "append", "extend", "insert", "pop", "remove", "clear", "index", "count", "sort",
    "reverse", "copy",
):
    setattr(ListaEspia, _nombre, _espiar(_nombre))
del _nombre


def vigente(espacio, indice):
    """Regla de data-model §4.2 y §4.3: una entrada vale solo si su época coincide con la del espacio."""
    return espacio.epoca[indice] == espacio.epoca_actual


class ConModulo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modulo = importlib.import_module("Modelo.BusquedaRuta")
        cls.EspacioBusqueda = cls.modulo.EspacioBusqueda


class TestTamano(ConModulo):
    def test_fr033_principio_i_dist_primero_y_epoca_tienen_tamano_n(self):
        for n in (1, 2, 7, 100, 10_000):
            espacio = self.EspacioBusqueda(n)
            self.assertIsInstance(espacio.dist, list)
            self.assertIsInstance(espacio.primero, list)
            self.assertIsInstance(espacio.epoca, list)
            self.assertEqual(len(espacio.dist), n)
            self.assertEqual(len(espacio.primero), n)
            self.assertEqual(len(espacio.epoca), n)

    def test_fr033_principio_i_listas_distintas_entre_si_y_entre_espacios(self):
        # Tres listas propias por espacio y nada compartido entre espacios: escribir en una no cambia otra.
        uno = self.EspacioBusqueda(5)
        otro = self.EspacioBusqueda(5)
        listas = [uno.dist, uno.primero, uno.epoca, otro.dist, otro.primero, otro.epoca]
        for i in range(len(listas)):
            for j in range(i + 1, len(listas)):
                self.assertIsNot(listas[i], listas[j])
        self.assertIsNot(uno.cola, otro.cola)

    def test_fr033_principio_i_tamano_no_depende_de_reiniciar(self):
        espacio = self.EspacioBusqueda(9)
        for _ in range(5):
            espacio.reiniciar()
        self.assertEqual((len(espacio.dist), len(espacio.primero), len(espacio.epoca)), (9, 9, 9))


class TestEpoca(ConModulo):
    def test_fr033_principio_i_epoca_actual_es_entero(self):
        espacio = self.EspacioBusqueda(4)
        self.assertIsInstance(espacio.epoca_actual, int)

    def test_fr033_principio_i_espacio_nuevo_no_tiene_entradas_vigentes(self):
        # Si epoca empezara igual a epoca_actual, la primera búsqueda leería basura como distancias válidas.
        espacio = self.EspacioBusqueda(50)
        for indice in range(50):
            self.assertFalse(vigente(espacio, indice), f"la entrada {indice} vale sin que nadie la escribiera")

    def test_fr033_principio_i_entrada_vale_solo_si_su_epoca_coincide(self):
        espacio = self.EspacioBusqueda(6)
        espacio.reiniciar()
        actual = espacio.epoca_actual

        espacio.dist[2] = 300
        espacio.primero[2] = 4
        espacio.epoca[2] = actual
        espacio.dist[3] = 100
        espacio.epoca[3] = actual - 1  # escrita en una búsqueda anterior
        espacio.dist[5] = 200
        espacio.epoca[5] = actual + 1  # época que todavía no ocurrió

        self.assertTrue(vigente(espacio, 2))
        self.assertFalse(vigente(espacio, 3))
        self.assertFalse(vigente(espacio, 5))
        for indice in (0, 1, 4):
            self.assertFalse(vigente(espacio, indice))

    def test_fr033_principio_i_reiniciar_aumenta_epoca_actual(self):
        espacio = self.EspacioBusqueda(3)
        anterior = espacio.epoca_actual
        for _ in range(20):
            espacio.reiniciar()
            self.assertIsInstance(espacio.epoca_actual, int)
            self.assertGreater(espacio.epoca_actual, anterior)
            anterior = espacio.epoca_actual

    def test_fr033_principio_i_reiniciar_invalida_todas_las_entradas(self):
        n = 200
        espacio = self.EspacioBusqueda(n)
        espacio.reiniciar()
        for indice in range(n):
            espacio.dist[indice] = indice * 100
            espacio.primero[indice] = (indice + 1) % n
            espacio.epoca[indice] = espacio.epoca_actual
        self.assertTrue(all(vigente(espacio, indice) for indice in range(n)))

        espacio.reiniciar()
        for indice in range(n):
            self.assertFalse(vigente(espacio, indice), f"la entrada {indice} sigue valiendo tras reiniciar")

    def test_fr033_principio_i_entradas_de_epocas_viejas_nunca_vuelven_a_valer(self):
        # La época solo aumenta: lo escrito en la búsqueda k no vale en k + 1, k + 2, ... (R2: no se reinicia).
        espacio = self.EspacioBusqueda(4)
        espacio.reiniciar()
        espacio.dist[1] = 700
        espacio.epoca[1] = espacio.epoca_actual
        for _ in range(30):
            espacio.reiniciar()
            self.assertFalse(vigente(espacio, 1))

    def test_fr033_principio_i_tras_reiniciar_se_puede_escribir_en_la_nueva_epoca(self):
        espacio = self.EspacioBusqueda(4)
        espacio.reiniciar()
        espacio.dist[0] = 500
        espacio.epoca[0] = espacio.epoca_actual
        espacio.reiniciar()
        espacio.dist[0] = 100
        espacio.epoca[0] = espacio.epoca_actual
        self.assertTrue(vigente(espacio, 0))
        self.assertEqual(espacio.dist[0], 100)


class TestReinicioConstante(ConModulo):
    def _con_espias(self, n):
        espacio = self.EspacioBusqueda(n)
        espacio.dist = ListaEspia(espacio.dist)
        espacio.primero = ListaEspia(espacio.primero)
        espacio.epoca = ListaEspia(espacio.epoca)
        return espacio

    def test_fr033_principio_i_reiniciar_no_toca_dist_primero_ni_epoca(self):
        # Prueba de O(1): reiniciar no lee, no escribe, no recorre y no reemplaza ninguna de las tres listas. Si las
        # recorriera, su costo crecería con n y rompería FR-033.
        espacio = self._con_espias(1000)
        dist, primero, epoca = espacio.dist, espacio.primero, espacio.epoca
        antes = (list.copy(dist), list.copy(primero), list.copy(epoca))

        for _ in range(10):
            espacio.reiniciar()

        self.assertIs(espacio.dist, dist, "reiniciar reemplazó dist por otra lista")
        self.assertIs(espacio.primero, primero, "reiniciar reemplazó primero por otra lista")
        self.assertIs(espacio.epoca, epoca, "reiniciar reemplazó epoca por otra lista")
        self.assertEqual(dist.operaciones, [], "reiniciar tocó dist")
        self.assertEqual(primero.operaciones, [], "reiniciar tocó primero")
        self.assertEqual(epoca.operaciones, [], "reiniciar tocó epoca")
        self.assertEqual((list.copy(dist), list.copy(primero), list.copy(epoca)), antes)

    def test_fr033_principio_i_reiniciar_no_depende_de_n(self):
        # Mismo resultado observable con n chico y n grande: solo cambia epoca_actual y la cola queda vacía.
        for n in (1, 10, 100_000):
            espacio = self._con_espias(n)
            anterior = espacio.epoca_actual
            espacio.reiniciar()
            self.assertGreater(espacio.epoca_actual, anterior)
            self.assertEqual(espacio.dist.operaciones + espacio.primero.operaciones + espacio.epoca.operaciones, [])


class TestValidar(ConModulo):
    def test_fr033_principio_i_validar_acepta_grafo_con_la_misma_cantidad_de_salas(self):
        for n in (1, 3, 64):
            espacio = self.EspacioBusqueda(n)
            espacio.validar(GrafoFalso(n))  # no lanza

    def test_fr033_principio_i_validar_rechaza_otra_cantidad_de_salas(self):
        espacio = self.EspacioBusqueda(10)
        for otra in (0, 1, 9, 11, 1000):
            with self.assertRaises(ValueError, msg=f"un espacio de 10 salas aceptó un grafo de {otra}"):
                espacio.validar(GrafoFalso(otra))

    def test_fr033_principio_i_validar_usa_el_n_de_creacion_y_no_cambia_el_espacio(self):
        espacio = self.EspacioBusqueda(5)
        espacio.reiniciar()
        epoca_actual = espacio.epoca_actual
        with self.assertRaises(ValueError):
            espacio.validar(GrafoFalso(6))
        # Un rechazo no agranda las listas para el grafo nuevo ni reinicia la búsqueda.
        self.assertEqual((len(espacio.dist), len(espacio.primero), len(espacio.epoca)), (5, 5, 5))
        self.assertEqual(espacio.epoca_actual, epoca_actual)
        espacio.validar(GrafoFalso(5))


class TestCola(ConModulo):
    def test_fr011_fr033_principio_i_la_cola_es_una_cola_prioridad(self):
        espacio = self.EspacioBusqueda(8)
        self.assertIsInstance(espacio.cola, ColaPrioridad)
        self.assertTrue(espacio.cola.vacia())

    def test_fr033_principio_i_reiniciar_vacia_la_cola(self):
        espacio = self.EspacioBusqueda(8)
        for ordinal in range(8):
            espacio.cola.insertar(100 * ordinal, ordinal)
        self.assertFalse(espacio.cola.vacia())
        espacio.reiniciar()
        self.assertTrue(espacio.cola.vacia())
        self.assertIsNone(espacio.cola.extraer_minimo())

    def test_fr033_principio_i_la_misma_cola_se_reutiliza_entre_busquedas(self):
        # No se crea una cola por búsqueda: es el mismo objeto antes y después de reiniciar, y sigue sirviendo.
        espacio = self.EspacioBusqueda(8)
        cola = espacio.cola
        for busqueda in range(3):
            espacio.reiniciar()
            self.assertIs(espacio.cola, cola)
            self.assertTrue(cola.vacia())
            cola.insertar(300, 2 + busqueda)
            cola.insertar(100, 5)
            self.assertEqual(cola.extraer_minimo(), (100, 5))
        espacio.reiniciar()
        self.assertIs(espacio.cola, cola)
        self.assertTrue(cola.vacia())


class TestEstructuraPropia(ConModulo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with open(cls.modulo.__file__, encoding="utf-8") as archivo:
            cls.arbol = ast.parse(archivo.read())

    def test_fr033_principio_i_no_importa_heapq_bisect_ni_collections(self):
        for nodo in ast.walk(self.arbol):
            if isinstance(nodo, ast.Import):
                nombres = [alias.name for alias in nodo.names]
            elif isinstance(nodo, ast.ImportFrom):
                nombres = [nodo.module or ""]
            else:
                continue
            for nombre in nombres:
                self.assertNotIn(nombre.split(".")[0], MODULOS_PROHIBIDOS,
                                 f"Modelo/BusquedaRuta.py importa {nombre} (línea {nodo.lineno})")

    def test_fr033_principio_i_sin_estado_a_nivel_de_modulo(self):
        # En el nivel del módulo solo hay docstring, imports, funciones, clases y constantes inmutables en MAYÚSCULAS
        # (por ejemplo INFINITO = float("inf")). Nada de listas, dicts, cachés ni objetos creados al importar.
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

    def test_fr033_principio_i_ninguna_funcion_escribe_variables_del_modulo(self):
        for nodo in ast.walk(self.arbol):
            self.assertNotIsInstance(nodo, ast.Global, f"`global` en la línea {getattr(nodo, 'lineno', '?')}")


if __name__ == "__main__":
    unittest.main()
