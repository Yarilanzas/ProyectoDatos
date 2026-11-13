"""Bench de la verificación de resolubilidad (spec 002, FR-029, FR-030, SC-004, SC-005).

Mide solo `Resolubilidad.verificar(...)` con los datos ya en memoria: el esqueleto y las ubicaciones se arman antes
de medir, así que no entra la obtención de datos (SC-004). Las criptas salen de `tests/generador_criptas.py` con
semillas fijas (Principio IV: ningún dato de cripta real; 300/760/4 son parámetros). No instancia la vista.

Escribe `resultados_bench_resolubilidad.txt` con el mismo formato que los demás bench (equipo, versión de Python,
mediana y p95). Toda cifra del Documento de Decisiones sobre resolubilidad sale de ese archivo (Principio VIII).

Principio I: los tiempos se ordenan con `merge_sort` de `Modelo/ordenamiento.py` (sin `sorted` ni `.sort`).
"""

import os
import platform
import sys
import time

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Modelo import Resolubilidad
from Modelo.ordenamiento import merge_sort
from tests.generador_criptas import generar_cripta

ARCHIVO_RESULTADOS = "resultados_bench_resolubilidad.txt"
SEMILLA = 2026            # semilla base de las criptas sintéticas
CALENTAMIENTO = 3         # ejecuciones descartadas antes de medir
REPETICIONES = 30         # ejecuciones medidas por caso


def _identidad(valor):
    return valor


class CasoBench:
    """Argumentos de `verificar` ya en memoria (DTOs armados una vez, fuera de la medición)."""

    def __init__(self, cripta):
        detalles = cripta.detalles
        self.cripta = cripta
        self.args = (cripta.id_cripta, detalles.sala_inicial, detalles.sala_salida, detalles.llave_salida,
                     cripta.esqueleto(), cripta.ubicaciones())
        self.salas = len(cripta.salas_json)
        self.salidas = 0
        for sala in cripta.salas_json:
            self.salidas += len(sala["salidas"])
        self.llaves = len(cripta.llaves)

    def verificar(self):
        return Resolubilidad.verificar(*self.args)


def caso(salas, llaves, resoluble=True, con_ciclo=False, semilla=SEMILLA):
    return CasoBench(generar_cripta(semilla, salas, llaves, resoluble=resoluble, con_ciclo=con_ciclo,
                                    id_cripta=f"bench-{salas}-{llaves}"))


def medir(funcion, repeticiones=REPETICIONES, calentamiento=CALENTAMIENTO):
    """Tiempos en ms de `funcion`, ordenados de menor a mayor, tras `calentamiento` ejecuciones descartadas."""
    for _ in range(calentamiento):
        funcion()
    tiempos = []
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        funcion()
        tiempos.append((time.perf_counter() - inicio) * 1000)
    ordenados, _ = merge_sort(tiempos, _identidad)
    return ordenados


def mediana(ordenados):
    n = len(ordenados)
    if n % 2 == 1:
        return ordenados[n // 2]
    return (ordenados[n // 2 - 1] + ordenados[n // 2]) / 2


def p95(ordenados):
    # rango más cercano: el menor valor que deja al menos el 95 % de las muestras por debajo o igual
    rango = (95 * len(ordenados) + 99) // 100
    return ordenados[max(rango, 1) - 1]


def encabezado():
    return [
        "-Verificación de resolubilidad (spec 002, FR-029, FR-030)-",
        f"equipo: {platform.platform()} | {platform.processor() or platform.machine()} | "
        f"Python {platform.python_version()}",
        f"solo Resolubilidad.verificar con los datos en memoria; {CALENTAMIENTO} de calentamiento y "
        f"{REPETICIONES} repeticiones por caso; semilla {SEMILLA}",
    ]


def correr_bench():
    lineas = encabezado()
    for seccion in SECCIONES:
        lineas.append("")
        seccion(lineas)

    for linea in lineas:
        print(linea)
    with open(ARCHIVO_RESULTADOS, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(lineas) + "\n")
    print(f"Resultados guardados en: {ARCHIVO_RESULTADOS}")


# Mediciones M1 a M5 (T047 a T050), en el orden en que se escriben en el archivo.
SECCIONES = []


if __name__ == "__main__":
    correr_bench()
