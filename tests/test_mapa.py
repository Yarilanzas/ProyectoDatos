# Pruebas del comando `mapa` (T033 a T036, Historia 3, y parte de `mapa` del Escenario US2-4).
# FR-005, FR-010, FR-011, FR-012, FR-018, FR-019, FR-020, SC-002. Contrato: contracts/comandos.md.

import os
import sys

# Permite ejecutar este archivo desde cualquier carpeta (PyCharm, unittest o pytest).
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import unittest

from Vista.VistaConsola import AYUDA, VistaConsola
from tests.test_antorcha import CONTENIDO as CONTENIDO_ANTORCHA, ID_ANTORCHA
from tests.test_antorcha import mapa as mapa_antorcha
from tests.test_conocimiento import BaseConocimiento, foto
from tests.test_conocimiento import mapa as mapa_conocimiento
from tests.utiles_niebla import LLAVE, PERGAMINO, contenido_sala, salida


def mapa_desordenado():
    # Se empieza en 7: las salas se revelan en el orden 7, 3, 9, 1, que no es el de sus ids.
    return [
        {"id": 7, "nombre": "Inicio", "salidas": {"O": salida(3), "E": salida(9)}},
        {"id": 3, "nombre": "Oeste", "salidas": {"E": salida(7), "S": salida(1)}},
        {"id": 9, "nombre": "Este", "salidas": {"O": salida(7)}},
        {"id": 1, "nombre": "Fondo", "salidas": {"N": salida(3), "S": salida(20)}},
        {"id": 20, "nombre": "Salida", "salidas": {"N": salida(1)}},
    ]


def mapa_cerrado():
    # 1 y 2 se conectan entre sí; 3 (la salida) no se alcanza, así que nunca se revela.
    return [
        {"id": 1, "nombre": "Entrada", "salidas": {"E": salida(2)}},
        {"id": 2, "nombre": "Pasillo", "salidas": {"O": salida(1)}},
        {"id": 3, "nombre": "Salida", "salidas": {}},
    ]


class BaseMapa(BaseConocimiento):

    def texto_mapa(self, motor):
        lineas = []
        VistaConsola(salida=lineas.append).mostrar_mapa(motor.mapa_conocido())
        return lineas

    def mapa_por_comando(self):
        # Lo que el controlador le pasa a la vista con el comando `mapa`.
        vista = self.controlador.vista
        vista.lineas.clear()
        self.assertTrue(self.controlador.ejecutar("mapa"))
        llamadas = [args for nombre, args in vista.lineas if nombre == "mostrar_mapa"]
        self.assertEqual(len(llamadas), 1, vista.lineas)
        return llamadas[0][0]

    def bitacora(self):
        with open(os.path.join(self.carpeta, "partida.log"), encoding="utf-8") as archivo:
            return archivo.read()


class TestMapaConocido(BaseMapa):

    def test_fr005_fr012_fr018_exploradas_con_salidas_y_avistadas_aparte(self):
        # Escenario US3-1: exploradas 1 y 2.
        motor = self.partida(mapa_conocimiento())
        self.acciones(motor, ("mover", "E"))
        self.assertEqual(self.texto_mapa(motor), [
            "Mapa conocido:",
            "  Sala 1: Entrada",
            "    E -> sala 2   costo 100   abierta",
            "    S -> sala 3   costo 100   abierta",
            "  Sala 2: Pasillo",
            "    O -> sala 1   costo 100   abierta",
            "    S -> sala 4   costo 100   abierta",
            "Avistadas: 3, 4",
        ])

    def test_fr018_el_dto_trae_direccion_destino_costo_y_estado(self):
        # Escenario US3-1, por el comando: el controlador pasa el DTO a la vista.
        motor = self.partida(mapa_conocimiento())
        self.acciones(motor, ("mover", "E"))
        mapa = self.mapa_por_comando()

        self.assertEqual([sala.id for sala in mapa.exploradas], [1, 2])
        self.assertEqual([sala.nombre for sala in mapa.exploradas], ["Entrada", "Pasillo"])
        self.assertEqual(mapa.avistadas, [3, 4])
        self.assertEqual([(s.direccion, s.destino_id, s.costo, s.estado) for s in mapa.exploradas[1].salidas],
                         [("O", 1, 100, "abierta"), ("S", 4, 100, "abierta")])

    def test_fr018_ninguna_sala_desconocida_aparece_como_entrada_propia(self):
        # Escenario US3-1: 5 y 6 son desconocidas.
        motor = self.partida(mapa_conocimiento())
        self.acciones(motor, ("mover", "E"))
        mapa = motor.mapa_conocido()
        mostradas = [sala.id for sala in mapa.exploradas] + list(mapa.avistadas)
        for id_sala in (5, 6):
            self.assertNotIn(id_sala, mostradas)
        for linea in self.texto_mapa(motor):
            self.assertNotIn("sala 5", linea.lower())
            self.assertNotIn("sala 6", linea.lower())


