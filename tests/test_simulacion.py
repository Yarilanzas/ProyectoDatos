import unittest
from types import SimpleNamespace

from Modelo.MotorSimulacion import MotorSimulacion
from Modelo.Inventario import Inventario, NodoInventario
from Modelo.Enemigo import Enemigo


class JugadorPrueba:
    def __init__(self, sala):
        self.id = "jugador-test"
        self.sala = sala
        self.vida = 100
        self.vida_max = 100
        self.vivo = True
        self.velocidad = 100
        self.defensa = 0
        self.ataque = 100
        self.tiempo_siguiente = 0
        self.evento_actual = None
        self.inventario = Inventario(cap_max=10)

    def esta_vivo(self):
        return self.vivo

    def recibir_dano(self, cantidad):
        self.vida = max(0, self.vida - cantidad)
        if self.vida == 0:
            self.vivo = False


class GestorPrueba:
    def __init__(self, fichas):
        self.fichas = fichas

    def conectar_estado_juego(self, estado):
        self.estado = estado

    def obtener_ficha(self, id_ficha):
        return self.fichas.get(id_ficha)


def crear_sala(id_sala):
    return SimpleNamespace(
        id=id_sala,
        salidas={},
        rastro=None,
    )


def crear_contenido_trampa():
    trampa = SimpleNamespace(
        instancia="trampa-1",
        tipo="tipo-trampa",
    )

    contenido = SimpleNamespace(
        id_sala="s2",
        trampas=[trampa],
        enemigos=[],
        objetos=[],
    )

    ficha = SimpleNamespace(
        id="tipo-trampa",
        clase="trampa",
        nombre="Trampa de prueba",
        danio=5,
        rearme=300,
    )

    return contenido, ficha


# SIMULACIÓN DE UNA PARTIDA


class TestPartidaCompleta(unittest.TestCase):

    def test_partida_integrada(self):
        print("\n========== INICIO DE PARTIDA ==========")

        sala1 = crear_sala("s1")
        sala2 = crear_sala("s2")

        sala1.salidas["E"] = SimpleNamespace(
            cerrada=False,
            sala_destino="s2",
        )
        sala2.salidas["O"] = SimpleNamespace(
            cerrada=False,
            sala_destino="s1",
        )

        contenido, ficha_trampa = crear_contenido_trampa()

        gestor = GestorPrueba({
            "tipo-trampa": ficha_trampa,
        })

        motor = MotorSimulacion(
            semilla=123,
            gestor_datos=gestor,
        )

        jugador = JugadorPrueba(sala1)

        # El pergamino está disponible desde el inicio.
        pergamino = NodoInventario(
            "pergamino-1",
            "tipo-pergamino",
            "Pergamino de retroceso",
            1,
            10,
            "pergamino_retroceso",
        )
        jugador.inventario.recoge(pergamino)

        # Enemigo de prueba situado en la segunda sala.
        enemigo = Enemigo(
            id="enemigo-1",
            vida=20,
            vida_max=20,
            ataque=2,
            defensa=0,
            velocidad=100,
            comportamiento="guardian",
            sala=sala2,
            tipo_id="tipo-enemigo",
        )

        motor.iniciar_partida(
            jugador,
            [sala1, sala2],
            [enemigo],
            [contenido],
        )

        # No depender de una API ni de datos externos.
        motor.activar_enemigos_de_sala = (
            lambda sala: (
                motor.activar_enemigos(
                    motor.obtener_enemigos(
                        sala=sala,
                        solo_vivos=True,
                    )
                )
            )
        )

        # La activación de enemigos de la sala inicial ya ocurrió
        # al iniciar la partida. La segunda sala activa al enemigo
        # cuando el jugador se mueve hacia ella.

        print("1. Partida inicializada")
        print("   Sala:", jugador.sala.id)
        print("   Vida:", jugador.vida)
        self.assertEqual(motor.reloj, 0)

        # MOVIMIENTO Y TRAMPA


        print("\n2. Jugador se mueve al este")
        resultado = motor.ejecutar_accion("mover", "E")

        self.assertTrue(resultado)
        self.assertIs(jugador.sala, sala2)
        # 100 - 5 (trampa) - 2 (el guardián, activado al entrar, actúa en t=100
        # antes que el jugador por menor secuencia; ataque 2 + azar 0).
        self.assertEqual(motor.reloj, 100)
        self.assertEqual(jugador.vida, 93)
        self.assertFalse(
            motor._obtener_estado_trampa("trampa-1")
        )

        eventos_rearme = [
            evento for evento in motor.agenda.heap
            if evento.tipo == "REARMAR_TRAMPA"
            and not evento.cancelado
        ]

        self.assertEqual(len(eventos_rearme), 1)
        print("   Sala actual:", jugador.sala.id)
        print("   Vida después de la trampa:", jugador.vida)
        print("   Trampa desarmada y rearme programado")


        # RECOGER OBJETO


        daga = NodoInventario(
            "daga-1",
            "tipo-daga",
            "Daga de prueba",
            1,
            20,
            "arma",
            ataque_bonus=3,
        )

        motor.objetos_suelo.append(["s2", [daga]])

        print("\n3. Jugador recoge una daga")
        reloj_antes_recoger = motor.reloj

        resultado = motor.ejecutar_accion(
            "recoger",
            "daga-1",
        )

        self.assertTrue(resultado)
        self.assertIn(
            "daga-1",
            [objeto.instancia_id for objeto in jugador.inventario],
        )
        self.assertNotIn(
            daga,
            motor.obtener_objetos_suelo(sala2),
        )

        print("   Daga recogida")
        print("   Reloj:", motor.reloj)


        # RETROCESO DE LA RECOLECCIÓN


        print("\n4. Jugador usa el pergamino")

        resultado = motor.usar_pergamino_retroceso(pergamino)

        self.assertTrue(resultado)

        ids_inventario = [
            objeto.instancia_id
            for objeto in jugador.inventario
        ]

        self.assertNotIn("pergamino-1", ids_inventario)
        self.assertNotIn("daga-1", ids_inventario)
        self.assertIn(
            daga,
            motor.obtener_objetos_suelo(sala2),
        )
        self.assertEqual(motor.reloj, reloj_antes_recoger)

        print("   Pergamino consumido")
        print("   Daga devuelta al suelo")
        print("   Reloj restaurado:", motor.reloj)

        # COMBATE

        print("\n5. Jugador ataca al enemigo")

        resultado = motor.ejecutar_accion(
            "atacar",
            "enemigo-1",
        )

        self.assertTrue(resultado)
        self.assertFalse(enemigo.esta_vivo())
        self.assertEqual(enemigo.vida, 0)

        print("   Enemigo derrotado")
        print("   Vida del enemigo:", enemigo.vida)

        # ESTADO FINAL

        print("\n6. Resumen final")
        resumen = motor.obtener_estado_resumen()

        self.assertIn("reloj", resumen)
        self.assertIn("jugador", resumen)
        self.assertIn("enemigos", resumen)
        self.assertIn("eventos", resumen)

        print("   Reloj:", resumen["reloj"])
        print("   Jugador:", resumen["jugador"])
        print("   Enemigos:", resumen["enemigos"])
        print("   Eventos pendientes:", len(resumen["eventos"]))

        print("\n========== PARTIDA FINALIZADA ==========")


if __name__ == "__main__":
    unittest.main(verbosity=2)