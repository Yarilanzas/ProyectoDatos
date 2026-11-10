# Pruebas del viaje «ir a» (Fase 4, Historia 4): T044 a T054 y la parada por paso rechazado de T060.
# FR-011, FR-014, FR-021 a FR-029, FR-031, SC-002, SC-005, PR-09, PR-10.
# Contratos: contracts/comandos.md e interfaz-ruta.md.
#
# Todo se prueba con un buscador inyectado (`buscador_prueba` o un guion). El cuerpo real de `primer_paso`
# delega en Modelo/BusquedaRuta.py de Persona A (D-PEND-01, opción A), que aún no existe: la prueba con la
# búsqueda real es T064.
#
# Mapa principal (tests.test_conocimiento.mapa): 1 -E-> 2, 1 -S-> 3, 2 -S-> 4, 3 -E-> 4, 4 -S-> 5 -E-> 6,
# todas de ida y vuelta. Se empieza en 1 y la salida (6) queda lejos.

import os
import sys

# Permite ejecutar este archivo desde cualquier carpeta (PyCharm, unittest o pytest).
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import tempfile
import unittest
from types import SimpleNamespace

from DTOS.Salida import Salida
from Modelo.Conocimiento import ABIERTA, CERRADA, Conocimiento, GrafoConocido
from Modelo.MotorSimulacion import MotorSimulacion
from Modelo.retroceso import Historial
from Modelo.rutas_ir_a import Paso
from Modelo.Viaje import DANO, DESTINO, ENEMIGOS, FIN_PARTIDA, PASO_RECHAZADO, SIN_RUTA, Viaje
from tests.test_antorcha import CONTENIDO as CONTENIDO_ANTORCHA, ID_ANTORCHA
from tests.test_antorcha import mapa as mapa_antorcha
from tests.test_conocimiento import BaseConocimiento
from tests.test_conocimiento import mapa as mapa_cuadro
from tests.utiles_niebla import (ANTORCHA, CRIPTA_NIEBLA, ENEMIGO_LENTO, LLAVE, PERGAMINO, buscador_prueba,
                                 contenido_sala, partida_niebla, salida)

AVISO_DESCONOCIDA = "No conoces esa sala."
AVISO_ACTUAL = "Ya estás en esa sala."
AVISO_SIN_RUTA = "No conoces una ruta hasta esa sala."
AVISO_USO = "Use: ir a <sala>"
AVISO_NO_DISPONIBLE = "«ir a» aún no está disponible."
PARADA_DANO = "Viaje detenido: recibiste daño."
PARADA_ENEMIGOS = "Viaje detenido: hay enemigos en la sala."
PARADA_SIN_RUTA = "Viaje detenido: ya no conoces una ruta."
RECHAZO_MOVER = "No se pudo realizar esa acción"

# Recorre el cuadro 1-2-4-3 y vuelve a 1: quedan exploradas 1 a 4 y todas sus puertas recordadas abiertas.
CUADRO = (("mover", "E"), ("mover", "S"), ("mover", "O"), ("mover", "N"))


def id_objeto(sala, tipo, indice):
    return f"obj-{CRIPTA_NIEBLA}-{sala}-{tipo}-{indice}"


def guion(*pasos):
    """Buscador que da, desde cada sala, la dirección indicada: [(id_origen, dirección)].

    Si la dirección no está en el grafo devuelve igual el paso (hacia la misma sala), para simular un
    paso que el motor rechaza (FR-027f). Sin entrada para el origen, no hay ruta.
    """
    def buscar(grafo, origen, destino):
        for id_origen, direccion in pasos:
            if id_origen != origen.id:
                continue
            for direccion_arista, vecina, costo in grafo.aristas(origen):
                if direccion_arista == direccion:
                    return Paso(direccion, vecina, costo)
            return Paso(direccion, origen, 0)
        return None
    return buscar


def contador(buscar, origenes):
    # Envuelve un buscador y anota el id de la sala desde la que se calculó cada ruta.
    def buscar_contando(grafo, origen, destino):
        origenes.append(origen.id)
        return buscar(grafo, origen, destino)
    return buscar_contando