class TestMapaEsConsulta(BaseMapa):
    # Escenario US3-2 (FR-019): no cambia reloj, acciones, bitácora ni ningún otro estado.

    def sin_efectos(self, motor):
        antes = (motor.obtener_estado_resumen(), motor.acciones_jugador, foto(motor.conocimiento),
                 list(motor.mensajes.ultimos()), motor.historial.puede_deshacer(), self.bitacora())
        self.mapa_por_comando()
        despues = (motor.obtener_estado_resumen(), motor.acciones_jugador, foto(motor.conocimiento),
                   list(motor.mensajes.ultimos()), motor.historial.puede_deshacer(), self.bitacora())
        self.assertEqual(despues, antes)

    def test_fr019_en_el_instante_0(self):
        motor = self.partida(mapa_conocimiento())
        self.sin_efectos(motor)
        self.assertEqual(motor.reloj, 0)
        self.assertEqual(motor.acciones_jugador, 0)

    def test_fr019_despues_de_moverse_y_con_pergamino(self):
        motor = self.partida(mapa_conocimiento(), [contenido_sala(1, objetos=[PERGAMINO])])
        self.acciones(motor, ("recoger", f"obj-cripta-niebla-1-{PERGAMINO}-0"), ("mover", "E"))
        self.sin_efectos(motor)

    def test_fr019_con_enemigos_en_la_sala(self):
        motor = self.partida(mapa_conocimiento(), [contenido_sala(2, enemigos=["e-rata"])])
        self.acciones(motor, ("mover", "E"))
        self.assertTrue(motor.obtener_enemigos(sala=motor.jugador.sala, solo_vivos=True))
        self.sin_efectos(motor)

    def test_fr019_con_la_partida_terminada(self):
        motor = self.partida(mapa_cerrado(), sala_salida=2)
        self.acciones(motor, ("mover", "E"))
        self.assertEqual(motor.estado_partida(), "victoria")
        self.sin_efectos(motor)

    def test_fr019_mapa_no_se_anota_en_la_bitacora(self):
        motor = self.partida(mapa_conocimiento())
        self.acciones(motor, ("mover", "E"))
        self.controlador.ejecutar("e")    # una acción por el controlador sí se anota
        antes = self.bitacora()
        self.controlador.ejecutar("mapa")
        self.assertEqual(self.bitacora(), antes)
        self.assertNotIn("mapa", antes)

    def test_fr020_la_ayuda_incluye_mapa(self):
        self.assertIn("mapa", AYUDA)


class TestMapaConAntorcha(BaseMapa):

    def test_fr011_fr018_sc002_puerta_de_una_vecina_sin_observar(self):
        # Escenario US2-4, parte de `mapa`: C (3) se exploró con antorcha desde B; C -> D no se observó.
        motor = self.partida(mapa_antorcha(), CONTENIDO_ANTORCHA)
        self.acciones(motor, ("recoger", ID_ANTORCHA), ("usar", ID_ANTORCHA), ("mover", "E"))
        lineas = self.texto_mapa(motor)

        inicio = lineas.index("  Sala 3: C")
        self.assertEqual(lineas[inicio + 1:inicio + 3], [
            "    S -> sala 2   costo 100   abierta",      # entra a B, donde está el jugador
            "    E -> sala 4   costo 100   sin observar",
        ])

        sala_c = [sala for sala in motor.mapa_conocido().exploradas if sala.id == 3][0]
        salida_cd = [s for s in sala_c.salidas if s.direccion == "E"][0]
        self.assertEqual((salida_cd.destino_id, salida_cd.costo, salida_cd.estado), (4, 100, "sin observar"))


