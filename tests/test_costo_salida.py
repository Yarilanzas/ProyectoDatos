# Pruebas de motor.costo_salida (T118). FR-005: cada salida muestra su costo, 100 si no lo declara.
# FR-024 y PR-13: es el único acceso al costo. `mover` usa el costo de la salida: costo * 100 // velocidad.

import os
import sys

# Permite ejecutar este archivo desde cualquier carpeta (PyCharm, unittest o pytest).
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import unittest
from types import SimpleNamespace

from DTOS.Salida import Salida
from Modelo.MotorSimulacion import COSTO_MOVER, MotorSimulacion
from Modelo.prueba_actores import GestorPrueba, JugadorPrueba, sala


class TestCostoSalida(unittest.TestCase):
    def setUp(self):
        self.motor = MotorSimulacion(semilla=1)

    def test_fr005_costo_por_defecto_vale_100(self):
        self.assertEqual(COSTO_MOVER, 100)

    def test_fr005_devuelve_el_costo_propio_de_la_salida(self):
        salida = SimpleNamespace(costo=250)
        self.assertEqual(self.motor.costo_salida(salida), 250)

    def test_fr005_salida_sin_el_atributo_cuesta_100(self):
        salida = SimpleNamespace(sala_destino=2, cerrada=False)
        self.assertEqual(self.motor.costo_salida(salida), 100)

    def test_fr005_salida_con_costo_none_cuesta_100(self):
        self.assertEqual(self.motor.costo_salida(SimpleNamespace(costo=None)), 100)

    def test_fr005_salida_del_dto_actual_cuesta_100(self):
        # El DTO trae `costo` con 100 por defecto (COSTO_POR_DEFECTO, spec 003 T030): sin declararlo, cuesta 100.
        self.assertEqual(self.motor.costo_salida(Salida(2, False, None, None)), 100)

    def test_fr005_solo_lee_la_salida(self):
        salida = SimpleNamespace(sala_destino=2)
        self.motor.costo_salida(salida)
        self.assertEqual(vars(salida), {"sala_destino": 2})


class TestMoverUsaElCosto(unittest.TestCase):
    # FR-005: `mover` usa el costo de la salida que atraviesa (costo * 100 // velocidad); sin costo declarado, 100.

    def preparar(self, velocidad=100, costo=None):
        s1, s2 = sala("s1"), sala("s2")
        s1.salidas["E"] = SimpleNamespace(sala_destino="s2", cerrada=False, llave=None,
                                          cierre_automatico=None, costo=costo)
        motor = MotorSimulacion(semilla=1, gestor_datos=GestorPrueba())
        jugador = JugadorPrueba(s1, velocidad=velocidad)
        motor.jugador = jugador
        motor.salas = [s1, s2]
        motor._salas_contenido_cargado = ["s1", "s2"]
        motor.activar_enemigos_de_sala = lambda _s: None
        jugador.evento_actual = motor.programar_evento(0, "ACCION_ACTOR", jugador)
        motor.avanzar_hasta_jugador()   # consume el turno inicial, como al empezar la partida
        return motor

    def test_fr005_mover_sin_costo_declarado_cuesta_100(self):
        motor = self.preparar()
        self.assertTrue(motor.ejecutar_accion("mover", "E"))
        self.assertEqual(motor.jugador.sala.id, "s2")
        self.assertEqual(motor.reloj, 100)

    def test_fr005_mover_usa_el_costo_de_la_salida(self):
        motor = self.preparar(costo=250)
        self.assertEqual(motor.costo_salida(motor.jugador.sala.salidas["E"]), 250)
        self.assertTrue(motor.ejecutar_accion("mover", "E"))
        self.assertEqual(motor.reloj, 250)

    def test_fr005_mover_usa_el_costo_con_otra_velocidad(self):
        motor = self.preparar(velocidad=50, costo=250)
        self.assertTrue(motor.ejecutar_accion("mover", "E"))
        self.assertEqual(motor.reloj, 500)   # 250 * 100 // 50


# Lo que faltaba de T006, T007 y T009 (conciliación con la spec 003) y una prueba de «ir a» con costos que vienen
# de los datos (FR-024). Son pruebas de caracterización: el código ya lo escribió la spec 003 (T027 a T031), así que
# describen el comportamiento actual y pasaron desde el primer intento. Sin red: paquetes offline en carpetas
# temporales, con la caché en disco dentro de cada carpeta.

import json
import tempfile

from API.Fuentes import FuenteDatosOffline
from Controlador.ControladorPartida import ControladorPartida
from Gestor.GestorDatos import GestorDatos
from tests.test_integracion import VistaFalsa
from Vista.VistaConsola import VistaConsola
from tests.utiles_niebla import CRIPTA_NIEBLA, JUGADOR, PERGAMINO, contenido_sala, crear_paquete_niebla, salida

VELOCIDAD = 80   # distinta de 100, para que el intervalo dependa de la fórmula costo * 100 // velocidad
ID_PERGAMINO = f"obj-{CRIPTA_NIEBLA}-1-{PERGAMINO}-0"


