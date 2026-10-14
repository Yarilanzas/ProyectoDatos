import os
import sys

# Permite ejecutar este archivo desde cualquier carpeta (PyCharm, unittest o pytest).
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import unittest
from types import SimpleNamespace

from Modelo.MotorSimulacion import MotorSimulacion
from Modelo.Inventario import Inventario, NodoInventario
from Modelo.prueba_actores import JugadorPrueba, GestorPrueba, sala


def llave(tipo="llave_roja"):
    return NodoInventario("inst-" + tipo, tipo, "Llave", 1, 1, "llave")


class TestPuertas(unittest.TestCase):
    def setUp(self):
        self.s1, self.s2 = sala("s1"), sala("s2")
        self.puerta = SimpleNamespace(sala_destino="s2", cerrada=True,
                                      llave="llave_roja", cierre_automatico=None)
        self.s1.salidas["E"] = self.puerta
        self.motor = MotorSimulacion(semilla=1, gestor_datos=GestorPrueba())
        self.jugador = JugadorPrueba(self.s1)
        self.jugador.inventario = Inventario(cap_max=10)
        self.motor.jugador = self.jugador
        self.motor.salas = [self.s1, self.s2]
        self.motor.activar_enemigos_de_sala = lambda _s: None
        self.jugador.evento_actual = self.motor.programar_evento(0, "ACCION_ACTOR", self.jugador)
        self.motor.avanzar_hasta_jugador()   # consume el turno inicial, como al empezar la partida

    def test_sin_llave_no_abre(self):
        self.assertFalse(self.motor.ejecutar_accion("abrir", "E"))
        self.assertTrue(self.puerta.cerrada)

    def test_con_llave_abre_y_consume_tiempo(self):
        self.jugador.inventario.recoge(llave())
        self.assertTrue(self.motor.ejecutar_accion("abrir", "e"))
        self.assertFalse(self.puerta.cerrada)
        self.assertEqual(self.motor.reloj, 50)   # costo 50 a velocidad 100

    def test_puerta_sin_llave_requerida_abre_libre(self):
        self.puerta.llave = None
        self.assertTrue(self.motor.abrir_salida("E"))

    def test_no_abre_si_ya_esta_abierta_o_no_existe(self):
        self.puerta.cerrada = False
        self.assertFalse(self.motor.abrir_salida("E"))
        self.assertFalse(self.motor.abrir_salida("N"))

    def test_cierre_automatico_programa_y_cierra(self):
        self.puerta.cierre_automatico = 120
        self.jugador.inventario.recoge(llave())
        self.motor.abrir_salida("E")
        cierres = [e for e in self.motor.agenda.heap
                   if e.tipo == "CERRAR_PUERTA" and not e.cancelado]
        self.assertEqual(len(cierres), 1)
        self.assertEqual(cierres[0].tiempo, 120)   # reloj 0 + 120
        self.motor.ejecutar_accion("esperar")      # 50 -> 150
        self.motor.ejecutar_accion("esperar")
        self.assertTrue(self.puerta.cerrada)

    def test_pergamino_deshace_la_apertura(self):
        self.puerta.cierre_automatico = 120
        self.jugador.inventario.recoge(llave())
        self.motor.abrir_salida("E")
        self.motor.historial.deshacer_ultimo()
        self.assertTrue(self.puerta.cerrada)
        self.assertEqual(self.motor.reloj, 0)
        self.assertFalse([e for e in self.motor.agenda.heap
                          if e.tipo == "CERRAR_PUERTA" and not e.cancelado])


if __name__ == "__main__":
    unittest.main()
