# Pruebas del núcleo de LineaTiempo (spec 004, T013; invariantes de data-model.md#invariantes).
# Atiende: FR-016, FR-017, FR-021, FR-018. Sin red.
#
# El «observador» de estas pruebas imita lo que hará el ObservadorLinea del controlador: registra solo las acciones que
# el motor aceptó, con el mismo texto que la bitácora.

import os
import sys
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Bitacora.BitacoraPartida import leer_bitacora
from Modelo.CopiaEstado import materializar
from Modelo.LineaTiempo import (ErrorReconstruccion, LineaTiempo, ReferenciaInvalida, TIPO_ACCION)
from tests.utiles_linea import GeneradorAcciones, partida_linea, preparar_motor_linea
from tests.utiles_terreno import armar_motor, cripta_terreno


def motor_sintetico(salas=20, semilla=1):
    motor = armar_motor(cripta_terreno(semilla, salas), sala_jugador=1, cazadores=[], semilla=semilla)
    return preparar_motor_linea(motor, espiar=False)


def aplicar(linea, motor, nombre, argumento=""):
    """Ejecuta la acción en el motor y, solo si la aceptó, la registra en la línea (como el observador)."""
    if not motor.ejecutar_accion(nombre, argumento):
        return False
    linea.registrar_accion(motor, nombre, argumento)
    return True


def jugar_con_linea(linea, motor, generador, cantidad):
    jugadas = []
    while len(jugadas) < cantidad and not motor.victoria and motor.jugador.esta_vivo():
        nombre, argumento = generador.siguiente(motor)
        if aplicar(linea, motor, nombre, argumento):
            jugadas.append((nombre, argumento))
    return jugadas


