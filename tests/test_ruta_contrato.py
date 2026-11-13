# Prueba de contrato de la interfaz de ruta de «ir a» (T043). Contrato: contracts/interfaz-ruta.md.
# FR-022, FR-023, FR-024, PR-10. Ejercita la interfaz sin mirar la implementación, con grafos de prueba
# pequeños, y está parametrizada por buscador:
# - contra `buscador_prueba` (utilidad de prueba, T042);
# - contra `primer_paso` de Modelo/rutas_ir_a.py (T063), que delega en Modelo/BusquedaRuta.py de Persona A
#   (D-PEND-01, opción A). Esa búsqueda es la misma que usa el cazador, y TestContratoBusquedaRuta la llama
#   directamente con la misma tabla de casos.

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


class TestContratoPrimerPaso(ContratoRuta, unittest.TestCase):
    buscar = staticmethod(primer_paso)


# ───────────────────────── Capacidad 003, T010 ─────────────────────────
# Modelo.BusquedaRuta se importa dentro de las clases nuevas (setUpClass) y con otro nombre: mientras no exista su
# `primer_paso`, solo fallan estas clases, y no se pisa el `primer_paso` de Modelo.rutas_ir_a importado arriba.


class TestContratoBusquedaRuta(ContratoRuta, unittest.TestCase):
    """T010 (a). Los casos del contrato de 001 contra `Modelo.BusquedaRuta.primer_paso`, llamado directamente
    (FR-011, FR-014; contracts/interfaz-ruta.md)."""

    @classmethod
    def setUpClass(cls):
        from Modelo.BusquedaRuta import primer_paso as primer_paso_busqueda
        cls.buscar = staticmethod(primer_paso_busqueda)


# Grafo para `limite`: 1 -E(100)-> 2 -E(150)-> 3, y un atajo caro 1 -S(400)-> 3. d(1, 3) = 250 por 2.
LINEA = ([1, 2, 3], [(1, "S", 3, 400), (1, "E", 2, 100), (2, "E", 3, 150)])

# Los mismos casos de desempate que ContratoRuta (obligación 2, FR-024): (ids, aristas, origen, destino, esperado).
DESEMPATES = (
    ([1, 2, 3, 4], [(1, "E", 3, 100), (1, "S", 2, 100), (3, "S", 4, 100), (2, "E", 4, 100)], 1, 4, ("S", 2, 200)),
    ([1, 2, 3, 4, 8, 9], [(1, "S", 3, 100), (3, "E", 4, 100), (4, "E", 9, 100),
                          (1, "E", 2, 100), (2, "E", 8, 100), (8, "S", 9, 100)], 1, 9, ("E", 2, 300)),
    ([1, 2], [(1, "E", 2, 100), (1, "N", 2, 100)], 1, 2, ("N", 2, 100)),
    ([1, 2], [(1, "O", 2, 100), (1, "S", 2, 100)], 1, 2, ("S", 2, 100)),
    ([1, 2], [(1, "O", 2, 100), (1, "E", 2, 100)], 1, 2, ("E", 2, 100)),
    ([1, 2], [(1, "N", 2, 300), (1, "E", 2, 100)], 1, 2, ("E", 2, 100)),
)

# Casos para comparar con y sin espacio: (ids, aristas, origen, destino, limite).
CASOS_ESPACIO = (
    LINEA + (1, 3, None),
    LINEA + (1, 3, 250),
    LINEA + (1, 3, 249),
    LINEA + (1, 3, 0),
    LINEA + (2, 1, None),                      # sin ruta
    DESEMPATES[0][:4] + (None,),
    DESEMPATES[1][:4] + (300,),
)


def resumen(paso):
    # (dirección, id de la vecina, costo_total), o None.
    return None if paso is None else (paso.direccion, paso.destino.id, paso.costo_total)


