# Pruebas del conocimiento del jugador (T013 a T019, Historia 1).
# FR-001 a FR-008, FR-012 a FR-014. Apéndice B: sala inicial en el instante 0, de avistada a
# explorada y puerta recordada abierta que está cerrada.

import os
import sys

# Permite ejecutar este archivo desde cualquier carpeta (PyCharm, unittest o pytest).
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import tempfile
import unittest
from types import SimpleNamespace

from API.Fuentes import FuenteDatosOffline
from Gestor.GestorDatos import GestorDatos
from Gestor.PreparadorPartida import cargar_partida
from Modelo.Conocimiento import ABIERTA, AVISTADA, CERRADA, Conocimiento, DESCONOCIDA, EXPLORADA
from Modelo.Inventario import Inventario
from Modelo.MotorSimulacion import MotorSimulacion
from Modelo.prueba_actores import GestorPrueba, JugadorPrueba, sala as sala_prueba
from Vista.VistaConsola import VistaConsola
from tests.utiles_niebla import CRIPTA_NIEBLA, PERGAMINO, contenido_sala, partida_niebla, salida

MENSAJE_CIERRE = "Una puerta se cerró sola."


def foto(conocimiento):
    # El conocimiento completo, para comparar antes y después con igualdad exacta (FR-014).
    return (list(conocimiento.estado_sala), list(conocimiento.recuerdo_puerta),
            [sala.id for sala in conocimiento.reveladas],
            [(vista._origen.id, vista.sala_destino) for vista in conocimiento.observadas])


def mapa(cerrada=False, cierre=None, llave=None):
    # 1 -E-> 2 es la puerta bajo prueba. 3 y 4 dan la vuelta, para alejarse de ella y llegar a 2
    # sin pasar por 1. La salida (6) queda lejos para que ningún recorrido termine la partida.
    return [
        {"id": 1, "nombre": "Entrada", "salidas": {
            "E": salida(2, cerrada=cerrada, cierre_automatico=cierre, llave=llave), "S": salida(3)}},
        {"id": 2, "nombre": "Pasillo", "salidas": {"O": salida(1), "S": salida(4)}},
        {"id": 3, "nombre": "Bodega", "salidas": {"N": salida(1), "E": salida(4)}},
        {"id": 4, "nombre": "Cruce", "salidas": {"O": salida(3), "N": salida(2), "S": salida(5)}},
        {"id": 5, "nombre": "Sótano", "salidas": {"N": salida(4), "E": salida(6)}},
        {"id": 6, "nombre": "Salida", "salidas": {"O": salida(5)}},
    ]


class BaseConocimiento(unittest.TestCase):

    def partida(self, salas, contenido=(), **opciones):
        carpeta = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(carpeta.cleanup)
        self.carpeta = carpeta.name
        motor, controlador = partida_niebla(carpeta.name, salas, contenido, **opciones)
        self.addCleanup(controlador._cerrar)
        self.controlador = controlador
        return motor

    def sala(self, motor, id_sala):
        return motor.buscar_sala(motor.salas, id_sala)

    def estados(self, motor):
        # Ids de las salas exploradas, avistadas y desconocidas, en ese orden.
        return tuple([s.id for s in motor.salas if motor.conocimiento.estado(s) == estado]
                     for estado in (EXPLORADA, AVISTADA, DESCONOCIDA))

    def puerta(self, motor, id_sala, direccion):
        return self.sala(motor, id_sala).salidas[direccion]

    def recuerdo(self, motor, id_sala, direccion):
        return motor.conocimiento.recuerdo(self.puerta(motor, id_sala, direccion))

    def acciones(self, motor, *acciones):
        for accion in acciones:
            self.assertTrue(motor.ejecutar_accion(*accion), accion)


