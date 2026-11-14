# Pruebas de campo_hacia en Modelo/BusquedaRuta.py (spec 003, T012; data-model §4.2 y §4.3; Persona A).
# Búsqueda al revés acotada hacia un destino: al terminar, toda sala u con época vigente en el espacio tiene en `dist`
# su distancia de costo mínimo hasta el destino (destino = 0) y esa distancia es <= cota; cualquier otra sala vale ∞.
#
# Interfaz que se prueba:
#   campo_hacia(grafo, destino, cota, espacio=None) -> EspacioBusqueda (el recibido o uno nuevo)
#   vigente(u)  <=>  espacio.epoca[grafo.ordinal(u)] == espacio.epoca_actual
#   dist(u)     =    espacio.dist[grafo.ordinal(u)], solo si vigente(u)
#   Cota inclusiva; usa la salida w->x con SU costo; solo salidas abiertas; cada llamada sube epoca_actual en 1;
#   un espacio de otra cantidad_salas lanza ValueError.
#
# campo_hacia se importa en setUpClass de cada clase y no al principio del archivo: mientras no exista, cada clase
# falla por separado.

import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import importlib
import random
import unittest

from Modelo.BusquedaRuta import EspacioBusqueda, primer_paso
from Modelo.GrafoCripta import GrafoCripta
from tests.utiles_terreno import armar_motor, cripta_terreno, mapa_a_mano

SEMILLAS = (1, 7, 23)
TAMANOS = (12, 30)
VARIACIONES = (None, 60)
COTAS = (0, 100, 250, 900, 5000)
PROPORCION_CERRADAS = 0.2


def sala_por_id(motor, id_sala):
    for sala in motor.salas:
        if sala.id == id_sala:
            return sala
    raise ValueError(f"La sala {id_sala!r} no existe")


def grafo_de(motor):
    return GrafoCripta(motor.salas, motor._destino, motor.costo_salida)


def es_vigente(grafo, espacio, sala):
    return espacio.epoca[grafo.ordinal(sala)] == espacio.epoca_actual


def vigentes(grafo, espacio, salas):
    """[(id, dist)] de las salas con época vigente, en el orden de `salas`."""
    resultado = []
    for sala in salas:
        if es_vigente(grafo, espacio, sala):
            resultado.append((sala.id, espacio.dist[grafo.ordinal(sala)]))
    return resultado


def cerrar_al_azar(motor, semilla):
    """Cierra salidas abiertas al azar con una instancia local de random (no toca el random global)."""
    azar = random.Random(semilla * 31 + 5)
    for sala in motor.salas:
        for direccion in sala.salidas:
            salida = sala.salidas[direccion]
            if not salida.cerrada and azar.random() < PROPORCION_CERRADAS:
                salida.cerrada = True


class ConCampo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.campo_hacia = staticmethod(importlib.import_module("Modelo.BusquedaRuta").campo_hacia)


class TestCoincideConPrimerPaso(ConCampo):
    def test_fr011_fr016_fr033_dist_igual_a_primer_paso_dentro_de_la_cota(self):
        """FR-011, FR-016, FR-033: en criptas sintéticas (con y sin variación, con puertas cerradas al azar), cada sala
        u distinta del destino queda vigente con dist == primer_paso(u, destino).costo_total si hay ruta y cuesta
        <= cota; si no hay ruta o cuesta más que la cota, no queda vigente."""
        for semilla in SEMILLAS:
            for tamano in TAMANOS:
                for variacion in VARIACIONES:
                    motor = armar_motor(cripta_terreno(semilla, tamano, variacion=variacion), 1, [])
                    cerrar_al_azar(motor, semilla)
                    grafo = grafo_de(motor)
                    azar = random.Random(semilla)
                    destinos = [motor.salas[0], motor.salas[-1], motor.salas[azar.randrange(len(motor.salas))]]
                    for destino in destinos:
                        referencia = []
                        for sala in motor.salas:
                            if sala is destino:
                                continue
                            paso = primer_paso(grafo, sala, destino)
                            referencia.append((sala, None if paso is None else paso.costo_total))
                        for cota in COTAS:
                            with self.subTest(semilla=semilla, tamano=tamano, variacion=variacion,
                                              destino=destino.id, cota=cota):
                                espacio = self.campo_hacia(grafo, destino, cota)
                                self.assertTrue(es_vigente(grafo, espacio, destino))
                                self.assertEqual(espacio.dist[grafo.ordinal(destino)], 0)
                                for sala, costo in referencia:
                                    if costo is not None and costo <= cota:
                                        self.assertTrue(es_vigente(grafo, espacio, sala),
                                                        f"sala {sala.id} a {costo} <= {cota} no quedó vigente")
                                        self.assertEqual(espacio.dist[grafo.ordinal(sala)], costo,
                                                         f"sala {sala.id}")
                                    else:
                                        self.assertFalse(es_vigente(grafo, espacio, sala),
                                                         f"sala {sala.id} (costo {costo}) quedó vigente con "
                                                         f"cota {cota}")


