
"""Benchmark de reproducción de una partida desde su bitácora."""

import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path


# Permite importar los módulos del proyecto al ejecutar desde tests/.
CARPETA_PROYECTO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CARPETA_PROYECTO))

from Bitacora.BitacoraPartida import BitacoraPartida
from Bitacora.Reproductor import Reproductor


VERSION_CRIPTA = "1"
VERSION_CATALOGO = "1"
SEMILLA = 12345

TAMANOS = (100, 1000, 10000)
REPETICIONES = 7

ARCHIVO_RESULTADOS = (
    CARPETA_PROYECTO / "resultados_bench_reproduccion.txt"
)


class MotorFalso:
    """Motor sencillo que acepta acciones sin simular el juego"""

    def __init__(self, cripta_id, semilla):
        self.cripta_id = cripta_id
        self.semilla = semilla
        self.cantidad_acciones = 0

    def ejecutar_accion(self, nombre, argumento):
        self.cantidad_acciones += 1
        return True


def crear_bitacora(ruta, cantidad_acciones):
    """Crea una bitácora de prueba con la cantidad indicada"""

    with BitacoraPartida(
        ruta,
        "cripta-benchmark",
        VERSION_CRIPTA,
        VERSION_CATALOGO,
        SEMILLA,
    ) as bitacora:
        for numero in range(cantidad_acciones):
            bitacora.registrar("mover", str(numero % 4))


def percentil_95(valores):
    """Calcula el percentil 95 usando el método de rango más cercano"""

    ordenados = sorted(valores)
    posicion = int(0.95 * len(ordenados))
    posicion = min(posicion, len(ordenados) - 1)
    return ordenados[posicion]


def ejecutar_benchmark():
    """Mide la reproducción y guarda los resultados en un TXT"""

    reproductor = Reproductor(
        MotorFalso,
        VERSION_CRIPTA,
        VERSION_CATALOGO,
    )

    lineas = [
        "-Reproducción de una partida desde su bitácora-",
        f"Equipo: {platform.platform()}",
        f"Procesador: {platform.processor() or 'No disponible'}",
        f"Python: {sys.version.split()[0]}",
        f"Repeticiones por tamaño: {REPETICIONES}",
        "Motor falso: sin simulación real ni renderizado",
        "Se mide la lectura, validación y despacho de acciones.",
        "",
    ]

    with tempfile.TemporaryDirectory() as carpeta:
        for cantidad in TAMANOS:
            ruta = Path(carpeta) / f"bitacora_{cantidad}.txt"
            crear_bitacora(ruta, cantidad)

            tiempos = []

            for _ in range(REPETICIONES):
                inicio = time.perf_counter()
                motor = reproductor.reproducir(ruta)
                duracion = time.perf_counter() - inicio

                if motor.cantidad_acciones != cantidad:
                    raise AssertionError(
                        f"Se esperaban {cantidad} acciones, "
                        f"pero se reprodujeron "
                        f"{motor.cantidad_acciones}"
                    )

                tiempos.append(duracion)

            mediana = statistics.median(tiempos) * 1000
            p95 = percentil_95(tiempos) * 1000

            linea = (
                f"acciones = {cantidad:6d}   "
                f"mediana = {mediana:9.3f} ms   "
                f"p95 = {p95:9.3f} ms"
            )
            lineas.append(linea)

    contenido = "\n".join(lineas) + "\n"

    # Guarda el TXT en la raíz del proyecto
    ARCHIVO_RESULTADOS.write_text(contenido, encoding="utf-8")

    # Muestra los mismos resultados en la terminal
    print(contenido)
    print(f"Resultados guardados en: {ARCHIVO_RESULTADOS}")


if __name__ == "__main__":
    ejecutar_benchmark()