class TestEstadosDeSala(BaseConocimiento):

    def test_fr001_fr002_fr004_sala_inicial_en_el_instante_0(self):
        # Escenario US1-1. Apéndice B: sala inicial en el instante 0.
        motor = self.partida(mapa())
        self.assertEqual(motor.reloj, 0)
        self.assertEqual(motor.acciones_jugador, 0)
        self.assertEqual(self.estados(motor), ([1], [2, 3], [4, 5, 6]))

    def test_fr001_lo_revelado_es_coherente_con_los_estados(self):
        motor = self.partida(mapa())
        self.acciones(motor, ("mover", "E"), ("mover", "S"))
        conocimiento = motor.conocimiento
        ids = [s.id for s in conocimiento.reveladas]
        for sala in motor.salas:
            esperadas = 0 if conocimiento.estado(sala) == DESCONOCIDA else 1
            self.assertEqual(ids.count(sala.id), esperadas, sala.id)

    def test_fr003_fr004_fr005_de_avistada_a_explorada(self):
        # Escenario US1-2. Apéndice B: de avistada a explorada.
        motor = self.partida(mapa())
        self.assertEqual(motor.conocimiento.estado(self.sala(motor, 2)), AVISTADA)
        self.acciones(motor, ("mover", "E"))
        self.assertEqual(self.estados(motor), ([1, 2], [3, 4], [5, 6]))

        pasillo = self.sala(motor, 2)
        self.assertEqual(pasillo.nombre, "Pasillo")
        for direccion, salida_pasillo in pasillo.salidas.items():
            self.assertEqual(motor.conocimiento.recuerdo(salida_pasillo), ABIERTA, direccion)
            self.assertEqual(motor.costo_salida(salida_pasillo), 100, direccion)

    def test_fr004_una_sala_explorada_no_vuelve_a_avistada(self):
        motor = self.partida(mapa())
        self.acciones(motor, ("mover", "E"), ("mover", "O"), ("mover", "S"))
        self.assertEqual(self.estados(motor), ([1, 2, 3], [4], [5, 6]))

    def test_fr001_ids_opacos_y_destino_inexistente(self):
        # H7: los ids son de texto y una salida puede apuntar a una sala que no está.
        s1, s2 = sala_prueba("s1"), sala_prueba("s2")
        s1.salidas["E"] = SimpleNamespace(sala_destino="s2", cerrada=False)
        s1.salidas["N"] = SimpleNamespace(sala_destino="fantasma", cerrada=True)
        destinos = lambda salida_doble: s2 if salida_doble.sala_destino == "s2" else None
        conocimiento = Conocimiento([s1, s2], destinos)
        conocimiento.entrar(s1, False, SimpleNamespace(registrar=lambda **_: None))
        self.assertEqual(conocimiento.estado(s1), EXPLORADA)
        self.assertEqual(conocimiento.estado(s2), AVISTADA)
        self.assertEqual(conocimiento.recuerdo(s1.salidas["N"]), CERRADA)


class TestMemoriaDePuertas(BaseConocimiento):

    def alejarse(self, motor):
        # La puerta 1 -E-> 2 se abre en el instante 0 y se cierra en 300, con el jugador en 4.
        self.acciones(motor, ("abrir", "E"), ("mover", "S"), ("mover", "E"), ("esperar", ""))
        self.assertEqual(motor.jugador.sala.id, 4)
        self.assertTrue(self.puerta(motor, 1, "E").cerrada)

    def test_fr007_fr012_cierre_no_observado_conserva_el_recuerdo(self):
        # Escenario US1-3. H6: tampoco aparece el mensaje de cierre.
        motor = self.partida(mapa(cerrada=True, cierre=300))
        self.alejarse(motor)
        self.assertEqual(self.recuerdo(motor, 1, "E"), ABIERTA)
        self.assertNotIn(MENSAJE_CIERRE, motor.mensajes.ultimos())

    def test_fr006_al_entrar_al_origen_el_recuerdo_queda_cerrado(self):
        # Escenario US1-4, entrando a A. Apéndice B: puerta recordada abierta que está cerrada.
        motor = self.partida(mapa(cerrada=True, cierre=300))
        self.alejarse(motor)
        self.acciones(motor, ("mover", "O"), ("mover", "N"))
        self.assertEqual(motor.jugador.sala.id, 1)
        self.assertEqual(self.recuerdo(motor, 1, "E"), CERRADA)

    def test_fr006_al_entrar_al_destino_el_recuerdo_queda_cerrado(self):
        # Escenario US1-4, entrando a B por otro lado: se observa la salida que entra (lectura P-05).
        motor = self.partida(mapa(cerrada=True, cierre=300))
        self.alejarse(motor)
        self.acciones(motor, ("mover", "N"))
        self.assertEqual(motor.jugador.sala.id, 2)
        self.assertEqual(self.recuerdo(motor, 1, "E"), CERRADA)
        self.assertEqual(self.recuerdo(motor, 2, "O"), ABIERTA)    # cada sentido tiene su recuerdo

    def test_fr008_abrir_se_refleja_de_inmediato(self):
        motor = self.partida(mapa(cerrada=True))
        self.assertEqual(self.recuerdo(motor, 1, "E"), CERRADA)
        self.acciones(motor, ("abrir", "E"))
        self.assertEqual(self.recuerdo(motor, 1, "E"), ABIERTA)

    def test_fr006_esperando_en_la_sala_se_observa_el_cierre(self):
        motor = self.partida(mapa(cerrada=True, cierre=120))
        self.acciones(motor, ("abrir", "E"), ("esperar", ""))
        self.assertEqual(self.recuerdo(motor, 1, "E"), CERRADA)
        self.assertIn(MENSAJE_CIERRE, motor.mensajes.ultimos())

    def test_fr006_desde_el_destino_tambien_se_observa_el_cierre(self):
        motor = self.partida(mapa(cerrada=True, cierre=120))
        self.acciones(motor, ("abrir", "E"), ("mover", "E"))
        self.assertEqual(motor.jugador.sala.id, 2)
        self.assertEqual(self.recuerdo(motor, 1, "E"), CERRADA)
        self.assertIn(MENSAJE_CIERRE, motor.mensajes.ultimos())