class TestCotaCero(ConCampo):
    def test_fr016_cota_cero_solo_el_destino(self):
        """FR-016: con cota 0 solo el destino queda vigente, con distancia 0."""
        motor = armar_motor(cripta_terreno(5, 25), 1, [])
        grafo = grafo_de(motor)
        destino = motor.salas[3]
        espacio = self.campo_hacia(grafo, destino, 0)
        self.assertEqual(vigentes(grafo, espacio, motor.salas), [(destino.id, 0)])


# Cadena 1 -> 2 -> 3 -> 4 con costos 100, 250, 75 (vueltas caras, 1000): distancias hacia 4: 425, 325, 75, 0.
CADENA = [
    (1, [("E", 2, 100, False)]),
    (2, [("E", 3, 250, False), ("O", 1, 1000, False)]),
    (3, [("E", 4, 75, False), ("O", 2, 1000, False)]),
    (4, [("O", 3, 1000, False)]),
]


class TestCotaExacta(ConCampo):
    def test_fr016_cota_inclusiva(self):
        """FR-016: la cota es inclusiva: con cota igual a la distancia de una sala, la sala entra; con cota - 1, no."""
        motor = mapa_a_mano(CADENA, sala_jugador=1)
        grafo = grafo_de(motor)
        cuatro = sala_por_id(motor, 4)

        espacio = self.campo_hacia(grafo, cuatro, 325)
        self.assertEqual(vigentes(grafo, espacio, motor.salas), [(2, 325), (3, 75), (4, 0)])

        espacio = self.campo_hacia(grafo, cuatro, 324)
        self.assertEqual(vigentes(grafo, espacio, motor.salas), [(3, 75), (4, 0)])

        espacio = self.campo_hacia(grafo, cuatro, 425)
        self.assertEqual(vigentes(grafo, espacio, motor.salas), [(1, 425), (2, 325), (3, 75), (4, 0)])

        espacio = self.campo_hacia(grafo, cuatro, 424)
        self.assertEqual(vigentes(grafo, espacio, motor.salas), [(2, 325), (3, 75), (4, 0)])


class TestDirigidas(ConCampo):
    def test_fr003_usa_el_costo_de_la_salida_w_a_x(self):
        """FR-003: con A->B 100 y B->A 500, el campo hacia A da dist[B] = 500 y hacia B da dist[A] = 100."""
        motor = mapa_a_mano([("A", [("E", "B", 100, False)]), ("B", [("O", "A", 500, False)])], sala_jugador="A")
        grafo = grafo_de(motor)
        a, b = sala_por_id(motor, "A"), sala_por_id(motor, "B")

        espacio = self.campo_hacia(grafo, a, 5000)
        self.assertEqual(vigentes(grafo, espacio, motor.salas), [("A", 0), ("B", 500)])

        espacio = self.campo_hacia(grafo, b, 5000)
        self.assertEqual(vigentes(grafo, espacio, motor.salas), [("A", 100), ("B", 0)])

        espacio = self.campo_hacia(grafo, a, 499)
        self.assertEqual(vigentes(grafo, espacio, motor.salas), [("A", 0)])

    def test_fr003_dos_salidas_hacia_la_misma_sala_gana_la_barata(self):
        """FR-003: si w tiene dos salidas abiertas hacia x con costos distintos, dist[w] usa la más barata."""
        motor = mapa_a_mano([
            (1, [("N", 2, 300, False), ("E", 2, 120, False), ("S", 2, 5, True)]),
            (2, []),
        ], sala_jugador=1)
        grafo = grafo_de(motor)
        espacio = self.campo_hacia(grafo, sala_por_id(motor, 2), 5000)
        self.assertEqual(vigentes(grafo, espacio, motor.salas), [(1, 120), (2, 0)])


