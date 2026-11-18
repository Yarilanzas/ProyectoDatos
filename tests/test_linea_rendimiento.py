# Rendimiento de las consultas de la línea de tiempo (spec 004, T090; Escenario US6-1; FR-020, SC-002).
# Comprobación de humo: una partida real de 5 000 acciones (semilla fija, K por defecto, sin red) y una muestra repartida
# en toda la partida de consultas `#k` y de consultas por instante. Todas deben responder en menos de 50 ms. La medición
# completa (varias K, la alternativa sin puntos de control, mediana y p95) es M1 de `tests/bench_linea.py` (T101).

import gc
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
REPETICIONES = 3       # repeticiones extra de una consulta que tardó LIMITE_MS o más


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

        # Se mide con el recolector de basura detenido (y vaciado antes): una pasada completa sobre el montón de las ~1 100
        # pruebas anteriores tarda más de 100 ms y no es el costo de la consulta (sí aparecería en M1 con la mediana y el p95).
        gc.collect()
        gc.disable()
        self.addCleanup(gc.enable)
        # Una pausa del sistema operativo (no el costo de la consulta) puede ensanchar una sola medida: M1 mide un máximo de
        # 15.6 ms con K = 50. Por eso, si una consulta tarda LIMITE_MS o más, se repite hasta REPETICIONES veces más y se toma
        # el MÍNIMO de las medidas: una consulta realmente lenta lo sería también al repetirse, y la prueba falla.
        def medir(consulta, *argumentos):
            desde = time.perf_counter_ns()
            consulta(*argumentos)
            mejor = milisegundos(desde)
            repeticiones = 0
            while mejor >= LIMITE_MS and repeticiones < REPETICIONES:
                desde = time.perf_counter_ns()
                consulta(*argumentos)
                mejor = min(mejor, milisegundos(desde))
                repeticiones += 1
            return mejor

        tiempos = []   # (ms, qué se pidió)
        for i in range(MUESTRA):
            numero = 1 + i * ACCIONES // MUESTRA        # repartidas desde la acción 1 hasta cerca de la última
            tiempos.append((medir(linea.consultar_accion, numero, motor), f"#{numero}"))
        for i in range(MUESTRA):
            t = i * (linea.reloj_actual - 1) // MUESTRA  # desde el instante 0 hasta cerca del final
            tiempos.append((medir(linea.consultar_instante, t, motor), f"t={t}"))

        lentas = [(ms, que) for ms, que in tiempos if ms >= LIMITE_MS]
        mayor = tiempos[0]
        for medida in tiempos:
            if medida[0] > mayor[0]:
                mayor = medida
        self.assertEqual(lentas, [], f"consultas de {LIMITE_MS} ms o más; la mayor: {mayor[0]:.1f} ms en {mayor[1]}")
        self.assertEqual(len(tiempos), 2 * MUESTRA)


if __name__ == "__main__":
    unittest.main()
