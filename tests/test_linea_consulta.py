# Pruebas de las consultas de la línea de tiempo (spec 004, Historia 1; T018 a T021; Quickstart 1).
# Atiende: FR-001, FR-003, FR-004, FR-006, SC-003. Sin red: paquete offline temporal, cripta resoluble creada por
# ControladorPartida.nueva_partida. El «motor espía» (MotorEspiaConsulta) anota el estado vivo sin usar la reconstrucción.

import os
import sys
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from DTOS.ResumenHistorico import ResumenHistorico
from Modelo.LineaTiempo import LineaTiempo, ReferenciaInvalida
from Vista.TextoResumen import lineas_resumen
from tests.utiles_linea import MotorLinea, huella, partida_con_linea, partida_linea, preparar_motor_linea


def contenido(resumen):
    """Lo que `historia` muestra del estado, sin el título."""
    return lineas_resumen(resumen)[1:]


def esperado_en(motor, t):
    """Lo que el espía registró para el instante `t`: la decisión si `t` es una decisión; si no, el último estado
    registrado con reloj <= t (tras un evento o tras el efecto de una acción)."""
    for reloj, texto in motor.decisiones:
        if reloj == t:
            return texto
    ultimo = None
    for reloj, texto in motor.instantaneas:
        if reloj <= t:
            ultimo = texto
    return ultimo


class BaseConsulta(unittest.TestCase):

    def setUp(self):
        self.pl = partida_con_linea(k=3)
        self.addCleanup(self.pl.cerrar)
        self.motor = self.pl.motor
        self.linea = self.pl.linea
        self.pl.jugar(hasta_reloj=700)
        self.assertGreaterEqual(self.motor.reloj, 700)
        self.assertGreaterEqual(self.linea.acciones, 6)
        self.assertGreater(self.linea.cantidad_puntos, 2, "la prueba necesita varios puntos de control")


class PruebasHistoriaPorInstante(BaseConsulta):

    def test_us1_1_historia_250_coincide_con_el_estado_que_registro_el_espia(self):
        resumen = self.linea.consultar_instante(250, self.motor)
        self.assertIsInstance(resumen, ResumenHistorico)
        self.assertEqual(resumen.reloj, 250)
        self.assertEqual(resumen.referencia, ("instante", 250))
        self.assertEqual(contenido(resumen), esperado_en(self.motor, 250))
        tipos_efecto = [tipo for tipo, _detalle in resumen.efectos]
        self.assertIn("VENENO", tipos_efecto)
        self.assertIn("APAGAR_ANTORCHA", tipos_efecto)

    def test_us1_1_todos_los_instantes_con_evento_y_todas_las_decisiones(self):
        instantes = [reloj for reloj, _ in self.motor.instantaneas] + [reloj for reloj, _ in self.motor.decisiones]
        instantes = sorted(set(i for i in instantes if i < self.linea.reloj_actual))
        self.assertGreater(len(instantes), 10)
        for t in instantes:
            with self.subTest(t=t):
                resumen = self.linea.consultar_instante(t, self.motor)
                self.assertEqual(resumen.reloj, t)
                self.assertEqual(contenido(resumen), esperado_en(self.motor, t))

    def test_us1_1_tambien_entre_dos_eventos_y_entre_dos_acciones(self):
        for t in range(0, self.linea.reloj_actual, 17):
            with self.subTest(t=t):
                self.assertEqual(contenido(self.linea.consultar_instante(t, self.motor)), esperado_en(self.motor, t))

    def test_us1_1_todas_las_acciones(self):
        for k in range(1, self.linea.acciones + 1):
            with self.subTest(k=k):
                resumen = self.linea.consultar_accion(k, self.motor)
                self.assertEqual(resumen.referencia, ("accion", k))
                self.assertEqual(resumen.reloj, self.linea.vig_reloj[k - 1])
                self.assertEqual(contenido(resumen), self.motor.decisiones[k - 1][1])

    def test_fr001_la_reconstruccion_nunca_ejecuta_retroceder_dentro_de_un_clon(self):
        """Medido en T003: con `Historial()` vacío el clon rechaza `retroceder`. Aquí ninguna acción rehecha lo es."""
        ejecutadas = []
        original = MotorLinea.ejecutar_accion

        def espia(motor, nombre, argumento=""):
            ejecutadas.append(nombre)
            return original(motor, nombre, argumento)

        MotorLinea.ejecutar_accion = espia
        try:
            for k in range(1, self.linea.acciones + 2):
                self.linea.consultar_accion(k, self.motor)
            self.linea.consultar_instante(250, self.motor)
        finally:
            del MotorLinea.ejecutar_accion
        self.assertTrue(ejecutadas)
        self.assertNotIn("retroceder", ejecutadas)
        self.assertNotIn("retroceder", self.linea.guion_nombre)