class TestSeparacionDelMapaReal(BaseConocimiento):

    def lineas_estado(self, motor):
        lineas = []
        VistaConsola(salida=lineas.append).mostrar_estado(motor)
        return [linea for linea in lineas if str(linea).startswith("Salidas:")]

    def test_fr013_la_precarga_no_cambia_el_conocimiento(self):
        motor = self.partida(mapa())
        antes = foto(motor.conocimiento)
        self.controlador.gestor.precargar(1)
        motor.cargar_contenido_salas(CRIPTA_NIEBLA, [s.id for s in motor.salas])
        self.assertEqual(foto(motor.conocimiento), antes)

    def test_fr012_la_linea_salidas_sale_del_recuerdo(self):
        motor = self.partida(mapa())
        self.assertEqual(motor.salidas_recordadas(self.sala(motor, 1)),
                         [("E", "abierta", None), ("S", "abierta", None)])

        # Un cambio que el jugador no observó: la pantalla sigue con lo que recuerda.
        self.puerta(motor, 1, "E").cerrada = True
        self.assertEqual(self.lineas_estado(motor), ["Salidas: E este (abierta) | S sur (abierta)"])

    def test_fr012_la_llave_de_una_salida_cerrada_sigue_visible(self):
        # R8: es comportamiento de la Parte I.
        motor = self.partida(mapa(cerrada=True, llave="itm_llave"))
        self.assertEqual(self.lineas_estado(motor),
                         ["Salidas: E este (cerrada, llave itm_llave) | S sur (abierta)"])