class BaseViaje(BaseConocimiento):

    def partida(self, salas, contenido=(), buscar=buscador_prueba, **opciones):
        motor = super().partida(salas, contenido, **opciones)
        if buscar is not None:
            self.controlador.buscar_ruta = buscar
        return motor

    def gemela(self, salas, contenido=(), **opciones):
        # Otra partida igual (mismo paquete y semilla), para comparar contra `mover` a mano.
        carpeta = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(carpeta.cleanup)
        motor, controlador = partida_niebla(carpeta.name, salas, contenido, **opciones)
        self.addCleanup(controlador._cerrar)
        return motor, controlador

    def ejecutar(self, controlador, linea):
        vista = controlador.vista
        vista.lineas.clear()
        self.assertTrue(controlador.ejecutar(linea))
        return list(vista.lineas)

    def ir(self, destino):
        return self.ejecutar(self.controlador, f"ir a {destino}")

    def avisos(self, lineas):
        return [args[0] for nombre, args in lineas if nombre == "mostrar_aviso"]

    def errores(self, lineas):
        return [args[0] for nombre, args in lineas if nombre == "mostrar_error"]

    def movimientos(self, carpeta=None):
        # Líneas de acción de la bitácora, después del separador.
        with open(os.path.join(carpeta or self.carpeta, "partida.log"), encoding="utf-8") as archivo:
            lineas = archivo.read().splitlines()
        return lineas[lineas.index("---") + 1:]

    def sin_efectos(self, motor):
        return (motor.reloj, motor.acciones_jugador, motor.obtener_estado_resumen(), self.movimientos())


# T044: GrafoConocido y Escenario US2-4, parte de «ir a».

class SalaFalsa:
    def __init__(self, id_sala, salidas):
        self.id = id_sala
        self.salidas = salidas


def conocimiento_falso(salas):
    def destino_de(salida_falsa):
        for sala in salas:
            if sala.id == salida_falsa.sala_destino:
                return sala
        return None
    return Conocimiento(salas, destino_de)


def puerta(destino, cerrada=False):
    return Salida(destino, cerrada, None, None)


class TestGrafoConocido(unittest.TestCase):

    def aristas(self, grafo, sala):
        return [(direccion, vecina.id, costo) for direccion, vecina, costo in grafo.aristas(sala)]

    def test_fr023_fr029_solo_salas_exploradas_y_puertas_recordadas_abiertas(self):
        uno = SalaFalsa(1, {"E": puerta(2), "S": puerta(3, cerrada=True), "O": puerta(4)})
        dos = SalaFalsa(2, {"O": puerta(1)})
        tres = SalaFalsa(3, {"N": puerta(1)})
        cuatro = SalaFalsa(4, {})
        salas = [uno, dos, tres, cuatro]
        conocimiento = conocimiento_falso(salas)
        grafo = GrafoConocido(conocimiento, MotorSimulacion().costo_salida)
        historial = Historial()

        self.assertEqual(grafo.cantidad_salas, 4)
        self.assertEqual([grafo.ordinal(sala) for sala in salas], [0, 1, 2, 3])

        conocimiento.entrar(uno, False, historial)
        # 2, 3 y 4 solo están avistadas: no hay aristas hacia ellas (FR-023).
        self.assertEqual(self.aristas(grafo, uno), [])
        self.assertEqual(self.aristas(grafo, dos), [])  # una sala no explorada no tiene aristas

        conocimiento.entrar(dos, False, historial)
        conocimiento.entrar(tres, False, historial)
        # 1 -S-> 3 está recordada cerrada (FR-029) y 4 sigue sin explorar.
        self.assertEqual(self.aristas(grafo, uno), [("E", 2, 100)])
        self.assertEqual(self.aristas(grafo, tres), [("N", 1, 100)])

    def test_fr011_una_salida_sin_observar_no_existe_para_la_busqueda(self):
        # Con antorcha desde 1 se exploran 2 y 3 sin entrar: 2 -S-> 3 queda sin observar.
        uno = SalaFalsa(1, {"E": puerta(2), "S": puerta(3)})
        dos = SalaFalsa(2, {"S": puerta(3)})
        tres = SalaFalsa(3, {})
        conocimiento = conocimiento_falso([uno, dos, tres])
        grafo = GrafoConocido(conocimiento, MotorSimulacion().costo_salida)

        conocimiento.entrar(uno, True, Historial())
        self.assertEqual(self.aristas(grafo, uno), [("E", 2, 100), ("S", 3, 100)])
        self.assertEqual(self.aristas(grafo, dos), [])

    def test_fr005_fr024_el_costo_viene_de_costo_salida(self):
        uno = SalaFalsa(1, {"E": puerta(2)})
        dos = SalaFalsa(2, {"O": puerta(1)})
        uno.salidas["E"].costo = 7  # puesto a mano: el DTO Salida aún no trae costo (T010)
        conocimiento = conocimiento_falso([uno, dos])
        grafo = GrafoConocido(conocimiento, MotorSimulacion().costo_salida)
        historial = Historial()
        conocimiento.entrar(uno, False, historial)
        conocimiento.entrar(dos, False, historial)
        self.assertEqual(self.aristas(grafo, uno), [("E", 2, 7)])
        self.assertEqual(self.aristas(grafo, dos), [("O", 1, 100)])