class PruebasDecisionDelJugador(BaseConsulta):

    def test_us1_2_en_el_reloj_de_una_decision_el_estado_es_justo_antes_de_tomarla(self):
        for k in range(1, self.linea.acciones + 1):
            reloj = self.linea.vig_reloj[k - 1]
            with self.subTest(k=k, reloj=reloj):
                antes = contenido(self.linea.consultar_instante(reloj, self.motor))
                self.assertEqual(antes, self.motor.decisiones[k - 1][1])

    def test_us1_2_un_movimiento_no_se_refleja_en_la_sala_de_su_propia_decision(self):
        for k in range(1, self.linea.acciones + 1):
            posicion = self.linea.vig_guion[k - 1]
            if self.linea.guion_nombre[posicion] != "mover":
                continue
            reloj = self.linea.vig_reloj[k - 1]
            antes = self.linea.consultar_instante(reloj, self.motor).sala
            despues = self.linea.consultar_instante(reloj + 1, self.motor).sala
            self.assertNotEqual(antes, despues, f"la acción {k} (mover) ya se ve en su propia decisión")
            return
        self.fail("el escenario no tiene ningún mover")


class PruebasHistoriaPorAccion(BaseConsulta):

    def test_us1_3_historia_numeral_3_es_el_estado_antes_de_la_tercera_accion(self):
        resumen = self.linea.consultar_accion(3, self.motor)
        self.assertEqual(resumen.reloj, self.linea.vig_reloj[2])
        self.assertEqual(contenido(resumen), self.motor.decisiones[2][1])

    def test_us1_4_numeral_1_es_el_estado_inicial_y_el_ultimo_mas_uno_es_el_actual(self):
        inicial = self.linea.consultar_accion(1, self.motor)
        self.assertEqual(inicial.reloj, 0)
        self.assertEqual(inicial.sala[0], 1)  # sala inicial
        self.assertEqual(contenido(inicial), self.motor.decisiones[0][1])
        self.assertIsNone(inicial.resultado)

        actual = self.linea.consultar_accion(self.linea.acciones + 1, self.motor)
        self.assertEqual(actual.referencia, ("actual", None))
        self.assertEqual(actual.reloj, self.motor.reloj)
        self.assertEqual(contenido(actual), huella(self.motor))

    def test_us1_4_clon_antes_de_devuelve_un_motor_en_la_decision_pedida(self):
        for k in (1, 4, self.linea.acciones + 1):
            clon = self.linea.clon_antes_de(k, self.motor)
            try:
                self.assertIsNot(clon, self.motor)
                self.assertEqual((clon.reloj, clon.secuencia), self.linea.sello_de(k))
                esperado = huella(self.motor) if k == self.linea.acciones + 1 else self.motor.decisiones[k - 1][1]
                self.assertEqual(huella(clon), esperado)
            finally:
                self.linea._soltar_clon()


class PruebasEdgeCases(BaseConsulta):

    def test_us1_edge_historia_0_es_el_estado_inicial_tras_los_eventos_del_instante_0(self):
        resumen = self.linea.consultar_instante(0, self.motor)
        self.assertEqual(resumen.reloj, 0)
        self.assertEqual(contenido(resumen), self.motor.decisiones[0][1])

    def test_us1_edge_t_igual_al_reloj_actual_es_el_estado_actual(self):
        resumen = self.linea.consultar_instante(self.linea.reloj_actual, self.motor)
        self.assertEqual(resumen.referencia, ("actual", None))
        self.assertEqual(contenido(resumen), huella(self.motor))

    def test_us1_edge_t_mayor_que_el_reloj_actual_es_referencia_invalida(self):
        with self.assertRaises(ReferenciaInvalida) as contexto:
            self.linea.consultar_instante(self.linea.reloj_actual + 1, self.motor)
        self.assertIn("No hay historia más allá del reloj actual", contexto.exception.motivo)

    def test_us1_edge_acciones_fuera_de_rango_son_referencia_invalida(self):
        with self.assertRaises(ReferenciaInvalida) as cero:
            self.linea.consultar_accion(0, self.motor)
        self.assertEqual(cero.exception.motivo, "Las acciones se numeran desde 1.")
        with self.assertRaises(ReferenciaInvalida) as grande:
            self.linea.consultar_accion(99, self.motor)
        self.assertEqual(grande.exception.motivo,
                         f"La acción 99 no existe: la próxima acción es la {self.linea.acciones + 1}.")
        for malo in (-3, 1.5, "7", None, True):
            with self.assertRaises(ReferenciaInvalida):
                self.linea.consultar_instante(malo, self.motor)

    def test_us1_edge_instante_entre_dos_acciones_es_el_estado_de_la_ultima_mas_los_eventos_hasta_t(self):
        d0, d1 = self.linea.vig_reloj[0], self.linea.vig_reloj[1]
        self.assertGreater(d1 - d0, 1)
        for t in range(d0 + 1, d1):
            self.assertEqual(contenido(self.linea.consultar_instante(t, self.motor)), esperado_en(self.motor, t))


