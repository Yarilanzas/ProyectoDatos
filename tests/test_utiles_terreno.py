# Pruebas de tests/utiles_terreno.py (spec 003, T003): las criptas sintéticas y el motor sin red que usan las pruebas
# de equivalencia del cazador (FR-028) y el bench de escala (FR-033).

import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import random
import unittest

from tests.utiles_terreno import armar_motor, cripta_terreno, mapa_a_mano


def costos(cripta):
    # (origen, dirección, destino, costo) de cada salida, en el orden de salas_json
    resultado = []
    for sala in cripta.salas_json:
        for direccion in sala["salidas"]:
            salida = sala["salidas"][direccion]
            resultado.append((sala["id"], direccion, salida["sala"], salida["costo"]))
    return resultado


def costo_de(cripta, origen, destino):
    salidas = cripta.salas_json[origen - 1]["salidas"]
    for direccion in salidas:
        if salidas[direccion]["sala"] == destino:
            return salidas[direccion]["costo"]
    return None


class TestCriptaTerreno(unittest.TestCase):
    def test_fr033_misma_semilla_mismos_costos(self):
        a = cripta_terreno(7, 300, variacion=60)
        b = cripta_terreno(7, 300, variacion=60)
        self.assertEqual(costos(a), costos(b))
        self.assertNotEqual(costos(a), costos(cripta_terreno(8, 300, variacion=60)))

    def test_fr028_costos_distintos_por_sentido(self):
        cripta = cripta_terreno(3, 100, variacion=40)
        for origen, _, destino, costo in costos(cripta):
            vuelta = costo_de(cripta, destino, origen)
            self.assertIsNotNone(vuelta)
            self.assertNotEqual(costo, vuelta, f"{origen}↔{destino}")
            self.assertIsInstance(costo, int)
            self.assertGreaterEqual(costo, 1)

    def test_fr028_sin_variacion_ida_y_vuelta_fijas(self):
        cripta = cripta_terreno(3, 50, costo_ida=100, costo_vuelta=300)
        for origen, _, destino, costo in costos(cripta):
            self.assertEqual(costo, 100 if destino > origen else 300)

    def test_fr028_los_costos_llegan_a_las_salidas_del_esqueleto(self):
        cripta = cripta_terreno(5, 20, variacion=30)
        esperado = costos(cripta)
        leidos = []
        for sala in cripta.esqueleto():
            for direccion in sala.salidas:
                salida = sala.salidas[direccion]
                leidos.append((sala.id, direccion, salida.sala_destino, salida.costo))
        self.assertEqual(leidos, esperado)

    def test_fr033_diez_mil_salas_sin_error(self):
        cripta = cripta_terreno(11, 10_000, variacion=50)
        self.assertEqual(len(cripta.salas_json), 10_000)
        motor = armar_motor(cripta, 1, [(5_000, 10)])
        self.assertEqual(len(motor.salas), 10_000)

    def test_fr028_no_cambia_el_random_global(self):
        antes = random.getstate()
        cripta = cripta_terreno(9, 200, variacion=25)
        armar_motor(cripta, 1, [(50, 5), (150, 8)])
        mapa_a_mano([(1, [("E", 2, 300, False)]), (2, [("O", 1, 200, False)])], 1, [(2, 3)])
        self.assertEqual(random.getstate(), antes)


class TestArmarMotor(unittest.TestCase):
    def test_fr028_jugador_y_k_cazadores_en_las_salas_pedidas(self):
        cripta = cripta_terreno(2, 400, variacion=20)
        pedidos = [(10, 3), (200, 7), (399, 3), (10, 12)]
        motor = armar_motor(cripta, 50, pedidos)

        self.assertEqual(motor.jugador.sala.id, 50)
        self.assertEqual(motor.reloj, 0)
        self.assertEqual(len(motor.enemigos), len(pedidos))
        for indice in range(len(pedidos)):
            sala, rango = pedidos[indice]
            cazador = motor.enemigos[indice]
            self.assertEqual(cazador.sala.id, sala)
            self.assertIs(cazador.sala, motor.buscar_sala(motor.salas, sala))
            self.assertEqual(cazador.comportamiento, "cazador")
            self.assertEqual(motor.gestor_datos.obtener_ficha(cazador.tipo_id).rango, rango)

    def test_fr028_mapa_a_mano_con_costos_y_cerradas(self):
        motor = mapa_a_mano([
            (1, [("E", 2, 250, False), ("S", 3, None, True)]),
            (2, [("O", 1, 400, False)]),
            (3, []),
        ], sala_jugador=2, cazadores=[(1, 400)])

        sala1 = motor.buscar_sala(motor.salas, 1)
        self.assertEqual(motor.costo_salida(sala1.salidas["E"]), 250)
        self.assertEqual(motor.costo_salida(sala1.salidas["S"]), 100)
        self.assertTrue(sala1.salidas["S"].cerrada)
        self.assertEqual(motor.costo_salida(motor.jugador.sala.salidas["O"]), 400)
        self.assertEqual(motor.jugador.sala.id, 2)
        self.assertEqual(motor.enemigos[0].sala.id, 1)


if __name__ == "__main__":
    unittest.main()
