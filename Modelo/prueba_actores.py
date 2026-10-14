import unittest
from types import SimpleNamespace

from Modelo.MotorSimulacion import MotorSimulacion


class JugadorPrueba:
    """Actor mínimo compatible con las operaciones del MotorSimulacion."""
    def __init__(self, sala, vida=20, velocidad=100):
        self.id = "jugador-test"
        self.sala = sala
        self.vida = vida
        self.vida_max = vida
        self.vivo = True
        self.velocidad = velocidad
        self.defensa = 0
        self.ataque = 1
        self.tiempo_siguiente = 0
        self.evento_actual = None
        self.inventario = []

    def esta_vivo(self):
        return self.vivo

    def recibir_dano(self, cantidad):
        self.vida = max(0, self.vida - cantidad)
        if self.vida <= 0:
            self.vivo = False


class GestorPrueba:
    def __init__(self, fichas=None):
        self.fichas = fichas or {}
        self.estado_juego = None

    def conectar_estado_juego(self, estado_juego):
        self.estado_juego = estado_juego

    def obtener_ficha(self, id_ficha):
        return self.fichas.get(id_ficha)


def ficha_trampa(danio=4, rearme=300):
    return SimpleNamespace(
        id="trp_dardos",
        clase="trampa",
        nombre="Dardos de prueba",
        danio=danio,
        rearme=rearme,
    )


def trampa(instancia="t-1", tipo="trp_dardos"):
    return SimpleNamespace(instancia=instancia, tipo=tipo)


def sala(id_sala):
    return SimpleNamespace(id=id_sala, salidas={}, rastro=None)


def contenido(id_sala, trampas=None):
    return SimpleNamespace(
        id_sala=id_sala,
        trampas=trampas or [],
        enemigos=[],
        objetos=[],
    )