class TestPuertasCerradas(ConCampo):
    def test_fr011_sala_tras_puerta_cerrada_y_luego_abierta(self):
        """FR-011: una sala que solo llega al destino por una puerta cerrada no queda vigente; al abrir la puerta
        (el grafo lee en vivo) y repetir, sí queda."""
        motor = mapa_a_mano([
            (1, [("E", 2, 100, False)]),
            (2, [("O", 1, 100, False)]),
            (3, [("N", 1, 200, True)]),
        ], sala_jugador=1)
        grafo = grafo_de(motor)
        uno = sala_por_id(motor, 1)

        espacio = self.campo_hacia(grafo, uno, 5000)
        self.assertEqual(vigentes(grafo, espacio, motor.salas), [(1, 0), (2, 100)])

        sala_por_id(motor, 3).salidas["N"].cerrada = False
        espacio = self.campo_hacia(grafo, uno, 5000)
        self.assertEqual(vigentes(grafo, espacio, motor.salas), [(1, 0), (2, 100), (3, 200)])


class TestEspacioPersistente(ConCampo):
    def test_fr033_con_espacio_igual_que_sin_espacio_y_devuelve_el_mismo(self):
        """FR-033: con un EspacioBusqueda propio el resultado es igual al de sin espacio y se devuelve el mismo
        espacio recibido."""
        motor = armar_motor(cripta_terreno(11, 30, variacion=40), 1, [])
        grafo = grafo_de(motor)
        espacio = EspacioBusqueda(grafo.cantidad_salas)
        for destino in (motor.salas[0], motor.salas[17]):
            for cota in (250, 900):
                with self.subTest(destino=destino.id, cota=cota):
                    sin = self.campo_hacia(grafo, destino, cota)
                    con = self.campo_hacia(grafo, destino, cota, espacio)
                    self.assertIs(con, espacio)
                    self.assertEqual(vigentes(grafo, con, motor.salas), vigentes(grafo, sin, motor.salas))

    def test_fr033_epoca_sube_en_uno_por_llamada(self):
        """FR-033: cada llamada sube epoca_actual del espacio exactamente en 1."""
        motor = armar_motor(cripta_terreno(4, 20), 1, [])
        grafo = grafo_de(motor)
        espacio = EspacioBusqueda(grafo.cantidad_salas)
        for indice in range(5):
            antes = espacio.epoca_actual
            self.campo_hacia(grafo, motor.salas[indice], COTAS[indice], espacio)
            self.assertEqual(espacio.epoca_actual, antes + 1)

    def test_fr033_dos_campos_seguidos_no_se_mezclan(self):
        """FR-033: dos campos seguidos sobre el mismo espacio con destinos distintos no se mezclan: manda el segundo."""
        motor = armar_motor(cripta_terreno(9, 30, variacion=50), 1, [])
        grafo = grafo_de(motor)
        primero, segundo = motor.salas[0], motor.salas[-1]
        esperado = vigentes(grafo, self.campo_hacia(grafo, segundo, 900), motor.salas)

        espacio = EspacioBusqueda(grafo.cantidad_salas)
        self.campo_hacia(grafo, primero, 5000, espacio)
        self.campo_hacia(grafo, segundo, 900, espacio)
        self.assertEqual(vigentes(grafo, espacio, motor.salas), esperado)
        self.assertEqual(espacio.dist[grafo.ordinal(segundo)], 0)


class TestEspacioDeOtroTamano(ConCampo):
    def test_fr033_espacio_de_otra_cantidad_de_salas_lanza_value_error(self):
        """FR-033: un espacio creado para otra cantidad de salas lanza ValueError."""
        motor = mapa_a_mano(CADENA, sala_jugador=1)
        grafo = grafo_de(motor)
        for cantidad in (grafo.cantidad_salas - 1, grafo.cantidad_salas + 1):
            with self.subTest(cantidad=cantidad):
                with self.assertRaises(ValueError):
                    self.campo_hacia(grafo, sala_por_id(motor, 4), 5000, EspacioBusqueda(cantidad))


class TestDeterminista(ConCampo):
    def test_fr011_dos_llamadas_identicas_dan_lo_mismo(self):
        """FR-011: dos llamadas idénticas dan las mismas distancias vigentes."""
        motor = armar_motor(cripta_terreno(23, 30, variacion=60), 1, [])
        cerrar_al_azar(motor, 23)
        grafo = grafo_de(motor)
        destino = motor.salas[12]
        uno = vigentes(grafo, self.campo_hacia(grafo, destino, 900), motor.salas)
        otro = vigentes(grafo, self.campo_hacia(grafo, destino, 900), motor.salas)
        self.assertEqual(uno, otro)
        self.assertTrue(len(uno) > 1, "el campo no alcanzó ninguna sala además del destino")


if __name__ == "__main__":
    unittest.main()