class TestLimiteBusquedaRuta(unittest.TestCase):
    """T010 (b). Los parámetros opcionales `limite` y `espacio` de `Modelo.BusquedaRuta.primer_paso`
    (contracts/interfaz-ruta.md, P-01 aceptada; research R2 y R3). No hereda de ContratoRuta."""

    @classmethod
    def setUpClass(cls):
        from Modelo.BusquedaRuta import EspacioBusqueda, primer_paso as primer_paso_busqueda
        cls.buscar = staticmethod(primer_paso_busqueda)
        cls.EspacioBusqueda = EspacioBusqueda

    def paso(self, grafo, origen, destino, **opciones):
        return self.buscar(grafo, grafo.sala(origen), grafo.sala(destino), **opciones)

    def test_fr012_d_igual_a_limite_devuelve_el_paso(self):
        """FR-012: si el costo mínimo d es igual a `limite`, la ruta está dentro del rango y se devuelve el paso."""
        grafo = GrafoPrueba(*LINEA)
        self.assertEqual(resumen(self.paso(grafo, 1, 3, limite=250)), ("E", 2, 250))

    def test_fr012_d_mayor_que_limite_devuelve_none(self):
        """FR-012: si d > `limite`, el resultado es None, aunque exista una ruta y su primer paso sea barato."""
        grafo = GrafoPrueba(*LINEA)
        self.assertIsNone(self.paso(grafo, 1, 3, limite=249))
        self.assertIsNone(self.paso(grafo, 1, 3, limite=100))

    def test_fr012_limite_cero_con_origen_distinto_de_destino_devuelve_none(self):
        """FR-012: con `limite=0` y origen distinto de destino no hay ruta posible, porque todo costo es ≥ 1."""
        grafo = GrafoPrueba([1, 2], [(1, "E", 2, 1)])
        self.assertIsNone(self.paso(grafo, 1, 2, limite=0))

    def test_fr033_mismo_resultado_con_y_sin_espacio(self):
        """FR-033: dar un `espacio` no cambia el resultado (dirección, destino y costo_total, o None) respecto de
        dejar que la función cree uno por llamada."""
        for ids, aristas, origen, destino, limite in CASOS_ESPACIO:
            with self.subTest(origen=origen, destino=destino, limite=limite, ids=ids):
                grafo = GrafoPrueba(ids, aristas)
                sin_espacio = self.paso(grafo, origen, destino, limite=limite)
                espacio = self.EspacioBusqueda(grafo.cantidad_salas)
                con_espacio = self.paso(grafo, origen, destino, limite=limite, espacio=espacio)
                self.assertEqual(resumen(con_espacio), resumen(sin_espacio))

    def test_fr033_llamadas_seguidas_con_el_mismo_espacio_no_se_contaminan(self):
        """FR-033: una segunda llamada con el mismo `espacio` da lo mismo que con un espacio nuevo, aunque la primera
        haya dejado distancias en salas que la segunda no puede alcanzar o no debe ver por su `limite`."""
        # 1 -E(100)-> 2 -E(100)-> 4;  3 -S(500)-> 4;  3 -E(100)-> 5 -S(100)-> 4.
        # La primera llamada (1 → 4) deja dist[2] = 100 y dist[4] = 200 con primer paso hacia 2.
        grafo = GrafoPrueba([1, 2, 3, 4, 5], [(1, "E", 2, 100), (2, "E", 4, 100), (3, "S", 4, 500),
                                              (3, "E", 5, 100), (5, "S", 4, 100)])
        segundas = (
            (3, 4, 300, ("E", 5, 200)),   # 4 vale 200 por 5; lo viejo diría «por 2», que no es vecina de 3
            (3, 2, None, None),           # 2 no es alcanzable desde 3, aunque la primera llamada lo fijó
            (3, 4, 199, None),            # 4 quedó a 200 en la primera llamada, pero aquí supera el límite
            (5, 4, None, ("S", 4, 100)),
        )
        for origen, destino, limite, esperado in segundas:
            with self.subTest(origen=origen, destino=destino, limite=limite):
                compartido = self.EspacioBusqueda(grafo.cantidad_salas)
                self.assertEqual(resumen(self.paso(grafo, 1, 4, espacio=compartido)), ("E", 2, 200))

                reutilizado = self.paso(grafo, origen, destino, limite=limite, espacio=compartido)
                nuevo = self.paso(grafo, origen, destino, limite=limite,
                                  espacio=self.EspacioBusqueda(grafo.cantidad_salas))
                self.assertEqual(resumen(reutilizado), resumen(nuevo))
                self.assertEqual(resumen(reutilizado), esperado)

    def test_fr014_tabla_de_desempates_con_limite_grande(self):
        """FR-014: con un `limite` mayor que cualquier ruta, los desempates del contrato (menor id de la primera
        vecina, primer paso y no último, N, S, E, O entre salidas a la misma vecina, la más barata) no cambian, en
        cualquier orden de `aristas`."""
        for ids, aristas, origen, destino, esperado in DESEMPATES:
            for orden in (aristas, invertido(aristas)):
                with self.subTest(ids=ids, aristas=orden):
                    grafo = GrafoPrueba(ids, orden)
                    self.assertEqual(resumen(self.paso(grafo, origen, destino, limite=10 ** 9)), esperado)

    def test_fr012_limite_none_equivale_a_no_pasarlo(self):
        """FR-012 (P-01): `limite=None` no pone cota; da lo mismo que llamar sin `limite`, con ruta y sin ruta."""
        for ids, aristas, origen, destino, _ in CASOS_ESPACIO + tuple(caso[:4] + (None,) for caso in DESEMPATES):
            with self.subTest(origen=origen, destino=destino, ids=ids):
                grafo = GrafoPrueba(ids, aristas)
                self.assertEqual(resumen(self.paso(grafo, origen, destino, limite=None)),
                                 resumen(self.paso(grafo, origen, destino)))