class TestGrafoDelMotor(BaseViaje):

    def test_fr005_fr023_el_motor_arma_el_grafo_con_su_conocimiento_y_costo_salida(self):
        motor = self.partida(mapa_cuadro())
        self.acciones(motor, *CUADRO)
        self.puerta(motor, 1, "E").costo = 30
        grafo = motor.grafo_conocido()
        aristas = [(d, v.id, c) for d, v, c in grafo.aristas(self.sala(motor, 1))]
        self.assertEqual(aristas, [("E", 2, 30), ("S", 3, 100)])

    def test_fr011_fr023_sc002_escenario_us2_4_ir_a_no_usa_salidas_sin_observar(self):
        # Escenario US2-4, parte de «ir a». La antorcha explora 3 (detrás de una puerta cerrada) y 5,
        # pero sus salidas quedan sin observar: hacia 3 no hay ruta; hacia 5 sí, por 2 -S-> 5.
        motor = self.partida(mapa_antorcha(), CONTENIDO_ANTORCHA)
        self.acciones(motor, ("recoger", ID_ANTORCHA), ("usar", ID_ANTORCHA), ("mover", "E"))
        antes = self.sin_efectos(motor)

        self.assertEqual(self.avisos(self.ir(3)), [AVISO_SIN_RUTA])
        self.assertEqual(self.sin_efectos(motor), antes)
        self.assertFalse(any(enemigo.activo for enemigo in motor.enemigos))  # FR-010

        self.assertEqual(self.avisos(self.ir(5)), ["Llegaste a la sala 5."])
        self.assertEqual(self.movimientos()[-1], "mover S")


# T045: Escenario US4-1.

class TestRechazos(BaseViaje):

    def test_fr022_sc005_escenario_us4_1_sala_avistada_desconocida_inexistente_o_no_valida(self):
        # Apéndice B: «ir a» hacia sala no explorada. Todos dan el mismo aviso, para no revelar si existe.
        motor = self.partida(mapa_cuadro())
        antes = self.sin_efectos(motor)
        for destino in (2, 3, 5, 99, "abc"):
            self.assertEqual(self.avisos(self.ir(destino)), [AVISO_DESCONOCIDA], destino)
            self.assertEqual(self.sin_efectos(motor), antes, destino)


# T046: Escenario US4-2.

class TestPuertaRecordadaAbierta(BaseViaje):

    def test_fr026_con_otra_ruta_el_viaje_sigue_por_ella(self):
        # Apéndice B: puerta recordada abierta que está cerrada. 2 -S-> 4 se cierra sin que el jugador
        # lo vea; al llegar a 2 la observa y el recálculo rodea por 1 y 3.
        motor = self.partida(mapa_cuadro())
        self.acciones(motor, *CUADRO)
        self.puerta(motor, 2, "S").cerrada = True
        antes = len(self.movimientos())

        self.assertEqual(self.avisos(self.ir(4)), ["Llegaste a la sala 4."])
        self.assertEqual(self.movimientos()[antes:], ["mover E", "mover O", "mover S", "mover E"])
        self.assertEqual(self.recuerdo(motor, 2, "S"), CERRADA)
        self.assertEqual(motor.jugador.sala.id, 4)

    def test_fr026_fr027_sin_otra_ruta_se_detiene_sin_tiempo_adicional(self):
        pasos = (("mover", "E"), ("mover", "S"), ("mover", "N"), ("mover", "O"))  # 3 nunca se explora
        motor = self.partida(mapa_cuadro())
        self.acciones(motor, *pasos)
        self.puerta(motor, 2, "S").cerrada = True
        gemelo, _ = self.gemela(mapa_cuadro())
        for accion in pasos:
            self.assertTrue(gemelo.ejecutar_accion(*accion))
        self.puerta(gemelo, 2, "S").cerrada = True
        self.assertTrue(gemelo.ejecutar_accion("mover", "E"))

        self.assertEqual(self.avisos(self.ir(4)), [PARADA_SIN_RUTA])
        self.assertEqual(self.movimientos()[-1], "mover E")
        self.assertEqual(motor.jugador.sala.id, 2)
        # Mismo estado que un solo `mover E`: el recálculo sin ruta no consume tiempo (FR-027d).
        self.assertEqual(motor.obtener_estado_resumen(), gemelo.obtener_estado_resumen())