class PruebasInvariantesDeLaLinea(unittest.TestCase):

    def _linea_jugada(self, k, acciones, semilla=1):
        motor = motor_sintetico(semilla=semilla)
        linea = LineaTiempo(k=k)
        linea.iniciar(motor)
        jugadas = jugar_con_linea(linea, motor, GeneradorAcciones(semilla), acciones)
        return linea, motor, jugadas

    def test_fr016_arreglos_paralelos_del_mismo_largo(self):
        for k in (1, 7, 50):
            with self.subTest(k=k):
                linea, _motor, jugadas = self._linea_jugada(k, 60)
                n = len(jugadas)
                self.assertEqual(linea.acciones, n)
                self.assertEqual(len(linea.vig_guion), n)
                self.assertEqual(len(linea.vig_reloj), n)
                self.assertEqual(len(linea.vig_sec), n)
                for lista in (linea.guion_tipo, linea.guion_nombre, linea.guion_argumento, linea.guion_reloj,
                              linea.guion_secuencia):
                    self.assertEqual(len(lista), n)
                self.assertEqual(len(linea.pc_accion), len(linea.pc_reloj))
                self.assertEqual(len(linea.pc_accion), len(linea.pc_epoca))
                self.assertEqual(len(linea.pc_accion), len(linea.pc_punto))
                self.assertEqual(linea.cantidad_puntos, len(linea.pc_accion))

    def test_fr016_vig_reloj_crece_estrictamente(self):
        linea, _motor, _jugadas = self._linea_jugada(10, 80)
        for anterior, siguiente in zip(linea.vig_reloj, linea.vig_reloj[1:]):
            self.assertLess(anterior, siguiente)

    def test_fr017_pc_accion_acotado_no_decreciente_y_con_punto_inicial(self):
        linea, _motor, _jugadas = self._linea_jugada(10, 75)
        self.assertEqual(linea.pc_accion[0], 0, "falta el punto de la acción 0")
        for anterior, siguiente in zip(linea.pc_accion, linea.pc_accion[1:]):
            self.assertLessEqual(anterior, siguiente)
        for accion in linea.pc_accion:
            self.assertLessEqual(accion, linea.acciones)

    def test_fr018_con_n_multiplo_de_k_hay_punto_de_control(self):
        for k in (1, 5, 10):
            with self.subTest(k=k):
                motor = motor_sintetico(semilla=3)
                linea = LineaTiempo(k=k)
                linea.iniciar(motor)
                generador = GeneradorAcciones(3)
                for _ in range(30):
                    jugar_con_linea(linea, motor, generador, 1)
                    if linea.acciones % k == 0:
                        self.assertIn(linea.acciones, linea.pc_accion)
                # y no hay más que los de cada K, más el inicial (cota C <= ceil(n/K) + 1)
                self.assertEqual(linea.cantidad_puntos, linea.acciones // k + 1)
                self.assertLessEqual(linea.cantidad_puntos, -(-linea.acciones // k) + 1)

    def test_fr018_k_invalido_lanza_value_error(self):
        for k in (0, -1, 1.5, "5", None, True):
            with self.subTest(k=k):
                with self.assertRaises(ValueError):
                    LineaTiempo(k=k)
        self.assertEqual(LineaTiempo(k=1).k, 1)
        self.assertEqual(LineaTiempo().k, 50)

    def test_fr021_el_sello_sale_del_motor_y_no_de_evento_actual(self):
        motor = motor_sintetico(semilla=5)
        linea = LineaTiempo(k=50)
        linea.iniciar(motor)
        self.assertEqual(linea.sello_de(1), (motor.reloj, motor.secuencia))
        generador = GeneradorAcciones(5)
        esperados = []
        for _ in range(25):
            esperados.append((motor.reloj, motor.secuencia))   # la decisión previa a la acción
            motor.jugador.evento_actual = None                 # si la línea lo leyera de aquí, el sello saldría mal
            jugar_con_linea(linea, motor, generador, 1)
        self.assertEqual(linea.acciones, 25)
        for indice in range(25):
            self.assertEqual((linea.vig_reloj[indice], linea.vig_sec[indice]), esperados[indice])
            self.assertEqual(linea.sello_de(indice + 1), esperados[indice])
        # y el sello de la decisión actual es el del motor ya avanzado
        self.assertEqual(linea.sello_de(26), (motor.reloj, motor.secuencia))
        self.assertEqual(linea.reloj_actual, motor.reloj)

    def test_fr021_el_punto_de_control_es_la_decision_siguiente(self):
        linea, _motor, _jugadas = self._linea_jugada(5, 20)
        for indice in range(linea.cantidad_puntos):
            accion = linea.pc_accion[indice]
            self.assertEqual((linea.pc_punto[indice].reloj, linea.pc_punto[indice].secuencia),
                             linea.sello_de(accion + 1))
            self.assertEqual(linea.pc_reloj[indice], linea.pc_punto[indice].reloj)
            self.assertEqual(linea.pc_punto[indice].accion, accion)

    def test_fr021_rehacer_desde_un_punto_reproduce_los_sellos(self):
        """El mismo guion desde el mismo punto da los mismos sellos (comprobar_sello no lanza)."""
        linea, motor, _jugadas = self._linea_jugada(10, 45, semilla=2)
        indice = linea.cantidad_puntos - 1
        punto = linea.pc_punto[indice]
        clon = materializar(punto, motor.gestor_datos)
        desde = linea.pc_accion[indice]
        linea.comprobar_sello(clon, desde + 1)
        for k in range(desde + 1, linea.acciones + 1):
            posicion = linea.vig_guion[k - 1]
            self.assertTrue(clon.ejecutar_accion(linea.guion_nombre[posicion], linea.guion_argumento[posicion]))
            linea.comprobar_sello(clon, k + 1)

    def test_fr021_comprobar_sello_detecta_la_divergencia(self):
        linea, motor, _jugadas = self._linea_jugada(10, 12)
        clon = materializar(linea.pc_punto[0], motor.gestor_datos)
        with self.assertRaises(ErrorReconstruccion):
            linea.comprobar_sello(clon, 5)
        with self.assertRaises(ReferenciaInvalida):
            linea.comprobar_sello(clon, 0)
        with self.assertRaises(ReferenciaInvalida):
            linea.sello_de(linea.acciones + 2)

    def test_fr016_una_accion_rechazada_no_registra_nada(self):
        motor = motor_sintetico(semilla=6)
        linea = LineaTiempo(k=3)
        linea.iniciar(motor)
        self.assertTrue(aplicar(linea, motor, "esperar"))
        antes = (linea.acciones, len(linea.guion_tipo), linea.cantidad_puntos, linea.sello_de(2))
        self.assertFalse(aplicar(linea, motor, "mover", "X"))
        self.assertFalse(aplicar(linea, motor, "atacar", "no-existe"))
        self.assertEqual((linea.acciones, len(linea.guion_tipo), linea.cantidad_puntos, linea.sello_de(2)), antes)

    def test_fr016_registrar_sin_iniciar_lanza_runtime_error(self):
        with self.assertRaises(RuntimeError):
            LineaTiempo().registrar_accion(motor_sintetico(), "esperar", "")

    def test_fr016_iniciar_de_nuevo_descarta_lo_anterior(self):
        motor = motor_sintetico(semilla=7)
        linea = LineaTiempo(k=2)
        linea.iniciar(motor)
        jugar_con_linea(linea, motor, GeneradorAcciones(7), 6)
        linea.iniciar(motor)
        self.assertEqual((linea.acciones, linea.cantidad_puntos, len(linea.guion_tipo)), (0, 1, 0))


class PruebasGuionIgualQueLaBitacora(unittest.TestCase):

    def test_fr025_el_guion_guarda_las_acciones_con_el_mismo_texto_que_la_bitacora(self):
        """Partida por ControladorPartida.nueva_partida (cripta resoluble). Cada comando va a la bitácora y a la línea
        con el mismo (nombre, argumento); un comando rechazado no va a ninguna."""
        partida = partida_linea()
        self.addCleanup(partida.cerrar)
        controlador, motor = partida.controlador, partida.motor
        linea = LineaTiempo(k=4)
        linea.iniciar(motor)
        generador = GeneradorAcciones(13)

        aceptadas = 0
        while aceptadas < 30:
            nombre, argumento = generador.siguiente(motor)
            texto = nombre if argumento == "" else f"{nombre} {argumento}"
            antes = motor.acciones_jugador
            controlador.ejecutar(texto)
            if motor.acciones_jugador != antes:  # el motor aceptó: la acción cuenta
                linea.registrar_accion(motor, nombre, argumento)
                aceptadas += 1
        controlador.ejecutar("mover X")  # rechazado: ni bitácora ni línea
        controlador.bitacora.cerrar()

        _encabezado, acciones = leer_bitacora(partida.ruta_bitacora)
        guion = [(linea.guion_nombre[i], linea.guion_argumento[i]) for i in range(len(linea.guion_tipo))]
        self.assertEqual(guion, acciones)
        self.assertEqual(linea.guion_tipo, [TIPO_ACCION] * 30)
        self.assertEqual(linea.acciones, 30)


if __name__ == "__main__":
    unittest.main()
