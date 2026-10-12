import os
import tempfile
import time

from Persistencia.ArchivoPartida import guardar_partida, LectorPartida
from Persistencia.ExportadorJSON import guardar_partida_json, cargar_partida_json, leer_sala_json
from Persistencia.RegistroSala import RegistroSala

REPETICIONES = 5
TAMANOS = [20, 200, 2000]
ARCHIVO_RESULTADOS = "resultados_bench_personaD.txt"

# salas sinteticas, la cantidad de enemigos, objetos y trampas varía según el id
def crear_registros(n):
    registros = []
    for i in range(1, n + 1):
        enemigos = [(f"e-{i}-{k}", "ent_rata_gigante", 12) for k in range(i % 4)]
        objetos = ["itm_daga_oxidada" for _ in range(i % 3)]
        trampas = [(f"t-{i}", "trp_dardos", True)] if i % 5 == 0 else []
        puertas = [("N", False), ("E", i % 2 == 0)]
        registros.append(RegistroSala(i, i * 10, enemigos, objetos, trampas, puertas))
    return registros


# se repite y se toma el mejor tiempo
def medir(funcion):
    mejor = None
    for _ in range(REPETICIONES):
        inicio = time.perf_counter()
        funcion()
        duracion = time.perf_counter() - inicio
        if mejor is None or duracion < mejor:
            mejor = duracion
    return mejor


def bench_formatos(lineas):
    lineas.append("-Guardado binario vs JSON-")
    with tempfile.TemporaryDirectory() as carpeta:
        ruta_bin = os.path.join(carpeta, "partida.bin")
        ruta_json = os.path.join(carpeta, "partida.json")

        for n in TAMANOS:
            registros = crear_registros(n)
            sala_buscada = n // 2

            def guardar_bin():
                guardar_partida(ruta_bin, "cripta-01", "a3f91c", "cat-2026-08-01", 12345, 250, registros)

            def guardar_json():
                guardar_partida_json(ruta_json, "cripta-01", "a3f91c", "cat-2026-08-01", 12345, 250, registros)

            def cargar_todo_bin():
                with LectorPartida(ruta_bin) as lector:
                    lector.leer_todas_salas()

            def una_sala_bin():
                with LectorPartida(ruta_bin) as lector:
                    lector.leer_sala(sala_buscada)

            def cargar_todo_json():
                cargar_partida_json(ruta_json)

            def una_sala_json():
                leer_sala_json(ruta_json, sala_buscada)

            guardar_bin()
            guardar_json()
            lineas.append(f"n = {n:5d} tamaño:         binario = {os.path.getsize(ruta_bin):7d} B   json = {os.path.getsize(ruta_json):7d} B")
            lineas.append(f"n = {n:5d} guardar:        binario = {medir(guardar_bin):.6f}s  json = {medir(guardar_json):.6f}s")
            lineas.append(f"n = {n:5d} cargar todo:    binario = {medir(cargar_todo_bin):.6f}s  json = {medir(cargar_todo_json):.6f}s")
            lineas.append(f"n = {n:5d} cargar 1 sala:  binario = {medir(una_sala_bin):.6f}s  json = {medir(una_sala_json):.6f}s")


def correr_bench():
    lineas = []
    bench_formatos(lineas)
    for linea in lineas:
        print(linea)

    with open(ARCHIVO_RESULTADOS, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(lineas) + "\n")


if __name__ == "__main__":
    correr_bench()