# T047: Escenario US4-3.

def mapa_pasillo():
    # 1 - 2 - 3 - 4 en línea, de ida y vuelta. La salida (9) no se alcanza.
    return [
        {"id": 1, "nombre": "A", "salidas": {"E": salida(2)}},
        {"id": 2, "nombre": "B", "salidas": {"O": salida(1), "E": salida(3)}},
        {"id": 3, "nombre": "C", "salidas": {"O": salida(2), "E": salida(4)}},
        {"id": 4, "nombre": "D", "salidas": {"O": salida(3)}},
        {"id": 9, "nombre": "Salida", "salidas": {}},
    ]


class TestParadaPorEnemigos(BaseViaje):

    def test_fr027b_escenario_us4_3_enemigo_dormido_se_activa_y_detiene(self):
        # Apéndice B: «ir a» entra a sala con enemigos dormidos. La antorcha explora 3 sin activar a la
        # babosa (FR-010); al entrar en viaje, se activa (§2.4) y el viaje se detiene ahí.
        contenido = [contenido_sala(1, objetos=[ANTORCHA]),
                     contenido_sala(3, enemigos=["e-babosa"], tipo_enemigo=ENEMIGO_LENTO)]
        motor = self.partida(mapa_pasillo(), contenido)
        self.acciones(motor, ("recoger", id_objeto(1, ANTORCHA, 0)), ("usar", id_objeto(1, ANTORCHA, 0)),
                      ("mover", "E"), ("mover", "O"))
        # La antorcha no carga el contenido de 3: la babosa aún no está en juego (FR-010).
        self.assertEqual(motor.obtener_enemigos(sala=self.sala(motor, 3)), [])

        self.assertEqual(self.avisos(self.ir(3)), [PARADA_ENEMIGOS])
        babosa, = motor.obtener_enemigos(sala=self.sala(motor, 3))
        self.assertTrue(babosa.activo)
        self.assertEqual(motor.jugador.sala.id, 3)

    def test_fr027b_se_detiene_en_la_sala_intermedia_con_enemigos_activos(self):
        contenido = [contenido_sala(2, enemigos=["e-babosa"], tipo_enemigo=ENEMIGO_LENTO)]
        motor = self.partida(mapa_pasillo(), contenido)
        self.acciones(motor, ("mover", "E"), ("mover", "E"), ("mover", "E"))
        vida = motor.jugador.vida

        self.assertEqual(self.avisos(self.ir(1)), [PARADA_ENEMIGOS])
        self.assertEqual(motor.jugador.sala.id, 2)
        self.assertEqual(motor.jugador.vida, vida)
        self.assertEqual(self.movimientos()[-2:], ["mover O", "mover O"])

    def test_fr027b_enemigos_ya_derrotados_no_detienen(self):
        motor = self.partida(mapa_pasillo(), [contenido_sala(2, enemigos=["e-rata"])])
        self.acciones(motor, ("mover", "E"))
        rata = motor.enemigos[0]
        while rata.esta_vivo():
            self.acciones(motor, ("atacar", "e-rata"))
        self.acciones(motor, ("mover", "E"), ("mover", "E"))

        self.assertEqual(self.avisos(self.ir(1)), ["Llegaste a la sala 1."])
        self.assertEqual(self.movimientos()[-3:], ["mover O", "mover O", "mover O"])


