# Pruebas de la antorcha sobre el conocimiento (T020 a T024, Historia 2).
# FR-004, FR-006, FR-009, FR-010, FR-011, FR-014. Apéndice B: antorcha explora sin activar enemigos
# ni trampas, y pergamino revierte entrada con antorcha.

import os
import sys

# Permite ejecutar este archivo desde cualquier carpeta (PyCharm, unittest o pytest).
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import unittest

from Modelo.Conocimiento import ABIERTA, AVISTADA, CERRADA, DESCONOCIDA, EXPLORADA, SIN_OBSERVAR
from tests.test_conocimiento import BaseConocimiento, foto
from tests.utiles_niebla import ANTORCHA, CRIPTA_NIEBLA, PERGAMINO, contenido_sala, salida

ID_ANTORCHA = f"obj-{CRIPTA_NIEBLA}-1-{ANTORCHA}-0"
ID_PERGAMINO = f"obj-{CRIPTA_NIEBLA}-1-{PERGAMINO}-1"


def mapa():
    # B (2) tiene a C (3) detrás de una salida cerrada. D (4) se alcanza por C o rodeando por 5.
    return [
        {"id": 1, "nombre": "Entrada", "salidas": {"E": salida(2)}},
        {"id": 2, "nombre": "B", "salidas": {"O": salida(1), "N": salida(3, cerrada=True), "S": salida(5)}},
        {"id": 3, "nombre": "C", "salidas": {"S": salida(2), "E": salida(4)}},
        {"id": 4, "nombre": "D", "salidas": {"O": salida(3), "S": salida(5), "E": salida(6)}},
        {"id": 5, "nombre": "Rodeo", "salidas": {"N": salida(2), "E": salida(4)}},
        {"id": 6, "nombre": "Salida", "salidas": {"O": salida(4)}},
    ]


CONTENIDO = [
    contenido_sala(1, objetos=[ANTORCHA, PERGAMINO]),
    contenido_sala(3, enemigos=["e-rata"], trampas=["t-dardos"]),
]


class BaseAntorcha(BaseConocimiento):

    def encender(self, motor):
        self.acciones(motor, ("recoger", ID_ANTORCHA), ("recoger", ID_PERGAMINO), ("usar", ID_ANTORCHA))
        self.assertTrue(motor.jugador.antorcha_encendida)


class TestAntorcha(BaseAntorcha):

    def test_fr009_fr010_explora_sin_activar_enemigos_ni_trampas(self):
        # Escenario US2-1. Apéndice B: antorcha explora sin activar enemigos ni trampas.
        motor = self.partida(mapa(), CONTENIDO)
        self.encender(motor)
        vida = motor.jugador.vida
        self.acciones(motor, ("mover", "E"))

        for id_sala in (2, 3):
            self.assertEqual(motor.conocimiento.estado(self.sala(motor, id_sala)), EXPLORADA)
        self.assertFalse(any(enemigo.activo for enemigo in motor.enemigos))
        self.assertTrue(motor._obtener_estado_trampa("t-dardos", True))
        self.assertEqual(motor.jugador.vida, vida)
        self.assertFalse(motor.contenido_disponible(3))
        self.assertEqual(motor.obtener_objetos_suelo(self.sala(motor, 3)), [])

    def test_fr014_pergamino_restaura_exactamente_el_conocimiento(self):
        # Escenario US2-2. Apéndice B: pergamino revierte entrada con antorcha.
        motor = self.partida(mapa(), CONTENIDO)
        self.encender(motor)
        antes = foto(motor.conocimiento)
        self.acciones(motor, ("mover", "E"))
        self.assertNotEqual(foto(motor.conocimiento), antes)

        self.acciones(motor, ("retroceder", ""))
        self.assertEqual(motor.jugador.sala.id, 1)
        self.assertEqual(foto(motor.conocimiento), antes)
        self.assertEqual(self.estados(motor), ([1], [2], [3, 4, 5, 6]))

    def test_fr009_con_la_antorcha_apagada_solo_explora_la_sala_de_llegada(self):
        # Escenario US2-3.
        motor = self.partida(mapa(), CONTENIDO)
        self.acciones(motor, ("mover", "E"))
        self.assertEqual(self.estados(motor), ([1, 2], [3, 5], [4, 6]))

    def test_fr006_fr011_las_puertas_de_una_vecina_quedan_sin_observar(self):
        # Escenario US2-4, parte del conocimiento: C -> D, sin estar en C ni en D.
        motor = self.partida(mapa(), CONTENIDO)
        self.encender(motor)
        self.acciones(motor, ("mover", "E"))
        self.assertEqual(self.recuerdo(motor, 3, "E"), SIN_OBSERVAR)
        self.assertEqual(self.recuerdo(motor, 5, "E"), SIN_OBSERVAR)
        # Lo que sí se observa desde B: sus salidas y las que entran a B.
        self.assertEqual(self.recuerdo(motor, 2, "N"), CERRADA)
        self.assertEqual(self.recuerdo(motor, 3, "S"), ABIERTA)

    def test_fr006_al_entrar_al_origen_la_puerta_se_observa(self):
        motor = self.partida(mapa())
        self.acciones(motor, ("mover", "E"), ("abrir", "N"), ("mover", "N"))
        self.assertEqual(self.recuerdo(motor, 3, "E"), ABIERTA)

    def test_fr006_al_entrar_al_destino_la_puerta_se_observa(self):
        motor = self.partida(mapa(), CONTENIDO)
        self.encender(motor)
        self.acciones(motor, ("mover", "E"), ("mover", "S"))
        self.assertEqual(self.recuerdo(motor, 3, "E"), SIN_OBSERVAR)
        self.acciones(motor, ("mover", "E"))
        self.assertEqual(motor.jugador.sala.id, 4)
        self.assertEqual(self.recuerdo(motor, 3, "E"), ABIERTA)


class TestAntorchaBordes(BaseAntorcha):

    def test_fr009_vecinas_ya_exploradas_no_cambian(self):
        motor = self.partida(mapa(), CONTENIDO)
        self.encender(motor)
        self.acciones(motor, ("mover", "E"), ("mover", "O"))
        antes = foto(motor.conocimiento)
        self.acciones(motor, ("mover", "E"))
        self.assertEqual(foto(motor.conocimiento), antes)

    def test_fr004_los_vecinos_de_una_explorada_con_antorcha_quedan_avistados(self):
        motor = self.partida(mapa(), CONTENIDO)
        self.encender(motor)
        self.acciones(motor, ("mover", "E"))
        self.assertEqual(motor.conocimiento.estado(self.sala(motor, 4)), AVISTADA)
        self.assertEqual(motor.conocimiento.estado(self.sala(motor, 6)), DESCONOCIDA)

    def test_fr011_una_salida_observada_no_vuelve_a_sin_observar(self):
        # 2 -> 1 se observó sin antorcha; explorar 2 otra vez con antorcha no la toca.
        motor = self.partida(mapa(), CONTENIDO)
        self.acciones(motor, ("mover", "E"), ("mover", "O"))
        self.assertEqual(self.recuerdo(motor, 2, "O"), ABIERTA)
        self.encender(motor)
        self.acciones(motor, ("mover", "E"))
        self.assertEqual(self.recuerdo(motor, 2, "O"), ABIERTA)
        self.assertEqual(self.recuerdo(motor, 3, "E"), SIN_OBSERVAR)


if __name__ == "__main__":
    unittest.main()
