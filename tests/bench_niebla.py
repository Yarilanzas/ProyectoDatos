# Mediciones de la capacidad de niebla de guerra, mapa conocido e «ir a» (Fase 6, M1 a M6; research R9).
# Base de la medición (T100): mediana de varias repeticiones y escritura de resultados_bench_niebla.txt con equipo y
# versión de Python, igual que tests/bench_ciclo.py. M1 a M6 (T101 a T106) se agregan aquí; `--bench` la llama (T107).
# Sin red y sin vista. Los mapas son sintéticos (tests/mapas_sinteticos.py), sin datos de ninguna cripta real.
# Atiende: PR-15, SC-006, Principio VIII.
#
# Principio I: la mediana usa el ordenamiento propio del repositorio (Modelo/ordenamiento.py), ni el ordenamiento
# ni las estadísticas de la biblioteca estándar.

import os
import platform
import sys
import time

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Modelo.ordenamiento import merge_sort

# Límite del cálculo de un paso de «ir a», en ms, con el mapa conocido completo de la cripta de referencia
# (enunciado §6.1; plan.md, P-08). El valor puede cambiar por enmienda: este es el único lugar que lo escribe,
# y M4 (T104) compara contra esta constante.
LIMITE_PASO_IR_A_MS = 5

REPETICIONES = 7
ARCHIVO_RESULTADOS = "resultados_bench_niebla.txt"


def _identidad(valor):
    return valor


def mediana(valores):
    """Mediana de ``valores``; con cantidad par, el promedio de los dos centrales. No cambia la entrada.
    O(r log r) con r = len(valores), por merge_sort."""
    if len(valores) == 0:
        raise ValueError("mediana de una lista vacía")
    ordenados, _ = merge_sort(valores, _identidad)
    centro = len(ordenados) // 2
    if len(ordenados) % 2 == 1:
        return ordenados[centro]
    return (ordenados[centro - 1] + ordenados[centro]) / 2


def medir_ms(funcion, repeticiones=REPETICIONES, reloj=time.perf_counter_ns):
    """Llama ``funcion`` ``repeticiones`` veces y devuelve la mediana de los tiempos, en ms.
    ``reloj`` devuelve nanosegundos; se puede cambiar en las pruebas."""
    if repeticiones < 1:
        raise ValueError("repeticiones debe ser >= 1")
    tiempos = []
    for _ in range(repeticiones):
        inicio = reloj()
        funcion()
        tiempos.append((reloj() - inicio) / 1_000_000)
    return mediana(tiempos)


def encabezado():
    return [
        "-Niebla de guerra, mapa conocido e «ir a» (Fase 6, M1 a M6)-",
        f"equipo: {platform.platform()} | {platform.processor() or platform.machine()}"
        f" | Python {platform.python_version()}",
        f"cada dato es la mediana de {REPETICIONES} repeticiones, sin red ni vista, con mapas sintéticos",
        f"resultado provisional: el límite de {LIMITE_PASO_IR_A_MS} ms de §6.1 se define para la cripta de "
        "referencia, que aún no está publicada",
    ]


def escribir_resultados(lineas, ruta=ARCHIVO_RESULTADOS):
    """Escribe el encabezado y ``lineas`` en ``ruta`` y los muestra en consola."""
    todas = encabezado() + list(lineas)
    for linea in todas:
        print(linea)
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(todas) + "\n")


def correr_bench(ruta=ARCHIVO_RESULTADOS):
    # M1 a M6 se agregan con T101 a T106.
    escribir_resultados(["M1 a M6: pendientes (T101 a T106)"], ruta)


if __name__ == "__main__":
    correr_bench()