# T048: Escenario US4-4.

class TestPergaminoTrasViaje(BaseViaje):

    def test_fr014_fr031_escenario_us4_4_tras_viaje_completo_deshace_solo_el_ultimo_paso(self):
        # Apéndice B: pergamino durante un viaje.
        motor = self.partida(mapa_cuadro(), [contenido_sala(1, objetos=[PERGAMINO])])
        self.acciones(motor, ("recoger", id_objeto(1, PERGAMINO, 0)), *CUADRO)
        self.assertEqual(self.avisos(self.ir(4)), ["Llegaste a la sala 4."])

        self.ejecutar(self.controlador, "retroceder")
        self.assertEqual(motor.jugador.sala.id, 2)
        self.assertEqual(self.movimientos()[-3:], ["mover E", "mover S", "retroceder"])

    def test_fr014_fr031_tras_viaje_detenido_deshace_el_paso_con_su_conocimiento(self):
        pasos = (("mover", "E"), ("mover", "S"), ("mover", "N"), ("mover", "O"))
        motor = self.partida(mapa_cuadro(), [contenido_sala(1, objetos=[PERGAMINO])])
        self.acciones(motor, ("recoger", id_objeto(1, PERGAMINO, 0)), *pasos)
        self.puerta(motor, 2, "S").cerrada = True
        self.assertEqual(self.avisos(self.ir(4)), [PARADA_SIN_RUTA])
        self.assertEqual(self.recuerdo(motor, 2, "S"), CERRADA)

        self.ejecutar(self.controlador, "retroceder")
        self.assertEqual(motor.jugador.sala.id, 1)
        self.assertEqual(self.recuerdo(motor, 2, "S"), ABIERTA)  # el recuerdo vuelve con el paso
        self.assertEqual(self.movimientos()[-2:], ["mover E", "retroceder"])  # el viaje no se reanuda


# T049: Escenario US4-5, parte que no depende de Modelo/BusquedaRuta.py.

class TestDesempateConBuscadorInyectado(BaseViaje):

    def test_fr024_escenario_us4_5_empate_va_a_la_vecina_de_menor_id(self):
        # 1 -> 2 -> 4 y 1 -> 3 -> 4 cuestan 200: el primer paso va a 2.
        motor = self.partida(mapa_cuadro())
        self.acciones(motor, *CUADRO)
        self.assertEqual(self.avisos(self.ir(4)), ["Llegaste a la sala 4."])
        self.assertEqual(self.movimientos()[-2:], ["mover E", "mover S"])

    def test_fr021_el_viaje_sigue_el_paso_que_entrega_el_buscador(self):
        motor = self.partida(mapa_cuadro(), buscar=guion((1, "S"), (3, "E")))
        self.acciones(motor, *CUADRO)
        self.assertEqual(self.avisos(self.ir(4)), ["Llegaste a la sala 4."])
        self.assertEqual(self.movimientos()[-2:], ["mover S", "mover E"])


# T050: Escenario US4-6.

class TestParadaPorDano(BaseViaje):

    def test_fr027c_escenario_us4_6_veneno_activo_desde_antes_de_la_orden(self):
        motor = self.partida(mapa_cuadro())
        self.acciones(motor, *CUADRO)
        motor.aplicar_veneno(motor.jugador, 1)
        vida = motor.jugador.vida

        self.assertEqual(self.avisos(self.ir(4)), [PARADA_DANO])
        self.assertEqual(motor.jugador.sala.id, 2)
        self.assertLess(motor.jugador.vida, vida)
        self.assertEqual(self.movimientos()[-1], "mover E")

    def test_fr027c_trampa_rearmada_en_la_ruta(self):
        motor = self.partida(mapa_cuadro(), [contenido_sala(3, trampas=["t-dardos"])],
                             buscar=guion((1, "S"), (3, "E")))
        self.acciones(motor, *CUADRO)
        while not motor._obtener_estado_trampa("t-dardos", True):
            self.acciones(motor, ("esperar",))
        vida = motor.jugador.vida

        self.assertEqual(self.avisos(self.ir(4)), [PARADA_DANO])
        self.assertEqual(motor.jugador.sala.id, 3)
        self.assertLess(motor.jugador.vida, vida)


# T051: Escenario US4-8.

