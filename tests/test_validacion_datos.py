# Pruebas de validación del costo de las salidas (spec 003, T030 y T031; FR-001, FR-002, FR-003).
# Persona B implementó `costo` y su validación en DTOS/Salida.py (Salida.desde_json); estas pruebas solo lo verifican.
# Sin red, sin datos de criptas reales (Constitución IV), sin random global.

import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import unittest

from DTOS.SalaEsqueleto import SalaEsqueleto
from DTOS.Salida import Salida
from tests.utiles_terreno import mapa_a_mano

# Id de sala destino que no se confunde con ningún costo de las pruebas, para buscarlo en el mensaje.
DESTINO = 42
COSTOS_INVALIDOS = (0, -5, 2.5, "100", True)
COSTOS_VALIDOS = (1, 100, 250, 1000)


def salida_json(costo=None, con_costo=True):
    datos = {"sala": DESTINO, "cerrada": False}
    if con_costo:
        datos["costo"] = costo
    return datos


# ───────────────────────── T030 ─────────────────────────

class TestCostoInvalidoSeRechaza(unittest.TestCase):
    def test_fr001_salida_rechaza_costo_invalido_con_valueerror(self):
        """T030 (FR-001): un costo 0, negativo o no entero (0, -5, 2.5, "100", True) hace que Salida.desde_json
        lance ValueError, sin asumir ningún valor."""
        for costo in COSTOS_INVALIDOS:
            with self.subTest(costo=costo):
                with self.assertRaises(ValueError):
                    Salida.desde_json(salida_json(costo))

    def test_fr001_mensaje_menciona_la_sala_destino_y_el_valor_rechazado(self):
        """T030 (FR-001): el rechazo trae un mensaje claro que habla del costo y nombra la sala destino y el valor
        rechazado (con repr, para distinguir "100" de 100 y True de 1)."""
        for costo in COSTOS_INVALIDOS:
            with self.subTest(costo=costo):
                with self.assertRaises(ValueError) as contexto:
                    Salida.desde_json(salida_json(costo))
                mensaje = str(contexto.exception)
                self.assertIn("costo", mensaje.lower())
                self.assertIn(str(DESTINO), mensaje)
                self.assertIn(repr(costo), mensaje)

    def test_fr001_sala_del_esqueleto_con_costo_invalido_se_rechaza(self):
        """T030 (FR-001): una sala del esqueleto con una salida de costo inválido no se construye: SalaEsqueleto.desde_json
        propaga el ValueError y la cripta no se carga. Las salidas válidas de la misma sala no lo evitan."""
        for costo in COSTOS_INVALIDOS:
            with self.subTest(costo=costo):
                datos = {"id": 1, "nombre": "Sala 1", "salidas": {
                    "N": {"sala": 2, "cerrada": False, "costo": 100},
                    "E": salida_json(costo),
                }}
                with self.assertRaises(ValueError) as contexto:
                    SalaEsqueleto.desde_json(datos)
                self.assertIn(repr(costo), str(contexto.exception))

    def test_fr001_cripta_con_costo_invalido_no_se_arma(self):
        """T030 (FR-001): armar un motor con una salida de costo 0 falla con ValueError antes de existir la partida."""
        with self.assertRaises(ValueError):
            mapa_a_mano([
                (1, [("E", 2, 0, False)]),
                (2, [("O", 1, 100, False)]),
            ], sala_jugador=1)


class TestCostoValidoSeConserva(unittest.TestCase):
    def test_fr001_costo_valido_se_acepta_y_se_conserva_tal_cual(self):
        """T030 (FR-001): un costo entero ≥ 1 (1, 100, 250, 1000) se acepta y la salida lo guarda sin cambios."""
        for costo in COSTOS_VALIDOS:
            with self.subTest(costo=costo):
                salida = Salida.desde_json(salida_json(costo))
                self.assertIs(type(salida.costo), int)
                self.assertEqual(salida.costo, costo)
                self.assertEqual(salida.sala_destino, DESTINO)

    def test_fr002_salida_sin_costo_declarado_vale_100(self):
        """T030 (FR-002): una salida sin la clave `costo` se acepta y vale 100."""
        salida = Salida.desde_json(salida_json(con_costo=False))
        self.assertEqual(salida.costo, 100)
        self.assertEqual(salida.sala_destino, DESTINO)


