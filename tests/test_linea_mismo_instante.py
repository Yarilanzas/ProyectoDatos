# Varios eventos en el mismo instante (spec 004, Historia 3; T050 a T052; Quickstart 3).
# Atiende: FR-001, FR-002. Sin red: cripta resoluble creada por ControladorPartida.nueva_partida (tests/utiles_linea.py,
# `partida_coincidencia`). El orden de resolución de referencia es el que anotó el motor espía en la partida real.

import os
import sys
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from DTOS.ResumenHistorico import EFECTO_ANTORCHA, EFECTO_VELOCIDAD
from Modelo.AgendaConCorte import AgendaConCorte
from tests.test_linea_consulta import contenido, esperado_en
from tests.utiles_linea import EVENTOS_EN_T, huella, partida_coincidencia, partida_linea, preparar_motor_linea
from tests.utiles_linea import MotorEspiaConsulta, LineaTiempo, GeneradorAcciones, PartidaConLinea


def tipos(resumen):
    return [tipo for tipo, _detalle in resumen.efectos]


def clon_de_instante(linea, motor, t):
    """Lo mismo que `consultar_instante` para un `t` entre dos decisiones, pero devolviendo el clon para mirar el orden de
    resolución que él observó (su motor espía anota cada evento). El llamador debe soltar el clon."""
    from Modelo.BusquedaBinaria import ultimo_menor_o_igual
    k = ultimo_menor_o_igual(linea.vig_reloj, t) + 1
    clon = linea.clon_antes_de(k, motor)
    clon.agenda.__class__ = AgendaConCorte
    clon.agenda.corte = t
    posicion = linea.vig_guion[k - 1]
    clon.ejecutar_accion(linea.guion_nombre[posicion], linea.guion_argumento[posicion])
    return clon


class PruebasMismoInstante(unittest.TestCase):

    def setUp(self):
        self.c = partida_coincidencia(k=3)
        self.addCleanup(self.c.pl.cerrar)
        self.linea = self.c.pl.linea
        self.motor = self.c.pl.motor
        self.t = self.c.t

    def test_us3_el_escenario_tiene_tres_eventos_en_t_y_t_no_es_una_decision(self):
        self.assertEqual([tipo for _t, tipo, _actor in self.c.orden], list(EVENTOS_EN_T))
        self.assertNotIn(self.t, self.linea.vig_reloj)
        self.assertNotIn(self.t, [reloj for reloj, _ in self.motor.decisiones])
        self.assertIn((self.t + 1, "APAGAR_ANTORCHA", "jugador"), self.motor.orden)

    def test_us3_1_historia_t_refleja_los_tres_eventos_en_el_orden_de_la_partida(self):
        resumen = self.linea.consultar_instante(self.t, self.motor)
        self.assertEqual(contenido(resumen), esperado_en(self.motor, self.t))
        # los tres se reflejan: el efecto de velocidad terminó, la rata atacó y la puerta quedó cerrada
        self.assertNotIn(EFECTO_VELOCIDAD, tipos(resumen))
        antes = self.linea.consultar_instante(self.t - 1, self.motor)
        self.assertIn(EFECTO_VELOCIDAD, tipos(antes))
        self.assertLess(resumen.vida, antes.vida)
        puerta = [linea for linea in contenido(resumen) if linea.strip().startswith("E -> sala 2")]
        self.assertTrue(puerta and puerta[0].endswith("cerrada"), puerta)
        self.assertTrue(antes is not None and [l for l in contenido(antes) if l.strip().startswith("E -> sala 2")][0]
                        .endswith("abierta"))
        # el mismo orden de resolución que en la partida (lo anotó el motor espía del clon)
        clon = clon_de_instante(self.linea, self.motor, self.t)
        try:
            en_t = [evento for evento in clon.orden if evento[0] == self.t]
            self.assertEqual(en_t, self.c.orden)
        finally:
            self.linea._soltar_clon()

    def test_us3_1_cualquier_k_da_el_mismo_resumen_en_t(self):
        esperado = contenido(self.linea.consultar_instante(self.t, self.motor))
        for k in (1, 2, 5, 50):
            pl = partida_coincidencia(k=k)
            self.addCleanup(pl.pl.cerrar)
            self.assertEqual(contenido(pl.pl.linea.consultar_instante(pl.t, pl.pl.motor)), esperado, f"K = {k}")

    def test_us3_2_el_evento_de_t_mas_1_no_se_refleja_en_historia_t(self):
        en_t = self.linea.consultar_instante(self.t, self.motor)
        en_t1 = self.linea.consultar_instante(self.t + 1, self.motor)
        self.assertIn(EFECTO_ANTORCHA, tipos(en_t))
        self.assertNotIn(EFECTO_ANTORCHA, tipos(en_t1))
        self.assertEqual(contenido(en_t1), esperado_en(self.motor, self.t + 1))
        clon = clon_de_instante(self.linea, self.motor, self.t)
        try:
            self.assertNotIn((self.t + 1, "APAGAR_ANTORCHA", "jugador"), clon.orden)
            self.assertTrue(clon.jugador.antorcha_encendida)
        finally:
            self.linea._soltar_clon()


class PruebasDecisionYEventoPosterior(unittest.TestCase):

    def test_us3_quickstart_3_una_decision_en_t_es_el_estado_previo_y_un_evento_posterior_no_se_refleja(self):
        """Con una decisión del jugador en `t`, `historia t` es el estado previo a decidir; un evento con tiempo `t` y
        secuencia POSTERIOR a la decisión no se refleja (el motor lo resuelve después de la acción del jugador)."""
        partida = partida_linea(semilla=4)
        self.addCleanup(partida.cerrar)
        motor = preparar_motor_linea(partida.motor, espiar=False)
        motor.__class__ = MotorEspiaConsulta
        motor.instantaneas, motor.decisiones, motor.orden = [], [], []
        motor.jugador.antorcha_encendida = True
        linea = LineaTiempo(k=1, gestor_historico=partida.nuevo_gestor_historico())
        linea.iniciar(motor)
        pl = PartidaConLinea(partida, linea, GeneradorAcciones(4))

        antes = (motor.reloj, huella(motor))
        self.assertTrue(motor.ejecutar_accion("esperar", ""))      # acción 1; ahora es la decisión 2, en el reloj 100
        t = motor.reloj
        self.assertEqual(t, 100)
        # evento con tiempo t y secuencia posterior a la del evento de la decisión (ya sacado de la agenda)
        motor.programar_evento(t, "APAGAR_ANTORCHA", motor.jugador)
        motor.decisiones.append(antes)
        linea.registrar_accion(motor, "esperar", "")               # K = 1: el punto ya trae el evento
        pl.hacer([("esperar", ""), ("esperar", "")])
        self.assertEqual(linea.vig_reloj[1], t)
        self.assertIn((t, "APAGAR_ANTORCHA", "jugador"), motor.orden)
        self.assertLess(motor.orden.index((t, "APAGAR_ANTORCHA", "jugador")), len(motor.orden))

        en_decision = linea.consultar_instante(t, motor)
        self.assertEqual(contenido(en_decision), motor.decisiones[1][1])
        self.assertIn(EFECTO_ANTORCHA, tipos(en_decision))          # el evento posterior no se refleja
        despues = linea.consultar_instante(t + 1, motor)
        self.assertNotIn(EFECTO_ANTORCHA, tipos(despues))           # sí se ve al avanzar un instante
        self.assertEqual(contenido(despues), esperado_en(motor, t + 1))
        self.assertEqual(contenido(linea.consultar_accion(2, motor)), contenido(en_decision))


if __name__ == "__main__":
    unittest.main()
