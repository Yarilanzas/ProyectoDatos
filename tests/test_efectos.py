import unittest
from types import SimpleNamespace

from Modelo.MotorSimulacion import MotorSimulacion
from Modelo.Inventario import Inventario, NodoInventario
from Modelo.Enemigo import Enemigo
from Modelo.Actor import Actor
from Modelo.prueba_actores import JugadorPrueba, GestorPrueba, sala


def nodo(tipo, clase):
    return NodoInventario("inst-" + tipo, tipo, tipo, 1, 1, clase)


FICHAS = {
    "pocion_cura": SimpleNamespace(id="pocion_cura", clase="pocion", cura=5,
                                   modificador_velocidad=None, duracion=None),
    "pocion_veloz": SimpleNamespace(id="pocion_veloz", clase="pocion", cura=None,
                                    modificador_velocidad=50, duracion=300),
    "antidoto": SimpleNamespace(id="antidoto", clase="antidoto"),
    "antorcha": SimpleNamespace(id="antorcha", clase="antorcha", duracion=200),
}


class Base(unittest.TestCase):
    def setUp(self):
        self.s1, self.s2 = sala("s1"), sala("s2")
        self.motor = MotorSimulacion(semilla=1, gestor_datos=GestorPrueba(dict(FICHAS)))
        self.j = JugadorPrueba(self.s1, vida=20)
        self.j.inventario = Inventario(cap_max=10)
        self.motor.jugador = self.j
        self.motor.salas = [self.s1, self.s2]
        self.motor.activar_enemigos_de_sala = lambda _s: None
        self.j.evento_actual = self.motor.programar_evento(0, "ACCION_ACTOR", self.j)
        self.motor.avanzar_hasta_jugador()   # consume el turno inicial

    def esperar(self, n=1):
        for _ in range(n):
            self.assertTrue(self.motor.ejecutar_accion("esperar"))

    def usar(self, tipo, clase):
        self.j.inventario.recoge(nodo(tipo, clase))
        return self.motor.ejecutar_accion("usar", "inst-" + tipo)

    def pendientes(self, tipo):
        return [e for e in self.motor.agenda.heap if e.tipo == tipo and not e.cancelado]


class TestVeneno(Base):
    def test_cinco_ticks_y_termina(self):
        self.motor.aplicar_veneno(self.j, 2)
        self.esperar(4)                       # reloj 400
        self.assertEqual(self.j.vida, 12)
        self.esperar(2)
        self.assertEqual(self.j.vida, 10)     # 5 ticks x 2, ninguno más
        self.assertIsNone(self.j.veneno)

    def test_antidoto_cancela(self):
        self.motor.aplicar_veneno(self.j, 2)
        self.esperar(1)                       # tick en 80
        self.assertEqual(self.j.vida, 18)
        self.assertTrue(self.usar("antidoto", "antidoto"))
        self.esperar(6)
        self.assertEqual(self.j.vida, 18)
        self.assertFalse(self.pendientes("VENENO"))

    def test_antidoto_sin_veneno_se_rechaza(self):
        self.assertFalse(self.usar("antidoto", "antidoto"))
        self.assertEqual(self.motor.reloj, 0)

    def test_deshacer_restaura_vida_reloj_y_tick(self):
        self.motor.aplicar_veneno(self.j, 2)
        self.esperar(1)
        self.motor.historial.deshacer_ultimo()
        self.assertEqual(self.j.vida, 20)
        self.assertEqual(self.motor.reloj, 0)
        ticks = self.pendientes("VENENO")
        self.assertEqual([e.tiempo for e in ticks], [80])

    def test_veneno_mortal_mata_y_cancela(self):
        self.j.vida = 3
        self.motor.aplicar_veneno(self.j, 5)
        self.motor.ejecutar_accion("esperar")
        self.assertFalse(self.j.esta_vivo())
        self.assertFalse(self.pendientes("VENENO"))

    def test_el_tick_no_se_confunde_con_turno_del_jugador(self):
        self.motor.aplicar_veneno(self.j, 1)
        self.esperar(1)
        self.assertEqual(self.motor.reloj, 100)   # el jugador actúa en 100, no en 80