# ───────────────────────── T031 ─────────────────────────

def conexion(costo_ida, costo_vuelta):
    """Esqueleto A = 1, B = 2: 1 -E-> 2 con `costo_ida` y 2 -O-> 1 con `costo_vuelta` (None = sin declarar)."""
    return [
        (1, [("E", 2, costo_ida, False)]),
        (2, [("O", 1, costo_vuelta, False)]),
    ]


CASOS_ASIMETRICOS = (
    (300, 100, 100),     # (costo A→B, costo B→A declarado, lo que vale B→A)
    (300, None, 100),
)


class TestSentidosConCostoDistinto(unittest.TestCase):
    def test_fr001_fr003_esqueleto_con_costos_distintos_por_sentido_se_carga(self):
        """T031 (FR-001, FR-003): si los dos sentidos de A–B declaran costos distintos (300 y 100), o uno declarado y
        el otro ausente (300 y sin costo), las salas se construyen sin error; cada salida conserva el suyo."""
        for ida, vuelta, vale_vuelta in CASOS_ASIMETRICOS:
            with self.subTest(ida=ida, vuelta=vuelta):
                salidas_b = {"O": {"sala": 1, "cerrada": False}}
                if vuelta is not None:
                    salidas_b["O"]["costo"] = vuelta
                a = SalaEsqueleto.desde_json({"id": 1, "nombre": "A", "salidas": {
                    "E": {"sala": 2, "cerrada": False, "costo": ida}}})
                b = SalaEsqueleto.desde_json({"id": 2, "nombre": "B", "salidas": salidas_b})
                self.assertEqual(a.salidas["E"].costo, ida)
                self.assertEqual(b.salidas["O"].costo, vale_vuelta)

    def test_fr001_fr003_jugador_tarda_lo_de_la_salida_que_atraviesa(self):
        """T031 (FR-001, FR-003): con un motor de mapa_a_mano, el jugador cruza A→B en 300 y vuelve B→A en 100 (el
        costo declarado de la vuelta, o 100 si no lo declara): cada cruce usa el costo de la salida atravesada."""
        for ida, vuelta, vale_vuelta in CASOS_ASIMETRICOS:
            with self.subTest(ida=ida, vuelta=vuelta):
                motor = mapa_a_mano(conexion(ida, vuelta), sala_jugador=1)
                self.assertEqual(motor.reloj, 0)

                self.assertTrue(motor.ejecutar_accion("mover", "E"))
                self.assertEqual(motor.jugador.sala.id, 2)
                self.assertEqual(motor.reloj, ida)

                self.assertTrue(motor.ejecutar_accion("mover", "O"))
                self.assertEqual(motor.jugador.sala.id, 1)
                self.assertEqual(motor.reloj, ida + vale_vuelta)

    def test_fr001_fr003_dos_actores_cada_uno_tarda_lo_de_su_salida(self):
        """T031 (FR-001, FR-003): dos actores en motores separados sobre la misma cripta, uno cruza A→B y otro B→A;
        tardan 300 y 100 respectivamente, cada uno lo de la salida que atraviesa."""
        for ida, vuelta, vale_vuelta in CASOS_ASIMETRICOS:
            with self.subTest(ida=ida, vuelta=vuelta):
                desde_a = mapa_a_mano(conexion(ida, vuelta), sala_jugador=1)
                desde_b = mapa_a_mano(conexion(ida, vuelta), sala_jugador=2)

                self.assertTrue(desde_a.ejecutar_accion("mover", "E"))
                self.assertTrue(desde_b.ejecutar_accion("mover", "O"))

                self.assertEqual(desde_a.reloj, ida)
                self.assertEqual(desde_b.reloj, vale_vuelta)


if __name__ == "__main__":
    unittest.main()