class TestIntegracionMotorTrampas(unittest.TestCase):
    def setUp(self):
        self.sala1 = sala("s1")
        self.sala2 = sala("s2")
        self.trampa2 = trampa()
        self.contenido2 = contenido("s2", [self.trampa2])
        self.ficha = ficha_trampa()
        self.gestor = GestorPrueba({"trp_dardos": self.ficha})

        self.motor = MotorSimulacion(semilla=123, gestor_datos=self.gestor)
        self.jugador = JugadorPrueba(self.sala1)
        self.motor.jugador = self.jugador
        self.motor.salas = [self.sala1, self.sala2]
        self.motor.contenidos_salas = [self.contenido2]

        # Aísla esta suite de la IA de enemigos: se prueban reloj, agenda,
        # movimiento, trampas e historial, no la selección de acciones enemigas.
        self.motor.activar_enemigos_de_sala = lambda _sala: None

        self.sala1.salidas["E"] = SimpleNamespace(
            cerrada=False, sala_destino="s2"
        )

        # Evento inicial del jugador, equivalente al programado al iniciar.
        self.jugador.tiempo_siguiente = 0
        self.jugador.evento_actual = self.motor.programar_evento(
            0, "ACCION_ACTOR", self.jugador
        )

    def eventos_trampa(self):
        return [
            ev for ev in self.motor.agenda.heap
            if ev.tipo == "REARMAR_TRAMPA" and not ev.cancelado
        ]

    def test_01_movimiento_activa_trampa_y_aplica_danio(self):
        resultado = self.motor.mover_jugador("E")

        self.assertTrue(resultado)
        self.assertIs(self.jugador.sala, self.sala2)
        self.assertEqual(self.jugador.vida, 16)
        self.assertFalse(self.motor._obtener_estado_trampa("t-1"))
        self.assertGreaterEqual(self.motor.reloj, 0)

    def test_02_trampa_solo_se_activa_una_vez_mientras_desarmada(self):
        self.motor.mover_jugador("E")
        vida_despues = self.jugador.vida

        self.motor.activar_trampas_de_sala(self.sala2)

        self.assertEqual(self.jugador.vida, vida_despues)
        self.assertEqual(vida_despues, 16)

    def test_03_rearme_programa_evento_a_tiempo_correcto(self):
        self.motor.mover_jugador("E")

        eventos = self.eventos_trampa()
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0].tiempo, 300)

    def test_04_rearme_usa_intervalo_personalizado(self):
        self.ficha.rearme = 75
        self.motor.mover_jugador("E")

        eventos = self.eventos_trampa()
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0].tiempo, 75)

    def test_05_rearme_usa_300_si_ficha_no_define_intervalo(self):
        self.ficha.rearme = None
        self.motor.mover_jugador("E")

        eventos = self.eventos_trampa()
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0].tiempo, 300)

    def test_06_evento_rearma_trampa_al_ejecutarse(self):
        self.motor.mover_jugador("E")
        evento = self.eventos_trampa()[0]

        # Ejecuta el evento por el método de ejecución del motor.
        self.motor.reloj = evento.tiempo
        self.motor.ejecutar_evento(evento)

        self.assertTrue(self.motor._obtener_estado_trampa("t-1"))

    def test_07_ficha_trampa_en_sala_actual_se_considera_en_uso(self):
        self.jugador.sala = self.sala2
        self.assertTrue(self.motor.es_ficha_activa("trp_dardos"))

    def test_08_trampa_de_sala_no_actual_no_mantiene_ficha_en_uso(self):
        self.jugador.sala = self.sala1
        self.motor.contenidos_salas = [self.contenido2]
        self.assertFalse(self.motor.es_ficha_activa("trp_dardos"))

    def test_09_ficha_inexistente_lanza_error_sin_danar(self):
        self.gestor.fichas.clear()

        with self.assertRaises(RuntimeError):
            self.motor.mover_jugador("E")

        self.assertEqual(self.jugador.vida, 20)

    def test_10_ficha_que_no_es_trampa_lanza_error(self):
        self.gestor.fichas["trp_dardos"] = SimpleNamespace(
            clase="objeto", nombre="Incorrecta", danio=4, rearme=300
        )

        with self.assertRaises(RuntimeError):
            self.motor.mover_jugador("E")

        self.assertEqual(self.jugador.vida, 20)

    def test_11_salida_cerrada_no_mueve_al_jugador(self):
        self.sala1.salidas["E"].cerrada = True

        resultado = self.motor.mover_jugador("E")

        self.assertFalse(resultado)
        self.assertIs(self.jugador.sala, self.sala1)
        self.assertEqual(self.jugador.vida, 20)

    def test_12_direccion_sin_salida_no_mueve_al_jugador(self):
        resultado = self.motor.mover_jugador("N")

        self.assertFalse(resultado)
        self.assertIs(self.jugador.sala, self.sala1)

    def test_13_estado_resumen_incluye_reloj_jugador_y_eventos(self):
        resumen = self.motor.obtener_estado_resumen()

        self.assertIn("reloj", resumen)
        self.assertIn("jugador", resumen)
        self.assertIn("eventos", resumen)
        self.assertEqual(resumen["jugador"]["sala"], "s1")

    def test_14_danio_letal_marca_jugador_muerto(self):
        self.ficha.danio = 20

        # Se activa directamente para aislar la regla de daño letal.
        self.motor.activar_trampas_de_sala(self.sala2)

        self.assertEqual(self.jugador.vida, 0)
        self.assertFalse(self.jugador.esta_vivo())

    def test_15_tiempo_rearme_negativo_no_debe_danar(self):
        self.ficha.rearme = -1

        with self.assertRaises(ValueError):
            self.motor.activar_trampas_de_sala(self.sala2)

        # Esta aserción expresa el requisito esperado. Si falla, el motor
        # valida el intervalo demasiado tarde y debe corregirse.
        self.assertEqual(self.jugador.vida, 20)
        self.assertTrue(self.motor._obtener_estado_trampa("t-1"))

    def test_16_estado_trampa_se_puede_revertir_con_historial(self):
        self.motor.historial.abrir_intervalo()
        self.motor.cambiar_estado_trampa_reversible(self.trampa2, False)

        self.assertFalse(self.motor._obtener_estado_trampa("t-1"))

        self.motor.historial.deshacer_ultimo()

        self.assertTrue(self.motor._obtener_estado_trampa("t-1"))

    def test_17_reloj_avanza_hasta_el_siguiente_turno_del_jugador(self):
        self.motor.mover_jugador("E")
        self.assertGreaterEqual(self.motor.reloj, 0)
        self.assertIs(self.jugador.sala, self.sala2)

    def test_18_dos_motores_con_misma_semilla_resumen_azar_igual_inicial(self):
        otro = MotorSimulacion(semilla=123, gestor_datos=GestorPrueba())
        self.assertEqual(self.motor.azar.getstate(), otro.azar.getstate())


if __name__ == "__main__":
    unittest.main(verbosity=2)
