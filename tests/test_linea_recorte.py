# El recorte cuesta en proporción a lo recortado (spec 004, T043; Escenario US2-7; FR-027, SC-010). Sin red.
# El umbral numérico lo fija M4 (T104): aquí solo se comprueba que el tiempo no crece con `n` (razón entre dos tamaños por
# debajo de un margen generoso, mediana de varias repeticiones) y que el trabajo es V (posiciones y puntos retirados).

import os
import statistics
import sys
import time
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Modelo.LineaTiempo import LineaTiempo
from tests.utiles_linea import dar_pergaminos, preparar_motor_linea
from tests.utiles_terreno import armar_motor, cripta_terreno

V = 5          # cinco pergaminos seguidos: cada uno revierte una acción
MARGEN = 8.0   # razón máxima admitida entre el tiempo con n grande y con n chico (generoso: el tiempo debe ser plano)


def partida_larga(acciones, k=500):
    motor = armar_motor(cripta_terreno(1, 20), sala_jugador=1, cazadores=[], semilla=1)
    preparar_motor_linea(motor, espiar=False)
    dar_pergaminos(motor, V)
    linea = LineaTiempo(k=k)
    linea.iniciar(motor)
    for _ in range(acciones):
        assert motor.ejecutar_accion("esperar", "")
        linea.registrar_accion(motor, "esperar", "")
    return linea, motor


def recortar_v(linea, motor):
    """Usa V pergaminos seguidos. Devuelve (tiempos de cada registrar_retroceso, posiciones retiradas, puntos retirados)."""
    tiempos = []
    posiciones = 0
    puntos = 0
    for _ in range(V):
        antes_posiciones, antes_puntos = len(linea.vig_guion), len(linea.pc_accion)
        assert motor.ejecutar_accion("retroceder", "")
        inicio = time.perf_counter()
        linea.registrar_retroceso(motor)
        tiempos.append(time.perf_counter() - inicio)
        posiciones += antes_posiciones - len(linea.vig_guion)
        puntos += max(0, antes_puntos - len(linea.pc_accion))
    return tiempos, posiciones, puntos


class PruebasCostoDelRecorte(unittest.TestCase):

    def test_sc010_el_trabajo_del_recorte_es_v_en_partidas_de_500_y_5000_acciones(self):
        for acciones in (500, 5000):
            with self.subTest(acciones=acciones):
                linea, motor = partida_larga(acciones)
                n_antes = linea.acciones
                _tiempos, posiciones, _puntos = recortar_v(linea, motor)
                self.assertEqual(posiciones, V, "las posiciones retiradas son V, no dependen de n")
                self.assertEqual(linea.acciones, n_antes - V)
                self.assertEqual(len(linea.vig_reloj), n_antes - V)
                self.assertEqual(len(linea.vig_sec), n_antes - V)
                # cada punto retirado tenía accion > nuevo_n: a lo sumo uno por retroceso con K = 500
                for accion in linea.pc_accion:
                    self.assertLessEqual(accion, linea.acciones)

    def test_sc010_los_puntos_retirados_son_los_posteriores_al_nuevo_n(self):
        linea, motor = partida_larga(1003, k=1)          # un punto por acción: el peor caso para el recorte
        antes = len(linea.pc_accion)
        self.assertEqual(antes, 1004)
        assert motor.ejecutar_accion("retroceder", "")
        linea.registrar_retroceso(motor)
        # se retira el punto de la acción 1003 y se reemplaza el de la 1002 por el del motor real: 1 retirado
        self.assertEqual(len(linea.pc_accion), antes - 1)
        self.assertEqual(linea.pc_accion[-1], 1002)

    def test_sc010_el_tiempo_no_crece_con_n(self):
        medianas = []
        for acciones in (500, 5000):
            tiempos, _posiciones, _puntos = recortar_v(*partida_larga(acciones))
            medianas.append(statistics.median(tiempos))
        razon = medianas[1] / medianas[0]
        self.assertLess(razon, MARGEN,
                        f"el recorte con n = 5000 tardó {razon:.1f} veces lo que con n = 500 "
                        f"({medianas[1] * 1000:.2f} ms frente a {medianas[0] * 1000:.2f} ms)")


if __name__ == "__main__":
    unittest.main()
