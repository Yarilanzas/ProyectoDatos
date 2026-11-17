# Rendimiento de las consultas de la línea de tiempo (spec 004, T090; Escenario US6-1; FR-020, SC-002).
# Comprobación de humo: una partida real de 5 000 acciones (semilla fija, K por defecto, sin red) y una muestra repartida
# en toda la partida de consultas `#k` y de consultas por instante. Todas deben responder en menos de 50 ms. La medición
# completa (varias K, la alternativa sin puntos de control, mediana y p95) es M1 de `tests/bench_linea.py` (T101).

import os
import sys
import time
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Modelo.LineaTiempo import K_POR_OMISION
from tests.utiles_linea import SesionLinea

ACCIONES = 5000
SEMILLA = 11
MUESTRA = 100          # de cada tipo (#k y t)
LIMITE_MS = 50


def milisegundos(desde):
    return (time.perf_counter_ns() - desde) / 1_000_000


class PruebasRendimiento(unittest.TestCase):

    def test_fr020_sc002_todas_las_consultas_de_la_muestra_responden_en_menos_de_50_ms(self):
        sesion = SesionLinea(k=K_POR_OMISION, semilla=SEMILLA, huellas=False)
        self.addCleanup(sesion.cerrar)
        sesion.jugar(ACCIONES)
        linea, motor = sesion.linea, sesion.motor
        self.assertEqual(linea.acciones, ACCIONES)
        self.assertEqual(linea.k, 50)

        tiempos = []   # (ms, qué se pidió)
        for i in range(MUESTRA):
            numero = 1 + i * ACCIONES // MUESTRA        # repartidas desde la acción 1 hasta cerca de la última
            desde = time.perf_counter_ns()
            linea.consultar_accion(numero, motor)
            tiempos.append((milisegundos(desde), f"#{numero}"))
        for i in range(MUESTRA):
            t = i * (linea.reloj_actual - 1) // MUESTRA  # desde el instante 0 hasta cerca del final
            desde = time.perf_counter_ns()
            linea.consultar_instante(t, motor)
            tiempos.append((milisegundos(desde), f"t={t}"))

        lentas = [(ms, que) for ms, que in tiempos if ms >= LIMITE_MS]
        mayor = tiempos[0]
        for medida in tiempos:
            if medida[0] > mayor[0]:
                mayor = medida
        self.assertEqual(lentas, [], f"consultas de {LIMITE_MS} ms o más; la mayor: {mayor[0]:.1f} ms en {mayor[1]}")
        self.assertEqual(len(tiempos), 2 * MUESTRA)


if __name__ == "__main__":
    unittest.main()