class TestContratoDeSalida(BaseMapa):

    def test_fr018_salas_por_id_ascendente(self):
        motor = self.partida(mapa_desordenado())
        self.acciones(motor, ("mover", "O"))
        self.assertEqual([s.id for s in motor.conocimiento.reveladas], [7, 3, 9, 1])
        self.assertEqual(self.texto_mapa(motor), [
            "Mapa conocido:",
            "  Sala 3: Oeste",
            "    E -> sala 7   costo 100   abierta",
            "    S -> sala 1   costo 100   abierta",
            "  Sala 7: Inicio",
            "    O -> sala 3   costo 100   abierta",
            "    E -> sala 9   costo 100   abierta",
            "Avistadas: 1, 9",
        ])

    def test_fr018_avistadas_ninguna(self):
        motor = self.partida(mapa_cerrado(), forzar=True)  # salida inalcanzable a propósito: forzar=True (spec 002, FR-021)
        self.acciones(motor, ("mover", "E"))
        lineas = self.texto_mapa(motor)
        self.assertEqual(lineas[-1], "Avistadas: ninguna")
        self.assertEqual(motor.mapa_conocido().avistadas, [])
        self.assertNotIn("Sala 3", "\n".join(lineas))

    def test_fr005_avistada_solo_por_su_id(self):
        motor = self.partida(mapa_conocimiento())
        texto = "\n".join(self.texto_mapa(motor))
        for nombre in ("Pasillo", "Bodega"):    # nombres de 2 y 3, que están avistadas
            self.assertNotIn(nombre, texto)
        self.assertNotIn("Sala 2:", texto)
        self.assertNotIn("Sala 3:", texto)
        self.assertTrue(texto.endswith("Avistadas: 2, 3"))

    def test_fr010_fr018_sin_llaves_enemigos_trampas_ni_objetos(self):
        salas = mapa_conocimiento(cerrada=True, llave=LLAVE)
        contenido = [contenido_sala(1, enemigos=["e-rata"], trampas=["t-dardos"], objetos=[LLAVE, PERGAMINO])]
        motor = self.partida(salas, contenido)
        texto = "\n".join(self.texto_mapa(motor))

        self.assertIn("    E -> sala 2   costo 100   cerrada", texto)
        for prohibido in ("llave", LLAVE, PERGAMINO, "e-rata", "Rata", "t-dardos", "Dardos", "obj-"):
            self.assertNotIn(prohibido, texto)

    def test_fr005_costo_distinto_de_100(self):
        # El DTO `Salida` aún no trae `costo` (T010, capacidad de terreno y costos): se pone a mano en la
        # salida, que es lo que `costo_salida` lee.
        motor = self.partida(mapa_conocimiento())
        self.puerta(motor, 1, "E").costo = 250
        self.assertIn("    E -> sala 2   costo 250   abierta", self.texto_mapa(motor))
        self.assertIn("    S -> sala 3   costo 100   abierta", self.texto_mapa(motor))

    def test_fr012_sc002_muestra_el_recuerdo_y_no_la_puerta_real(self):
        motor = self.partida(mapa_conocimiento())
        self.puerta(motor, 1, "E").cerrada = True     # cambio real que el jugador no observó
        self.assertIn("    E -> sala 2   costo 100   abierta", self.texto_mapa(motor))

        motor = self.partida(mapa_conocimiento(cerrada=True))
        self.puerta(motor, 1, "E").cerrada = False
        self.assertIn("    E -> sala 2   costo 100   cerrada", self.texto_mapa(motor))


if __name__ == "__main__":
    unittest.main()
