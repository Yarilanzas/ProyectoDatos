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


def _linea_tiempos(etiqueta, tiempos):
    return f"{etiqueta}   mediana = {mediana(tiempos):8.3f} ms   p95 = {p95(tiempos):8.3f} ms"


# M1 (SC-004): cripta del tamaño de la publicada más grande (parámetros, no datos de una cripta real)
LIMITE_M1_MS = 200
M1_SALAS, M1_LLAVES = 300, 4


def bench_m1(lineas):
    lineas.append(f"-M1: cripta sintética de {M1_SALAS} salas y {M1_LLAVES} llaves, p95 < {LIMITE_M1_MS} ms (SC-004)-")
    casos = [("resoluble", caso(M1_SALAS, M1_LLAVES)),
             ("no resoluble con ciclo", caso(M1_SALAS, M1_LLAVES, resoluble=False, con_ciclo=True))]
    for nombre, c in casos:
        tiempos = medir(c.verificar)
        cumple = "CUMPLE" if p95(tiempos) < LIMITE_M1_MS else "NO CUMPLE"
        etiqueta = f"{nombre:<23} S = {c.salas:4d}  E = {c.salidas:4d}  K = {c.llaves:2d}"
        lineas.append(f"{_linea_tiempos(etiqueta, tiempos)}   {cumple}")


# M2 y M3 (SC-005): duplicar a la vez salas, salidas (≈ 2,5 por sala, las da el generador) y llaves
LIMITE_COCIENTE = 2.5
DUPLICACIONES = [(300, 4), (600, 8), (1200, 16), (2400, 32), (4800, 64), (9600, 128)]
REPETICIONES_PEOR_CASO = 5


def _bench_duplicaciones(lineas, casos, limite=LIMITE_COCIENTE, repeticiones=REPETICIONES):
    medianas = []
    for c in casos:
        tiempos = medir(c.verificar, repeticiones=repeticiones)
        medianas.append(mediana(tiempos))
        etiqueta = f"S = {c.salas:5d}  E = {c.salidas:5d}  K = {c.llaves:3d}"
        lineas.append(_linea_tiempos(etiqueta, tiempos))
    for i in range(1, len(casos)):
        cociente = medianas[i] / medianas[i - 1]
        veredicto = ""
        if limite is not None:
            veredicto = "   CUMPLE" if cociente <= limite else "   NO CUMPLE"
        lineas.append(f"S {casos[i - 1].salas:5d} -> {casos[i].salas:5d}   cociente de medianas = {cociente:5.2f}"
                      f"{veredicto}")


def bench_m2(lineas):
    lineas.append(f"-M2: duplicaciones, caso resoluble, cociente de medianas <= {LIMITE_COCIENTE} (SC-005)-")
    _bench_duplicaciones(lineas, [caso(s, k) for s, k in DUPLICACIONES])


def bench_m3(lineas):
    lineas.append(f"-M3: duplicaciones, caso no resoluble con reporte, dependencias y ciclos, zonas disjuntas, "
                  f"cociente <= {LIMITE_COCIENTE} (SC-005)-")
    _bench_duplicaciones(lineas, [caso(s, k, resoluble=False, con_ciclo=True) for s, k in DUPLICACIONES])


class CasoPeorCaso(CasoBench):
    """Peor caso de las dependencias (P-11): zonas que se solapan.

    Parte de la cripta resoluble de 2 llaves y quita la ubicación de k1: la región R1 (≈ la mitad de las salas) queda
    fuera de lo alcanzable, con todas las puertas que entran desde R0 pidiendo k1, así que ninguna zona corta antes de
    tiempo por conflicto. Luego agrega `extras` llaves, cada una en una sala distinta de R1: cada sala calcula su zona,
    que es toda R1, y el costo crece como L·(S + E).
    """

    def __init__(self, salas, extras, semilla=SEMILLA):
        cripta = generar_cripta(semilla, salas, 2, id_cripta=f"peor-{salas}-{extras}")
        primera, ultima = cripta.regiones[1]
        llaves_json = []
        for ubicacion in cripta.llaves_json:
            if ubicacion["id"] != cripta.llaves[0]:
                llaves_json.append(ubicacion)
        paso = max(1, (ultima - primera + 1) // extras)
        for i in range(extras):
            llaves_json.append({"id": f"extra_{i + 1:04d}", "sala": primera + (i * paso) % (ultima - primera + 1)})
        cripta.llaves_json = llaves_json
        super().__init__(cripta)
        self.llaves = len(llaves_json)  # en este caso la columna K informa L, las ubicaciones de llaves


def bench_peor_caso(lineas):
    lineas.append("-Peor caso de dependencias (P-11, zonas que se solapan): informativo, sin límite (FR-029, SC-005)-")
    lineas.append(f"{REPETICIONES_PEOR_CASO} repeticiones por caso; K = L, ubicaciones de llaves, casi todas en salas "
                  f"distintas de una región no alcanzable")
    _bench_duplicaciones(lineas, [CasoPeorCaso(s, k) for s, k in DUPLICACIONES], limite=None,
                         repeticiones=REPETICIONES_PEOR_CASO)


# Mediciones M1 a M5 (T047 a T050), en el orden en que se escriben en el archivo.
SECCIONES = [bench_m1, bench_m2, bench_m3, bench_peor_caso]


if __name__ == "__main__":
    correr_bench()