def mapa_llave():
    # 1 -E-> 2 cerrada con llave. Desde 3, otra puerta cerrada (sin llave) da a 2: con la antorcha en 3,
    # 2 queda explorada sin entrar. La salida (9) no se alcanza.
    return [
        {"id": 1, "nombre": "A", "salidas": {"E": salida(2, cerrada=True, llave=LLAVE), "S": salida(3)}},
        {"id": 2, "nombre": "B", "salidas": {"O": salida(1)}},
        {"id": 3, "nombre": "C", "salidas": {"N": salida(1), "E": salida(2, cerrada=True)}},
        {"id": 9, "nombre": "Salida", "salidas": {}},
    ]


class TestNoAbrePuertas(BaseViaje):

    def test_fr023_fr029_escenario_us4_8_puerta_cerrada_con_llave_no_cuenta(self):
        motor = self.partida(mapa_llave(), [contenido_sala(1, objetos=[ANTORCHA, LLAVE])])
        self.acciones(motor, ("recoger", id_objeto(1, ANTORCHA, 0)), ("recoger", id_objeto(1, LLAVE, 1)),
                      ("usar", id_objeto(1, ANTORCHA, 0)), ("mover", "S"), ("mover", "N"))
        self.assertEqual(self.estados(motor)[0], [1, 2, 3])
        antes = self.sin_efectos(motor)

        self.assertEqual(self.avisos(self.ir(2)), [AVISO_SIN_RUTA])
        self.assertTrue(self.puerta(motor, 1, "E").cerrada)
        self.assertEqual(self.sin_efectos(motor), antes)


# T052: Escenario US4-9.

class TestEnemigosEnLaSalaDePartida(BaseViaje):

    def test_fr028_escenario_us4_9_se_acepta_con_enemigos_en_la_sala_actual(self):
        # La babosa está activa en 2, donde está el jugador. La parada por enemigos solo se evalúa al
        # entrar: el viaje sale de 2 y llega a 4 sin detenerse.
        contenido = [contenido_sala(2, enemigos=["e-babosa"], tipo_enemigo=ENEMIGO_LENTO)]
        motor = self.partida(mapa_pasillo(), contenido)
        self.acciones(motor, ("mover", "E"), ("mover", "E"), ("mover", "E"), ("mover", "O"), ("mover", "O"))
        self.assertTrue(motor.enemigos[0].activo)
        self.assertEqual(motor.jugador.sala.id, 2)

        self.assertEqual(self.avisos(self.ir(4)), ["Llegaste a la sala 4."])
        self.assertEqual(self.movimientos()[-2:], ["mover E", "mover E"])


# T053: casos borde.

def mapa_salida():
    # Con la antorcha en 2 se explora 3, que es la salida, sin entrar.
    return [
        {"id": 1, "nombre": "A", "salidas": {"E": salida(2)}},
        {"id": 2, "nombre": "B", "salidas": {"O": salida(1), "E": salida(3)}},
        {"id": 3, "nombre": "Salida", "salidas": {"O": salida(2)}},
    ]