def intervalo(costo, velocidad=VELOCIDAD):
    # Mismo cálculo que MotorSimulacion.calcu_inter.
    return max(1, costo * 100 // velocidad)


def mapa_costos(con_costos=True):
    # 1 -E-> 2 cuesta 250 en ambos sentidos; 1 -S-> 3 y 3 -E-> 4 no declaran costo (valen 100). La salida es 4.
    caro = 250 if con_costos else None
    return [
        {"id": 1, "nombre": "Entrada", "salidas": {"E": salida(2, costo=caro), "S": salida(3)}},
        {"id": 2, "nombre": "Cara", "salidas": {"O": salida(1, costo=caro)}},
        {"id": 3, "nombre": "Barata", "salidas": {"N": salida(1), "E": salida(4)}},
        {"id": 4, "nombre": "Salida", "salidas": {"O": salida(3)}},
    ]


def mapa_ruta():
    # De 1 a 4: directo por 1 -E-> 4 cuesta 500 (un salto); por 1 -S-> 2 -E-> 3 -N-> 4 cuesta 300 (tres saltos).
    # La salida (5) está detrás de 4 y el viaje nunca entra a ella.
    return [
        {"id": 1, "nombre": "A", "salidas": {"E": salida(4, costo=500), "S": salida(2, costo=100)}},
        {"id": 2, "nombre": "B", "salidas": {"N": salida(1, costo=100), "E": salida(3, costo=100)}},
        {"id": 3, "nombre": "C", "salidas": {"O": salida(2, costo=100), "N": salida(4, costo=100)}},
        {"id": 4, "nombre": "D", "salidas": {"O": salida(1, costo=500), "S": salida(3, costo=100),
                                             "E": salida(5, costo=100)}},
        {"id": 5, "nombre": "Salida", "salidas": {"O": salida(4, costo=100)}},
    ]


class FuenteSinEsqueleto(FuenteDatosOffline):
    # Falla si se le pide el esqueleto: prueba que la segunda partida lo lee de la caché en disco.
    def obtener_esqueleto_cripta(self, id_cripta):
        raise AssertionError("el esqueleto debía salir de la caché en disco")


class BasePaquete(unittest.TestCase):

    def carpeta(self):
        carpeta = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(carpeta.cleanup)
        return carpeta.name

    def partida(self, carpeta, fuente, nombre_log="partida.log"):
        gestor = GestorDatos(fuente, ruta_base=os.path.join(carpeta, "cache"), cache_size=25)
        controlador = ControladorPartida(gestor, VistaFalsa(), os.path.join(carpeta, nombre_log))
        self.addCleanup(controlador._cerrar)
        controlador.nueva_partida(CRIPTA_NIEBLA, 7)
        return controlador.motor, controlador

    def paquete(self, carpeta, salas, contenido=(), velocidad=VELOCIDAD):
        ruta = os.path.join(carpeta, "paquete")
        crear_paquete_niebla(ruta, salas, contenido, jugador=dict(JUGADOR, velocidad=velocidad))
        return ruta


class TestSalidaSerializacion(unittest.TestCase):
    # T006, lo que faltaba (T030 de la 003 ya cubre 0, -5, 2.5, "100" y True, y que sin la clave vale 100).

    def test_fr005_costo_null_se_rechaza(self):
        with self.assertRaises(ValueError):
            Salida.desde_json({"sala": 2, "cerrada": False, "costo": None})

    def test_fr005_ida_y_vuelta_por_a_json_conserva_el_costo(self):
        for costo in (1, 100, 250):
            with self.subTest(costo=costo):
                original = Salida(2, False, None, None, costo=costo)
                copia = Salida.desde_json(original.a_json())
                self.assertEqual(copia.costo, costo)
                self.assertEqual(copia.sala_destino, 2)


class TestCostoDesdeElPaquete(BasePaquete):
    # T009: el costo llega desde FuenteDatosOffline, sobrevive la caché en disco y `mover` lo cobra.

    def test_fr005_el_costo_llega_del_paquete_pasa_por_la_cache_y_mover_lo_cobra(self):
        carpeta = self.carpeta()
        paquete = self.paquete(carpeta, mapa_costos())
        self.partida(carpeta, FuenteDatosOffline(paquete), "primera.log")   # lee la fuente y llena la caché

        with open(os.path.join(carpeta, "cache", f"esqueleto_{CRIPTA_NIEBLA}.json"), encoding="utf-8") as archivo:
            guardado = json.load(archivo)["esqueleto"]
        sala_1 = [sala for sala in guardado if sala["id"] == 1][0]
        self.assertEqual(sala_1["salidas"]["E"]["costo"], 250)
        # Sin costo declarado, la caché guarda 100: `a_json` escribe el costo siempre (diseño de la spec 003).
        self.assertEqual(sala_1["salidas"]["S"]["costo"], 100)

        motor, _ = self.partida(carpeta, FuenteSinEsqueleto(paquete), "segunda.log")   # esqueleto desde la caché
        self.assertEqual(motor.costo_salida(motor.jugador.sala.salidas["E"]), 250)
        self.assertTrue(motor.ejecutar_accion("mover", "E"))
        self.assertEqual(motor.reloj, intervalo(250))
        self.assertTrue(motor.ejecutar_accion("mover", "O"))
        self.assertEqual(motor.reloj, 2 * intervalo(250))
        antes = motor.reloj
        self.assertTrue(motor.ejecutar_accion("mover", "S"))       # sin costo declarado: 100
        self.assertEqual(motor.reloj - antes, intervalo(100))

    def test_fr005_el_mapa_muestra_el_costo_que_viene_del_paquete(self):
        # FR-005 por el comando real: el controlador le pasa a la vista el MapaConocido de `mapa`, y la vista de
        # consola le da formato. 1 -E-> 2 declara 250 en el paquete; 1 -S-> 3 no declara costo y vale 100.
        carpeta = self.carpeta()
        _, controlador = self.partida(carpeta, FuenteDatosOffline(self.paquete(carpeta, mapa_costos())))
        controlador.vista.lineas.clear()
        self.assertTrue(controlador.ejecutar("mapa"))
        llamadas = [args for nombre, args in controlador.vista.lineas if nombre == "mostrar_mapa"]
        self.assertEqual(len(llamadas), 1, controlador.vista.lineas)

        lineas = []
        VistaConsola(salida=lineas.append).mostrar_mapa(llamadas[0][0])
        self.assertEqual(lineas[:4], [
            "Mapa conocido:",
            "  Sala 1: Entrada",
            "    E -> sala 2   costo 250   abierta",
            "    S -> sala 3   costo 100   abierta",
        ])

    def test_fr005_un_paquete_sin_costos_da_el_mismo_reloj_que_la_parte_i(self):
        # Antes de la capacidad de terreno, `mover` costaba siempre 100: intervalo(100) por paso.
        carpeta = self.carpeta()
        motor, _ = self.partida(carpeta, FuenteDatosOffline(self.paquete(carpeta, mapa_costos(con_costos=False))))
        for numero, direccion in enumerate(("E", "O", "S", "N"), start=1):
            self.assertTrue(motor.ejecutar_accion("mover", direccion))
            self.assertEqual(motor.reloj, numero * intervalo(100))


class TestRetrocederTrasMoverConCosto(BasePaquete):
    # T007, lo que faltaba: `retroceder` deshace un `mover` cuyo costo no es 100.

    def test_fr005_retroceder_deshace_un_mover_de_costo_250(self):
        carpeta = self.carpeta()
        motor, _ = self.partida(carpeta, FuenteDatosOffline(
            self.paquete(carpeta, mapa_costos(), [contenido_sala(1, objetos=[PERGAMINO])])))
        self.assertTrue(motor.ejecutar_accion("recoger", ID_PERGAMINO))
        antes = (motor.reloj, motor.jugador.sala.id, motor.acciones_jugador)

        self.assertTrue(motor.ejecutar_accion("mover", "E"))
        self.assertEqual(motor.jugador.sala.id, 2)
        self.assertEqual(motor.reloj, antes[0] + intervalo(250))

        self.assertTrue(motor.ejecutar_accion("retroceder", ""))
        self.assertEqual((motor.reloj, motor.jugador.sala.id, motor.acciones_jugador), antes)


class TestIrAConCostosDelPaquete(BasePaquete):
    # FR-024 con costos que vienen de los datos y la búsqueda real (sin buscador inyectado).

    def test_fr024_ir_a_elige_la_ruta_de_menor_suma_aunque_tenga_mas_saltos(self):
        carpeta = self.carpeta()
        motor, controlador = self.partida(carpeta, FuenteDatosOffline(
            self.paquete(carpeta, mapa_ruta(), velocidad=100)))
        for direccion in ("S", "E", "N", "O"):   # explora 2, 3 y 4 y vuelve a 1 por la salida cara
            self.assertTrue(motor.ejecutar_accion("mover", direccion))
        self.assertEqual(motor.jugador.sala.id, 1)
        antes = motor.reloj

        controlador.vista.lineas.clear()
        self.assertTrue(controlador.ejecutar("ir a 4"))
        avisos = [args[0] for nombre, args in controlador.vista.lineas if nombre == "mostrar_aviso"]
        self.assertEqual(avisos, ["Llegaste a la sala 4."])
        self.assertEqual(motor.jugador.sala.id, 4)
        self.assertEqual(motor.reloj - antes, 300)   # 100 + 100 + 100, no los 500 del salto directo

        with open(os.path.join(carpeta, "partida.log"), encoding="utf-8") as archivo:
            lineas = archivo.read().splitlines()
        self.assertEqual(lineas[-4:], ["# ir a 4", "mover S", "mover E", "mover N"])


if __name__ == "__main__":
    unittest.main()
