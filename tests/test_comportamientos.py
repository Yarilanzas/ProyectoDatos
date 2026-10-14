import os
import sys

# Permite ejecutar este archivo desde cualquier carpeta (PyCharm, unittest o pytest).
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import contextlib
import io
import unittest
from types import SimpleNamespace

from Modelo.Enemigo import Enemigo
from Modelo.RegistroMensajes import RegistroMensajes
from Modelo.prueba_actores import sala
from Modelo.MotorSimulacion import MotorSimulacion
from Modelo.Inventario import Inventario
from Modelo.prueba_actores import JugadorPrueba, GestorPrueba


class Base(unittest.TestCase):
    """Jugador en s1 con inventario real; el turno inicial ya fue consumido."""

    def setUp(self):
        self.s1, self.s2 = sala("s1"), sala("s2")
        self.motor = MotorSimulacion(semilla=1, gestor_datos=GestorPrueba())
        self.j = JugadorPrueba(self.s1, vida=20)
        self.j.inventario = Inventario(cap_max=10)
        self.motor.jugador = self.j
        self.motor.salas = [self.s1, self.s2]
        self.motor.activar_enemigos_de_sala = lambda _s: None
        self.j.evento_actual = self.motor.programar_evento(0, "ACCION_ACTOR", self.j)
        self.motor.avanzar_hasta_jugador()


def puerta(destino, cerrada=False):
    return SimpleNamespace(sala_destino=destino, cerrada=cerrada)


class TestRegistroMensajes(unittest.TestCase):
    def test_orden_antes_de_llenarse(self):
        r = RegistroMensajes(20)
        for i in range(3):
            r.agregar(f"m{i}")
        self.assertEqual(r.ultimos(), ["m0", "m1", "m2"])

    def test_conserva_solo_los_ultimos_20(self):
        r = RegistroMensajes(20)
        for i in range(55):
            r.agregar(f"m{i}")
        self.assertEqual(r.ultimos(), [f"m{i}" for i in range(35, 55)])
        self.assertEqual(len(r), 20)

    def test_memoria_constante(self):
        r = RegistroMensajes(20)
        for i in range(10_000):
            r.agregar(i)
        self.assertEqual(len(r._datos), 20)    # la lista nunca crece ni se desplaza


class TestMensajesDelMotor(Base):
    def test_ataque_se_registra_y_no_imprime(self):
        rata = Enemigo("rata-1", 1, 5, 1, 0, 100, "guardian", sala=self.s1)
        self.motor.registrar_enemigo(rata)
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            self.motor.atacar(self.j, rata)
        self.assertEqual(salida.getvalue(), "")
        textos = self.motor.mensajes.ultimos()
        self.assertTrue(any("rata-1" in m and "daño" in m for m in textos))
        self.assertTrue(any("ha muerto" in m for m in textos))


class TestComportamientos(Base):
    def setUp(self):
        super().setUp()
        self.s3 = sala("s3")
        # s1 - s2 - s3 en línea; el jugador está en s1 (rastro 0).
        self.s1.salidas["E"] = puerta("s2")
        self.s2.salidas["O"] = puerta("s1")
        self.s2.salidas["E"] = puerta("s3")
        self.s3.salidas["O"] = puerta("s2")
        self.motor.salas = [self.s1, self.s2, self.s3]
        self.s1.rastro = 0

    def enemigo(self, comportamiento, sala_, velocidad=100, id_="e1"):
        e = Enemigo(id_, 50, 50, 1, 0, velocidad, comportamiento, sala=sala_)
        self.motor.registrar_enemigo(e)
        self.motor.activar_enemigo(e)
        return e

    def test_guardian_nunca_abandona_su_sala(self):
        e = self.enemigo("guardian", self.s2)
        self.motor.ejecutar_accion("esperar")
        self.motor.ejecutar_accion("esperar")
        self.motor.ejecutar_accion("esperar")
        self.assertIs(e.sala, self.s2)

    def test_enemigo_en_la_sala_del_jugador_ataca(self):
        for comportamiento in ("guardian", "errante", "rastreador"):
            e = Enemigo("x", 5, 5, 1, 0, 100, comportamiento, sala=self.s1)
            self.assertEqual(self.motor.accion_enemigo(e, self.j), "ATACAR")

    def test_ataque_baja_la_vida_del_jugador(self):
        self.enemigo("guardian", self.s1)
        self.motor.ejecutar_accion("esperar")
        self.assertLess(self.j.vida, 20)

    def test_errante_se_mueve_por_salidas_abiertas(self):
        e = self.enemigo("errante", self.s3)         # única salida: O -> s2
        self.motor.ejecutar_accion("esperar")
        self.assertIs(e.sala, self.s2)

    def test_errante_espera_si_no_hay_salidas_abiertas(self):
        self.s3.salidas["O"].cerrada = True
        e = self.enemigo("errante", self.s3)
        self.motor.ejecutar_accion("esperar")
        self.motor.ejecutar_accion("esperar")
        self.assertIs(e.sala, self.s3)

    def test_enemigo_no_abre_puertas_cerradas(self):
        self.s2.salidas["O"].cerrada = True
        e = self.enemigo("rastreador", self.s2)
        self.motor.ejecutar_accion("esperar")
        self.assertIs(e.sala, self.s2)

    def test_rastreador_sigue_el_rastro_y_luego_ataca(self):
        e = self.enemigo("rastreador", self.s2)
        self.motor.ejecutar_accion("esperar")        # llega a s1
        self.assertIs(e.sala, self.s1)
        self.motor.ejecutar_accion("esperar")        # ya comparte sala: ataca
        self.assertLess(self.j.vida, 20)

    def test_rastreador_sin_rastro_fresco_espera(self):
        # El jugador está lejos, en una sala aislada; el rastro de s1 es viejo.
        s4 = sala("s4")
        self.motor.salas.append(s4)
        self.j.sala = s4
        self.s1.rastro = -1000
        e = self.enemigo("rastreador", self.s2)
        self.motor.ejecutar_accion("esperar")
        self.assertIs(e.sala, self.s2)

    def test_primera_accion_usa_la_velocidad(self):
        e = self.enemigo("guardian", self.s3, velocidad=150)
        self.assertEqual(e.tiempo_siguiente, 66)     # 100*100//150 (§2.4)

    def test_activacion_simultanea_en_orden_de_id(self):
        b = Enemigo("b", 5, 5, 1, 0, 100, "guardian", sala=self.s3)
        a = Enemigo("a", 5, 5, 1, 0, 100, "guardian", sala=self.s3)
        self.motor.registrar_enemigos([b, a])
        self.motor.activar_enemigos([b, a])
        self.assertLess(a.evento_actual.secuencia, b.evento_actual.secuencia)

    def test_enemigo_que_llega_avisa_en_pantalla(self):
        self.enemigo("rastreador", self.s2)
        self.motor.ejecutar_accion("esperar")
        self.assertTrue(any("entra a la sala" in m for m in self.motor.mensajes.ultimos()))


if __name__ == "__main__":
    unittest.main()