class TestCasosBorde(BaseViaje):

    def test_fr022_sala_actual(self):
        motor = self.partida(mapa_cuadro())
        antes = self.sin_efectos(motor)
        self.assertEqual(self.avisos(self.ir(1)), [AVISO_ACTUAL])
        self.assertEqual(self.sin_efectos(motor), antes)

    def test_fr022_explorada_sin_ruta(self):
        salas = [
            {"id": 1, "nombre": "A", "salidas": {"E": salida(2)}},
            {"id": 2, "nombre": "B", "salidas": {"O": salida(1, cerrada=True)}},
            {"id": 9, "nombre": "Salida", "salidas": {}},
        ]
        motor = self.partida(salas)
        self.acciones(motor, ("mover", "E"))
        antes = self.sin_efectos(motor)
        self.assertEqual(self.avisos(self.ir(1)), [AVISO_SIN_RUTA])
        self.assertEqual(self.sin_efectos(motor), antes)

    def test_fr021_ir_mal_formado_da_error_de_uso(self):
        motor = self.partida(mapa_cuadro())
        self.acciones(motor, ("mover", "E"))
        antes = self.sin_efectos(motor)
        for linea in ("ir", "ir a", "ir b 1", "ir 1"):
            lineas = self.ejecutar(self.controlador, linea)
            self.assertEqual(self.errores(lineas), [AVISO_USO], linea)
            self.assertEqual(self.avisos(lineas), [], linea)
            self.assertEqual(self.sin_efectos(motor), antes, linea)

    def test_fr021_el_comando_admite_mayusculas_y_espacios(self):
        motor = self.partida(mapa_cuadro())
        self.acciones(motor, ("mover", "E"))
        self.assertEqual(self.avisos(self.ejecutar(self.controlador, "  IR  A  1 ")), ["Llegaste a la sala 1."])

    def test_fr027e_victoria_en_un_paso(self):
        contenido = [contenido_sala(1, objetos=[ANTORCHA])]
        motor = self.partida(mapa_salida(), contenido)
        self.acciones(motor, ("recoger", id_objeto(1, ANTORCHA, 0)), ("usar", id_objeto(1, ANTORCHA, 0)),
                      ("mover", "E"), ("mover", "O"))

        lineas = self.ir(3)
        self.assertEqual(motor.estado_partida(), "victoria")
        self.assertEqual(self.avisos(lineas), [])  # el fin lo muestra el flujo normal (FR-027e)
        self.assertEqual(self.movimientos()[-2:], ["mover E", "mover E"])

    def test_fr027e_muerte_en_un_paso_gana_sobre_el_dano(self):
        motor = self.partida(mapa_cuadro())
        self.acciones(motor, *CUADRO)
        motor.aplicar_veneno(motor.jugador, 1000)

        lineas = self.ir(4)
        self.assertEqual(motor.estado_partida(), "derrota")
        self.assertEqual(self.avisos(lineas), [])
        self.assertEqual(self.movimientos()[-1], "mover E")

    def test_fr026_puerta_que_se_cierra_sola_con_el_jugador_en_ella(self):
        # 1 -E-> 2 se abre y se cierra sola mientras el jugador está en 1, en pleno viaje de 3 a 2.
        # El jugador lo ve (FR-006) y el recálculo rodea por 4.
        salas = mapa_cuadro(cerrada=True, cierre=450)
        motor = self.partida(salas)
        self.acciones(motor, ("abrir", "E"), ("mover", "E"), ("mover", "S"), ("mover", "O"))
        self.assertFalse(self.puerta(motor, 1, "E").cerrada)

        self.assertEqual(self.avisos(self.ir(2)), ["Llegaste a la sala 2."])
        self.assertIn("Una puerta se cerró sola.", motor.mensajes.ultimos())
        self.assertEqual(self.recuerdo(motor, 1, "E"), CERRADA)
        self.assertEqual(self.movimientos()[-4:], ["mover N", "mover S", "mover E", "mover N"])

    def test_pendiente_t062_sin_busqueda_real_avisa_sin_efectos(self):
        # T058: mientras Persona A no suba Modelo/BusquedaRuta.py, primer_paso lanza NotImplementedError
        # y el controlador da un aviso sin efectos. Se retira en T065.
        motor = self.partida(mapa_cuadro(), buscar=None)
        self.acciones(motor, *CUADRO)
        antes = self.sin_efectos(motor)
        self.assertEqual(self.avisos(self.ir(4)), [AVISO_NO_DISPONIBLE])
        self.assertEqual(self.sin_efectos(motor), antes)
        # Los rechazos que no necesitan la búsqueda siguen funcionando.
        self.assertEqual(self.avisos(self.ir(5)), [AVISO_DESCONOCIDA])
        self.assertEqual(self.avisos(self.ir(1)), [AVISO_ACTUAL])


# T054: equivalencia con `mover`.