# ───────────────────────── 001, T062 y T063 ─────────────────────────


class TestPrimerPasoDelegaEnBusquedaRuta(unittest.TestCase):
    """T062/T063. `primer_paso` de «ir a» solo llama a `Modelo.BusquedaRuta.primer_paso` (D-PEND-01, opción A):
    acepta al final `limite` y `espacio` y da lo mismo que la búsqueda compartida (contracts/interfaz-ruta.md)."""

    @classmethod
    def setUpClass(cls):
        from Modelo.BusquedaRuta import EspacioBusqueda, primer_paso as primer_paso_busqueda
        cls.busqueda = staticmethod(primer_paso_busqueda)
        cls.EspacioBusqueda = EspacioBusqueda

    def test_fr024_pr10_misma_tabla_de_desempates_que_la_busqueda_compartida(self):
        for ids, aristas, origen, destino, esperado in DESEMPATES:
            for orden in (aristas, invertido(aristas)):
                with self.subTest(ids=ids, aristas=orden):
                    grafo = GrafoPrueba(ids, orden)
                    propio = primer_paso(grafo, grafo.sala(origen), grafo.sala(destino))
                    compartido = self.busqueda(grafo, grafo.sala(origen), grafo.sala(destino))
                    self.assertEqual(resumen(propio), esperado)
                    self.assertEqual(resumen(propio), resumen(compartido))

    def test_fr024_pr10_acepta_limite_y_espacio_al_final(self):
        for ids, aristas, origen, destino, limite in CASOS_ESPACIO:
            with self.subTest(origen=origen, destino=destino, limite=limite, ids=ids):
                grafo = GrafoPrueba(ids, aristas)
                espacio = self.EspacioBusqueda(grafo.cantidad_salas)
                propio = primer_paso(grafo, grafo.sala(origen), grafo.sala(destino), limite, espacio)
                compartido = self.busqueda(grafo, grafo.sala(origen), grafo.sala(destino), limite=limite)
                self.assertEqual(resumen(propio), resumen(compartido))

    def test_fr024_no_modifica_el_grafo(self):
        grafo = GrafoPrueba(*LINEA)
        antes = grafo.foto()
        primer_paso(grafo, grafo.sala(1), grafo.sala(3), espacio=self.EspacioBusqueda(grafo.cantidad_salas))
        self.assertEqual(grafo.foto(), antes)

    def test_principio_i_rutas_ir_a_no_usa_estructuras_prohibidas(self):
        """Principio I (obligación 6): Modelo/rutas_ir_a.py no importa heapq, bisect, collections ni networkx, ni
        llama a sorted() o a .sort()."""
        import ast
        ruta = os.path.join(RAIZ, "Modelo", "rutas_ir_a.py")
        with open(ruta, encoding="utf-8") as archivo:
            arbol = ast.parse(archivo.read())
        prohibidos = ("heapq", "bisect", "collections", "networkx")
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                for alias in nodo.names:
                    self.assertNotIn(alias.name.split(".")[0], prohibidos)
            elif isinstance(nodo, ast.ImportFrom):
                self.assertNotIn((nodo.module or "").split(".")[0], prohibidos)
            elif isinstance(nodo, ast.Call):
                funcion = nodo.func
                self.assertFalse(isinstance(funcion, ast.Name) and funcion.id == "sorted")
                self.assertFalse(isinstance(funcion, ast.Attribute) and funcion.attr == "sort")


if __name__ == "__main__":
    unittest.main()