class PruebasEdgeCasesConPartidaPropia(unittest.TestCase):

    def test_us1_edge_varias_acciones_con_el_mismo_intervalo_se_distinguen_por_numero(self):
        """Acciones seguidas del mismo costo (varios `esperar`): `#k` apunta a cada una. (No hay acciones de costo 0 en
        el motor: cada acción cuesta al menos una unidad, así que `vig_reloj` siempre crece estrictamente.)"""
        partida = partida_linea(semilla=4)
        self.addCleanup(partida.cerrar)
        motor = preparar_motor_linea(partida.motor, espiar=False)
        linea = LineaTiempo(k=2, gestor_historico=partida.nuevo_gestor())
        linea.iniciar(motor)
        for _ in range(5):
            self.assertTrue(motor.ejecutar_accion("esperar", ""))
            linea.registrar_accion(motor, "esperar", "")
        relojes = [linea.consultar_accion(k, motor).reloj for k in range(1, 7)]
        self.assertEqual(relojes, [0, 100, 200, 300, 400, 500])

    def test_us1_edge_los_pasos_de_ir_a_cuentan_como_acciones_y_numeral_k_apunta_a_cada_paso(self):
        from Controlador.ControladorPartida import ControladorPartida

        class ControladorConLinea(ControladorPartida):
            # imita el enganche de T035 (que no está hecho): registra cada acción aceptada en la línea
            def _accion(self, nombre, argumento, comentario=None):
                aceptada = super()._accion(nombre, argumento, comentario)
                if aceptada:
                    self.linea.registrar_accion(self.motor, nombre, argumento)
                return aceptada

        partida = partida_linea(semilla=5)
        self.addCleanup(partida.cerrar)
        controlador = partida.controlador
        controlador.__class__ = ControladorConLinea
        motor = preparar_motor_linea(controlador.motor, espiar=False)
        controlador.linea = LineaTiempo(k=2, gestor_historico=partida.nuevo_gestor())
        controlador.linea.iniciar(motor)
        controlador.ejecutar("s")       # a la sala 4
        controlador.ejecutar("e")       # a la sala 5
        controlador.ejecutar("ir a 1")  # dos pasos por el mapa conocido: 5 -> 4 -> 1 (la sala 2 tiene una rata)
        self.assertEqual(motor.jugador.sala.id, 1)
        linea = controlador.linea
        self.assertEqual(linea.acciones, 4)
        self.assertEqual(linea.guion_nombre, ["mover"] * 4)
        salas = [linea.consultar_accion(k, motor).sala[0] for k in range(1, 6)]
        self.assertEqual(salas, [1, 4, 5, 4, 1])

    def test_us1_edge_en_una_partida_recien_iniciada_solo_valen_t_0_y_numeral_1(self):
        partida = partida_linea(semilla=6)
        self.addCleanup(partida.cerrar)
        motor = preparar_motor_linea(partida.motor, espiar=False)
        linea = LineaTiempo(k=5, gestor_historico=partida.nuevo_gestor())
        linea.iniciar(motor)
        self.assertEqual(linea.consultar_instante(0, motor).referencia, ("actual", None))
        self.assertEqual(linea.consultar_accion(1, motor).referencia, ("actual", None))
        for malo in (1, 100):
            with self.assertRaises(ReferenciaInvalida):
                linea.consultar_instante(malo, motor)
        with self.assertRaises(ReferenciaInvalida):
            linea.consultar_accion(2, motor)


if __name__ == "__main__":
    unittest.main()