class TestEquivalenciaConMover(BaseViaje):

    def test_fr021_fr025_mismo_estado_y_bitacora_que_los_mover_a_mano(self):
        # Con una babosa activa en 3, que actúa entre los pasos (FR-025).
        contenido = [contenido_sala(3, enemigos=["e-babosa"], tipo_enemigo=ENEMIGO_LENTO)]
        motor = self.partida(mapa_cuadro(), contenido)
        gemelo, controlador_gemelo = self.gemela(mapa_cuadro(), contenido)
        for accion in CUADRO:
            self.ejecutar(self.controlador, " ".join(accion))
            self.ejecutar(controlador_gemelo, " ".join(accion))

        self.assertEqual(self.avisos(self.ir(4)), ["Llegaste a la sala 4."])
        self.ejecutar(controlador_gemelo, "mover E")
        self.ejecutar(controlador_gemelo, "mover S")

        self.assertEqual(motor.obtener_estado_resumen(), gemelo.obtener_estado_resumen())
        self.assertEqual(motor.mensajes.ultimos(), gemelo.mensajes.ultimos())
        self.assertEqual(self.movimientos(), self.movimientos(os.path.dirname(controlador_gemelo.ruta_bitacora)))

    def test_fr026_recalcula_antes_de_cada_paso(self):
        origenes = []
        motor = self.partida(mapa_cuadro(), buscar=contador(buscador_prueba, origenes))
        self.acciones(motor, *CUADRO)
        self.ir(4)
        self.assertEqual(origenes, [1, 2])

    def test_fr027_prioridad_fin_dano_enemigos_destino(self):
        destino = object()
        jugador = SimpleNamespace(vida=10, sala=destino)
        motor = SimpleNamespace(jugador=jugador, enemigos_al_entrar=True, estado_partida=lambda: "derrota")

        def motivo(**cambios):
            for nombre, valor in cambios.items():
                setattr(jugador if nombre in ("vida", "sala") else motor, nombre, valor)
            viaje = Viaje(motor, destino, buscador_prueba, Paso("E", destino, 100))
            self.assertIsNotNone(viaje.siguiente_paso())
            jugador.vida -= 1  # pierde vida durante el paso
            return viaje.terminar_paso(True)

        self.assertEqual(motivo(), FIN_PARTIDA)
        motor.estado_partida = lambda: "en_curso"
        self.assertEqual(motivo(), DANO)

        viaje = Viaje(motor, destino, buscador_prueba, Paso("E", destino, 100))
        viaje.siguiente_paso()
        self.assertEqual(viaje.terminar_paso(True), ENEMIGOS)

        motor.enemigos_al_entrar = False
        viaje = Viaje(motor, destino, buscador_prueba, Paso("E", destino, 100))
        viaje.siguiente_paso()
        self.assertEqual(viaje.terminar_paso(True), DESTINO)

        jugador.sala = object()
        viaje = Viaje(motor, destino, buscador_prueba, Paso("E", destino, 100))
        viaje.siguiente_paso()
        self.assertIsNone(viaje.terminar_paso(True))  # sigue
        self.assertEqual(viaje.terminar_paso(False), PASO_RECHAZADO)

    def test_fr027d_sin_ruta_al_recalcular(self):
        motor = SimpleNamespace(jugador=SimpleNamespace(vida=10, sala=object()),
                                grafo_conocido=lambda: None)
        viaje = Viaje(motor, object(), lambda grafo, origen, destino: None, None)
        self.assertIsNone(viaje.siguiente_paso())
        self.assertEqual(viaje.motivo, SIN_RUTA)


# T060: FR-027f, paso rechazado por el motor.

class TestPasoRechazado(BaseViaje):

    def test_fr027f_paso_rechazado_detiene_con_el_mensaje_de_mover_sin_tiempo(self):
        # El buscador manda, desde 2, un paso hacia N, que no existe: el motor lo rechaza.
        motor = self.partida(mapa_cuadro(), buscar=guion((1, "E"), (2, "N")))
        gemelo, controlador_gemelo = self.gemela(mapa_cuadro())
        for accion in CUADRO:
            self.ejecutar(self.controlador, " ".join(accion))
            self.ejecutar(controlador_gemelo, " ".join(accion))
        self.ejecutar(controlador_gemelo, "mover E")
        rechazo = self.ejecutar(controlador_gemelo, "mover N")
        self.assertEqual(self.avisos(rechazo), [RECHAZO_MOVER])

        lineas = self.ir(4)
        self.assertEqual(lineas, rechazo)  # el mismo mensaje que daría `mover`, y nada más
        self.assertEqual(self.movimientos()[-1], "mover E")
        self.assertEqual(motor.obtener_estado_resumen(), gemelo.obtener_estado_resumen())
        self.assertEqual(motor.mensajes.ultimos(), gemelo.mensajes.ultimos())


if __name__ == "__main__":
    unittest.main()
