# Pruebas de motor.costo_salida (T118). FR-005: cada salida muestra su costo, 100 si no lo declara.
# FR-024 y PR-13: es el único acceso al costo. `mover` usa el costo de la salida: costo * 100 // velocidad.

import os
import sys

# Permite ejecutar este archivo desde cualquier carpeta (PyCharm, unittest o pytest).
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import unittest
from types import SimpleNamespace

from DTOS.Salida import Salida
from Modelo.MotorSimulacion import COSTO_MOVER, MotorSimulacion
from Modelo.prueba_actores import GestorPrueba, JugadorPrueba, sala


class TestCostoSalida(unittest.TestCase):
    def setUp(self):
        self.motor = MotorSimulacion(semilla=1)

    def test_fr005_costo_por_defecto_vale_100(self):
        self.assertEqual(COSTO_MOVER, 100)

    def test_fr005_devuelve_el_costo_propio_de_la_salida(self):
        salida = SimpleNamespace(costo=250)
        self.assertEqual(self.motor.costo_salida(salida), 250)

    def test_fr005_salida_sin_el_atributo_cuesta_100(self):
        salida = SimpleNamespace(sala_destino=2, cerrada=False)
        self.assertEqual(self.motor.costo_salida(salida), 100)

    def test_fr005_salida_con_costo_none_cuesta_100(self):
        self.assertEqual(self.motor.costo_salida(SimpleNamespace(costo=None)), 100)

    def test_fr005_salida_del_dto_actual_cuesta_100(self):
        # El DTO aún no tiene el campo: lo agrega la capacidad de terreno y costos.
        self.assertEqual(self.motor.costo_salida(Salida(2, False, None, None)), 100)

    def test_fr005_solo_lee_la_salida(self):
        salida = SimpleNamespace(sala_destino=2)
        self.motor.costo_salida(salida)
        self.assertEqual(vars(salida), {"sala_destino": 2})


class TestMoverUsaElCosto(unittest.TestCase):
    # FR-005: `mover` usa el costo de la salida que atraviesa (costo * 100 // velocidad); sin costo declarado, 100.

    def preparar(self, velocidad=100, costo=None):
        s1, s2 = sala("s1"), sala("s2")
        s1.salidas["E"] = SimpleNamespace(sala_destino="s2", cerrada=False, llave=None,
                                          cierre_automatico=None, costo=costo)
        motor = MotorSimulacion(semilla=1, gestor_datos=GestorPrueba())
        jugador = JugadorPrueba(s1, velocidad=velocidad)
        motor.jugador = jugador
        motor.salas = [s1, s2]
        motor._salas_contenido_cargado = ["s1", "s2"]
        motor.activar_enemigos_de_sala = lambda _s: None
        jugador.evento_actual = motor.programar_evento(0, "ACCION_ACTOR", jugador)
        motor.avanzar_hasta_jugador()   # consume el turno inicial, como al empezar la partida
        return motor

    def test_fr005_mover_sin_costo_declarado_cuesta_100(self):
        motor = self.preparar()
        self.assertTrue(motor.ejecutar_accion("mover", "E"))
        self.assertEqual(motor.jugador.sala.id, "s2")
        self.assertEqual(motor.reloj, 100)

    def test_fr005_mover_usa_el_costo_de_la_salida(self):
        motor = self.preparar(costo=250)
        self.assertEqual(motor.costo_salida(motor.jugador.sala.salidas["E"]), 250)
        self.assertTrue(motor.ejecutar_accion("mover", "E"))
        self.assertEqual(motor.reloj, 250)

    def test_fr005_mover_usa_el_costo_con_otra_velocidad(self):
        motor = self.preparar(velocidad=50, costo=250)
        self.assertTrue(motor.ejecutar_accion("mover", "E"))
        self.assertEqual(motor.reloj, 500)   # 250 * 100 // 50


if __name__ == "__main__":
    unittest.main()
