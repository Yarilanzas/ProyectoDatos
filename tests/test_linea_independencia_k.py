# K no cambia lo que se ve: solo el costo (spec 004, T094; Escenario US6-5, Quickstart 11; FR-028, SC-003).
# Los mismos 100 instantes de una misma partida, con K = 1, 50 y 500, dan resúmenes idénticos en contenido, y lo mismo por
# los dos caminos de consulta: el comando `historia <t>` de la partida y la reproducción de la bitácora con el observador
# (lo que hace `--replay --hasta`: `Reproductor` + `ObservadorLinea` + `consultar_instante`). Tres semillas. Sin red.
#
# La opción `--replay --hasta` del programa llega con T062 y T063b; aquí se prueba su mecanismo con las piezas que ya están
# (el `Reproductor` con observador y la línea), que es lo que `ConsultaHistoria` llamará.

import os
import sys
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Bitacora.BitacoraPartida import leer_bitacora
from Bitacora.Reproductor import Reproductor
from Controlador.ObservadorLinea import ObservadorLinea
from Gestor.PreparadorPartida import preparar_partida
from Modelo.LineaTiempo import LineaTiempo
from tests.test_linea_consulta import contenido
from tests.utiles_linea import GeneradorAcciones, partida_linea
from tests.utiles_niebla import CRIPTA_NIEBLA

SEMILLAS = (1, 2, 3)
KS = (1, 50, 500)
ACCIONES = 60
INSTANTES = 100


def instantes(reloj):
    """100 instantes repartidos de 0 a justo antes del reloj final (el final es el estado vivo, sin reconstruir)."""
    return [reloj * i // INSTANTES for i in range(INSTANTES)]


def jugar_con_el_controlador(test, semilla, k):
    """Partida nueva con la K dada, jugada por comandos con el generador de pruebas. Devuelve la `PartidaLinea`."""
    partida = partida_linea(semilla=semilla)
    test.addCleanup(partida.cerrar)
    controlador = partida.controlador
    controlador.k_linea = k
    controlador.nueva_partida(CRIPTA_NIEBLA, semilla)       # la misma partida, ahora con esa K y su bitácora
    generador = GeneradorAcciones(semilla)
    aceptadas = 0
    while aceptadas < ACCIONES:
        nombre, argumento = generador.siguiente(controlador.motor)
        antes = controlador.linea.acciones
        controlador.ejecutar(f"{nombre} {argumento}".strip())
        aceptadas += controlador.linea.acciones - antes
    test.assertEqual(controlador.linea.k, k)
    return partida


def por_historia(partida, tiempos):
    controlador, vista = partida.controlador, partida.vista
    resultado = []
    for t in tiempos:
        vista.lineas.clear()
        controlador.ejecutar(f"historia {t}")
        nombre, argumentos = vista.lineas[-1]
        if nombre != "mostrar_resumen_historico":
            raise AssertionError(f"historia {t} mostró {nombre}: {argumentos}")
        resultado.append(contenido(argumentos[0]))
    return resultado


def por_replay(partida, k, tiempos):
    """Lo que hace `--replay --hasta T`: reproduce la bitácora con una línea de esa K y consulta el instante."""
    partida.controlador.bitacora.cerrar()
    gestor = partida.nuevo_gestor()
    linea = LineaTiempo(k, partida.nuevo_gestor_historico())
    encabezado, acciones = leer_bitacora(partida.ruta_bitacora)
    reproductor = Reproductor(lambda cripta_id, semilla: preparar_partida(cripta_id, semilla, gestor),
                              gestor.version_cripta(CRIPTA_NIEBLA), gestor.version_catalogo(),
                              observador=ObservadorLinea(linea))
    motor = reproductor.reproducir_acciones(encabezado, acciones)
    return [contenido(linea.consultar_instante(t, motor)) for t in tiempos]


class PruebasIndependenciaDeK(unittest.TestCase):

    def test_fr028_sc003_los_mismos_100_instantes_con_k_1_50_y_500_por_historia_y_por_replay(self):
        for semilla in SEMILLAS:
            referencia = None
            tiempos = None
            for k in KS:
                with self.subTest(semilla=semilla, k=k):
                    partida = jugar_con_el_controlador(self, semilla, k)
                    reloj = partida.controlador.linea.reloj_actual
                    if tiempos is None:
                        tiempos = instantes(reloj)
                    self.assertEqual(reloj, partida.motor.reloj)
                    self.assertEqual(len(tiempos), INSTANTES)
                    historia = por_historia(partida, tiempos)
                    replay = por_replay(partida, k, tiempos)
                    self.assertEqual(historia, replay, "historia y --replay --hasta dan lo mismo")
                    if referencia is None:
                        referencia = historia
                    self.assertEqual(historia, referencia, f"K={k} cambió lo que se ve")

    def test_fr028_k_solo_cambia_la_cantidad_de_puntos(self):
        puntos = []
        for k in KS:
            partida = jugar_con_el_controlador(self, 1, k)
            puntos.append(partida.controlador.linea.cantidad_puntos)
        self.assertEqual(puntos[0], ACCIONES + 1)          # K = 1: un punto por acción y el inicial
        self.assertEqual(puntos[1], ACCIONES // 50 + 1)    # K = 50: el inicial y el de la acción 50
        self.assertEqual(puntos[2], 1)                     # K = 500 > 60 acciones: solo el inicial


if __name__ == "__main__":
    unittest.main()
