# Pruebas del ObservadorLinea (spec 004, T034; FR-025, FR-016, PR-12). Sin red.
# La línea es un doble que anota las llamadas: `registrar_retroceso` y `registrar_carga` de la real son de T047 y T082.

import os
import sys
import tempfile
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Controlador.ObservadorLinea import ObservadorLinea
from Modelo.LineaTiempo import LineaTiempo
from tests.utiles_linea import GeneradorAcciones, partida_linea, preparar_motor_linea


class LineaDoble:
    def __init__(self):
        self.llamadas = []

    def iniciar(self, motor):
        self.llamadas.append(("iniciar", motor))

    def registrar_accion(self, motor, nombre, argumento):
        self.llamadas.append(("accion", motor, nombre, argumento))

    def registrar_retroceso(self, motor):
        self.llamadas.append(("retroceso", motor))

    def registrar_carga(self, motor, ruta):
        self.llamadas.append(("carga", motor, ruta))


class RestauradorFalso:
    def __init__(self, ruta):
        self.ruta = ruta


class MotorFalso:
    def __init__(self, ruta=None):
        self.restaurador = None if ruta is None else RestauradorFalso(ruta)


class PruebasObservadorLinea(unittest.TestCase):

    def test_fr025_traduce_los_tres_avisos(self):
        linea = LineaDoble()
        observador = ObservadorLinea(linea)
        motor = MotorFalso()
        observador.al_crear_motor(motor)
        observador.despues_de_accion(motor, "mover", "N")
        observador.despues_de_accion(motor, "esperar", "")
        observador.despues_de_accion(motor, "retroceder", "")
        observador.despues_de_carga(motor)
        self.assertEqual(linea.llamadas, [("iniciar", motor), ("accion", motor, "mover", "N"),
                                          ("accion", motor, "esperar", ""), ("retroceso", motor),
                                          ("carga", motor, None)])

    def test_fr025_no_guarda_referencias_al_motor_anterior(self):
        observador = ObservadorLinea(LineaDoble())
        anterior, nuevo = MotorFalso(), MotorFalso()
        observador.al_crear_motor(anterior)
        observador.despues_de_carga(nuevo)
        for valor in vars(observador).values():
            self.assertIsNot(valor, anterior)
            self.assertIsNot(valor, nuevo)

    def test_fr025_despues_de_carga_hace_una_copia_privada_del_archivo_cargado(self):
        with tempfile.TemporaryDirectory() as base:
            original = os.path.join(base, "partida.cripta")
            with open(original, "wb") as archivo:
                archivo.write(b"CRPT contenido")
            copias = os.path.join(base, "copias")
            os.makedirs(copias)
            linea = LineaDoble()
            observador = ObservadorLinea(linea, copias)
            observador.despues_de_carga(MotorFalso(original))
            ruta = linea.llamadas[0][2]
            self.assertNotEqual(ruta, original)
            self.assertEqual(os.path.dirname(ruta), copias)
            # un guardado posterior sobrescribe el original, la copia conserva lo que decía al cargar
            with open(original, "wb") as archivo:
                archivo.write(b"otro")
            with open(ruta, "rb") as archivo:
                self.assertEqual(archivo.read(), b"CRPT contenido")
            observador.despues_de_carga(MotorFalso(original))
            self.assertNotEqual(linea.llamadas[1][2], ruta)
            observador.cerrar()
            self.assertFalse(os.path.exists(ruta))
            self.assertTrue(os.path.exists(original))

    def test_fr025_sin_restaurador_o_sin_carpeta_la_epoca_se_abre_sin_copia(self):
        linea = LineaDoble()
        ObservadorLinea(linea, tempfile.gettempdir()).despues_de_carga(MotorFalso())
        ObservadorLinea(linea).despues_de_carga(MotorFalso("no-importa.cripta"))
        self.assertEqual([llamada[2] for llamada in linea.llamadas], [None, None])

    def test_fr016_con_la_linea_real_registra_lo_mismo_que_la_llamada_directa(self):
        """Por el observador o llamando a la línea directamente, el guion y los sellos son idénticos (una sola vía)."""
        resultados = []
        for por_observador in (True, False):
            partida = partida_linea(semilla=12)
            self.addCleanup(partida.cerrar)
            motor = preparar_motor_linea(partida.motor, espiar=False)
            linea = LineaTiempo(k=3)
            observador = ObservadorLinea(linea)
            if por_observador:
                observador.al_crear_motor(motor)
            else:
                linea.iniciar(motor)
            generador = GeneradorAcciones(12)
            for _ in range(10):
                nombre, argumento = generador.siguiente(motor)
                if motor.ejecutar_accion(nombre, argumento):
                    if por_observador:
                        observador.despues_de_accion(motor, nombre, argumento)
                    else:
                        linea.registrar_accion(motor, nombre, argumento)
            resultados.append((linea.guion_nombre, linea.guion_argumento, linea.vig_reloj, linea.vig_sec,
                               linea.pc_accion))
        self.assertEqual(resultados[0], resultados[1])


if __name__ == "__main__":
    unittest.main()