class TestVelocidad(Base):
    def test_reescala_tiempo_restante(self):
        a = Actor("a", 10, 10, 1, 0, 100)
        self.motor.reloj = 0
        self.motor.proxima_accion(a, 100)           # tiempo_siguiente = 100
        viejo = a.evento_actual
        self.motor.reloj = 40
        nuevo = self.motor.cambiar_velocidad(a, 200)  # 60*100//200 = 30
        self.assertEqual(a.tiempo_siguiente, 70)
        self.assertTrue(viejo.cancelado)
        self.assertIs(a.evento_actual, nuevo)
        self.assertGreater(nuevo.secuencia, viejo.secuencia)

    def test_ralentizar_aleja(self):
        a = Actor("a", 10, 10, 1, 0, 200)
        self.motor.proxima_accion(a, 100)           # 50
        self.motor.reloj = 10
        self.motor.cambiar_velocidad(a, 100)        # 40*200//100 = 80
        self.assertEqual(a.tiempo_siguiente, 90)

    def test_sin_accion_pendiente_no_duplica_eventos(self):
        self.motor.cambiar_velocidad(self.j, 150)
        self.assertFalse([e for e in self.motor.agenda.heap
                          if e.actor is self.j and not e.cancelado])
        self.assertEqual(self.j.velocidad, 150)

    def test_pocion_veloz_y_fin_restaura(self):
        self.assertTrue(self.usar("pocion_veloz", "pocion"))
        self.assertEqual(self.j.velocidad, 150)
        self.assertEqual(self.j.tiempo_siguiente, 33)   # 50*100//150
        while self.motor.reloj < 300:
            self.esperar()
        self.assertEqual(self.j.velocidad, 100)
        # En el instante de decisión no debe quedar ningún evento del jugador
        # sobrante (el reajuste del fin del efecto no duplica turnos).
        self.assertEqual(len([e for e in self.motor.agenda.heap
                              if e.actor is self.j and e.tipo == "ACCION_ACTOR"
                              and not e.cancelado]), 0)

    def test_deshacer_pocion(self):
        self.usar("pocion_veloz", "pocion")
        self.motor.historial.deshacer_ultimo()
        self.assertEqual(self.j.velocidad, 100)
        self.assertEqual(self.motor.reloj, 0)
        self.assertEqual(len(list(self.j.inventario)), 1)   # la poción vuelve
        self.assertFalse(self.pendientes("FIN_VELOCIDAD"))


class TestPocionCuraYAntorcha(Base):
    def test_cura_sin_superar_maximo(self):
        self.j.vida = 18
        self.assertTrue(self.usar("pocion_cura", "pocion"))
        self.assertEqual(self.j.vida, 20)
        self.assertEqual(len(list(self.j.inventario)), 0)
        self.assertEqual(self.j.tiempo_siguiente, 50)

    def test_antorcha_se_enciende_y_apaga(self):
        self.assertTrue(self.usar("antorcha", "antorcha"))
        self.assertTrue(self.j.antorcha_encendida)
        self.esperar(3)                          # reloj 250 > 200
        self.assertFalse(self.j.antorcha_encendida)

    def test_no_se_enciende_otra_si_ya_esta_encendida(self):
        self.usar("antorcha", "antorcha")
        self.j.inventario.recoge(NodoInventario("i2", "antorcha", "A", 1, 1, "antorcha"))
        self.assertIsNone(self.motor.usar_objeto())


class TestRegeneracion(Base):
    def test_enemigo_regenera_y_respeta_maximo(self):
        e = Enemigo("e1", 5, 10, 1, 0, 100, "guardian", sala=self.s2)
        e.regeneracion = 3
        self.motor.registrar_enemigo(e)
        self.motor.activar_enemigo(e)
        self.esperar(2)                          # reloj 200
        self.assertEqual(e.vida, 8)
        self.esperar(2)                          # reloj 400
        self.assertEqual(e.vida, 10)

    def test_enemigo_muerto_no_regenera(self):
        e = Enemigo("e1", 5, 10, 1, 0, 100, "guardian", sala=self.s2)
        e.regeneracion = 3
        self.motor.registrar_enemigo(e)
        self.motor.activar_enemigo(e)
        e.recibir_dano(99)
        self.motor._al_morir(e)
        self.esperar(3)
        self.assertEqual(e.vida, 0)
        self.assertFalse(self.pendientes("REGENERAR"))


if __name__ == "__main__":
    unittest.main()