class TestRetrocesoYBordes(BaseConocimiento):

    def test_fr014_pergamino_revierte_un_mover_sin_antorcha(self):
        motor = self.partida(mapa(), [contenido_sala(1, objetos=[PERGAMINO])])
        self.acciones(motor, ("recoger", f"obj-{CRIPTA_NIEBLA}-1-{PERGAMINO}-0"))
        antes = foto(motor.conocimiento)
        self.acciones(motor, ("mover", "E"))
        self.assertNotEqual(foto(motor.conocimiento), antes)
        self.acciones(motor, ("retroceder", ""))
        self.assertEqual(motor.jugador.sala.id, 1)
        self.assertEqual(foto(motor.conocimiento), antes)

    def test_fr014_pergamino_revierte_el_cierre_observado(self):
        # El cierre cae dentro del intervalo del `esperar`, y el recuerdo se deshace con él (R2).
        motor = self.partida(mapa(cerrada=True, cierre=120), [contenido_sala(1, objetos=[PERGAMINO])])
        self.acciones(motor, ("recoger", f"obj-{CRIPTA_NIEBLA}-1-{PERGAMINO}-0"), ("abrir", "E"))
        antes = foto(motor.conocimiento)
        self.acciones(motor, ("esperar", ""))
        self.assertEqual(self.recuerdo(motor, 1, "E"), CERRADA)
        self.acciones(motor, ("retroceder", ""))
        self.assertEqual(foto(motor.conocimiento), antes)
        self.assertEqual(self.recuerdo(motor, 1, "E"), ABIERTA)

    def test_fr002_la_sala_inicial_no_se_puede_revertir(self):
        motor = self.partida(mapa())
        antes = foto(motor.conocimiento)
        self.assertFalse(motor.historial.puede_deshacer())

        self.acciones(motor, ("esperar", ""))
        motor.historial.deshacer_ultimo()
        self.assertEqual(foto(motor.conocimiento), antes)
        self.assertEqual(motor.conocimiento.estado(self.sala(motor, 1)), EXPLORADA)

    def test_fr014_una_entrada_sin_novedades_no_registra_cambios(self):
        motor = self.partida(mapa())
        self.acciones(motor, ("mover", "E"))
        descripciones = [c.description for c in motor.historial._intervalos[-1]]
        self.assertEqual(descripciones.count("conocimiento del jugador"), 1)    # un solo lote

        self.acciones(motor, ("mover", "O"))
        descripciones = [c.description for c in motor.historial._intervalos[-1]]
        self.assertNotIn("conocimiento del jugador", descripciones)

    def test_fr003_una_trampa_mortal_no_impide_explorar_la_sala(self):
        # mover_jugador retorna de inmediato si la trampa mata: el conocimiento va antes (T030).
        motor = self.partida(mapa(), [contenido_sala(2, trampas=["t-mortal"])],
                             jugador={"vida_max": 2, "ataque": 1, "defensa": 0, "velocidad": 100})
        self.acciones(motor, ("mover", "E"))
        self.assertEqual(motor.estado_partida(), "derrota")
        self.assertEqual(motor.conocimiento.estado(self.sala(motor, 2)), EXPLORADA)

    def test_fr014_varios_pergaminos_seguidos_restauran_cada_estado(self):
        # Hasta 5 intervalos: `pop` es correcto porque los lotes se deshacen en orden inverso.
        motor = self.partida(mapa())
        fotos = []
        for direccion in ("E", "S", "O", "N", "E"):
            fotos.append(foto(motor.conocimiento))
            self.acciones(motor, ("mover", direccion))

        while fotos:
            self.assertTrue(motor.historial.deshacer_ultimo())
            self.assertEqual(foto(motor.conocimiento), fotos.pop())

    def test_sc006_motor_sin_iniciar_partida_funciona_sin_conocimiento(self):
        # H7: las pruebas de la Parte I arman el motor a mano.
        s1, s2 = sala_prueba("s1"), sala_prueba("s2")
        puerta = SimpleNamespace(sala_destino="s2", cerrada=True, llave=None, cierre_automatico=60)
        s1.salidas["E"] = puerta
        motor = MotorSimulacion(semilla=1, gestor_datos=GestorPrueba())
        jugador = JugadorPrueba(s1)
        jugador.inventario = Inventario(cap_max=5)
        motor.jugador, motor.salas = jugador, [s1, s2]
        motor._salas_contenido_cargado = ["s1", "s2"]
        motor.activar_enemigos_de_sala = lambda _s: None
        jugador.evento_actual = motor.programar_evento(0, "ACCION_ACTOR", jugador)
        motor.avanzar_hasta_jugador()

        self.assertIsNone(motor.conocimiento)
        self.assertEqual(motor.salidas_recordadas(s1), [("E", "cerrada", None)])
        self.assertTrue(motor.abrir_salida("E"))
        self.assertTrue(motor.ejecutar_accion("esperar"))
        self.assertIn(MENSAJE_CIERRE, motor.mensajes.ultimos())    # sin conocimiento, como en la Parte I
        self.assertTrue(motor.ejecutar_accion("esperar"))


class TestDespuesDeCargar(BaseConocimiento):
    # Hasta T079 el conocimiento no se guarda, pero la sala donde retoma el jugador debe verse bien.

    def cargar(self, motor):
        ruta = os.path.join(self.carpeta, "prueba.cripta")
        self.assertTrue(self.controlador.guardar(ruta))
        gestor = GestorDatos(FuenteDatosOffline(os.path.join(self.carpeta, "paquete")),
                             ruta_base=os.path.join(self.carpeta, "cache_carga"), cache_size=25)
        cargado = cargar_partida(ruta, gestor)
        self.addCleanup(cargado.restaurador.cerrar)
        return cargado

    def test_fr006_la_sala_donde_se_retoma_queda_explorada_y_observada(self):
        motor = self.partida(mapa())
        self.acciones(motor, ("mover", "E"))
        cargado = self.cargar(motor)
        sala = cargado.jugador.sala
        self.assertEqual(sala.id, 2)
        self.assertEqual(cargado.conocimiento.estado(sala), EXPLORADA)
        self.assertEqual(cargado.salidas_recordadas(sala), [("O", "abierta", None), ("S", "abierta", None)])

    def test_fr006_una_puerta_abierta_antes_de_guardar_se_ve_abierta_al_cargar(self):
        # El esqueleto la trae cerrada; la sala se restaura después de crear el conocimiento.
        motor = self.partida(mapa(cerrada=True))
        self.acciones(motor, ("abrir", "E"))
        cargado = self.cargar(motor)
        self.assertEqual(cargado.salidas_recordadas(cargado.jugador.sala),
                         [("E", "abierta", None), ("S", "abierta", None)])
        self.assertFalse(cargado.historial.puede_deshacer())


if __name__ == "__main__":
    unittest.main()
